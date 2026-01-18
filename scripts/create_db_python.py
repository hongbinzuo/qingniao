#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 psycopg2 直接创建数据库
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sys

POSTGRES_PASSWORD = "woQunide008!"

def main():
    print("=" * 60)
    print("PostgreSQL 数据库创建 (使用 psycopg2)")
    print("=" * 60)
    print()
    
    try:
        # 连接到 postgres 数据库
        print("[1/8] 连接到 PostgreSQL...")
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='postgres',
            user='postgres',
            password=POSTGRES_PASSWORD
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        print("   [OK] 连接成功")
        
        # 创建数据库
        print("[2/8] 创建数据库 qingniao_abu...")
        try:
            cursor.execute("CREATE DATABASE qingniao_abu ENCODING 'UTF8'")
            print("   [OK] 数据库创建成功")
        except psycopg2.errors.DuplicateDatabase:
            print("   [OK] 数据库已存在")
        
        # 创建用户
        print("[3/8] 创建用户 abu_user...")
        try:
            cursor.execute("CREATE USER abu_user WITH PASSWORD 'Abu2026!Secure'")
            print("   [OK] 用户创建成功")
        except psycopg2.errors.DuplicateObject:
            print("   [OK] 用户已存在")
        
        # 授予数据库权限
        print("[4/8] 授予数据库权限...")
        cursor.execute("GRANT ALL PRIVILEGES ON DATABASE qingniao_abu TO abu_user")
        print("   [OK] 数据库权限已授予")
        
        cursor.close()
        conn.close()
        
        # 连接到新数据库
        print("[5/8] 连接到 qingniao_abu 数据库...")
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='qingniao_abu',
            user='postgres',
            password=POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        print("   [OK] 连接成功")
        
        # 授予 schema 权限
        print("[6/8] 授予 schema 权限...")
        cursor.execute("GRANT ALL ON SCHEMA public TO abu_user")
        cursor.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user")
        cursor.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user")
        conn.commit()
        print("   [OK] Schema 权限已授予")
        
        # 设置默认权限
        print("[7/8] 设置默认权限...")
        cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO abu_user")
        cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO abu_user")
        conn.commit()
        print("   [OK] 默认权限已设置")
        
        # 测试 abu_user 连接
        print("[8/8] 测试 abu_user 连接...")
        cursor.close()
        conn.close()
        
        test_conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='qingniao_abu',
            user='abu_user',
            password='Abu2026!Secure'
        )
        test_conn.close()
        print("   [OK] abu_user 连接测试成功")
        
        print()
        print("=" * 60)
        print("[SUCCESS] 数据库创建完成！")
        print("=" * 60)
        print()
        print("数据库信息:")
        print("  主机: 127.0.0.1")
        print("  端口: 5432")
        print("  数据库: qingniao_abu")
        print("  用户: abu_user")
        print("  密码: Abu2026!Secure")
        
    except Exception as e:
        print(f"\n[ERROR] 创建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
