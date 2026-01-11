-- 英语学习管理后台数据库初始化脚本
-- 创建时间: 2026-01-11

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建数据库（如果不存在）
-- 注意：这个脚本在容器启动时会自动执行

-- 输出初始化信息
DO $$
BEGIN
    RAISE NOTICE '数据库初始化完成';
    RAISE NOTICE '数据库名称: eng_learning_db';
    RAISE NOTICE '用户: eng_admin';
    RAISE NOTICE '时区: Asia/Shanghai';
END $$;
