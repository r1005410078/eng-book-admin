# 项目结构

## 📁 目录结构

```
eng-book-admin/
│
├── 📄 README.md                    # 项目说明文档
├── 📄 PROJECT_SUMMARY.md           # 项目总结文档
├── 📄 STRUCTURE.md                 # 项目结构说明（本文件）
├── 📄 requirements.txt             # Python 依赖列表
├── 📄 Makefile                     # 常用命令快捷方式
├── 📄 .env.example                 # 环境变量示例
├── 📄 .gitignore                   # Git 忽略配置
├── 🚀 start.sh                     # 快速启动脚本
│
├── 📂 app/                         # 应用主目录
│   ├── 📄 __init__.py
│   ├── 📄 main.py                  # FastAPI 应用入口 ⭐
│   │
│   ├── 📂 api/                     # API 路由层
│   │   ├── 📄 __init__.py
│   │   └── 📂 v1/                  # API v1 版本
│   │       ├── 📄 __init__.py
│   │       ├── 📄 hello.py         # Hello World API ✅
│   │       └── 📄 router.py        # 路由汇总
│   │
│   ├── 📂 core/                    # 核心配置
│   │   ├── 📄 __init__.py
│   │   └── 📄 config.py            # 应用配置 ⚙️
│   │
│   ├── 📂 models/                  # 数据库模型（SQLAlchemy）
│   │   └── 📄 __init__.py
│   │
│   ├── 📂 schemas/                 # Pydantic 数据模型
│   │   └── 📄 __init__.py
│   │
│   ├── 📂 services/                # 业务逻辑层
│   │   └── 📄 __init__.py
│   │
│   ├── 📂 repositories/            # 数据访问层
│   │   └── 📄 __init__.py
│   │
│   ├── 📂 tasks/                   # Celery 异步任务
│   │   └── 📄 __init__.py
│   │
│   └── 📂 utils/                   # 工具函数
│       └── 📄 __init__.py
│
├── 📂 tests/                       # 测试目录
│   ├── 📄 __init__.py
│   └── 📄 test_hello.py            # Hello API 测试 ✅
│
└── 📂 openspec/                    # 项目规范文档
    └── 📄 project.md               # 项目上下文文档
```

## 📝 文件说明

### 核心文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `app/main.py` | FastAPI 应用入口，配置路由和中间件 | ✅ 完成 |
| `app/core/config.py` | 应用配置，使用 Pydantic Settings | ✅ 完成 |
| `app/api/v1/hello.py` | Hello World API 实现 | ✅ 完成 |
| `app/api/v1/router.py` | API v1 路由汇总 | ✅ 完成 |

### 配置文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `requirements.txt` | Python 依赖列表 | ✅ 完成 |
| `.env.example` | 环境变量示例 | ✅ 完成 |
| `.gitignore` | Git 忽略配置 | ✅ 完成 |
| `Makefile` | 常用命令快捷方式 | ✅ 完成 |

### 文档文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `README.md` | 项目说明和快速开始指南 | ✅ 完成 |
| `PROJECT_SUMMARY.md` | 项目总结和开发计划 | ✅ 完成 |
| `openspec/project.md` | 详细的项目上下文文档 | ✅ 完成 |

### 测试文件

| 文件 | 说明 | 状态 |
|------|------|------|
| `tests/test_hello.py` | Hello API 单元测试 | ✅ 完成 |

## 🎯 架构说明

### 分层架构

```
┌─────────────────────────────────────┐
│         API Layer (FastAPI)         │  ← app/api/
│    (路由、请求处理、响应格式化)        │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│       Service Layer (业务逻辑)       │  ← app/services/
│   (核心业务逻辑、数据处理、AI调用)     │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│    Repository Layer (数据访问)       │  ← app/repositories/
│      (数据库操作、ORM 封装)           │
└─────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│         Database (PostgreSQL)       │
└─────────────────────────────────────┘
```

### 目录职责

- **app/api/** - API 路由定义，处理 HTTP 请求和响应
- **app/core/** - 核心配置和依赖注入
- **app/models/** - SQLAlchemy 数据库模型
- **app/schemas/** - Pydantic 数据验证模型
- **app/services/** - 业务逻辑实现
- **app/repositories/** - 数据库访问层
- **app/tasks/** - Celery 异步任务
- **app/utils/** - 通用工具函数
- **tests/** - 单元测试和集成测试

## 🚀 快速命令

```bash
# 查看所有可用命令
make help

# 安装依赖
make install

# 启动开发服务器
make run

# 运行测试
make test

# 代码格式化
make format

# 代码检查
make lint

# 清理临时文件
make clean
```

## 📊 当前进度

- ✅ 项目结构搭建
- ✅ FastAPI 应用配置
- ✅ Hello World API 实现
- ✅ 测试框架搭建
- ✅ 文档编写
- ⏳ 数据库集成
- ⏳ 单词本功能
- ⏳ 文章功能
- ⏳ 视频功能
- ⏳ AI 集成
- ⏳ 异步任务处理

## 📚 相关文档

- [README.md](README.md) - 项目介绍和快速开始
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 项目总结和开发计划
- [openspec/project.md](openspec/project.md) - 详细的项目上下文
