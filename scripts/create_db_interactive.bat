@echo off
echo ========================================
echo PostgreSQL 数据库创建脚本
echo ========================================
echo.
echo 请按照提示输入 postgres 用户密码
echo.
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE qingniao_abu ENCODING 'UTF8';"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE USER abu_user WITH PASSWORD 'Abu2026!Secure';"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE qingniao_abu TO abu_user;"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "GRANT ALL ON SCHEMA public TO abu_user;"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user;"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user;"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO abu_user;"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO abu_user;"
echo.
echo ========================================
echo 数据库创建完成！
echo ========================================
pause
