#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估是否需要重新运行全部1000张图片
"""

import sys
import json
from pathlib import Path
from collections import Counter

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'

def analyze_results():
    """分析当前结果质量"""
    
    print("=" * 80)
    print("评估是否需要重新运行全部1000张图片")
    print("=" * 80)
    print()
    
    if not OUTPUT_FILE.exists():
        print("❌ 输出文件不存在，需要重新运行")
        return True
    
    # 读取所有结果
    results = []
    parse_errors = 0
    missing_fields = Counter()
    patterns_count = 0
    signals_count = 0
    
    with OUTPUT_FILE.open('r', encoding='utf-8') as f:
        for line in f:
            try:
                record = json.loads(line)
                result = record.get('result', {})
                results.append(result)
                
                # 检查JSON解析错误
                if 'parse_error' in result or 'raw' in result:
                    parse_errors += 1
                
                # 检查新字段
                if 'chart_overview' not in result:
                    missing_fields['chart_overview'] += 1
                if 'complete_price_path' not in result:
                    missing_fields['complete_price_path'] += 1
                if 'complete_narrative' not in result:
                    missing_fields['complete_narrative'] += 1
                
                # 统计patterns和signals
                patterns = result.get('patterns', [])
                signals = result.get('trading_signals', [])
                patterns_count += len(patterns)
                signals_count += len(signals)
                
            except Exception as e:
                print(f"⚠️  解析记录失败: {e}")
                continue
    
    total = len(results)
    print(f"总记录数: {total}")
    print()
    
    # JSON解析错误率
    parse_error_rate = parse_errors / total * 100 if total > 0 else 0
    print(f"JSON解析错误: {parse_errors}/{total} ({parse_error_rate:.1f}%)")
    
    # 缺失字段统计
    print()
    print("缺失字段统计:")
    for field, count in missing_fields.items():
        rate = count / total * 100 if total > 0 else 0
        print(f"  - {field}: {count}/{total} ({rate:.1f}%)")
    
    # 平均patterns和signals
    avg_patterns = patterns_count / total if total > 0 else 0
    avg_signals = signals_count / total if total > 0 else 0
    print()
    print(f"平均patterns: {avg_patterns:.1f}/张")
    print(f"平均signals: {avg_signals:.1f}/张")
    print()
    
    # 评估
    print("=" * 80)
    print("评估结果")
    print("=" * 80)
    print()
    
    issues = []
    if parse_error_rate > 10:
        issues.append(f"❌ JSON解析错误率过高 ({parse_error_rate:.1f}%)")
    if missing_fields.get('chart_overview', 0) > total * 0.2:
        issues.append(f"❌ chart_overview缺失率过高 ({missing_fields.get('chart_overview', 0)/total*100:.1f}%)")
    if missing_fields.get('complete_price_path', 0) > total * 0.2:
        issues.append(f"❌ complete_price_path缺失率过高 ({missing_fields.get('complete_price_path', 0)/total*100:.1f}%)")
    if missing_fields.get('complete_narrative', 0) > total * 0.2:
        issues.append(f"❌ complete_narrative缺失率过高 ({missing_fields.get('complete_narrative', 0)/total*100:.1f}%)")
    if avg_patterns < 0.5:
        issues.append(f"⚠️  平均patterns过少 ({avg_patterns:.1f}/张)")
    if avg_signals < 0.3:
        issues.append(f"⚠️  平均signals过少 ({avg_signals:.1f}/张)")
    
    if issues:
        print("发现问题:")
        for issue in issues:
            print(f"  {issue}")
        print()
        print("✅ 建议: 重新运行全部1000张图片")
        print("  理由:")
        print("    1. 已优化Prompt，要求返回完整字段")
        print("    2. 已改进JSON解析逻辑，更健壮")
        print("    3. 当前结果质量不达标，需要重新处理")
        return True
    else:
        print("✅ 结果质量良好，无需重新运行")
        return False

def main():
    try:
        should_rerun = analyze_results()
        
        print()
        print("=" * 80)
        if should_rerun:
            print("建议操作:")
            print("  1. 清空现有输出: python scripts/abu_reset_stage0.py")
            print("  2. 使用优化后的Prompt重新处理: python scripts/abu_optimize_speed.py")
        else:
            print("当前结果质量可接受，继续处理剩余图片即可")
        
        return 0 if not should_rerun else 1
    except Exception as e:
        print(f"❌ 评估失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())



