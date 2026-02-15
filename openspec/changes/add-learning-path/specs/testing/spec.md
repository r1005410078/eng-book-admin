## ADDED Requirements

### Requirement: 自动化测试覆盖
系统 MUST 为新增的课程管理核心流程提供自动化集成测试，确保接口契约与数据库状态的一致性。

- **测试范围**: 
  - **Upload Flow**: 验证 `POST /upload` 能够正确创建 Course/Unit/Lesson 层级结构，并初始化 TaskJournal。
  - **Modify Flow**: 验证 `PATCH /courses/{id}` 能够正确更新元数据。
  - **Progress Flow**: 验证 `GET /progress` 能够正确聚合 Lesson 状态和 Journal 日志。
- **环境隔离**: 测试执行 MUST 使用独立的数据库会话或事务回滚机制，避免污染开发/生产环境数据。

#### Scenario: 上传流程集成测试
- **GIVEN** 构造一个包含2个视频文件的 `multipart/form-data` 请求
- **WHEN** 调用 `POST /api/v1/courses/upload`
- **THEN** 响应状态码为 200
- **AND** 数据库中新增 1 个 Course, 1 个 Default Unit, 2 个 Lesson
- **AND** 每个 Lesson 都有对应的 `INIT` 状态日志

#### Scenario: 进度查询集成测试
- **GIVEN** 数据库中存在一个正在处理中的 Lesson (Status: PROCESSING) 且包含 2 条日志
- **WHEN** 调用 `GET /api/v1/courses/{id}/progress`
- **THEN** 响应中包含该 Lesson 的进度百分比
- **AND** `logs` 数组中包含完整的 2 条日志记录
