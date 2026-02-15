.PHONY: help install run test clean format lint

help:  ## 显示帮助信息
	@echo "英语学习管理后台 - 可用命令："
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## 安装依赖
	@echo "📦 安装 Python 依赖..."
	pip install -r requirements.txt

run:  ## 启动开发服务器
	@echo "🚀 启动开发服务器..."
	@set -a && [ -f .env ] && . .env && set +a && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

worker:  ## 启动 Celery Worker (单进程模式)
	@echo "⚙️  启动 Celery Worker (Concurrency: 1)..."
	@set -a && [ -f .env ] && . .env && set +a && celery -A app.core.celery_app worker --loglevel=info -c 1

test:  ## 运行测试
	@echo "🧪 运行测试..."
	pytest tests/ -v

test-cov:  ## 运行测试并生成覆盖率报告
	@echo "🧪 运行测试并生成覆盖率报告..."
	pytest tests/ --cov=app --cov-report=html --cov-report=term

format:  ## 格式化代码
	@echo "✨ 格式化代码..."
	black app/ tests/
	isort app/ tests/

lint:  ## 代码检查
	@echo "🔍 代码检查..."
	flake8 app/ tests/
	mypy app/

clean:  ## 清理临时文件
	@echo "🧹 清理临时文件..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage

dev-setup:  ## 开发环境初始化
	@echo "🔧 初始化开发环境..."
	python -m venv venv
	@echo "✓ 虚拟环境已创建"
	@echo ""
	@echo "请运行以下命令激活虚拟环境："
	@echo "  source venv/bin/activate  # macOS/Linux"
	@echo "  venv\\Scripts\\activate     # Windows"
	@echo ""
	@echo "然后运行: make install"

env-example:  ## 创建 .env 文件
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✓ .env 文件已创建，请编辑配置"; \
	else \
		echo "⚠️  .env 文件已存在"; \
	fi
