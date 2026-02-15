# 提案：移除 Videos API 并迁移功能到 Lessons

## 📋 概述

**目标**：简化 API 架构，移除独立的 `/api/v1/videos/*` 接口，将视频相关功能整合到 Lesson 级别的接口中。

**原因**：
1. 功能重复 - Videos 接口与 Courses/Lessons 接口有重叠
2. 架构简化 - 统一通过 Course → Unit → Lesson 层级管理所有内容
3. 更符合业务逻辑 - 视频始终属于某个 Lesson，不应独立存在

## 🎯 当前问题

### 现有 Videos 接口
```
POST   /api/v1/videos/upload              - 独立上传视频
GET    /api/v1/videos/                     - 列出所有视频
GET    /api/v1/videos/{video_id}           - 获取视频详情
DELETE /api/v1/videos/{video_id}           - 删除视频
POST   /api/v1/videos/{video_id}/run_sync  - 手动触发处理
POST   /api/v1/videos/{video_id}/reprocess - 重新处理视频
GET    /api/v1/videos/{video_id}/status    - 获取处理状态
GET    /api/v1/videos/{video_id}/subtitles - 获取字幕
```

### 问题分析
1. **重复上传路径** - 既有 `POST /videos/upload` 又有 `POST /courses/upload`
2. **孤立的视频管理** - 视频应该总是属于某个 Lesson
3. **状态查询分散** - 处理状态既可以从 Video 查，也可以从 Course 查
4. **删除逻辑复杂** - 需要同时处理 Video 和 Lesson 的关联

## ✅ 解决方案

### 1. 移除的接口

**完全移除：**
- ❌ `POST /api/v1/videos/upload` - 已有 `POST /courses/upload`
- ❌ `GET /api/v1/videos/` - 不需要列出所有视频
- ❌ `GET /api/v1/videos/{video_id}` - 通过 Lesson 获取
- ❌ `DELETE /api/v1/videos/{video_id}` - 通过删除 Lesson 级联删除

### 2. 迁移到 Lessons 的功能

**新增 Lesson 接口：**

```
GET    /api/v1/lessons/{lesson_id}/subtitles
       获取课时的字幕列表
       Response: List[SubtitleResponse]

POST   /api/v1/lessons/{lesson_id}/reprocess
       重新处理课时视频（重新生成字幕、分析等）
       Request: { force: bool }
       Response: { message: str, task_id: str }

GET    /api/v1/lessons/{lesson_id}/processing-status
       获取课时视频处理状态
       Response: { 
         status: str,
         progress_percent: int,
         tasks: List[TaskJournalResponse]
       }
```

### 3. 保留的现有接口

**Courses 接口（已存在）：**
```
POST   /api/v1/courses/upload
       上传课程（包含视频文件）
       
GET    /api/v1/courses/{course_id}/progress
       获取课程所有 Lesson 的处理进度
```

## 📝 实现步骤

### Phase 1: 添加 Lesson 级别接口
1. ✅ 创建 `GET /lessons/{id}/subtitles` 接口
2. ✅ 创建 `POST /lessons/{id}/reprocess` 接口
3. ✅ 创建 `GET /lessons/{id}/processing-status` 接口
4. ✅ 添加对应的测试

### Phase 2: 迁移现有功能
1. ✅ 确保 `POST /courses/upload` 正常工作
2. ✅ 确保 `GET /courses/{id}/progress` 返回完整信息
3. ✅ 更新文档和示例

### Phase 3: 移除 Videos 接口
1. ✅ 从 `app/api/v1/router.py` 移除 video router
2. ✅ 标记 `app/api/v1/video.py` 为废弃（或删除）
3. ✅ 更新所有引用 Videos 接口的代码
4. ✅ 更新 API 文档

### Phase 4: 清理和优化
1. ✅ 保留 Video 模型（Lesson 仍需要关联）
2. ✅ 保留 VideoService（内部使用）
3. ✅ 清理不再使用的代码
4. ✅ 更新测试

## 🔄 数据模型变化

**保持不变：**
- ✅ `Video` 模型继续存在（作为 Lesson 的关联）
- ✅ `Lesson.video_id` 外键保持
- ✅ 视频文件存储逻辑不变

**删除：**
- ❌ 独立的 Video CRUD 接口
- ❌ Video 相关的 API schemas（如果只用于 API）

## 📊 影响分析

### 前端影响
- 需要更新所有调用 `/videos/*` 的代码
- 改为调用 `/lessons/*` 或 `/courses/*`

### 后端影响
- 移除 `app/api/v1/video.py` 路由
- 保留 `app/services/video_service.py`（内部使用）
- 保留 `app/models/video.py`

### 数据库影响
- ✅ 无需修改数据库结构
- ✅ 现有数据完全兼容

## 🧪 测试计划

1. **单元测试**
   - Lesson 字幕接口测试
   - Lesson 重处理接口测试
   - Lesson 状态查询测试

2. **集成测试**
   - 完整的课程上传 → 处理 → 查询流程
   - 删除 Lesson 时视频的级联删除

3. **回归测试**
   - 确保现有 Course 功能不受影响
   - 确保 Subtitle 功能正常

## 📅 时间估算

- Phase 1: 2-3 小时（添加新接口）
- Phase 2: 1 小时（验证现有功能）
- Phase 3: 1-2 小时（移除旧接口）
- Phase 4: 1 小时（清理优化）

**总计**: 约 5-7 小时

## ✅ 验收标准

1. ✅ 所有 Lesson 相关功能通过新接口正常工作
2. ✅ `POST /courses/upload` 完整流程正常
3. ✅ 所有测试通过
4. ✅ API 文档更新完成
5. ✅ 无 `/videos/*` 路由存在

## 🚀 后续优化

完成此重构后，可以考虑：
1. 优化 Lesson 的视频处理流程
2. 添加批量重处理功能
3. 改进处理状态的实时推送

## 📌 注意事项

1. **向后兼容** - 如果有外部系统依赖 Videos API，需要提供迁移指南
2. **数据完整性** - 确保删除 Lesson 时正确清理 Video 和相关文件
3. **性能** - Lesson 接口需要高效查询关联的 Video 数据

---

**提案人**: AI Assistant  
**日期**: 2026-02-15  
**状态**: 待审批
