# Video Processing Specification Delta - 异步化改造

## ADDED Requirements

### Requirement: Asynchronous Run Sync Processing
系统 SHALL 提供异步触发的调试接口，避免 HTTP 请求超时。

#### Scenario: 异步触发视频处理
- **WHEN** 用户调用 `POST /api/v1/videos/{video_id}/run_sync`
- **THEN** 系统立即返回 `202 Accepted` 状态码
- **AND** 系统返回响应包含 `{"message": "任务已启动", "video_id": 1, "task_id": "celery-uuid", "status": "pending"}`
- **AND** 系统在后台启动 Celery 任务处理视频
- **AND** 用户无需等待处理完成

#### Scenario: 检测并发任务冲突
- **WHEN** 用户对同一视频调用 `run_sync`
- **AND** 该视频已有正在进行的处理任务
- **THEN** 系统返回 `409 Conflict` 状态码
- **AND** 系统提示"该视频正在处理中，请稍后再试"
- **AND** 系统不启动新任务

#### Scenario: 强制重新处理
- **WHEN** 用户调用 `POST /api/v1/videos/{video_id}/run_sync?force=true`
- **AND** 该视频已有正在进行的任务
- **THEN** 系统取消现有任务（如可能）
- **AND** 系统启动新的处理任务
- **AND** 系统返回新任务的信息

### Requirement: Reprocess Progress Query
系统 SHALL 提供 reprocess 进度查询接口，支持实时查询任务进度。

#### Scenario: 查询处理中的任务进度
- **WHEN** 用户调用 `GET /api/v1/videos/{video_id}/reprocess`
- **AND** 视频正在进行处理（总进度 45%）
- **THEN** 系统返回 `200 OK` 状态码
- **AND** 系统返回响应包含：
  ```json
  {
    "video_id": 1,
    "status": "processing",
    "progress": 45,
    "tasks": [
      {"name": "extract_audio", "status": "completed", "progress": 100},
      {"name": "generate_subtitle", "status": "processing", "progress": 50},
      {"name": "translate", "status": "pending", "progress": 0},
      {"name": "phonetic", "status": "pending", "progress": 0},
      {"name": "grammar_analysis", "status": "pending", "progress": 0}
    ],
    "started_at": "2026-01-11T10:00:00Z",
    "updated_at": "2026-01-11T10:05:30Z"
  }
  ```

#### Scenario: 查询已完成的任务
- **WHEN** 用户查询已完成处理的视频进度
- **THEN** 系统返回 `status` 为 `"completed"`
- **AND** 系统返回 `progress` 为 `100`
- **AND** 所有子任务的 `status` 均为 `"completed"`
- **AND** 所有子任务的 `progress` 均为 `100`

#### Scenario: 查询失败的任务
- **WHEN** 用户查询处理失败的视频进度
- **THEN** 系统返回 `status` 为 `"failed"`
- **AND** 系统返回失败的子任务信息
- **AND** 系统返回错误消息（如有）
- **AND** 系统返回失败时间戳

#### Scenario: 查询不存在的任务
- **WHEN** 用户查询从未处理过的视频进度
- **THEN** 系统返回 `404 Not Found` 状态码
- **AND** 系统提示"未找到处理任务"

### Requirement: Task Progress Calculation
系统 SHALL 基于固定步骤权重计算总体进度。

#### Scenario: 计算总体进度
- **WHEN** 系统计算视频处理总体进度
- **THEN** 系统使用以下步骤权重：
  - `extract_audio`: 10%
  - `generate_subtitle`: 20%
  - `translate`: 30%
  - `phonetic`: 20%
  - `grammar_analysis`: 20%
- **AND** 系统计算总进度 = Σ(步骤进度 × 步骤权重)
- **AND** 系统返回 0-100 之间的整数

#### Scenario: 子任务进度更新
- **WHEN** 某个子任务正在执行
- **THEN** 系统实时更新该子任务的进度（0-100）
- **AND** 系统重新计算总体进度
- **AND** 系统更新 `updated_at` 时间戳

### Requirement: Task Status Management
系统 SHALL 管理任务的生命周期状态。

#### Scenario: 任务状态转换
- **WHEN** 任务被创建
- **THEN** 系统设置状态为 `"pending"`
- **WHEN** 任务开始执行
- **THEN** 系统更新状态为 `"processing"`
- **WHEN** 任务成功完成
- **THEN** 系统更新状态为 `"completed"`
- **WHEN** 任务执行失败
- **THEN** 系统更新状态为 `"failed"`

#### Scenario: 状态持久化
- **WHEN** 任务状态发生变化
- **THEN** 系统将状态保存到 `processing_tasks` 表
- **AND** 系统同时更新 Redis 缓存（如配置）
- **AND** 系统记录状态变更时间

## MODIFIED Requirements

### Requirement: Video Reprocessing
系统 SHALL 允许重新处理已上传的视频，并支持通过 GET 方法查询进度。

#### Scenario: 触发重新处理（POST）
- **WHEN** 用户调用 `POST /api/v1/videos/{video_id}/reprocess`
- **AND** 指定任务类型为 `["translation", "phonetic", "grammar_analysis"]`
- **THEN** 系统保留原始字幕文本和时间轴
- **AND** 系统启动异步任务重新执行指定的处理步骤
- **AND** 系统返回 `202 Accepted` 状态码
- **AND** 系统返回任务启动信息

#### Scenario: 查询重新处理进度（GET）
- **WHEN** 用户调用 `GET /api/v1/videos/{video_id}/reprocess`
- **THEN** 系统返回当前重新处理任务的进度
- **AND** 系统返回格式与进度查询接口相同
- **AND** 系统区分初次处理和重新处理的任务

#### Scenario: 重新生成字幕
- **WHEN** 用户请求重新处理视频ID为 1，任务类型为 `"subtitle_generation"`
- **THEN** 系统删除现有字幕数据
- **AND** 系统启动新的字幕生成任务
- **AND** 系统返回 `202 Accepted` 和新任务状态

### Requirement: Processing Status Query
系统 SHALL 提供视频处理进度查询功能，支持详细的子任务进度。

#### Scenario: 查询处理中的视频状态
- **WHEN** 用户查询视频ID为 1 的处理状态
- **AND** 视频正在进行字幕生成（进度 60%）
- **THEN** 系统返回视频状态为 `"processing"`
- **AND** 系统返回所有处理任务列表
- **AND** 系统显示 `"extract_audio"` 任务状态为 `"completed"`，进度 100%
- **AND** 系统显示 `"generate_subtitle"` 任务状态为 `"processing"`，进度 60%
- **AND** 系统显示 `"translate"` 任务状态为 `"pending"`，进度 0%
- **AND** 系统计算并返回总体进度百分比（基于权重）
- **AND** 系统返回任务开始时间和最后更新时间

#### Scenario: 查询已完成的视频状态
- **WHEN** 用户查询已完成处理的视频
- **THEN** 系统返回视频状态为 `"completed"`
- **AND** 系统返回所有任务状态均为 `"completed"`
- **AND** 系统返回总体进度为 100%
- **AND** 系统返回任务完成时间

#### Scenario: 查询失败的视频状态
- **WHEN** 用户查询处理失败的视频
- **THEN** 系统返回视频状态为 `"failed"`
- **AND** 系统返回失败的子任务名称和错误信息
- **AND** 系统返回已完成的子任务列表
- **AND** 系统返回失败时间

## REMOVED Requirements

无删除的需求。
