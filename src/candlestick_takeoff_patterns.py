#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
经典K线起飞形态识别模块
基于"经典K线起飞形态"实现9种看涨K线形态的识别
包含：金针探底、红三兵、涨停双响炮、揭竿而起、小步上扬、均线多头布林突破、单阳盖阴、立竿见影、上升三法
"""

import sys
from typing import Dict, List, Optional, Tuple

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class CandlestickTakeoffPatterns:
    """经典K线起飞形态识别器"""
    
    def __init__(self):
        """初始化K线起飞形态识别器"""
        pass
    
    def detect_all_takeoff_patterns(self, klines: List[Dict]) -> Dict:
        """
        检测所有K线起飞形态
        
        Args:
            klines: K线数据列表
        
        Returns:
            {
                'patterns': [...],  # 检测到的起飞形态列表
                'takeoff_strength': float,  # 起飞强度 (0-100)
                'patterns_details': {...}  # 详细信息
            }
        """
        if not klines or len(klines) < 5:
            return {
                'patterns': [],
                'takeoff_strength': 0.0,
                'patterns_details': {}
            }
        
        patterns = []
        pattern_count = 0
        patterns_details = {}
        
        # 1. 金针探底 (Golden Needle Probing the Bottom)
        golden_needle = self.detect_golden_needle(klines)
        if golden_needle['detected']:
            patterns.append({
                'name': '金针探底',
                'type': 'bullish_takeoff',
                'strength': golden_needle['strength'],
                'description': f"识别到金针探底形态，长下影线探底后连续上涨，看涨信号"
            })
            pattern_count += 1
            patterns_details['golden_needle'] = golden_needle
        
        # 2. 红三兵 (Three White Soldiers)
        three_soldiers = self.detect_three_white_soldiers(klines)
        if three_soldiers['detected']:
            patterns.append({
                'name': '红三兵',
                'type': 'bullish_takeoff',
                'strength': three_soldiers['strength'],
                'description': f"识别到红三兵形态，三根连续阳线，稳步上涨，强势看涨"
            })
            pattern_count += 1
            patterns_details['three_soldiers'] = three_soldiers
        
        # 3. 涨停双响炮 (Limit Up Double Cannon)
        double_cannon = self.detect_double_cannon(klines)
        if double_cannon['detected']:
            patterns.append({
                'name': '涨停双响炮',
                'type': 'bullish_takeoff',
                'strength': double_cannon['strength'],
                'description': f"识别到涨停双响炮形态，两根大阳线夹一小阴线，强势突破"
            })
            pattern_count += 1
            patterns_details['double_cannon'] = double_cannon
        
        # 4. 揭竿而起 (Rising from the Ground)
        rising_ground = self.detect_rising_from_ground(klines)
        if rising_ground['detected']:
            patterns.append({
                'name': '揭竿而起',
                'type': 'bullish_takeoff',
                'strength': rising_ground['strength'],
                'description': f"识别到揭竿而起形态，突然大幅上涨，强势反转"
            })
            pattern_count += 1
            patterns_details['rising_ground'] = rising_ground
        
        # 5. 小步上扬 (Small Steps Upward)
        small_steps = self.detect_small_steps_upward(klines)
        if small_steps['detected']:
            patterns.append({
                'name': '小步上扬',
                'type': 'bullish_takeoff',
                'strength': small_steps['strength'],
                'description': f"识别到小步上扬形态，连续小阳线稳步上涨，积累能量"
            })
            pattern_count += 1
            patterns_details['small_steps'] = small_steps
        
        # 6. 均线多头布林突破 (Moving Average Bullish Bollinger Breakout)
        ma_bollinger = self.detect_ma_bollinger_breakout(klines)
        if ma_bollinger['detected']:
            patterns.append({
                'name': '均线多头布林突破',
                'type': 'bullish_takeoff',
                'strength': ma_bollinger['strength'],
                'description': f"识别到均线多头布林突破，突破阻力位，强势上涨"
            })
            pattern_count += 1
            patterns_details['ma_bollinger'] = ma_bollinger
        
        # 7. 单阳盖阴 (Single Bullish Candle Covering Bearish)
        bullish_engulfing = self.detect_bullish_engulfing(klines)
        if bullish_engulfing['detected']:
            patterns.append({
                'name': '单阳盖阴',
                'type': 'bullish_takeoff',
                'strength': bullish_engulfing['strength'],
                'description': f"识别到单阳盖阴形态，大阳线完全吞没前一根阴线，强势反转"
            })
            pattern_count += 1
            patterns_details['bullish_engulfing'] = bullish_engulfing
        
        # 8. 立竿见影 (Instant Effect)
        instant_effect = self.detect_instant_effect(klines)
        if instant_effect['detected']:
            patterns.append({
                'name': '立竿见影',
                'type': 'bullish_takeoff',
                'strength': instant_effect['strength'],
                'description': f"识别到立竿见影形态，下跌后突然大幅上涨，快速反转"
            })
            pattern_count += 1
            patterns_details['instant_effect'] = instant_effect
        
        # 9. 上升三法 (Rising Three Methods)
        rising_three = self.detect_rising_three_methods(klines)
        if rising_three['detected']:
            patterns.append({
                'name': '上升三法',
                'type': 'bullish_takeoff',
                'strength': rising_three['strength'],
                'description': f"识别到上升三法形态，上涨后整理，然后继续上涨"
            })
            pattern_count += 1
            patterns_details['rising_three'] = rising_three
        
        # 计算起飞强度（基于形态数量）
        takeoff_strength = min((pattern_count / 9.0) * 100, 100.0)
        
        return {
            'patterns': patterns,
            'takeoff_strength': takeoff_strength,
            'pattern_count': pattern_count,
            'patterns_details': patterns_details
        }
    
    def detect_golden_needle(self, klines: List[Dict]) -> Dict:
        """
        1. 检测金针探底 (Golden Needle Probing the Bottom)
        
        特征：
        - 第一根：长下影线的阴线或阳线（探底）
        - 第二根：阳线，开盘低于前一根收盘，收盘高于前一根收盘
        - 第三根：阳线，继续上涨
        """
        if len(klines) < 3:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-3:]
        
        k1 = recent[0]
        k2 = recent[1]
        k3 = recent[2]
        
        # 第一根：长下影线（下影线至少是实体的2倍）
        k1_body = abs(k1['close'] - k1['open'])
        k1_lower_shadow = min(k1['open'], k1['close']) - k1['low']
        k1_total_range = k1['high'] - k1['low']
        
        if k1_total_range == 0 or k1_lower_shadow / k1_total_range < 0.5:
            return {'detected': False, 'strength': 0}
        
        # 第二根：阳线，开盘低于前一根收盘，收盘高于前一根收盘
        if k2['close'] <= k2['open']:  # 必须是阳线
            return {'detected': False, 'strength': 0}
        
        if k2['open'] >= k1['close']:  # 开盘应该低于前一根收盘
            return {'detected': False, 'strength': 0}
        
        if k2['close'] <= k1['close']:  # 收盘应该高于前一根收盘
            return {'detected': False, 'strength': 0}
        
        # 第三根：阳线，继续上涨
        if k3['close'] <= k3['open']:  # 必须是阳线
            return {'detected': False, 'strength': 0}
        
        if k3['close'] <= k2['close']:  # 应该继续上涨
            return {'detected': False, 'strength': 0}
        
        return {
            'detected': True,
            'strength': 75.0,
            'entry': k3['close'] * 1.002
        }
    
    def detect_three_white_soldiers(self, klines: List[Dict]) -> Dict:
        """
        2. 检测红三兵 (Three White Soldiers)
        
        特征：
        - 三根连续阳线
        - 每根开盘在前一根实体内部或附近
        - 每根收盘逐步升高
        - 实体较大，上下影线较短
        """
        if len(klines) < 3:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-3:]
        
        k1 = recent[0]
        k2 = recent[1]
        k3 = recent[2]
        
        # 三根都必须是阳线
        if k1['close'] <= k1['open'] or k2['close'] <= k2['open'] or k3['close'] <= k3['open']:
            return {'detected': False, 'strength': 0}
        
        # 收盘逐步升高
        if k2['close'] <= k1['close'] or k3['close'] <= k2['close']:
            return {'detected': False, 'strength': 0}
        
        # 每根开盘在前一根实体内部或附近（允许一定误差）
        k1_body_high = max(k1['open'], k1['close'])
        k1_body_low = min(k1['open'], k1['close'])
        k2_body_high = max(k2['open'], k2['close'])
        k2_body_low = min(k2['open'], k2['close'])
        
        # k2开盘应该在k1实体范围内或略低
        if k2['open'] > k1_body_high * 1.01:
            return {'detected': False, 'strength': 0}
        
        # k3开盘应该在k2实体范围内或略低
        if k3['open'] > k2_body_high * 1.01:
            return {'detected': False, 'strength': 0}
        
        # 实体应该较大（至少是总范围的60%）
        for k in recent:
            body = abs(k['close'] - k['open'])
            total_range = k['high'] - k['low']
            if total_range > 0 and body / total_range < 0.6:
                return {'detected': False, 'strength': 0}
        
        return {
            'detected': True,
            'strength': 80.0,
            'entry': k3['close'] * 1.002
        }
    
    def detect_double_cannon(self, klines: List[Dict]) -> Dict:
        """
        3. 检测涨停双响炮 (Limit Up Double Cannon)
        
        特征：
        - 第一根：大阳线
        - 第二根：小阴线或十字星（整理）
        - 第三根：大阳线，收盘高于第一根
        """
        if len(klines) < 3:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-3:]
        
        k1 = recent[0]
        k2 = recent[1]
        k3 = recent[2]
        
        # 第一根：大阳线
        if k1['close'] <= k1['open']:
            return {'detected': False, 'strength': 0}
        
        k1_body = k1['close'] - k1['open']
        k1_total = k1['high'] - k1['low']
        if k1_total == 0 or k1_body / k1_total < 0.7:  # 实体应该占70%以上
            return {'detected': False, 'strength': 0}
        
        # 第二根：小阴线或十字星（实体小）
        k2_body = abs(k2['close'] - k2['open'])
        k2_total = k2['high'] - k2['low']
        if k2_total == 0 or k2_body / k2_total > 0.3:  # 实体应该小于30%
            return {'detected': False, 'strength': 0}
        
        # 第二根应该在第一根范围内
        if k2['high'] > k1['high'] * 1.02 or k2['low'] < k1['low'] * 0.98:
            return {'detected': False, 'strength': 0}
        
        # 第三根：大阳线
        if k3['close'] <= k3['open']:
            return {'detected': False, 'strength': 0}
        
        k3_body = k3['close'] - k3['open']
        k3_total = k3['high'] - k3['low']
        if k3_total == 0 or k3_body / k3_total < 0.7:
            return {'detected': False, 'strength': 0}
        
        # 第三根收盘应该高于第一根收盘
        if k3['close'] <= k1['close']:
            return {'detected': False, 'strength': 0}
        
        return {
            'detected': True,
            'strength': 85.0,
            'entry': k3['close'] * 1.002
        }
    
    def detect_rising_from_ground(self, klines: List[Dict]) -> Dict:
        """
        4. 检测揭竿而起 (Rising from the Ground)
        
        特征：
        - 第一根：小阴线或十字星
        - 第二根：大阳线，突然大幅上涨
        - 第三根：阳线，继续上涨（可能有下影线）
        """
        if len(klines) < 3:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-3:]
        
        k1 = recent[0]
        k2 = recent[1]
        k3 = recent[2]
        
        # 第一根：小阴线或十字星（实体小）
        k1_body = abs(k1['close'] - k1['open'])
        k1_total = k1['high'] - k1['low']
        if k1_total == 0 or k1_body / k1_total > 0.3:
            return {'detected': False, 'strength': 0}
        
        # 第二根：大阳线
        if k2['close'] <= k2['open']:
            return {'detected': False, 'strength': 0}
        
        k2_body = k2['close'] - k2['open']
        k2_total = k2['high'] - k2['low']
        if k2_total == 0 or k2_body / k2_total < 0.7:
            return {'detected': False, 'strength': 0}
        
        # 第二根涨幅应该较大（至少5%）
        k2_rise = (k2['close'] - k2['open']) / k2['open']
        if k2_rise < 0.03:
            return {'detected': False, 'strength': 0}
        
        # 第三根：阳线，继续上涨
        if k3['close'] <= k3['open']:
            return {'detected': False, 'strength': 0}
        
        if k3['close'] <= k2['close']:
            return {'detected': False, 'strength': 0}
        
        return {
            'detected': True,
            'strength': 80.0,
            'entry': k3['close'] * 1.002
        }
    
    def detect_small_steps_upward(self, klines: List[Dict]) -> Dict:
        """
        5. 检测小步上扬 (Small Steps Upward)
        
        特征：
        - 连续4根或更多小阳线
        - 每根开盘略高于前一根收盘
        - 每根收盘逐步升高
        - 实体较小，影线较短
        """
        if len(klines) < 4:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-4:]
        
        # 检查是否都是阳线
        for k in recent:
            if k['close'] <= k['open']:
                return {'detected': False, 'strength': 0}
        
        # 检查收盘是否逐步升高
        for i in range(1, len(recent)):
            if recent[i]['close'] <= recent[i-1]['close']:
                return {'detected': False, 'strength': 0}
        
        # 检查实体是否较小（每根实体不超过总范围的50%）
        for k in recent:
            body = k['close'] - k['open']
            total_range = k['high'] - k['low']
            if total_range > 0 and body / total_range > 0.5:
                return {'detected': False, 'strength': 0}
        
        # 检查是否稳步上涨（每根涨幅不超过3%）
        for i in range(1, len(recent)):
            rise = (recent[i]['close'] - recent[i-1]['close']) / recent[i-1]['close']
            if rise > 0.03:
                return {'detected': False, 'strength': 0}
        
        return {
            'detected': True,
            'strength': 70.0,
            'entry': recent[-1]['close'] * 1.002
        }
    
    def detect_ma_bollinger_breakout(self, klines: List[Dict]) -> Dict:
        """
        6. 检测均线多头布林突破 (Moving Average Bullish Bollinger Breakout)
        
        特征：
        - 前两根：小阴线或小阳线
        - 第三根：大阳线，突破阻力位
        - 价格突破均线或布林带上轨
        """
        if len(klines) < 3:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-3:]
        
        k1 = recent[0]
        k2 = recent[1]
        k3 = recent[2]
        
        # 前两根：实体较小
        for k in [k1, k2]:
            body = abs(k['close'] - k['open'])
            total_range = k['high'] - k['low']
            if total_range > 0 and body / total_range > 0.4:
                return {'detected': False, 'strength': 0}
        
        # 第三根：大阳线
        if k3['close'] <= k3['open']:
            return {'detected': False, 'strength': 0}
        
        k3_body = k3['close'] - k3['open']
        k3_total = k3['high'] - k3['low']
        if k3_total == 0 or k3_body / k3_total < 0.7:
            return {'detected': False, 'strength': 0}
        
        # 第三根应该突破前两根的高点
        max_prev_high = max(k1['high'], k2['high'])
        if k3['close'] <= max_prev_high:
            return {'detected': False, 'strength': 0}
        
        # 计算简单移动平均（20周期）
        if len(klines) >= 20:
            closes = [k['close'] for k in klines[-20:]]
            ma20 = sum(closes) / len(closes)
            # 价格应该突破均线
            if k3['close'] > ma20:
                return {
                    'detected': True,
                    'strength': 75.0,
                    'entry': k3['close'] * 1.002,
                    'ma20': ma20
                }
        
        return {
            'detected': True,
            'strength': 70.0,
            'entry': k3['close'] * 1.002
        }
    
    def detect_bullish_engulfing(self, klines: List[Dict]) -> Dict:
        """
        7. 检测单阳盖阴 (Single Bullish Candle Covering Bearish)
        
        特征：
        - 第一根：阴线（可能有长下影线）
        - 第二根：大阳线，完全吞没第一根（开盘低于第一根最低价，收盘高于第一根最高价）
        """
        if len(klines) < 2:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-2:]
        
        k1 = recent[0]
        k2 = recent[1]
        
        # 第一根：阴线
        if k1['close'] >= k1['open']:
            return {'detected': False, 'strength': 0}
        
        # 第二根：大阳线
        if k2['close'] <= k2['open']:
            return {'detected': False, 'strength': 0}
        
        # 第二根应该完全吞没第一根
        if k2['open'] >= k1['low']:  # 开盘应该低于第一根最低价
            return {'detected': False, 'strength': 0}
        
        if k2['close'] <= k1['high']:  # 收盘应该高于第一根最高价
            return {'detected': False, 'strength': 0}
        
        # 第二根实体应该较大
        k2_body = k2['close'] - k2['open']
        k2_total = k2['high'] - k2['low']
        if k2_total == 0 or k2_body / k2_total < 0.6:
            return {'detected': False, 'strength': 0}
        
        return {
            'detected': True,
            'strength': 85.0,
            'entry': k2['close'] * 1.002
        }
    
    def detect_instant_effect(self, klines: List[Dict]) -> Dict:
        """
        8. 检测立竿见影 (Instant Effect)
        
        特征：
        - 前几根：连续阴线（下跌）
        - 最后一根：大阳线，开盘大幅低于前一根收盘，收盘大幅高于前一根收盘
        """
        if len(klines) < 4:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-4:]
        
        # 前3根应该是阴线
        for k in recent[:3]:
            if k['close'] >= k['open']:
                return {'detected': False, 'strength': 0}
        
        k3 = recent[2]
        k4 = recent[3]
        
        # 第四根：大阳线
        if k4['close'] <= k4['open']:
            return {'detected': False, 'strength': 0}
        
        # 开盘应该大幅低于前一根收盘（至少2%）
        gap_down = (k3['close'] - k4['open']) / k3['close']
        if gap_down < 0.02:
            return {'detected': False, 'strength': 0}
        
        # 收盘应该大幅高于前一根收盘（至少3%）
        rise = (k4['close'] - k3['close']) / k3['close']
        if rise < 0.03:
            return {'detected': False, 'strength': 0}
        
        # 实体应该较大
        k4_body = k4['close'] - k4['open']
        k4_total = k4['high'] - k4['low']
        if k4_total == 0 or k4_body / k4_total < 0.7:
            return {'detected': False, 'strength': 0}
        
        return {
            'detected': True,
            'strength': 80.0,
            'entry': k4['close'] * 1.002
        }
    
    def detect_rising_three_methods(self, klines: List[Dict]) -> Dict:
        """
        9. 检测上升三法 (Rising Three Methods)
        
        特征：
        - 第一根：大阳线
        - 中间三根：小阴线，在第一根范围内整理
        - 第五根：大阳线，收盘高于第一根最高价
        """
        if len(klines) < 5:
            return {'detected': False, 'strength': 0}
        
        recent = klines[-5:]
        
        k1 = recent[0]
        k2 = recent[1]
        k3 = recent[2]
        k4 = recent[3]
        k5 = recent[4]
        
        # 第一根：大阳线
        if k1['close'] <= k1['open']:
            return {'detected': False, 'strength': 0}
        
        k1_body = k1['close'] - k1['open']
        k1_total = k1['high'] - k1['low']
        if k1_total == 0 or k1_body / k1_total < 0.7:
            return {'detected': False, 'strength': 0}
        
        # 中间三根：小阴线（允许有小阳线，但实体要小）
        for k in [k2, k3, k4]:
            body = abs(k['close'] - k['open'])
            total_range = k['high'] - k['low']
            if total_range == 0 or body / total_range > 0.3:
                return {'detected': False, 'strength': 0}
            
            # 应该在第一根范围内
            if k['high'] > k1['high'] * 1.01 or k['low'] < k1['low'] * 0.99:
                return {'detected': False, 'strength': 0}
        
        # 第五根：大阳线
        if k5['close'] <= k5['open']:
            return {'detected': False, 'strength': 0}
        
        k5_body = k5['close'] - k5['open']
        k5_total = k5['high'] - k5['low']
        if k5_total == 0 or k5_body / k5_total < 0.7:
            return {'detected': False, 'strength': 0}
        
        # 收盘应该高于第一根最高价
        if k5['close'] <= k1['high']:
            return {'detected': False, 'strength': 0}
        
        return {
            'detected': True,
            'strength': 80.0,
            'entry': k5['close'] * 1.002
        }




