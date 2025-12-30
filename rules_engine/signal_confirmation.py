"""
三层确认机制：
1. 技术指标确认
2. 模型确认（价格行为模型、市场结构模型）
3. 裸K确认（K线形态、价格行为确认）
"""

from typing import Dict, List, Optional


def confirm_technical_indicators(signal: Dict, market_data: Dict) -> bool:
    """第一层：技术指标确认"""
    signal_type = signal.get('type')
    current_price = market_data.get('current_price', 0)
    
    # 检查Vegas通道
    ema_144 = market_data.get('ema_144')
    ema_169 = market_data.get('ema_169')
    
    if signal_type == 'long':
        # 做多：价格应该在Vegas通道上方或从Vegas反弹
        if ema_144 and ema_169:
            if current_price > ema_169:
                return True
            elif current_price > ema_144:
                # 在Vegas通道内，但接近上沿
                return True
    else:
        # 做空：价格应该在Vegas通道下方或从Vegas回落
        if ema_144 and ema_169:
            if current_price < ema_144:
                return True
            elif current_price < ema_169:
                # 在Vegas通道内，但接近下沿
                return True
    
    # 检查VWAP
    vwap = market_data.get('vwap')
    if vwap:
        if signal_type == 'long' and current_price > vwap:
            return True
        elif signal_type == 'short' and current_price < vwap:
            return True
    
    # 检查RSI
    rsi = market_data.get('rsi')
    if rsi:
        if signal_type == 'long' and rsi < 70:  # 未超买
            return True
        elif signal_type == 'short' and rsi > 30:  # 未超卖
            return True
    
    return False


def confirm_price_action_model(signal: Dict, klines: List[Dict]) -> bool:
    """第二层：价格行为模型确认"""
    if not klines or len(klines) < 10:
        return False
    
    signal_type = signal.get('type')
    entry = signal.get('entry', 0)
    
    # 检查价格行为
    recent_closes = [k['close'] for k in klines[-10:]]
    recent_highs = [k['high'] for k in klines[-10:]]
    recent_lows = [k['low'] for k in klines[-10:]]
    
    if signal_type == 'long':
        # 做多：检查是否从低点反弹
        # 1. 最近有低点
        recent_low = min(recent_lows)
        # 2. 价格从低点反弹
        if recent_low < entry and recent_closes[-1] > recent_closes[-3]:
            return True
        # 3. 价格在支撑位附近反弹
        if abs(recent_low - entry) / entry < 0.01:
            return True
    else:
        # 做空：检查是否从高点回落
        # 1. 最近有高点
        recent_high = max(recent_highs)
        # 2. 价格从高点回落
        if recent_high > entry and recent_closes[-1] < recent_closes[-3]:
            return True
        # 3. 价格在阻力位附近回落
        if abs(recent_high - entry) / entry < 0.01:
            return True
    
    return False


def confirm_market_structure_model(signal: Dict, klines: List[Dict]) -> bool:
    """第二层：市场结构模型确认"""
    if not klines or len(klines) < 20:
        return False
    
    signal_type = signal.get('type')
    
    # 检查市场结构
    # 1. 检查是否有明显的趋势
    closes = [k['close'] for k in klines[-20:]]
    
    # 计算价格趋势
    price_trend = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0
    
    if signal_type == 'long':
        # 做多：趋势应该向上或横盘
        if price_trend >= -0.01:  # 允许小幅下跌
            return True
    else:
        # 做空：趋势应该向下或横盘
        if price_trend <= 0.01:  # 允许小幅上涨
            return True
    
    # 2. 检查是否有明显的支撑/阻力
    highs = [k['high'] for k in klines[-20:]]
    lows = [k['low'] for k in klines[-20:]]
    
    if signal_type == 'long':
        # 做多：检查是否有支撑
        recent_low = min(lows)
        if abs(closes[-1] - recent_low) / closes[-1] < 0.02:
            return True
    else:
        # 做空：检查是否有阻力
        recent_high = max(highs)
        if abs(closes[-1] - recent_high) / closes[-1] < 0.02:
            return True
    
    return False


def confirm_naked_kline(signal: Dict, naked_kline: Dict) -> bool:
    """第三层：裸K确认"""
    if not naked_kline:
        return False
    
    signal_type = signal.get('type')
    patterns = naked_kline.get('patterns', [])
    
    if signal_type == 'long':
        # 做多：检查是否有看涨K线形态
        bullish_patterns = ['hammer', 'engulfing_bullish', 'morning_star', 'piercing_pattern', 'big_bullish']
        for pattern in patterns:
            if pattern in bullish_patterns:
                return True
    else:
        # 做空：检查是否有看跌K线形态
        bearish_patterns = ['engulfing_bearish', 'evening_star', 'dark_cloud_cover', 'big_bearish']
        for pattern in patterns:
            if pattern in bearish_patterns:
                return True
    
    return False


def confirm_signal_with_three_layers(signal: Dict, market_data: Dict, klines: List[Dict], naked_kline: Dict) -> Dict:
    """
    三层确认机制：
    1. 技术指标确认
    2. 模型确认（价格行为模型、市场结构模型）
    3. 裸K确认（K线形态、价格行为确认）
    
    返回增强后的信号，包含确认信息
    """
    confirmations = []
    
    # 第一层：技术指标确认
    if confirm_technical_indicators(signal, market_data):
        confirmations.append("技术指标")
    
    # 第二层：模型确认
    if confirm_price_action_model(signal, klines):
        confirmations.append("价格行为模型")
    if confirm_market_structure_model(signal, klines):
        confirmations.append("市场结构模型")
    
    # 第三层：裸K确认
    if confirm_naked_kline(signal, naked_kline):
        confirmations.append("裸K确认")
    
    # 根据确认数量确定信号强度
    if len(confirmations) >= 3:
        signal['strength'] = 'strong'
        signal['confirmed'] = True
        signal['needs_confirmation'] = False
    elif len(confirmations) >= 2:
        signal['strength'] = 'medium'
        signal['confirmed'] = True
        signal['needs_confirmation'] = False
    else:
        signal['strength'] = 'weak'
        signal['confirmed'] = False
        signal['needs_confirmation'] = True
        signal['missing_confirmations'] = 3 - len(confirmations)
    
    signal['confirmations'] = confirmations
    signal['confirmation_count'] = len(confirmations)
    
    return signal


