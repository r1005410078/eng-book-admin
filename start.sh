#!/bin/bash

# 英语学习管理后台 - 快速启动脚本

echo "🚀 启动英语学习管理后台..."
echo ""

# 检查 Python 版本
python_version=$(python --version 2>&1)
echo "✓ Python 版本: $python_version"

# 检查是否在虚拟环境中
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✓ 虚拟环境: $VIRTUAL_ENV"
else
    echo "⚠️  警告: 未检测到虚拟环境，建议使用虚拟环境"
fi

echo ""
echo "📦 检查依赖..."

# 检查关键依赖是否安装
if python -c "import fastapi" 2>/dev/null; then
    echo "✓ FastAPI 已安装"
else
    echo "✗ FastAPI 未安装"
    echo "正在安装依赖..."
    pip install fastapi uvicorn pydantic pydantic-settings python-multipart
fi

echo ""
echo "🌐 启动服务器..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 启动 uvicorn 服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
