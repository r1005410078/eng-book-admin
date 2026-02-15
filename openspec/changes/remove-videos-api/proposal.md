# 移除 Videos API 并迁移功能到 Lessons

## 概述

简化 API 架构，移除独立的 `/api/v1/videos/*` 接口，将视频相关功能整合到 Lesson 级别的接口中。

## 背景

当前系统同时提供了 Videos API 和 Courses/Lessons API，导致：
1. **功能重复** - 视频上传既可以通过 `/videos/upload` 也可以通过 `/courses/upload`
2. **架构复杂** - 视频管理分散在两个不同的 API 层级
3. **逻辑混乱** - Video 可以独立存在，但实际上总是属于某个 Lesson

## 目标

1. 统一视频管理入口，所有视频操作通过 Lesson 进行
2. 简化 API 结构，减少维护成本
3. 保持现有功能完整性

## 变更内容

### 移除的接口

| 方法 | 路径 | 说明 | 替代方案 |
|------|------|------|----------|
| POST | `/api/v1/videos/upload` | 独立上传视频 | `POST /courses/upload` |
| GET | `/api/v1/videos/` | 列出所有视频 | 通过 Course/Lesson 查询 |
| GET | `/api/v1/videos/{id}` | 获取视频详情 | Lesson 中包含 video 信息 |
| DELETE | `/api/v1/videos/{id}` | 删除视频 | `DELETE /lessons/{id}` 级联删除 |
| POST | `/api/v1/videos/{id}/run_sync` | 手动触发处理 | `POST /lessons/{id}/reprocess` |
| POST | `/api/v1/videos/{id}/reprocess` | 重新处理 | `POST /lessons/{id}/reprocess` |
| GET | `/api/v1/videos/{id}/status` | 处理状态 | `GET /lessons/{id}/processing-status` |
| GET | `/api/v1/videos/{id}/subtitles` | 获取字幕 | `GET /lessons/{id}/subtitles` |

### 新增的接口

#### 1. 获取课时字幕
```
GET /api/v1/lessons/{lesson_id}/subtitles
```

**Response:**
```json
[
  {
    "id": 1,
    "lesson_id": 123,
    "start_time": 0.0,
    "end_time": 2.5,
    "text": "Hello world",
    "translation": "你好世界",
    "phonetic": "[həˈloʊ wɜːrld]"
  }
]
```

#### 2. 重新处理课时
```
POST /api/v1/lessons/{lesson_id}/reprocess
```

**Request:**
```json
{
  "force": true
}
```

**Response:**
```json
{
  "message": "Reprocessing started",
  "lesson_id": 123,
  "task_id": "abc-123"
}
```

#### 3. 获取处理状态
```
GET /api/v1/lessons/{lesson_id}/processing-status
```

**Response:**
```json
{
  "lesson_id": 123,
  "status": "PROCESSING",
  "progress_percent": 45,
  "tasks": [
    {
      "step_name": "TRANSCODE",
      "action": "COMPLETE",
      "created_at": "2026-02-15T12:00:00Z"
    }
  ]
}
```

### 保留的接口

以下接口保持不变：
- `POST /api/v1/courses/upload` - 上传课程（包含视频）
- `GET /api/v1/courses/{id}/progress` - 获取课程处理进度

## 数据模型

### 保持不变
- ✅ `Video` 模型继续存在
- ✅ `Lesson.video_id` 外键保持
- ✅ 视频文件存储逻辑不变

### 代码变更
- ❌ 移除 `app/api/v1/video.py` 路由注册
- ✅ 保留 `app/services/video_service.py`（内部使用）
- ✅ 保留 `app/models/video.py`

## 影响分析

### 前端影响
需要更新所有调用 `/videos/*` 的代码，改为：
- 视频上传 → 使用 `/courses/upload`
- 获取字幕 → 使用 `/lessons/{id}/subtitles`
- 重新处理 → 使用 `/lessons/{id}/reprocess`
- 查看状态 → 使用 `/lessons/{id}/processing-status`

### 后端影响
- 移除 video router 注册
- 添加 3 个新的 lesson 接口
- 内部服务层保持不变

### 数据库影响
- ✅ 无需修改数据库结构
- ✅ 现有数据完全兼容

## 实施计划

### Phase 1: 添加 Lesson 接口（2-3小时）
- [ ] 实现 `GET /lessons/{id}/subtitles`
- [ ] 实现 `POST /lessons/{id}/reprocess`
- [ ] 实现 `GET /lessons/{id}/processing-status`
- [ ] 添加单元测试

### Phase 2: 验证现有功能（1小时）
- [ ] 确认 `POST /courses/upload` 正常
- [ ] 确认 `GET /courses/{id}/progress` 正常
- [ ] 运行集成测试

### Phase 3: 移除 Videos 接口（1-2小时）
- [ ] 从 router.py 移除 video router
- [ ] 标记 video.py 为废弃
- [ ] 更新 API 文档

### Phase 4: 清理优化（1小时）
- [ ] 清理未使用的代码
- [ ] 更新测试
- [ ] 更新 README

## 测试策略

### 单元测试
- Lesson 字幕接口测试
- Lesson 重处理接口测试
- Lesson 状态查询测试

### 集成测试
- 完整上传流程测试
- 删除级联测试
- 重处理流程测试

### 回归测试
- 所有现有 Course 测试
- 所有现有 Lesson 测试

## 风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 前端依赖旧接口 | 高 | 提供迁移指南，保留旧接口一段时间 |
| 数据不一致 | 中 | 完整的测试覆盖 |
| 性能问题 | 低 | Lesson 查询已优化 |

## 验收标准

- [ ] 所有新 Lesson 接口正常工作
- [ ] 所有测试通过（单元+集成）
- [ ] API 文档更新完成
- [ ] 无 `/videos/*` 路由存在
- [ ] 前端迁移指南完成

## 时间估算

总计：**5-7 小时**

## 相关文档

- [Course Structure Spec](../add-learning-path/specs/course-structure/spec.md)
- [Subtitle API Spec](../add-learning-path/specs/subtitle-api/spec.md)

---

**创建日期**: 2026-02-15  
**状态**: 提案中
