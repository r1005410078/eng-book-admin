# 数据库和依赖配置完成

## ✅ 已完成的配置

### 1. Docker 数据库服务

已创建 `docker-compose.yml`，包含：

#### PostgreSQL 15
- **容器名**: eng-book-postgres
- **端口**: 5432
- **数据库**: eng_learning_db
- **用户**: eng_admin
- **密码**: eng_password_2026
- **数据卷**: postgres_data (持久化存储)

#### Redis 7
- **容器名**: eng-book-redis
- **端口**: 6379
- **数据卷**: redis_data (持久化存储)

### 2. 数据库连接配置

已更新 `.env.example` 和 `.env`:

```bash
DATABASE_URL=postgresql://eng_admin:eng_password_2026@localhost:5432/eng_learning_db
REDIS_URL=redis://localhost:6379/0
```

### 3. Python 依赖更新

已更新 `requirements.txt`，使用 `whisper` 而不是 `openai-whisper`:

```txt
# 视频/音频处理
ffmpeg-python==0.2.0
srt==3.5.3
aiofiles==23.2.1

# Whisper 语音识别
whisper  # 本地 Whisper 模型（使用 pip install whisper）
torch>=2.0.0  # PyTorch（支持 GPU 加速）
```

### 4. 数据库管理脚本

已创建 `db.sh` 脚本，提供以下功能：

| 命令 | 功能 |
|------|------|
| `./db.sh start` | 启动数据库服务 |
| `./db.sh stop` | 停止数据库服务 |
| `./db.sh restart` | 重启数据库服务 |
| `./db.sh status` | 查看服务状态 |
| `./db.sh logs` | 查看数据库日志 |
| `./db.sh psql` | 连接到 PostgreSQL |
| `./db.sh redis-cli` | 连接到 Redis |
| `./db.sh backup` | 备份数据库 |
| `./db.sh restore <file>` | 恢复数据库 |
| `./db.sh clean` | 清理所有数据 |

## 🚀 服务状态

### 当前运行的服务

```
✅ eng-book-postgres - PostgreSQL 15 (健康检查中)
✅ eng-book-redis - Redis 7 (健康检查中)
```

### 连接测试

```bash
✅ PostgreSQL: /var/run/postgresql:5432 - accepting connections
```

## 📋 快速使用指南

### 启动数据库

```bash
# 方式1: 使用管理脚本
./db.sh start

# 方式2: 使用 docker compose
docker compose up -d
```

### 停止数据库

```bash
# 方式1: 使用管理脚本
./db.sh stop

# 方式2: 使用 docker compose
docker compose stop
```

### 连接到数据库

```bash
# PostgreSQL
./db.sh psql

# 或直接使用 psql
psql postgresql://eng_admin:eng_password_2026@localhost:5432/eng_learning_db

# Redis
./db.sh redis-cli
```

### 查看日志

```bash
# PostgreSQL 日志
./db.sh logs

# 所有服务日志
docker compose logs -f
```

### 备份和恢复

```bash
# 备份数据库
./db.sh backup
# 备份文件保存在: backup/db_backup_YYYYMMDD_HHMMSS.sql

# 恢复数据库
./db.sh restore backup/db_backup_20260111_123456.sql
```

## 🔧 下一步操作

### 1. 安装 Python 依赖

```bash
# 安装所有依赖（包括 whisper 和 torch）
pip install -r requirements.txt

# 注意：torch 可能需要较长时间下载
```

### 2. 配置数据库模型

```bash
# 创建数据库迁移
alembic revision --autogenerate -m "Initial migration"

# 运行迁移
alembic upgrade head
```

### 3. 验证配置

```python
# 测试数据库连接
from sqlalchemy import create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    result = conn.execute("SELECT version();")
    print(result.fetchone())
```

## 📝 重要说明

### Whisper 包说明

您使用的是 `pip install whisper` 而不是 `openai-whisper`。两者的区别：

- **whisper**: 可能是其他实现或包装
- **openai-whisper**: OpenAI 官方实现

如果遇到问题，可能需要：
```bash
pip uninstall whisper
pip install openai-whisper
```

或者确认 `whisper` 包的具体实现。

### GPU 支持

如果要使用 GPU 加速 Whisper：

1. 安装 CUDA Toolkit
2. 安装支持 CUDA 的 PyTorch:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. 验证 GPU 可用:
   ```python
   import torch
   print(torch.cuda.is_available())  # 应返回 True
   ```

### 数据持久化

数据库数据存储在 Docker volumes 中：
- `eng-book-admin_postgres_data`
- `eng-book-admin_redis_data`

即使删除容器，数据也会保留。要完全清理：
```bash
./db.sh clean  # 会删除所有数据，需要确认
```

## 🔍 故障排查

### 端口冲突

如果 5432 或 6379 端口被占用：

```bash
# 查看端口占用
lsof -i :5432
lsof -i :6379

# 修改 docker-compose.yml 中的端口映射
# 例如: "15432:5432" 和 "16379:6379"
```

### 连接失败

```bash
# 检查服务状态
./db.sh status

# 查看日志
./db.sh logs

# 重启服务
./db.sh restart
```

### 数据库初始化失败

```bash
# 查看初始化日志
docker compose logs postgres

# 重新初始化
docker compose down -v
docker compose up -d
```

## 📚 相关文件

- `docker-compose.yml` - Docker 服务配置
- `docker/postgres/init/01-init.sql` - 数据库初始化脚本
- `db.sh` - 数据库管理脚本
- `.env` - 环境变量配置
- `requirements.txt` - Python 依赖

---

**配置完成时间**: 2026-01-11 12:22  
**数据库状态**: ✅ 运行中  
**准备就绪**: 是
