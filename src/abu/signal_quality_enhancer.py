#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号质量增强器
改进入场点、止损、止盈的计算逻辑
"""
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
import numpy as np

def find_swing_points(klines: List[Dict], window: int = 5) -> Tuple[Optional[float], Optional[float]]:
    """
    寻找摆动点（swing high/low）
    
    Args:
        klines: K线数据列表
        window: 窗口大小（前后各多少根K线）
    
    Returns:
        (swing_low, swing_high)
    """
    if not klines or len(klines) < window * 2 + 1:
        return None, None
    
    swing_low = None
    swing_high = None
    
    # 寻找摆动低点
    for i in range(window, len(klines) - window):
        current_low = klines[i]['low']
        # 检查是否比前后window根K线都低
        is_swing_low = True
        for j in range(i - window, i + window + 1):
            if j != i and klines[j]['low'] < current_low:
                is_swing_low = False
                break
        
        if is_swing_low:
            if swing_low is None or current_low < swing_low:
                swing_low = current_low
    
    # 寻找摆动高点
    for i in range(window, len(klines) - window):
        current_high = klines[i]['high']
        # 检查是否比前后window根K线都高
        is_swing_high = True
        for j in range(i - window, i + window + 1):
            if j != i and klines[j]['high'] > current_high:
                is_swing_high = False
                break
        
        if is_swing_high:
            if swing_high is None or current_high > swing_high:
                swing_high = current_high
    
    return swing_low, swing_high

def find_recent_support_resistance(klines: List[Dict], lookback: int = 50) -> Dict:
    """
    找到最近的支撑和阻力位
    
    Args:
        klines: K线数据列表
        lookback: 回看周期
    
    Returns:
        {'support': float, 'resistance': float}
    """
    if not klines or len(klines) < lookback:
        return {'support': None, 'resistance': None}
    
    recent = klines[-lookback:]
    
    # 简单方法：使用最近的高点和低点
    # 可以后续改进为更复杂的方法（如摆动点、成交量分布等）
    lows = [k['low'] for k in recent]
    highs = [k['high'] for k in recent]
    
    # 找到最近的低点（支撑）
    recent_low = min(lows) if lows else None
    
    # 找到最近的高点（阻力）
    recent_high = max(highs) if highs else None
    
    return {
        'support': recent_low,
        'resistance': recent_high
    }

def calculate_improved_stop_loss(klines: List[Dict], direction: str, entry_price: float, 
                                 use_swing_points: bool = True) -> float:
    """
    改进的止损计算
    
    Args:
        klines: K线数据列表
        direction: 'long' 或 'short'
        entry_price: 入场价格
        use_swing_points: 是否使用摆动点
    
    Returns:
        止损价格
    """
    if direction == 'long':
        if use_swing_points:
            swing_low, _ = find_swing_points(klines, window=5)
            if swing_low and swing_low < entry_price:
                # 在摆动低点下方设置一点缓冲
                return swing_low * 0.999  # 0.1%缓冲
        
        # 备用：使用最近低点
        recent_lows = [k['low'] for k in klines[-20:]]
        if recent_lows:
            min_low = min(recent_lows)
            if min_low < entry_price:
                return min_low * 0.999
        
        # 最后备用：默认2%
        return entry_price * 0.98
    
    else:  # short
        if use_swing_points:
            _, swing_high = find_swing_points(klines, window=5)
            if swing_high and swing_high > entry_price:
                # 在摆动高点上方设置一点缓冲
                return swing_high * 1.001  # 0.1%缓冲
        
        # 备用：使用最近高点
        recent_highs = [k['high'] for k in klines[-20:]]
        if recent_highs:
            max_high = max(recent_highs)
            if max_high > entry_price:
                return max_high * 1.001
        
        # 最后备用：默认2%
        return entry_price * 1.02

def calculate_improved_take_profit(klines: List[Dict], direction: str, entry_price: float,
                                   stop_loss: float, use_resistance: bool = True) -> Tuple[float, float]:
    """
    改进的止盈计算
    
    Args:
        klines: K线数据列表
        direction: 'long' 或 'short'
        entry_price: 入场价格
        stop_loss: 止损价格
        use_resistance: 是否使用阻力位
    
    Returns:
        (take_profit_1, take_profit_2)
    """
    # 计算风险
    if direction == 'long':
        risk = entry_price - stop_loss
    else:
        risk = stop_loss - entry_price
    
    if risk <= 0:
        # 如果风险无效，使用默认
        if direction == 'long':
            return entry_price * 1.03, entry_price * 1.06
        else:
            return entry_price * 0.97, entry_price * 0.94
    
    # 如果有阻力位信息，使用阻力位
    if use_resistance:
        levels = find_recent_support_resistance(klines, lookback=50)
        
        if direction == 'long':
            resistance = levels.get('resistance')
            if resistance and resistance > entry_price:
                # TP1: 最近的阻力位
                tp1 = resistance * 0.998  # 稍低于阻力位
                # TP2: 如果还有更高的阻力位，或使用2倍风险
                tp2 = tp1 + risk * 1.5  # 基于风险扩展
                return tp1, tp2
        
        else:  # short
            support = levels.get('support')
            if support and support < entry_price:
                # TP1: 最近的支撑位
                tp1 = support * 1.002  # 稍高于支撑位
                # TP2: 如果还有更低的支撑位，或使用2倍风险
                tp2 = tp1 - risk * 1.5  # 基于风险扩展
                return tp1, tp2
    
    # 备用：基于风险回报比
    # TP1: 2:1 RR, TP2: 3:1 RR
    if direction == 'long':
        tp1 = entry_price + risk * 2.0
        tp2 = entry_price + risk * 3.0
    else:
        tp1 = entry_price - risk * 2.0
        tp2 = entry_price - risk * 3.0
    
    return tp1, tp2

def enhance_signal_prices(signal: Dict, klines: List[Dict], 
                          use_swing_points: bool = True,
                          use_resistance: bool = True) -> Dict:
    """
    增强信号的价格设置（入场、止损、止盈）
    
    Args:
        signal: 原始信号字典（包含direction, entry_price等）
        klines: K线数据列表
        use_swing_points: 是否使用摆动点计算止损
        use_resistance: 是否使用阻力位计算止盈
    
    Returns:
        增强后的信号字典
    """
    direction = signal.get('direction', '').lower()
    entry_price = signal.get('entry_price', 0)
    
    if not entry_price or entry_price <= 0:
        return signal
    
    # 改进止损
    stop_loss = calculate_improved_stop_loss(
        klines, direction, entry_price, use_swing_points=use_swing_points
    )
    
    # 改进止盈
    tp1, tp2 = calculate_improved_take_profit(
        klines, direction, entry_price, stop_loss, use_resistance=use_resistance
    )
    
    # 更新信号
    enhanced_signal = signal.copy()
    enhanced_signal['stop_loss'] = stop_loss
    enhanced_signal['take_profit_1'] = tp1
    enhanced_signal['take_profit_2'] = tp2
    
    # 添加标记，表示已增强
    enhanced_signal['price_enhanced'] = True
    
    return enhanced_signal



