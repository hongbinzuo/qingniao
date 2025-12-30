#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
科学的支撑阻力判断方法（综合多种方法）
"""

import numpy as np
from collections import defaultdict

def calculate_pivot_points(high, low, close):
    """计算枢轴点（Pivot Points）"""
    pp = (high + low + close) / 3
    r1 = 2 * pp - low
    r2 = pp + (high - low)
    r3 = high + 2 * (pp - low)
    s1 = 2 * pp - high
    s2 = pp - (high - low)
    s3 = low - 2 * (high - pp)
    return {
        'pivot': pp,
        'r1': r1, 'r2': r2, 'r3': r3,
        's1': s1, 's2': s2, 's3': s3
    }

def calculate_fibonacci_levels(high, low):
    """计算斐波那契回撤位"""
    diff = high - low
    return {
        'fib_0': high,
        'fib_236': high - diff * 0.236,
        'fib_382': high - diff * 0.382,
        'fib_500': high - diff * 0.500,
        'fib_618': high - diff * 0.618,
        'fib_786': high - diff * 0.786,
        'fib_100': low
    }

def identify_price_action_levels(klines, lookback=100, min_touches=3, tolerance_pct=0.01):
    """价格行为法：识别多次测试的支撑阻力位"""
    if len(klines) < lookback:
        lookback = len(klines)
    
    recent = klines[-lookback:]
    levels = defaultdict(lambda: {'touches': 0, 'volume': 0, 'type': None})
    
    for k in recent:
        high = k['high']
        low = k['low']
        close = k['close']
        volume = k['volume']
        
        # 检查高点（阻力）
        for price in [high]:
            key = round(price / (tolerance_pct * price)) * (tolerance_pct * price)
            levels[key]['touches'] += 1
            levels[key]['volume'] += volume
            if levels[key]['type'] is None:
                levels[key]['type'] = 'resistance'
        
        # 检查低点（支撑）
        for price in [low]:
            key = round(price / (tolerance_pct * price)) * (tolerance_pct * price)
            levels[key]['touches'] += 1
            levels[key]['volume'] += volume
            if levels[key]['type'] is None:
                levels[key]['type'] = 'support'
    
    # 筛选出测试次数>=min_touches的级别
    significant_levels = []
    for price, data in levels.items():
        if data['touches'] >= min_touches:
            significant_levels.append({
                'price': price,
                'touches': data['touches'],
                'volume': data['volume'],
                'type': data['type'],
                'strength': data['touches'] * 2 + (data['volume'] / max([k['volume'] for k in recent]) if recent else 1)
            })
    
    return sorted(significant_levels, key=lambda x: x['strength'], reverse=True)

def calculate_volume_profile(klines, num_bins=20):
    """计算成交量分布（Volume Profile）"""
    if not klines:
        return None
    
    prices = []
    volumes = []
    for k in klines:
        prices.extend([k['high'], k['low'], k['close']])
        volumes.extend([k['volume']/3, k['volume']/3, k['volume']/3])
    
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price
    
    if price_range == 0:
        return None
    
    bins = {}
    bin_size = price_range / num_bins
    
    for price, volume in zip(prices, volumes):
        bin_index = int((price - min_price) / bin_size)
        bin_index = min(bin_index, num_bins - 1)
        bin_price = min_price + bin_index * bin_size
        
        if bin_price not in bins:
            bins[bin_price] = 0
        bins[bin_price] += volume
    
    # 找出POC（成交量最大的价格点）
    poc_price = max(bins.items(), key=lambda x: x[1])[0]
    max_volume = bins[poc_price]
    
    # 找出价值区域（70%成交量）
    sorted_bins = sorted(bins.items(), key=lambda x: x[1], reverse=True)
    total_volume = sum(bins.values())
    cumulative_volume = 0
    value_area_prices = []
    
    for price, volume in sorted_bins:
        cumulative_volume += volume
        value_area_prices.append(price)
        if cumulative_volume >= total_volume * 0.70:
            break
    
    value_area_high = max(value_area_prices)
    value_area_low = min(value_area_prices)
    
    # 找出价格上方的成交量密集区（用于阻力位）
    # 找出成交量前3大的价格区间（在价格上方）
    high_volume_bins = sorted(bins.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'poc': poc_price,
        'value_area_high': value_area_high,
        'value_area_low': value_area_low,
        'bins': bins,
        'high_volume_bins': high_volume_bins  # 高成交量区间
    }

def identify_trend_lines(klines, lookback=50):
    """识别趋势线（简化版：连接高点/低点）"""
    if len(klines) < 10:
        return None
    
    recent = klines[-lookback:]
    highs = [(i, k['high']) for i, k in enumerate(recent)]
    lows = [(i, k['low']) for i, k in enumerate(recent)]
    
    # 找出局部高点和低点
    local_highs = []
    local_lows = []
    
    for i in range(1, len(recent) - 1):
        if recent[i]['high'] > recent[i-1]['high'] and recent[i]['high'] > recent[i+1]['high']:
            local_highs.append((i, recent[i]['high']))
        if recent[i]['low'] < recent[i-1]['low'] and recent[i]['low'] < recent[i+1]['low']:
            local_lows.append((i, recent[i]['low']))
    
    # 计算趋势线（连接最近的两个高点/低点）
    resistance_line = None
    support_line = None
    
    if len(local_highs) >= 2:
        # 取最近两个高点
        p1 = local_highs[-2]
        p2 = local_highs[-1]
        slope = (p2[1] - p1[1]) / (p2[0] - p1[0]) if p2[0] != p1[0] else 0
        resistance_line = {
            'slope': slope,
            'price_at_end': p2[1],
            'type': 'resistance'
        }
    
    if len(local_lows) >= 2:
        p1 = local_lows[-2]
        p2 = local_lows[-1]
        slope = (p2[1] - p1[1]) / (p2[0] - p1[0]) if p2[0] != p1[0] else 0
        support_line = {
            'slope': slope,
            'price_at_end': p2[1],
            'type': 'support'
        }
    
    return {
        'resistance_line': resistance_line,
        'support_line': support_line
    }

def identify_historical_levels(klines, lookback=200, tolerance_pct=0.01):
    """识别历史关键高低点（多次触及）"""
    if len(klines) < lookback:
        lookback = len(klines)
    
    recent = klines[-lookback:]
    highs = [k['high'] for k in recent]
    lows = [k['low'] for k in recent]
    
    # 找出历史高点和低点
    max_high = max(highs)
    min_low = min(lows)
    
    # 统计价格在这些关键位置附近的测试次数
    high_touches = 0
    low_touches = 0
    
    for k in recent:
        if abs(k['high'] - max_high) / max_high <= tolerance_pct:
            high_touches += 1
        if abs(k['low'] - min_low) / min_low <= tolerance_pct:
            low_touches += 1
    
    return {
        'resistance': {
            'price': max_high,
            'touches': high_touches,
            'strength': high_touches
        },
        'support': {
            'price': min_low,
            'touches': low_touches,
            'strength': low_touches
        }
    }

def calculate_advanced_support_resistance(klines, current_price, ema_144=None, ema_169=None, vwap=None):
    """综合多种方法计算支撑阻力位"""
    if not klines or len(klines) < 50:
        return None
    
    results = {
        'methods': {},
        'support_levels': [],
        'resistance_levels': []
    }
    
    # 方法1：价格行为法
    price_action_levels = identify_price_action_levels(klines, lookback=100, min_touches=2)
    results['methods']['price_action'] = price_action_levels
    
    # 方法2：成交量分布（Volume Profile）
    volume_profile = calculate_volume_profile(klines[-100:], num_bins=30)
    results['methods']['volume_profile'] = volume_profile
    
    # 方法3：枢轴点
    recent_high = max([k['high'] for k in klines[-20:]])
    recent_low = min([k['low'] for k in klines[-20:]])
    recent_close = klines[-1]['close']
    pivot_points = calculate_pivot_points(recent_high, recent_low, recent_close)
    results['methods']['pivot_points'] = pivot_points
    
    # 方法4：斐波那契回撤
    swing_high = max([k['high'] for k in klines[-50:]])
    swing_low = min([k['low'] for k in klines[-50:]])
    fib_levels = calculate_fibonacci_levels(swing_high, swing_low)
    results['methods']['fibonacci'] = fib_levels
    
    # 方法5：历史高低点
    historical_levels = identify_historical_levels(klines, lookback=200)
    results['methods']['historical'] = historical_levels
    
    # 方法6：趋势线
    trend_lines = identify_trend_lines(klines[-100:])
    results['methods']['trend_lines'] = trend_lines
    
    # 收集所有支撑位和阻力位，并打分
    all_levels = []
    
    # 价格行为法
    for level in price_action_levels:
        if level['type'] == 'support' and level['price'] < current_price:
            all_levels.append({
                'price': level['price'],
                'type': 'support',
                'method': 'price_action',
                'strength': level['strength'],
                'score': level['touches'] * 3 + (level['volume'] / max([k['volume'] for k in klines[-100:]]) if klines else 1) * 2
            })
        elif level['type'] == 'resistance' and level['price'] > current_price:
            all_levels.append({
                'price': level['price'],
                'type': 'resistance',
                'method': 'price_action',
                'strength': level['strength'],
                'score': level['touches'] * 3 + (level['volume'] / max([k['volume'] for k in klines[-100:]]) if klines else 1) * 2
            })
    
    # 成交量分布
    if volume_profile:
        # POC
        if volume_profile['poc'] < current_price:
            all_levels.append({
                'price': volume_profile['poc'],
                'type': 'support',
                'method': 'volume_poc',
                'strength': 'very_strong',
                'score': 10
            })
        else:
            all_levels.append({
                'price': volume_profile['poc'],
                'type': 'resistance',
                'method': 'volume_poc',
                'strength': 'very_strong',
                'score': 10
            })
        
        # 价值区域边界
        if volume_profile['value_area_low'] < current_price:
            all_levels.append({
                'price': volume_profile['value_area_low'],
                'type': 'support',
                'method': 'volume_value_area',
                'strength': 'strong',
                'score': 8
            })
        if volume_profile['value_area_high'] > current_price:
            all_levels.append({
                'price': volume_profile['value_area_high'],
                'type': 'resistance',
                'method': 'volume_value_area',
                'strength': 'strong',
                'score': 8
            })
        
        # 价格上方的成交量密集区（如果POC和价值区域都在下方）
        if volume_profile.get('high_volume_bins'):
            for price, volume in volume_profile['high_volume_bins']:
                if price > current_price:
                    # 价格上方的成交量密集区，作为阻力位
                    # 根据成交量大小给分（相对于最大成交量）
                    max_vol = max([v for _, v in volume_profile['high_volume_bins']])
                    volume_score = (volume / max_vol) * 8  # 最高8分
                    all_levels.append({
                        'price': price,
                        'type': 'resistance',
                        'method': 'volume_dense',
                        'strength': 'strong' if volume_score >= 6 else 'moderate',
                        'score': volume_score
                    })
    
    # 枢轴点
    if pivot_points['s1'] < current_price:
        all_levels.append({'price': pivot_points['s1'], 'type': 'support', 'method': 'pivot_s1', 'score': 5})
    if pivot_points['s2'] < current_price:
        all_levels.append({'price': pivot_points['s2'], 'type': 'support', 'method': 'pivot_s2', 'score': 6})
    if pivot_points['s3'] < current_price:
        all_levels.append({'price': pivot_points['s3'], 'type': 'support', 'method': 'pivot_s3', 'score': 7})
    if pivot_points['r1'] > current_price:
        all_levels.append({'price': pivot_points['r1'], 'type': 'resistance', 'method': 'pivot_r1', 'score': 5})
    if pivot_points['r2'] > current_price:
        all_levels.append({'price': pivot_points['r2'], 'type': 'resistance', 'method': 'pivot_r2', 'score': 6})
    if pivot_points['r3'] > current_price:
        all_levels.append({'price': pivot_points['r3'], 'type': 'resistance', 'method': 'pivot_r3', 'score': 7})
    
    # 斐波那契回撤（重点关注618-786）
    for fib_name, fib_price in fib_levels.items():
        if '618' in fib_name or '786' in fib_name:
            if fib_price < current_price:
                all_levels.append({'price': fib_price, 'type': 'support', 'method': f'fib_{fib_name}', 'score': 7})
            elif fib_price > current_price:
                all_levels.append({'price': fib_price, 'type': 'resistance', 'method': f'fib_{fib_name}', 'score': 7})
    
    # 历史高低点
    if historical_levels['support']['price'] < current_price:
        all_levels.append({
            'price': historical_levels['support']['price'],
            'type': 'support',
            'method': 'historical',
            'strength': historical_levels['support']['touches'],
            'score': historical_levels['support']['touches'] * 2
        })
    if historical_levels['resistance']['price'] > current_price:
        all_levels.append({
            'price': historical_levels['resistance']['price'],
            'type': 'resistance',
            'method': 'historical',
            'strength': historical_levels['resistance']['touches'],
            'score': historical_levels['resistance']['touches'] * 2
        })
    
    # EMA144/169（Vegas通道）
    if ema_144 and ema_144 < current_price:
        all_levels.append({'price': ema_144, 'type': 'support', 'method': 'ema144', 'score': 8})
    if ema_169 and ema_169 < current_price:
        all_levels.append({'price': ema_169, 'type': 'support', 'method': 'ema169', 'score': 7})
    if ema_144 and ema_144 > current_price:
        all_levels.append({'price': ema_144, 'type': 'resistance', 'method': 'ema144', 'score': 8})
    if ema_169 and ema_169 > current_price:
        all_levels.append({'price': ema_169, 'type': 'resistance', 'method': 'ema169', 'score': 7})
    
    # VWAP
    if vwap:
        if vwap < current_price:
            all_levels.append({'price': vwap, 'type': 'support', 'method': 'vwap', 'score': 6})
        else:
            all_levels.append({'price': vwap, 'type': 'resistance', 'method': 'vwap', 'score': 6})
    
    # 合并相近的级别（容差1%）
    tolerance = current_price * 0.01
    merged_levels = []
    used_prices = set()
    
    for level in sorted(all_levels, key=lambda x: x['score'], reverse=True):
        price = level['price']
        merged = False
        
        for used_price in used_prices:
            if abs(price - used_price) <= tolerance:
                # 找到相近的级别，合并（取分数更高的）
                for merged_level in merged_levels:
                    if abs(merged_level['price'] - used_price) <= tolerance:
                        if level['score'] > merged_level.get('score', 0):
                            merged_level['price'] = (merged_level['price'] + price) / 2  # 取平均
                            merged_level['score'] = level['score']
                            merged_level['methods'] = merged_level.get('methods', []) + [level['method']]
                        else:
                            merged_level['methods'] = merged_level.get('methods', []) + [level['method']]
                        merged = True
                        break
        
        if not merged:
            level['methods'] = [level['method']]
            merged_levels.append(level)
            used_prices.add(price)
    
    # 分离支撑和阻力
    support_levels = sorted([l for l in merged_levels if l['type'] == 'support'], key=lambda x: x['price'], reverse=True)
    resistance_levels = sorted([l for l in merged_levels if l['type'] == 'resistance'], key=lambda x: x['price'])
    
    # 只保留最强的几个
    results['support_levels'] = support_levels[:5]
    results['resistance_levels'] = resistance_levels[:5]
    
    return results

