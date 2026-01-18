#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查电子书规则的质量和内容"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from db_manager_trader import TraderDBManager

def main():
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 获取有交易规则的记录
    items = conn.execute('''
        SELECT trading_rules_json, content_text
        FROM ebook_knowledge_base
        WHERE trading_rules_json IS NOT NULL AND trading_rules_json != ''
        LIMIT 10
    ''').fetchall()
    
    print("=" * 80)
    print("电子书交易规则质量分析")
    print("=" * 80)
    print(f"\n找到 {len(items)} 条有交易规则的记录\n")
    
    has_numbers = 0
    has_percentages = 0
    has_prices = 0
    
    for idx, (rules_json, content_text) in enumerate(items, 1):
        try:
            rules = json.loads(rules_json)
            print(f"规则 #{idx}:")
            print("-" * 80)
            
            # 检查是否包含数字
            rules_str = json.dumps(rules, ensure_ascii=False)
            if any(c.isdigit() for c in rules_str):
                has_numbers += 1
                print("✅ 包含数字")
            
            # 检查是否包含百分比
            if '%' in rules_str or 'percent' in rules_str.lower():
                has_percentages += 1
                print("✅ 包含百分比")
            
            # 检查是否包含价格（$符号）
            if '$' in rules_str:
                has_prices += 1
                print("✅ 包含价格")
            
            # 显示规则内容
            print("规则内容:")
            for rule_type, rule_list in rules.items():
                if rule_list:
                    print(f"  {rule_type}:")
                    for rule in rule_list[:2]:  # 最多显示2条
                        print(f"    - {rule[:150]}...")
            
            # 显示原始文本片段
            if content_text:
                print(f"\n原文片段: {content_text[:200]}...")
            
            print()
            
        except Exception as e:
            print(f"❌ 解析失败: {e}\n")
    
    print("=" * 80)
    print("统计结果")
    print("=" * 80)
    print(f"包含数字: {has_numbers}/{len(items)} ({has_numbers/len(items)*100:.1f}%)")
    print(f"包含百分比: {has_percentages}/{len(items)} ({has_percentages/len(items)*100:.1f}%)")
    print(f"包含价格: {has_prices}/{len(items)} ({has_prices/len(items)*100:.1f}%)")
    
    # 结论
    print("\n" + "=" * 80)
    print("结论")
    print("=" * 80)
    if has_numbers / len(items) > 0.3:
        print("⚠️  较多规则包含数字，建议使用NLP提取数值参数")
    else:
        print("✅ 规则主要是文本描述，当前NLP处理已足够")
    
    if has_percentages / len(items) > 0.2:
        print("⚠️  较多规则包含百分比，可以考虑使用NLP提取")
    else:
        print("✅ 规则较少包含百分比，主要是相对描述")
    
    db.close()

if __name__ == '__main__':
    main()



