#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查数据库中的重复记录
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

def check_duplicates():
    """检查重复记录"""
    print("=" * 80)
    print("检查数据库中的重复记录")
    print("=" * 80)
    print()
    
    try:
        db = TraderDBManager('de')
        conn = db._get_connection()
        
        # 检查总记录数
        total = conn.execute("SELECT COUNT(*) FROM trader_viewpoints").fetchone()[0]
        print(f"📊 总记录数: {total} 条")
        print()
        
        # 检查重复记录（基于内容和时间戳）
        duplicates = conn.execute('''
            SELECT content, timestamp, COUNT(*) as count
            FROM trader_viewpoints
            GROUP BY content, timestamp
            HAVING COUNT(*) > 1
        ''').fetchall()
        
        if duplicates:
            print(f"⚠️  发现 {len(duplicates)} 组重复记录:")
            total_duplicates = 0
            for dup in duplicates:
                count = dup[2]
                total_duplicates += (count - 1)
                print(f"\n  重复 {count} 次:")
                print(f"    时间: {dup[1]}")
                print(f"    内容: {dup[0][:80]}...")
            
            print(f"\n📊 需要删除的重复记录: {total_duplicates} 条")
            print(f"📊 保留后的记录数: {total - total_duplicates} 条")
        else:
            print("✅ 未发现重复记录")
        
        print()
        
        # 显示按时间排序的记录
        print("📅 按时间排序的记录（最近10条）:")
        recent = conn.execute('''
            SELECT id, timestamp, content, category
            FROM trader_viewpoints
            ORDER BY timestamp DESC
            LIMIT 10
        ''').fetchall()
        
        for r in recent:
            print(f"  [{r[3]}] {r[1]}: {r[2][:60]}...")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_duplicates()

