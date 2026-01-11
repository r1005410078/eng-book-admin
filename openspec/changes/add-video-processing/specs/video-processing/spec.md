# Video Processing Specification Delta

## ADDED Requirements

### Requirement: Video Upload
系统 SHALL 允许用户上传视频文件，并保存视频元数据。

#### Scenario: 成功上传视频
- **WHEN** 用户上传一个有效的 MP4 视频文件（标题为"英语学习视频"，大小为100MB）
- **THEN** 系统保存视频文件到本地存储
- **AND** 系统提取视频元数据（时长、分辨率、文件大小）
- **AND** 系统创建视频记录并返回视频ID
- **AND** 系统将视频状态设置为 "uploading"

#### Scenario: 上传文件过大
- **WHEN** 用户上传一个大于 2GB 的视频文件
- **THEN** 系统返回 413 错误
- **AND** 系统提示"文件过大，最大支持 2GB"

#### Scenario: 上传不支持的格式
- **WHEN** 用户上传一个 .avi 格式的视频文件
- **THEN** 系统接受该文件（支持 MP4, AVI, MOV, MKV, WebM）
- **AND** 系统正常处理

### Requirement: Audio Extraction
系统 SHALL 使用 FFmpeg 从视频中提取音频轨道。

#### Scenario: 成功提取音频
- **WHEN** 视频上传完成后
- **THEN** 系统启动异步任务提取音频
- **AND** 系统使用 FFmpeg 将视频转换为 WAV 格式音频（16kHz, 单声道）
- **AND** 系统保存音频文件到 `uploads/videos/{video_id}/audio.wav`
- **AND** 系统更新处理任务状态为 "completed"

#### Scenario: FFmpeg 执行失败
- **WHEN** FFmpeg 执行过程中发生错误
- **THEN** 系统记录错误信息
- **AND** 系统将任务状态设置为 "failed"
- **AND** 系统保留错误日志供调试

### Requirement: Subtitle Generation
系统 SHALL 使用本地 Whisper 模型从音频生成英文字幕。

#### Scenario: 成功生成字幕
- **WHEN** 音频提取完成后
- **THEN** 系统加载本地 Whisper 模型（默认使用 medium 模型）
- **AND** 系统使用 Whisper 模型进行语音识别
- **AND** 系统生成 SRT 格式字幕
- **AND** 系统解析 SRT 文件，提取每句字幕的序号、时间轴和文本
- **AND** 系统将字幕保存到数据库
- **AND** 系统保存 SRT 文件到 `uploads/videos/{video_id}/subtitles.srt`

#### Scenario: Whisper 模型处理失败
- **WHEN** Whisper 模型处理过程中发生错误（如内存不足）
- **THEN** 系统记录详细错误信息
- **AND** 系统将任务状态设置为 "failed"
- **AND** 系统保留错误日志供调试

#### Scenario: 使用 GPU 加速
- **WHEN** 系统检测到可用的 CUDA GPU
- **THEN** 系统使用 GPU 模式运行 Whisper 模型
- **AND** 系统处理速度显著提升（约 3-5 倍）

#### Scenario: CPU 模式降级
- **WHEN** 系统未检测到 GPU 或 GPU 不可用
- **THEN** 系统自动降级到 CPU 模式
- **AND** 系统记录警告日志提示性能较慢
- **AND** 系统继续处理但速度较慢

### Requirement: Subtitle Translation
系统 SHALL 将英文字幕翻译成中文。

#### Scenario: 批量翻译字幕
- **WHEN** 字幕生成完成后
- **THEN** 系统启动字幕增强任务
- **AND** 系统遍历所有字幕句子
- **AND** 系统调用 OpenAI API 将每句英文翻译成中文
- **AND** 系统将翻译结果保存到 `subtitles` 表的 `translation` 字段

#### Scenario: 翻译单句失败
- **WHEN** 某一句字幕翻译失败
- **THEN** 系统记录该句的错误
- **AND** 系统继续处理下一句
- **AND** 系统在任务完成后报告部分失败

### Requirement: Phonetic Notation
系统 SHALL 为每句字幕生成国际音标（IPA）。

#### Scenario: 生成美式音标
- **WHEN** 字幕翻译完成后
- **THEN** 系统调用 OpenAI API 为每句英文生成美式音标
- **AND** 系统将音标保存到 `subtitles` 表的 `phonetic` 字段
- **AND** 系统使用国际音标（IPA）格式

#### Scenario: 音标生成失败
- **WHEN** 音标生成过程中发生错误
- **THEN** 系统记录错误但继续处理
- **AND** 系统将该句的 `phonetic` 字段设置为 NULL

### Requirement: Grammar Analysis
系统 SHALL 分析每句字幕的语法结构和重点。

#### Scenario: 完整语法分析
- **WHEN** 音标生成完成后
- **THEN** 系统调用 OpenAI API 分析每句字幕
- **AND** 系统提取句子结构类型（简单句/复合句/复杂句）
- **AND** 系统识别语法重点（如时态、从句、语态等）
- **AND** 系统提取难点词汇及其释义和音标
- **AND** 系统识别常用短语
- **AND** 系统生成整体语法解释
- **AND** 系统将分析结果保存到 `grammar_analysis` 表

#### Scenario: 语法分析返回 JSON
- **WHEN** OpenAI API 返回语法分析结果
- **THEN** 结果 MUST 包含 `sentence_structure` 字段
- **AND** 结果 MUST 包含 `grammar_points` 数组
- **AND** 结果 MUST 包含 `difficult_words` 数组
- **AND** 结果 MAY 包含 `phrases` 数组
- **AND** 结果 MAY 包含 `explanation` 字段

### Requirement: Subtitle Editing
系统 SHALL 允许用户编辑生成的字幕内容。

#### Scenario: 编辑字幕文本
- **WHEN** 用户更新字幕ID为 123 的原文为 "Hello, world!"
- **THEN** 系统验证字幕存在
- **AND** 系统更新 `original_text` 字段
- **AND** 系统更新 `updated_at` 时间戳
- **AND** 系统返回更新后的字幕对象

#### Scenario: 编辑字幕时间轴
- **WHEN** 用户更新字幕的 `start_time` 为 10.5 秒，`end_time` 为 15.0 秒
- **THEN** 系统验证 `end_time` 大于 `start_time`
- **AND** 系统更新时间轴
- **AND** 系统返回成功

#### Scenario: 时间轴验证失败
- **WHEN** 用户设置 `end_time` 小于或等于 `start_time`
- **THEN** 系统返回 400 错误
- **AND** 系统提示"结束时间必须大于开始时间"

### Requirement: Processing Status Query
系统 SHALL 提供视频处理进度查询功能。

#### Scenario: 查询处理中的视频状态
- **WHEN** 用户查询视频ID为 1 的处理状态
- **AND** 视频正在进行字幕生成（进度 60%）
- **THEN** 系统返回视频状态为 "processing"
- **AND** 系统返回所有处理任务列表
- **AND** 系统显示 "audio_extraction" 任务状态为 "completed"
- **AND** 系统显示 "subtitle_generation" 任务状态为 "processing"，进度 60%
- **AND** 系统显示 "translation" 任务状态为 "pending"
- **AND** 系统计算并返回总体进度百分比

#### Scenario: 查询已完成的视频状态
- **WHEN** 用户查询已完成处理的视频
- **THEN** 系统返回视频状态为 "completed"
- **AND** 系统返回所有任务状态均为 "completed"
- **AND** 系统返回总体进度为 100%

### Requirement: Video List Query
系统 SHALL 提供视频列表查询功能，支持分页和筛选。

#### Scenario: 分页查询视频列表
- **WHEN** 用户请求第 2 页，每页 20 条记录
- **THEN** 系统返回第 21-40 条视频记录
- **AND** 系统返回总记录数
- **AND** 系统返回当前页码和每页大小

#### Scenario: 按状态筛选视频
- **WHEN** 用户筛选状态为 "completed" 的视频
- **THEN** 系统只返回状态为 "completed" 的视频
- **AND** 系统按创建时间倒序排列

#### Scenario: 按难度级别筛选
- **WHEN** 用户筛选难度级别为 "intermediate" 的视频
- **THEN** 系统只返回 `difficulty_level` 为 "intermediate" 的视频

### Requirement: Subtitle List Query
系统 SHALL 提供字幕列表查询功能，支持关联查询语法分析。

#### Scenario: 查询视频字幕列表
- **WHEN** 用户查询视频ID为 1 的字幕列表
- **THEN** 系统返回该视频的所有字幕
- **AND** 系统按 `sequence_number` 升序排列
- **AND** 每条字幕包含：序号、时间轴、原文、翻译、音标

#### Scenario: 包含语法分析的字幕查询
- **WHEN** 用户查询字幕列表并设置 `includeGrammar=true`
- **THEN** 系统返回字幕列表
- **AND** 每条字幕关联其语法分析数据
- **AND** 语法分析包含：句子结构、语法点、难点词汇、短语、解释

### Requirement: Video Deletion
系统 SHALL 允许删除视频及其关联数据。

#### Scenario: 删除视频
- **WHEN** 用户删除视频ID为 1 的视频
- **THEN** 系统删除视频记录
- **AND** 系统级联删除所有关联的字幕记录
- **AND** 系统级联删除所有关联的语法分析记录
- **AND** 系统级联删除所有关联的处理任务记录
- **AND** 系统删除本地存储的视频文件、音频文件和字幕文件
- **AND** 系统返回成功

#### Scenario: 删除不存在的视频
- **WHEN** 用户删除不存在的视频ID
- **THEN** 系统返回 404 错误
- **AND** 系统提示"视频不存在"

### Requirement: Video Reprocessing
系统 SHALL 允许重新处理已上传的视频。

#### Scenario: 重新生成字幕
- **WHEN** 用户请求重新处理视频ID为 1，任务类型为 "subtitle_generation"
- **THEN** 系统删除现有字幕数据
- **AND** 系统启动新的字幕生成任务
- **AND** 系统返回新任务的状态

#### Scenario: 重新处理所有增强任务
- **WHEN** 用户请求重新处理，任务类型为 ["translation", "phonetic", "grammar_analysis"]
- **THEN** 系统保留原始字幕文本和时间轴
- **AND** 系统重新执行翻译、音标和语法分析
- **AND** 系统更新相应字段

### Requirement: Asynchronous Task Processing
系统 SHALL 使用 Celery 异步处理视频任务，避免阻塞 API 请求。

#### Scenario: 视频上传后启动异步任务
- **WHEN** 视频上传成功
- **THEN** 系统立即返回视频ID和状态
- **AND** 系统在后台启动 Celery 任务处理视频
- **AND** 用户可以通过状态查询 API 获取进度

#### Scenario: 任务失败重试
- **WHEN** Celery 任务执行失败（如网络错误）
- **THEN** 系统自动重试最多 3 次
- **AND** 系统使用指数退避策略（1秒、2秒、4秒）
- **AND** 如果所有重试失败，系统标记任务为 "failed"

### Requirement: Concurrent Processing Limit
系统 SHALL 限制同时处理的视频数量，避免资源耗尽。

#### Scenario: 并发限制
- **WHEN** 系统已有 3 个视频正在处理
- **AND** 新视频上传成功
- **THEN** 系统将新视频任务加入队列
- **AND** 系统等待现有任务完成后再处理新任务
- **AND** 系统配置最大并发数为 3（可配置）

### Requirement: Error Handling and Logging
系统 SHALL 记录所有处理错误和关键操作日志。

#### Scenario: 记录处理错误
- **WHEN** 任何处理步骤失败
- **THEN** 系统记录详细错误信息到日志
- **AND** 系统将错误信息保存到 `processing_tasks` 表的 `error_message` 字段
- **AND** 系统包含错误堆栈跟踪（用于调试）

#### Scenario: 记录关键操作
- **WHEN** 视频上传、处理开始、处理完成等关键操作发生
- **THEN** 系统记录操作日志
- **AND** 日志包含：时间戳、视频ID、操作类型、用户信息（如有）

### Requirement: File Storage Organization
系统 SHALL 按照规范的目录结构组织存储文件。

#### Scenario: 文件存储结构
- **WHEN** 视频ID为 123 的文件被处理
- **THEN** 系统创建目录 `uploads/videos/123/`
- **AND** 系统保存原始视频为 `uploads/videos/123/original.mp4`
- **AND** 系统保存提取的音频为 `uploads/videos/123/audio.wav`
- **AND** 系统保存字幕文件为 `uploads/videos/123/subtitles.srt`
- **AND** 系统可选保存缩略图为 `uploads/videos/123/thumbnail.jpg`
