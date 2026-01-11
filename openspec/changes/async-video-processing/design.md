# 技术设计文档：异步化 Run Sync 与 Reprocess 进度查询

## Context

当前系统的 `run_sync` 接口是同步执行的调试接口，在处理长视频时容易导致 HTTP 请求超时。同时，`reprocess` 接口虽然可以触发重新处理，但缺少直观的进度查询能力，用户无法了解任务的执行状态。

### 背景约束
- 现有系统已使用 Celery + Redis 进行异步任务处理
- 视频处理包含多个步骤：音频提取、字幕生成、翻译、音标、语法分析
- 需要保持 API 的向后兼容性（尽可能）
- 需要支持并发处理多个视频

### 利益相关者
- **内容创作者**：需要实时了解视频处理进度
- **开发团队**：需要可靠的异步处理机制
- **运维团队**：需要监控任务执行状态

## Goals / Non-Goals

### Goals
- ✅ 将 `run_sync` 改造为异步触发接口，避免 HTTP 超时
- ✅ 提供统一的进度查询接口，支持实时查询任务进度
- ✅ 返回详细的子任务进度信息
- ✅ 保持现有数据模型的兼容性
- ✅ 提供清晰的任务状态（pending, processing, completed, failed）

### Non-Goals
- ❌ 不改变视频处理的核心逻辑
- ❌ 不引入新的消息队列系统
- ❌ 不改变现有的数据库表结构（除非必要）
- ❌ 不支持任务取消功能（可作为未来扩展）

## Decisions

### 决策 1：使用 FastAPI BackgroundTasks vs Celery

**选择**：优先使用现有的 Celery 任务系统

**理由**：
- 系统已经配置了 Celery + Redis
- Celery 提供更强大的任务管理能力（重试、监控、分布式）
- FastAPI BackgroundTasks 适合轻量级任务，视频处理属于重量级任务
- Celery 支持任务进度追踪（使用 `update_state`）

**备选方案**：
- FastAPI BackgroundTasks：简单但功能有限，不适合长时间运行的任务
- 自建任务队列：开发成本高，不推荐

### 决策 2：进度查询接口设计

**选择**：添加 `GET /api/v1/videos/{video_id}/reprocess` 用于查询进度

**理由**：
- 符合 RESTful 设计原则（GET 用于查询）
- 与 `POST /api/v1/videos/{video_id}/reprocess` 形成完整的触发-查询对
- 语义清晰，用户容易理解

**备选方案考虑**：
- **方案 A**：使用现有的 `/status` 接口
  - 优点：复用现有逻辑
  - 缺点：用户反馈希望在 `reprocess` 接口直接查询
- **方案 B**：创建独立的 `/progress` 接口
  - 优点：职责更单一
  - 缺点：增加 API 数量，用户需要记住更多端点

### 决策 3：进度计算方式

**选择**：基于固定步骤数计算总体进度

**实现方式**：
```python
# 定义处理步骤及其权重
PROCESSING_STEPS = {
    "extract_audio": 10,      # 10%
    "generate_subtitle": 20,  # 20%
    "translate": 30,          # 30%
    "phonetic": 20,           # 20%
    "grammar_analysis": 20    # 20%
}

# 总进度 = Σ(步骤进度 × 步骤权重)
total_progress = sum(task.progress * PROCESSING_STEPS[task.name] / 100 
                     for task in tasks)
```

**理由**：
- 简单直观，易于理解和维护
- 权重可根据实际耗时调整
- 支持子任务级别的进度展示

**备选方案**：
- 基于时间估算：不准确，不同视频处理时间差异大
- 基于文件大小：不能反映实际处理进度

### 决策 4：响应格式设计

**run_sync 异步响应**（202 Accepted）：
```json
{
  "code": 202,
  "message": "任务已启动",
  "data": {
    "video_id": 1,
    "task_id": "celery-task-uuid",
    "status": "pending"
  }
}
```

**进度查询响应**（200 OK）：
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "video_id": 1,
    "status": "processing",
    "progress": 45,
    "tasks": [
      {
        "name": "extract_audio",
        "status": "completed",
        "progress": 100
      },
      {
        "name": "generate_subtitle",
        "status": "processing",
        "progress": 50
      },
      {
        "name": "translate",
        "status": "pending",
        "progress": 0
      }
    ],
    "started_at": "2026-01-11T10:00:00Z",
    "updated_at": "2026-01-11T10:05:30Z"
  }
}
```

### 决策 5：任务状态管理

**状态定义**：
- `pending`: 任务已创建，等待执行
- `processing`: 任务正在执行
- `completed`: 任务成功完成
- `failed`: 任务执行失败

**状态存储**：
- 使用现有的 `processing_tasks` 表
- 如需要，添加 `subtasks_progress` JSON 字段存储子任务进度

## Risks / Trade-offs

### 风险 1：并发任务管理

**风险**：同一视频可能被多次触发处理

**缓解措施**：
- 在启动任务前检查是否有正在进行的任务
- 如有进行中的任务，返回 409 Conflict
- 提供强制重新处理选项（query parameter: `force=true`）

### 风险 2：进度更新延迟

**风险**：Celery 任务进度更新可能有延迟

**缓解措施**：
- 使用 Redis 作为进度缓存，减少数据库查询
- 设置合理的进度更新频率（每个子任务完成时更新）
- 前端使用轮询或 WebSocket 实时获取进度

### 风险 3：任务失败处理

**风险**：任务失败后状态可能不一致

**缓解措施**：
- 使用 Celery 的重试机制（最多 3 次）
- 记录详细的错误日志
- 提供手动重试接口
- 失败后保留中间结果，支持断点续传

### Trade-off：API 兼容性

**权衡**：改变 `run_sync` 的响应格式会破坏向后兼容性

**决策**：
- 接受这个破坏性变更，因为 `run_sync` 是调试接口
- 在文档中明确标注为 **BREAKING CHANGE**
- 提供迁移指南
- 如需要，可保留旧接口并标记为 deprecated

## Migration Plan

### 阶段 1：开发和测试（3-5 天）
1. 实现异步任务触发逻辑
2. 实现进度查询接口
3. 编写单元测试和集成测试
4. 更新 API 文档

### 阶段 2：灰度发布（1-2 天）
1. 在测试环境部署
2. 使用真实视频进行测试
3. 监控任务执行情况
4. 收集性能数据

### 阶段 3：正式发布（1 天）
1. 更新生产环境
2. 通知用户 API 变更
3. 监控错误日志
4. 准备回滚方案

### 回滚方案
如果发现严重问题：
1. 恢复旧版本代码
2. 清理未完成的任务
3. 通知受影响的用户
4. 分析问题原因

## Implementation Details

### 核心代码结构

```python
# app/api/v1/video.py

@router.post("/videos/{video_id}/run_sync", status_code=202)
async def run_sync_processing(
    video_id: int,
    db: Session = Depends(get_db)
):
    """异步触发视频处理"""
    # 1. 检查视频是否存在
    video = get_video_or_404(db, video_id)
    
    # 2. 检查是否有正在进行的任务
    existing_task = check_running_task(db, video_id)
    if existing_task:
        raise HTTPException(409, "任务正在进行中")
    
    # 3. 启动 Celery 任务
    task = process_video_task.delay(video_id)
    
    # 4. 记录任务信息
    create_task_record(db, video_id, task.id)
    
    return {
        "code": 202,
        "message": "任务已启动",
        "data": {
            "video_id": video_id,
            "task_id": task.id,
            "status": "pending"
        }
    }

@router.get("/videos/{video_id}/reprocess")
async def get_reprocess_progress(
    video_id: int,
    db: Session = Depends(get_db)
):
    """查询视频处理进度"""
    # 1. 获取任务记录
    task_record = get_task_record(db, video_id)
    if not task_record:
        raise HTTPException(404, "未找到处理任务")
    
    # 2. 从 Celery 获取任务状态
    task = AsyncResult(task_record.task_id)
    
    # 3. 计算总体进度
    progress_data = calculate_progress(task)
    
    return {
        "code": 200,
        "message": "成功",
        "data": progress_data
    }
```

### 进度追踪实现

```python
# app/tasks/video_processing.py

@celery_app.task(bind=True)
def process_video_task(self, video_id: int):
    """视频处理任务"""
    steps = [
        ("extract_audio", extract_audio_step),
        ("generate_subtitle", generate_subtitle_step),
        ("translate", translate_step),
        ("phonetic", phonetic_step),
        ("grammar_analysis", grammar_analysis_step),
    ]
    
    for i, (step_name, step_func) in enumerate(steps):
        # 更新当前步骤状态
        self.update_state(
            state='PROGRESS',
            meta={
                'current_step': step_name,
                'step_index': i,
                'total_steps': len(steps),
                'progress': int((i / len(steps)) * 100)
            }
        )
        
        # 执行步骤
        try:
            step_func(video_id)
        except Exception as e:
            # 记录错误并失败
            self.update_state(
                state='FAILURE',
                meta={'error': str(e), 'step': step_name}
            )
            raise
    
    return {'status': 'completed', 'progress': 100}
```

## Open Questions

1. **Q**: 是否需要支持 WebSocket 实时推送进度？
   **A**: 暂不实现，使用轮询即可。可作为未来优化项。

2. **Q**: 任务保留时间多久？
   **A**: 建议保留 7 天，之后自动清理。可配置。

3. **Q**: 是否需要支持批量查询多个视频的进度？
   **A**: 暂不需要，可作为未来扩展。

4. **Q**: 失败的任务是否自动重试？
   **A**: 使用 Celery 的自动重试机制，最多 3 次，指数退避。

## References

- [Celery Task State](https://docs.celeryproject.org/en/stable/userguide/tasks.html#task-states)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
- [RESTful API Design Best Practices](https://restfulapi.net/)
