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
