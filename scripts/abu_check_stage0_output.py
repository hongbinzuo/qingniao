#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查阶段0输出质量（优化前后对比）
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent

def analyze_output(file_path: Path):
    """分析输出文件"""
    if not file_path.exists():
        return None
    
    stats = {
        'total': 0,
        'with_patterns': 0,
        'with_trading_signals': 0,
        'with_pattern_combination': 0,
        'with_kline_features': 0,
        'patterns_count': 0,
        'signals_count': 0,
        'parse_errors': 0,
        'confidence_avg': 0.0,
        'confidence_sum': 0.0
    }
    
    patterns_found = defaultdict(int)
    signal_directions = defaultdict(int)
    
    with file_path.open('r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            
            try:
                record = json.loads(line)
                stats['total'] += 1
                
                result = record.get('result', {})
                
                # 检查是否有parse_error
                if 'parse_error' in result:
                    stats['parse_errors'] += 1
                    # 尝试从raw中提取
                    raw = result.get('raw', '')
                    if raw and 'patterns' in raw:
                        stats['with_patterns'] += 1
                    if raw and 'trading_signals' in raw:
                        stats['with_trading_signals'] += 1
                    continue
                
                # Patterns
                patterns = result.get('patterns', [])
                if patterns:
                    stats['with_patterns'] += 1
                    stats['patterns_count'] += len(patterns)
                    for p in patterns:
                        patterns_found[p.get('name', 'unknown')] += 1
                
                # Pattern combination
                if result.get('pattern_combination'):
                    stats['with_pattern_combination'] += 1
                
                # Trading signals
                signals = result.get('trading_signals', [])
                if signals:
                    stats['with_trading_signals'] += 1
                    stats['signals_count'] += len(signals)
                    for s in signals:
                        direction = s.get('direction', 'unknown')
                        signal_directions[direction] += 1
                
                # K-line features
                kline_features = result.get('price_action_behavior', {}).get('kline_features', [])
                if kline_features:
                    stats['with_kline_features'] += 1
                
                # Confidence
                conf = result.get('confidence', 0.0)
                if conf:
                    stats['confidence_sum'] += conf
                
            except Exception as e:
                print(f"解析错误: {e}")
                continue
    
    if stats['total'] > 0:
        stats['confidence_avg'] = stats['confidence_sum'] / stats['total']
        stats['patterns_rate'] = stats['with_patterns'] / stats['total'] * 100
        stats['signals_rate'] = stats['with_trading_signals'] / stats['total'] * 100
    
    stats['top_patterns'] = dict(sorted(patterns_found.items(), key=lambda x: x[1], reverse=True)[:10])
    stats['signal_directions'] = dict(signal_directions)
    
    return stats

def main():
    output_file = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'
    
    print("=" * 80)
    print("阶段0输出质量分析（优化后）")
    print("=" * 80)
    print()
    
    stats = analyze_output(output_file)
    
    if not stats:
        print("❌ 输出文件不存在或为空")
        return 1
    
    print(f"总图片数: {stats['total']}")
    print()
    print("识别率:")
    print(f"  - Patterns识别率: {stats['patterns_rate']:.1f}% ({stats['with_patterns']}/{stats['total']})")
    print(f"  - Trading Signals识别率: {stats['signals_rate']:.1f}% ({stats['with_trading_signals']}/{stats['total']})")
    print(f"  - Pattern组合识别率: {stats['with_pattern_combination']/stats['total']*100:.1f}% ({stats['with_pattern_combination']}/{stats['total']})")
    print(f"  - K-line特征识别率: {stats['with_kline_features']/stats['total']*100:.1f}% ({stats['with_kline_features']}/{stats['total']})")
    print()
    print("数量统计:")
    print(f"  - 总Patterns数: {stats['patterns_count']} (平均: {stats['patterns_count']/stats['total']:.1f}/张)")
    print(f"  - 总Signals数: {stats['signals_count']} (平均: {stats['signals_count']/stats['total']:.1f}/张)")
    print()
    print("质量指标:")
    print(f"  - 平均Confidence: {stats['confidence_avg']:.2f}")
    print(f"  - JSON解析错误: {stats['parse_errors']} ({stats['parse_errors']/stats['total']*100:.1f}%)")
    print()
    
    if stats['top_patterns']:
        print("最常见的Patterns (Top 10):")
        for name, count in list(stats['top_patterns'].items())[:10]:
            print(f"  - {name}: {count}次")
        print()
    
    if stats['signal_directions']:
        print("Trading Signals方向分布:")
        for direction, count in stats['signal_directions'].items():
            print(f"  - {direction}: {count}个")
        print()
    
    # 评估
    print("=" * 80)
    print("优化效果评估:")
    print("=" * 80)
    
    if stats['patterns_rate'] >= 50 and stats['signals_rate'] >= 50:
        print("✅ 优化效果显著！")
        print("   - Patterns和Trading Signals识别率均超过50%")
        print("   - 可以继续处理全部1000张图片")
    elif stats['patterns_rate'] >= 30 or stats['signals_rate'] >= 30:
        print("⚠️  优化效果中等")
        print("   - 识别率有所提升，但仍有改进空间")
        print("   - 建议继续处理全部1000张，然后根据完整数据进一步优化")
    else:
        print("❌ 优化效果不明显")
        print("   - 识别率仍然较低，建议进一步优化Prompt")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

