#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini匹配验证器

功能：
- 测试不同的阈值和参数
- 收集匹配结果进行验证
- 生成验证报告
- 分析匹配性能

使用：
    python scripts/abu_gemini_match_validator.py \
        --symbols BTC,ETH,SOL \
        --timeframes 5m,15m,1h,4h \
        --days 28 \
        --min-similarities 0.3,0.4,0.5,0.6,0.7 \
        --output outputs/abu_match_validation.json
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin

try:
    from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
    MATCHER_AVAILABLE = True
except ImportError:
    MATCHER_AVAILABLE = False
    EnhancedGeminiPatternMatcher = None
    try:
        from abu.gemini_pattern_matcher import GeminiPatternMatcher
        # 兼容旧版本
        class EnhancedGeminiPatternMatcher:
            def __init__(self, use_dl=False):
                self.matcher = GeminiPatternMatcher()
                self.pattern_library = self.matcher.pattern_library
            
            def match_patterns(self, klines_dict, min_similarity=0.5, max_matches=10):
                klines_15m = klines_dict.get('15m', [])
                klines_1h = klines_dict.get('1h', [])
                return self.matcher.match_patterns(klines_15m, klines_1h, min_similarity, max_matches)
            
            def generate_signal_from_match(self, match, current_price, klines_15m):
                return self.matcher.generate_signal_from_match(match, current_price, klines_15m)
    except ImportError:
        pass


def get_klines(symbol: str, timeframe: str, limit: int, exchange: str = 'binance') -> List[Dict]:
    """获取K线数据"""
    try:
        if exchange == 'binance':
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        else:
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
    except Exception:
        return []
    return []


def calculate_klines_limit(timeframe: str, days: int) -> int:
    """计算K线数量限制"""
    timeframe_limits = {
        '5m': 288,
        '15m': 96,
        '1h': 24,
        '4h': 6
    }
    limit_per_day = timeframe_limits.get(timeframe, 96)
    return limit_per_day * days


def validate_match(matcher: EnhancedGeminiPatternMatcher, symbol: str, 
                   klines_dict: Dict[str, List[Dict]], min_similarity: float) -> Dict[str, Any]:
    """
    验证单个币种的匹配
    
    Args:
        matcher: 匹配器
        symbol: 币种
        klines_dict: K线数据字典
        min_similarity: 最小相似度阈值
    
    Returns:
        验证结果字典
    """
    result = {
        'symbol': symbol,
        'min_similarity': min_similarity,
        'matches_count': 0,
        'matches': [],
        'avg_similarity': 0.0,
        'max_similarity': 0.0,
        'min_similarity_found': 1.0,
        'success': False,
        'error': None
    }
    
    try:
        # 匹配模式
        matches = matcher.match_patterns(
            klines_dict,
            min_similarity=min_similarity,
            max_matches=20  # 获取更多匹配用于分析
        )
        
        if matches:
            result['matches_count'] = len(matches)
            result['matches'] = [
                {
                    'pattern_id': m['pattern_id'],
                    'pattern_name': m['pattern_name'],
                    'similarity': m['similarity']
                }
                for m in matches
            ]
            
            similarities = [m['similarity'] for m in matches]
            result['avg_similarity'] = sum(similarities) / len(similarities) if similarities else 0.0
            result['max_similarity'] = max(similarities) if similarities else 0.0
            result['min_similarity_found'] = min(similarities) if similarities else 1.0
            result['success'] = True
        else:
            result['success'] = True  # 没有匹配也算成功
    
    except Exception as e:
        result['error'] = str(e)
        result['success'] = False
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ABU Gemini匹配验证器')
    parser.add_argument('--symbols', type=str, default='BTC,ETH,SOL', 
                       help='测试币种，逗号分隔')
    parser.add_argument('--timeframes', type=str, default='5m,15m,1h,4h',
                       help='时间框架，逗号分隔')
    parser.add_argument('--days', type=int, default=28, help='时间跨度（天数）')
    parser.add_argument('--min-similarities', type=str, default='0.3,0.4,0.5,0.6,0.7',
                       help='最小相似度阈值列表，逗号分隔')
    parser.add_argument('--exchange', type=str, default='binance', help='交易所')
    parser.add_argument('--use-dl', type=int, default=0, help='是否使用深度学习（0/1）')
    parser.add_argument('--output', type=str, default='outputs/abu_match_validation.json',
                       help='输出文件路径')
    
    args = parser.parse_args()
    
    if not MATCHER_AVAILABLE or not EnhancedGeminiPatternMatcher:
        print("✗ 错误: 无法导入EnhancedGeminiPatternMatcher模块", file=sys.stderr)
        return 1
    
    # 解析参数
    symbols = [s.strip() for s in args.symbols.split(',') if s.strip()]
    timeframes = [tf.strip() for tf in args.timeframes.split(',') if tf.strip()]
    min_similarities = [float(s.strip()) for s in args.min_similarities.split(',') if s.strip()]
    
    if not symbols or not timeframes or not min_similarities:
        print("✗ 错误: 参数解析失败", file=sys.stderr)
        return 1
    
    print("=" * 80)
    print("ABU Gemini匹配验证器")
    print("=" * 80)
    print(f"测试币种: {', '.join(symbols)}")
    print(f"时间框架: {', '.join(timeframes)}")
    print(f"时间跨度: {args.days} 天")
    print(f"相似度阈值: {', '.join(map(str, min_similarities))}")
    print()
    
    # 初始化匹配器
    print("加载模式库...")
    matcher = EnhancedGeminiPatternMatcher(use_dl=bool(args.use_dl))
    
    if not hasattr(matcher, 'pattern_library') or len(matcher.pattern_library) == 0:
        print("✗ 错误: 模式库为空", file=sys.stderr)
        return 1
    
    pattern_count = len(matcher.pattern_library) if hasattr(matcher, 'pattern_library') else 0
    print(f"✓ 模式库已加载: {pattern_count} 个模式")
    print()
    
    # 执行验证
    all_results = []
    stats_by_threshold = defaultdict(lambda: {
        'total_matches': 0,
        'total_symbols': 0,
        'successful_symbols': 0,
        'avg_matches_per_symbol': 0.0,
        'avg_similarity': 0.0,
        'max_similarity': 0.0
    })
    
    for symbol in symbols:
        print(f"处理 {symbol}...", end=' ', flush=True)
        
        # 获取K线数据
        klines_dict = {}
        for tf in timeframes:
            limit = calculate_klines_limit(tf, args.days)
            klines = get_klines(symbol, tf, limit, args.exchange)
            if klines and len(klines) >= 20:
                klines_dict[tf] = klines
        
        if not klines_dict:
            print("跳过（K线数据不足）")
            continue
        
        # 测试不同阈值
        symbol_results = []
        for min_sim in min_similarities:
            result = validate_match(matcher, symbol, klines_dict, min_sim)
            symbol_results.append(result)
            all_results.append(result)
            
            # 更新统计
            stats = stats_by_threshold[min_sim]
            stats['total_symbols'] += 1
            if result['success']:
                stats['successful_symbols'] += 1
            if result['matches_count'] > 0:
                stats['total_matches'] += result['matches_count']
                stats['avg_similarity'] = (stats['avg_similarity'] * (stats['total_matches'] - result['matches_count']) + 
                                         result['avg_similarity'] * result['matches_count']) / stats['total_matches']
                stats['max_similarity'] = max(stats['max_similarity'], result['max_similarity'])
        
        # 计算平均值
        for min_sim in min_similarities:
            stats = stats_by_threshold[min_sim]
            if stats['successful_symbols'] > 0:
                stats['avg_matches_per_symbol'] = stats['total_matches'] / stats['successful_symbols']
        
        print(f"完成")
    
    print()
    
    # 打印统计结果
    print("=" * 80)
    print("验证结果统计")
    print("=" * 80)
    print(f"{'阈值':<8} {'成功币种':<10} {'总匹配数':<10} {'平均匹配/币种':<15} {'平均相似度':<12} {'最大相似度':<12}")
    print("-" * 80)
    
    for min_sim in sorted(min_similarities):
        stats = stats_by_threshold[min_sim]
        print(f"{min_sim:<8.2f} {stats['successful_symbols']:<10} {stats['total_matches']:<10} "
              f"{stats['avg_matches_per_symbol']:<15.2f} {stats['avg_similarity']:<12.3f} "
              f"{stats['max_similarity']:<12.3f}")
    
    print()
    
    # 保存结果
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'config': {
            'symbols': symbols,
            'timeframes': timeframes,
            'days': args.days,
            'min_similarities': min_similarities,
            'exchange': args.exchange,
            'use_dl': bool(args.use_dl),
            'pattern_count': pattern_count
        },
        'results': all_results,
        'statistics': {
            str(k): v for k, v in stats_by_threshold.items()
        }
    }
    
    with output_file.open('w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 结果已保存到: {output_file}")
    
    # 生成Markdown报告
    md_file = output_file.with_suffix('.md')
    lines = [
        f"# ABU Gemini匹配验证报告",
        f"",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**模式库规模**: {pattern_count} 个模式",
        f"**测试币种**: {', '.join(symbols)}",
        f"**时间框架**: {', '.join(timeframes)}",
        f"**时间跨度**: {args.days} 天",
        f"",
        "## 统计结果",
        f"",
        "| 阈值 | 成功币种 | 总匹配数 | 平均匹配/币种 | 平均相似度 | 最大相似度 |",
        "|---|---|---|---|---|---|"
    ]
    
    for min_sim in sorted(min_similarities):
        stats = stats_by_threshold[min_sim]
        lines.append(
            f"| {min_sim:.2f} | {stats['successful_symbols']} | {stats['total_matches']} | "
            f"{stats['avg_matches_per_symbol']:.2f} | {stats['avg_similarity']:.3f} | "
            f"{stats['max_similarity']:.3f} |"
        )
    
    lines.extend([
        "",
        "## 详细结果",
        "",
        "### 按币种分组",
        ""
    ])
    
    for symbol in symbols:
        symbol_results = [r for r in all_results if r['symbol'] == symbol]
        if symbol_results:
            lines.append(f"#### {symbol}")
            lines.append("")
            lines.append("| 阈值 | 匹配数 | 平均相似度 | 最大相似度 | 最小相似度 |")
            lines.append("|---|---|---|---|---|")
            for r in symbol_results:
                lines.append(
                    f"| {r['min_similarity']:.2f} | {r['matches_count']} | "
                    f"{r['avg_similarity']:.3f} | {r['max_similarity']:.3f} | "
                    f"{r['min_similarity_found']:.3f} |"
                )
            lines.append("")
    
    md_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"✓ Markdown报告已保存到: {md_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

