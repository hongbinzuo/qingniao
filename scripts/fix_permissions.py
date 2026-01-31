#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 PostgreSQL 权限问题
"""

import psycopg2
import sys

# 使用 postgres 超级用户来授权
POSTGRES_PASSWORD = "woQunide008!"

def main():
    print("=" * 60)
    print("PostgreSQL 权限修复")
    print("=" * 60)
    print()
    
    try:
        # 连接到 qingniao_abu 数据库（使用 postgres 超级用户）
        print("[1/4] 连接到 qingniao_abu 数据库...")
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            database='qingniao_abu',
            user='postgres',
            password=POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        print("   [OK] 连接成功")
        
        # 授予 public schema 的所有权限
        print("[2/4] 授予 abu_user 对 public schema 的权限...")
        cursor.execute("GRANT ALL ON SCHEMA public TO abu_user;")
        cursor.execute("GRANT CREATE ON SCHEMA public TO abu_user;")
        cursor.execute("GRANT USAGE ON SCHEMA public TO abu_user;")
        conn.commit()
        print("   [OK] Schema 权限已授予")
        
        # 授予表和序列的权限
        print("[3/4] 授予表和序列权限...")
        cursor.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO abu_user;")
        cursor.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO abu_user;")
        conn.commit()
        print("   [OK] 表和序列权限已授予")
        
        # 设置默认权限
        print("[4/4] 设置默认权限...")
        cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO abu_user;")
        cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO abu_user;")
        cursor.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO abu_user;")
        
        # 修改 public schema 的所有者为 abu_user（可选，但推荐）
        cursor.execute("ALTER SCHEMA public OWNER TO abu_user;")
        conn.commit()
        print("   [OK] 默认权限已设置，public schema 所有者已修改")
        
        cursor.close()
        conn.close()
        
        print()
        print("=" * 60)
        print("[SUCCESS] 权限修复完成！")
        print("=" * 60)
        print()
        print("现在可以运行:")
        print("  python scripts\\abu\\init_postgres_abu_db.py")
        
    except Exception as e:
        print(f"\n[ERROR] 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
