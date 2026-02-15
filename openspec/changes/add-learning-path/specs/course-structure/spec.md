## ADDED Requirements

### Requirement: 简化版课程管理接口
系统 MUST 提供简洁、高层级的课程管理接口，聚焦于“上传”、“修改”、“获取课程内容”和“进度获取”三个核心场景，屏蔽内部复杂的处理细节。

- **上传课程 (Upload)**: 提供一个聚合接口或流程，允许用户一次性定义课程结构并上传核心视频文件。
- **修改课程 (Modify)**: 提供统一的接口用于修改课程结构、更新视频内容或人工修正 AI 生成的数据（字幕/翻译）。
- **获取进度 (Get Progress)**: 提供统一的进度查询接口，返回课程下所有内容的自动化处理状态及详细日志。
- **Resource Recovery**: 当课程或课时被删除时，系统 MUST 支持通过级联策略 (Soft Delete + GC) 回收关联的视频及字幕文件，防止产生孤儿数据。

#### Scenario: 极简上传流程
- **WHEN** 用户调用 `POST /courses/upload` 接口
- **AND** 提交课程基本信息及一组视频文件
- **THEN** 系统自动完成结构创建、文件关联及后台任务触发
- **AND** 返回一个 `job_id` 或 `course_id` 用于后续进度查询

#### Scenario: 统一进度查询
- **WHEN** 用户调用 `GET /courses/{id}/progress`
- **THEN** 系统返回该课程下所有课时的处理状态（转码、翻译、分析）
- **AND** 包含每个步骤的详细日志（开始时间、耗时、结果）

### Requirement: 动静分离的课程内容查询
系统 MUST 将课程内容的查询拆分为“静态内容”和“动态进度”两个维度，以优化加载速度和缓存策略，并支持高效率的数据关联查询。

- **静态内容接口**: 提供 `GET /lessons/{id}/content` 接口，返回视频 URL、全量字幕、语法解析等不常变更的数据。该接口 MUST 支持 ETag 缓存机制。
- **动态进度接口**: 提供 `GET /lessons/{id}/progress` 接口，仅返回当前用户的学习进度（如 completed status, last timestamp）。
- **智能预加载**: 系统 SHOULD 支持返回下一课时的 ID，以便前端提前预加载静态内容。
- **语法全局关联**: 语法解析数据 MUST 包含结构化标签 (Tag/ID)，以支持跨课程的知识点关联查询。

#### Scenario: 获取完整课时内容
- **WHEN** 用户进入学习页面
- **THEN** 前端并发请求 `/content` (可缓存) 和 `/progress` (不可缓存)
- **AND** 系统返回带版本号 (ETag) 的字幕和语法数据
- **AND** 前端组合数据进行渲染

### Requirement: 获取课程列表及状态
为了支持后台管理和用户浏览，系统 MUST 提供获取所有课程列表的接口，并包含课程的基本信息及当前的状态概览。

- **获取课程列表 (List Courses)**: 提供 `GET /api/v1/courses/` 接口，支持分页查询。
- **状态概览 (Status Overview)**: 返回列表中应包含每个课程的单元数、课时数以及处理进度状态（如：Processing, Completed）。

#### Scenario: 浏览课程列表
- **WHEN** 管理员或用户访问课程管理页面
- **THEN** 调用 `GET /api/v1/courses/`
- **AND** 系统返回课程列表，包含 ID, Title, Description, Cover, Tags, Units Count, Lessons Summary (Total/Processed)

### Requirement: 完整的课程内容管理 (CMS)
为了支持后台管理人员维护课程，系统 MUST 提供完整的 CRUD 接口，支持对课程、单元和课时的增删改查及排序。

- **删除课程 (Delete Course)**: 提供 `DELETE /api/v1/courses/{id}` 接口。
  - **Logic**: 执行级联软删除 (Soft Delete)，将课程及其下属所有单元、课时、任务日志标记为已删除。关联的视频文件应在后台异步清理 (GC)。
- **删除课时 (Delete Lesson)**: 提供 `DELETE /api/v1/lessons/{id}` 接口。
  - **Logic**: 软删除指定课时。如果单元因此为空，保留单元。
- **添加课时 (Add Lesson)**: 提供 `POST /api/v1/units/{id}/lessons` 接口，支持上传单个视频文件作为新课时。
  - **Logic**: 类似课程上传流程，创建课时 -> 创建视频占位 -> 异步处理 -> 触发任务。
- **调整排序 (Reorder)**: 提供 `PATCH /api/v1/lessons/{id}` 接口，支持修改 `order_index` 或移动至其他单元 (`unit_id`)。

#### Scenario: 删除过期课程
- **WHEN** 管理员调用 `DELETE /api/v1/courses/101`
- **THEN** 系统将 Course 101 及其 Unit, Lesson 状态标记为 DELETED
- **AND** 返回 200 OK
- **BUT** 物理文件暂时保留，等待 GC 任务回收

#### Scenario: 向现有课程补充课时
- **WHEN** 管理员调用 `POST /api/v1/units/5/lessons` 上传视频 `new_video.mp4`
- **THEN** 系统在 Unit 5 下创建新课时
- **AND** 立即开始后台转码和 AI 处理任务
