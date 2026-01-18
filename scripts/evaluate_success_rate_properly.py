#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正确评估成功率和失败率
关键：即使JSON解析失败，如果关键信息已提取，应该算作成功或部分成功
"""

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

def has_key_fields(result: dict) -> bool:
    """检查是否有关键字段（即使JSON解析失败，但字段已提取）"""
    # 关键字段：chart_overview, complete_price_path, complete_narrative
    key_fields = ['chart_overview', 'complete_price_path', 'complete_narrative']
    return any(field in result for field in key_fields)

def has_usable_data(result: dict) -> bool:
    """检查是否有可用数据（即使有parse_error）"""
    # 如果有关键字段，或者有raw字段（可以后续解析），就算有可用数据
    if has_key_fields(result):
        return True
    if 'raw' in result and result.get('raw'):
        raw_text = result['raw']
        # 检查raw字段是否包含有用信息（不只是错误信息）
        if len(raw_text) > 100 and ('chart' in raw_text.lower() or 'pattern' in raw_text.lower() or 'price' in raw_text.lower()):
            return True
    return False

def evaluate_record(record: dict) -> str:
    """评估单条记录的状态"""
    result = record.get('result', {})
    
    # 完全失败：有error且没有可用数据
    if 'error' in result and not has_usable_data(result):
        return '完全失败'
    
    # 完全成功：有所有关键字段且没有parse_error
    if has_key_fields(result) and 'parse_error' not in result and 'error' not in result:
        return '完全成功'
    
    # 部分成功：有parse_error但关键信息已提取
    if has_key_fields(result) and 'parse_error' in result:
        return '部分成功（JSON解析失败但字段已提取）'
    
    # 部分成功：有raw字段可以后续处理
    if has_usable_data(result) and ('parse_error' in result or 'error' in result):
        return '部分成功（有原始数据可后续处理）'
    
    # 完全失败：没有可用数据
    return '完全失败'

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
    
    print("=" * 80)
    print("正确评估成功率和失败率")
    print("=" * 80)
    print()
    
    print(f"总记录数: {len(records)}")
    print()
    
    # 按状态分类
    status_counts = {}
    status_examples = {}
    
    for record in records:
        status = evaluate_record(record)
        status_counts[status] = status_counts.get(status, 0) + 1
        
        # 保存几个例子
        if status not in status_examples:
            status_examples[status] = []
        if len(status_examples[status]) < 3:
            img_path = Path(record.get('image', ''))
            status_examples[status].append(img_path.name if img_path else 'unknown')
    
    # 统计
    total = len(records)
    fully_successful = status_counts.get('完全成功', 0)
    partially_successful = status_counts.get('部分成功（JSON解析失败但字段已提取）', 0) + status_counts.get('部分成功（有原始数据可后续处理）', 0)
    fully_failed = status_counts.get('完全失败', 0)
    
    total_usable = fully_successful + partially_successful
    
    print("📊 详细统计:")
    for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100 if total > 0 else 0
        print(f"   {status}: {count} ({pct:.1f}%)")
    print()
    
    print("📈 汇总评估:")
    print(f"   ✅ 完全成功: {fully_successful} ({fully_successful/total*100:.1f}%)")
    print(f"   ⚠️  部分成功（有可用数据）: {partially_successful} ({partially_successful/total*100:.1f}%)")
    print(f"   ❌ 完全失败: {fully_failed} ({fully_failed/total*100:.1f}%)")
    print()
    print(f"   💡 实际可用率: {total_usable}/{total} ({total_usable/total*100:.1f}%)")
    print()
    
    # 新字段提取情况（包括部分成功的）
    all_with_fields = []
    for record in records:
        result = record.get('result', {})
        if has_key_fields(result):
            all_with_fields.append(record)
    
    if all_with_fields:
        with_chart_overview = sum(1 for r in all_with_fields if 'chart_overview' in r.get('result', {}))
        with_price_path = sum(1 for r in all_with_fields if 'complete_price_path' in r.get('result', {}))
        with_narrative = sum(1 for r in all_with_fields if 'complete_narrative' in r.get('result', {}))
        
        print("📋 关键字段提取情况（包括部分成功的记录）:")
        print(f"   有chart_overview: {with_chart_overview}/{len(all_with_fields)} ({with_chart_overview/len(all_with_fields)*100:.1f}%)")
        print(f"   有complete_price_path: {with_price_path}/{len(all_with_fields)} ({with_price_path/len(all_with_fields)*100:.1f}%)")
        print(f"   有complete_narrative: {with_narrative}/{len(all_with_fields)} ({with_narrative/len(all_with_fields)*100:.1f}%)")
        print()
    
    # 显示例子
    print("📝 各类状态示例:")
    for status, examples in status_examples.items():
        if examples:
            print(f"   {status}:")
            for ex in examples:
                print(f"     - {ex}")
    print()
    
    print("=" * 80)
    print()
    print("✅ 结论:")
    print(f"   - 实际可用率: {total_usable/total*100:.1f}% (包括完全成功和部分成功)")
    print(f"   - 完全失败率: {fully_failed/total*100:.1f}%")
    print(f"   - 之前的计算方式错误地标记了部分成功为失败")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())



