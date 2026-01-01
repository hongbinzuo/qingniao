#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查待处理的任务和对话
"""

import sys
from pathlib import Path
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def check_pending_conversations():
    """检查待处理的对话"""
    print("=" * 80)
    print("检查待处理的对话和任务")
    print("=" * 80)
    print()
    
    data_dir = Path("data")
    
    # 检查JSON文件
    json_files = list(data_dir.glob("de_conversations_*.json"))
    print(f"📁 JSON对话文件: {len(json_files)} 个")
    
    # 检查是否有未迁移的文件
    print("\n📋 所有对话文件:")
    for f in sorted(json_files):
        print(f"  - {f.name}")
    
    # 检查数据库记录
    try:
        from db_manager_trader import TraderDBManager
        db = TraderDBManager('de')
        conn = db._get_connection()
        
        count = conn.execute("SELECT COUNT(*) FROM trader_viewpoints").fetchone()[0]
        print(f"\n💾 数据库记录: {count} 条")
        
        # 检查最近的记录
        recent = conn.execute('''
            SELECT timestamp, content, category
            FROM trader_viewpoints
            ORDER BY id DESC
            LIMIT 5
        ''').fetchall()
        
        print("\n📝 最近的5条记录:")
        for r in recent:
            print(f"  [{r[2]}] {r[0]}: {r[1][:60]}...")
        
        db.close()
    except Exception as e:
        print(f"\n❌ 数据库检查失败: {e}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_pending_conversations()

