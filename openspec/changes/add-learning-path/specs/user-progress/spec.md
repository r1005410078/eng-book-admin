## ADDED Requirements

### Requirement: 用户进度追踪
系统 MUST 追踪用户在学习路径中的进度。
- **范围**: 针对每个用户单独追踪每个 `Course`, `Unit`, 和 `Lesson` 实例的状态。
- **状态**: 至少支持 `LOCKED` (锁定), `ACTIVE` (进行中), 和 `COMPLETED` (已完成)。
- **解锁逻辑**: 提供一种机制，当完成项目 N 时自动解锁项目 N+1。

#### Scenario: 完成课时并解锁下一课
- **WHEN** 用户以及格分数完成“课时 1.1”
- **THEN** “课时 1.1”的进度被标记为 `COMPLETED`
- **AND** 下一个顺序课时“课时 1.2”（如果是 `LOCKED` 状态）更新为 `ACTIVE`

### Requirement: 进度整合的大纲视图
API MUST 提供整合了用户进度状态的大纲结构。
- 获取课程结构时，每个项目都应反映调用用户的状态（`LOCKED`, `ACTIVE`, 或 `COMPLETED`）。

#### Scenario: 查看带有进度的课程大纲
- **WHEN** 用户查看“商务英语”的课程大纲
- **THEN** 之前完成的课时显示为 `COMPLETED`
- **AND** 当前课时显示为 `ACTIVE`
- **AND** 未来的课时显示为 `LOCKED`

### Requirement: 用户进度管理接口 (User Progress & History)
系统 MUST 提供针对用户端的进度管理 API，支持上报学习数据和查询历史状态。

- **上报学习进度 (Report Progress)**: 提供 `POST /api/v1/lessons/{id}/progress` 接口。
  - **Body**: `{ "status": "COMPLETED", "video_progress": 120, "last_played_at": "timestamp" }`
  - **Logic**: 
    - 更新 `user_progress` 表。
    - 如果 status 变为 COMPLETED，触发解锁下一个课时的逻辑 (Unlock Next)。
    - 如果 status 为 ACTIVE，仅更新最后访问时间。

- **获取课程学习状态 (Get Learning Status)**: 提供 `GET /api/v1/courses/{id}/learning-status` 接口。
  - **Response**: `{ "course_id": 1, "completed_lessons": 5, "total_lessons": 20, "last_accessed_lesson_id": 12, "is_completed": false }`
  - **Use Case**: 首页仪表盘展示“继续学习”按钮。

#### Scenario: 完成视频观看并自动解锁
- **WHEN** 用户观看完 Lesson 5 的视频
- **THEN** 前端调用 `POST /lessons/5/progress` with status=COMPLETED
- **AND** 后端验证通过（如：观看时长 >= 视频时长 * 90%）
- **AND** 后端将 Lesson 5 标记为 COMPLETED
- **AND** 后端查找 Lesson 6 并将其状态从 LOCKED 更新为 ACTIVE
