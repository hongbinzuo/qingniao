#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表形态识别模块
基于图片"图表形态及其对应的交易策略"实现所有形态的识别
包含：头肩顶/底、双顶/底、三重顶/底、三角形、旗形、楔形、矩形、圆顶/底等
"""

import sys
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class ChartPatternsDetector:
    """图表形态识别器"""
    
    def __init__(self, min_pattern_length: int = 20, max_pattern_length: int = 200):
        """
        初始化形态识别器
        
        Args:
            min_pattern_length: 最小形态长度（K线数）
            max_pattern_length: 最大形态长度（K线数）
        """
        self.min_pattern_length = min_pattern_length
        self.max_pattern_length = max_pattern_length
    
    def find_swing_points(self, klines: List[Dict], lookback: int = 5) -> Tuple[List[Tuple[int, float]], List[Tuple[int, float]]]:
        """
        找到摆动点（峰值和谷值）
        
        Args:
            klines: K线数据
            lookback: 向前/向后看的K线数量
        
        Returns:
            (peaks, troughs) - 峰值列表和谷值列表，每个元素为(index, price)
        """
        if len(klines) < lookback * 2 + 1:
            return [], []
        
        highs = [k['high'] for k in klines]
        lows = [k['low'] for k in klines]
        closes = [k['close'] for k in klines]
        
        peaks = []
        troughs = []
        
        for i in range(lookback, len(klines) - lookback):
            # 检测峰值：当前高点比前后lookback个K线都高
            is_peak = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and highs[j] >= highs[i]:
                    is_peak = False
                    break
            if is_peak:
                peaks.append((i, highs[i]))
            
            # 检测谷值：当前低点比前后lookback个K线都低
            is_trough = True
            for j in range(i - lookback, i + lookback + 1):
                if j != i and lows[j] <= lows[i]:
                    is_trough = False
                    break
            if is_trough:
                troughs.append((i, lows[i]))
        
        return peaks, troughs
    
    def detect_all_patterns(self, klines: List[Dict]) -> Dict:
        """
        检测所有图表形态
        
        Args:
            klines: K线数据列表，每个元素包含 'open', 'high', 'low', 'close', 'volume'
        
        Returns:
            {
                'patterns': [...],  # 检测到的形态列表
                'reversal_patterns': [...],  # 反转形态
                'continuation_patterns': [...],  # 持续形态
                'pattern_details': {...}  # 形态详细信息
            }
        """
        if not klines or len(klines) < self.min_pattern_length:
            return {
                'patterns': [],
                'reversal_patterns': [],
                'continuation_patterns': [],
                'pattern_details': {}
            }
        
        patterns = []
        reversal_patterns = []
        continuation_patterns = []
        pattern_details = {}
        
        # === 反转形态 ===
        
        # 1. 头肩顶/底
        hst = self.detect_head_shoulders_top(klines)
        if hst['detected']:
            reversal_patterns.append({
                'name': '头肩顶',
                'type': 'bearish_reversal',
                'confidence': hst['confidence'],
                'entry': hst.get('entry'),
                'stop_loss': hst.get('stop_loss'),
                'take_profit': hst.get('take_profit'),
                'details': hst
            })
            patterns.append(f"头肩顶形态 (置信度: {hst['confidence']:.1f}%)")
            pattern_details['head_shoulders_top'] = hst
        
        hsb = self.detect_head_shoulders_bottom(klines)
        if hsb['detected']:
            reversal_patterns.append({
                'name': '反头肩顶',
                'type': 'bullish_reversal',
                'confidence': hsb['confidence'],
                'entry': hsb.get('entry'),
                'stop_loss': hsb.get('stop_loss'),
                'take_profit': hsb.get('take_profit'),
                'details': hsb
            })
            patterns.append(f"反头肩顶形态 (置信度: {hsb['confidence']:.1f}%)")
            pattern_details['head_shoulders_bottom'] = hsb
        
        # 2. 双顶/底
        dt = self.detect_double_top(klines)
        if dt['detected']:
            reversal_patterns.append({
                'name': '双顶',
                'type': 'bearish_reversal',
                'confidence': dt['confidence'],
                'entry': dt.get('entry'),
                'stop_loss': dt.get('stop_loss'),
                'take_profit': dt.get('take_profit'),
                'details': dt
            })
            patterns.append(f"双顶形态 (置信度: {dt['confidence']:.1f}%)")
            pattern_details['double_top'] = dt
        
        db = self.detect_double_bottom(klines)
        if db['detected']:
            reversal_patterns.append({
                'name': '双底',
                'type': 'bullish_reversal',
                'confidence': db['confidence'],
                'entry': db.get('entry'),
                'stop_loss': db.get('stop_loss'),
                'take_profit': db.get('take_profit'),
                'details': db
            })
            patterns.append(f"双底形态 (置信度: {db['confidence']:.1f}%)")
            pattern_details['double_bottom'] = db
        
        # 3. 三重顶/底
        tt = self.detect_triple_top(klines)
        if tt['detected']:
            reversal_patterns.append({
                'name': '三重顶',
                'type': 'bearish_reversal',
                'confidence': tt['confidence'],
                'entry': tt.get('entry'),
                'stop_loss': tt.get('stop_loss'),
                'take_profit': tt.get('take_profit'),
                'details': tt
            })
            patterns.append(f"三重顶形态 (置信度: {tt['confidence']:.1f}%)")
            pattern_details['triple_top'] = tt
        
        tb = self.detect_triple_bottom(klines)
        if tb['detected']:
            reversal_patterns.append({
                'name': '三重底',
                'type': 'bullish_reversal',
                'confidence': tb['confidence'],
                'entry': tb.get('entry'),
                'stop_loss': tb.get('stop_loss'),
                'take_profit': tb.get('take_profit'),
                'details': tb
            })
            patterns.append(f"三重底形态 (置信度: {tb['confidence']:.1f}%)")
            pattern_details['triple_bottom'] = tb
        
        # 4. 圆顶/底（简化实现）
        rt = self.detect_rounding_top(klines)
        if rt['detected']:
            reversal_patterns.append({
                'name': '圆顶',
                'type': 'bearish_reversal',
                'confidence': rt['confidence'],
                'entry': rt.get('entry'),
                'stop_loss': rt.get('stop_loss'),
                'take_profit': rt.get('take_profit'),
                'details': rt
            })
            patterns.append(f"圆顶形态 (置信度: {rt['confidence']:.1f}%)")
            pattern_details['rounding_top'] = rt
        
        rb = self.detect_rounding_bottom(klines)
        if rb['detected']:
            reversal_patterns.append({
                'name': '圆底',
                'type': 'bullish_reversal',
                'confidence': rb['confidence'],
                'entry': rb.get('entry'),
                'stop_loss': rb.get('stop_loss'),
                'take_profit': rb.get('take_profit'),
                'details': rb
            })
            patterns.append(f"圆底形态 (置信度: {rb['confidence']:.1f}%)")
            pattern_details['rounding_bottom'] = rb
        
        # === 持续形态 ===
        
        # 5. 上升/下降三角形
        at = self.detect_ascending_triangle(klines)
        if at['detected']:
            continuation_patterns.append({
                'name': '上升三角形',
                'type': 'bullish_continuation',
                'confidence': at['confidence'],
                'entry': at.get('entry'),
                'stop_loss': at.get('stop_loss'),
                'take_profit': at.get('take_profit'),
                'details': at
            })
            patterns.append(f"上升三角形形态 (置信度: {at['confidence']:.1f}%)")
            pattern_details['ascending_triangle'] = at
        
        dt = self.detect_descending_triangle(klines)
        if dt['detected']:
            continuation_patterns.append({
                'name': '下降三角形',
                'type': 'bearish_continuation',
                'confidence': dt['confidence'],
                'entry': dt.get('entry'),
                'stop_loss': dt.get('stop_loss'),
                'take_profit': dt.get('take_profit'),
                'details': dt
            })
            patterns.append(f"下降三角形形态 (置信度: {dt['confidence']:.1f}%)")
            pattern_details['descending_triangle'] = dt
        
        # 6. 牛旗/熊旗
        bf = self.detect_bull_flag(klines)
        if bf['detected']:
            continuation_patterns.append({
                'name': '牛旗',
                'type': 'bullish_continuation',
                'confidence': bf['confidence'],
                'entry': bf.get('entry'),
                'stop_loss': bf.get('stop_loss'),
                'take_profit': bf.get('take_profit'),
                'details': bf
            })
            patterns.append(f"牛旗形态 (置信度: {bf['confidence']:.1f}%)")
            pattern_details['bull_flag'] = bf
        
        bef = self.detect_bear_flag(klines)
        if bef['detected']:
            continuation_patterns.append({
                'name': '熊旗',
                'type': 'bearish_continuation',
                'confidence': bef['confidence'],
                'entry': bef.get('entry'),
                'stop_loss': bef.get('stop_loss'),
                'take_profit': bef.get('take_profit'),
                'details': bef
            })
            patterns.append(f"熊旗形态 (置信度: {bef['confidence']:.1f}%)")
            pattern_details['bear_flag'] = bef
        
        # 7. 牛楔/熊楔（楔形）
        bp = self.detect_bull_pennant(klines)
        if bp['detected']:
            continuation_patterns.append({
                'name': '牛楔',
                'type': 'bullish_continuation',
                'confidence': bp['confidence'],
                'entry': bp.get('entry'),
                'stop_loss': bp.get('stop_loss'),
                'take_profit': bp.get('take_profit'),
                'details': bp
            })
            patterns.append(f"牛楔形态 (置信度: {bp['confidence']:.1f}%)")
            pattern_details['bull_pennant'] = bp
        
        bep = self.detect_bear_pennant(klines)
        if bep['detected']:
            continuation_patterns.append({
                'name': '熊楔',
                'type': 'bearish_continuation',
                'confidence': bep['confidence'],
                'entry': bep.get('entry'),
                'stop_loss': bep.get('stop_loss'),
                'take_profit': bep.get('take_profit'),
                'details': bep
            })
            patterns.append(f"熊楔形态 (置信度: {bep['confidence']:.1f}%)")
            pattern_details['bear_pennant'] = bep
        
        # 8. 牛矩形/熊矩形
        br = self.detect_bull_rectangle(klines)
        if br['detected']:
            continuation_patterns.append({
                'name': '牛矩形',
                'type': 'bullish_continuation',
                'confidence': br['confidence'],
                'entry': br.get('entry'),
                'stop_loss': br.get('stop_loss'),
                'take_profit': br.get('take_profit'),
                'details': br
            })
            patterns.append(f"牛矩形形态 (置信度: {br['confidence']:.1f}%)")
            pattern_details['bull_rectangle'] = br
        
        ber = self.detect_bear_rectangle(klines)
        if ber['detected']:
            continuation_patterns.append({
                'name': '熊矩形',
                'type': 'bearish_continuation',
                'confidence': ber['confidence'],
                'entry': ber.get('entry'),
                'stop_loss': ber.get('stop_loss'),
                'take_profit': ber.get('take_profit'),
                'details': ber
            })
            patterns.append(f"熊矩形形态 (置信度: {ber['confidence']:.1f}%)")
            pattern_details['bear_rectangle'] = ber
        
        return {
            'patterns': patterns,
            'reversal_patterns': reversal_patterns,
            'continuation_patterns': continuation_patterns,
            'pattern_details': pattern_details
        }
    
    # === 反转形态检测方法 ===
    
    def detect_head_shoulders_top(self, klines: List[Dict]) -> Dict:
        """检测头肩顶形态"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        peaks, troughs = self.find_swing_points(klines[-60:], lookback=3)
        if len(peaks) < 3:
            return {'detected': False, 'confidence': 0}
        
        # 取最后3个峰值
        peaks = peaks[-3:]
        left_shoulder_idx, left_shoulder_price = peaks[0]
        head_idx, head_price = peaks[1]
        right_shoulder_idx, right_shoulder_price = peaks[2]
        
        # 头部应该是最高的
        if head_price <= left_shoulder_price or head_price <= right_shoulder_price:
            return {'detected': False, 'confidence': 0}
        
        # 左右肩高度应该相近（允许3%误差）
        shoulder_diff = abs(left_shoulder_price - right_shoulder_price) / max(left_shoulder_price, right_shoulder_price)
        if shoulder_diff > 0.03:
            return {'detected': False, 'confidence': 0}
        
        # 计算颈线（两个肩之间的最低点）
        neck_start = left_shoulder_idx
        neck_end = right_shoulder_idx
        neck_lows = [klines[-60 + i]['low'] for i in range(neck_start, neck_end + 1)]
        neckline = min(neck_lows) if neck_lows else (left_shoulder_price + right_shoulder_price) / 2 * 0.97
        
        current_price = klines[-1]['close']
        pattern_height = head_price - neckline
        
        # 如果价格跌破颈线，确认形态
        if current_price < neckline:
            # 计算置信度（基于形态的对称性和清晰度）
            symmetry_score = 1 - shoulder_diff  # 对称性得分
            head_protrusion = (head_price - max(left_shoulder_price, right_shoulder_price)) / max(left_shoulder_price, right_shoulder_price)
            clarity_score = min(head_protrusion * 5, 1.0)  # 头部突出程度
            confidence = (symmetry_score * 0.6 + clarity_score * 0.4) * 100
            
            return {
                'detected': True,
                'confidence': min(confidence, 85.0),
                'entry': neckline * 0.998,  # 颈线下方入场做空
                'stop_loss': right_shoulder_price * 1.005,  # 右肩上方止损
                'take_profit': neckline - pattern_height * 0.618,  # 头部到颈线距离的0.618倍
                'left_shoulder': left_shoulder_price,
                'head': head_price,
                'right_shoulder': right_shoulder_price,
                'neckline': neckline,
                'pattern_height': pattern_height
            }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_head_shoulders_bottom(self, klines: List[Dict]) -> Dict:
        """检测反头肩顶（头肩底）形态"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        peaks, troughs = self.find_swing_points(klines[-60:], lookback=3)
        if len(troughs) < 3:
            return {'detected': False, 'confidence': 0}
        
        troughs = troughs[-3:]
        left_shoulder_idx, left_shoulder_price = troughs[0]
        head_idx, head_price = troughs[1]
        right_shoulder_idx, right_shoulder_price = troughs[2]
        
        # 头部应该是最低的
        if head_price >= left_shoulder_price or head_price >= right_shoulder_price:
            return {'detected': False, 'confidence': 0}
        
        shoulder_diff = abs(left_shoulder_price - right_shoulder_price) / min(left_shoulder_price, right_shoulder_price)
        if shoulder_diff > 0.03:
            return {'detected': False, 'confidence': 0}
        
        # 计算颈线（两个肩之间的最高点）
        neck_start = left_shoulder_idx
        neck_end = right_shoulder_idx
        neck_highs = [klines[-60 + i]['high'] for i in range(neck_start, neck_end + 1)]
        neckline = max(neck_highs) if neck_highs else (left_shoulder_price + right_shoulder_price) / 2 * 1.03
        
        current_price = klines[-1]['close']
        pattern_height = neckline - head_price
        
        # 如果价格突破颈线，确认形态
        if current_price > neckline:
            symmetry_score = 1 - shoulder_diff
            head_depression = (min(left_shoulder_price, right_shoulder_price) - head_price) / min(left_shoulder_price, right_shoulder_price)
            clarity_score = min(head_depression * 5, 1.0)
            confidence = (symmetry_score * 0.6 + clarity_score * 0.4) * 100
            
            # 优化入场价：确保入场价在当前价格的可达范围内
            # 如果颈线距离当前价格太远（>3%），调整入场价到更合理的位置
            price_distance_from_neckline = (current_price - neckline) / neckline
            
            if price_distance_from_neckline > 0.03:
                # 当前价格已经远高于颈线，入场价应该设置在等待回调的位置
                # 设置在当前价格下方1-2%，等待回调
                entry = current_price * 0.985  # 当前价格下方1.5%，等待回调
                entry_reason = f"当前价格已突破颈线{price_distance_from_neckline*100:.1f}%，入场价设置在{entry:.0f}等待回调"
            elif price_distance_from_neckline > 0.01:
                # 当前价格略高于颈线，入场价设置在颈线附近，但更接近当前价格
                entry = neckline + (current_price - neckline) * 0.3  # 颈线和当前价格之间的30%位置
                entry_reason = f"当前价格略高于颈线，入场价设置在{entry:.0f}（颈线{neckline:.0f}上方）"
            else:
                # 当前价格刚突破颈线，使用原逻辑
                entry = neckline * 1.002  # 颈线上方0.2%
                entry_reason = f"价格刚突破颈线，入场价设置在{entry:.0f}"
            
            return {
                'detected': True,
                'confidence': min(confidence, 85.0),
                'entry': entry,
                'stop_loss': right_shoulder_price * 0.995,  # 右肩下方止损
                'take_profit': neckline + pattern_height * 0.618,
                'left_shoulder': left_shoulder_price,
                'head': head_price,
                'right_shoulder': right_shoulder_price,
                'neckline': neckline,
                'pattern_height': pattern_height,
                'entry_reason': entry_reason  # 添加入场价设置理由
            }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_double_top(self, klines: List[Dict]) -> Dict:
        """检测双顶形态"""
        if len(klines) < 20:
            return {'detected': False, 'confidence': 0}
        
        peaks, troughs = self.find_swing_points(klines[-50:], lookback=3)
        if len(peaks) < 2:
            return {'detected': False, 'confidence': 0}
        
        peaks = peaks[-2:]
        peak1_idx, peak1_price = peaks[0]
        peak2_idx, peak2_price = peaks[1]
        
        # 两个峰值应该相近（2%误差）
        peak_diff = abs(peak1_price - peak2_price) / max(peak1_price, peak2_price)
        if peak_diff > 0.02:
            return {'detected': False, 'confidence': 0}
        
        # 计算颈线（两个峰值之间的最低点）
        neck_start = peak1_idx
        neck_end = peak2_idx
        neck_lows = [klines[-50 + i]['low'] for i in range(neck_start, neck_end + 1)]
        neckline = min(neck_lows) if neck_lows else (peak1_price + peak2_price) / 2 * 0.97
        
        current_price = klines[-1]['close']
        pattern_height = (peak1_price + peak2_price) / 2 - neckline
        
        # 如果价格跌破颈线，确认形态
        if current_price < neckline:
            confidence = (1 - peak_diff * 10) * 75  # 基于峰值相似度
            
            return {
                'detected': True,
                'confidence': max(confidence, 60.0),
                'entry': neckline * 0.998,  # 颈线下方入场做空
                'stop_loss': max(peak1_price, peak2_price) * 1.005,  # 较高峰值上方止损
                'take_profit': neckline - pattern_height * 0.618,
                'peak1': peak1_price,
                'peak2': peak2_price,
                'neckline': neckline,
                'pattern_height': pattern_height
            }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_double_bottom(self, klines: List[Dict]) -> Dict:
        """检测双底形态"""
        if len(klines) < 20:
            return {'detected': False, 'confidence': 0}
        
        peaks, troughs = self.find_swing_points(klines[-50:], lookback=3)
        if len(troughs) < 2:
            return {'detected': False, 'confidence': 0}
        
        troughs = troughs[-2:]
        trough1_idx, trough1_price = troughs[0]
        trough2_idx, trough2_price = troughs[1]
        
        trough_diff = abs(trough1_price - trough2_price) / min(trough1_price, trough2_price)
        if trough_diff > 0.02:
            return {'detected': False, 'confidence': 0}
        
        neck_start = trough1_idx
        neck_end = trough2_idx
        neck_highs = [klines[-50 + i]['high'] for i in range(neck_start, neck_end + 1)]
        neckline = max(neck_highs) if neck_highs else (trough1_price + trough2_price) / 2 * 1.03
        
        current_price = klines[-1]['close']
        pattern_height = neckline - (trough1_price + trough2_price) / 2
        
        if current_price > neckline:
            confidence = (1 - trough_diff * 10) * 75
            
            return {
                'detected': True,
                'confidence': max(confidence, 60.0),
                'entry': neckline * 1.002,  # 颈线上方入场做多
                'stop_loss': min(trough1_price, trough2_price) * 0.995,  # 较低低点下方止损
                'take_profit': neckline + pattern_height * 0.618,
                'trough1': trough1_price,
                'trough2': trough2_price,
                'neckline': neckline,
                'pattern_height': pattern_height
            }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_triple_top(self, klines: List[Dict]) -> Dict:
        """检测三重顶形态"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        peaks, troughs = self.find_swing_points(klines[-60:], lookback=3)
        if len(peaks) < 3:
            return {'detected': False, 'confidence': 0}
        
        peaks = peaks[-3:]
        peak1_price = peaks[0][1]
        peak2_price = peaks[1][1]
        peak3_price = peaks[2][1]
        
        # 三个峰值应该相近
        max_peak = max(peak1_price, peak2_price, peak3_price)
        min_peak = min(peak1_price, peak2_price, peak3_price)
        peak_diff = (max_peak - min_peak) / max_peak
        
        if peak_diff > 0.02:
            return {'detected': False, 'confidence': 0}
        
        # 计算颈线
        neck_start = peaks[0][0]
        neck_end = peaks[2][0]
        neck_lows = [klines[-60 + i]['low'] for i in range(neck_start, neck_end + 1)]
        neckline = min(neck_lows) if neck_lows else max_peak * 0.97
        
        current_price = klines[-1]['close']
        pattern_height = max_peak - neckline
        
        if current_price < neckline:
            confidence = (1 - peak_diff * 10) * 80
            
            return {
                'detected': True,
                'confidence': max(confidence, 65.0),
                'entry': neckline * 0.998,
                'stop_loss': max_peak * 1.005,
                'take_profit': neckline - pattern_height * 0.618,
                'neckline': neckline,
                'pattern_height': pattern_height
            }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_triple_bottom(self, klines: List[Dict]) -> Dict:
        """检测三重底形态"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        peaks, troughs = self.find_swing_points(klines[-60:], lookback=3)
        if len(troughs) < 3:
            return {'detected': False, 'confidence': 0}
        
        troughs = troughs[-3:]
        trough1_price = troughs[0][1]
        trough2_price = troughs[1][1]
        trough3_price = troughs[2][1]
        
        max_trough = max(trough1_price, trough2_price, trough3_price)
        min_trough = min(trough1_price, trough2_price, trough3_price)
        trough_diff = (max_trough - min_trough) / min_trough
        
        if trough_diff > 0.02:
            return {'detected': False, 'confidence': 0}
        
        neck_start = troughs[0][0]
        neck_end = troughs[2][0]
        neck_highs = [klines[-60 + i]['high'] for i in range(neck_start, neck_end + 1)]
        neckline = max(neck_highs) if neck_highs else min_trough * 1.03
        
        current_price = klines[-1]['close']
        pattern_height = neckline - min_trough
        
        if current_price > neckline:
            confidence = (1 - trough_diff * 10) * 80
            
            # 优化入场价：确保入场价在当前价格的可达范围内
            # 如果颈线距离当前价格太远（>3%），调整入场价到更合理的位置
            price_distance_from_neckline = (current_price - neckline) / neckline
            
            if price_distance_from_neckline > 0.03:
                # 当前价格已经远高于颈线，入场价应该设置在等待回调的位置
                # 设置在当前价格下方1-2%，等待回调
                entry = current_price * 0.985  # 当前价格下方1.5%，等待回调
                entry_reason = f"当前价格已突破颈线{price_distance_from_neckline*100:.1f}%，入场价设置在{entry:.0f}等待回调"
            elif price_distance_from_neckline > 0.01:
                # 当前价格略高于颈线，入场价设置在颈线附近，但更接近当前价格
                entry = neckline + (current_price - neckline) * 0.3  # 颈线和当前价格之间的30%位置
                entry_reason = f"当前价格略高于颈线，入场价设置在{entry:.0f}（颈线{neckline:.0f}上方）"
            else:
                # 当前价格刚突破颈线，使用原逻辑
                entry = neckline * 1.002  # 颈线上方0.2%
                entry_reason = f"价格刚突破颈线，入场价设置在{entry:.0f}"
            
            return {
                'detected': True,
                'confidence': max(confidence, 65.0),
                'entry': entry,
                'stop_loss': min_trough * 0.995,
                'take_profit': neckline + pattern_height * 0.618,
                'neckline': neckline,
                'pattern_height': pattern_height,
                'entry_reason': entry_reason  # 添加入场价设置理由
            }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_rounding_top(self, klines: List[Dict]) -> Dict:
        """检测圆顶形态（简化实现）"""
        if len(klines) < 40:
            return {'detected': False, 'confidence': 0}
        
        # 使用最近40根K线
        recent = klines[-40:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        
        # 检查价格是否形成圆弧形顶部（价格先上升后下降，中间平滑过渡）
        mid_point = len(recent) // 2
        first_half = closes[:mid_point]
        second_half = closes[mid_point:]
        
        # 前半部分应该总体上升，后半部分应该总体下降
        if len(first_half) < 5 or len(second_half) < 5:
            return {'detected': False, 'confidence': 0}
        
        first_trend = (first_half[-1] - first_half[0]) / first_half[0]
        second_trend = (second_half[-1] - second_half[0]) / second_half[0]
        
        if first_trend > 0.02 and second_trend < -0.02:  # 先涨后跌
            max_price = max(highs)
            current_price = closes[-1]
            
            # 如果当前价格已经明显下跌（至少5%）
            if (max_price - current_price) / max_price > 0.05:
                return {
                    'detected': True,
                    'confidence': 60.0,  # 简化实现，置信度较低
                    'entry': current_price * 0.998,
                    'stop_loss': max_price * 1.01,
                    'take_profit': current_price - (max_price - current_price) * 0.618,
                    'top_price': max_price
                }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_rounding_bottom(self, klines: List[Dict]) -> Dict:
        """检测圆底形态（简化实现）"""
        if len(klines) < 40:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-40:]
        closes = [k['close'] for k in recent]
        lows = [k['low'] for k in recent]
        
        mid_point = len(recent) // 2
        first_half = closes[:mid_point]
        second_half = closes[mid_point:]
        
        if len(first_half) < 5 or len(second_half) < 5:
            return {'detected': False, 'confidence': 0}
        
        first_trend = (first_half[-1] - first_half[0]) / first_half[0]
        second_trend = (second_half[-1] - second_half[0]) / second_half[0]
        
        if first_trend < -0.02 and second_trend > 0.02:  # 先跌后涨
            min_price = min(lows)
            current_price = closes[-1]
            
            if (current_price - min_price) / min_price > 0.05:
                return {
                    'detected': True,
                    'confidence': 60.0,
                    'entry': current_price * 1.002,
                    'stop_loss': min_price * 0.99,
                    'take_profit': current_price + (current_price - min_price) * 0.618,
                    'bottom_price': min_price
                }
        
        return {'detected': False, 'confidence': 0}
    
    # === 持续形态检测方法 ===
    
    def detect_ascending_triangle(self, klines: List[Dict]) -> Dict:
        """检测上升三角形形态（持续看涨）"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-50:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        # 检测水平阻力线和上升支撑线
        # 简化：检查最近的高点是否相近，低点是否上升
        last_10_highs = highs[-10:]
        last_10_lows = lows[-10:]
        
        # 阻力线：高点相近（2%误差）
        max_high = max(last_10_highs)
        min_high = min(last_10_highs)
        resistance_flat = (max_high - min_high) / max_high < 0.02
        
        # 支撑线：低点上升
        first_low = last_10_lows[0]
        last_low = last_10_lows[-1]
        support_rising = (last_low - first_low) / first_low > 0.01
        
        if resistance_flat and support_rising:
            resistance = max_high
            current_price = closes[-1]
            
            # 如果价格接近阻力线，可能突破
            if current_price > resistance * 0.98:
                return {
                    'detected': True,
                    'confidence': 65.0,
                    'entry': resistance * 1.002,  # 突破阻力线入场
                    'stop_loss': min(last_10_lows) * 0.995,  # 支撑线下方止损
                    'take_profit': resistance + (resistance - min(last_10_lows)) * 0.618,
                    'resistance': resistance,
                    'support': min(last_10_lows)
                }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_descending_triangle(self, klines: List[Dict]) -> Dict:
        """检测下降三角形形态（持续看跌）"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-50:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        last_10_highs = highs[-10:]
        last_10_lows = lows[-10:]
        
        # 支撑线：低点相近
        max_low = max(last_10_lows)
        min_low = min(last_10_lows)
        support_flat = (max_low - min_low) / max_low < 0.02
        
        # 阻力线：高点下降
        first_high = last_10_highs[0]
        last_high = last_10_highs[-1]
        resistance_falling = (first_high - last_high) / first_high > 0.01
        
        if support_flat and resistance_falling:
            support = min_low
            current_price = closes[-1]
            
            if current_price < support * 1.02:
                return {
                    'detected': True,
                    'confidence': 65.0,
                    'entry': support * 0.998,  # 跌破支撑线入场
                    'stop_loss': max(last_10_highs) * 1.005,  # 阻力线上方止损
                    'take_profit': support - (max(last_10_highs) - support) * 0.618,
                    'support': support,
                    'resistance': max(last_10_highs)
                }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_bull_flag(self, klines: List[Dict]) -> Dict:
        """检测牛旗形态（持续看涨）"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        # 牛旗：强上涨趋势（旗杆）+ 小幅回调整理（旗面）
        mid_point = len(recent) // 2
        
        # 前半部分：强上涨（旗杆）
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_upward = (pole_end - pole_start) / pole_start > 0.05  # 至少5%涨幅
        
        # 后半部分：小幅整理（旗面），通常是水平或轻微下降
        flag_start = closes[mid_point]
        flag_end = closes[-1]
        flag_consolidation = abs(flag_end - flag_start) / flag_start < 0.03  # 3%以内整理
        
        if pole_upward and flag_consolidation:
            pole_high = max(highs[:mid_point+1])
            flag_high = max(highs[mid_point:])
            flag_low = min(lows[mid_point:])
            current_price = closes[-1]
            
            # 如果价格突破旗面高点，入场
            if current_price > flag_high:
                pattern_height = pole_high - pole_start
                return {
                    'detected': True,
                    'confidence': 70.0,
                    'entry': flag_high * 1.002,  # 突破旗面上沿入场
                    'stop_loss': flag_low * 0.995,  # 旗面下沿止损
                    'take_profit': flag_high + pattern_height * 0.618,
                    'pole_height': pattern_height,
                    'flag_high': flag_high,
                    'flag_low': flag_low
                }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_bear_flag(self, klines: List[Dict]) -> Dict:
        """检测熊旗形态（持续看跌）"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        mid_point = len(recent) // 2
        
        # 前半部分：强下跌（旗杆）
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_downward = (pole_start - pole_end) / pole_start > 0.05
        
        # 后半部分：小幅整理（旗面），通常是水平或轻微上升
        flag_start = closes[mid_point]
        flag_end = closes[-1]
        flag_consolidation = abs(flag_end - flag_start) / flag_start < 0.03
        
        if pole_downward and flag_consolidation:
            pole_low = min(lows[:mid_point+1])
            flag_high = max(highs[mid_point:])
            flag_low = min(lows[mid_point:])
            current_price = closes[-1]
            
            # 如果价格跌破旗面低点，入场
            if current_price < flag_low:
                pattern_height = pole_start - pole_low
                return {
                    'detected': True,
                    'confidence': 70.0,
                    'entry': flag_low * 0.998,  # 跌破旗面下沿入场
                    'stop_loss': flag_high * 1.005,  # 旗面上沿止损
                    'take_profit': flag_low - pattern_height * 0.618,
                    'pole_height': pattern_height,
                    'flag_high': flag_high,
                    'flag_low': flag_low
                }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_bull_pennant(self, klines: List[Dict]) -> Dict:
        """检测牛楔形态（持续看涨）"""
        # 类似牛旗，但旗面是收敛三角形
        # 简化实现：使用类似逻辑
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        mid_point = len(recent) // 2
        
        # 前半部分：强上涨
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_upward = (pole_end - pole_start) / pole_start > 0.05
        
        # 后半部分：收敛三角形（高点下降，低点上升）
        flag_highs = highs[mid_point:]
        flag_lows = lows[mid_point:]
        
        if len(flag_highs) < 5:
            return {'detected': False, 'confidence': 0}
        
        flag_high_trend = (flag_highs[-1] - flag_highs[0]) / flag_highs[0]
        flag_low_trend = (flag_lows[-1] - flag_lows[0]) / flag_lows[0]
        converging = flag_high_trend < -0.01 and flag_low_trend > 0.01
        
        if pole_upward and converging:
            pole_high = max(highs[:mid_point+1])
            flag_top = max(flag_highs)
            flag_bottom = min(flag_lows)
            current_price = closes[-1]
            
            # 突破收敛区间上沿
            if current_price > (flag_top + flag_bottom) / 2:
                pattern_height = pole_high - pole_start
                return {
                    'detected': True,
                    'confidence': 68.0,
                    'entry': flag_top * 1.002,
                    'stop_loss': flag_bottom * 0.995,
                    'take_profit': flag_top + pattern_height * 0.618,
                    'pole_height': pattern_height
                }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_bear_pennant(self, klines: List[Dict]) -> Dict:
        """检测熊楔形态（持续看跌）"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-50:]
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        
        mid_point = len(recent) // 2
        
        pole_start = closes[0]
        pole_end = closes[mid_point]
        pole_downward = (pole_start - pole_end) / pole_start > 0.05
        
        flag_highs = highs[mid_point:]
        flag_lows = lows[mid_point:]
        
        if len(flag_highs) < 5:
            return {'detected': False, 'confidence': 0}
        
        flag_high_trend = (flag_highs[-1] - flag_highs[0]) / flag_highs[0]
        flag_low_trend = (flag_lows[-1] - flag_lows[0]) / flag_lows[0]
        converging = flag_high_trend < -0.01 and flag_low_trend > 0.01
        
        if pole_downward and converging:
            pole_low = min(lows[:mid_point+1])
            flag_top = max(flag_highs)
            flag_bottom = min(flag_lows)
            current_price = closes[-1]
            
            # 跌破收敛区间下沿
            if current_price < (flag_top + flag_bottom) / 2:
                pattern_height = pole_start - pole_low
                return {
                    'detected': True,
                    'confidence': 68.0,
                    'entry': flag_bottom * 0.998,
                    'stop_loss': flag_top * 1.005,
                    'take_profit': flag_bottom - pattern_height * 0.618,
                    'pole_height': pattern_height
                }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_bull_rectangle(self, klines: List[Dict]) -> Dict:
        """检测牛矩形形态（持续看涨）"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-40:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        # 矩形：价格在水平区间内震荡
        resistance = max(highs)
        support = min(lows)
        range_size = (resistance - support) / support
        
        # 区间大小应该在合理范围内（1-5%）
        if range_size < 0.01 or range_size > 0.05:
            return {'detected': False, 'confidence': 0}
        
        # 检查价格是否多次触及上下边界
        touches_resistance = sum(1 for h in highs if abs(h - resistance) / resistance < 0.005)
        touches_support = sum(1 for l in lows if abs(l - support) / support < 0.005)
        
        if touches_resistance >= 2 and touches_support >= 2:
            current_price = closes[-1]
            
            # 如果价格突破上边界
            if current_price > resistance * 0.998:
                return {
                    'detected': True,
                    'confidence': 65.0,
                    'entry': resistance * 1.002,
                    'stop_loss': support * 0.995,
                    'take_profit': resistance + (resistance - support) * 0.618,
                    'resistance': resistance,
                    'support': support
                }
        
        return {'detected': False, 'confidence': 0}
    
    def detect_bear_rectangle(self, klines: List[Dict]) -> Dict:
        """检测熊矩形形态（持续看跌）"""
        if len(klines) < 30:
            return {'detected': False, 'confidence': 0}
        
        recent = klines[-40:]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        closes = [k['close'] for k in recent]
        
        resistance = max(highs)
        support = min(lows)
        range_size = (resistance - support) / support
        
        if range_size < 0.01 or range_size > 0.05:
            return {'detected': False, 'confidence': 0}
        
        touches_resistance = sum(1 for h in highs if abs(h - resistance) / resistance < 0.005)
        touches_support = sum(1 for l in lows if abs(l - support) / support < 0.005)
        
        if touches_resistance >= 2 and touches_support >= 2:
            current_price = closes[-1]
            
            # 如果价格跌破下边界，做空入场应该在阻力位（等待反弹）
            if current_price < support * 1.002:
                return {
                    'detected': True,
                    'confidence': 65.0,
                    'entry': resistance * 1.002,  # 做空入场在阻力位上方，等待反弹
                    'stop_loss': resistance * 1.005,
                    'take_profit': support - (resistance - support) * 0.618,
                    'resistance': resistance,
                    'support': support,
                    'entry_reason': f'价格已跌破支撑{support:.0f}，等待反弹到阻力位{resistance:.0f}上方做空'
                }
        
        return {'detected': False, 'confidence': 0}
