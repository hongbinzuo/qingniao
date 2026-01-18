#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用提供的密码创建 PostgreSQL 数据库
"""

import subprocess
import sys

POSTGRES_PASSWORD = "woQunide008!"
PSQL_PATH = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"

def run_sql(sql_command, dbname='postgres'):
    """执行 SQL 命令"""
    env = {'PGPASSWORD': POSTGRES_PASSWORD}
    # 使用 -h 127.0.0.1 代替 localhost
    cmd = [PSQL_PATH, '-U', 'postgres', '-h', '127.0.0.1', '-d', dbname, '-c', sql_command]
    
    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, '', str(e)

def main():
    import sys
    import io
    # 设置标准输出为 UTF-8
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("PostgreSQL 数据库自动创建")
    print("=" * 60)
    print()
    
    # Step 1: 创建数据库
    print("[1/7] 创建数据库 qingniao_abu...")
    success, stdout, stderr = run_sql("CREATE DATABASE qingniao_abu ENCODING 'UTF8';")
    if success or 'already exists' in stderr:
        print("   [OK] 数据库创建成功（或已存在）")
    else:
        print(f"   [ERROR] 失败: {stderr}")
    
    # Step 2: 创建用户
    print("[2/7] 创建用户 abu_user...")
    success, stdout, stderr = run_sql("CREATE USER abu_user WITH PASSWORD 'Abu2026!Secure';")
    if success or 'already exists' in stderr:
        print("   [OK] 用户创建成功（或已存在）")
    else:
        print(f"   [ERROR] 失败: {stderr}")
    
    # Step 3: 授予数据库权限
    print("[3/7] 授予数据库权限...")
    success, stdout, stderr = run_sql("GRANT ALL PRIVILEGES ON DATABASE qingniao_abu TO abu_user;")
    if success:
        print("   [OK] 数据库权限已授予")
    else:
        print(f"   [ERROR] 失败: {stderr}")
    
    # Step 4: 授予 schema 权限
    print("[4/7] 授予 schema 权限...")
    success, stdout, stderr = run_sql("GRANT ALL ON SCHEMA public TO abu_user;", 'qingniao_abu')
    if success:
        print("   [OK] Schema 权限已授予")
    else:
        print(f"   [ERROR] 失败: {stderr}")
    
    # Step 5: 授予表权限
    print("[5/7] 授予表权限...")
    success, stdout, stderr = run_sql(
        "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user;",
        'qingniao_abu'
    )
    if success:
        print("   [OK] 表权限已授予")
    else:
        print(f"   [ERROR] 失败: {stderr}")
    
    # Step 6: 授予序列权限
    print("[6/7] 授予序列权限...")
    success, stdout, stderr = run_sql(
        "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user;",
        'qingniao_abu'
    )
    if success:
        print("   [OK] 序列权限已授予")
    else:
        print(f"   [ERROR] 失败: {stderr}")
    
    # Step 7: 设置默认权限
    print("[7/7] 设置默认权限...")
    success1, _, _ = run_sql(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO abu_user;",
        'qingniao_abu'
    )
    success2, _, _ = run_sql(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO abu_user;",
        'qingniao_abu'
    )
    if success1 and success2:
        print("   [OK] 默认权限已设置")
    else:
        print("   [ERROR] 部分权限设置失败")
    
    print()
    print("=" * 60)
    print("[SUCCESS] 数据库创建完成！")
    print("=" * 60)
    print()
    print("数据库信息:")
    print("  数据库: qingniao_abu")
    print("  用户: abu_user")
    print("  密码: Abu2026!Secure")

if __name__ == '__main__':
    main()
