#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主力洗盘场景识别模块
基于"六种最常见的主力洗盘场景"实现洗盘后的做多机会识别
包含：箱体震荡、三角形震荡、五浪调整、旗形下跌、缩量圆弧、旗形上涨
"""

import sys
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class MainForceWashoutDetector:
    """主力洗盘场景识别器"""
    
    def __init__(self):
        """初始化主力洗盘场景识别器"""
        pass
    
    def detect_all_washout_scenarios(self, klines: List[Dict]) -> Dict:
        """
        检测所有主力洗盘场景
        
        Args:
            klines: K线数据列表
        
        Returns:
            {
                'scenarios': [...],  # 检测到的洗盘场景列表
                'long_opportunity_strength': float,  # 做多机会强度 (0-100)
                'scenarios_details': {...}  # 详细信息
            }
        """
        if not klines or len(klines) < 30:
            return {
                'scenarios': [],
                'long_opportunity_strength': 0.0,
                'scenarios_details': {}
            }
        
        scenarios = []
        scenario_count = 0
        scenarios_details = {}
        
        # 1. 箱体震荡 (Box Oscillation)
        box_oscillation = self.detect_box_oscillation(klines)
        if box_oscillation['detected']:
            scenarios.append({
                'name': '箱体震荡',
                'type': 'long_opportunity',
                'strength': box_oscillation['strength'],
                'description': f"识别到箱体震荡，调整幅度{box_oscillation['adjustment_pct']:.1f}%，未超过上涨的1/3，突破后做多"
            })
            scenario_count += 1
            scenarios_details['box_oscillation'] = box_oscillation
        
        # 2. 三角形震荡 (Triangle Oscillation)
        triangle_oscillation = self.detect_triangle_oscillation(klines)
        if triangle_oscillation['detected']:
            scenarios.append({
                'name': '三角形震荡',
                'type': 'long_opportunity',
                'strength': triangle_oscillation['strength'],
                'description': f"识别到收敛三角形，成交量缩量，突破上沿后做多"
            })
            scenario_count += 1
            scenarios_details['triangle_oscillation'] = triangle_oscillation
        
        # 3. 五浪调整 (Five-Wave Adjustment)
        five_wave = self.detect_five_wave_adjustment(klines)
        if five_wave['detected']:
            scenarios.append({
                'name': '五浪调整',
                'type': 'long_opportunity',
                'strength': five_wave['strength'],
                'description': f"识别到五浪调整，调整幅度{five_wave['adjustment_pct']:.1f}%，约上涨的1/2，破位下降趋势线后做多"
            })
            scenario_count += 1
            scenarios_details['five_wave'] = five_wave
        
        # 4. 旗形下跌 (Falling Flag)
        falling_flag = self.detect_falling_flag(klines)
        if falling_flag['detected']:
            scenarios.append({
                'name': '旗形下跌',
                'type': 'long_opportunity',
                'strength': falling_flag['strength'],
                'description': f"识别到旗形下跌，调整缩量，调整幅度{falling_flag['adjustment_pct']:.1f}%，突破上沿后做多"
            })
            scenario_count += 1
            scenarios_details['falling_flag'] = falling_flag
        
        # 5. 缩量圆弧 (Volume Shrinking Arc)
        shrinking_arc = self.detect_shrinking_arc(klines)
        if shrinking_arc['detected']:
            scenarios.append({
                'name': '缩量圆弧',
                'type': 'long_opportunity',
                'strength': shrinking_arc['strength'],
                'description': f"识别到缩量圆弧形态，成交量持续缩量，放量后做多"
            })
            scenario_count += 1
            scenarios_details['shrinking_arc'] = shrinking_arc
        
        # 6. 旗形上涨 (Rising Flag)
        rising_flag = self.detect_rising_flag(klines)
        if rising_flag['detected']:
            scenarios.append({
                'name': '旗形上涨',
                'type': 'long_opportunity',
                'strength': rising_flag['strength'],
                'description': f"识别到旗形上涨，上涨途中温和放量，主力边拉升边洗盘，突破后加速"
            })
            scenario_count += 1
            scenarios_details['rising_flag'] = rising_flag
        
        # 计算做多机会强度（基于场景数量）
        long_opportunity_strength = min((scenario_count / 6.0) * 100, 100.0)
        
        return {
            'scenarios': scenarios,
            'long_opportunity_strength': long_opportunity_strength,
            'scenario_count': scenario_count,
            'scenarios_details': scenarios_details
        }
    
    def detect_box_oscillation(self, klines: List[Dict]) -> Dict:
        """
        1. 检测箱体震荡 (Box Oscillation)
        
        特征：
        - 维持矩形箱体震荡
        - 调整幅度不会超过上涨的1/3
        - 两波上涨1:1等高
        """
        if len(klines) < 40:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-60:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        # 找到上涨阶段（前半部分）
        mid_point = len(recent) // 2
        first_half = recent[:mid_point]
        second_half = recent[mid_point:]
        
        # 前半部分应该有上涨
        first_start_price = first_half[0]['close']
        first_end_price = first_half[-1]['close']
        first_rise = (first_end_price - first_start_price) / first_start_price
        
        if first_rise < 0.05:  # 至少5%涨幅
            return {'detected': False, 'strength': 0}
        
        # 后半部分应该是箱体震荡
        second_highs = [k['high'] for k in second_half]
        second_lows = [k['low'] for k in second_half]
        box_top = max(second_highs)
        box_bottom = min(second_lows)
        box_range = box_top - box_bottom
        box_range_pct = box_range / box_top
        
        # 检查是否是矩形（高点相近，低点相近）
        high_std = sum([abs(h - box_top) for h in second_highs]) / len(second_highs) / box_top
        low_std = sum([abs(l - box_bottom) for l in second_lows]) / len(second_lows) / box_bottom
        
        if high_std > 0.02 or low_std > 0.02:  # 允许2%误差
            return {'detected': False, 'strength': 0}
        
        # 调整幅度不应该超过上涨的1/3
        adjustment_pct = box_range / first_end_price
        if adjustment_pct > first_rise / 3:
            return {'detected': False, 'strength': 0}
        
        # 如果当前价格接近或突破箱体上沿
        current_price = closes[-1]
        if current_price > box_top * 0.98:
            strength = min(70.0 + (1 - adjustment_pct / (first_rise / 3)) * 30, 100.0)
            return {
                'detected': True,
                'strength': strength,
                'box_top': box_top,
                'box_bottom': box_bottom,
                'adjustment_pct': adjustment_pct * 100,
                'first_rise_pct': first_rise * 100,
                'entry': box_top * 1.002  # 突破上沿入场
            }
        
        return {'detected': False, 'strength': 0}
    
    def detect_triangle_oscillation(self, klines: List[Dict]) -> Dict:
        """
        2. 检测三角形震荡 (Triangle Oscillation)
        
        特征：
        - 形态呈现三角形（收敛三角形）
        - 成交量不断缩量，三角形角的时候最低
        - 开始变盘，上涨必须放量
        - 两波上涨1:1等高
        """
        if len(klines) < 40:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-50:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        volumes = [k['volume'] for k in recent]
        
        # 将数据分为三段
        third = len(recent) // 3
        first_third_highs = highs[:third]
        second_third_highs = highs[third:2*third]
        third_third_highs = highs[2*third:]
        
        first_third_lows = lows[:third]
        second_third_lows = lows[third:2*third]
        third_third_lows = lows[2*third:]
        
        first_high = max(first_third_highs) if first_third_highs else 0
        second_high = max(second_third_highs) if second_third_highs else 0
        third_high = max(third_third_highs) if third_third_highs else 0
        
        first_low = min(first_third_lows) if first_third_lows else 0
        second_low = min(second_third_lows) if second_third_lows else 0
        third_low = min(third_third_lows) if third_third_lows else 0
        
        # 检查是否形成收敛三角形（高点下降，低点上升）
        high_converging = first_high > second_high > third_high
        low_diverging = first_low < second_low < third_low
        
        if not (high_converging and low_diverging):
            return {'detected': False, 'strength': 0}
        
        # 检查成交量是否缩量
        first_volume = sum(volumes[:third]) / third if third > 0 else 0
        second_volume = sum(volumes[third:2*third]) / third if third > 0 else 0
        third_volume = sum(volumes[2*third:]) / len(volumes[2*third:]) if len(volumes[2*third:]) > 0 else 0
        
        volume_decreasing = third_volume < second_volume < first_volume
        
        if not volume_decreasing:
            return {'detected': False, 'strength': 0}
        
        # 检查最近是否有放量突破
        recent_volume = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
        volume_expanding = recent_volume > third_volume * 1.2
        
        current_price = closes[-1]
        triangle_top = (first_high + second_high) / 2  # 简化的三角形上沿
        
        if current_price > triangle_top * 0.98 and volume_expanding:
            return {
                'detected': True,
                'strength': 75.0,
                'triangle_top': triangle_top,
                'entry': triangle_top * 1.002
            }
        
        return {'detected': False, 'strength': 0}
    
    def detect_five_wave_adjustment(self, klines: List[Dict]) -> Dict:
        """
        3. 检测五浪调整 (Five-Wave Adjustment)
        
        特征：
        - 5段走势，波浪式下跌
        - 破位下降趋势线必须放量
        - 调整一般是上涨的1/2
        - 两波上涨1:1等高
        """
        if len(klines) < 50:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-70:]
        closes = [k['close'] for k in recent]
        volumes = [k['volume'] for k in recent]
        
        # 找到上涨阶段（前30根K线）
        first_30 = closes[:30]
        first_start = first_30[0]
        first_end = first_30[-1]
        first_rise = (first_end - first_start) / first_start
        
        if first_rise < 0.05:
            return {'detected': False, 'strength': 0}
        
        # 找到调整阶段（后40根K线）
        last_40 = closes[30:]
        adjustment_start = last_40[0]
        adjustment_low = min(last_40)
        adjustment_pct = (adjustment_start - adjustment_low) / adjustment_start
        
        # 调整应该是上涨的1/2（允许一定误差）
        expected_adjustment = first_rise / 2
        if abs(adjustment_pct - expected_adjustment) / expected_adjustment > 0.3:
            return {'detected': False, 'strength': 0}
        
        # 简化：检查是否有5个明显的波动
        # 实际应该识别具体的5浪结构，这里简化处理
        current_price = closes[-1]
        recent_high = max(closes[-10:])
        
        # 检查是否突破下降趋势线（简化为突破最近高点）
        if current_price > adjustment_start * 0.98:
            # 检查是否有放量
            recent_volume = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
            earlier_volume = sum(volumes[-20:-5]) / 15 if len(volumes) >= 20 else 0
            
            if recent_volume > earlier_volume * 1.2:
                return {
                    'detected': True,
                    'strength': 70.0,
                    'adjustment_pct': adjustment_pct * 100,
                    'entry': adjustment_start * 1.002
                }
        
        return {'detected': False, 'strength': 0}
    
    def detect_falling_flag(self, klines: List[Dict]) -> Dict:
        """
        4. 检测旗形下跌 (Falling Flag)
        
        特征：
        - 旗子旗杆，调整缩量
        - 破位下降趋势线须放量
        - 调整一般是上涨的1/2
        - 两波上涨1:1等高
        """
        if len(klines) < 40:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        volumes = [k['volume'] for k in recent]
        
        mid_point = len(recent) // 2
        
        # 前半部分：强上涨（旗杆）
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_rise = (pole_end - pole_start) / pole_start
        
        if pole_rise < 0.05:
            return {'detected': False, 'strength': 0}
        
        # 后半部分：下降通道（旗面）
        flag_highs = highs[mid_point:]
        flag_lows = lows[mid_point:]
        flag_closes = closes[mid_point:]
        
        # 检查是否是下降通道
        flag_high_trend = (max(flag_highs) - min(flag_highs)) / max(flag_highs)
        flag_low_trend = (max(flag_lows) - min(flag_lows)) / max(flag_lows)
        
        # 旗面应该是一个下降的通道
        flag_start_price = flag_closes[0]
        flag_low_price = min(flag_lows)
        adjustment_pct = (flag_start_price - flag_low_price) / flag_start_price
        
        # 调整应该是上涨的1/2
        if abs(adjustment_pct - pole_rise / 2) / (pole_rise / 2) > 0.3:
            return {'detected': False, 'strength': 0}
        
        # 检查成交量是否缩量
        pole_volume = sum(volumes[:mid_point]) / mid_point if mid_point > 0 else 0
        flag_volume = sum(volumes[mid_point:]) / len(volumes[mid_point:]) if len(volumes[mid_point:]) > 0 else 0
        
        if flag_volume > pole_volume * 0.9:  # 应该明显缩量
            return {'detected': False, 'strength': 0}
        
        # 检查是否突破上沿
        current_price = closes[-1]
        flag_top = max(flag_highs)
        
        if current_price > flag_top * 0.98:
            # 检查是否有放量
            recent_volume = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
            if recent_volume > flag_volume * 1.2:
                return {
                    'detected': True,
                    'strength': 75.0,
                    'adjustment_pct': adjustment_pct * 100,
                    'flag_top': flag_top,
                    'entry': flag_top * 1.002
                }
        
        return {'detected': False, 'strength': 0}
    
    def detect_shrinking_arc(self, klines: List[Dict]) -> Dict:
        """
        5. 检测缩量圆弧 (Volume Shrinking Arc)
        
        特征：
        - 圆弧型态调整，成交量缩量
        - 放量开始进场
        - 两波上涨1:1等高
        """
        if len(klines) < 40:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        volumes = [k['volume'] for k in recent]
        
        # 检查价格是否形成圆弧底部
        mid_point = len(recent) // 2
        
        first_half = closes[:mid_point]
        second_half = closes[mid_point:]
        
        # 前半部分应该下降，后半部分应该上升（形成圆弧）
        first_trend = (first_half[-1] - first_half[0]) / first_half[0]
        second_trend = (second_half[-1] - second_half[0]) / second_half[0]
        
        if first_trend > -0.02 or second_trend < 0.02:  # 应该有明显的圆弧
            return {'detected': False, 'strength': 0}
        
        # 检查成交量是否缩量
        first_volume = sum(volumes[:mid_point]) / mid_point if mid_point > 0 else 0
        mid_volume = sum(volumes[mid_point//2:mid_point+mid_point//2]) / (mid_point) if mid_point > 0 else 0
        second_volume = sum(volumes[mid_point:]) / len(volumes[mid_point:]) if len(volumes[mid_point:]) > 0 else 0
        
        # 成交量应该在中间最低（圆弧底部）
        if mid_volume > first_volume * 0.9 or mid_volume > second_volume * 0.9:
            return {'detected': False, 'strength': 0}
        
        # 检查最近是否有放量
        recent_volume = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
        if recent_volume > mid_volume * 1.3:
            return {
                'detected': True,
                'strength': 70.0,
                'arc_bottom': min(closes),
                'entry': closes[-1] * 1.002
            }
        
        return {'detected': False, 'strength': 0}
    
    def detect_rising_flag(self, klines: List[Dict]) -> Dict:
        """
        6. 检测旗形上涨 (Rising Flag)
        
        特征：
        - 旗子旗杆，上涨途中温和放量
        - 主力边拉升边洗盘
        - 后市加速
        - 两波上涨1:1等高
        """
        if len(klines) < 40:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        volumes = [k['volume'] for k in recent]
        
        mid_point = len(recent) // 2
        
        # 前半部分：强上涨（旗杆）
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_rise = (pole_end - pole_start) / pole_start
        
        if pole_rise < 0.05:
            return {'detected': False, 'strength': 0}
        
        # 后半部分：上升通道（旗面）
        flag_highs = highs[mid_point:]
        flag_lows = lows[mid_point:]
        flag_closes = closes[mid_point:]
        
        # 检查是否是上升通道
        flag_start_price = flag_closes[0]
        flag_end_price = flag_closes[-1]
        flag_rise = (flag_end_price - flag_start_price) / flag_start_price
        
        # 旗面应该是温和上升
        if flag_rise < 0.01 or flag_rise > 0.05:
            return {'detected': False, 'strength': 0}
        
        # 检查成交量（温和放量）
        pole_volume = sum(volumes[:mid_point]) / mid_point if mid_point > 0 else 0
        flag_volume = sum(volumes[mid_point:]) / len(volumes[mid_point:]) if len(volumes[mid_point:]) > 0 else 0
        
        # 旗面成交量应该比旗杆略高（温和放量）
        if flag_volume < pole_volume * 1.1 or flag_volume > pole_volume * 1.5:
            return {'detected': False, 'strength': 0}
        
        # 检查是否突破上沿
        current_price = closes[-1]
        flag_top = max(flag_highs)
        
        if current_price > flag_top * 0.98:
            return {
                'detected': True,
                'strength': 80.0,
                'flag_top': flag_top,
                'entry': flag_top * 1.002
            }
        
        return {'detected': False, 'strength': 0}




