#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析对话类型：区分观点和交易记录
重新分类已记录的对话
"""

import json
from pathlib import Path
import sys
import re

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def is_trading_record(content):
    """判断是否为交易记录"""
    trading_keywords = [
        '止盈', '止损', '挂单', '扫单', '追单', '吃了', '吃了', '拿下',
        '空', '多', '做空', '做多', '进空', '进多',
        '点', '盈利', '亏损', '保本',
        '入场', '出场', '目标', '止损',
        '已经', '目前', '昨天', '今天',
        '交易', '执行', '成交'
    ]
    
    # 检查是否包含价格和交易动作
    has_price = bool(re.search(r'\d{3,4}', content))
    has_trading_action = any(kw in content for kw in trading_keywords)
    
    return has_price and has_trading_action

def is_trading_signal(content):
    """判断是否为交易信号"""
    signal_keywords = [
        '可以', '应该', '建议', '可以空', '可以多',
        '目标', '止损', '止盈',
        '看起来', '很好', '机会'
    ]
    
    has_signal_keyword = any(kw in content for kw in signal_keywords)
    has_price = bool(re.search(r'\d{3,4}', content))
    
    return has_signal_keyword and has_price

def is_viewpoint(content):
    """判断是否为观点"""
    viewpoint_keywords = [
        '理论', '逻辑', '道理', '意义', '概念',
        '认为', '觉得', '应该', '可能', '大概',
        '永远', '都是', '不是', '没有',
        '策略', '方法', '方式'
    ]
    
    # 排除交易记录和交易信号
    if is_trading_record(content) or is_trading_signal(content):
        return False
    
    return any(kw in content for kw in viewpoint_keywords)

def analyze_conversation_file(json_file):
    """分析对话文件，重新分类"""
    with open(json_file, 'r', encoding='utf-8') as f:
        records = json.load(f)
    
    updated_count = 0
    
    for record in records:
        content = record.get('content', '')
        original_category = record.get('category', '')
        
        # 重新分类
        new_category = original_category
        
        if is_trading_record(content):
            new_category = 'trading_execution'
        elif is_trading_signal(content):
            new_category = 'trading_signal'
        elif is_viewpoint(content):
            new_category = 'viewpoint'
        else:
            # 保持原分类或使用默认
            if not original_category:
                new_category = 'conversation'
        
        if new_category != original_category:
            record['category'] = new_category
            record['original_category'] = original_category  # 保留原分类
            updated_count += 1
    
    return records, updated_count

def main():
    """主函数"""
    print("=" * 80)
    print("分析对话类型：区分观点和交易记录")
    print("=" * 80)
    print()
    
    data_dir = Path("data")
    json_files = list(data_dir.glob("de_conversations_*.json"))
    
    print(f"找到 {len(json_files)} 个对话JSON文件")
    print()
    
    total_updated = 0
    
    for json_file in json_files:
        print(f"处理: {json_file.name}")
        
        try:
            records, updated = analyze_conversation_file(json_file)
            
            if updated > 0:
                # 保存更新后的文件
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(records, f, ensure_ascii=False, indent=2)
                print(f"  ✅ 更新 {updated} 条记录的分类")
                total_updated += updated
            else:
                print(f"  ℹ️  无需更新")
            
            # 显示分类统计
            categories = {}
            for r in records:
                cat = r.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"  分类统计: {categories}")
            print()
            
        except Exception as e:
            print(f"  ❌ 处理失败: {e}")
            print()
    
    print("=" * 80)
    print(f"分析完成！共更新 {total_updated} 条记录")
    print("=" * 80)
    
    print("\n分类说明:")
    print("  - trading_execution: 交易执行记录（已完成的交易）")
    print("  - trading_signal: 交易信号（建议或计划）")
    print("  - viewpoint: 观点和理论")
    print("  - conversation: 一般对话")

if __name__ == '__main__':
    main()


