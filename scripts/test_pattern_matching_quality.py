#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模式匹配效果测试与对比

测试ABU系统v3.0的模式匹配质量，对比不同数据源的效果。
"""

import sys
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
    from abu.unified_pattern_library import UnifiedPatternLibrary
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def get_btc_kline_gateio(timeframe='15m', limit=200):
    """从Gate.io获取BTC K线数据"""
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h'}
        interval = tf_map.get(timeframe, '15m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
                klines = []
                for k in data:
                    klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[5]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'close': float(k[2]),
                        'volume': float(k[1])
                    })
                return klines
    except Exception as e:
        print(f"[WARN] Gate.io获取失败: {e}", file=sys.stderr)
    return None


def extract_features_from_klines(klines: List[Dict], timeframe: str) -> Dict:
    """从K线数据提取特征"""
    if not klines or len(klines) < 20:
        return {}
    
    recent = klines[-50:] if len(klines) >= 50 else klines
    
    closes = [k['close'] for k in recent]
    highs = [k['high'] for k in recent]
    lows = [k['low'] for k in recent]
    volumes = [k.get('volume', 0) for k in recent]
    
    # 趋势特征
    if len(closes) >= 10:
        price_trend = 'bullish' if closes[-1] > closes[0] else 'bearish'
        trend_strength = abs(closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
    else:
        price_trend = 'neutral'
        trend_strength = 0
    
    # K线特征
    kline_features = []
    if len(recent) >= 2:
        for i in range(max(1, len(recent) - 5), len(recent)):
            if i < 1:
                continue
            last = recent[i]
            prev = recent[i-1]
            
            if last['close'] > last['open'] and prev['close'] < prev['open']:
                if last['open'] < prev['close'] and last['close'] > prev['open']:
                    kline_features.append('bullish_engulfing')
            elif last['close'] < last['open'] and prev['close'] > prev['open']:
                if last['open'] > prev['close'] and last['close'] < prev['open']:
                    kline_features.append('bearish_engulfing')
            
            if last['high'] < prev['high'] and last['low'] > prev['low']:
                kline_features.append('inside_bar')
    
    # 波动率
    price_ranges = [(h - l) for h, l in zip(highs, lows)]
    avg_range = sum(price_ranges) / len(price_ranges) if price_ranges else 0
    volatility = avg_range / closes[-1] if closes and closes[-1] > 0 else 0
    
    features = {
        'pattern_type': 'unknown',
        'direction': 'long' if price_trend == 'bullish' else 'short' if price_trend == 'bearish' else 'neutral',
        'trend': price_trend,
        'trend_strength': trend_strength,
        'kline_features': list(set(kline_features)),
        'volatility': volatility,
        'market_conditions': {
            'trend_strength': 'strong' if trend_strength > 0.02 else 'weak',
            'volatility': 'high' if volatility > 0.01 else 'low',
            'trend_direction': price_trend
        }
    }
    
    return features


def analyze_match_quality(matches: List, query_features: Dict) -> Dict:
    """分析匹配质量"""
    stats = {
        'total_matches': len(matches),
        'by_source': defaultdict(int),
        'by_pattern_type': defaultdict(int),
        'confidence_distribution': [],
        'score_distribution': [],
        'direction_match': {'long': 0, 'short': 0, 'neutral': 0},
        'high_confidence_count': 0,  # >= 0.8
        'medium_confidence_count': 0,  # 0.5-0.8
        'low_confidence_count': 0,  # < 0.5
    }
    
    query_direction = query_features.get('direction', 'neutral')
    
    for match in matches:
        # 统计数据源
        source = match.source
        stats['by_source'][source] += 1
        
        # 统计模式类型
        pattern_type = match.pattern_type
        stats['by_pattern_type'][pattern_type] += 1
        
        # 置信度分布
        confidence = match.combined_confidence
        stats['confidence_distribution'].append(confidence)
        if confidence >= 0.8:
            stats['high_confidence_count'] += 1
        elif confidence >= 0.5:
            stats['medium_confidence_count'] += 1
        else:
            stats['low_confidence_count'] += 1
        
        # 分数分布
        final_score = match.final_score
        stats['score_distribution'].append(final_score)
        
        # 方向匹配
        pattern_name_lower = match.pattern_name.lower()
        pattern_type_lower = pattern_type.lower()
        
        if any(kw in pattern_name_lower or kw in pattern_type_lower 
               for kw in ['bull', 'long', 'buy', 'up', 'ascending']):
            stats['direction_match']['long'] += 1
        elif any(kw in pattern_name_lower or kw in pattern_type_lower 
                 for kw in ['bear', 'short', 'sell', 'down', 'descending']):
            stats['direction_match']['short'] += 1
        else:
            stats['direction_match']['neutral'] += 1
    
    # 计算统计值
    if stats['confidence_distribution']:
        stats['avg_confidence'] = sum(stats['confidence_distribution']) / len(stats['confidence_distribution'])
        stats['max_confidence'] = max(stats['confidence_distribution'])
        stats['min_confidence'] = min(stats['confidence_distribution'])
    else:
        stats['avg_confidence'] = 0
        stats['max_confidence'] = 0
        stats['min_confidence'] = 0
    
    if stats['score_distribution']:
        stats['avg_score'] = sum(stats['score_distribution']) / len(stats['score_distribution'])
        stats['max_score'] = max(stats['score_distribution'])
        stats['min_score'] = min(stats['score_distribution'])
    else:
        stats['avg_score'] = 0
        stats['max_score'] = 0
        stats['min_score'] = 0
    
    # 方向匹配率
    if query_direction != 'neutral':
        if query_direction == 'long':
            direction_match_rate = stats['direction_match']['long'] / stats['total_matches'] if stats['total_matches'] > 0 else 0
        else:
            direction_match_rate = stats['direction_match']['short'] / stats['total_matches'] if stats['total_matches'] > 0 else 0
        stats['direction_match_rate'] = direction_match_rate
    else:
        stats['direction_match_rate'] = 0
    
    return stats


async def test_matching_quality():
    """测试匹配质量"""
    print("=" * 80)
    print("ABU系统v3.0模式匹配效果测试")
    print("=" * 80)
    print()
    
    # 1. 获取BTC K线数据
    print("1. 获取BTC市场数据...")
    klines_5m = get_btc_kline_gateio('5m', 200)
    klines_15m = get_btc_kline_gateio('15m', 200)
    
    if not klines_5m or not klines_15m:
        print("[ERROR] 无法获取K线数据")
        return 1
    
    current_price = klines_15m[-1]['close']
    print(f"   当前价格: ${current_price:,.2f}")
    print(f"   5分钟K线: {len(klines_5m)}根")
    print(f"   15分钟K线: {len(klines_15m)}根")
    print()
    
    # 2. 提取特征
    print("2. 提取K线特征...")
    features_5m = extract_features_from_klines(klines_5m, '5m')
    features_15m = extract_features_from_klines(klines_15m, '15m')
    
    print(f"   5分钟趋势: {features_5m.get('trend')} ({features_5m.get('direction')})")
    print(f"   15分钟趋势: {features_15m.get('trend')} ({features_15m.get('direction')})")
    print()
    
    # 3. 初始化匹配器
    print("3. 初始化匹配器...")
    matcher = EnhancedHybridMatcher(
        strategy='comprehensive',
        use_async=True,
        use_vision=False,
        top_k=20,
        min_confidence=0.2,
        min_similarity=0.25
    )
    print("   [OK] 匹配器初始化完成")
    print()
    
    # 4. 测试5分钟匹配
    print("4. 测试5分钟匹配...")
    print("-" * 80)
    klines_dict_5m = {'5m': klines_5m}
    matches_5m = await matcher.async_match(
        query_features=features_5m,
        klines_dict=klines_dict_5m,
        symbol="BTC_USDT"
    )
    
    stats_5m = analyze_match_quality(matches_5m, features_5m)
    
    print(f"匹配数量: {stats_5m['total_matches']}")
    print(f"平均置信度: {stats_5m['avg_confidence']:.2%}")
    print(f"置信度范围: {stats_5m['min_confidence']:.2%} - {stats_5m['max_confidence']:.2%}")
    print(f"平均分数: {stats_5m['avg_score']:.3f}")
    print(f"分数范围: {stats_5m['min_score']:.3f} - {stats_5m['max_score']:.3f}")
    print()
    print("数据源分布:")
    for source, count in sorted(stats_5m['by_source'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}个 ({count/stats_5m['total_matches']*100:.1f}%)")
    print()
    print("置信度分布:")
    print(f"  高置信度 (>=0.8): {stats_5m['high_confidence_count']}个")
    print(f"  中置信度 (0.5-0.8): {stats_5m['medium_confidence_count']}个")
    print(f"  低置信度 (<0.5): {stats_5m['low_confidence_count']}个")
    print()
    print("Top 5 匹配:")
    for i, match in enumerate(matches_5m[:5], 1):
        print(f"  {i}. {match.pattern_name} ({match.pattern_type})")
        print(f"     数据源: {match.source} | 置信度: {match.combined_confidence:.2%} | 分数: {match.final_score:.3f}")
    print()
    
    # 5. 测试15分钟匹配
    print("5. 测试15分钟匹配...")
    print("-" * 80)
    klines_dict_15m = {'15m': klines_15m}
    matches_15m = await matcher.async_match(
        query_features=features_15m,
        klines_dict=klines_dict_15m,
        symbol="BTC_USDT"
    )
    
    stats_15m = analyze_match_quality(matches_15m, features_15m)
    
    print(f"匹配数量: {stats_15m['total_matches']}")
    print(f"平均置信度: {stats_15m['avg_confidence']:.2%}")
    print(f"置信度范围: {stats_15m['min_confidence']:.2%} - {stats_15m['max_confidence']:.2%}")
    print(f"平均分数: {stats_15m['avg_score']:.3f}")
    print(f"分数范围: {stats_15m['min_score']:.3f} - {stats_15m['max_score']:.3f}")
    print()
    print("数据源分布:")
    for source, count in sorted(stats_15m['by_source'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count}个 ({count/stats_15m['total_matches']*100:.1f}%)")
    print()
    print("置信度分布:")
    print(f"  高置信度 (>=0.8): {stats_15m['high_confidence_count']}个")
    print(f"  中置信度 (0.5-0.8): {stats_15m['medium_confidence_count']}个")
    print(f"  低置信度 (<0.5): {stats_15m['low_confidence_count']}个")
    print()
    print("Top 5 匹配:")
    for i, match in enumerate(matches_15m[:5], 1):
        print(f"  {i}. {match.pattern_name} ({match.pattern_type})")
        print(f"     数据源: {match.source} | 置信度: {match.combined_confidence:.2%} | 分数: {match.final_score:.3f}")
    print()
    
    # 6. 对比分析
    print("6. 对比分析...")
    print("-" * 80)
    print("5分钟 vs 15分钟:")
    print(f"  匹配数量: {stats_5m['total_matches']} vs {stats_15m['total_matches']}")
    print(f"  平均置信度: {stats_5m['avg_confidence']:.2%} vs {stats_15m['avg_confidence']:.2%}")
    print(f"  平均分数: {stats_5m['avg_score']:.3f} vs {stats_15m['avg_score']:.3f}")
    print(f"  高置信度比例: {stats_5m['high_confidence_count']/stats_5m['total_matches']*100:.1f}% vs {stats_15m['high_confidence_count']/stats_15m['total_matches']*100:.1f}%")
    print()
    
    # 7. 数据源效果对比
    print("7. 数据源效果对比...")
    print("-" * 80)
    all_sources = set(list(stats_5m['by_source'].keys()) + list(stats_15m['by_source'].keys()))
    
    print("各数据源在5分钟和15分钟的表现:")
    for source in sorted(all_sources):
        count_5m = stats_5m['by_source'].get(source, 0)
        count_15m = stats_15m['by_source'].get(source, 0)
        print(f"  {source}:")
        print(f"    5分钟: {count_5m}个匹配")
        print(f"    15分钟: {count_15m}个匹配")
        print(f"    总计: {count_5m + count_15m}个匹配")
    print()
    
    # 8. 质量评估
    print("8. 质量评估...")
    print("-" * 80)
    
    # 计算质量分数
    quality_score_5m = (
        stats_5m['avg_confidence'] * 0.4 +
        (stats_5m['high_confidence_count'] / stats_5m['total_matches']) * 0.3 +
        stats_5m['avg_score'] * 0.3
    ) if stats_5m['total_matches'] > 0 else 0
    
    quality_score_15m = (
        stats_15m['avg_confidence'] * 0.4 +
        (stats_15m['high_confidence_count'] / stats_15m['total_matches']) * 0.3 +
        stats_15m['avg_score'] * 0.3
    ) if stats_15m['total_matches'] > 0 else 0
    
    print(f"5分钟质量分数: {quality_score_5m:.3f} (满分1.0)")
    if quality_score_5m >= 0.7:
        print("  评价: 优秀 ✓")
    elif quality_score_5m >= 0.5:
        print("  评价: 良好")
    else:
        print("  评价: 需要改进")
    
    print(f"15分钟质量分数: {quality_score_15m:.3f} (满分1.0)")
    if quality_score_15m >= 0.7:
        print("  评价: 优秀 ✓")
    elif quality_score_15m >= 0.5:
        print("  评价: 良好")
    else:
        print("  评价: 需要改进")
    print()
    
    # 9. 建议
    print("9. 改进建议...")
    print("-" * 80)
    
    if stats_5m['low_confidence_count'] > stats_5m['total_matches'] * 0.5:
        print("  ⚠️  5分钟低置信度匹配过多，建议:")
        print("     - 提高相似度阈值")
        print("     - 优化特征提取算法")
        print("     - 增加模式库质量")
    
    if stats_15m['low_confidence_count'] > stats_15m['total_matches'] * 0.5:
        print("  ⚠️  15分钟低置信度匹配过多，建议:")
        print("     - 提高相似度阈值")
        print("     - 优化特征提取算法")
        print("     - 增加模式库质量")
    
    if len(stats_5m['by_source']) == 1:
        print("  ⚠️  5分钟只匹配到一个数据源，建议:")
        print("     - 检查其他数据源的模式库")
        print("     - 降低数据源筛选阈值")
    
    if len(stats_15m['by_source']) == 1:
        print("  ⚠️  15分钟只匹配到一个数据源，建议:")
        print("     - 检查其他数据源的模式库")
        print("     - 降低数据源筛选阈值")
    
    print()
    
    # 清理
    matcher.close()
    
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(test_matching_quality())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
