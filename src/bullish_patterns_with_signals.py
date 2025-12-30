#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看涨图表形态识别模块（带交易信号）
基于"8种常见看涨图表形态"实现形态识别，包含明确的买入点和止损点
包含：旗形、三角旗、对称三角形、衡量上涨、杯柄形态、上升三角形、上升贝壳、上升三连谷
"""

import sys
from typing import Dict, List, Optional, Tuple

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class BullishPatternsWithSignals:
    """看涨图表形态识别器（带交易信号）"""
    
    def __init__(self):
        """初始化看涨形态识别器"""
        pass
    
    def detect_all_bullish_patterns(self, klines: List[Dict]) -> Dict:
        """
        检测所有看涨图表形态（带交易信号）
        
        Args:
            klines: K线数据列表
        
        Returns:
            {
                'patterns': [...],  # 检测到的形态列表（包含买入点和止损点）
                'bullish_strength': float,  # 看涨强度 (0-100)
                'patterns_details': {...}  # 详细信息
            }
        """
        if not klines or len(klines) < 20:
            return {
                'patterns': [],
                'bullish_strength': 0.0,
                'patterns_details': {}
            }
        
        patterns = []
        pattern_count = 0
        patterns_details = {}
        
        # 1. 旗形 (Flag Pattern)
        flag_pattern = self.detect_flag_pattern_with_signals(klines)
        if flag_pattern['detected']:
            patterns.append(flag_pattern['signal'])
            pattern_count += 1
            patterns_details['flag'] = flag_pattern
        
        # 2. 三角旗 (Pennant Pattern)
        pennant_pattern = self.detect_pennant_pattern_with_signals(klines)
        if pennant_pattern['detected']:
            patterns.append(pennant_pattern['signal'])
            pattern_count += 1
            patterns_details['pennant'] = pennant_pattern
        
        # 3. 对称三角形 (Symmetrical Triangle)
        symmetrical_triangle = self.detect_symmetrical_triangle_with_signals(klines)
        if symmetrical_triangle['detected']:
            patterns.append(symmetrical_triangle['signal'])
            pattern_count += 1
            patterns_details['symmetrical_triangle'] = symmetrical_triangle
        
        # 4. 衡量上涨 (Measured Move Up)
        measured_move = self.detect_measured_move_up_with_signals(klines)
        if measured_move['detected']:
            patterns.append(measured_move['signal'])
            pattern_count += 1
            patterns_details['measured_move'] = measured_move
        
        # 5. 杯柄形态 (Cup and Handle Pattern)
        cup_handle = self.detect_cup_handle_with_signals(klines)
        if cup_handle['detected']:
            patterns.append(cup_handle['signal'])
            pattern_count += 1
            patterns_details['cup_handle'] = cup_handle
        
        # 6. 上升三角形 (Ascending Triangle)
        ascending_triangle = self.detect_ascending_triangle_with_signals(klines)
        if ascending_triangle['detected']:
            patterns.append(ascending_triangle['signal'])
            pattern_count += 1
            patterns_details['ascending_triangle'] = ascending_triangle
        
        # 7. 上升贝壳 (Rising Scallop)
        rising_scallop = self.detect_rising_scallop_with_signals(klines)
        if rising_scallop['detected']:
            patterns.append(rising_scallop['signal'])
            pattern_count += 1
            patterns_details['rising_scallop'] = rising_scallop
        
        # 8. 上升三连谷 (Three Rising Valleys)
        three_rising_valleys = self.detect_three_rising_valleys_with_signals(klines)
        if three_rising_valleys['detected']:
            patterns.append(three_rising_valleys['signal'])
            pattern_count += 1
            patterns_details['three_rising_valleys'] = three_rising_valleys
        
        # 计算看涨强度（基于形态数量）
        bullish_strength = min((pattern_count / 8.0) * 100, 100.0)
        
        return {
            'patterns': patterns,
            'bullish_strength': bullish_strength,
            'pattern_count': pattern_count,
            'patterns_details': patterns_details
        }
    
    def detect_flag_pattern_with_signals(self, klines: List[Dict]) -> Dict:
        """
        1. 检测旗形 (Flag Pattern)
        
        特征：
        - 强上涨（旗杆）
        - 下降通道整理（旗面）
        - 买入点：突破旗面上沿
        - 止损点：旗面下沿下方
        """
        if len(klines) < 30:
            return {'detected': False}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        mid_point = len(recent) // 2
        
        # 前半部分：强上涨（旗杆）
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_rise = (pole_end - pole_start) / pole_start
        
        if pole_rise < 0.05:
            return {'detected': False}
        
        # 后半部分：下降通道（旗面）
        flag_highs = highs[mid_point:]
        flag_lows = lows[mid_point:]
        flag_closes = closes[mid_point:]
        
        # 检查是否是下降通道
        flag_top = max(flag_highs)
        flag_bottom = min(flag_lows)
        
        # 检查高点是否下降，低点是否也下降（形成下降通道）
        flag_start_high = flag_highs[0] if flag_highs else 0
        flag_end_high = flag_highs[-1] if len(flag_highs) > 1 else flag_highs[0] if flag_highs else 0
        flag_start_low = flag_lows[0] if flag_lows else 0
        flag_end_low = flag_lows[-1] if len(flag_lows) > 1 else flag_lows[0] if flag_lows else 0
        
        if flag_end_high >= flag_start_high * 0.98 or flag_end_low >= flag_start_low * 0.98:
            return {'detected': False}
        
        current_price = closes[-1]
        
        # 买入点：突破旗面上沿
        buy_point = flag_top * 1.002
        
        # 止损点：旗面下沿下方
        stop_loss = flag_bottom * 0.998
        
        # 如果价格接近或突破买入点
        if current_price > flag_top * 0.98:
            return {
                'detected': True,
                'signal': {
                    'name': '旗形',
                    'type': 'bullish_pattern',
                    'strength': 75.0,
                    'entry': buy_point,
                    'stop_loss': stop_loss,
                    'description': f"识别到旗形形态，买入点${buy_point:,.0f}，止损点${stop_loss:,.0f}"
                },
                'flag_top': flag_top,
                'flag_bottom': flag_bottom,
                'pole_height': pole_end - pole_start
            }
        
        return {'detected': False}
    
    def detect_pennant_pattern_with_signals(self, klines: List[Dict]) -> Dict:
        """
        2. 检测三角旗 (Pennant Pattern)
        
        特征：
        - 强上涨（旗杆）
        - 对称三角形整理（三角旗）
        - 买入点：突破三角旗上沿
        - 止损点：三角旗下沿下方
        """
        if len(klines) < 30:
            return {'detected': False}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        mid_point = len(recent) // 2
        
        # 前半部分：强上涨（旗杆）
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_rise = (pole_end - pole_start) / pole_start
        
        if pole_rise < 0.05:
            return {'detected': False}
        
        # 后半部分：对称三角形（三角旗）
        pennant_highs = highs[mid_point:]
        pennant_lows = lows[mid_point:]
        
        # 检查是否形成对称三角形（高点下降，低点上升）
        third = len(pennant_highs) // 3
        first_third_high = max(pennant_highs[:third]) if third > 0 and pennant_highs else 0
        third_third_high = max(pennant_highs[2*third:]) if len(pennant_highs) > 2*third and pennant_highs else 0
        
        first_third_low = min(pennant_lows[:third]) if third > 0 and pennant_lows else 0
        third_third_low = min(pennant_lows[2*third:]) if len(pennant_lows) > 2*third and pennant_lows else 0
        
        # 高点下降，低点上升
        if third_third_high >= first_third_high * 0.98 or third_third_low <= first_third_low * 1.02:
            return {'detected': False}
        
        pennant_top = max(pennant_highs)
        pennant_bottom = min(pennant_lows)
        current_price = closes[-1]
        
        # 买入点：突破三角旗上沿
        buy_point = pennant_top * 1.002
        
        # 止损点：三角旗下沿下方
        stop_loss = pennant_bottom * 0.998
        
        if current_price > pennant_top * 0.98:
            return {
                'detected': True,
                'signal': {
                    'name': '三角旗',
                    'type': 'bullish_pattern',
                    'strength': 75.0,
                    'entry': buy_point,
                    'stop_loss': stop_loss,
                    'description': f"识别到三角旗形态，买入点${buy_point:,.0f}，止损点${stop_loss:,.0f}"
                },
                'pennant_top': pennant_top,
                'pennant_bottom': pennant_bottom
            }
        
        return {'detected': False}
    
    def detect_symmetrical_triangle_with_signals(self, klines: List[Dict]) -> Dict:
        """
        3. 检测对称三角形 (Symmetrical Triangle)
        
        特征：
        - 高点下降，低点上升（收敛）
        - 买入点：突破上沿
        - 止损点：下沿下方
        """
        if len(klines) < 30:
            return {'detected': False}
        
        recent = klines[-40:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        # 检查是否形成对称三角形
        third = len(recent) // 3
        first_third_high = max(highs[:third]) if third > 0 else 0
        third_third_high = max(highs[2*third:]) if len(highs) > 2*third else 0
        
        first_third_low = min(lows[:third]) if third > 0 else 0
        third_third_low = min(lows[2*third:]) if len(lows) > 2*third else 0
        
        # 高点下降，低点上升
        if third_third_high >= first_third_high * 0.98 or third_third_low <= first_third_low * 1.02:
            return {'detected': False}
        
        triangle_top = max(highs[-10:])  # 最近的上沿
        triangle_bottom = min(lows[-10:])  # 最近的下沿
        current_price = closes[-1]
        
        # 买入点：突破上沿
        buy_point = triangle_top * 1.002
        
        # 止损点：下沿下方
        stop_loss = triangle_bottom * 0.998
        
        if current_price > triangle_top * 0.98:
            return {
                'detected': True,
                'signal': {
                    'name': '对称三角形',
                    'type': 'bullish_pattern',
                    'strength': 70.0,
                    'entry': buy_point,
                    'stop_loss': stop_loss,
                    'description': f"识别到对称三角形形态，买入点${buy_point:,.0f}，止损点${stop_loss:,.0f}"
                },
                'triangle_top': triangle_top,
                'triangle_bottom': triangle_bottom
            }
        
        return {'detected': False}
    
    def detect_measured_move_up_with_signals(self, klines: List[Dict]) -> Dict:
        """
        4. 检测衡量上涨 (Measured Move Up)
        
        特征：
        - 初始上涨
        - 上升通道整理（向上倾斜的旗面）
        - 买入点：突破整理通道上沿
        - 止损点：整理通道下沿下方
        """
        if len(klines) < 30:
            return {'detected': False}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        mid_point = len(recent) // 2
        
        # 前半部分：初始上涨
        first_start = closes[0]
        first_end = closes[mid_point]
        first_rise = (first_end - first_start) / first_start
        
        if first_rise < 0.05:
            return {'detected': False}
        
        # 后半部分：上升通道整理
        channel_highs = highs[mid_point:]
        channel_lows = lows[mid_point:]
        
        # 检查是否是上升通道（高点上升，低点也上升）
        channel_start_high = channel_highs[0] if channel_highs else 0
        channel_end_high = channel_highs[-1] if len(channel_highs) > 1 else channel_highs[0] if channel_highs else 0
        channel_start_low = channel_lows[0] if channel_lows else 0
        channel_end_low = channel_lows[-1] if len(channel_lows) > 1 else channel_lows[0] if channel_lows else 0
        
        if channel_end_high <= channel_start_high * 1.01 or channel_end_low <= channel_start_low * 1.01:
            return {'detected': False}
        
        channel_top = max(channel_highs)
        channel_bottom = min(channel_lows)
        current_price = closes[-1]
        
        # 买入点：突破通道上沿
        buy_point = channel_top * 1.002
        
        # 止损点：通道下沿下方
        stop_loss = channel_bottom * 0.998
        
        if current_price > channel_top * 0.98:
            return {
                'detected': True,
                'signal': {
                    'name': '衡量上涨',
                    'type': 'bullish_pattern',
                    'strength': 75.0,
                    'entry': buy_point,
                    'stop_loss': stop_loss,
                    'description': f"识别到衡量上涨形态，买入点${buy_point:,.0f}，止损点${stop_loss:,.0f}"
                },
                'channel_top': channel_top,
                'channel_bottom': channel_bottom
            }
        
        return {'detected': False}
    
    def detect_cup_handle_with_signals(self, klines: List[Dict]) -> Dict:
        """
        5. 检测杯柄形态 (Cup and Handle Pattern)
        
        特征：
        - U型杯（圆底）
        - 小的下降整理（柄）
        - 买入点：突破杯沿和柄的顶部
        - 止损点：柄的最低价下方
        """
        if len(klines) < 50:
            return {'detected': False}
        
        recent = klines[-60:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        # 找到杯形（前半部分，U型）
        cup_length = len(recent) * 2 // 3
        cup_klines = recent[:cup_length]
        handle_klines = recent[cup_length:]
        
        if len(cup_klines) < 20 or len(handle_klines) < 10:
            return {'detected': False}
        
        # 检查杯形（U型底部）
        cup_start = closes[0]
        cup_mid_low = min([k['low'] for k in cup_klines[cup_length//4:cup_length*3//4]])
        cup_end = closes[cup_length-1]
        
        # 杯形应该是先下降后上升
        cup_mid_idx = cup_length // 2
        cup_mid_price = closes[cup_mid_idx] if cup_mid_idx < len(closes) else cup_start
        cup_bottom = min([k['low'] for k in cup_klines])
        
        # 检查是否有U型（中间低，两端高）
        if cup_mid_price > cup_start * 0.95 or cup_mid_price > cup_end * 0.95:
            return {'detected': False}
        
        # 检查柄（小的下降整理）
        handle_highs = [k['high'] for k in handle_klines]
        handle_lows = [k['low'] for k in handle_klines]
        handle_bottom = min(handle_lows)
        handle_top = max(handle_highs)
        
        # 柄应该比杯小
        cup_rim = max(cup_start, cup_end)
        if handle_top > cup_rim * 1.02:
            return {'detected': False}
        
        current_price = closes[-1]
        
        # 买入点：突破杯沿和柄的顶部
        buy_point = max(cup_rim, handle_top) * 1.002
        
        # 止损点：柄的最低价下方
        stop_loss = handle_bottom * 0.998
        
        if current_price > buy_point * 0.98:
            return {
                'detected': True,
                'signal': {
                    'name': '杯柄形态',
                    'type': 'bullish_pattern',
                    'strength': 80.0,
                    'entry': buy_point,
                    'stop_loss': stop_loss,
                    'description': f"识别到杯柄形态，买入点${buy_point:,.0f}，止损点${stop_loss:,.0f}"
                },
                'cup_rim': cup_rim,
                'handle_bottom': handle_bottom,
                'handle_top': handle_top
            }
        
        return {'detected': False}
    
    def detect_ascending_triangle_with_signals(self, klines: List[Dict]) -> Dict:
        """
        6. 检测上升三角形 (Ascending Triangle)
        
        特征：
        - 水平阻力线
        - 上升支撑线
        - 买入点：突破水平阻力线
        - 止损点：上升支撑线下方
        """
        if len(klines) < 30:
            return {'detected': False}
        
        recent = klines[-40:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        # 检查是否有水平阻力线
        recent_highs = highs[-15:]
        max_high = max(recent_highs)
        min_high = min(recent_highs)
        high_flatness = (max_high - min_high) / max_high
        
        if high_flatness > 0.02:  # 高点差异应该小于2%
            return {'detected': False}
        
        # 检查是否有上升支撑线
        recent_lows = lows[-15:]
        first_low = recent_lows[0] if recent_lows else 0
        last_low = recent_lows[-1] if len(recent_lows) > 1 else recent_lows[0] if recent_lows else 0
        
        if last_low <= first_low * 1.01:  # 低点应该上升
            return {'detected': False}
        
        resistance = max_high
        support = min(recent_lows)
        current_price = closes[-1]
        
        # 买入点：突破水平阻力线
        buy_point = resistance * 1.002
        
        # 止损点：上升支撑线下方
        stop_loss = support * 0.998
        
        if current_price > resistance * 0.98:
            return {
                'detected': True,
                'signal': {
                    'name': '上升三角形',
                    'type': 'bullish_pattern',
                    'strength': 75.0,
                    'entry': buy_point,
                    'stop_loss': stop_loss,
                    'description': f"识别到上升三角形形态，买入点${buy_point:,.0f}，止损点${stop_loss:,.0f}"
                },
                'resistance': resistance,
                'support': support
            }
        
        return {'detected': False}
    
    def detect_rising_scallop_with_signals(self, klines: List[Dict]) -> Dict:
        """
        7. 检测上升贝壳 (Rising Scallop)
        
        特征：
        - U型价格走势（贝壳形）
        - 买入点：突破U型最高点
        - 止损点：U型最低点下方
        """
        if len(klines) < 30:
            return {'detected': False}
        
        recent = klines[-40:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        # 找到U型（贝壳形）
        mid_point = len(recent) // 2
        
        # 检查是否是U型（中间低，两端高）
        start_price = closes[0]
        mid_price = closes[mid_point]
        end_price = closes[-1]
        bottom_price = min(lows)
        
        # 中间应该比两端低
        if mid_price > start_price * 0.95 or mid_price > end_price * 0.95:
            return {'detected': False}
        
        # U型最高点（两端较高的那个）
        scallop_top = max(start_price, end_price)
        scallop_bottom = bottom_price
        current_price = closes[-1]
        
        # 买入点：突破U型最高点
        buy_point = scallop_top * 1.002
        
        # 止损点：U型最低点下方
        stop_loss = scallop_bottom * 0.998
        
        if current_price > scallop_top * 0.98:
            return {
                'detected': True,
                'signal': {
                    'name': '上升贝壳',
                    'type': 'bullish_pattern',
                    'strength': 70.0,
                    'entry': buy_point,
                    'stop_loss': stop_loss,
                    'description': f"识别到上升贝壳形态，买入点${buy_point:,.0f}，止损点${stop_loss:,.0f}"
                },
                'scallop_top': scallop_top,
                'scallop_bottom': scallop_bottom
            }
        
        return {'detected': False}
    
    def detect_three_rising_valleys_with_signals(self, klines: List[Dict]) -> Dict:
        """
        8. 检测上升三连谷 (Three Rising Valleys)
        
        特征：
        - 三个逐步升高的低点（谷1、谷2、谷3）
        - 买入点：突破连接峰值的阻力线
        - 止损点：第三个谷下方
        """
        if len(klines) < 40:
            return {'detected': False}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        # 寻找三个低点
        # 简化：找到最近三个显著的低点
        valleys = []
        for i in range(2, len(recent) - 2):
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and \
               lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                valleys.append((i, lows[i]))
        
        if len(valleys) < 3:
            return {'detected': False}
        
        # 取最近三个
        valleys = valleys[-3:]
        
        valley1_price = valleys[0][1]
        valley2_price = valleys[1][1]
        valley3_price = valleys[2][1]
        
        # 检查是否逐步升高
        if valley2_price <= valley1_price * 1.01 or valley3_price <= valley2_price * 1.01:
            return {'detected': False}
        
        # 找到连接峰值的阻力线（简化：使用最近的高点）
        resistance = max(highs[valleys[0][0]:valleys[2][0]+1])
        valley3_idx = valleys[2][0]
        valley3_low = valleys[2][1]
        current_price = closes[-1]
        
        # 买入点：突破阻力线
        buy_point = resistance * 1.002
        
        # 止损点：第三个谷下方
        stop_loss = valley3_low * 0.998
        
        if current_price > resistance * 0.98:
            return {
                'detected': True,
                'signal': {
                    'name': '上升三连谷',
                    'type': 'bullish_pattern',
                    'strength': 75.0,
                    'entry': buy_point,
                    'stop_loss': stop_loss,
                    'description': f"识别到上升三连谷形态，买入点${buy_point:,.0f}，止损点${stop_loss:,.0f}"
                },
                'resistance': resistance,
                'valley3_low': valley3_low
            }
        
        return {'detected': False}




