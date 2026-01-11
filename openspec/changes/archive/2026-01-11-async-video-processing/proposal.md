# Change: 异步化 Run Sync 与 Reprocess 进度查询

## Why

当前 `/api/v1/videos/{video_id}/run_sync` 是一个同步执行的调试接口，在处理长视频时容易导致 HTTP 请求超时（可能需要数分钟）。同时，`/api/v1/videos/{video_id}/reprocess` 接口虽然可以触发重新处理，但缺少直观的进度查询能力，用户无法实时了解任务的执行状态和进度。

这导致：
- 用户体验差：长时间等待无响应，不知道任务是否在执行
- 系统不稳定：HTTP 超时导致连接断开，但后台任务可能仍在执行
- 调试困难：无法追踪任务执行到哪一步

## What Changes

- **BREAKING** 将 `POST /api/v1/videos/{video_id}/run_sync` 改为异步触发接口
  - 立即返回 `202 Accepted` 而非等待处理完成
  - 返回任务 ID 和初始状态
  - 使用现有的 Celery 任务系统
- 添加 `GET /api/v1/videos/{video_id}/reprocess` 进度查询接口
  - 返回详细的任务进度（总体进度 + 子任务进度）
  - 支持实时查询任务状态（pending, processing, completed, failed）
  - 返回任务时间信息（开始时间、更新时间）
- 实现基于权重的进度计算逻辑
  - 定义各处理步骤的权重（音频提取 10%、字幕生成 20% 等）
  - 聚合子任务进度计算总体进度
- 添加并发任务检测和处理
  - 防止同一视频被重复处理
  - 支持强制重新处理选项
- 修改 `POST /api/v1/videos/{video_id}/reprocess` 接口
  - 改为异步触发，返回 `202 Accepted`
  - 与 `run_sync` 保持一致的响应格式

## Impact

- **影响的能力**: `video-processing`
- **影响的 API 端点**:
  - `POST /api/v1/videos/{video_id}/run_sync` - **BREAKING** 响应格式变更（同步 → 异步）
  - `GET /api/v1/videos/{video_id}/reprocess` - **新增** 进度查询接口
  - `POST /api/v1/videos/{video_id}/reprocess` - 响应格式变更（同步 → 异步）
  - `GET /api/v1/videos/{video_id}/status` - 可能需要增强以支持更详细的进度信息
- **影响的代码**:
  - `app/api/v1/video.py` - 修改 `run_sync_processing` 和 `reprocess_video` 函数
  - `app/services/video_service.py` - 添加进度查询和计算逻辑
  - `app/tasks/video_processing.py` - 增强任务进度追踪
  - `app/schemas/video.py` - 添加新的响应模型（`AsyncTaskResponse`, `TaskProgressResponse`）
- **数据库变更**:
  - 可能需要在 `processing_tasks` 表添加字段（如 `subtasks_progress` JSON 字段）
  - 或使用 Redis 缓存进度信息
- **依赖变更**:
  - 无新增外部依赖（使用现有的 Celery + Redis）
- **配置变更**:
  - 可能需要配置任务保留时间
  - 可能需要配置进度更新频率

## 替代方案讨论

- **方案 A** (选择): 保持 `POST /reprocess` 为触发，添加 `GET /reprocess` 为查询进度
  - ✅ 符合 RESTful 设计原则
  - ✅ 语义清晰，用户容易理解
  - ✅ 与用户需求一致
- **方案 B**: 保持 `reprocess` 仅作为触发，使用现有的 `/status` 查询进度
  - ❌ 用户反馈希望在 `reprocess` 接口直接查询
  - ❌ 需要记住两个不同的端点
- **方案 C**: 使用 WebSocket 推送进度
  - ❌ 增加系统复杂度
  - ❌ 需要额外的基础设施
  - 💡 可作为未来优化项

## 下一步

确认提案后，将按照以下步骤实施：

1. **API 改造**（1-2 天）
   - 重构 `POST /api/v1/videos/{video_id}/run_sync` 为异步触发
   - 添加 `GET /api/v1/videos/{video_id}/reprocess` 进度查询接口
   - 修改 `POST /api/v1/videos/{video_id}/reprocess` 为异步触发

2. **服务层实现**（1-2 天）
   - 实现进度计算逻辑
   - 实现任务状态管理
   - 实现并发任务检测

3. **测试**（1 天）
   - 单元测试：进度计算、状态管理
   - 集成测试：完整的异步处理流程
   - 端到端测试：真实视频处理场景

4. **文档和部署**（0.5 天）
   - 更新 API 文档
   - 更新迁移指南（BREAKING CHANGE）
   - 部署到测试环境验证

**预计总时间**: 3.5-5.5 天
