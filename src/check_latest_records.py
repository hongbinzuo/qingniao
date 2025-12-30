#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查最新的记录，看看是否有遗漏
"""

import sys
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager

def check_latest_records():
    """检查最新记录"""
    print("=" * 80)
    print("检查最新的对话记录")
    print("=" * 80)
    print()
    
    # 检查JSON文件
    data_dir = Path("data")
    json_files = sorted(data_dir.glob("de_conversations_*.json"))
    
    print("📁 JSON文件检查:")
    print(f"  文件总数: {len(json_files)}")
    if json_files:
        latest_file = json_files[-1]
        print(f"  最新文件: {latest_file.name}")
        
        # 读取最新文件，查看最新时间
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                records = json.load(f)
            if records:
                latest_record = max(records, key=lambda x: x.get('timestamp', ''))
                print(f"  最新记录时间: {latest_record.get('timestamp', 'N/A')}")
        except Exception as e:
            print(f"  读取失败: {e}")
    
    print()
    
    # 检查数据库记录
    try:
        db = TraderDBManager('de')
        conn = db._get_connection()
        
        # 获取所有记录，按时间排序
        all_records = conn.execute('''
            SELECT timestamp, content, category
            FROM trader_viewpoints
            ORDER BY timestamp DESC
        ''').fetchall()
        
        print(f"💾 数据库记录总数: {len(all_records)} 条")
        print()
        
        if all_records:
            latest_db_record = all_records[0]
            print(f"📅 数据库最新记录:")
            print(f"  时间: {latest_db_record[0]}")
            print(f"  分类: {latest_db_record[2]}")
            print(f"  内容: {latest_db_record[1][:100]}...")
            print()
            
            # 显示26日之后的记录
            print("📅 2025/12/26 之后的记录:")
            records_after_26 = [r for r in all_records if r[0] and r[0] >= '2025-12-26']
            print(f"  找到 {len(records_after_26)} 条记录")
            
            if records_after_26:
                print("\n  详细列表:")
                for i, r in enumerate(records_after_26[:20], 1):  # 只显示前20条
                    print(f"    {i}. [{r[2]}] {r[0]}: {r[1][:60]}...")
                if len(records_after_26) > 20:
                    print(f"    ... 还有 {len(records_after_26) - 20} 条")
            else:
                print("  ⚠️  没有找到26日之后的记录！")
            
            # 按日期分组统计
            print("\n📊 按日期统计:")
            date_counts = {}
            for r in all_records:
                if r[0]:
                    date = r[0][:10]  # 提取日期部分
                    date_counts[date] = date_counts.get(date, 0) + 1
            
            for date in sorted(date_counts.keys(), reverse=True):
                print(f"  {date}: {date_counts[date]} 条")
        
        db.close()
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    import json
    check_latest_records()

