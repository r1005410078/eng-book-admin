# 英语学习管理后台

这是一个基于 FastAPI 的英语学习应用管理后台系统。

## 功能特性

- ✅ **单词本管理** - 创建、编辑、删除单词本和单词条目
- ✅ **英语文章管理** - 上传和管理英语学习文章
- ✅ **英语视频管理** - 上传视频，自动生成字幕、翻译、音标和语法解析

## 技术栈

- **Python 3.8+**
- **FastAPI** - 现代化的高性能 Web 框架
- **SQLAlchemy** - ORM 数据库操作
- **Celery** - 异步任务处理
- **Redis** - 缓存和任务队列
- **OpenAI API** - AI 翻译和语法分析
- **FFmpeg** - 视频/音频处理

## 项目结构

```
eng-book-admin/
├── app/
│   ├── api/              # API 路由
│   │   └── v1/
│   │       ├── hello.py      # Hello World API
│   │       └── router.py     # 路由汇总
│   ├── core/             # 核心配置
│   │   └── config.py         # 应用配置
│   ├── models/           # 数据库模型
│   ├── schemas/          # Pydantic 模型
│   ├── services/         # 业务逻辑层
│   ├── repositories/     # 数据访问层
│   ├── tasks/            # Celery 任务
│   ├── utils/            # 工具函数
│   └── main.py           # 应用入口
├── tests/                # 测试文件
├── requirements.txt      # 依赖列表
├── .env.example          # 环境变量示例
└── README.md             # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入你的配置
# 特别是 OPENAI_API_KEY 和数据库连接信息
```

### 3. 启动应用

```bash
# 开发模式启动（支持热重载）
python app/main.py

# 或使用 uvicorn 命令
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问 API 文档

启动成功后，访问以下地址：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **根路径**: http://localhost:8000/

## API 接口

### Hello World 接口

#### 1. 基本问候
```bash
GET /api/v1/hello
```

响应示例：
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "greeting": "你好，欢迎使用英语学习管理后台！",
    "english": "Hello, Welcome to English Learning Admin System!",
    "timestamp": "2026-01-11T11:12:00",
    "version": "0.1.0"
  }
}
```

#### 2. 个性化问候
```bash
GET /api/v1/hello/{name}
```

示例：
```bash
curl http://localhost:8000/api/v1/hello/张三
```

#### 3. 健康检查
```bash
GET /api/v1/health
```

### OpenAI 接口

#### 1. 查看配置
```bash
GET /api/v1/openai/config
```

#### 2. 测试连接
```bash
GET /api/v1/openai/test
```

#### 3. 翻译文本
```bash
POST /api/v1/openai/translate
Content-Type: application/json

{
  "text": "Hello World",
  "target_language": "中文"
}
```

#### 4. 语法分析
```bash
POST /api/v1/openai/grammar
Content-Type: application/json

{
  "sentence": "I have been studying English for three years."
}
```

#### 5. 生成音标
```bash
POST /api/v1/openai/phonetic
Content-Type: application/json

{
  "text": "Hello World",
  "accent": "美式"
}
```

## 视频处理功能

系统提供完整的视频处理流水线，支持：

1. **视频上传**：自动保存并提取元数据
2. **音频提取**：使用 FFmpeg 提取音频
3. **字幕生成**：使用本地 **Whisper** 模型生成中英文对照字幕
4. **AI 增强**：使用 GPT-4 进行批量翻译、音标标注和语法分析
5. **异步处理**：基于 Celery 的后台任务队列，支持进度查询

### 依赖配置

**1. 系统依赖**
- **FFmpeg**: 必需，用于音视频处理
  ```bash
  # macOS
  brew install ffmpeg
  # Ubuntu
  sudo apt-get install ffmpeg
  ```

- **GPU 支持 (可选但推荐)**:
  - 安装 NVIDIA 驱动
  - 安装 CUDA Toolkit (11.8 或 12.x)

**2. Python 依赖**
```bash
pip install -r requirements.txt
```
> 注意：`whisper` 包会在首次运行时自动下载模型（默认 medium 模型约 1.5GB）。

**3. 服务依赖**
- **Redis**: 用于 Celery 消息队列
- **PostgreSQL**: 数据库

### 部署指南

推荐使用 Docker Compose 启动基础设施：

```bash
# 启动数据库和 Redis
./db.sh start
# 或
docker compose up -d

# 初始化数据库
alembic upgrade head

# 启动 API 服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动 Celery Worker (处理异步任务)
celery -A app.core.celery_app worker --loglevel=info
```

### 视频 API 接口

#### 1. 上传视频
```bash
POST /api/v1/videos/upload
Content-Type: multipart/form-data
# file: 视频文件
# title: 标题
```

#### 2. 查询处理状态
```bash
GET /api/v1/videos/{video_id}/status
```

#### 3. 获取字幕（含语法分析）
```bash
GET /api/v1/videos/{video_id}/subtitles?include_grammar=true
```

## 开发指南

### 代码规范

- 遵循 **PEP 8** Python 代码规范
- 使用 **Black** 进行代码格式化
- 使用 **isort** 进行导入排序
- 函数和类必须有完整的中文文档字符串

### 运行测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html
```

### 代码格式化

```bash
# 格式化代码
black app/

# 排序导入
isort app/

# 代码检查
flake8 app/
```

## 下一步计划
- [x] 集成 OpenAI API ✅
- [x] 实现视频 CRUD API ✅
- [x] 实现视频处理流程（FFmpeg + Whisper）✅
- [x] 添加数据库迁移 ✅
- [x] Docker 容器化部署 (DB & Redis) ✅
- [ ] 实现用户认证和授权
- [ ] 添加单词本 CRUD API
- [ ] 添加文章 CRUD API

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue。
