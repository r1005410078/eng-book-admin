# 任务列表

## Phase 1: 添加 Lesson 接口
- [x] 1.1 实现 `GET /api/v1/lessons/{lesson_id}/subtitles` 接口
  - 从 Lesson 关联的 Video 获取字幕
  - 返回完整的字幕列表（包含翻译、音标等）
  - ✅ 已在 `app/api/v1/lessons.py` 实现
- [x] 1.2 实现 `POST /api/v1/lessons/{lesson_id}/reprocess` 接口
  - 支持 force 参数
  - 触发 Celery 任务重新处理视频
  - 返回任务 ID
- [ ] 1.3 添加请求/响应 Schema
  - ReprocessRequest
  - ReprocessResponse
- [x] 1.4 添加单元测试
  - 测试字幕获取
  - 测试重处理触发

**说明**：不实现单独的 processing-status 接口，使用现有的 `GET /courses/{id}/progress` 代替

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
- [x] 3.1 从 `app/api/v1/router.py` 移除 video router
  - 删除 `from app.api.v1 import video`
  - 删除 `api_router.include_router(video.router, ...)`
- [x] 3.2 删除 `app/api/v1/video.py` 文件
  - 移除整个文件（应用未使用）
- [x] 3.3 更新 API 文档
  - 移除 Videos 相关文档
  - 更新 Lesson 接口文档

## Phase 4: 清理和优化
- [ ] 4.1 清理未使用的代码
  - 检查是否有其他地方引用 video router
  - 清理未使用的 imports
- [ ] 4.2 保留必要的服务层
  - ✅ 保留 `app/services/video_service.py`（内部使用）
  - ✅ 保留 `app/models/video.py`（Lesson 关联）
  - ✅ 保留 `app/schemas/video.py`（内部使用）
- [ ] 4.3 更新测试
  - 移除 Videos API 相关测试（如果有）
  - 确保 Lesson 测试覆盖新功能
- [ ] 4.4 更新项目文档
  - 更新 README
  - 更新 API 使用示例

## 验收检查清单
- [ ] Lesson reprocess 接口正常工作
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] 无 `/videos/*` 路由存在
- [ ] 代码审查通过

## 注意事项
1. **数据完整性** - 删除 Lesson 时确保级联删除 Video 和文件
2. **性能** - Lesson 接口需要高效查询关联数据
3. **错误处理** - 完善的错误信息和状态码
4. **应用未使用** - 当前应用没有前端，无需考虑向后兼容
