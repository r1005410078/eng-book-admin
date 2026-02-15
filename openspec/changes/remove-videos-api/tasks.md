# 任务列表

## Phase 1: 添加 Lesson 接口
- [ ] 1.1 实现 `GET /api/v1/lessons/{lesson_id}/subtitles` 接口
  - 从 Lesson 关联的 Video 获取字幕
  - 返回完整的字幕列表（包含翻译、音标等）
- [ ] 1.2 实现 `POST /api/v1/lessons/{lesson_id}/reprocess` 接口
  - 支持 force 参数
  - 触发 Celery 任务重新处理视频
  - 返回任务 ID
- [ ] 1.3 实现 `GET /api/v1/lessons/{lesson_id}/processing-status` 接口
  - 返回当前处理状态
  - 返回进度百分比
  - 返回任务日志列表
- [ ] 1.4 添加请求/响应 Schema
  - SubtitleResponse
  - ReprocessRequest
  - ProcessingStatusResponse
- [ ] 1.5 添加单元测试
  - 测试字幕获取
  - 测试重处理触发
  - 测试状态查询

## Phase 2: 验证现有功能
- [ ] 2.1 测试 `POST /courses/upload` 完整流程
  - 上传多个视频文件
  - 验证 Course/Unit/Lesson 创建
  - 验证 Video 记录创建
  - 验证 Celery 任务触发
- [ ] 2.2 测试 `GET /courses/{id}/progress` 
  - 验证返回所有 Lesson 的处理状态
  - 验证进度计算正确
- [ ] 2.3 运行所有现有测试
  - Course 相关测试
  - Lesson 相关测试
  - 确保无回归

## Phase 3: 移除 Videos 接口
- [ ] 3.1 从 `app/api/v1/router.py` 移除 video router
  - 删除 `from app.api.v1 import video`
  - 删除 `api_router.include_router(video.router, ...)`
- [ ] 3.2 处理 `app/api/v1/video.py`
  - 选项 A: 删除文件
  - 选项 B: 添加废弃标记，保留一段时间
- [ ] 3.3 更新 API 文档
  - 移除 Videos 相关文档
  - 添加新 Lesson 接口文档
  - 添加迁移指南

## Phase 4: 清理和优化
- [ ] 4.1 清理未使用的代码
  - 检查是否有其他地方引用 video router
  - 清理未使用的 imports
- [ ] 4.2 保留必要的服务层
  - ✅ 保留 `app/services/video_service.py`
  - ✅ 保留 `app/models/video.py`
  - ✅ 保留 `app/schemas/video.py`（如果内部使用）
- [ ] 4.3 更新测试
  - 移除 Videos API 相关测试
  - 确保 Lesson 测试覆盖新功能
- [ ] 4.4 更新项目文档
  - 更新 README
  - 更新 API 使用示例

## Phase 5: 前端迁移支持
- [ ] 5.1 创建迁移指南文档
  - 列出所有 API 变更
  - 提供代码迁移示例
- [ ] 5.2 提供过渡期支持（可选）
  - 如果需要，可以保留旧接口一段时间
  - 添加废弃警告

## 验收检查清单
- [ ] 所有新 Lesson 接口正常工作
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] API 文档更新完成
- [ ] 无 `/videos/*` 路由注册
- [ ] 前端迁移指南完成
- [ ] 代码审查通过
- [ ] 性能测试通过

## 注意事项
1. **数据完整性** - 删除 Lesson 时确保级联删除 Video 和文件
2. **向后兼容** - 如果有外部依赖，需要提供过渡期
3. **性能** - Lesson 接口需要高效查询关联数据
4. **错误处理** - 完善的错误信息和状态码
