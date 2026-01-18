#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查实际处理进度"""

import sys
import json
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'

def main():
    if not OUTPUT_FILE.exists():
        print("输出文件不存在")
        return 1
    
    lines = OUTPUT_FILE.read_text(encoding='utf-8').strip().split('\n')
    records = []
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            records.append(record)
        except:
            continue
    
    print("=" * 70)
    print("实际处理进度检查")
    print("=" * 70)
    print()
    
    print(f"输出文件记录数: {len(records)}")
    
    # 正确评估：即使JSON解析失败，如果关键信息已提取，应该算作成功或部分成功
    def has_key_fields(result: dict) -> bool:
        """检查是否有关键字段"""
        key_fields = ['chart_overview', 'complete_price_path', 'complete_narrative']
        return any(field in result for field in key_fields)
    
    def has_usable_data(result: dict) -> bool:
        """检查是否有可用数据（即使有parse_error）"""
        if has_key_fields(result):
            return True
        if 'raw' in result and result.get('raw'):
            raw_text = result['raw']
            if len(raw_text) > 100 and ('chart' in raw_text.lower() or 'pattern' in raw_text.lower() or 'price' in raw_text.lower()):
                return True
        return False
    
    fully_successful = []
    partially_successful = []
    fully_failed = []
    
    for record in records:
        result = record.get('result', {})
        
        # 完全成功：有所有关键字段且没有parse_error
        if has_key_fields(result) and 'parse_error' not in result and 'error' not in result:
            fully_successful.append(record)
        # 部分成功：有parse_error但关键信息已提取，或有raw字段可后续处理
        elif has_usable_data(result):
            partially_successful.append(record)
        # 完全失败：没有可用数据
        else:
            fully_failed.append(record)
    
    total_usable = len(fully_successful) + len(partially_successful)
    
    print(f"✅ 完全成功: {len(fully_successful)} 张 ({len(fully_successful)/len(records)*100:.1f}%)")
    print(f"⚠️  部分成功（有可用数据）: {len(partially_successful)} 张 ({len(partially_successful)/len(records)*100:.1f}%)")
    print(f"❌ 完全失败: {len(fully_failed)} 张 ({len(fully_failed)/len(records)*100:.1f}%)")
    print()
    print(f"💡 实际可用率: {total_usable}/{len(records)} ({total_usable/len(records)*100:.1f}%)")
    print()
    
    # 统计新字段提取（包括部分成功的）
    all_with_fields = [r for r in records if has_key_fields(r.get('result', {}))]
    with_chart_overview = sum(1 for r in all_with_fields if 'chart_overview' in r.get('result', {}))
    with_price_path = sum(1 for r in all_with_fields if 'complete_price_path' in r.get('result', {}))
    with_narrative = sum(1 for r in all_with_fields if 'complete_narrative' in r.get('result', {}))
    
    if len(all_with_fields) > 0:
        print(f"新字段提取情况（包括部分成功的记录）:")
        print(f"  chart_overview: {with_chart_overview}/{len(all_with_fields)} ({with_chart_overview/len(all_with_fields)*100:.1f}%)")
        print(f"  complete_price_path: {with_price_path}/{len(all_with_fields)} ({with_price_path/len(all_with_fields)*100:.1f}%)")
        print(f"  complete_narrative: {with_narrative}/{len(all_with_fields)} ({with_narrative/len(all_with_fields)*100:.1f}%)")
        print()
    
    # 显示最新处理的几张
    if records:
        print("最新处理的图片（最后5张）:")
        for i, record in enumerate(records[-5:], 1):
            img_path = Path(record.get('image', ''))
            img_name = img_path.name if img_path else 'unknown'
            has_error = 'error' in record.get('result', {}) or 'parse_error' in record.get('result', {})
            status = "❌" if has_error else "✅"
            print(f"  {i}. {status} {img_name}")
    
    print()
    print("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

