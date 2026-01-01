#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的De.交易系统分析模块
整合核心理念：量能分析、区间识别、入场模型标注
"""

from typing import List, Dict, Optional, Tuple
import sys


def analyze_volume_profile(klines: List[Dict], num_bins: int = 30) -> Dict:
    """
    分析成交量分布（Volume Profile）
    识别量能大的位置（真正的支撑阻力）
    
    Returns:
        {
            'high_volume_zones': [(price, volume), ...],  # 高量区域
            'low_volume_zones': [(price, volume), ...],   # 低量区域
            'poc': float,  # Point of Control (成交量最大的价格)
            'va_high': float,  # Value Area High
            'va_low': float   # Value Area Low
        }
    """
    if not klines or len(klines) < 10:
        return {}
    
    # 计算价格区间
    all_prices = []
    for k in klines:
        all_prices.extend([k['high'], k['low'], k['close']])
    
    price_min = min(all_prices)
    price_max = max(all_prices)
    price_range = price_max - price_min
    
    if price_range == 0:
        return {}
    
    # 创建价格档位
    bin_size = price_range / num_bins
    bins = {}
    
    # 分配成交量和价格到各个档位
    for k in klines:
        typical_price = (k['high'] + k['low'] + k['close']) / 3
        volume = k['volume']
        
        # 确定这个K线属于哪个价格档位
        bin_index = int((typical_price - price_min) / bin_size)
        bin_index = max(0, min(num_bins - 1, bin_index))
        bin_price = price_min + bin_index * bin_size
        
        if bin_price not in bins:
            bins[bin_price] = 0
        bins[bin_price] += volume
    
    # 计算统计值
    volumes = list(bins.values())
    if not volumes:
        return {}
    
    avg_volume = sum(volumes) / len(volumes)
    max_volume = max(volumes)
    
    # 找到POC (Point of Control - 成交量最大的价格)
    poc_price = max(bins.items(), key=lambda x: x[1])[0]
    
    # 识别高量区域（量能大的位置，真正的支撑阻力）
    high_volume_threshold = avg_volume * 1.5
    high_volume_zones = [(price, vol) for price, vol in bins.items() 
                         if vol > high_volume_threshold]
    high_volume_zones.sort(key=lambda x: x[1], reverse=True)
    
    # 识别低量区域（流动性稀疏区）
    low_volume_threshold = avg_volume * 0.5
    low_volume_zones = [(price, vol) for price, vol in bins.items() 
                        if vol < low_volume_threshold]
    
    # 计算Value Area（包含70%成交量的价格区间）
    sorted_bins = sorted(bins.items(), key=lambda x: x[1], reverse=True)
    total_volume = sum(volumes)
    value_area_volume = total_volume * 0.7
    
    accumulated_volume = 0
    value_area_prices = []
    for price, vol in sorted_bins:
        accumulated_volume += vol
        value_area_prices.append(price)
        if accumulated_volume >= value_area_volume:
            break
    
    va_high = max(value_area_prices) if value_area_prices else None
    va_low = min(value_area_prices) if value_area_prices else None
    
    return {
        'high_volume_zones': high_volume_zones,
        'low_volume_zones': low_volume_zones,
        'poc': poc_price,
        'va_high': va_high,
        'va_low': va_low,
        'bins': bins
    }


def identify_consolidation_ranges(klines: List[Dict], lookback: int = 50, 
                                  min_touches: int = 3) -> List[Dict]:
    """
    识别区间（流动性密集区域）
    做区间其实就是一个密集，每个流动性都是分区间的
    
    Returns:
        [{
            'range_low': float,
            'range_high': float,
            'touches': int,  # 价格触及该区间的次数
            'volume_profile': dict,  # 该区间的量能分布
            'strength': str  # 'strong'/'medium'/'weak'
        }, ...]
    """
    if not klines or len(klines) < lookback:
        return []
    
    recent_klines = klines[-lookback:]
    
    # 找到价格密集区域（区间）
    prices = []
    for k in recent_klines:
        prices.extend([k['high'], k['low'], k['close']])
    
    if not prices:
        return []
    
    price_min = min(prices)
    price_max = max(prices)
    price_range = price_max - price_min
    
    if price_range == 0:
        return []
    
    # 使用滑动窗口识别区间
    ranges = []
    window_size = price_range * 0.1  # 区间宽度为价格范围的10%
    
    # 检查多个可能的区间
    test_points = []
    step = price_range / 20
    for i in range(20):
        test_price = price_min + i * step
        test_points.append(test_price)
    
    for test_price in test_points:
        range_low = test_price - window_size / 2
        range_high = test_price + window_size / 2
        
        # 计算价格触及该区间的次数
        touches = 0
        range_volumes = []
        for k in recent_klines:
            if (range_low <= k['high'] <= range_high or 
                range_low <= k['low'] <= range_high or
                (k['low'] <= range_low and k['high'] >= range_high)):
                touches += 1
                range_volumes.append(k['volume'])
        
        if touches >= min_touches:
            # 分析该区间的量能
            avg_volume = sum(range_volumes) / len(range_volumes) if range_volumes else 0
            
            # 计算强度（基于触及次数和量能）
            strength = 'strong' if touches >= 5 and avg_volume > 0 else 'medium' if touches >= 3 else 'weak'
            
            ranges.append({
                'range_low': range_low,
                'range_high': range_high,
                'range_center': (range_low + range_high) / 2,
                'touches': touches,
                'avg_volume': avg_volume,
                'strength': strength
            })
    
    # 合并重叠的区间
    merged_ranges = []
    ranges.sort(key=lambda x: x['range_low'])
    
    for current_range in ranges:
        if not merged_ranges:
            merged_ranges.append(current_range)
        else:
            last_range = merged_ranges[-1]
            # 如果区间重叠，合并
            if current_range['range_low'] <= last_range['range_high']:
                last_range['range_high'] = max(last_range['range_high'], current_range['range_high'])
                last_range['touches'] = max(last_range['touches'], current_range['touches'])
                last_range['strength'] = 'strong' if last_range['touches'] >= 5 else last_range['strength']
            else:
                merged_ranges.append(current_range)
    
    return merged_ranges


def enhance_support_resistance_with_volume(sr_levels: Dict, volume_profile: Dict, 
                                           current_price: float) -> Dict:
    """
    用量能分析增强支撑阻力识别
    量能大的那个位置才是真正的支撑阻力
    
    Args:
        sr_levels: 原有的支撑阻力位 {'support': [...], 'resistance': [...]}
        volume_profile: 量能分布分析结果
        current_price: 当前价格
    
    Returns:
        增强后的支撑阻力，包含量能信息
    """
    enhanced_sr = {
        'support': [],
        'resistance': [],
        'high_volume_support': [],  # 量能大的支撑位（真正的支撑）
        'high_volume_resistance': [],  # 量能大的阻力位（真正的阻力）
        'low_volume_support': [],  # 量能小的支撑位
        'low_volume_resistance': []  # 量能小的阻力位
    }
    
    if not volume_profile:
        return enhanced_sr
    
    high_volume_zones = volume_profile.get('high_volume_zones', [])
    low_volume_zones = volume_profile.get('low_volume_zones', [])
    
    # 创建量能区域的价格集合
    high_volume_prices = set([price for price, _ in high_volume_zones])
    low_volume_prices = set([price for price, _ in low_volume_zones])
    
    # 处理支撑位
    for support in sr_levels.get('support', []):
        if support > current_price:
            continue
        
        # 检查是否在量能大的区域
        is_high_volume = any(abs(support - hv_price) / current_price < 0.01 
                            for hv_price in high_volume_prices)
        is_low_volume = any(abs(support - lv_price) / current_price < 0.01 
                           for lv_price in low_volume_prices)
        
        enhanced_sr['support'].append(support)
        
        if is_high_volume:
            enhanced_sr['high_volume_support'].append(support)
        elif is_low_volume:
            enhanced_sr['low_volume_support'].append(support)
    
    # 处理阻力位
    for resistance in sr_levels.get('resistance', []):
        if resistance < current_price:
            continue
        
        # 检查是否在量能大的区域
        is_high_volume = any(abs(resistance - hv_price) / current_price < 0.01 
                            for hv_price in high_volume_prices)
        is_low_volume = any(abs(resistance - lv_price) / current_price < 0.01 
                           for lv_price in low_volume_prices)
        
        enhanced_sr['resistance'].append(resistance)
        
        if is_high_volume:
            enhanced_sr['high_volume_resistance'].append(resistance)
        elif is_low_volume:
            enhanced_sr['low_volume_resistance'].append(resistance)
    
    return enhanced_sr


def identify_interval_breakout_opportunities(klines: List[Dict], 
                                             consolidation_ranges: List[Dict],
                                             current_price: float) -> List[Dict]:
    """
    识别区间突破机会
    做好区间突破推止盈，大概率能拿到大收获
    
    Returns:
        [{
            'type': 'long' or 'short',
            'range': {...},  # 区间信息
            'breakout_price': float,
            'target': float,  # 突破后的目标位
            'entry_model': str,
            'reason': str
        }, ...]
    """
    opportunities = []
    
    for range_info in consolidation_ranges:
        range_low = range_info['range_low']
        range_high = range_info['range_high']
        range_center = range_info['range_center']
        range_size = range_high - range_low
        
        # 向上突破
        if current_price > range_high * 1.002:  # 突破上沿（允许0.2%容差）
            # 突破后推止盈：目标位 = 突破价格 + 区间大小 * 倍数
            target_1 = current_price + range_size * 0.618  # 0.618倍
            target_2 = current_price + range_size * 1.0    # 1倍
            target_3 = current_price + range_size * 1.618  # 1.618倍
            
            opportunities.append({
                'type': 'long',
                'range': range_info,
                'breakout_price': range_high,
                'target_1': target_1,
                'target_2': target_2,
                'target_3': target_3,
                'entry_model': '区间突破',
                'reason': f'价格突破区间上沿({range_high:.0f})，区间大小{range_size:.0f}，推止盈目标{target_1:.0f}/{target_2:.0f}/{target_3:.0f}'
            })
        
        # 向下突破
        elif current_price < range_low * 0.998:  # 突破下沿（允许0.2%容差）
            # 突破后推止盈
            target_1 = current_price - range_size * 0.618
            target_2 = current_price - range_size * 1.0
            target_3 = current_price - range_size * 1.618
            
            opportunities.append({
                'type': 'short',
                'range': range_info,
                'breakout_price': range_low,
                'target_1': target_1,
                'target_2': target_2,
                'target_3': target_3,
                'entry_model': '区间突破',
                'reason': f'价格突破区间下沿({range_low:.0f})，区间大小{range_size:.0f}，推止盈目标{target_1:.0f}/{target_2:.0f}/{target_3:.0f}'
            })
    
    return opportunities




