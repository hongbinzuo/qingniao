#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重新分类数据库中的记录
根据改进的分类规则更新数据库中的分类
"""

import sys
import re
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

def classify_content(content):
    """分类内容"""
    content_lower = content.lower()
    
    # 交易执行记录特征
    execution_keywords = [
        '已经', '目前', '昨天', '今天', '刚才',
        '止盈了', '止损了', '吃了', '拿下', '成交了',
        '扫了', '追单', '挂单', '执行',
        '盈利', '亏损', '赚了', '亏了',
        '点', '已经.*点', '目前.*点'
    ]
    
    # 交易信号特征
    signal_keywords = [
        '可以', '应该', '建议', '可以空', '可以多',
        '看起来', '很好', '机会', '可以进',
        '目标', '止损', '止盈', '挂',
        '如果.*可以', '如果.*应该'
    ]
    
    # 观点特征
    viewpoint_keywords = [
        '理论', '逻辑', '道理', '意义', '概念',
        '认为', '觉得', '应该', '可能', '大概',
        '永远', '都是', '不是', '没有',
        '策略', '方法', '方式', '理念',
        '因为', '所以', '但是', '如果',
        '组织', '庄家', '巨鲸', '市场'
    ]
    
    execution_score = sum(1 for kw in execution_keywords if re.search(kw, content))
    signal_score = sum(1 for kw in signal_keywords if re.search(kw, content))
    viewpoint_score = sum(1 for kw in viewpoint_keywords if re.search(kw, content))
    
    has_price_and_action = bool(re.search(r'\d{3,4}', content)) and (
        '止盈' in content or '止损' in content or '空' in content or '多' in content or
        '吃了' in content or '拿下' in content or '点' in content
    )
    
    if execution_score >= 2 or (has_price_and_action and execution_score >= 1):
        return 'trading_execution'
    elif signal_score >= 2 or (has_price_and_action and signal_score >= 1):
        return 'trading_signal'
    elif viewpoint_score >= 2:
        return 'viewpoint'
    elif has_price_and_action:
        return 'trading_signal'
    else:
        return 'conversation'

def reclassify_records():
    """重新分类数据库中的记录"""
    print("=" * 80)
    print("重新分类数据库中的记录")
    print("=" * 80)
    print()
    
    db = TraderDBManager('de')
    conn = db._get_connection()
    
    # 获取所有记录
    cursor = conn.execute('''
        SELECT id, content, category
        FROM trader_viewpoints
    ''')
    
    records = cursor.fetchall()
    print(f"找到 {len(records)} 条记录")
    print()
    
    updated_count = 0
    
    for record in records:
        record_id, content, old_category = record
        
        # 提取原始内容（去掉添加的元数据）
        original_content = content
        if '[BTC价格:' in content:
            original_content = content.split(']', 1)[1].strip()
        if '[上下文:' in original_content:
            original_content = original_content.split(']', 1)[1].strip()
        if '[解析价格:' in original_content:
            original_content = original_content.split('\n')[0]
        if '[概念:' in original_content:
            original_content = original_content.split('\n')[0]
        
        # 重新分类
        new_category = classify_content(original_content)
        
        if new_category != old_category:
            # 更新数据库
            conn.execute('''
                UPDATE trader_viewpoints
                SET category = ?
                WHERE id = ?
            ''', (new_category, record_id))
            
            updated_count += 1
            if updated_count <= 10:  # 只显示前10个更新
                print(f"  ID {record_id}: {old_category} -> {new_category}")
                print(f"    内容: {original_content[:60]}...")
    
    conn.commit()
    
    print()
    print("=" * 80)
    print(f"重新分类完成！更新了 {updated_count} 条记录")
    print("=" * 80)
    
    # 显示新的分类统计
    cursor = conn.execute('''
        SELECT category, COUNT(*) as count
        FROM trader_viewpoints
        GROUP BY category
    ''')
    
    print("\n📊 新的分类统计:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} 条")
    
    db.close()

if __name__ == '__main__':
    reclassify_records()


