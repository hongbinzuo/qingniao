#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的记录
"""

import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager

def check_records():
    """检查数据库记录"""
    print("=" * 80)
    print("检查数据库中的记录")
    print("=" * 80)
    print()
    
    try:
        db = TraderDBManager('de')
        conn = db._get_connection()
        
        # 检查表是否存在
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"📊 数据库表: {[t[0] for t in tables]}")
        print()
        
        # 检查trader_viewpoints表
        try:
            count = conn.execute("SELECT COUNT(*) FROM trader_viewpoints").fetchone()[0]
            print(f"✅ trader_viewpoints 表: {count} 条记录")
            
            if count > 0:
                # 显示最近的5条记录
                recent = conn.execute('''
                    SELECT id, timestamp, content, category
                    FROM trader_viewpoints
                    ORDER BY id DESC
                    LIMIT 5
                ''').fetchall()
                
                print("\n📝 最近的5条记录:")
                for r in recent:
                    print(f"  ID {r[0]}: [{r[2]}] {r[1]} - {r[3]}")
                    print(f"    内容: {r[1][:80]}...")
                    print()
        except Exception as e:
            print(f"❌ trader_viewpoints 表查询失败: {e}")
        
        # 检查conversation_logs表
        try:
            count = conn.execute("SELECT COUNT(*) FROM conversation_logs").fetchone()[0]
            print(f"✅ conversation_logs 表: {count} 条记录")
        except Exception as e:
            print(f"❌ conversation_logs 表查询失败: {e}")
        
        # 检查trade_records表
        try:
            count = conn.execute("SELECT COUNT(*) FROM trade_records").fetchone()[0]
            print(f"✅ trade_records 表: {count} 条记录")
        except Exception as e:
            print(f"❌ trade_records 表查询失败: {e}")
        
        db.close()
        
    except FileNotFoundError as e:
        print(f"❌ 数据库文件不存在: {e}")
        print("   需要先运行 database_design_v2.py 创建数据库")
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_records()

