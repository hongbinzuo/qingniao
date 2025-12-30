#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按日期显示所有记录
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

def show_all_by_date():
    """按日期显示所有记录"""
    print("=" * 80)
    print("按日期显示所有记录")
    print("=" * 80)
    print()
    
    try:
        db = TraderDBManager('de')
        conn = db._get_connection()
        
        # 获取所有记录，按时间排序
        all_records = conn.execute('''
            SELECT timestamp, content, category
            FROM trader_viewpoints
            ORDER BY timestamp DESC
        ''').fetchall()
        
        print(f"💾 总记录数: {len(all_records)} 条")
        print()
        
        if all_records:
            latest = all_records[0]
            print(f"📅 最新记录时间: {latest[0]}")
            print(f"   内容: {latest[1][:80]}...")
            print()
            
            # 按日期分组
            print("📊 按日期统计:")
            date_groups = {}
            for r in all_records:
                if r[0]:
                    date = r[0][:10]
                    if date not in date_groups:
                        date_groups[date] = []
                    date_groups[date].append(r)
            
            for date in sorted(date_groups.keys(), reverse=True):
                records = date_groups[date]
                print(f"\n  📅 {date}: {len(records)} 条记录")
                for i, r in enumerate(records[:5], 1):  # 只显示前5条
                    print(f"    {i}. [{r[2]}] {r[0][11:16]}: {r[1][:50]}...")
                if len(records) > 5:
                    print(f"    ... 还有 {len(records) - 5} 条")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    show_all_by_date()

