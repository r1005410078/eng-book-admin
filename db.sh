#!/bin/bash

# 数据库管理脚本

case "$1" in
  start)
    echo "🚀 启动数据库服务..."
    docker compose up -d postgres redis
    echo "✅ 数据库服务已启动"
    ;;
    
  stop)
    echo "🛑 停止数据库服务..."
    docker compose stop postgres redis
    echo "✅ 数据库服务已停止"
    ;;
    
  restart)
    echo "🔄 重启数据库服务..."
    docker compose restart postgres redis
    echo "✅ 数据库服务已重启"
    ;;
    
  status)
    echo "📊 数据库服务状态:"
    docker compose ps postgres redis
    ;;
    
  logs)
    echo "📋 数据库日志:"
    docker compose logs -f postgres
    ;;
    
  psql)
    echo "🔌 连接到 PostgreSQL..."
    docker exec -it eng-book-postgres psql -U eng_admin -d eng_learning_db
    ;;
    
  redis-cli)
    echo "🔌 连接到 Redis..."
    docker exec -it eng-book-redis redis-cli
    ;;
    
  backup)
    echo "💾 备份数据库..."
    timestamp=$(date +%Y%m%d_%H%M%S)
    backup_file="backup/db_backup_${timestamp}.sql"
    mkdir -p backup
    docker exec eng-book-postgres pg_dump -U eng_admin eng_learning_db > "$backup_file"
    echo "✅ 备份完成: $backup_file"
    ;;
    
  restore)
    if [ -z "$2" ]; then
      echo "❌ 请指定备份文件: ./db.sh restore backup/db_backup_xxx.sql"
      exit 1
    fi
    echo "📥 恢复数据库: $2"
    docker exec -i eng-book-postgres psql -U eng_admin eng_learning_db < "$2"
    echo "✅ 恢复完成"
    ;;
    
  clean)
    echo "🧹 清理数据库数据..."
    read -p "确定要删除所有数据吗？(yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
      docker compose down -v
      echo "✅ 数据已清理"
    else
      echo "❌ 取消操作"
    fi
    ;;
    
  *)
    echo "数据库管理脚本"
    echo ""
    echo "用法: ./db.sh [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动数据库服务"
    echo "  stop        停止数据库服务"
    echo "  restart     重启数据库服务"
    echo "  status      查看服务状态"
    echo "  logs        查看数据库日志"
    echo "  psql        连接到 PostgreSQL"
    echo "  redis-cli   连接到 Redis"
    echo "  backup      备份数据库"
    echo "  restore     恢复数据库 (需要指定备份文件)"
    echo "  clean       清理所有数据（危险操作）"
    echo ""
    echo "示例:"
    echo "  ./db.sh start"
    echo "  ./db.sh psql"
    echo "  ./db.sh backup"
    echo "  ./db.sh restore backup/db_backup_20260111.sql"
    ;;
esac
