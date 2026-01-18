#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速检查新字段提取情况"""

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
    print(f"总记录数: {len(lines)}")
    print()
    
    chart_overview_count = 0
    price_path_count = 0
    narrative_count = 0
    parse_error_count = 0
    
    for i, line in enumerate(lines[:10], 1):
        try:
            record = json.loads(line)
            result = record.get('result', {})
            image_name = Path(record.get('image', '')).name
            
            has_chart_overview = 'chart_overview' in result
            has_price_path = 'complete_price_path' in result
            has_narrative = 'complete_narrative' in result
            has_error = 'parse_error' in result
            
            if has_chart_overview:
                chart_overview_count += 1
            if has_price_path:
                price_path_count += 1
            if has_narrative:
                narrative_count += 1
            if has_error:
                parse_error_count += 1
            
            print(f"{i}. {image_name}")
            print(f"   chart_overview: {'✅' if has_chart_overview else '❌'}")
            print(f"   complete_price_path: {'✅' if has_price_path else '❌'}")
            print(f"   complete_narrative: {'✅' if has_narrative else '❌'}")
            print(f"   parse_error: {'⚠️' if has_error else '✅'}")
            print()
            
        except Exception as e:
            print(f"{i}. 解析失败: {e}")
            print()
    
    print("=" * 60)
    print(f"前{min(10, len(lines))}条记录统计:")
    print(f"  chart_overview: {chart_overview_count}/{min(10, len(lines))} ({chart_overview_count/min(10, len(lines))*100:.1f}%)")
    print(f"  complete_price_path: {price_path_count}/{min(10, len(lines))} ({price_path_count/min(10, len(lines))*100:.1f}%)")
    print(f"  complete_narrative: {narrative_count}/{min(10, len(lines))} ({narrative_count/min(10, len(lines))*100:.1f}%)")
    print(f"  parse_error: {parse_error_count}/{min(10, len(lines))} ({parse_error_count/min(10, len(lines))*100:.1f}%)")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())



