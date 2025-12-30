#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为conversations表添加评价字段
数据库迁移脚本
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

def add_evaluation_field(trader_id='de'):
    """为conversations表添加评价字段"""
    db = TraderDBManager(trader_id)
    conn = db._get_connection()
    
    try:
        # 检查字段是否已存在
        columns = conn.execute("PRAGMA table_info(conversations)").fetchall()
        column_names = [col[1] for col in columns]
        
        if 'user_evaluation' not in column_names:
            print(f"为 {trader_id} 数据库添加 user_evaluation 字段...")
            conn.execute('''
                ALTER TABLE conversations 
                ADD COLUMN user_evaluation TEXT
            ''')
            conn.commit()
            print("✓ 字段添加成功")
        else:
            print(f"✓ {trader_id} 数据库已有 user_evaluation 字段")
        
        # 检查是否有evaluation_keywords字段（用于存储关键词）
        if 'evaluation_keywords' not in column_names:
            print(f"为 {trader_id} 数据库添加 evaluation_keywords 字段...")
            conn.execute('''
                ALTER TABLE conversations 
                ADD COLUMN evaluation_keywords TEXT
            ''')
            conn.commit()
            print("✓ 字段添加成功")
        else:
            print(f"✓ {trader_id} 数据库已有 evaluation_keywords 字段")
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='为conversations表添加评价字段')
    parser.add_argument('--trader', default='de', help='交易员ID（默认: de）')
    
    args = parser.parse_args()
    
    add_evaluation_field(args.trader)

