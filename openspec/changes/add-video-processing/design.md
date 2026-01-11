# Design Document: Video Processing

## Context

英语学习管理后台需要添加视频处理能力，这是一个新的核心功能模块。该功能涉及：
- 文件上传和存储
- 外部服务集成（FFmpeg, OpenAI Whisper, OpenAI GPT-4）
- 异步任务处理
- 数据库设计
- API 设计

**约束条件**:
- 数据库: PostgreSQL
- 文件存储: 本地文件系统
- 不进行视频转码
- 预算: 控制 OpenAI API 调用成本

**利益相关者**:
- 内容创作者: 需要高效的视频处理工具
- 学习者: 需要高质量的学习材料
- 系统管理员: 需要可靠和可维护的系统

## Goals / Non-Goals

### Goals
- 自动化视频字幕生成流程
- 提供高质量的翻译、音标和语法分析
- 支持大文件上传（最大 2GB）
- 异步处理，不阻塞用户操作
- 可编辑生成的内容
- 可追踪处理进度

### Non-Goals
- 视频转码和格式转换
- 实时视频流处理
- 多语言字幕支持（仅英文→中文）
- 视频编辑功能
- CDN 集成
- 云存储集成（本版本）

## Decisions

### Decision 1: 使用 Celery 进行异步处理
**选择**: Celery + Redis

**理由**:
- 视频处理是耗时操作（可能需要几分钟）
- 需要避免阻塞 HTTP 请求
- Celery 成熟稳定，与 FastAPI 集成良好
- Redis 已在技术栈中，无需额外依赖

**替代方案**:
- ❌ 同步处理: 会导致请求超时
- ❌ 后台线程: 难以管理和监控
- ❌ RQ (Redis Queue): 功能较少，社区较小

### Decision 2: 使用本地 Whisper 模型
**选择**: 本地 Whisper 模型（openai-whisper）

**理由**:
- 无 API 调用成本，长期成本更低
- 数据隐私性更好，视频不需要上传到外部服务
- 处理速度可控，不受 API 限流影响
- 离线可用，不依赖网络连接
- 可选择不同模型大小（tiny, base, small, medium, large）平衡速度和准确性

**替代方案**:
- ❌ OpenAI Whisper API: 有调用成本，数据需上传
- ❌ Google Speech-to-Text: 需要额外账号和配置，有成本
- ❌ Azure Speech: 同上

**技术要求**:
- **CPU 模式**: 可用但较慢（10分钟视频约需 5-10 分钟）
- **GPU 模式**: 推荐，需要 CUDA 支持（10分钟视频约需 1-2 分钟）
- **内存**: 至少 4GB RAM（medium 模型）
- **模型选择**: 
  - `tiny`: 最快，准确率较低（~39M 参数）
  - `base`: 快速，准确率一般（~74M 参数）
  - `small`: 平衡（~244M 参数）
  - `medium`: 推荐，高准确率（~769M 参数）
  - `large`: 最高准确率，最慢（~1550M 参数）

**成本对比**:
- 本地模型: 仅硬件成本（一次性）
- Whisper API: $0.006/分钟 × 100视频/月 × 10分钟 = $6/月
- **长期节省**: 1年节省 $72

### Decision 3: 数据库设计 - 关系型存储
**选择**: PostgreSQL 关系型存储

**理由**:
- 字幕数据结构化，适合关系型数据库
- 需要事务支持（删除视频时级联删除）
- PostgreSQL 支持 JSONB，可存储灵活的语法分析数据
- 查询性能好

**表设计**:
```
videos (1) ─┬─> (N) subtitles (1) ─> (1) grammar_analysis
            └─> (N) processing_tasks
```

**替代方案**:
- ❌ NoSQL: 不适合结构化数据和关系查询
- ❌ 文件存储: 查询和管理困难

### Decision 4: 文件存储 - 本地文件系统
**选择**: 本地文件系统，按视频ID组织目录

**目录结构**:
```
uploads/videos/{video_id}/
├── original.{ext}
├── audio.wav
├── subtitles.srt
└── thumbnail.jpg (可选)
```

**理由**:
- 简单直接，无需额外服务
- 便于开发和调试
- 成本低

**替代方案**:
- ❌ 云存储 (OSS/S3): 增加复杂度和成本，未来可扩展
- ❌ 数据库 BLOB: 性能差，不适合大文件

### Decision 5: 批量处理策略
**选择**: 逐句处理，批量保存

**流程**:
1. 生成所有字幕
2. 遍历每句字幕
3. 调用 OpenAI API（翻译、音标、语法）
4. 批量保存到数据库（每10句一批）

**理由**:
- 平衡 API 调用频率和数据库写入
- 部分失败时可恢复
- 进度可追踪

**替代方案**:
- ❌ 完全批量: API 限流风险，失败难恢复
- ❌ 完全逐句: 数据库写入过于频繁

### Decision 6: 错误处理和重试
**选择**: 指数退避重试 + 错误记录

**策略**:
- API 调用失败: 重试 3 次（1s, 2s, 4s）
- 任务失败: 标记状态，记录错误
- 部分失败: 继续处理，最后报告

**理由**:
- 网络波动常见，重试可提高成功率
- 指数退避避免过度重试
- 错误记录便于调试

## Architecture

### 系统架构图

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────────────────┐
│      FastAPI Server         │
│  ┌─────────────────────┐    │
│  │   API Layer         │    │
│  │  /api/v1/videos     │    │
│  └──────────┬──────────┘    │
│             │                │
│  ┌──────────▼──────────┐    │
│  │   Service Layer     │    │
│  │  VideoService       │    │
│  │  SubtitleService    │    │
│  └──────────┬──────────┘    │
│             │                │
│  ┌──────────▼──────────┐    │
│  │  Repository Layer   │    │
│  │  Database ORM       │    │
│  └──────────┬──────────┘    │
└─────────────┼─────────────┘
              │
              ▼
      ┌───────────────┐
      │  PostgreSQL   │
      └───────────────┘

┌─────────────────────────────┐
│    Celery Workers           │
│  ┌─────────────────────┐    │
│  │  Video Tasks        │    │
│  │  - extract_audio    │    │
│  │  - generate_subs    │    │
│  │  - enhance_subs     │    │
│  └──────────┬──────────┘    │
│             │                │
│  ┌──────────▼──────────┐    │
│  │  External Services  │    │
│  │  - FFmpeg           │    │
│  │  - Local Whisper    │    │
│  │  - OpenAI GPT-4     │    │
│  └─────────────────────┘    │
└─────────────────────────────┘
       ▲
       │ Redis Queue
       │
┌──────┴──────┐
│    Redis    │
└─────────────┘
```

### 数据流

```
1. 上传视频
   Client → API → Save File → DB → Queue Task → Return Response

2. 处理视频
   Queue → Worker → FFmpeg → Local Whisper Model → Save Subtitles → DB

3. 增强字幕
   Queue → Worker → Loop Subtitles → GPT-4 API → Save Data → DB

4. 查询状态
   Client → API → DB → Return Status
```

## Risks / Trade-offs

### Risk 1: GPU 资源不足或不可用
**风险**: 本地 Whisper 模型在 CPU 模式下处理速度慢，可能导致处理积压

**缓解措施**:
- 优先使用 GPU 模式（如果可用）
- 使用较小的模型（如 small 或 medium）平衡速度和准确性
- 限制并发处理数量
- 监控处理队列长度
- 提供处理时间估算

### Risk 2: 模型加载和内存占用
**风险**: Whisper 模型较大，加载和运行需要较多内存

**缓解措施**:
- 使用模型缓存，避免重复加载
- 选择合适大小的模型（medium 推荐）
- 监控内存使用
- 配置 worker 数量避免内存耗尽

### Risk 2: 磁盘空间不足
**风险**: 大量视频文件可能耗尽磁盘空间

**缓解措施**:
- 监控磁盘使用率
- 实现定期清理机制（删除旧的临时文件）
- 配置磁盘空间告警
- 文档说明存储需求

### Risk 3: 处理失败恢复
**风险**: 处理过程中系统崩溃或重启

**缓解措施**:
- 使用 Celery 的持久化队列
- 任务状态记录到数据库
- 支持重新处理功能
- 实现幂等性（重复处理不会产生副作用）

### Risk 4: 成本控制
**风险**: OpenAI API 调用成本可能超出预算

**缓解措施**:
- 实现使用量监控
- 设置每月预算告警
- 考虑缓存常见翻译
- 提供成本估算工具

### Trade-off 1: 准确性 vs 成本
**选择**: 使用 GPT-4 而非 GPT-3.5

**权衡**:
- ✅ 更高的翻译和分析质量
- ❌ 更高的成本（约 10 倍）
- **决策**: 使用 GPT-4，质量优先

### Trade-off 2: 实时性 vs 资源消耗
**选择**: 异步处理

**权衡**:
- ✅ 不阻塞用户操作
- ✅ 更好的资源利用
- ❌ 用户需要等待处理完成
- **决策**: 异步处理，提供进度查询

## Migration Plan

### 阶段 1: 开发环境设置
1. 安装 FFmpeg
2. 配置 Celery 和 Redis
3. 创建数据库表
4. 创建上传目录

### 阶段 2: 核心功能开发
1. 实现视频上传
2. 实现音频提取
3. 实现字幕生成
4. 实现字幕增强

### 阶段 3: 测试和优化
1. 单元测试
2. 集成测试
3. 性能测试
4. 错误处理测试

### 阶段 4: 部署
1. 生产环境配置
2. 数据库迁移
3. 监控设置
4. 文档更新

### 回滚计划
如果部署后发现严重问题：
1. 停止 Celery workers
2. 回滚数据库迁移
3. 恢复旧版本代码
4. 清理上传的文件（如需要）

## Performance Considerations

### 预期性能指标
- 视频上传: < 5秒（100MB 文件）
- 音频提取: ~10秒/小时视频
- 字幕生成（GPU）: ~1-2分钟/小时视频
- 字幕生成（CPU）: ~5-10分钟/小时视频
- 字幕增强: ~2分钟/小时视频（50句）
- **总计（GPU）**: 10分钟视频约 1-2 分钟处理时间
- **总计（CPU）**: 10分钟视频约 3-5 分钟处理时间

### 优化策略
1. **并发处理**: 使用 Celery 多 worker
2. **批量操作**: 批量保存数据库
3. **缓存**: 缓存常见翻译和音标
4. **索引**: 数据库表添加适当索引

### 扩展性
- **水平扩展**: 增加 Celery worker 数量
- **垂直扩展**: 增加服务器资源
- **未来**: 考虑分布式存储和 CDN

## Security Considerations

### 文件上传安全
- 验证文件类型（MIME type）
- 限制文件大小
- 扫描恶意内容（未来）
- 使用安全的文件名

### API 安全
- 所有端点需要认证（未来）
- 限流保护
- 输入验证
- SQL 注入防护（使用 ORM）

### 数据安全
- 敏感信息加密
- 定期备份数据库
- 访问控制（用户只能访问自己的视频）

## Monitoring and Logging

### 监控指标
- 视频处理成功率
- 平均处理时间
- API 调用次数和成本
- 磁盘使用率
- Celery 队列长度
- 错误率

### 日志记录
- 视频上传日志
- 处理任务日志
- API 调用日志
- 错误日志（包含堆栈跟踪）

### 告警
- 处理失败率 > 10%
- 磁盘使用率 > 80%
- API 成本超出预算
- Celery 队列积压 > 100

## Open Questions

1. **缩略图生成**: 是否需要自动生成视频缩略图？
   - **建议**: 第一版不实现，未来可添加

2. **批量上传**: 是否需要支持批量上传多个视频？
   - **建议**: 第一版不实现，单个上传即可

3. **用户认证**: 何时添加用户认证和权限控制？
   - **建议**: 在基本功能完成后添加

4. **字幕格式**: 是否需要支持导出其他字幕格式（如 VTT, ASS）？
   - **建议**: 第一版只支持 SRT，未来可扩展

5. **视频预览**: 是否需要在线视频播放器？
   - **建议**: 前端功能，后端只提供文件访问

## Dependencies

### 新增 Python 包
```txt
# 视频和音频处理
ffmpeg-python==0.2.0
srt==3.5.3
aiofiles==23.2.1

# Whisper 模型（使用 whisper 而不是 openai-whisper）
whisper  # 本地 Whisper 模型
# GPU 支持（可选，推荐）
torch>=2.0.0  # PyTorch
# 如果使用 GPU，还需要安装 CUDA toolkit

# 异步任务
celery[redis]>=5.3.6  # 已有
```

### 系统依赖
```bash
# FFmpeg（必需）
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Ubuntu

# GPU 支持（可选，推荐）
# NVIDIA GPU + CUDA Toolkit
# 参考: https://developer.nvidia.com/cuda-downloads

# Whisper 模型下载（首次运行时自动下载）
# 模型会下载到 ~/.cache/whisper/
# medium 模型约 1.5GB
```

### 服务依赖
- Redis (已有，用于 Celery)
- PostgreSQL (已有)

## References

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [OpenAI Whisper (GitHub)](https://github.com/openai/whisper)
- [Whisper Model Card](https://github.com/openai/whisper/blob/main/model-card.md)
- [Celery Documentation](https://docs.celeryproject.org/)
- [SRT Format Specification](https://en.wikipedia.org/wiki/SubRip)
- [PyTorch Documentation](https://pytorch.org/docs/stable/index.html)

---

**文档版本**: 1.0  
**作者**: AI Assistant  
**创建日期**: 2026-01-11  
**最后审核**: 待审核
