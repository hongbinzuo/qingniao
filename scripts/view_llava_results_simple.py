#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单查看 llava 分类结果
"""

import json
from pathlib import Path
from collections import Counter

# 读取 patterns.json
patterns_file = Path('data/abu/patterns.json')
if not patterns_file.exists():
    print(f"文件不存在: {patterns_file}")
    exit(1)

with open(patterns_file, 'r', encoding='utf-8') as f:
    patterns = json.load(f)

print(f"\n{'='*80}")
print(f"Patterns.json 统计")
print(f"{'='*80}")
print(f"总记录数: {len(patterns)}")

# 统计 pattern_type
pattern_types = Counter(p.get('pattern_type', 'unknown') for p in patterns)
print(f"\n模式类型分布:")
for ptype, count in sorted(pattern_types.items(), key=lambda x: -x[1]):
    print(f"  {ptype}: {count}")

# 查找有分类信息的记录
classified = []
for p in patterns:
    ptype = p.get('pattern_type', '')
    if ptype and ptype != 'other':
        classified.append(p)
    elif p.get('timeframe_hint') or p.get('direction') or p.get('key_features'):
        classified.append(p)

print(f"\n已分类记录数: {len(classified)}")
if classified:
    print(f"\n前5条已分类记录:")
    for i, p in enumerate(classified[:5], 1):
        print(f"\n{i}. ID={p.get('id')}, 类型={p.get('pattern_type')}, 页面={p.get('source_page')}")
        if p.get('timeframe_hint'):
            print(f"   时间周期: {p.get('timeframe_hint')}")
        if p.get('direction'):
            print(f"   方向: {p.get('direction')}")
        if p.get('key_features'):
            print(f"   特征: {p.get('key_features')[:100]}...")

# 检查是否有 llava 相关的输出文件
print(f"\n{'='*80}")
print(f"查找输出文件")
print(f"{'='*80}")

for dir_path in [Path('outputs'), Path('data/abu')]:
    if dir_path.exists():
        for f in dir_path.rglob('*llava*'):
            if f.is_file():
                print(f"找到: {f}")
                print(f"  大小: {f.stat().st_size} bytes")
                if f.suffix == '.jsonl':
                    try:
                        with open(f, 'r', encoding='utf-8') as file:
                            lines = file.readlines()
                            print(f"  行数: {len(lines)}")
                            if lines:
                                sample = json.loads(lines[0])
                                print(f"  示例: {json.dumps(sample, ensure_ascii=False)[:200]}...")
                    except:
                        pass



