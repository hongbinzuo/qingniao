#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Al Brooks特殊模式检测器

检测Gemini可能未完全识别的Al Brooks核心概念：
1. 前18根K线范围突破（First 18 Bars Range Breakout）
2. 日内反转/End of Day Reversal
3. 竭尽式抛售高潮（Exhaustive Sell Climax）
4. 失败突破（Failed Breakout）
5. 下降楔形（Descending Wedge）

这些概念在Al Brooks交易系统中非常重要，但Gemini可能没有完全识别到。
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class AlBrooksSpecialPatternsDetector:
    """Al Brooks特殊模式检测器"""
    
    def __init__(self, initial_bars_count: int = 18):
        """
        初始化检测器
        
        Args:
            initial_bars_count: 初始K线数量（默认18，对应"前18根K线"）
        """
        self.initial_bars_count = initial_bars_count
    
    def detect_first_18_bars_breakout(self, klines: List[Dict]) -> Optional[Dict]:
        """
        检测前18根K线范围突破
        
        概念：
        - 识别前18根K线的最高点和最低点，形成初始交易范围
        - 检测价格是否突破这个范围
        - 根据突破顺序评估后续概率
        
        Returns:
            检测结果字典，包含：
            - detected: 是否检测到
            - initial_range_high: 初始范围高点
            - initial_range_low: 初始范围低点
            - breakouts: 突破序列（向上/向下）
            - probabilities: 后续突破概率
        """
        if not klines or len(klines) < self.initial_bars_count + 5:
            return None
        
        # 获取前18根K线
        initial_bars = klines[:self.initial_bars_count]
        if len(initial_bars) < self.initial_bars_count:
            return None
        
        # 计算初始范围
        initial_high = max([k['high'] for k in initial_bars])
        initial_low = min([k['low'] for k in initial_bars])
        initial_range = initial_high - initial_low
        
        if initial_range <= 0:
            return None
        
        # 检测后续K线的突破情况
        subsequent_bars = klines[self.initial_bars_count:]
        breakouts = []
        
        for i, bar in enumerate(subsequent_bars):
            # 检测向上突破
            if bar['high'] > initial_high:
                breakouts.append({
                    'index': self.initial_bars_count + i,
                    'type': 'bullish_breakout',
                    'price': bar['high'],
                    'bar': bar
                })
                break
            
            # 检测向下突破
            if bar['low'] < initial_low:
                breakouts.append({
                    'index': self.initial_bars_count + i,
                    'type': 'bearish_breakout',
                    'price': bar['low'],
                    'bar': bar
                })
                break
        
        # 如果没有突破，检查是否在范围内
        if not breakouts:
            current_price = klines[-1]['close']
            if initial_low <= current_price <= initial_high:
                return {
                    'detected': True,
                    'initial_range_high': initial_high,
                    'initial_range_low': initial_low,
                    'initial_range': initial_range,
                    'breakouts': [],
                    'status': 'within_range',
                    'current_price': current_price
                }
            return None
        
        # 检测后续突破（反向突破）
        first_breakout = breakouts[0]
        subsequent_breakouts = []
        
        for i, bar in enumerate(subsequent_bars[first_breakout['index'] - self.initial_bars_count + 1:]):
            if first_breakout['type'] == 'bullish_breakout':
                # 如果先向上突破，检测是否向下突破
                if bar['low'] < initial_low:
                    subsequent_breakouts.append({
                        'index': first_breakout['index'] + i + 1,
                        'type': 'bearish_breakout',
                        'price': bar['low'],
                        'bar': bar,
                        'probability': 0.1 if initial_range < initial_high * 0.01 else 0.2  # 小范围20%，大范围10%
                    })
                    break
            else:
                # 如果先向下突破，检测是否向上突破
                if bar['high'] > initial_high:
                    subsequent_breakouts.append({
                        'index': first_breakout['index'] + i + 1,
                        'type': 'bullish_breakout',
                        'price': bar['high'],
                        'bar': bar,
                        'probability': 0.2  # 向下突破后，再次向上突破概率20%
                    })
                    break
        
        # 计算概率
        probabilities = {}
        if first_breakout['type'] == 'bullish_breakout':
            probabilities['reverse_breakdown_probability'] = 0.1 if initial_range < initial_high * 0.01 else 0.2
        else:
            probabilities['reverse_breakup_probability'] = 0.2
        
        return {
            'detected': True,
            'initial_range_high': initial_high,
            'initial_range_low': initial_low,
            'initial_range': initial_range,
            'breakouts': breakouts + subsequent_breakouts,
            'first_breakout': first_breakout,
            'subsequent_breakouts': subsequent_breakouts,
            'probabilities': probabilities,
            'current_price': klines[-1]['close']
        }
    
    def detect_end_of_day_reversal(self, klines: List[Dict], 
                                   lookback_hours: int = 2) -> Optional[Dict]:
        """
        检测日内反转/End of Day Reversal
        
        概念：
        - 识别下跌趋势后的竭尽式抛售高潮
        - 检测失败的向下突破
        - 识别强劲的向上反转
        - 评估日末多空行为
        
        Args:
            klines: K线数据
            lookback_hours: 回看小时数（用于判断是否接近日末）
        
        Returns:
            检测结果字典
        """
        if not klines or len(klines) < 20:
            return None
        
        # 检测下降楔形（Wedge）
        wedge_result = self._detect_descending_wedge(klines)
        
        # 检测竭尽式抛售高潮
        climax_result = self._detect_exhaustive_sell_climax(klines)
        
        # 检测失败的向下突破
        failed_breakout = self._detect_failed_breakout_below(klines)
        
        # 检测强劲的向上反转
        reversal_result = self._detect_strong_bullish_reversal(klines)
        
        # 检测日末行为
        end_of_day_behavior = self._detect_end_of_day_behavior(klines, lookback_hours)
        
        # 综合判断
        if not any([wedge_result, climax_result, failed_breakout, reversal_result]):
            return None
        
        return {
            'detected': True,
            'wedge': wedge_result,
            'exhaustive_sell_climax': climax_result,
            'failed_breakout_below': failed_breakout,
            'strong_bullish_reversal': reversal_result,
            'end_of_day_behavior': end_of_day_behavior,
            'confidence': self._calculate_reversal_confidence(
                wedge_result, climax_result, failed_breakout, reversal_result
            )
        }
    
    def _detect_descending_wedge(self, klines: List[Dict]) -> Optional[Dict]:
        """检测下降楔形"""
        if len(klines) < 20:
            return None
        
        # 寻找摆动高点和低点
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        
        # 寻找最近的高点和低点趋势
        recent_highs = []
        recent_lows = []
        
        for i in range(5, len(klines) - 5):
            # 检查是否是局部高点
            is_high = True
            for j in range(max(0, i - 5), min(len(klines), i + 6)):
                if j != i and highs[j] > highs[i]:
                    is_high = False
                    break
            if is_high:
                recent_highs.append((i, highs[i]))
            
            # 检查是否是局部低点
            is_low = True
            for j in range(max(0, i - 5), min(len(klines), i + 6)):
                if j != i and lows[j] < lows[i]:
                    is_low = False
                    break
            if is_low:
                recent_lows.append((i, lows[i]))
        
        # 检查是否形成下降楔形（高点下降，低点也下降但幅度更小）
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            # 检查高点是否下降
            high_trend = recent_highs[-1][1] < recent_highs[-2][1]
            # 检查低点是否下降但幅度较小
            low_decline = recent_lows[-1][1] - recent_lows[-2][1]
            high_decline = recent_highs[-1][1] - recent_highs[-2][1]
            
            if high_trend and abs(low_decline) < abs(high_decline) * 0.7:
                return {
                    'detected': True,
                    'high_points': recent_highs[-2:],
                    'low_points': recent_lows[-2:],
                    'convergence': True
                }
        
        return None
    
    def _detect_exhaustive_sell_climax(self, klines: List[Dict]) -> Optional[Dict]:
        """检测竭尽式抛售高潮"""
        if len(klines) < 10:
            return None
        
        # 寻找大幅下跌后的快速反弹
        for i in range(5, len(klines) - 3):
            # 检查前几根K线是否大幅下跌
            recent_bars = klines[i-5:i]
            bearish_bars = [b for b in recent_bars if b['close'] < b['open']]
            if len(bearish_bars) >= 3:
                # 计算平均跌幅
                avg_decline = np.mean([(b['open'] - b['close']) / b['open'] for b in bearish_bars])
                
                # 检查后续是否有强劲反弹
                next_bars = klines[i:i+3]
                bullish_bars = [b for b in next_bars if b['close'] > b['open']]
                
                if len(bullish_bars) >= 2 and avg_decline > 0.01:  # 平均跌幅超过1%
                    # 检查反弹强度
                    rebound_strength = (next_bars[0]['close'] - recent_bars[-1]['close']) / recent_bars[-1]['close']
                    if rebound_strength > 0.005:  # 反弹超过0.5%
                        return {
                            'detected': True,
                            'climax_index': i,
                            'decline_strength': avg_decline,
                            'rebound_strength': rebound_strength,
                            'bearish_bars_count': len(bearish_bars),
                            'bullish_reversal_bars_count': len(bullish_bars)
                        }
        
        return None
    
    def _detect_failed_breakout_below(self, klines: List[Dict]) -> Optional[Dict]:
        """检测失败的向下突破"""
        if len(klines) < 15:
            return None
        
        # 寻找支撑位（最近的低点）
        recent_lows = [k['low'] for k in klines[-20:]]
        support_level = min(recent_lows)
        
        # 检查是否跌破支撑但快速反弹
        for i in range(len(klines) - 10, len(klines) - 2):
            current_bar = klines[i]
            next_bar = klines[i + 1]
            
            # 检查是否跌破支撑
            if current_bar['low'] < support_level * 0.998:  # 跌破0.2%
                # 检查是否快速反弹
                if next_bar['close'] > support_level:
                    return {
                        'detected': True,
                        'breakout_index': i,
                        'support_level': support_level,
                        'breakout_low': current_bar['low'],
                        'recovery_price': next_bar['close'],
                        'recovery_strength': (next_bar['close'] - current_bar['low']) / current_bar['low']
                    }
        
        return None
    
    def _detect_strong_bullish_reversal(self, klines: List[Dict]) -> Optional[Dict]:
        """检测强劲的向上反转"""
        if len(klines) < 10:
            return None
        
        # 检查最近是否有强劲的阳线
        recent_bars = klines[-5:]
        bullish_bars = [b for b in recent_bars if b['close'] > b['open']]
        
        if len(bullish_bars) >= 3:
            # 计算平均涨幅
            avg_gain = np.mean([(b['close'] - b['open']) / b['open'] for b in bullish_bars])
            
            # 检查收盘价是否接近最高价（强势）
            strong_bars = [b for b in bullish_bars 
                          if (b['close'] - b['open']) / (b['high'] - b['low']) > 0.7]
            
            if len(strong_bars) >= 2 and avg_gain > 0.005:  # 平均涨幅超过0.5%
                return {
                    'detected': True,
                    'bullish_bars_count': len(bullish_bars),
                    'strong_bars_count': len(strong_bars),
                    'average_gain': avg_gain,
                    'reversal_strength': 'strong'
                }
        
        return None
    
    def _detect_end_of_day_behavior(self, klines: List[Dict], 
                                    lookback_hours: int) -> Optional[Dict]:
        """检测日末行为"""
        if not klines:
            return None
        
        # 检查最后一根K线
        last_bar = klines[-1]
        body = abs(last_bar['close'] - last_bar['open'])
        total_range = last_bar['high'] - last_bar['low']
        
        # 检查是否"收盘价接近开盘价"
        if total_range > 0:
            body_ratio = body / total_range
            if body_ratio < 0.3:  # 实体小于30%
                return {
                    'detected': True,
                    'close_near_open': True,
                    'body_ratio': body_ratio,
                    'interpretation': '可能表示多空双方在日末的激烈争夺或获利了结'
                }
        
        return None
    
    def _calculate_reversal_confidence(self, wedge, climax, failed_breakout, 
                                      reversal) -> float:
        """计算反转置信度"""
        confidence = 0.0
        
        if wedge:
            confidence += 0.2
        if climax:
            confidence += 0.3
        if failed_breakout:
            confidence += 0.3
        if reversal:
            confidence += 0.2
        
        return min(1.0, confidence)
    
    def detect_all_special_patterns(self, klines: List[Dict]) -> Dict:
        """
        检测所有特殊模式
        
        Returns:
            包含所有检测结果的字典
        """
        results = {
            'first_18_bars_breakout': self.detect_first_18_bars_breakout(klines),
            'end_of_day_reversal': self.detect_end_of_day_reversal(klines),
            'timestamp': datetime.now().isoformat()
        }
        
        # 统计检测到的模式数量
        detected_count = sum(1 for v in results.values() 
                           if isinstance(v, dict) and v.get('detected'))
        results['detected_patterns_count'] = detected_count
        
        return results



