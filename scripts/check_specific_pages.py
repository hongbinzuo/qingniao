#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Page 208和Page 180的详细内容
"""
from __future__ import annotations
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

db = TraderDBManager('abu')
conn = db._get_connection()

print("=" * 80)
print("检查Page 208和Page 180的详细内容")
print("=" * 80)
print()

# 检查Page 208
print("Page 208: 前18根K线范围突破")
print("-" * 80)
query = '''
    SELECT id, pattern_name, source_page, gemini_annotation_json
    FROM pattern_library
    WHERE source_page = 208
      AND gemini_annotation_json IS NOT NULL
    LIMIT 1
'''
result = conn.execute(query).fetchone()
if result:
    print(f"ID: {result[0]}")
    print(f"Name: {result[1]}")
    print(f"Page: {result[2]}")
    print()
    try:
        ann = json.loads(result[3])
        ann_str = json.dumps(ann, ensure_ascii=False, indent=2)
        
        # 检查关键概念
        keywords_208 = ['18', 'first 18', 'initial range', 'opening range', 'first bars', 'breakout', 'BO']
        found_keywords = []
        ann_lower = ann_str.lower()
        for kw in keywords_208:
            if kw.lower() in ann_lower:
                found_keywords.append(kw)
        
        if found_keywords:
            print(f"✓ 找到相关关键词: {', '.join(found_keywords)}")
        else:
            print("✗ 未找到'前18根K线'相关关键词")
        
        print()
        print("Gemini标注摘要:")
        # 提取关键信息
        if isinstance(ann, dict):
            # 检查patterns
            if 'patterns' in ann:
                print(f"  模式数量: {len(ann['patterns'])}")
                for p in ann['patterns'][:3]:
                    if isinstance(p, dict):
                        print(f"    - {p.get('name', 'N/A')}: {p.get('type', 'N/A')}")
            
            # 检查price_action_behavior
            if 'price_action_behavior' in ann:
                pab = ann['price_action_behavior']
                if isinstance(pab, dict):
                    print(f"  趋势: {pab.get('trend', 'N/A')}")
                    if 'kline_features' in pab:
                        print(f"  K线特征: {pab['kline_features'][:5]}")
            
            # 检查trading_signals
            if 'trading_signals' in ann:
                print(f"  交易信号数量: {len(ann['trading_signals'])}")
        
        # 显示部分JSON内容（前500字符）
        print()
        print("JSON内容预览（前500字符）:")
        print(ann_str[:500])
        if len(ann_str) > 500:
            print("...")
            
    except Exception as e:
        print(f"解析JSON失败: {e}")
else:
    print("✗ Page 208 没有Gemini标注")

print()
print()

# 检查Page 180
print("Page 180: 日内反转/End of Day Reversal")
print("-" * 80)
query = '''
    SELECT id, pattern_name, source_page, gemini_annotation_json
    FROM pattern_library
    WHERE source_page = 180
      AND gemini_annotation_json IS NOT NULL
    LIMIT 1
'''
result = conn.execute(query).fetchone()
if result:
    print(f"ID: {result[0]}")
    print(f"Name: {result[1]}")
    print(f"Page: {result[2]}")
    print()
    try:
        ann = json.loads(result[3])
        ann_str = json.dumps(ann, ensure_ascii=False, indent=2)
        
        # 检查关键概念
        keywords_180 = ['reversal', 'end of day', 'profit taking', 'exhaustive', 'sell climax', 
                        'failed breakout', 'wedge', 'climax']
        found_keywords = []
        ann_lower = ann_str.lower()
        for kw in keywords_180:
            if kw.lower() in ann_lower:
                found_keywords.append(kw)
        
        if found_keywords:
            print(f"✓ 找到相关关键词: {', '.join(found_keywords)}")
        else:
            print("✗ 未找到'日内反转'相关关键词")
        
        print()
        print("Gemini标注摘要:")
        # 提取关键信息
        if isinstance(ann, dict):
            # 检查patterns
            if 'patterns' in ann:
                print(f"  模式数量: {len(ann['patterns'])}")
                for p in ann['patterns'][:3]:
                    if isinstance(p, dict):
                        print(f"    - {p.get('name', 'N/A')}: {p.get('type', 'N/A')}")
            
            # 检查price_action_behavior
            if 'price_action_behavior' in ann:
                pab = ann['price_action_behavior']
                if isinstance(pab, dict):
                    print(f"  趋势: {pab.get('trend', 'N/A')}")
                    if 'kline_features' in pab:
                        print(f"  K线特征: {pab['kline_features'][:5]}")
            
            # 检查trading_signals
            if 'trading_signals' in ann:
                print(f"  交易信号数量: {len(ann['trading_signals'])}")
        
        # 显示部分JSON内容（前500字符）
        print()
        print("JSON内容预览（前500字符）:")
        print(ann_str[:500])
        if len(ann_str) > 500:
            print("...")
            
    except Exception as e:
        print(f"解析JSON失败: {e}")
else:
    print("✗ Page 180 没有Gemini标注")

print()
print("=" * 80)
print("检查完成")
print("=" * 80)

db.close()



