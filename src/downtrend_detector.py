#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下降趋势识别模块
基于"9种经典形态识别下降趋势"实现下降趋势的识别
包含：高低点、斐波纳奇、支撑阻力、通道、旗形、成交量、移动平均线、均线交叉、艾略特波浪
"""

import sys
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class DowntrendDetector:
    """下降趋势识别器"""
    
    def __init__(self):
        """初始化下降趋势识别器"""
        pass
    
    def detect_all_downtrend_signals(self, klines: List[Dict]) -> Dict:
        """
        检测所有下降趋势信号
        
        Args:
            klines: K线数据列表
        
        Returns:
            {
                'signals': [...],  # 检测到的下降趋势信号列表
                'downtrend_strength': float,  # 下降趋势强度 (0-100)
                'signals_details': {...}  # 详细信息
            }
        """
        if not klines or len(klines) < 20:
            return {
                'signals': [],
                'downtrend_strength': 0.0,
                'signals_details': {}
            }
        
        signals = []
        signal_count = 0
        signals_details = {}
        
        # 1. 至高点&至低点 (Lower Highs & Lower Lows)
        lh_ll = self.detect_lower_highs_lower_lows(klines)
        if lh_ll['detected']:
            signals.append({
                'name': '至高点&至低点',
                'type': 'downtrend',
                'strength': lh_ll['strength'],
                'description': f"识别到下降趋势：{lh_ll['lh_count']}个更低高点，{lh_ll['ll_count']}个更低低点"
            })
            signal_count += 1
            signals_details['lower_highs_lower_lows'] = lh_ll
        
        # 2. 斐波纳奇位 (Fibonacci Resistance)
        fib_resistance = self.detect_fibonacci_resistance(klines)
        if fib_resistance['detected']:
            signals.append({
                'name': '斐波纳奇位',
                'type': 'downtrend',
                'strength': fib_resistance['strength'],
                'description': f"价格在斐波纳奇{fib_resistance['level']}位受阻，下降趋势延续"
            })
            signal_count += 1
            signals_details['fibonacci_resistance'] = fib_resistance
        
        # 3. 维持水准 (Support Turned Resistance)
        support_resistance = self.detect_support_turned_resistance(klines)
        if support_resistance['detected']:
            signals.append({
                'name': '维持水准',
                'type': 'downtrend',
                'strength': support_resistance['strength'],
                'description': f"价格在${support_resistance['level']:,.0f}（原支撑位）受阻，转为阻力"
            })
            signal_count += 1
            signals_details['support_turned_resistance'] = support_resistance
        
        # 4. 河型模式 (Downtrend Channel)
        channel = self.detect_downtrend_channel(klines)
        if channel['detected']:
            signals.append({
                'name': '河型模式',
                'type': 'downtrend',
                'strength': channel['strength'],
                'description': f"价格在下降通道内运行，通道上沿${channel['upper']:,.0f}，下沿${channel['lower']:,.0f}"
            })
            signal_count += 1
            signals_details['downtrend_channel'] = channel
        
        # 5. 旗形模式 (Bear Flag)
        bear_flag = self.detect_bear_flag_pattern(klines)
        if bear_flag['detected']:
            signals.append({
                'name': '旗形模式',
                'type': 'downtrend',
                'strength': bear_flag['strength'],
                'description': f"识别到熊旗形态，下降趋势中的整理，可能延续下跌"
            })
            signal_count += 1
            signals_details['bear_flag'] = bear_flag
        
        # 6. 交易量 (Volume Confirmation)
        volume_confirmation = self.detect_volume_confirmation(klines)
        if volume_confirmation['detected']:
            signals.append({
                'name': '交易量',
                'type': 'downtrend',
                'strength': volume_confirmation['strength'],
                'description': f"下跌时成交量放大，确认下降趋势强度"
            })
            signal_count += 1
            signals_details['volume_confirmation'] = volume_confirmation
        
        # 7. 移动平均线 (Price Below Moving Average)
        ma_resistance = self.detect_ma_resistance(klines)
        if ma_resistance['detected']:
            signals.append({
                'name': '移动平均线',
                'type': 'downtrend',
                'strength': ma_resistance['strength'],
                'description': f"价格持续在移动平均线（{ma_resistance['ma_period']}周期）下方，均线作为阻力"
            })
            signal_count += 1
            signals_details['ma_resistance'] = ma_resistance
        
        # 8. 移动平均线交叉 (Death Cross)
        ma_crossover = self.detect_death_cross(klines)
        if ma_crossover['detected']:
            signals.append({
                'name': '移动平均线交叉',
                'type': 'downtrend',
                'strength': ma_crossover['strength'],
                'description': f"死叉确认：快线（{ma_crossover['fast_period']}）下穿慢线（{ma_crossover['slow_period']}）"
            })
            signal_count += 1
            signals_details['death_cross'] = ma_crossover
        
        # 9. 艾略特波段 (Elliott Wave Downtrend)
        elliott_wave = self.detect_elliott_wave_downtrend(klines)
        if elliott_wave['detected']:
            signals.append({
                'name': '艾略特波段',
                'type': 'downtrend',
                'strength': elliott_wave['strength'],
                'description': f"识别到下降5浪结构，当前在浪{elliott_wave['current_wave']}"
            })
            signal_count += 1
            signals_details['elliott_wave'] = elliott_wave
        
        # 计算下降趋势强度（基于信号数量）
        downtrend_strength = min((signal_count / 9.0) * 100, 100.0)
        
        return {
            'signals': signals,
            'downtrend_strength': downtrend_strength,
            'signal_count': signal_count,
            'signals_details': signals_details
        }
    
    def detect_lower_highs_lower_lows(self, klines: List[Dict]) -> Dict:
        """
        1. 检测至高点&至低点 (Lower Highs & Lower Lows)
        
        下降趋势特征：一系列更低的高点和更低的低点
        """
        if len(klines) < 20:
            return {'detected': False, 'strength': 0}
        
        # 寻找最近的高点和低点
        recent = klines[-30:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        # 找到局部高点和低点
        peaks = []
        troughs = []
        
        for i in range(2, len(recent) - 2):
            # 检查是否是局部高点
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and \
               highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                peaks.append((i, highs[i]))
            
            # 检查是否是局部低点
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                troughs.append((i, lows[i]))
        
        if len(peaks) < 2 or len(troughs) < 2:
            return {'detected': False, 'strength': 0}
        
        # 检查是否有更低的高点
        lh_count = 0
        for i in range(1, len(peaks)):
            if peaks[i][1] < peaks[i-1][1]:
                lh_count += 1
        
        # 检查是否有更低的低点
        ll_count = 0
        for i in range(1, len(troughs)):
            if troughs[i][1] < troughs[i-1][1]:
                ll_count += 1
        
        # 如果至少有2个更低的高点和2个更低的低点，确认下降趋势
        if lh_count >= 2 and ll_count >= 2:
            strength = min((lh_count + ll_count) / 4.0 * 50, 100.0)
            return {
                'detected': True,
                'strength': strength,
                'lh_count': lh_count,
                'll_count': ll_count,
                'peaks': peaks[-3:],
                'troughs': troughs[-3:]
            }
        
        return {'detected': False, 'strength': 0}
    
    def detect_fibonacci_resistance(self, klines: List[Dict]) -> Dict:
        """
        2. 检测斐波纳奇位阻力 (Fibonacci Resistance)
        
        价格反弹在斐波纳奇回撤位受阻，继续下跌
        """
        if len(klines) < 30:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-50:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        # 找到最近的高点和低点
        swing_high = max(highs[:30])  # 前30根K线的最高点
        swing_low = min(lows[30:]) if len(lows) > 30 else min(lows)  # 后20根K线的最低点
        
        if swing_high <= swing_low:
            return {'detected': False, 'strength': 0}
        
        range_size = swing_high - swing_low
        
        # 计算斐波纳奇回撤位（从高点到低点）
        fib_levels = {
            '0.236': swing_high - range_size * 0.236,
            '0.382': swing_high - range_size * 0.382,
            '0.5': swing_high - range_size * 0.5,
            '0.618': swing_high - range_size * 0.618,
            '0.786': swing_high - range_size * 0.786
        }
        
        current_price = closes[-1]
        
        # 检查价格是否在斐波纳奇位附近受阻
        for level_name, level_price in fib_levels.items():
            if abs(current_price - level_price) / level_price < 0.01:  # 1%误差
                # 检查价格是否从该位置下跌
                recent_prices = closes[-5:]
                if len(recent_prices) >= 3 and recent_prices[-1] < recent_prices[-3]:
                    return {
                        'detected': True,
                        'strength': 70.0,
                        'level': level_name,
                        'level_price': level_price,
                        'swing_high': swing_high,
                        'swing_low': swing_low
                    }
        
        return {'detected': False, 'strength': 0}
    
    def detect_support_turned_resistance(self, klines: List[Dict]) -> Dict:
        """
        3. 检测维持水准 (Support Turned Resistance)
        
        价格跌破支撑位后，该支撑位转为阻力位
        """
        if len(klines) < 40:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-50:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        # 找到历史支撑位（前30根K线的显著低点）
        historical_support = min(lows[:30])
        
        # 检查价格是否跌破支撑位
        if min(lows[30:]) < historical_support * 0.98:  # 至少下跌2%
            # 检查价格是否反弹至原支撑位受阻
            recent_high = max(highs[30:])
            current_price = closes[-1]
            
            # 如果价格接近原支撑位但无法突破
            if abs(recent_high - historical_support) / historical_support < 0.02 and \
               current_price < historical_support * 1.01:
                return {
                    'detected': True,
                    'strength': 75.0,
                    'level': historical_support,
                    'breakdown_price': min(lows[30:]),
                    'rejection_price': recent_high
                }
        
        return {'detected': False, 'strength': 0}
    
    def detect_downtrend_channel(self, klines: List[Dict]) -> Dict:
        """
        4. 检测河型模式 (Downtrend Channel)
        
        价格在下降通道内运行，上沿和下沿都向下倾斜
        """
        if len(klines) < 30:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-40:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        # 找到通道的上沿（高点连线）和下沿（低点连线）
        # 简化：检查高点是否下降，低点是否也下降
        
        mid_point = len(recent) // 2
        first_half_highs = highs[:mid_point]
        second_half_highs = highs[mid_point:]
        first_half_lows = lows[:mid_point]
        second_half_lows = lows[mid_point:]
        
        first_high = max(first_half_highs) if first_half_highs else 0
        second_high = max(second_half_highs) if second_half_highs else 0
        first_low = min(first_half_lows) if first_half_lows else 0
        second_low = min(second_half_lows) if second_half_lows else 0
        
        # 高点下降，低点也下降
        if second_high < first_high and second_low < first_low:
            channel_height = (first_high + second_high) / 2 - (first_low + second_low) / 2
            if channel_height > 0:
                return {
                    'detected': True,
                    'strength': 70.0,
                    'upper': (first_high + second_high) / 2,
                    'lower': (first_low + second_low) / 2,
                    'channel_height': channel_height
                }
        
        return {'detected': False, 'strength': 0}
    
    def detect_bear_flag_pattern(self, klines: List[Dict]) -> Dict:
        """
        5. 检测旗形模式 (Bear Flag)
        
        强下跌后的小幅整理，通常延续下跌
        """
        if len(klines) < 30:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-40:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        mid_point = len(recent) // 2
        
        # 前半部分：强下跌（旗杆）
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_downward = (pole_start - pole_end) / pole_start > 0.05  # 至少5%跌幅
        
        # 后半部分：小幅整理（旗面）
        flag_start = closes[mid_point]
        flag_end = closes[-1]
        flag_range = (max(highs[mid_point:]) - min(lows[mid_point:])) / flag_start
        flag_consolidation = flag_range < 0.03  # 3%以内整理
        
        if pole_downward and flag_consolidation:
            return {
                'detected': True,
                'strength': 70.0,
                'pole_height': pole_start - pole_end,
                'flag_high': max(highs[mid_point:]),
                'flag_low': min(lows[mid_point:])
            }
        
        return {'detected': False, 'strength': 0}
    
    def detect_volume_confirmation(self, klines: List[Dict]) -> Dict:
        """
        6. 检测交易量确认 (Volume Confirmation)
        
        下跌时成交量放大，确认下降趋势
        """
        if len(klines) < 30:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-30:]
        closes = [k['close'] for k in recent]
        volumes = [k['volume'] for k in recent]
        
        # 计算价格变化和成交量
        mid_point = len(recent) // 2
        
        first_half_prices = closes[:mid_point]
        second_half_prices = closes[mid_point:]
        first_half_volumes = volumes[:mid_point]
        second_half_volumes = volumes[mid_point:]
        
        price_change = (first_half_prices[0] - second_half_prices[-1]) / first_half_prices[0]
        avg_volume_first = sum(first_half_volumes) / len(first_half_volumes) if first_half_volumes else 0
        avg_volume_second = sum(second_half_volumes) / len(second_half_volumes) if second_half_volumes else 0
        
        # 如果价格下跌且成交量放大
        if price_change > 0.02 and avg_volume_second > avg_volume_first * 1.2:
            return {
                'detected': True,
                'strength': 65.0,
                'price_change_pct': price_change * 100,
                'volume_increase_pct': ((avg_volume_second - avg_volume_first) / avg_volume_first) * 100
            }
        
        return {'detected': False, 'strength': 0}
    
    def detect_ma_resistance(self, klines: List[Dict], ma_period: int = 20) -> Dict:
        """
        7. 检测移动平均线阻力 (Moving Average Resistance)
        
        价格持续在移动平均线下方，均线作为阻力
        """
        if len(klines) < ma_period * 2:
            return {'detected': False, 'strength': 0}
        
        closes = [k['close'] for k in klines]
        
        # 计算移动平均线
        ma_values = []
        for i in range(ma_period - 1, len(closes)):
            ma = sum(closes[i - ma_period + 1:i + 1]) / ma_period
            ma_values.append(ma)
        
        if len(ma_values) < 10:
            return {'detected': False, 'strength': 0}
        
        current_ma = ma_values[-1]
        current_price = closes[-1]
        
        # 检查最近10根K线是否都在均线下方
        recent_closes = closes[-10:]
        recent_ma_values = ma_values[-10:]
        
        below_ma_count = sum(1 for i in range(len(recent_closes)) 
                            if recent_closes[i] < recent_ma_values[i])
        
        if below_ma_count >= 8:  # 至少8根K线在均线下方
            # 计算价格与均线的距离
            distance_pct = (current_ma - current_price) / current_ma * 100
            strength = min(60.0 + distance_pct * 2, 100.0)
            
            return {
                'detected': True,
                'strength': strength,
                'ma_period': ma_period,
                'ma_value': current_ma,
                'current_price': current_price,
                'distance_pct': distance_pct,
                'below_ma_count': below_ma_count
            }
        
        return {'detected': False, 'strength': 0}
    
    def detect_death_cross(self, klines: List[Dict], fast_period: int = 20, slow_period: int = 50) -> Dict:
        """
        8. 检测移动平均线交叉 (Death Cross)
        
        快线下穿慢线，形成死叉
        """
        if len(klines) < slow_period * 2:
            return {'detected': False, 'strength': 0}
        
        closes = [k['close'] for k in klines]
        
        # 计算快线和慢线
        fast_ma = []
        slow_ma = []
        
        for i in range(slow_period - 1, len(closes)):
            if i >= fast_period - 1:
                fast = sum(closes[i - fast_period + 1:i + 1]) / fast_period
                fast_ma.append(fast)
            else:
                fast_ma.append(None)
            
            slow = sum(closes[i - slow_period + 1:i + 1]) / slow_period
            slow_ma.append(slow)
        
        if len(fast_ma) < 5 or len(slow_ma) < 5:
            return {'detected': False, 'strength': 0}
        
        # 检查是否有死叉（快线下穿慢线）
        for i in range(1, min(len(fast_ma), len(slow_ma))):
            if fast_ma[i] and fast_ma[i-1] and slow_ma[i] and slow_ma[i-1]:
                # 之前快线在慢线上方，现在在下方
                if fast_ma[i-1] > slow_ma[i-1] and fast_ma[i] < slow_ma[i]:
                    # 检查当前价格是否在两条均线下方
                    current_price = closes[i + slow_period - 1]
                    if current_price < fast_ma[i] and current_price < slow_ma[i]:
                        return {
                            'detected': True,
                            'strength': 80.0,
                            'fast_period': fast_period,
                            'slow_period': slow_period,
                            'fast_ma': fast_ma[i],
                            'slow_ma': slow_ma[i],
                            'cross_price': current_price
                        }
        
        return {'detected': False, 'strength': 0}
    
    def detect_elliott_wave_downtrend(self, klines: List[Dict]) -> Dict:
        """
        9. 检测艾略特波段下降趋势 (Elliott Wave Downtrend)
        
        识别下降5浪结构（简化实现）
        """
        if len(klines) < 50:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-60:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        # 简化实现：寻找5个明显的价格波动
        # 理想情况下应该是：1跌、2涨、3跌、4涨、5跌
        
        # 找到主要的波动点
        swings = []
        for i in range(5, len(recent) - 5):
            # 检查是否是显著的高点或低点
            if highs[i] == max(highs[i-5:i+6]):
                swings.append(('high', i, highs[i]))
            elif lows[i] == min(lows[i-5:i+6]):
                swings.append(('low', i, lows[i]))
        
        if len(swings) < 5:
            return {'detected': False, 'strength': 0}
        
        # 简化：检查是否有下降趋势的5浪特征
        # 1浪：下跌，2浪：反弹，3浪：下跌（最猛烈），4浪：反弹，5浪：下跌
        
        # 检查最近的波动是否呈现下降趋势
        recent_swings = swings[-5:]
        if len(recent_swings) >= 5:
            # 检查整体是否下降
            first_price = recent_swings[0][2]
            last_price = recent_swings[-1][2]
            
            if last_price < first_price:
                # 简化：如果有5个波动且整体下降，认为可能是5浪结构
                return {
                    'detected': True,
                    'strength': 60.0,  # 简化实现，置信度较低
                    'current_wave': 5,
                    'wave_swings': len(recent_swings)
                }
        
        return {'detected': False, 'strength': 0}




