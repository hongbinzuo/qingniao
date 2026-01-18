#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查Gemini是否识别到了特定模式
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

print("=" * 80)
print("检查Gemini是否识别到特定模式")
print("=" * 80)
print()

db = TraderDBManager('abu')
conn = db._get_connection()

# 1. 检查"前18根K线"相关模式
print("1. 检查'前18根K线范围突破'相关模式...")
keywords_18_bars = ['18', 'first 18', 'initial range', 'opening range', 'first bars']
results_18 = []
for keyword in keywords_18_bars:
    query = '''
        SELECT id, pattern_name, source_page, gemini_annotation_json
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL
          AND (pattern_name LIKE ? OR gemini_annotation_json LIKE ?)
        LIMIT 10
    '''
    rows = conn.execute(query, (f'%{keyword}%', f'%{keyword}%')).fetchall()
    for row in rows:
        if row not in results_18:
            results_18.append(row)

print(f"   找到 {len(results_18)} 个相关模式")
if results_18:
    for r in results_18[:5]:
        print(f"   - ID: {r[0]}, Name: {r[1]}, Page: {r[2]}")
        # 检查JSON内容
        try:
            ann = json.loads(r[3])
            if '18' in str(ann).lower() or 'first' in str(ann).lower():
                print(f"     ✓ 包含相关概念")
        except:
            pass
else:
    print("   ✗ 未找到相关模式")

print()

# 2. 检查"日内反转"相关模式
print("2. 检查'日内反转/End of Day Reversal'相关模式...")
keywords_reversal = ['reversal', 'end of day', 'profit taking', 'exhaustive', 'sell climax', 'failed breakout']
results_reversal = []
for keyword in keywords_reversal:
    query = '''
        SELECT id, pattern_name, source_page, gemini_annotation_json
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL
          AND (pattern_name LIKE ? OR gemini_annotation_json LIKE ?)
        LIMIT 10
    '''
    rows = conn.execute(query, (f'%{keyword}%', f'%{keyword}%')).fetchall()
    for row in rows:
        if row not in results_reversal:
            results_reversal.append(row)

print(f"   找到 {len(results_reversal)} 个相关模式")
if results_reversal:
    for r in results_reversal[:5]:
        print(f"   - ID: {r[0]}, Name: {r[1]}, Page: {r[2]}")
        # 检查JSON内容
        try:
            ann = json.loads(r[3])
            ann_str = str(ann).lower()
            if any(kw in ann_str for kw in ['reversal', 'exhaustive', 'climax', 'failed breakout']):
                print(f"     ✓ 包含相关概念")
        except:
            pass
else:
    print("   ✗ 未找到相关模式")

print()

# 3. 检查Page 208和Page 180（这两张图对应的页面）
print("3. 检查Page 208和Page 180...")
for page in [208, 180]:
    query = '''
        SELECT id, pattern_name, source_page, gemini_annotation_json
        FROM pattern_library
        WHERE source_page = ?
          AND gemini_annotation_json IS NOT NULL
        LIMIT 5
    '''
    results = conn.execute(query, (page,)).fetchall()
    print(f"   Page {page}: {len(results)} 个模式")
    if results:
        for r in results:
            print(f"     - ID: {r[0]}, Name: {r[1]}")
            # 尝试解析JSON查看内容
            try:
                ann = json.loads(r[3])
                # 检查是否包含关键概念
                ann_str = json.dumps(ann, ensure_ascii=False).lower()
                if page == 208:
                    if '18' in ann_str or 'first' in ann_str or 'initial' in ann_str:
                        print(f"       ✓ 可能包含'前18根K线'概念")
                elif page == 180:
                    if any(kw in ann_str for kw in ['reversal', 'exhaustive', 'climax', 'profit taking']):
                        print(f"       ✓ 可能包含'日内反转'概念")
            except:
                pass
    else:
        print(f"     ✗ Page {page} 没有Gemini标注")

print()

# 4. 检查"楔形"和"失败突破"相关模式
print("4. 检查'楔形/Wedge'和'失败突破/Failed Breakout'相关模式...")
keywords_wedge = ['wedge', 'failed breakout', 'breakout below', 'breakout above']
results_wedge = []
for keyword in keywords_wedge:
    query = '''
        SELECT id, pattern_name, source_page, gemini_annotation_json
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL
          AND (pattern_name LIKE ? OR gemini_annotation_json LIKE ?)
        LIMIT 10
    '''
    rows = conn.execute(query, (f'%{keyword}%', f'%{keyword}%')).fetchall()
    for row in rows:
        if row not in results_wedge:
            results_wedge.append(row)

print(f"   找到 {len(results_wedge)} 个相关模式")
if results_wedge:
    for r in results_wedge[:5]:
        print(f"   - ID: {r[0]}, Name: {r[1]}, Page: {r[2]}")

print()
print("=" * 80)
print("检查完成")
print("=" * 80)

db.close()

