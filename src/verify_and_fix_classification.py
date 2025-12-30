#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证并修复数据库中的分类
确保观点和交易记录被正确区分
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

def verify_classification():
    """验证数据库中的分类"""
    print("=" * 80)
    print("验证数据库中的分类")
    print("=" * 80)
    print()
    
    db = TraderDBManager('de')
    
    # 查询所有记录
    conn = db._get_connection()
    
    # 统计各分类数量
    categories = {}
    cursor = conn.execute('''
        SELECT category, COUNT(*) as count
        FROM trader_viewpoints
        GROUP BY category
    ''')
    
    for row in cursor.fetchall():
        categories[row[0]] = row[1]
    
    print("📊 当前分类统计:")
    for cat, count in categories.items():
        print(f"  {cat}: {count} 条")
    print()
    
    # 检查可能分类错误的记录
    print("🔍 检查可能分类错误的记录:")
    print()
    
    # 查找包含交易关键词但分类不是trading_execution或trading_signal的记录
    cursor = conn.execute('''
        SELECT id, content, category, tags
        FROM trader_viewpoints
        WHERE (
            content LIKE '%止盈%' OR
            content LIKE '%止损%' OR
            content LIKE '%挂单%' OR
            content LIKE '%吃了%' OR
            content LIKE '%拿下%' OR
            content LIKE '%已经%点%' OR
            content LIKE '%目前%点%'
        )
        AND category NOT IN ('trading_execution', 'trading_signal')
        LIMIT 20
    ''')
    
    suspicious_records = cursor.fetchall()
    
    if suspicious_records:
        print(f"  发现 {len(suspicious_records)} 条可能分类错误的记录:")
        for record in suspicious_records:
            print(f"    ID {record[0]}: {record[2]} - {record[1][:50]}...")
    else:
        print("  ✅ 未发现明显分类错误")
    
    print()
    
    # 查找包含理论关键词但分类不是viewpoint的记录
    cursor = conn.execute('''
        SELECT id, content, category, tags
        FROM trader_viewpoints
        WHERE (
            content LIKE '%理论%' OR
            content LIKE '%逻辑%' OR
            content LIKE '%概念%' OR
            content LIKE '%策略%' OR
            content LIKE '%道理%'
        )
        AND category != 'viewpoint'
        LIMIT 20
    ''')
    
    viewpoint_records = cursor.fetchall()
    
    if viewpoint_records:
        print(f"  发现 {len(viewpoint_records)} 条可能应该是观点的记录:")
        for record in viewpoint_records:
            print(f"    ID {record[0]}: {record[2]} - {record[1][:50]}...")
    else:
        print("  ✅ 观点分类正确")
    
    print()
    
    # 显示一些示例记录
    print("📝 示例记录（按分类）:")
    print()
    
    for cat in ['trading_execution', 'trading_signal', 'viewpoint', 'conversation']:
        cursor = conn.execute('''
            SELECT content, category, tags
            FROM trader_viewpoints
            WHERE category = ?
            LIMIT 3
        ''', (cat,))
        
        records = cursor.fetchall()
        if records:
            print(f"  {cat}:")
            for r in records:
                print(f"    - {r[0][:60]}...")
            print()

if __name__ == '__main__':
    verify_classification()

