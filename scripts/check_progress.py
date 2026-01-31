#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查处理进度"""

import sys
from pathlib import Path
import json

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

ROOT = Path(__file__).resolve().parent.parent
output_file = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'
state_file = ROOT / 'outputs' / 'abu_gemini_analysis_state.json'

print("=" * 60)
print("处理进度检查")
print("=" * 60)
print()

# 检查输出文件
if output_file.exists() and output_file.stat().st_size > 0:
    with output_file.open('r', encoding='utf-8') as f:
        lines = sum(1 for line in f if line.strip())
    print(f"输出文件行数: {lines}/1000 ({lines/10:.1f}%)")
else:
    print("输出文件不存在或为空")
    lines = 0

# 检查状态文件
if state_file.exists():
    try:
        with state_file.open('r', encoding='utf-8') as f:
            state = json.load(f)
        print(f"\n状态信息:")
        print(f"  总图片数: {state.get('total_images', 0)}")
        print(f"  已完成: {state.get('completed_count', 0)}")
        print(f"  失败: {state.get('failed_count', 0)}")
        print(f"  跳过: {state.get('skipped_count', 0)}")
        print(f"  最后更新: {state.get('last_update', 'N/A')}")
    except Exception as e:
        print(f"\n状态文件读取错误: {e}")
else:
    print("\n状态文件不存在")

print()
if lines < 1000:
    remaining = 1000 - lines
    estimated_time = remaining * 30 / 60  # 假设每张30秒
    estimated_cost = remaining * 0.000125
    print(f"待处理: {remaining} 张")
    print(f"预计耗时: {estimated_time:.1f} 分钟")
    print(f"预计成本: ${estimated_cost:.6f}")
    print("\n建议: 运行 python scripts/abu/abu_run_stage0_full.py")
else:
    print("✅ 所有图片已处理完成!")

