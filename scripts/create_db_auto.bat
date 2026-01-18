@echo off
chcp 65001 >nul
echo ========================================
echo PostgreSQL 数据库自动创建
echo ========================================
echo.

set PGPASSWORD=woQunide008!

echo [1/7] 创建数据库 qingniao_abu...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE qingniao_abu ENCODING 'UTF8';" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    ✓ 数据库创建成功
) else (
    echo    ℹ️ 数据库可能已存在
)

echo [2/7] 创建用户 abu_user...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE USER abu_user WITH PASSWORD 'Abu2026!Secure';" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo    ✓ 用户创建成功
) else (
    echo    ℹ️ 用户可能已存在
)

echo [3/7] 授予数据库权限...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE qingniao_abu TO abu_user;"
echo    ✓ 数据库权限已授予

echo [4/7] 授予 schema 权限...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "GRANT ALL ON SCHEMA public TO abu_user;"
echo    ✓ Schema 权限已授予

echo [5/7] 授予表权限...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user;"
echo    ✓ 表权限已授予

echo [6/7] 授予序列权限...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user;"
echo    ✓ 序列权限已授予

echo [7/7] 设置默认权限...
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO abu_user;"
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d qingniao_abu -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO abu_user;"
echo    ✓ 默认权限已设置

echo.
echo ========================================
echo ✅ 数据库创建完成！
echo ========================================
set PGPASSWORD=
