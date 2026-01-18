-- 创建 Abu 数据库和用户
-- 以 postgres 超级用户身份执行

-- 创建数据库
CREATE DATABASE qingniao_abu ENCODING 'UTF8';

-- 创建用户
CREATE USER abu_user WITH PASSWORD 'Abu2026!Secure';

-- 授权数据库
GRANT ALL PRIVILEGES ON DATABASE qingniao_abu TO abu_user;

-- 连接到新数据库并授权 schema
\c qingniao_abu

-- 授权 public schema
GRANT ALL ON SCHEMA public TO abu_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user;

-- 默认权限（未来创建的对象）
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO abu_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO abu_user;

-- 显示结果
\l qingniao_abu
\du abu_user
