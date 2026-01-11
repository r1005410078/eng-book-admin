# Change: 添加视频处理功能

## Why

当前系统缺少视频内容管理能力。用户需要上传英语学习视频，并自动生成字幕、翻译、音标和语法分析，以便创建高质量的学习材料。这是英语学习应用的核心功能之一。

## What Changes

- 添加视频上传和存储功能
- 集成 FFmpeg 提取音频
- 集成本地 Whisper 模型生成字幕（支持 GPU 加速）
- 实现字幕的翻译、音标标注和语法分析
- 提供字幕编辑和查询 API
- 实现异步任务处理（Celery）
- 添加处理进度追踪

## Impact

- **新增能力**: `video-processing`
- **影响的代码**:
  - 新增数据库表: `videos`, `subtitles`, `grammar_analysis`, `processing_tasks`
  - 新增 API 路由: `/api/v1/videos/*`
  - 新增服务: `VideoService`, `FFmpegService`, `SubtitleService`
  - 新增 Celery 任务: `process_video`, `enhance_subtitles`
- **依赖变更**:
  - 新增: `openai-whisper`, `torch`, `ffmpeg-python`, `srt`, `aiofiles`
  - 系统依赖: FFmpeg, CUDA Toolkit (可选，用于 GPU 加速)
- **配置变更**:
  - 新增环境变量: `UPLOAD_DIR`, `MAX_VIDEO_SIZE`, `FFMPEG_PATH`
  - 需要配置 Celery 和 Redis
