#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用De.交易系统生成BTC 5分钟和15分钟交易信号
数据来源：Bitget或Gate.io
提供技术指标止损和实时订单簿止损两种止损方案
"""

import requests
import sys
from datetime import datetime

# 导入实时订单簿止损功能
try:
    import os
    import sys
    # 添加src目录到路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    from get_realtime_stop_loss import (
        get_order_book_with_retry,
        get_current_price as get_ob_current_price,
        calculate_stop_loss_by_orderbook
    )
    ORDERBOOK_AVAILABLE = True
except ImportError as e:
    ORDERBOOK_AVAILABLE = False
    print(f"警告: 无法导入实时订单簿止损功能 ({e})，将使用技术指标止损", file=sys.stderr)

# 导入增强分析模块（量能分析、区间识别）
try:
    from enhanced_de_analysis import (
        analyze_volume_profile,
        identify_consolidation_ranges,
        enhance_support_resistance_with_volume,
        identify_interval_breakout_opportunities
    )
    ENHANCED_ANALYSIS_AVAILABLE = True
except ImportError as e:
    ENHANCED_ANALYSIS_AVAILABLE = False
    print(f"警告: 无法导入增强分析模块 ({e})，将使用基础分析", file=sys.stderr)

# 导入波动率分析模块
try:
    from volatility_analyzer import (
        calculate_atr_percent,
        assess_volatility_level,
        calculate_risk_reward_ratio,
        analyze_signal_with_volatility
    )
    VOLATILITY_ANALYZER_AVAILABLE = True
except ImportError:
    VOLATILITY_ANALYZER_AVAILABLE = False

def get_btc_kline_gateio(timeframe='5m', limit=200):
    """从Gate.io获取BTC K线数据"""
    try:
        # 转换时间框架
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h'}
        interval = tf_map.get(timeframe, '5m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                # Gate.io返回的是从新到旧，需要反转
                data.reverse()
                klines = []
                for k in data:
                    # Gate.io格式: [timestamp, volume, close, high, low, open]
                    klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[5]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'close': float(k[2]),
                        'volume': float(k[1])
                    })
                return klines
    except Exception as e:
        print(f"Gate.io获取失败: {e}", file=sys.stderr)
    return None

def get_btc_kline_bitget(timeframe='5m', limit=200):
    """从Bitget获取BTC K线数据"""
    try:
        # 转换时间框架
        tf_map = {'5m': '5min', '15m': '15min', '1h': '1hour'}
        interval = tf_map.get(timeframe, '5min')
        
        url = "https://api.bitget.com/api/spot/v1/market/candles"
        params = {
            'symbol': 'BTCUSDT',
            'granularity': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                klines_data = data['data']
                # Bitget返回的是从新到旧，需要反转
                klines_data.reverse()
                klines = []
                for k in klines_data:
                    # Bitget格式: [timestamp, open, close, high, low, volume]
                    klines.append({
                        'timestamp': int(k[0]) // 1000,  # 转换为秒
                        'open': float(k[1]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'close': float(k[2]),
                        'volume': float(k[5])
                    })
                return klines
    except Exception as e:
        print(f"Bitget获取失败: {e}", file=sys.stderr)
    return None

def get_btc_current_price():
    """获取BTC当前价格"""
    # 先尝试Gate.io
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': 'BTC_USDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['last'])
    except:
        pass
    
    # 再尝试Bitget
    try:
        url = "https://api.bitget.com/api/spot/v1/market/ticker"
        params = {'symbol': 'BTCUSDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                return float(data['data']['last'])
    except:
        pass
    
    return None

def calculate_ema(prices, period):
    """计算EMA"""
    if len(prices) < period:
        return None
    multiplier = 2.0 / (period + 1)
    ema = [prices[0]]
    for i in range(1, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    return ema[-1]

def calculate_vwap(klines):
    """计算VWAP"""
    if not klines:
        return None
    total_pv = 0
    total_volume = 0
    for k in klines:
        typical_price = (k['high'] + k['low'] + k['close']) / 3
        total_pv += typical_price * k['volume']
        total_volume += k['volume']
    if total_volume > 0:
        return total_pv / total_volume
    return None

def calculate_rsi(prices, period=14):
    """计算RSI"""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def identify_fvg(klines, lookback=20):
    """识别FVG（Fair Value Gap）"""
    if len(klines) < 3:
        return []
    
    fvgs = []
    for i in range(1, len(klines) - 1):
        prev = klines[i-1]
        curr = klines[i]
        next_k = klines[i+1]
        
        # 上涨FVG：前一根K线高点 < 当前K线低点
        if prev['high'] < curr['low']:
            fvgs.append({
                'type': 'bullish',
                'low': prev['high'],
                'high': curr['low'],
                'price': (prev['high'] + curr['low']) / 2,
                'index': i
            })
        
        # 下跌FVG：前一根K线低点 > 当前K线高点
        if prev['low'] > curr['high']:
            fvgs.append({
                'type': 'bearish',
                'low': curr['high'],
                'high': prev['low'],
                'price': (curr['high'] + prev['low']) / 2,
                'index': i
            })
    
    return fvgs[-5:]  # 返回最近5个FVG

def identify_support_resistance(klines, current_price):
    """识别支撑阻力位（简化版）"""
    if not klines or len(klines) < 50:
        return {'support': [], 'resistance': []}
    
    highs = [k['high'] for k in klines[-50:]]
    lows = [k['low'] for k in klines[-50:]]
    
    # 找出关键高低点
    recent_high = max(highs)
    recent_low = min(lows)
    
    # 找出次要高低点
    sorted_highs = sorted(set(highs), reverse=True)[:3]
    sorted_lows = sorted(set(lows))[:3]
    
    support = [l for l in sorted_lows if l < current_price]
    resistance = [h for h in sorted_highs if h > current_price]
    
    return {
        'support': support[:3],
        'resistance': resistance[:3]
    }

def check_garbage_time(klines, current_price, tolerance_pct=0.01):
    """检查是否在垃圾时间内"""
    if len(klines) < 20:
        return False, None
    
    recent_highs = [k['high'] for k in klines[-20:]]
    recent_lows = [k['low'] for k in klines[-20:]]
    
    range_high = max(recent_highs)
    range_low = min(recent_lows)
    range_size = range_high - range_low
    range_pct = range_size / current_price if current_price > 0 else 0
    
    # 如果价格在区间内震荡，且区间很小（<2%），可能是垃圾时间
    if range_pct < 0.02 and range_low < current_price < range_high:
        return True, (range_low, range_high)
    
    return False, None

def check_multiple_push(klines, level, tolerance_pct=0.005):
    """检查是否出现多推模式"""
    if len(klines) < 10:
        return False, 0
    
    touches = 0
    for k in klines[-20:]:
        if abs(k['high'] - level) / level < tolerance_pct or abs(k['low'] - level) / tolerance_pct < tolerance_pct:
            touches += 1
    
    return touches >= 3, touches

def calculate_fibonacci_retracement(high, low):
    """计算斐波那契回撤位（重点关注618和786，用于OTE）"""
    diff = high - low
    if diff <= 0:
        return None
    return {
        '0': high,
        '236': high - diff * 0.236,
        '382': high - diff * 0.382,
        '500': high - diff * 0.500,
        '618': high - diff * 0.618,  # OTE区间下沿
        '786': high - diff * 0.786,  # OTE区间上沿（重点关注）
        '100': low
    }

def check_ote_zone(klines, current_price, lookback=50):
    """检查价格是否在OTE区间（618-786）或突破786"""
    if len(klines) < lookback:
        return None
    
    recent_klines = klines[-lookback:]
    highs = [k['high'] for k in recent_klines]
    lows = [k['low'] for k in recent_klines]
    
    recent_high = max(highs)
    recent_low = min(lows)
    
    # 计算斐波那契回撤位
    fib_levels = calculate_fibonacci_retracement(recent_high, recent_low)
    if not fib_levels:
        return None
    
    fib_618 = fib_levels['618']
    fib_786 = fib_levels['786']
    
    # 检查当前价格与OTE区间的关系
    if current_price >= fib_618 and current_price <= fib_786:
        return {
            'in_ote_zone': True,
            'fib_618': fib_618,
            'fib_786': fib_786,
            'current_price': current_price,
            'above_786': False,
            'below_618': False,
            'fib_levels': fib_levels
        }
    elif current_price > fib_786:
        return {
            'in_ote_zone': False,
            'fib_618': fib_618,
            'fib_786': fib_786,
            'current_price': current_price,
            'above_786': True,  # 突破786，看涨信号
            'below_618': False,
            'fib_levels': fib_levels
        }
    elif current_price < fib_618:
        return {
            'in_ote_zone': False,
            'fib_618': fib_618,
            'fib_786': fib_786,
            'current_price': current_price,
            'above_786': False,
            'below_618': True,  # 跌破618，可能继续下跌
            'fib_levels': fib_levels
        }
    return None

def validate_signal(signal, current_price, tolerance_pct=0.05):
    """验证交易信号的合法性
    
    Args:
        signal: 交易信号字典，包含 'type', 'entry', 'stop_loss', 'take_profit_1', 'take_profit_2'
        current_price: 当前价格
        tolerance_pct: 允许的偏差百分比（默认5%）
    
    Returns:
        (is_valid, error_msg): (是否合法, 错误信息)
    """
    if not signal or 'type' not in signal or 'entry' not in signal:
        return False, "信号格式不完整"
    
    signal_type = signal['type']
    entry = signal['entry']
    stop_loss = signal.get('stop_loss')
    take_profit_1 = signal.get('take_profit_1')
    take_profit_2 = signal.get('take_profit_2')
    
    # 检查入场价的合理性
    if signal_type == 'long':
        # 做多：入场价应该在当前价格附近或下方（允许5%偏差，因为可能是挂单等待回调）
        max_entry = current_price * (1 + tolerance_pct)
        if entry > max_entry:
            return False, f"做多入场价${entry:,.0f}高于当前价格${current_price:,.0f}超过{tolerance_pct*100}%，不合理"
        
        # 止损应该在入场价下方
        if stop_loss and stop_loss >= entry:
            return False, f"做多止损${stop_loss:,.0f}应该在入场价${entry:,.0f}下方"
        
        # 止盈应该在入场价上方
        if take_profit_1 and take_profit_1 <= entry:
            return False, f"做多止盈1${take_profit_1:,.0f}应该在入场价${entry:,.0f}上方"
        if take_profit_2 and take_profit_2 <= entry:
            return False, f"做多止盈2${take_profit_2:,.0f}应该在入场价${entry:,.0f}上方"
    
    elif signal_type == 'short':
        # 做空：入场价必须高于或等于当前价格（做空应该等待反弹到阻力位）
        # 严格检查：不允许入场价低于当前价格（即使只有0.1%也不行）
        if entry < current_price:
            return False, f"做空入场价${entry:,.0f}低于当前价格${current_price:,.0f}，不合理（做空应等待反弹到阻力位，入场价必须≥当前价格）"
        
        # 如果入场价等于当前价格，也建议调整到上方（至少0.1%），避免立即成交
        if entry == current_price:
            return False, f"做空入场价${entry:,.0f}等于当前价格${current_price:,.0f}，建议等待反弹到当前价格上方至少0.1%再入场"
        
        # 入场价不应该过高（超过当前价格5%），但如果是形态阻力位，可以接受
        if entry > current_price * 1.05:
            # 这是一个警告，不是错误，但如果太高可能需要调整
            pass
        
        # 止损应该在入场价上方
        if stop_loss and stop_loss <= entry:
            return False, f"做空止损${stop_loss:,.0f}应该在入场价${entry:,.0f}上方"
        
        # 止盈应该在入场价下方
        if take_profit_1 and take_profit_1 >= entry:
            return False, f"做空止盈1${take_profit_1:,.0f}应该在入场价${entry:,.0f}下方"
        if take_profit_2 and take_profit_2 >= entry:
            return False, f"做空止盈2${take_profit_2:,.0f}应该在入场价${entry:,.0f}下方"
    
    return True, ""

def add_signal_analysis_to_plan(plan, best_signal, klines, timeframe_name):
    """
    添加信号分析到计划（盈亏比和波动率）
    
    Args:
        plan: 计划列表
        best_signal: 最佳信号字典
        klines: K线数据
        timeframe_name: 时间框架名称
    """
    if not VOLATILITY_ANALYZER_AVAILABLE:
        return
    
    # 计算盈亏比（使用技术止损作为主要计算依据）
    try:
        stop_loss_price = best_signal['stop_loss']  # 预生成信号使用技术止损
        rr_analysis = calculate_risk_reward_ratio(
            entry=best_signal['entry'],
            stop_loss=stop_loss_price,
            take_profit_1=best_signal['take_profit_1'],
            take_profit_2=best_signal['take_profit_2'],
            signal_type=best_signal['type']
        )
        
        quality_map = {
            'excellent': '优秀（≥3.0）',
            'good': '良好（2.0-3.0）',
            'acceptable': '可接受（1.5-2.0）',
            'poor': '较低（1.0-1.5）',
            'very_poor': '过低（<1.0）'
        }
        
        plan.append(f"**盈亏比**: {rr_analysis['avg_rr_ratio']:.2f}:1 ({quality_map.get(rr_analysis['quality'], '未知')})")
        plan.append(f"   - 风险: ${rr_analysis['risk']:,.0f} ({abs(best_signal['entry'] - stop_loss_price) / best_signal['entry'] * 100:.2f}%)")
        plan.append(f"   - 止盈1回报: ${rr_analysis['reward_1']:,.0f} ({rr_analysis['rr_ratio_1']:.2f}:1)")
        plan.append(f"   - 止盈2回报: ${rr_analysis['reward_2']:,.0f} ({rr_analysis['rr_ratio_2']:.2f}:1)")
    except Exception as e:
        print(f"{timeframe_name}盈亏比计算失败: {e}", file=sys.stderr)
    
    # 计算波动率（使用增强的波动率分析）
    if klines:
        try:
            current_price = klines[-1]['close'] if klines else best_signal['entry']
            
            # 使用增强的波动率分析（包含动态ATR和自适应波动率）
            if 'get_enhanced_volatility_analysis' in globals():
                try:
                    enhanced_vol = get_enhanced_volatility_analysis(klines, current_price, timeframe_name)
                    if enhanced_vol.get('recommended_atr_percent'):
                        atr_percent = enhanced_vol['recommended_atr_percent']
                        volatility_assessment = enhanced_vol.get('assessment') or assess_volatility_level(atr_percent)
                        
                        # 显示多种波动率指标
                        volatility_info = [f"**市场波动率**: {volatility_assessment['description']}"]
                        if enhanced_vol.get('atr_traditional_percent'):
                            volatility_info.append(f"传统ATR: {enhanced_vol['atr_traditional_percent']:.2f}%")
                        if enhanced_vol.get('atr_dynamic_percent'):
                            volatility_info.append(f"动态ATR: {enhanced_vol['atr_dynamic_percent']:.2f}%")
                        if enhanced_vol.get('adaptive_volatility'):
                            adaptive = enhanced_vol['adaptive_volatility']
                            volatility_info.append(f"波动率趋势: {adaptive['description']} (短期/长期比值: {adaptive['ratio']:.2f})")
                        
                        plan.append(" | ".join(volatility_info))
                        plan.append(f"   推荐ATR: {atr_percent:.2f}% (用于短线止损止盈调整)")
                        plan.append(f"   {volatility_assessment['recommendation']}")
                        
                        # 如果波动率较高，给出止损建议
                        if volatility_assessment['level'] in ['high', 'very_high']:
                            stop_loss_price = best_signal['stop_loss']
                            current_stop_distance = abs(best_signal['entry'] - stop_loss_price) / best_signal['entry'] * 100
                            suggested_stop_distance = current_stop_distance * volatility_assessment['stop_loss_multiplier']
                            plan.append(f"   ⚠️ 建议止损距离: {suggested_stop_distance:.2f}% (当前: {current_stop_distance:.2f}%)")
                        
                        # 如果期权IV可用，显示
                        if enhanced_vol.get('options_iv'):
                            iv_data = enhanced_vol['options_iv']
                            plan.append(f"   📊 期权隐含波动率: {iv_data.get('iv_30d', 'N/A')}% (30天)")
                    else:
                        # 回退到传统ATR
                        atr_percent = calculate_atr_percent(klines, period=14)
                        volatility_assessment = assess_volatility_level(atr_percent)
                        plan.append(f"**市场波动率**: {volatility_assessment['description']} (ATR: {atr_percent:.2f}%)")
                        plan.append(f"   {volatility_assessment['recommendation']}")
                except Exception as e:
                    print(f"增强波动率分析失败，使用传统方法: {e}", file=sys.stderr)
                    # 回退到传统方法
                    atr_percent = calculate_atr_percent(klines, period=14)
                    volatility_assessment = assess_volatility_level(atr_percent)
                    plan.append(f"**市场波动率**: {volatility_assessment['description']} (ATR: {atr_percent:.2f}%)")
                    plan.append(f"   {volatility_assessment['recommendation']}")
            else:
                # 使用传统ATR
                atr_percent = calculate_atr_percent(klines, period=14)
                volatility_assessment = assess_volatility_level(atr_percent)
                plan.append(f"**市场波动率**: {volatility_assessment['description']} (ATR: {atr_percent:.2f}%)")
                plan.append(f"   {volatility_assessment['recommendation']}")
        except Exception as e:
            print(f"{timeframe_name}波动率分析失败: {e}", file=sys.stderr)


def detect_order_blocks(klines, lookback=100):
    """检测Order Block（订单块）
    
    Order Block定义：
    - 看涨OB：大幅上涨前的最后一根下跌K线（或几根下跌K线）
    - 看跌OB：大幅下跌前的最后一根上涨K线（或几根上涨K线）
    - OB通常是机构订单区域，价格回到OB时是交易机会
    """
    if len(klines) < 20:
        return []
    
    order_blocks = []
    
    # 从后往前查找，找到最近的大幅波动
    for i in range(len(klines) - 5, max(0, len(klines) - lookback), -1):
        if i < 3:
            break
        
        # 检查是否有大幅上涨（看涨OB）
        # 大幅上涨：当前K线收盘价 > 前3根K线最高价 * 1.02（至少2%涨幅）
        if i >= 3:
            prev_high = max([k['high'] for k in klines[i-3:i]])
            current_close = klines[i]['close']
            
            if current_close > prev_high * 1.02:
                # 找到大幅上涨，前一根或前几根下跌K线就是看涨OB
                ob_candles = []
                for j in range(max(0, i-5), i):
                    if klines[j]['close'] < klines[j]['open']:  # 下跌K线
                        ob_candles.append(klines[j])
                
                if ob_candles:
                    ob_low = min([k['low'] for k in ob_candles])
                    ob_high = max([k['high'] for k in ob_candles])
                    ob_volume = sum([k['volume'] for k in ob_candles])
                    
                    order_blocks.append({
                        'type': 'bullish',  # 看涨OB
                        'low': ob_low,
                        'high': ob_high,
                        'volume': ob_volume,
                        'timestamp': ob_candles[-1]['timestamp'],
                        'candle_count': len(ob_candles),
                        'strength': 'strong' if current_close > prev_high * 1.05 else 'medium'
                    })
        
        # 检查是否有大幅下跌（看跌OB）
        # 大幅下跌：当前K线收盘价 < 前3根K线最低价 * 0.98（至少2%跌幅）
        if i >= 3:
            prev_low = min([k['low'] for k in klines[i-3:i]])
            current_close = klines[i]['close']
            
            if current_close < prev_low * 0.98:
                # 找到大幅下跌，前一根或前几根上涨K线就是看跌OB
                ob_candles = []
                for j in range(max(0, i-5), i):
                    if klines[j]['close'] > klines[j]['open']:  # 上涨K线
                        ob_candles.append(klines[j])
                
                if ob_candles:
                    ob_low = min([k['low'] for k in ob_candles])
                    ob_high = max([k['high'] for k in ob_candles])
                    ob_volume = sum([k['volume'] for k in ob_candles])
                    
                    order_blocks.append({
                        'type': 'bearish',  # 看跌OB
                        'low': ob_low,
                        'high': ob_high,
                        'volume': ob_volume,
                        'timestamp': ob_candles[-1]['timestamp'],
                        'candle_count': len(ob_candles),
                        'strength': 'strong' if current_close < prev_low * 0.95 else 'medium'
                    })
    
    # 去重：合并相近的OB
    if order_blocks:
        unique_obs = []
        for ob in order_blocks:
            is_duplicate = False
            for existing_ob in unique_obs:
                # 如果OB区间重叠或非常接近（5%以内），认为是同一个OB
                if (ob['type'] == existing_ob['type'] and 
                    abs(ob['low'] - existing_ob['low']) / existing_ob['low'] < 0.05):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_obs.append(ob)
        
        return unique_obs[:5]  # 只返回最近5个OB
    
    return []

def analyze_timeframe(klines, timeframe_name, current_price):
    """分析单个时间框架"""
    if not klines or len(klines) < 50:
        return None
    
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # 计算技术指标
    ema_144 = calculate_ema(closes, 144) if len(closes) >= 144 else None
    ema_169 = calculate_ema(closes, 169) if len(closes) >= 169 else None
    vwap = calculate_vwap(klines[-100:])
    rsi = calculate_rsi(closes)
    
    # 识别FVG
    fvgs = identify_fvg(klines[-50:])
    
    # 识别支撑阻力
    sr = identify_support_resistance(klines, current_price)
    
    # 增强分析：量能分析和区间识别
    volume_profile = None
    consolidation_ranges = []
    enhanced_sr = sr
    
    if ENHANCED_ANALYSIS_AVAILABLE:
        try:
            # 量能分析（识别量能大的支撑阻力位置）
            volume_profile = analyze_volume_profile(klines[-100:], num_bins=30)
            
            # 用量能增强支撑阻力识别
            enhanced_sr = enhance_support_resistance_with_volume(sr, volume_profile, current_price)
            
            # 识别区间（流动性密集区域）
            consolidation_ranges = identify_consolidation_ranges(klines[-100:], lookback=50, min_touches=3)
        except Exception as e:
            print(f"增强分析失败: {e}", file=sys.stderr)
    
    # 检查垃圾时间
    is_garbage, garbage_range = check_garbage_time(klines, current_price)
    
    # OTE区间分析（618-786斐波那契回撤）
    ote_analysis = check_ote_zone(klines, current_price, lookback=50)
    
    # Order Block识别
    order_blocks = detect_order_blocks(klines, lookback=100)
    
    # 分析信号
    signals = []
    
    # 检查Vegas突破（新规则：突破后支撑转换）
    vegas_breakthrough = False
    if ema_144 and ema_169 and len(klines) >= 20:
        # 检查最近是否有突破
        recent_closes = [k['close'] for k in klines[-20:]]
        recent_highs = [k['high'] for k in klines[-20:]]
        # 如果当前价格在Vegas上方，且之前有突破行为
        if current_price > ema_169:
            # 检查是否刚突破（最近5根K线中有突破）
            for i in range(-5, 0):
                if i < -len(klines):
                    continue
                if klines[i]['high'] > ema_169 and (i == -1 or klines[i-1]['high'] <= ema_169):
                    vegas_breakthrough = True
                    break
    
    # 识别Pinbar形态
    def identify_pinbar(k):
        """识别Pinbar形态（影线长、实体小的反转信号）"""
        if k is None:
            return None
        body = abs(k['close'] - k['open'])
        total_range = k['high'] - k['low']
        if total_range == 0:
            return None
        
        upper_shadow = k['high'] - max(k['open'], k['close'])
        lower_shadow = min(k['open'], k['close']) - k['low']
        body_ratio = body / total_range
        upper_shadow_ratio = upper_shadow / total_range
        lower_shadow_ratio = lower_shadow / total_range
        
        is_bullish = k['close'] > k['open']
        
        # 看涨Pinbar：下影线长（>60%），实体小（<30%），上影线短（<10%）
        if lower_shadow_ratio > 0.6 and body_ratio < 0.3 and upper_shadow_ratio < 0.1:
            return {'type': 'bullish', 'strength': 'medium', 'shadow_ratio': lower_shadow_ratio}
        
        # 看跌Pinbar：上影线长（>60%），实体小（<30%），下影线短（<10%）
        if upper_shadow_ratio > 0.6 and body_ratio < 0.3 and lower_shadow_ratio < 0.1:
            return {'type': 'bearish', 'strength': 'medium', 'shadow_ratio': upper_shadow_ratio}
        
        return None
    
    # 检查最后一根K线的Pinbar形态
    pinbar_signal = None
    if len(klines) >= 1:
        pinbar_signal = identify_pinbar(klines[-1])
    
    # 检查大阳K线
    is_big_bullish_candle = False
    if len(klines) >= 1:
        last_k = klines[-1]
        candle_body = abs(last_k['close'] - last_k['open'])
        candle_range = last_k['high'] - last_k['low']
        if candle_range > 0:
            body_ratio = candle_body / candle_range
            # 大阳K线：实体占比>70%，且是阳线
            if body_ratio > 0.7 and last_k['close'] > last_k['open']:
                is_big_bullish_candle = True
    
    # 1. Vegas通道信号（包含突破后支撑转换）
    if ema_144 and ema_169:
        if current_price > ema_169:
            # 突破后支撑转换：Vegas成为支撑
            if vegas_breakthrough:
                # 回踩到Vegas不破做多
                entry = ema_169 * 1.002  # Vegas通道上方0.2%
                stop_loss = ema_169 * 0.98  # Vegas通道下方2%
                # 根据大阳K线设置目标
                if is_big_bullish_candle:
                    take_profit_1 = current_price + (current_price - ema_169) * 0.5  # 保守目标
                    take_profit_2 = current_price + (current_price - ema_169) * 1.5  # 激进目标
                else:
                    take_profit_1 = current_price * 1.02
                    take_profit_2 = current_price * 1.05
                
                entry_model = "Vegas通道突破"
                if pinbar_signal and pinbar_signal['type'] == 'bullish':
                    entry_model += " + Pinbar确认"
                
                signals.append({
                    'type': 'long',
                    'strength': 'strong' if is_big_bullish_candle else 'medium',
                    'entry': entry,
                    'stop_loss': stop_loss,
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'entry_model': entry_model,
                    'reason': f'【{entry_model}】价格突破Vegas通道(EMA169={ema_169:.0f})后，Vegas成为支撑，回踩不破做多{"，大阳K线不着急止盈" if is_big_bullish_candle else ""}'
                })
            else:
                # 原有逻辑：价格在Vegas上方
                entry_model = "Vegas通道"
                if pinbar_signal and pinbar_signal['type'] == 'bullish':
                    entry_model += " + Pinbar确认"
                
                signals.append({
                    'type': 'long',
                    'strength': 'medium',
                    'entry': ema_144 * 1.005,  # 通道下沿上方0.5%
                    'stop_loss': ema_144 * 0.98,  # 通道下沿下方2%
                    'take_profit_1': ema_169 * 1.02,  # 通道上沿
                    'take_profit_2': current_price * 1.02,
                    'entry_model': entry_model,
                    'reason': f'【{entry_model}】价格在Vegas通道上方，回调到EMA144({ema_144:.0f})做多'
                })
        elif current_price < ema_144:
            entry_model = "Vegas通道"
            if pinbar_signal and pinbar_signal['type'] == 'bearish':
                entry_model += " + Pinbar确认"
            
            signals.append({
                'type': 'short',
                'strength': 'medium',
                'entry': ema_169 * 0.995,  # 通道上沿下方0.5%
                'stop_loss': ema_169 * 1.02,  # 通道上沿上方2%
                'take_profit_1': ema_144 * 0.98,  # 通道下沿
                'take_profit_2': current_price * 0.98,
                'entry_model': entry_model,
                'reason': f'【{entry_model}】价格在Vegas通道下方，反弹到EMA169({ema_169:.0f})做空'
            })
    
    # 2. VWAP信号
    if vwap:
        if current_price > vwap * 1.01:
            # 价格在VWAP上方，可能回调
            if vwap < current_price * 0.99:
                entry_model = "VWAP"
                if pinbar_signal and pinbar_signal['type'] == 'bearish':
                    entry_model += " + Pinbar确认"
                
                signals.append({
                    'type': 'short',
                    'strength': 'weak',
                    'entry': current_price * 1.005,
                    'stop_loss': current_price * 1.02,
                    'take_profit_1': vwap * 1.01,
                    'take_profit_2': vwap,
                    'entry_model': entry_model,
                    'reason': f'【{entry_model}】价格在VWAP({vwap:.0f})上方，可能回调到VWAP'
                })
        elif current_price < vwap * 0.99:
            # 价格在VWAP下方，可能反弹
            entry_model = "VWAP"
            if pinbar_signal and pinbar_signal['type'] == 'bullish':
                entry_model += " + Pinbar确认"
            
            signals.append({
                'type': 'long',
                'strength': 'weak',
                'entry': current_price * 0.995,
                'stop_loss': current_price * 0.98,
                'take_profit_1': vwap * 0.99,
                'take_profit_2': vwap,
                'entry_model': entry_model,
                'reason': f'【{entry_model}】价格在VWAP({vwap:.0f})下方，可能反弹到VWAP'
            })
    
    # 3. FVG信号（ICT海龟汤相关）
    # 注意：5分钟级别的FVG太小，不够可靠，De.系统核心不是FVG回填
    # 因此5分钟时间框架不生成FVG回填信号，只在15分钟和1小时使用
    if timeframe_name != '5分钟':
        for fvg in fvgs:
            if fvg['type'] == 'bullish' and current_price < fvg['price']:
                # 上涨FVG在价格上方，可能回填
                entry_model = "FVG回填"
                if pinbar_signal and pinbar_signal['type'] == 'bullish':
                    entry_model += " + Pinbar确认"
                
                signals.append({
                    'type': 'long',
                    'strength': 'medium',  # 降低强度（从strong改为medium），因为FVG回填不是De.核心策略
                    'entry': fvg['low'] * 0.99,
                    'stop_loss': fvg['low'] * 0.97,
                    'take_profit_1': fvg['high'] * 1.01,
                    'take_profit_2': fvg['high'] * 1.02,
                    'entry_model': entry_model,
                    'reason': f'【{entry_model}】上涨FVG做多机会，FVG区间({fvg["low"]:.0f}-{fvg["high"]:.0f})，价格可能回填到{fvg["high"]:.0f}',
                    'pattern_priority': -1  # 最低优先级，因为FVG回填不是De.核心策略
                })
            elif fvg['type'] == 'bearish' and current_price > fvg['price']:
                # 下跌FVG在价格下方，可能回填
                entry_model = "FVG回填"
                if pinbar_signal and pinbar_signal['type'] == 'bearish':
                    entry_model += " + Pinbar确认"
                
                signals.append({
                    'type': 'short',
                    'strength': 'medium',  # 降低强度（从strong改为medium），因为FVG回填不是De.核心策略
                    'entry': fvg['high'] * 1.01,
                    'stop_loss': fvg['high'] * 1.03,
                    'take_profit_1': fvg['low'] * 0.99,
                    'take_profit_2': fvg['low'] * 0.98,
                    'entry_model': entry_model,
                    'reason': f'【{entry_model}】下跌FVG做空机会，FVG区间({fvg["low"]:.0f}-{fvg["high"]:.0f})，价格可能回填到{fvg["low"]:.0f}',
                    'pattern_priority': -1  # 最低优先级，因为FVG回填不是De.核心策略
                })
    
    # 4. 支撑阻力信号（优先使用量能大的支撑阻力位）
    # 量能大的那个位置才是真正的支撑阻力
    if ENHANCED_ANALYSIS_AVAILABLE and enhanced_sr.get('high_volume_support'):
        # 优先使用量能大的支撑位
        nearest_support = max(enhanced_sr['high_volume_support'])
        if current_price < nearest_support * 1.01:
            entry_model = "支撑位反弹(量能大)"
            if pinbar_signal and pinbar_signal['type'] == 'bullish':
                entry_model += " + Pinbar确认"
            
            signals.append({
                'type': 'long',
                'strength': 'strong',  # 量能大的支撑位，信号强度更高
                'entry': nearest_support * 1.002,
                'stop_loss': nearest_support * 0.98,
                'take_profit_1': current_price * 1.01,
                'take_profit_2': current_price * 1.02,
                'entry_model': entry_model,
                'reason': f'【{entry_model}】价格接近量能大的支撑位{nearest_support:.0f}（真正的支撑），可能反弹'
            })
    elif sr.get('support'):
        # 如果没有量能分析，使用普通支撑位
        nearest_support = max(sr['support'])
        if current_price < nearest_support * 1.01:
            entry_model = "支撑位反弹"
            if pinbar_signal and pinbar_signal['type'] == 'bullish':
                entry_model += " + Pinbar确认"
            
            signals.append({
                'type': 'long',
                'strength': 'medium',
                'entry': nearest_support * 1.002,
                'stop_loss': nearest_support * 0.98,
                'take_profit_1': current_price * 1.01,
                'take_profit_2': current_price * 1.02,
                'entry_model': entry_model,
                'reason': f'【{entry_model}】价格接近支撑位{nearest_support:.0f}，可能反弹'
            })
    
    if ENHANCED_ANALYSIS_AVAILABLE and enhanced_sr.get('high_volume_resistance'):
        # 优先使用量能大的阻力位
        nearest_resistance = min(enhanced_sr['high_volume_resistance'])
        if current_price > nearest_resistance * 0.99:
            entry_model = "阻力位回落(量能大)"
            if pinbar_signal and pinbar_signal['type'] == 'bearish':
                entry_model += " + Pinbar确认"
            
            signals.append({
                'type': 'short',
                'strength': 'strong',  # 量能大的阻力位，信号强度更高
                'entry': nearest_resistance * 0.998,
                'stop_loss': nearest_resistance * 1.02,
                'take_profit_1': current_price * 0.99,
                'take_profit_2': current_price * 0.98,
                'entry_model': entry_model,
                'reason': f'【{entry_model}】价格接近量能大的阻力位{nearest_resistance:.0f}（真正的阻力），可能回落'
            })
    elif sr.get('resistance'):
        # 如果没有量能分析，使用普通阻力位
        nearest_resistance = min(sr['resistance'])
        if current_price > nearest_resistance * 0.99:
            entry_model = "阻力位回落"
            if pinbar_signal and pinbar_signal['type'] == 'bearish':
                entry_model += " + Pinbar确认"
            
            signals.append({
                'type': 'short',
                'strength': 'medium',
                'entry': nearest_resistance * 0.998,
                'stop_loss': nearest_resistance * 1.02,
                'take_profit_1': current_price * 0.99,
                'take_profit_2': current_price * 0.98,
                'entry_model': entry_model,
                'reason': f'【{entry_model}】价格接近阻力位{nearest_resistance:.0f}，可能回落'
            })
    
    # 5. 区间突破信号（做好区间突破推止盈，大概率能拿到大收获）
    if ENHANCED_ANALYSIS_AVAILABLE and consolidation_ranges:
        breakout_opportunities = identify_interval_breakout_opportunities(
            klines, consolidation_ranges, current_price
        )
        
        for opp in breakout_opportunities:
            range_info = opp['range']
            if opp['type'] == 'long':
                signals.append({
                    'type': 'long',
                    'strength': 'strong' if range_info['strength'] == 'strong' else 'medium',
                    'entry': current_price * 1.001,  # 突破后稍微回调入场
                    'stop_loss': opp['breakout_price'] * 0.998,  # 止损在突破位下方
                    'take_profit_1': opp['target_1'],
                    'take_profit_2': opp['target_2'],
                    'entry_model': opp['entry_model'],
                    'reason': opp['reason']
                })
            elif opp['type'] == 'short':
                signals.append({
                    'type': 'short',
                    'strength': 'strong' if range_info['strength'] == 'strong' else 'medium',
                    'entry': current_price * 0.999,  # 突破后稍微反弹入场
                    'stop_loss': opp['breakout_price'] * 1.002,  # 止损在突破位上方
                    'take_profit_1': opp['target_1'],
                    'take_profit_2': opp['target_2'],
                    'entry_model': opp['entry_model'],
                    'reason': opp['reason']
                })
    
    # 6. 纯Pinbar信号（如果没有其他信号配合）
    if pinbar_signal and not any('Pinbar' in s.get('entry_model', '') for s in signals):
        if pinbar_signal['type'] == 'bullish' and len(klines) >= 1:
            last_k = klines[-1]
            entry_model = "Pinbar"
            entry = last_k['close'] * 1.001
            stop_loss = last_k['low'] * 0.998
            risk = entry - stop_loss
            if risk > 0:
                take_profit_1 = entry + risk * 2.5
                take_profit_2 = entry + risk * 3.5
            else:
                take_profit_1 = entry * 1.025
                take_profit_2 = entry * 1.035
            
            signals.append({
                'type': 'long',
                'strength': 'medium',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'entry_model': entry_model,
                'reason': f'【{entry_model}】看涨Pinbar形态，下影线占比{pinbar_signal["shadow_ratio"]*100:.1f}%，反转信号'
            })
        elif pinbar_signal['type'] == 'bearish' and len(klines) >= 1:
            last_k = klines[-1]
            entry_model = "Pinbar"
            entry = last_k['close'] * 0.999
            stop_loss = last_k['high'] * 1.002
            risk = stop_loss - entry
            if risk > 0:
                take_profit_1 = entry - risk * 2.5
                take_profit_2 = entry - risk * 3.5
            else:
                take_profit_1 = entry * 0.975
                take_profit_2 = entry * 0.965
            
            signals.append({
                'type': 'short',
                'strength': 'medium',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'entry_model': entry_model,
                'reason': f'【{entry_model}】看跌Pinbar形态，上影线占比{pinbar_signal["shadow_ratio"]*100:.1f}%，反转信号'
            })
    
    return {
        'timeframe': timeframe_name,
        'current_price': current_price,
        'ema_144': ema_144,
        'ema_169': ema_169,
        'vwap': vwap,
        'rsi': rsi,
        'fvgs': fvgs,
        'support_resistance': enhanced_sr if ENHANCED_ANALYSIS_AVAILABLE else sr,
        'volume_profile': volume_profile,
        'consolidation_ranges': consolidation_ranges,
        'is_garbage_time': is_garbage,
        'garbage_range': garbage_range,
        'ote_analysis': ote_analysis,
        'order_blocks': order_blocks,
        'signals': signals
    }

def get_orderbook_stop_loss(entry_price, signal_type, current_price):
    """获取基于实时订单簿的止损价格"""
    if not ORDERBOOK_AVAILABLE:
        return None, None
    
    try:
        # 获取实时订单簿
        order_book, exchange_name = get_order_book_with_retry('BTC', limit=50)
        if not order_book:
            return None, None
        
        # 计算基于订单簿的止损
        stop_loss, info = calculate_stop_loss_by_orderbook(
            entry_price, signal_type, order_book, current_price
        )
        
        if stop_loss and info:
            return stop_loss, {
                'stop_loss': stop_loss,
                'info': info,
                'exchange': exchange_name,
                'is_from_orderbook': info.get('is_from_orderbook', True)
            }
    except Exception as e:
        print(f"获取订单簿止损失败: {e}", file=sys.stderr)
    
    return None, None

# 全局变量：保存最后一次分析结果（用于信号追踪）
_last_analysis_result = None

# 尝试导入ML预测器（可选）
try:
    from ml_signal_predictor import MLSignalPredictor
    ML_PREDICTOR_AVAILABLE = True
except ImportError:
    ML_PREDICTOR_AVAILABLE = False
    MLSignalPredictor = None

# 尝试导入图表形态识别模块（可选）
try:
    from chart_patterns_detector import ChartPatternsDetector
    PATTERN_DETECTOR_AVAILABLE = True
except ImportError:
    PATTERN_DETECTOR_AVAILABLE = False
    ChartPatternsDetector = None

# 尝试导入下降趋势识别模块（可选）
try:
    from downtrend_detector import DowntrendDetector
    DOWNTREND_DETECTOR_AVAILABLE = True
except ImportError:
    DOWNTREND_DETECTOR_AVAILABLE = False
    DowntrendDetector = None

# 尝试导入主力洗盘场景识别模块（可选）
try:
    from main_force_washout_detector import MainForceWashoutDetector
    WASHOUT_DETECTOR_AVAILABLE = True
except ImportError:
    WASHOUT_DETECTOR_AVAILABLE = False
    MainForceWashoutDetector = None

# 尝试导入K线起飞形态识别模块（可选）
try:
    from candlestick_takeoff_patterns import CandlestickTakeoffPatterns
    TAKEOFF_PATTERNS_AVAILABLE = True
except ImportError:
    TAKEOFF_PATTERNS_AVAILABLE = False
    CandlestickTakeoffPatterns = None

# 尝试导入看涨图表形态识别模块（可选，带交易信号）
try:
    from bullish_patterns_with_signals import BullishPatternsWithSignals
    BULLISH_PATTERNS_AVAILABLE = True
except ImportError:
    BULLISH_PATTERNS_AVAILABLE = False
    BullishPatternsWithSignals = None

# 尝试导入顶级交易员常用形态识别模块（可选，统一接口，24种形态）
try:
    from top_trader_patterns import TopTraderPatterns
    TOP_TRADER_PATTERNS_AVAILABLE = True
except ImportError:
    TOP_TRADER_PATTERNS_AVAILABLE = False
    TopTraderPatterns = None

# 尝试导入滚仓策略模块（可选）
try:
    from rolling_position_manager import RollingPositionManager
    ROLLING_POSITION_AVAILABLE = True
except ImportError:
    ROLLING_POSITION_AVAILABLE = False
    RollingPositionManager = None

def generate_trading_plan():
    """生成交易计划"""
    global _last_analysis_result
    print("正在获取BTC市场数据...", file=sys.stderr)
    
    # 初始化ML预测器（如果可用）
    ml_predictor = None
    if ML_PREDICTOR_AVAILABLE:
        try:
            ml_predictor = MLSignalPredictor()
            if ml_predictor.is_trained:
                print("✓ ML模型已加载，将为信号添加成功率预测", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  ML预测器初始化失败: {e}", file=sys.stderr)
    
    # 获取数据（先尝试Gate.io，失败再尝试Bitget）
    current_price = get_btc_current_price()
    klines_5m = get_btc_kline_gateio('5m', 200)
    klines_15m = get_btc_kline_gateio('15m', 200)
    klines_1h = get_btc_kline_gateio('1h', 100)
    
    if not klines_5m:
        print("尝试从Bitget获取数据...", file=sys.stderr)
        klines_5m = get_btc_kline_bitget('5m', 200)
        klines_15m = get_btc_kline_bitget('15m', 200)
        klines_1h = get_btc_kline_bitget('1h', 100)
        if not current_price:
            current_price = get_btc_current_price()
    
    if not current_price or not klines_5m or not klines_15m:
        print("无法获取市场数据", file=sys.stderr)
        return
    
    # 使用最新K线价格
    if abs(klines_15m[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_15m[-1]['close']
    
    # 分析各时间框架
    analysis_5m = analyze_timeframe(klines_5m, '5分钟', current_price)
    analysis_15m = analyze_timeframe(klines_15m, '15分钟', current_price)
    analysis_1h = analyze_timeframe(klines_1h, '1小时', current_price) if klines_1h else None
    
    # 图表形态识别（作为独立信号来源）
    chart_pattern_signals_5m = []
    chart_pattern_signals_15m = []
    chart_pattern_signals_1h = []
    
    if PATTERN_DETECTOR_AVAILABLE:
        try:
            pattern_detector = ChartPatternsDetector()
            
            # 5分钟时间框架形态识别
            pattern_result_5m = pattern_detector.detect_all_patterns(klines_5m)
            if pattern_result_5m['reversal_patterns'] or pattern_result_5m['continuation_patterns']:
                # 将形态转换为交易信号
                for pattern in pattern_result_5m['reversal_patterns'] + pattern_result_5m['continuation_patterns']:
                    if pattern.get('entry') and pattern.get('stop_loss') and pattern.get('take_profit'):
                        signal_type = 'short' if 'bearish' in pattern['type'] else 'long'
                        
                        # 优化入场价：如果入场价距离当前价格太远，调整到合理位置
                        entry = pattern.get('entry')
                        entry_reason = pattern.get('entry_reason', '')
                        if entry and current_price:
                            price_distance = abs(entry - current_price) / current_price
                            if signal_type == 'long' and entry > current_price * 1.02:
                                # 做多入场价高于当前价格超过2%，调整到当前价格上方0.5-1%等待突破
                                entry = current_price * 1.008  # 当前价格上方0.8%，等待突破
                                if not entry_reason:
                                    entry_reason = f"入场价已调整到{entry:.0f}（当前价格上方0.8%，等待突破）"
                            elif signal_type == 'short':
                                # 做空入场价必须高于当前价格（等待反弹到阻力位）
                                if entry <= current_price:
                                    # 如果入场价低于或等于当前价格，必须调整到当前价格上方
                                    # 优先使用形态的阻力位，如果没有则使用当前价格上方
                                    if pattern.get('resistance') and pattern['resistance'] > current_price:
                                        entry = max(pattern['resistance'] * 1.002, current_price * 1.002)  # 阻力位上方0.2%，但至少高于当前价格0.2%
                                        entry_reason = f"入场价已调整到{entry:.0f}（等待反弹到阻力位{pattern['resistance']:.0f}上方，至少高于当前价格0.2%）"
                                    elif pattern.get('neckline') and pattern['neckline'] > current_price:
                                        # 三重顶等形态可能有颈线作为阻力位
                                        entry = max(pattern['neckline'] * 1.002, current_price * 1.002)
                                        entry_reason = f"入场价已调整到{entry:.0f}（等待反弹到颈线{pattern['neckline']:.0f}上方）"
                                    else:
                                        # 默认调整到当前价格上方0.3-0.5%，等待反弹
                                        entry = current_price * 1.003  # 当前价格上方0.3%，等待反弹
                                        entry_reason = f"入场价已调整到{entry:.0f}（当前价格上方0.3%，等待反弹到阻力位）"
                                elif entry > current_price * 1.02:
                                    # 入场价高于当前价格超过2%，调整到合理位置
                                    entry = current_price * 1.008  # 当前价格上方0.8%，等待反弹
                                    if not entry_reason:
                                        entry_reason = f"入场价已调整到{entry:.0f}（当前价格上方0.8%，等待反弹）"
                        
                        # 计算第二个止盈位
                        risk = abs(entry - pattern['stop_loss'])
                        if risk > 0:
                            if signal_type == 'long':
                                take_profit_1 = pattern['take_profit']
                                take_profit_2 = entry + risk * 2.5
                            else:
                                take_profit_1 = pattern['take_profit']
                                take_profit_2 = entry - risk * 2.5
                        else:
                            take_profit_1 = pattern['take_profit']
                            take_profit_2 = pattern['take_profit']
                        
                        # 构建入场理由，包含入场价设置说明
                        if entry_reason:
                            reason_text = f"识别到{pattern['name']}形态（置信度: {pattern['confidence']:.1f}%），{pattern['type']}信号。{entry_reason}"
                        else:
                            reason_text = f"识别到{pattern['name']}形态（置信度: {pattern['confidence']:.1f}%），{pattern['type']}信号"
                        
                        signal_dict = {
                            'type': signal_type,
                            'strength': 'strong' if pattern['confidence'] > 75 else 'medium',
                            'entry': entry,
                            'stop_loss': pattern['stop_loss'],
                            'take_profit_1': take_profit_1,
                            'take_profit_2': take_profit_2,
                            'entry_model': f"图表形态-{pattern['name']}",
                            'reason': reason_text
                        }
                        
                        # 验证信号合法性
                        is_valid, error_msg = validate_signal(signal_dict, current_price)
                        if is_valid:
                            chart_pattern_signals_5m.append(signal_dict)
                        else:
                            print(f"5分钟图表形态信号验证失败 ({pattern['name']}): {error_msg}", file=sys.stderr)
            
            # 15分钟时间框架形态识别
            pattern_result_15m = pattern_detector.detect_all_patterns(klines_15m)
            if pattern_result_15m['reversal_patterns'] or pattern_result_15m['continuation_patterns']:
                for pattern in pattern_result_15m['reversal_patterns'] + pattern_result_15m['continuation_patterns']:
                    if pattern.get('entry') and pattern.get('stop_loss') and pattern.get('take_profit'):
                        signal_type = 'short' if 'bearish' in pattern['type'] else 'long'
                        
                        # 优化入场价：如果入场价距离当前价格太远，调整到合理位置
                        entry = pattern.get('entry')
                        entry_reason = pattern.get('entry_reason', '')
                        if entry and current_price:
                            price_distance = abs(entry - current_price) / current_price
                            if signal_type == 'long' and entry > current_price * 1.02:
                                # 做多入场价高于当前价格超过2%，调整到当前价格上方0.5-1%等待突破
                                entry = current_price * 1.008  # 当前价格上方0.8%，等待突破
                                if not entry_reason:
                                    entry_reason = f"入场价已调整到{entry:.0f}（当前价格上方0.8%，等待突破）"
                            elif signal_type == 'short':
                                # 做空入场价必须高于当前价格（等待反弹到阻力位）
                                if entry <= current_price:
                                    # 如果入场价低于或等于当前价格，必须调整到当前价格上方
                                    # 优先使用形态的阻力位，如果没有则使用当前价格上方
                                    if pattern.get('resistance') and pattern['resistance'] > current_price:
                                        entry = max(pattern['resistance'] * 1.002, current_price * 1.002)  # 阻力位上方0.2%，但至少高于当前价格0.2%
                                        entry_reason = f"入场价已调整到{entry:.0f}（等待反弹到阻力位{pattern['resistance']:.0f}上方，至少高于当前价格0.2%）"
                                    elif pattern.get('neckline') and pattern['neckline'] > current_price:
                                        # 三重顶等形态可能有颈线作为阻力位
                                        entry = max(pattern['neckline'] * 1.002, current_price * 1.002)
                                        entry_reason = f"入场价已调整到{entry:.0f}（等待反弹到颈线{pattern['neckline']:.0f}上方）"
                                    else:
                                        # 默认调整到当前价格上方0.3-0.5%，等待反弹
                                        entry = current_price * 1.003  # 当前价格上方0.3%，等待反弹
                                        entry_reason = f"入场价已调整到{entry:.0f}（当前价格上方0.3%，等待反弹到阻力位）"
                                elif entry > current_price * 1.02:
                                    # 入场价高于当前价格超过2%，调整到合理位置
                                    entry = current_price * 1.008  # 当前价格上方0.8%，等待反弹
                                    if not entry_reason:
                                        entry_reason = f"入场价已调整到{entry:.0f}（当前价格上方0.8%，等待反弹）"
                        
                        risk = abs(entry - pattern['stop_loss'])
                        if risk > 0:
                            if signal_type == 'long':
                                take_profit_1 = pattern['take_profit']
                                take_profit_2 = entry + risk * 2.5
                            else:
                                take_profit_1 = pattern['take_profit']
                                take_profit_2 = entry - risk * 2.5
                        else:
                            take_profit_1 = pattern['take_profit']
                            take_profit_2 = pattern['take_profit']
                        
                        # 构建入场理由，包含入场价设置说明
                        if entry_reason:
                            reason_text = f"识别到{pattern['name']}形态（置信度: {pattern['confidence']:.1f}%），{pattern['type']}信号。{entry_reason}"
                        else:
                            reason_text = f"识别到{pattern['name']}形态（置信度: {pattern['confidence']:.1f}%），{pattern['type']}信号"
                        
                        signal_dict = {
                            'type': signal_type,
                            'strength': 'strong' if pattern['confidence'] > 75 else 'medium',
                            'entry': entry,
                            'stop_loss': pattern['stop_loss'],
                            'take_profit_1': take_profit_1,
                            'take_profit_2': take_profit_2,
                            'entry_model': f"图表形态-{pattern['name']}",
                            'reason': reason_text
                        }
                        
                        # 验证信号合法性
                        is_valid, error_msg = validate_signal(signal_dict, current_price)
                        if is_valid:
                            chart_pattern_signals_15m.append(signal_dict)
                        else:
                            print(f"15分钟图表形态信号验证失败 ({pattern['name']}): {error_msg}", file=sys.stderr)
        except Exception as e:
            print(f"图表形态识别失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # 下降趋势识别（用于趋势确认）
    if DOWNTREND_DETECTOR_AVAILABLE:
        try:
            downtrend_detector = DowntrendDetector()
            
            # 5分钟时间框架下降趋势识别
            downtrend_signals_5m = downtrend_detector.detect_all_downtrend_signals(klines_5m)
            
            # 15分钟时间框架下降趋势识别
            downtrend_signals_15m = downtrend_detector.detect_all_downtrend_signals(klines_15m)
        except Exception as e:
            print(f"下降趋势识别失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # 主力洗盘场景识别（用于做多机会确认）
    washout_scenarios_5m = None
    washout_scenarios_15m = None
    
    if WASHOUT_DETECTOR_AVAILABLE:
        try:
            washout_detector = MainForceWashoutDetector()
            
            # 5分钟时间框架主力洗盘场景识别
            washout_scenarios_5m = washout_detector.detect_all_washout_scenarios(klines_5m)
            
            # 15分钟时间框架主力洗盘场景识别
            washout_scenarios_15m = washout_detector.detect_all_washout_scenarios(klines_15m)
        except Exception as e:
            print(f"主力洗盘场景识别失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # K线起飞形态识别（用于做多信号确认）
    takeoff_patterns_5m = None
    takeoff_patterns_15m = None
    takeoff_patterns_1h = None
    
    if TAKEOFF_PATTERNS_AVAILABLE:
        try:
            takeoff_detector = CandlestickTakeoffPatterns()
            
            # 5分钟时间框架K线起飞形态识别
            takeoff_patterns_5m = takeoff_detector.detect_all_takeoff_patterns(klines_5m)
            
            # 15分钟时间框架K线起飞形态识别
            takeoff_patterns_15m = takeoff_detector.detect_all_takeoff_patterns(klines_15m)
            
            # 1小时时间框架K线起飞形态识别（形态更容易在长时间框架识别）
            if klines_1h:
                takeoff_patterns_1h = takeoff_detector.detect_all_takeoff_patterns(klines_1h)
        except Exception as e:
            print(f"K线起飞形态识别失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # 顶级交易员常用形态识别（24种形态，统一接口）
    top_trader_patterns_5m = None
    top_trader_patterns_15m = None
    top_trader_patterns_1h = None
    
    if TOP_TRADER_PATTERNS_AVAILABLE:
        try:
            top_trader_detector = TopTraderPatterns()
            
            # 5分钟时间框架顶级交易员形态识别
            top_trader_patterns_5m = top_trader_detector.detect_all_patterns(klines_5m)
            
            # 15分钟时间框架顶级交易员形态识别
            top_trader_patterns_15m = top_trader_detector.detect_all_patterns(klines_15m)
            
            # 1小时时间框架顶级交易员形态识别（形态更容易在长时间框架识别）
            if klines_1h:
                top_trader_patterns_1h = top_trader_detector.detect_all_patterns(klines_1h)
        except Exception as e:
            print(f"顶级交易员形态识别失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # 看涨图表形态识别（带交易信号）
    bullish_patterns_5m = None
    bullish_patterns_15m = None
    bullish_patterns_1h = None
    
    if BULLISH_PATTERNS_AVAILABLE:
        try:
            bullish_detector = BullishPatternsWithSignals()
            
            # 5分钟时间框架看涨形态识别
            bullish_patterns_5m = bullish_detector.detect_all_bullish_patterns(klines_5m)
            
            # 15分钟时间框架看涨形态识别
            bullish_patterns_15m = bullish_detector.detect_all_bullish_patterns(klines_15m)
            
            # 1小时时间框架看涨形态识别（形态更容易在长时间框架识别）
            if klines_1h:
                bullish_patterns_1h = bullish_detector.detect_all_bullish_patterns(klines_1h)
        except Exception as e:
            print(f"看涨图表形态识别失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    # 为每个信号获取实时订单簿止损（包括形态识别信号）
    all_signals_to_process = []
    
    if analysis_5m and analysis_5m['signals']:
        all_signals_to_process.extend([(s, '5m') for s in analysis_5m['signals']])
    
    if analysis_15m and analysis_15m['signals']:
        all_signals_to_process.extend([(s, '15m') for s in analysis_15m['signals']])
    
    if chart_pattern_signals_5m:
        all_signals_to_process.extend([(s, '5m') for s in chart_pattern_signals_5m])
    
    if chart_pattern_signals_15m:
        all_signals_to_process.extend([(s, '15m') for s in chart_pattern_signals_15m])
    
    if bullish_patterns_5m and bullish_patterns_5m.get('patterns'):
        for pattern in bullish_patterns_5m['patterns']:
            risk = abs(pattern['entry'] - pattern['stop_loss'])
            take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
            take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
            signal = {
                'type': 'long',
                'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                'entry': pattern['entry'],
                'stop_loss': pattern['stop_loss'],
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'entry_model': f"看涨形态-{pattern['name']}",
                'reason': pattern['description']
            }
            all_signals_to_process.append((signal, '5m'))
    
    if bullish_patterns_15m and bullish_patterns_15m.get('patterns'):
        for pattern in bullish_patterns_15m['patterns']:
            risk = abs(pattern['entry'] - pattern['stop_loss'])
            take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
            take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
            signal = {
                'type': 'long',
                'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                'entry': pattern['entry'],
                'stop_loss': pattern['stop_loss'],
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'entry_model': f"看涨形态-{pattern['name']}",
                'reason': pattern['description']
            }
            all_signals_to_process.append((signal, '15m'))
    
    if top_trader_patterns_5m and top_trader_patterns_5m.get('all_signals'):
        for signal in top_trader_patterns_5m['all_signals']:
            if signal.get('entry') and signal.get('stop_loss'):
                all_signals_to_process.append((signal, '5m'))
    
    if top_trader_patterns_15m and top_trader_patterns_15m.get('all_signals'):
        for signal in top_trader_patterns_15m['all_signals']:
            if signal.get('entry') and signal.get('stop_loss'):
                all_signals_to_process.append((signal, '15m'))
    
    # 添加1小时形态识别信号（优先级最高，因为形态在长时间框架更容易识别）
    if chart_pattern_signals_1h:
        all_signals_to_process.extend([(s, '1h') for s in chart_pattern_signals_1h])
    
    if bullish_patterns_1h and bullish_patterns_1h.get('patterns'):
        for pattern in bullish_patterns_1h['patterns']:
            risk = abs(pattern['entry'] - pattern['stop_loss'])
            take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
            take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
            signal = {
                'type': 'long',
                'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                'entry': pattern['entry'],
                'stop_loss': pattern['stop_loss'],
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'entry_model': f"看涨形态-{pattern['name']}",
                'reason': pattern['description']
            }
            all_signals_to_process.append((signal, '1h'))
    
    if top_trader_patterns_1h and top_trader_patterns_1h.get('all_signals'):
        for signal in top_trader_patterns_1h['all_signals']:
            if signal.get('entry') and signal.get('stop_loss'):
                all_signals_to_process.append((signal, '1h'))
    
    # 验证所有信号的合法性（在获取订单簿止损之前）
    valid_signals_to_process = []
    for signal, timeframe in all_signals_to_process:
        is_valid, error_msg = validate_signal(signal, current_price)
        if is_valid:
            valid_signals_to_process.append((signal, timeframe))
        else:
            print(f"信号验证失败 ({timeframe}, {signal.get('entry_model', '未知')}): {error_msg}", file=sys.stderr)
    
    # 最终验证：在所有处理完成后，再次严格验证所有信号
    # 确保不会有任何不合理的信号被输出
    final_valid_signals = []
    for signal, timeframe in valid_signals_to_process:
        is_valid, error_msg = validate_signal(signal, current_price, tolerance_pct=0.001)  # 更严格的验证（0.1%容差）
        if is_valid:
            final_valid_signals.append((signal, timeframe))
        else:
            print(f"⚠️ 最终验证失败，信号已过滤 ({timeframe}, {signal.get('entry_model', '未知')}): {error_msg}", file=sys.stderr)
    
    # 使用最终验证后的信号列表
    valid_signals_to_process = final_valid_signals
    
    # 为所有有效信号获取订单簿止损
    if valid_signals_to_process:
        print(f"正在为 {len(valid_signals_to_process)} 个有效信号获取实时订单簿止损...", file=sys.stderr)
        for signal, timeframe in valid_signals_to_process:
            ob_stop_loss, ob_info = get_orderbook_stop_loss(
                signal['entry'], signal['type'], current_price
            )
            if ob_stop_loss:
                signal['orderbook_stop_loss'] = ob_stop_loss
                signal['orderbook_info'] = ob_info
            else:
                signal['orderbook_stop_loss'] = None
                signal['orderbook_info'] = None
    
    # 生成简要版交易计划（只包含核心信号）
    brief_plan = []
    brief_plan.append("# BTC 交易信号（简要版）")
    brief_plan.append("")
    brief_plan.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    brief_plan.append(f"**当前价格**: ${current_price:,.2f}  ")
    brief_plan.append("**数据来源**: Gate.io / Bitget  ")
    brief_plan.append("")
    
    # 生成详细版交易计划（包含所有说明）
    plan = []
    plan.append("# BTC 交易信号（青鸟交易系统 - De.策略）")
    plan.append("")
    plan.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    plan.append(f"**当前价格**: ${current_price:,.2f}  ")
    plan.append("**数据来源**: Gate.io / Bitget  ")
    plan.append("")
    
    # 一、5分钟交易信号（简明）
    plan.append("## 一、5分钟交易信号")
    plan.append("")
    
    if analysis_5m:
        if analysis_5m['is_garbage_time']:
            plan.append("⚠️ **垃圾时间**: 建议等待突破")
            plan.append(f"   区间: ${analysis_5m['garbage_range'][0]:,.0f} - ${analysis_5m['garbage_range'][1]:,.0f}")
            plan.append("")
        
        # 合并图表形态信号和原有信号（形态识别信号优先级更高）
        all_signals_5m = []
        
        # 先添加形态识别信号（优先级高）
        if chart_pattern_signals_5m:
            all_signals_5m.extend(chart_pattern_signals_5m)
        
        if bullish_patterns_5m and bullish_patterns_5m.get('patterns'):
            for pattern in bullish_patterns_5m['patterns']:
                risk = abs(pattern['entry'] - pattern['stop_loss'])
                take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
                take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
                all_signals_5m.append({
                    'type': 'long',
                    'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                    'entry': pattern['entry'],
                    'stop_loss': pattern['stop_loss'],
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'entry_model': f"看涨形态-{pattern['name']}",
                    'reason': pattern['description'],
                    'pattern_priority': 1  # 形态识别优先级标记
                })
        
        if top_trader_patterns_5m and top_trader_patterns_5m.get('all_signals'):
            for signal in top_trader_patterns_5m['all_signals']:
                if signal.get('entry') and signal.get('stop_loss'):
                    risk = abs(signal['entry'] - signal['stop_loss'])
                    take_profit_1 = signal['entry'] + (risk * 2 if signal['type'] == 'long' else -risk * 2) if risk > 0 else (signal['entry'] * 1.02 if signal['type'] == 'long' else signal['entry'] * 0.98)
                    take_profit_2 = signal['entry'] + (risk * 3 if signal['type'] == 'long' else -risk * 3) if risk > 0 else (signal['entry'] * 1.04 if signal['type'] == 'long' else signal['entry'] * 0.96)
                    all_signals_5m.append({
                        'type': signal['type'],
                        'strength': 'strong' if signal.get('strength', 0) > 75 else 'medium',
                        'entry': signal['entry'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit_1': take_profit_1,
                        'take_profit_2': take_profit_2,
                        'entry_model': signal.get('entry_model', f"顶级交易员形态-{signal.get('name', '未知')}"),
                        'reason': signal.get('reason', f"识别到{signal.get('name', '形态')}"),
                        'pattern_priority': 1  # 形态识别优先级标记
                    })
        
        # 再添加Vegas等基础信号（优先级较低）
        if analysis_5m.get('signals'):
            for signal in analysis_5m['signals']:
                signal['pattern_priority'] = 0  # 基础信号优先级标记
                all_signals_5m.append(signal)
        
        if all_signals_5m:
            # 优先选择形态识别信号，然后按强度排序
            def signal_score(s):
                priority = s.get('pattern_priority', 0) * 10  # 形态识别信号加分
                strength = 3 if s['strength'] == 'strong' else 2 if s['strength'] == 'medium' else 1
                return priority + strength
            
            best_signal = max(all_signals_5m, key=signal_score)
            
            # 如果best_signal还没有订单簿止损，尝试获取
            if not best_signal.get('orderbook_stop_loss'):
                ob_stop_loss, ob_info = get_orderbook_stop_loss(
                    best_signal['entry'], best_signal['type'], current_price
                )
                if ob_stop_loss:
                    best_signal['orderbook_stop_loss'] = ob_stop_loss
                    best_signal['orderbook_info'] = ob_info
            
            # 添加波动率分析和建议
            if VOLATILITY_ANALYZER_AVAILABLE and klines_5m:
                try:
                    atr_percent = calculate_atr_percent(klines_5m, period=14)
                    volatility_assessment = assess_volatility_level(atr_percent)
                    
                    plan.append(f"**市场波动率**: {volatility_assessment['description']} (ATR: {atr_percent:.2f}%)")
                    plan.append(f"   {volatility_assessment['recommendation']}")
                    
                    # 如果波动率较高，给出止损建议
                    if volatility_assessment['level'] in ['high', 'very_high']:
                        current_stop_distance = abs(best_signal['entry'] - best_signal['stop_loss']) / best_signal['entry'] * 100
                        suggested_stop_distance = current_stop_distance * volatility_assessment['stop_loss_multiplier']
                        plan.append(f"   ⚠️ 建议止损距离: {suggested_stop_distance:.2f}% (当前: {current_stop_distance:.2f}%)")
                except Exception as e:
                    print(f"5分钟波动率分析失败: {e}", file=sys.stderr)
            
            # 显示所有识别到的形态（如果有多个）
            pattern_signals = [s for s in all_signals_5m if s.get('pattern_priority', 0) > 0]
            if len(pattern_signals) > 1:
                plan.append(f"**识别到 {len(pattern_signals)} 个形态信号**，已选择最强信号")
                plan.append("")
            
            # 使用ML模型预测成功率（如果可用）
            if ml_predictor and ml_predictor.is_trained:
                try:
                    ml_prediction = ml_predictor.predict_signal_success(best_signal)
                    best_signal['ml_score'] = ml_prediction['success_probability']
                    best_signal['ml_confidence'] = ml_prediction['confidence']
                    best_signal['ml_prediction'] = ml_prediction['prediction']
                except Exception as e:
                    pass  # ML预测失败时不影响信号生成
            
            direction = "做多" if best_signal['type'] == 'long' else "做空"
            strength = "强" if best_signal['strength'] == 'strong' else "中" if best_signal['strength'] == 'medium' else "弱"
            
            plan.append(f"**{direction}** ({strength})")
            plan.append(f"入场: ${best_signal['entry']:,.0f}")
            
            # 显示技术指标止损（主要止损）
            tech_distance = abs(best_signal['entry'] - best_signal['stop_loss'])
            tech_distance_pct = (tech_distance / best_signal['entry']) * 100
            plan.append(f"止损: ${best_signal['stop_loss']:,.0f} (技术指标，距离: {tech_distance_pct:.2f}%)")
            
            # 同时显示订单簿止损（参考止损）
            if best_signal.get('orderbook_stop_loss'):
                ob_info = best_signal.get('orderbook_info', {})
                ob_stop = best_signal['orderbook_stop_loss']
                is_from_ob = ob_info.get('is_from_orderbook', True)
                ob_status = "[实时订单簿]" if is_from_ob else "[备用方案]"
                ob_distance = abs(best_signal['entry'] - ob_stop)
                ob_distance_pct = (ob_distance / best_signal['entry']) * 100
                plan.append(f"参考止损: ${ob_stop:,.0f} {ob_status} (距离: {ob_distance_pct:.2f}%)")
                if ob_info.get('info', {}).get('reason'):
                    plan.append(f"   理由: {ob_info['info']['reason']}")
            
            plan.append(f"止盈: ${best_signal['take_profit_1']:,.0f} (50%) / ${best_signal['take_profit_2']:,.0f} (50%)")
            
            # 计算并显示盈亏比（使用技术止损作为主要计算依据）
            if VOLATILITY_ANALYZER_AVAILABLE:
                try:
                    stop_loss_price = best_signal['stop_loss']  # 预生成信号使用技术止损
                    rr_analysis = calculate_risk_reward_ratio(
                        entry=best_signal['entry'],
                        stop_loss=stop_loss_price,
                        take_profit_1=best_signal['take_profit_1'],
                        take_profit_2=best_signal['take_profit_2'],
                        signal_type=best_signal['type']
                    )
                    
                    quality_map = {
                        'excellent': '优秀（≥3.0）',
                        'good': '良好（2.0-3.0）',
                        'acceptable': '可接受（1.5-2.0）',
                        'poor': '较低（1.0-1.5）',
                        'very_poor': '过低（<1.0）'
                    }
                    quality_emoji = {
                        'excellent': '✅✅',
                        'good': '✅',
                        'acceptable': '⚠️',
                        'poor': '⚠️',
                        'very_poor': '❌'
                    }
                    quality = quality_map.get(rr_analysis['quality'], '未知')
                    emoji = quality_emoji.get(rr_analysis['quality'], '')
                    
                    plan.append(f"**预期盈亏比**: {rr_analysis['avg_rr_ratio']:.2f}:1 {emoji} ({quality})")
                    plan.append(f"   - 风险: ${rr_analysis['risk']:,.0f} ({abs(best_signal['entry'] - stop_loss_price) / best_signal['entry'] * 100:.2f}%)")
                    plan.append(f"   - 止盈1回报: ${rr_analysis['reward_1']:,.0f} ({rr_analysis['rr_ratio_1']:.2f}:1)")
                    plan.append(f"   - 止盈2回报: ${rr_analysis['reward_2']:,.0f} ({rr_analysis['rr_ratio_2']:.2f}:1)")
                except Exception as e:
                    print(f"5分钟盈亏比计算失败: {e}", file=sys.stderr)
            
            # 明确标注入场模型和入场原因
            entry_model = best_signal.get('entry_model', '未知模型')
            plan.append(f"**入场模型**: {entry_model}")
            plan.append(f"**入场原因**: {best_signal.get('reason', '无详细说明')}")
            
            # 添加ML预测结果（如果可用）
            if best_signal.get('ml_score') is not None:
                ml_score = best_signal['ml_score']
                ml_confidence = best_signal.get('ml_confidence', 0)
                ml_pred = "成功" if best_signal.get('ml_prediction') == 1 else "失败"
                plan.append(f"**ML预测成功率**: {ml_score:.1%} (预测: {ml_pred}, 置信度: {ml_confidence:.1%})")
            
            plan.append("")
            
            # 滚仓策略建议（如果可用）
            if ROLLING_POSITION_AVAILABLE and best_signal:
                try:
                    rolling_manager = RollingPositionManager()
                    rolling_analysis = rolling_manager.analyze_signal_for_rolling(best_signal, current_price)
                    
                    if rolling_analysis.get('suitable'):
                        plan.append("---")
                        plan.append("")
                        plan.append("### 💰 滚仓策略建议")
                        plan.append("")
                        
                        if rolling_analysis.get('suggestion'):
                            rolling_lines = rolling_manager.format_rolling_suggestion(rolling_analysis['suggestion'])
                            plan.extend(rolling_lines)
                        else:
                            plan.append(f"**分析结果**: {rolling_analysis.get('reason', '适合滚仓策略')}")
                            plan.append(f"**风险回报比**: {rolling_analysis.get('risk_reward_ratio', 0):.2f}:1")
                            plan.append("")
                            plan.append("**滚仓策略说明**:")
                            plan.append("- 当价格达到0.5R盈利时，将止损移至盈亏平衡点")
                            plan.append("- 当价格达到1.0R、1.5R、2.0R盈利时，可使用浮盈加仓30%")
                            plan.append("- 分批止盈：第一止盈位止盈30%，第二止盈位止盈30%，保留40%继续持有")
                            plan.append("")
                except Exception as e:
                    print(f"5分钟滚仓策略分析失败: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
        else:
            plan.append("无明确信号，观望")
            plan.append("")
    
    # 二、15分钟交易信号（简明）
    plan.append("## 二、15分钟交易信号")
    plan.append("")
    
    # 三、1小时交易信号（形态识别更容易在长时间框架识别）
    plan.append("## 三、1小时交易信号")
    plan.append("")
    
    if analysis_1h:
        if analysis_1h['is_garbage_time']:
            plan.append("⚠️ **垃圾时间**: 建议等待突破")
            plan.append(f"   区间: ${analysis_1h['garbage_range'][0]:,.0f} - ${analysis_1h['garbage_range'][1]:,.0f}")
            plan.append("")
        
        # 合并图表形态信号和原有信号（形态识别信号优先级更高）
        all_signals_1h = []
        
        # 先添加形态识别信号（优先级高）
        if chart_pattern_signals_1h:
            all_signals_1h.extend(chart_pattern_signals_1h)
        
        if top_trader_patterns_1h and top_trader_patterns_1h.get('all_signals'):
            for signal in top_trader_patterns_1h['all_signals']:
                if signal.get('entry') and signal.get('stop_loss'):
                    risk = abs(signal['entry'] - signal['stop_loss'])
                    take_profit_1 = signal['entry'] + (risk * 2 if signal['type'] == 'long' else -risk * 2) if risk > 0 else (signal['entry'] * 1.02 if signal['type'] == 'long' else signal['entry'] * 0.98)
                    take_profit_2 = signal['entry'] + (risk * 3 if signal['type'] == 'long' else -risk * 3) if risk > 0 else (signal['entry'] * 1.04 if signal['type'] == 'long' else signal['entry'] * 0.96)
                    all_signals_1h.append({
                        'type': signal['type'],
                        'strength': 'strong' if signal.get('strength', 0) > 75 else 'medium',
                        'entry': signal['entry'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit_1': take_profit_1,
                        'take_profit_2': take_profit_2,
                        'entry_model': signal.get('entry_model', f"顶级交易员形态-{signal.get('name', '未知')}"),
                        'reason': signal.get('reason', f"识别到{signal.get('name', '形态')}"),
                        'pattern_priority': 1  # 形态识别优先级标记
                    })
        
        if bullish_patterns_1h and bullish_patterns_1h.get('patterns'):
            for pattern in bullish_patterns_1h['patterns']:
                risk = abs(pattern['entry'] - pattern['stop_loss'])
                take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
                take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
                all_signals_1h.append({
                    'type': 'long',
                    'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                    'entry': pattern['entry'],
                    'stop_loss': pattern['stop_loss'],
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'entry_model': f"看涨形态-{pattern['name']}",
                    'reason': pattern['description'],
                    'pattern_priority': 1  # 形态识别优先级标记
                })
        
        # 再添加Vegas等基础信号（优先级较低）
        if analysis_1h.get('signals'):
            for signal in analysis_1h['signals']:
                signal['pattern_priority'] = 0  # 基础信号优先级标记
                all_signals_1h.append(signal)
        
        if all_signals_1h:
            # 优先选择形态识别信号，然后按强度排序
            def signal_score(s):
                priority = s.get('pattern_priority', 0) * 10  # 形态识别信号加分
                strength = 3 if s['strength'] == 'strong' else 2 if s['strength'] == 'medium' else 1
                return priority + strength
            
            best_signal = max(all_signals_1h, key=signal_score)
            
            # 如果best_signal还没有订单簿止损，尝试获取
            if not best_signal.get('orderbook_stop_loss'):
                ob_stop_loss, ob_info = get_orderbook_stop_loss(
                    best_signal['entry'], best_signal['type'], current_price
                )
                if ob_stop_loss:
                    best_signal['orderbook_stop_loss'] = ob_stop_loss
                    best_signal['orderbook_info'] = ob_info
            
            # 显示所有识别到的形态（如果有多个）
            pattern_signals = [s for s in all_signals_1h if s.get('pattern_priority', 0) > 0]
            if len(pattern_signals) > 1:
                plan.append(f"**识别到 {len(pattern_signals)} 个形态信号**，已选择最强信号")
                plan.append("")
            
            # 使用ML模型预测成功率（如果可用）
            if ml_predictor and ml_predictor.is_trained:
                try:
                    ml_prediction = ml_predictor.predict_signal_success(best_signal)
                    best_signal['ml_score'] = ml_prediction['success_probability']
                    best_signal['ml_confidence'] = ml_prediction['confidence']
                    best_signal['ml_prediction'] = ml_prediction['prediction']
                except Exception as e:
                    print(f"1小时信号ML预测失败: {e}", file=sys.stderr)
            
            direction = "做多" if best_signal['type'] == 'long' else "做空"
            strength = "强" if best_signal['strength'] == 'strong' else "中" if best_signal['strength'] == 'medium' else "弱"
            
            plan.append(f"**{direction}** ({strength})")
            plan.append(f"入场: ${best_signal['entry']:,.0f}")
            
            # 显示技术指标止损（主要止损）
            tech_distance = abs(best_signal['entry'] - best_signal['stop_loss'])
            tech_distance_pct = (tech_distance / best_signal['entry']) * 100
            plan.append(f"止损: ${best_signal['stop_loss']:,.0f} (技术指标，距离: {tech_distance_pct:.2f}%)")
            
            # 同时显示订单簿止损（参考止损）
            if best_signal.get('orderbook_stop_loss'):
                ob_info = best_signal.get('orderbook_info', {})
                ob_stop = best_signal['orderbook_stop_loss']
                is_from_ob = ob_info.get('is_from_orderbook', True)
                ob_status = "[实时订单簿]" if is_from_ob else "[备用方案]"
                ob_distance = abs(best_signal['entry'] - ob_stop)
                ob_distance_pct = (ob_distance / best_signal['entry']) * 100
                plan.append(f"参考止损: ${ob_stop:,.0f} {ob_status} (距离: {ob_distance_pct:.2f}%)")
                if ob_info.get('info', {}).get('reason'):
                    plan.append(f"   理由: {ob_info['info']['reason']}")
            
            plan.append(f"止盈: ${best_signal['take_profit_1']:,.0f} (50%) / ${best_signal['take_profit_2']:,.0f} (50%)")
            
            # 明确标注入场模型和入场原因
            entry_model = best_signal.get('entry_model', '未知模型')
            plan.append(f"**入场模型**: {entry_model}")
            plan.append(f"**入场原因**: {best_signal.get('reason', '无详细说明')}")
            
            # 添加ML预测结果（如果可用）
            if best_signal.get('ml_score') is not None:
                ml_score = best_signal['ml_score']
                ml_confidence = best_signal.get('ml_confidence', 0)
                ml_pred = "成功" if best_signal.get('ml_prediction') == 1 else "失败"
                plan.append(f"**ML预测成功率**: {ml_score:.1%} (预测: {ml_pred}, 置信度: {ml_confidence:.1%})")
            
            plan.append("")
        else:
            plan.append("无明确信号，观望")
            plan.append("")
    else:
        plan.append("无法分析1小时时间框架")
        plan.append("")
    
    plan.append("---")
    plan.append("")
    
    # 四、OTE区间和Order Block分析
    plan.append("## 四、OTE区间和Order Block分析")
    plan.append("")
    
    # 5分钟OTE和OB
    if analysis_5m:
        plan.append("### 5分钟级别")
        plan.append("")
        
        if analysis_5m.get('ote_analysis'):
            ote = analysis_5m['ote_analysis']
            if ote['in_ote_zone']:
                plan.append("✅ **价格在OTE区间内** (618-786斐波那契回撤)")
                plan.append(f"   - OTE区间: ${ote['fib_618']:,.0f} - ${ote['fib_786']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 这是最佳入场位置，可以挂单等待")
            elif ote['above_786']:
                plan.append("📈 **价格突破786** (看涨信号)")
                plan.append(f"   - 786位置: ${ote['fib_786']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 突破786后，回踩到OTE区间是入场机会")
            elif ote['below_618']:
                plan.append("📉 **价格跌破618** (可能继续下跌)")
                plan.append(f"   - 618位置: ${ote['fib_618']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 等待价格回到OTE区间或确认反转")
            plan.append("")
        
        if analysis_5m.get('order_blocks'):
            plan.append("**Order Block (订单块)**:")
            for i, ob in enumerate(analysis_5m['order_blocks'][:3], 1):  # 只显示前3个
                ob_type = "看涨OB" if ob['type'] == 'bullish' else "看跌OB"
                plan.append(f"  - {i}. {ob_type}: ${ob['low']:,.0f} - ${ob['high']:,.0f} (强度: {ob['strength']})")
                plan.append(f"    → 价格回到此区间时是交易机会")
            plan.append("")
    
    # 15分钟OTE和OB
    if analysis_15m:
        plan.append("### 15分钟级别")
        plan.append("")
        
        if analysis_15m.get('ote_analysis'):
            ote = analysis_15m['ote_analysis']
            if ote['in_ote_zone']:
                plan.append("✅ **价格在OTE区间内** (618-786斐波那契回撤)")
                plan.append(f"   - OTE区间: ${ote['fib_618']:,.0f} - ${ote['fib_786']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 这是最佳入场位置，可以挂单等待")
            elif ote['above_786']:
                plan.append("📈 **价格突破786** (看涨信号)")
                plan.append(f"   - 786位置: ${ote['fib_786']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 突破786后，回踩到OTE区间是入场机会")
            elif ote['below_618']:
                plan.append("📉 **价格跌破618** (可能继续下跌)")
                plan.append(f"   - 618位置: ${ote['fib_618']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 等待价格回到OTE区间或确认反转")
            plan.append("")
        
        if analysis_15m.get('order_blocks'):
            plan.append("**Order Block (订单块)**:")
            for i, ob in enumerate(analysis_15m['order_blocks'][:3], 1):  # 只显示前3个
                ob_type = "看涨OB" if ob['type'] == 'bullish' else "看跌OB"
                plan.append(f"  - {i}. {ob_type}: ${ob['low']:,.0f} - ${ob['high']:,.0f} (强度: {ob['strength']})")
                plan.append(f"    → 价格回到此区间时是交易机会")
            plan.append("")
    
    # 1小时OTE和OB
    if analysis_1h:
        plan.append("### 1小时级别")
        plan.append("")
        
        if analysis_1h.get('ote_analysis'):
            ote = analysis_1h['ote_analysis']
            if ote['in_ote_zone']:
                plan.append("✅ **价格在OTE区间内** (618-786斐波那契回撤)")
                plan.append(f"   - OTE区间: ${ote['fib_618']:,.0f} - ${ote['fib_786']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 这是最佳入场位置，可以挂单等待")
            elif ote['above_786']:
                plan.append("📈 **价格突破786** (看涨信号)")
                plan.append(f"   - 786位置: ${ote['fib_786']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 突破786后，回踩到OTE区间是入场机会")
            elif ote['below_618']:
                plan.append("📉 **价格跌破618** (可能继续下跌)")
                plan.append(f"   - 618位置: ${ote['fib_618']:,.0f}")
                plan.append(f"   - 当前价格: ${ote['current_price']:,.0f}")
                plan.append("   - **交易建议**: 等待价格回到OTE区间或确认反转")
            plan.append("")
        
        if analysis_1h.get('order_blocks'):
            plan.append("**Order Block (订单块)**:")
            for i, ob in enumerate(analysis_1h['order_blocks'][:3], 1):  # 只显示前3个
                ob_type = "看涨OB" if ob['type'] == 'bullish' else "看跌OB"
                plan.append(f"  - {i}. {ob_type}: ${ob['low']:,.0f} - ${ob['high']:,.0f} (强度: {ob['strength']})")
                plan.append(f"    → 价格回到此区间时是交易机会")
            plan.append("")
    
    plan.append("---")
    plan.append("")
    
    if analysis_15m:
        if analysis_15m['is_garbage_time']:
            plan.append("⚠️ **垃圾时间**: 建议等待突破")
            plan.append(f"   区间: ${analysis_15m['garbage_range'][0]:,.0f} - ${analysis_15m['garbage_range'][1]:,.0f}")
            plan.append("")
        
        # 合并图表形态信号和原有信号（形态识别信号优先级更高）
        all_signals_15m = []
        
        # 先添加形态识别信号（优先级高）
        if chart_pattern_signals_15m:
            all_signals_15m.extend(chart_pattern_signals_15m)
        
        if top_trader_patterns_15m and top_trader_patterns_15m.get('all_signals'):
            for signal in top_trader_patterns_15m['all_signals']:
                if signal.get('entry') and signal.get('stop_loss'):
                    risk = abs(signal['entry'] - signal['stop_loss'])
                    take_profit_1 = signal['entry'] + (risk * 2 if signal['type'] == 'long' else -risk * 2) if risk > 0 else (signal['entry'] * 1.02 if signal['type'] == 'long' else signal['entry'] * 0.98)
                    take_profit_2 = signal['entry'] + (risk * 3 if signal['type'] == 'long' else -risk * 3) if risk > 0 else (signal['entry'] * 1.04 if signal['type'] == 'long' else signal['entry'] * 0.96)
                    all_signals_15m.append({
                        'type': signal['type'],
                        'strength': 'strong' if signal.get('strength', 0) > 75 else 'medium',
                        'entry': signal['entry'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit_1': take_profit_1,
                        'take_profit_2': take_profit_2,
                        'entry_model': signal.get('entry_model', f"顶级交易员形态-{signal.get('name', '未知')}"),
                        'reason': signal.get('reason', f"识别到{signal.get('name', '形态')}"),
                        'pattern_priority': 1  # 形态识别优先级标记
                    })
        
        if bullish_patterns_15m and bullish_patterns_15m.get('patterns'):
            for pattern in bullish_patterns_15m['patterns']:
                risk = abs(pattern['entry'] - pattern['stop_loss'])
                take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
                take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
                all_signals_15m.append({
                    'type': 'long',
                    'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                    'entry': pattern['entry'],
                    'stop_loss': pattern['stop_loss'],
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'entry_model': f"看涨形态-{pattern['name']}",
                    'reason': pattern['description'],
                    'pattern_priority': 1  # 形态识别优先级标记
                })
        
        # 再添加Vegas等基础信号（优先级较低）
        if analysis_15m.get('signals'):
            for signal in analysis_15m['signals']:
                signal['pattern_priority'] = 0  # 基础信号优先级标记
                all_signals_15m.append(signal)
        
        if all_signals_15m:
            # 优先选择形态识别信号，然后按强度排序
            def signal_score(s):
                priority = s.get('pattern_priority', 0) * 10  # 形态识别信号加分
                strength = 3 if s['strength'] == 'strong' else 2 if s['strength'] == 'medium' else 1
                return priority + strength
            
            best_signal = max(all_signals_15m, key=signal_score)
            
            # 如果best_signal还没有订单簿止损，尝试获取
            if not best_signal.get('orderbook_stop_loss'):
                ob_stop_loss, ob_info = get_orderbook_stop_loss(
                    best_signal['entry'], best_signal['type'], current_price
                )
                if ob_stop_loss:
                    best_signal['orderbook_stop_loss'] = ob_stop_loss
                    best_signal['orderbook_info'] = ob_info
            
            # 显示所有识别到的形态（如果有多个）
            pattern_signals = [s for s in all_signals_15m if s.get('pattern_priority', 0) > 0]
            if len(pattern_signals) > 1:
                plan.append(f"**识别到 {len(pattern_signals)} 个形态信号**，已选择最强信号")
                plan.append("")
            
            # 使用ML模型预测成功率（如果可用）
            if ml_predictor and ml_predictor.is_trained:
                try:
                    ml_prediction = ml_predictor.predict_signal_success(best_signal)
                    best_signal['ml_score'] = ml_prediction['success_probability']
                    best_signal['ml_confidence'] = ml_prediction['confidence']
                    best_signal['ml_prediction'] = ml_prediction['prediction']
                except Exception as e:
                    print(f"15分钟信号ML预测失败: {e}", file=sys.stderr)
            direction = "做多" if best_signal['type'] == 'long' else "做空"
            strength = "强" if best_signal['strength'] == 'strong' else "中" if best_signal['strength'] == 'medium' else "弱"
            
            plan.append(f"**{direction}** ({strength})")
            plan.append(f"入场: ${best_signal['entry']:,.0f}")
            
            # 显示技术指标止损（主要止损）
            tech_distance = abs(best_signal['entry'] - best_signal['stop_loss'])
            tech_distance_pct = (tech_distance / best_signal['entry']) * 100
            plan.append(f"止损: ${best_signal['stop_loss']:,.0f} (技术指标，距离: {tech_distance_pct:.2f}%)")
            
            # 同时显示订单簿止损（参考止损）
            if best_signal.get('orderbook_stop_loss'):
                ob_info = best_signal.get('orderbook_info', {})
                ob_stop = best_signal['orderbook_stop_loss']
                is_from_ob = ob_info.get('is_from_orderbook', True)
                ob_status = "[实时订单簿]" if is_from_ob else "[备用方案]"
                ob_distance = abs(best_signal['entry'] - ob_stop)
                ob_distance_pct = (ob_distance / best_signal['entry']) * 100
                plan.append(f"参考止损: ${ob_stop:,.0f} {ob_status} (距离: {ob_distance_pct:.2f}%)")
                if ob_info.get('info', {}).get('reason'):
                    plan.append(f"   理由: {ob_info['info']['reason']}")
            
            plan.append(f"止盈: ${best_signal['take_profit_1']:,.0f} (50%) / ${best_signal['take_profit_2']:,.0f} (50%)")
            
            # 明确标注入场模型和入场原因
            entry_model = best_signal.get('entry_model', '未知模型')
            plan.append(f"**入场模型**: {entry_model}")
            plan.append(f"**入场原因**: {best_signal.get('reason', '无详细说明')}")
            
            # 添加ML预测结果（如果可用）
            if best_signal.get('ml_score') is not None:
                ml_score = best_signal['ml_score']
                ml_confidence = best_signal.get('ml_confidence', 0)
                ml_pred = "成功" if best_signal.get('ml_prediction') == 1 else "失败"
                plan.append(f"**ML预测成功率**: {ml_score:.1%} (预测: {ml_pred}, 置信度: {ml_confidence:.1%})")
            
            plan.append("")
            
            # 滚仓策略建议（如果可用）
            if ROLLING_POSITION_AVAILABLE and best_signal:
                try:
                    rolling_manager = RollingPositionManager()
                    rolling_analysis = rolling_manager.analyze_signal_for_rolling(best_signal, current_price)
                    
                    if rolling_analysis.get('suitable'):
                        plan.append("---")
                        plan.append("")
                        plan.append("### 💰 滚仓策略建议")
                        plan.append("")
                        
                        if rolling_analysis.get('suggestion'):
                            rolling_lines = rolling_manager.format_rolling_suggestion(rolling_analysis['suggestion'])
                            plan.extend(rolling_lines)
                        else:
                            plan.append(f"**分析结果**: {rolling_analysis.get('reason', '适合滚仓策略')}")
                            plan.append(f"**风险回报比**: {rolling_analysis.get('risk_reward_ratio', 0):.2f}:1")
                            plan.append("")
                            plan.append("**滚仓策略说明**:")
                            plan.append("- 当价格达到0.5R盈利时，将止损移至盈亏平衡点")
                            plan.append("- 当价格达到1.0R、1.5R、2.0R盈利时，可使用浮盈加仓30%")
                            plan.append("- 分批止盈：第一止盈位止盈30%，第二止盈位止盈30%，保留40%继续持有")
                            plan.append("")
                except Exception as e:
                    print(f"15分钟滚仓策略分析失败: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
        else:
            plan.append("无明确信号，观望")
            plan.append("")
    
    # 三、图表形态识别结果（如果可用）
    if PATTERN_DETECTOR_AVAILABLE and (chart_pattern_signals_5m or chart_pattern_signals_15m):
        plan.append("---")
        plan.append("")
        plan.append("## 三、图表形态识别")
        plan.append("")
        
        if chart_pattern_signals_5m:
            plan.append("### 3.1 5分钟时间框架形态")
            plan.append("")
            for signal in chart_pattern_signals_5m:
                direction = "做多" if signal['type'] == 'long' else "做空"
                plan.append(f"- **{signal['entry_model']}** ({direction})")
                plan.append(f"  - 入场: ${signal['entry']:,.0f}")
                plan.append(f"  - 止损: ${signal['stop_loss']:,.0f}")
                plan.append(f"  - 止盈: ${signal['take_profit_1']:,.0f} / ${signal['take_profit_2']:,.0f}")
                plan.append(f"  - {signal['reason']}")
                plan.append("")
        
        if chart_pattern_signals_15m:
            plan.append("### 3.2 15分钟时间框架形态")
            plan.append("")
            for signal in chart_pattern_signals_15m:
                direction = "做多" if signal['type'] == 'long' else "做空"
                plan.append(f"- **{signal['entry_model']}** ({direction})")
                plan.append(f"  - 入场: ${signal['entry']:,.0f}")
                plan.append(f"  - 止损: ${signal['stop_loss']:,.0f}")
                plan.append(f"  - 止盈: ${signal['take_profit_1']:,.0f} / ${signal['take_profit_2']:,.0f}")
                plan.append(f"  - {signal['reason']}")
                plan.append("")
    
    # 主力洗盘场景识别结果（如果可用）
    if WASHOUT_DETECTOR_AVAILABLE and (washout_scenarios_5m or washout_scenarios_15m):
        plan.append("---")
        plan.append("")
        washout_section = "四" if not (PATTERN_DETECTOR_AVAILABLE and (chart_pattern_signals_5m or chart_pattern_signals_15m)) and not (DOWNTREND_DETECTOR_AVAILABLE and (downtrend_signals_5m or downtrend_signals_15m)) else "五"
        if (PATTERN_DETECTOR_AVAILABLE and (chart_pattern_signals_5m or chart_pattern_signals_15m)) and (DOWNTREND_DETECTOR_AVAILABLE and (downtrend_signals_5m or downtrend_signals_15m)):
            washout_section = "五"
        elif (PATTERN_DETECTOR_AVAILABLE and (chart_pattern_signals_5m or chart_pattern_signals_15m)) or (DOWNTREND_DETECTOR_AVAILABLE and (downtrend_signals_5m or downtrend_signals_15m)):
            washout_section = "四"
        plan.append(f"## {washout_section}、主力洗盘场景识别（6种常见场景）")
        plan.append("")
        
        if washout_scenarios_5m and washout_scenarios_5m.get('scenarios'):
            plan.append(f"### {washout_section}.1 5分钟时间框架洗盘场景")
            plan.append("")
            plan.append(f"**做多机会强度**: {washout_scenarios_5m['long_opportunity_strength']:.1f}% (识别到 {washout_scenarios_5m['scenario_count']}/6 种场景)")
            plan.append("")
            
            for scenario in washout_scenarios_5m['scenarios']:
                plan.append(f"- **{scenario['name']}** (强度: {scenario['strength']:.1f}%)")
                plan.append(f"  - {scenario['description']}")
                # 尝试获取入场点
                name_map = {
                    '箱体震荡': 'box_oscillation',
                    '三角形震荡': 'triangle_oscillation',
                    '五浪调整': 'five_wave',
                    '旗形下跌': 'falling_flag',
                    '缩量圆弧': 'shrinking_arc',
                    '旗形上涨': 'rising_flag'
                }
                mapped_key = name_map.get(scenario['name'])
                if mapped_key and mapped_key in washout_scenarios_5m['scenarios_details']:
                    entry = washout_scenarios_5m['scenarios_details'][mapped_key].get('entry')
                    if entry:
                        plan.append(f"  - 建议入场: ${entry:,.0f}")
                plan.append("")
        
        if washout_scenarios_15m and washout_scenarios_15m.get('scenarios'):
            plan.append(f"### {washout_section}.2 15分钟时间框架洗盘场景")
            plan.append("")
            plan.append(f"**做多机会强度**: {washout_scenarios_15m['long_opportunity_strength']:.1f}% (识别到 {washout_scenarios_15m['scenario_count']}/6 种场景)")
            plan.append("")
            
            for scenario in washout_scenarios_15m['scenarios']:
                plan.append(f"- **{scenario['name']}** (强度: {scenario['strength']:.1f}%)")
                plan.append(f"  - {scenario['description']}")
                name_map = {
                    '箱体震荡': 'box_oscillation',
                    '三角形震荡': 'triangle_oscillation',
                    '五浪调整': 'five_wave',
                    '旗形下跌': 'falling_flag',
                    '缩量圆弧': 'shrinking_arc',
                    '旗形上涨': 'rising_flag'
                }
                mapped_key = name_map.get(scenario['name'])
                if mapped_key and mapped_key in washout_scenarios_15m['scenarios_details']:
                    entry = washout_scenarios_15m['scenarios_details'][mapped_key].get('entry')
                    if entry:
                        plan.append(f"  - 建议入场: ${entry:,.0f}")
                plan.append("")
        
        plan.append("**说明**: 主力洗盘场景识别包含6种常见场景：")
        plan.append("1. 箱体震荡 (Box Oscillation) - 矩形箱体震荡，调整幅度不超过上涨的1/3")
        plan.append("2. 三角形震荡 (Triangle Oscillation) - 收敛三角形，成交量缩量，突破放量")
        plan.append("3. 五浪调整 (Five-Wave Adjustment) - 5段走势波浪式下跌，调整约上涨的1/2")
        plan.append("4. 旗形下跌 (Falling Flag) - 下降通道整理，调整缩量，突破放量")
        plan.append("5. 缩量圆弧 (Volume Shrinking Arc) - 圆弧型态调整，成交量缩量，放量进场")
        plan.append("6. 旗形上涨 (Rising Flag) - 上升通道整理，温和放量，突破后加速")
        plan.append("")
    
    # K线起飞形态识别结果（如果可用）
    if TAKEOFF_PATTERNS_AVAILABLE and (takeoff_patterns_5m or takeoff_patterns_15m):
        plan.append("---")
        plan.append("")
        takeoff_section = "四"
        if PATTERN_DETECTOR_AVAILABLE and (chart_pattern_signals_5m or chart_pattern_signals_15m):
            takeoff_section = "五"
        if DOWNTREND_DETECTOR_AVAILABLE and (downtrend_signals_5m or downtrend_signals_15m):
            takeoff_section = "五" if takeoff_section == "四" else "六"
        if WASHOUT_DETECTOR_AVAILABLE and (washout_scenarios_5m or washout_scenarios_15m):
            if takeoff_section == "四":
                takeoff_section = "五"
            elif takeoff_section == "五":
                takeoff_section = "六"
            else:
                takeoff_section = "七"
        plan.append(f"## {takeoff_section}、经典K线起飞形态识别（9种形态）")
        plan.append("")
        
        if takeoff_patterns_5m and takeoff_patterns_5m.get('patterns'):
            plan.append(f"### {takeoff_section}.1 5分钟时间框架起飞形态")
            plan.append("")
            plan.append(f"**起飞强度**: {takeoff_patterns_5m['takeoff_strength']:.1f}% (识别到 {takeoff_patterns_5m['pattern_count']}/9 种形态)")
            plan.append("")
            
            for pattern in takeoff_patterns_5m['patterns']:
                plan.append(f"- **{pattern['name']}** (强度: {pattern['strength']:.1f}%)")
                plan.append(f"  - {pattern['description']}")
                # 尝试获取入场点
                name_map = {
                    '金针探底': 'golden_needle',
                    '红三兵': 'three_soldiers',
                    '涨停双响炮': 'double_cannon',
                    '揭竿而起': 'rising_ground',
                    '小步上扬': 'small_steps',
                    '均线多头布林突破': 'ma_bollinger',
                    '单阳盖阴': 'bullish_engulfing',
                    '立竿见影': 'instant_effect',
                    '上升三法': 'rising_three'
                }
                mapped_key = name_map.get(pattern['name'])
                if mapped_key and mapped_key in takeoff_patterns_5m['patterns_details']:
                    entry = takeoff_patterns_5m['patterns_details'][mapped_key].get('entry')
                    if entry:
                        plan.append(f"  - 建议入场: ${entry:,.0f}")
                plan.append("")
        
        if takeoff_patterns_15m and takeoff_patterns_15m.get('patterns'):
            plan.append(f"### {takeoff_section}.2 15分钟时间框架起飞形态")
            plan.append("")
            plan.append(f"**起飞强度**: {takeoff_patterns_15m['takeoff_strength']:.1f}% (识别到 {takeoff_patterns_15m['pattern_count']}/9 种形态)")
            plan.append("")
            
            for pattern in takeoff_patterns_15m['patterns']:
                plan.append(f"- **{pattern['name']}** (强度: {pattern['strength']:.1f}%)")
                plan.append(f"  - {pattern['description']}")
                name_map = {
                    '金针探底': 'golden_needle',
                    '红三兵': 'three_soldiers',
                    '涨停双响炮': 'double_cannon',
                    '揭竿而起': 'rising_ground',
                    '小步上扬': 'small_steps',
                    '均线多头布林突破': 'ma_bollinger',
                    '单阳盖阴': 'bullish_engulfing',
                    '立竿见影': 'instant_effect',
                    '上升三法': 'rising_three'
                }
                mapped_key = name_map.get(pattern['name'])
                if mapped_key and mapped_key in takeoff_patterns_15m['patterns_details']:
                    entry = takeoff_patterns_15m['patterns_details'][mapped_key].get('entry')
                    if entry:
                        plan.append(f"  - 建议入场: ${entry:,.0f}")
                plan.append("")
        
        plan.append("**说明**: 经典K线起飞形态识别包含9种形态：")
        plan.append("1. 金针探底 (Golden Needle) - 长下影线探底后连续上涨")
        plan.append("2. 红三兵 (Three White Soldiers) - 三根连续阳线稳步上涨")
        plan.append("3. 涨停双响炮 (Double Cannon) - 两根大阳线夹一小阴线")
        plan.append("4. 揭竿而起 (Rising from Ground) - 突然大幅上涨强势反转")
        plan.append("5. 小步上扬 (Small Steps) - 连续小阳线稳步上涨")
        plan.append("6. 均线多头布林突破 (MA Bollinger Breakout) - 突破阻力位强势上涨")
        plan.append("7. 单阳盖阴 (Bullish Engulfing) - 大阳线完全吞没前一根阴线")
        plan.append("8. 立竿见影 (Instant Effect) - 下跌后突然大幅上涨快速反转")
        plan.append("9. 上升三法 (Rising Three Methods) - 上涨后整理然后继续上涨")
        plan.append("")
    
    # 看涨图表形态识别结果（如果可用，带交易信号）
    if BULLISH_PATTERNS_AVAILABLE and (bullish_patterns_5m or bullish_patterns_15m):
        plan.append("---")
        plan.append("")
        bullish_section = "四"
        section_count_before = 0
        if PATTERN_DETECTOR_AVAILABLE and (chart_pattern_signals_5m or chart_pattern_signals_15m):
            section_count_before += 1
        if DOWNTREND_DETECTOR_AVAILABLE and (downtrend_signals_5m or downtrend_signals_15m):
            section_count_before += 1
        if WASHOUT_DETECTOR_AVAILABLE and (washout_scenarios_5m or washout_scenarios_15m):
            section_count_before += 1
        if TAKEOFF_PATTERNS_AVAILABLE and (takeoff_patterns_5m or takeoff_patterns_15m):
            section_count_before += 1
        bullish_section_map = {0: "四", 1: "五", 2: "六", 3: "七", 4: "八"}
        bullish_section = bullish_section_map.get(section_count_before, "四")
        
        plan.append(f"## {bullish_section}、看涨图表形态识别（8种形态，带交易信号）")
        plan.append("")
        
        if bullish_patterns_5m and bullish_patterns_5m.get('patterns'):
            plan.append(f"### {bullish_section}.1 5分钟时间框架看涨形态")
            plan.append("")
            plan.append(f"**看涨强度**: {bullish_patterns_5m['bullish_strength']:.1f}% (识别到 {bullish_patterns_5m['pattern_count']}/8 种形态)")
            plan.append("")
            
            for pattern in bullish_patterns_5m['patterns']:
                plan.append(f"- **{pattern['name']}** (强度: {pattern['strength']:.1f}%)")
                plan.append(f"  - {pattern['description']}")
                plan.append(f"  - 买入点: ${pattern['entry']:,.0f}")
                plan.append(f"  - 止损点: ${pattern['stop_loss']:,.0f}")
                risk = abs(pattern['entry'] - pattern['stop_loss'])
                if risk > 0:
                    take_profit_1 = pattern['entry'] + risk * 2
                    take_profit_2 = pattern['entry'] + risk * 3
                    plan.append(f"  - 建议止盈: ${take_profit_1:,.0f} (50%) / ${take_profit_2:,.0f} (50%)")
                plan.append("")
        
        if bullish_patterns_15m and bullish_patterns_15m.get('patterns'):
            plan.append(f"### {bullish_section}.2 15分钟时间框架看涨形态")
            plan.append("")
            plan.append(f"**看涨强度**: {bullish_patterns_15m['bullish_strength']:.1f}% (识别到 {bullish_patterns_15m['pattern_count']}/8 种形态)")
            plan.append("")
            
            for pattern in bullish_patterns_15m['patterns']:
                plan.append(f"- **{pattern['name']}** (强度: {pattern['strength']:.1f}%)")
                plan.append(f"  - {pattern['description']}")
                plan.append(f"  - 买入点: ${pattern['entry']:,.0f}")
                plan.append(f"  - 止损点: ${pattern['stop_loss']:,.0f}")
                risk = abs(pattern['entry'] - pattern['stop_loss'])
                if risk > 0:
                    take_profit_1 = pattern['entry'] + risk * 2
                    take_profit_2 = pattern['entry'] + risk * 3
                    plan.append(f"  - 建议止盈: ${take_profit_1:,.0f} (50%) / ${take_profit_2:,.0f} (50%)")
                plan.append("")
        
        plan.append("**说明**: 看涨图表形态识别包含8种形态，每种形态都提供明确的买入点和止损点：")
        plan.append("1. 旗形 (Flag) - 下降通道整理，突破上沿买入")
        plan.append("2. 三角旗 (Pennant) - 对称三角形整理，突破上沿买入")
        plan.append("3. 对称三角形 (Symmetrical Triangle) - 收敛三角形，突破上沿买入")
        plan.append("4. 衡量上涨 (Measured Move Up) - 上升通道整理，突破上沿买入")
        plan.append("5. 杯柄形态 (Cup and Handle) - U型杯+小柄，突破杯沿买入")
        plan.append("6. 上升三角形 (Ascending Triangle) - 水平阻力+上升支撑，突破阻力买入")
        plan.append("7. 上升贝壳 (Rising Scallop) - U型走势，突破最高点买入")
        plan.append("8. 上升三连谷 (Three Rising Valleys) - 三个逐步升高的低点，突破阻力买入")
        plan.append("")
    
    # 详细技术分析说明
    section_count = 0
    if PATTERN_DETECTOR_AVAILABLE and (chart_pattern_signals_5m or chart_pattern_signals_15m):
        section_count += 1
    if DOWNTREND_DETECTOR_AVAILABLE and (downtrend_signals_5m or downtrend_signals_15m):
        section_count += 1
    if WASHOUT_DETECTOR_AVAILABLE and (washout_scenarios_5m or washout_scenarios_15m):
        section_count += 1
    if TAKEOFF_PATTERNS_AVAILABLE and (takeoff_patterns_5m or takeoff_patterns_15m):
        section_count += 1
    if BULLISH_PATTERNS_AVAILABLE and (bullish_patterns_5m or bullish_patterns_15m):
        section_count += 1
    if TOP_TRADER_PATTERNS_AVAILABLE and (top_trader_patterns_5m or top_trader_patterns_15m):
        section_count += 1
    section_map = {0: "四", 1: "五", 2: "六", 3: "七", 4: "八", 5: "九", 6: "十"}
    next_section = section_map.get(section_count, "四")
    
    plan.append("---")
    plan.append("")
    plan.append(f"## {next_section}、详细技术分析说明")
    plan.append("")
    plan.append("### 3.1 数据来源")
    plan.append("")
    plan.append("**Gate.io API** (主要数据源):")
    plan.append("- API端点: `https://api.gateio.ws/api/v4/spot/candlesticks`")
    plan.append("- 交易对: `BTC_USDT`")
    plan.append("- 时间框架: `5m` (5分钟), `15m` (15分钟), `1h` (1小时)")
    plan.append("- 数据量: 200根K线（5分钟/15分钟），100根K线（1小时）")
    plan.append("- 数据格式: `[timestamp, volume, close, high, low, open]`")
    plan.append("")
    plan.append("**Bitget API** (备用数据源):")
    plan.append("- API端点: `https://api.bitget.com/api/spot/v1/market/candles`")
    plan.append("- 交易对: `BTCUSDT`")
    plan.append("- 时间框架: `5min`, `15min`, `1hour`")
    plan.append("- 数据格式: `[timestamp, open, close, high, low, volume]`")
    plan.append("")
    plan.append("**数据获取逻辑**:")
    plan.append("1. 优先使用Gate.io API获取数据")
    plan.append("2. 如果Gate.io失败，自动切换到Bitget API")
    plan.append("3. 如果两个都失败，提示无法获取数据")
    plan.append("")
    plan.append("### 3.2 技术指标计算方法")
    plan.append("")
    plan.append("**Vegas通道 (EMA144/169)**:")
    plan.append("- EMA144: 144周期指数移动平均线")
    plan.append("- EMA169: 169周期指数移动平均线")
    plan.append("- 计算公式: `EMA = (价格 - 前一日EMA) × 2/(周期+1) + 前一日EMA`")
    plan.append("- 作用: 动态支撑/阻力，价格在通道内=震荡，在通道外=趋势")
    plan.append("")
    plan.append("**VWAP (成交量加权平均价)**:")
    plan.append("- 计算公式: `VWAP = Σ(典型价格 × 成交量) / Σ成交量`")
    plan.append("- 典型价格: `(最高价 + 最低价 + 收盘价) / 3`")
    plan.append("- 作用: 代表市场平均成本，价格在VWAP上方=VWAP作为支撑，下方=阻力")
    plan.append("")
    plan.append("**RSI (相对强弱指标)**:")
    plan.append("- 周期: 14")
    plan.append("- 计算公式: `RSI = 100 - (100 / (1 + RS))`，其中`RS = 平均涨幅 / 平均跌幅`")
    plan.append("- 作用: RSI > 70 = 超买，RSI < 30 = 超卖")
    plan.append("")
    plan.append("**FVG (Fair Value Gap)**:")
    plan.append("- 识别方法: 价格快速移动，中间K线没有重叠")
    plan.append("- 上涨FVG: 前一根K线高点 < 当前K线低点")
    plan.append("- 下跌FVG: 前一根K线低点 > 当前K线高点")
    plan.append("- 作用: 价格缺口，通常会被回填")
    plan.append("")
    plan.append("**支撑阻力位**:")
    plan.append("- 方法: 最近50根K线的最高点和最低点")
    plan.append("- 支撑位: 价格下方的关键低点")
    plan.append("- 阻力位: 价格上方的关键高点")
    plan.append("")
    
    # 5分钟详细分析
    if analysis_5m:
        plan.append("### 5分钟级别")
        plan.append("")
        plan.append(f"**Vegas通道**:")
        if analysis_5m['ema_144'] and analysis_5m['ema_169']:
            plan.append(f"  - EMA144: ${analysis_5m['ema_144']:,.2f}")
            plan.append(f"  - EMA169: ${analysis_5m['ema_169']:,.2f}")
            if current_price > analysis_5m['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif current_price < analysis_5m['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
        plan.append("")
        
        if analysis_5m['vwap']:
            plan.append(f"**VWAP**: ${analysis_5m['vwap']:,.2f}")
            if current_price > analysis_5m['vwap']:
                plan.append("  → 价格在VWAP上方，VWAP作为支撑")
            else:
                plan.append("  → 价格在VWAP下方，VWAP作为阻力")
            plan.append("")
        
        if analysis_5m['rsi']:
            plan.append(f"**RSI**: {analysis_5m['rsi']:.1f}")
            if analysis_5m['rsi'] > 70:
                plan.append("  → 超买区域，可能回调")
            elif analysis_5m['rsi'] < 30:
                plan.append("  → 超卖区域，可能反弹")
            else:
                plan.append("  → 正常区域")
            plan.append("")
        
        if analysis_5m['fvgs']:
            plan.append(f"**FVG**: 发现{len(analysis_5m['fvgs'])}个FVG")
            for fvg in analysis_5m['fvgs'][-3:]:
                fvg_type = "上涨" if fvg['type'] == 'bullish' else "下跌"
                plan.append(f"  - {fvg_type}FVG: ${fvg['low']:,.0f} - ${fvg['high']:,.0f}")
            plan.append("")
        
        if analysis_5m['support_resistance']['support']:
            plan.append("**支撑位**:")
            for s in analysis_5m['support_resistance']['support'][:3]:
                plan.append(f"  - ${s:,.0f}")
            plan.append("")
        
        if analysis_5m['support_resistance']['resistance']:
            plan.append("**阻力位**:")
            for r in analysis_5m['support_resistance']['resistance'][:3]:
                plan.append(f"  - ${r:,.0f}")
        
        # 量能分析信息
        if ENHANCED_ANALYSIS_AVAILABLE and analysis_5m.get('volume_profile'):
            vp = analysis_5m['volume_profile']
            plan.append("**量能分析** (Volume Profile):")
            if vp.get('poc'):
                plan.append(f"  - POC (成交量最大点): ${vp['poc']:,.0f}")
            if vp.get('high_volume_zones'):
                plan.append(f"  - 高量区域数量: {len(vp['high_volume_zones'])} 个（真正的支撑阻力位）")
            if vp.get('va_high') and vp.get('va_low'):
                plan.append(f"  - Value Area: ${vp['va_low']:,.0f} - ${vp['va_high']:,.0f}")
        
        # 区间识别信息
        if ENHANCED_ANALYSIS_AVAILABLE and analysis_5m.get('consolidation_ranges'):
            ranges = analysis_5m['consolidation_ranges']
            plan.append("**区间识别** (Consolidation Ranges):")
            plan.append(f"  - 当前区间数量: {len(ranges)} 个")
            for i, r in enumerate(ranges[:2], 1):  # 只显示前2个
                plan.append(f"  - 区间{i}: ${r['range_low']:,.0f} - ${r['range_high']:,.0f} (强度: {r['strength']}, 触及{r['touches']}次)")
        
        plan.append("")
    
    # 15分钟详细分析
    if analysis_15m:
        plan.append("### 15分钟级别")
        plan.append("")
        plan.append(f"**Vegas通道**:")
        if analysis_15m['ema_144'] and analysis_15m['ema_169']:
            plan.append(f"  - EMA144: ${analysis_15m['ema_144']:,.2f}")
            plan.append(f"  - EMA169: ${analysis_15m['ema_169']:,.2f}")
            if current_price > analysis_15m['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif current_price < analysis_15m['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
        plan.append("")
        
        if analysis_15m['vwap']:
            plan.append(f"**VWAP**: ${analysis_15m['vwap']:,.2f}")
            if current_price > analysis_15m['vwap']:
                plan.append("  → 价格在VWAP上方，VWAP作为支撑")
            else:
                plan.append("  → 价格在VWAP下方，VWAP作为阻力")
            plan.append("")
        
        if analysis_15m['rsi']:
            plan.append(f"**RSI**: {analysis_15m['rsi']:.1f}")
            if analysis_15m['rsi'] > 70:
                plan.append("  → 超买区域，可能回调")
            elif analysis_15m['rsi'] < 30:
                plan.append("  → 超卖区域，可能反弹")
            else:
                plan.append("  → 正常区域")
            plan.append("")
        
        if analysis_15m['support_resistance']['support']:
            plan.append("**支撑位**:")
            for s in analysis_15m['support_resistance']['support'][:3]:
                plan.append(f"  - ${s:,.0f}")
            plan.append("")
        
        if analysis_15m['support_resistance']['resistance']:
            plan.append("**阻力位**:")
            for r in analysis_15m['support_resistance']['resistance'][:3]:
                plan.append(f"  - ${r:,.0f}")
            plan.append("")
        
        # 量能分析信息
        if ENHANCED_ANALYSIS_AVAILABLE and analysis_15m.get('volume_profile'):
            vp = analysis_15m['volume_profile']
            plan.append("**量能分析** (Volume Profile):")
            if vp.get('poc'):
                plan.append(f"  - POC (成交量最大点): ${vp['poc']:,.0f}")
            if vp.get('high_volume_zones'):
                plan.append(f"  - 高量区域数量: {len(vp['high_volume_zones'])} 个（真正的支撑阻力位）")
            if vp.get('va_high') and vp.get('va_low'):
                plan.append(f"  - Value Area: ${vp['va_low']:,.0f} - ${vp['va_high']:,.0f}")
            plan.append("")
        
        # 区间识别信息
        if ENHANCED_ANALYSIS_AVAILABLE and analysis_15m.get('consolidation_ranges'):
            ranges = analysis_15m['consolidation_ranges']
            plan.append("**区间识别** (Consolidation Ranges):")
            plan.append(f"  - 当前区间数量: {len(ranges)} 个")
            for i, r in enumerate(ranges[:2], 1):  # 只显示前2个
                plan.append(f"  - 区间{i}: ${r['range_low']:,.0f} - ${r['range_high']:,.0f} (强度: {r['strength']}, 触及{r['touches']}次)")
            plan.append("")
    
    # 四、信号生成逻辑说明
    plan.append("### 信号生成逻辑")
    plan.append("")
    plan.append("**优先级排序**:")
    plan.append("1. **FVG信号** (最强): 价格快速移动留下的缺口，通常会被回填")
    plan.append("2. **Vegas通道信号** (中等): 价格在EMA144/169通道附近，通道作为支撑/阻力")
    plan.append("3. **VWAP信号** (中等): 价格在VWAP附近，VWAP作为动态支撑/阻力")
    plan.append("4. **支撑阻力信号** (中等): 价格接近历史支撑/阻力位")
    plan.append("")
    plan.append("**垃圾时间识别**:")
    plan.append("- 价格在区间内震荡（区间宽度<2%）")
    plan.append("- 没有明确的趋势方向")
    plan.append("- 建议：等待突破后再交易")
    plan.append("")
    plan.append("**多推模式检测**:")
    plan.append("- 价格多次（3-5次）测试同一位置但无法突破")
    plan.append("- 是反转信号，需要结合K线形态确认")
    plan.append("")
    
    # 交易执行检查清单
    checklist_section_map = {"四": "五", "五": "六", "六": "七", "七": "八"}
    checklist_section = checklist_section_map.get(next_section, "五")
    plan.append(f"## {checklist_section}、交易执行检查清单")
    plan.append("")
    plan.append("**入场前**:")
    plan.append("□ 是否在垃圾时间内？（如果是，等待突破）")
    plan.append("□ 是否有FVG机会？")
    plan.append("□ 多时间框架Vegas是否确认？")
    plan.append("□ 是否有明确的支撑/阻力位？")
    plan.append("□ RSI是否在合理区域？")
    plan.append("")
    plan.append("**风险管理**:")
    plan.append("□ 已设置止损（技术指标止损为主）")
    plan.append("□ 已设置分批止盈（50%+50%）")
    plan.append("□ 仓位大小已计算（风险2-3%）")
    plan.append("□ 盈亏比≥2:1")
    plan.append("")
    plan.append("### 止损说明")
    plan.append("")
    plan.append("**技术指标止损**（主要使用）:")
    plan.append("- 基于EMA、VWAP、支撑阻力等技术指标计算")
    plan.append("- 适合预生成的交易信号（信号生成时的止损位置）")
    plan.append("- 稳定可靠，不受实时订单簿变化影响")
    plan.append("")
    plan.append("**实时订单簿止损**（参考使用）:")
    plan.append("- 基于实时订单簿的流动性分析")
    plan.append("- 识别流动性密集区（支撑/阻力）和稀疏区")
    plan.append("- 止损放在稀疏区，避免被扫止损")
    plan.append("- 适合实时交易时动态调整，但预生成信号时订单簿可能已变化")
    plan.append("")
    plan.append("**建议**: 预生成的信号使用技术指标止损，实时交易时可参考订单簿止损进行调整")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    plan.append("**免责声明**: 本交易信号基于De.交易系统自动生成，仅供参考。交易有风险，入市需谨慎。")
    
    # 生成简要版本（只包含核心信号）
    def format_signal_brief(signal, timeframe_name, klines=None):
        """格式化单个信号为简要版本（包含盈亏比和波动率）"""
        if not signal:
            return []
        
        lines = []
        direction = "做多" if signal['type'] == 'long' else "做空"
        strength = "强" if signal['strength'] == 'strong' else "中" if signal['strength'] == 'medium' else "弱"
        
        lines.append(f"**{direction}** ({strength})")
        lines.append(f"入场: ${signal['entry']:,.0f}")
        
        # 显示技术指标止损（主要止损）
        tech_distance = abs(signal['entry'] - signal['stop_loss'])
        tech_distance_pct = (tech_distance / signal['entry']) * 100
        lines.append(f"止损: ${signal['stop_loss']:,.0f} (技术指标，{tech_distance_pct:.2f}%)")
        
        # 同时显示订单簿止损（参考止损）
        stop_loss_price = signal['stop_loss']  # 盈亏比计算使用技术止损
        if signal.get('orderbook_stop_loss'):
            ob_info = signal.get('orderbook_info', {})
            ob_stop = signal['orderbook_stop_loss']
            is_from_ob = ob_info.get('is_from_orderbook', True)
            ob_status = "[实时订单簿]" if is_from_ob else "[备用]"
            ob_distance = abs(signal['entry'] - ob_stop)
            ob_distance_pct = (ob_distance / signal['entry']) * 100
            lines.append(f"参考止损: ${ob_stop:,.0f} {ob_status} ({ob_distance_pct:.2f}%)")
        
        lines.append(f"止盈: ${signal['take_profit_1']:,.0f} (50%) / ${signal['take_profit_2']:,.0f} (50%)")
        
        # 计算并显示盈亏比
        if VOLATILITY_ANALYZER_AVAILABLE:
            try:
                rr_analysis = calculate_risk_reward_ratio(
                    entry=signal['entry'],
                    stop_loss=stop_loss_price,
                    take_profit_1=signal['take_profit_1'],
                    take_profit_2=signal['take_profit_2'],
                    signal_type=signal['type']
                )
                quality_map = {
                    'excellent': '优秀',
                    'good': '良好',
                    'acceptable': '可接受',
                    'poor': '较低',
                    'very_poor': '过低'
                }
                quality_emoji = {
                    'excellent': '✅',
                    'good': '✅',
                    'acceptable': '⚠️',
                    'poor': '⚠️',
                    'very_poor': '❌'
                }
                quality = quality_map.get(rr_analysis['quality'], '未知')
                emoji = quality_emoji.get(rr_analysis['quality'], '')
                lines.append(f"盈亏比: {rr_analysis['avg_rr_ratio']:.2f}:1 {emoji} ({quality})")
            except Exception as e:
                print(f"{timeframe_name}盈亏比计算失败: {e}", file=sys.stderr)
        
        # 计算并显示波动率
        if klines and VOLATILITY_ANALYZER_AVAILABLE:
            try:
                atr_percent = calculate_atr_percent(klines, period=14)
                if atr_percent:
                    volatility_assessment = assess_volatility_level(atr_percent)
                    volatility_emoji = {
                        'low': '🟢',
                        'medium': '🟡',
                        'high': '🟠',
                        'very_high': '🔴'
                    }
                    emoji = volatility_emoji.get(volatility_assessment['level'], '')
                    lines.append(f"波动率: {emoji} {volatility_assessment['description']} (ATR: {atr_percent:.2f}%)")
                    
                    # 如果波动率高，给出止损建议
                    if volatility_assessment['level'] in ['high', 'very_high']:
                        multiplier = volatility_assessment.get('stop_loss_multiplier', 1.0)
                        suggested_distance = distance_pct * multiplier
                        lines.append(f"⚠️ 高波动建议: 止损距离应调整为 {suggested_distance:.2f}% (当前 {distance_pct:.2f}%)")
            except Exception as e:
                print(f"{timeframe_name}波动率计算失败: {e}", file=sys.stderr)
        
        lines.append(f"模型: {signal.get('entry_model', '未知')}")
        lines.append("")
        
        return lines
    
    # 构建简要版本
    brief_plan.append("## 5分钟信号")
    brief_plan.append("")
    if analysis_5m:
        if analysis_5m['is_garbage_time']:
            brief_plan.append("⚠️ 垃圾时间，建议等待突破")
            brief_plan.append("")
        
        all_signals_5m_brief = []
        if chart_pattern_signals_5m:
            all_signals_5m_brief.extend(chart_pattern_signals_5m)
        if top_trader_patterns_5m and top_trader_patterns_5m.get('all_signals'):
            for signal in top_trader_patterns_5m['all_signals']:
                if signal.get('entry') and signal.get('stop_loss'):
                    risk = abs(signal['entry'] - signal['stop_loss'])
                    take_profit_1 = signal['entry'] + (risk * 2 if signal['type'] == 'long' else -risk * 2) if risk > 0 else (signal['entry'] * 1.02 if signal['type'] == 'long' else signal['entry'] * 0.98)
                    take_profit_2 = signal['entry'] + (risk * 3 if signal['type'] == 'long' else -risk * 3) if risk > 0 else (signal['entry'] * 1.04 if signal['type'] == 'long' else signal['entry'] * 0.96)
                    all_signals_5m_brief.append({
                        'type': signal['type'],
                        'strength': 'strong' if signal.get('strength', 0) > 75 else 'medium',
                        'entry': signal['entry'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit_1': take_profit_1,
                        'take_profit_2': take_profit_2,
                        'entry_model': signal.get('entry_model', f"顶级交易员形态-{signal.get('name', '未知')}"),
                        'reason': signal.get('reason', f"识别到{signal.get('name', '形态')}"),
                        'pattern_priority': 1,
                        'orderbook_stop_loss': None,
                        'orderbook_info': None
                    })
        if bullish_patterns_5m and bullish_patterns_5m.get('patterns'):
            for pattern in bullish_patterns_5m['patterns']:
                risk = abs(pattern['entry'] - pattern['stop_loss'])
                take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
                take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
                all_signals_5m_brief.append({
                    'type': 'long',
                    'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                    'entry': pattern['entry'],
                    'stop_loss': pattern['stop_loss'],
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'entry_model': f"看涨形态-{pattern['name']}",
                    'reason': pattern['description'],
                    'pattern_priority': 1,
                    'orderbook_stop_loss': None,
                    'orderbook_info': None
                })
        if analysis_5m.get('signals'):
            for signal in analysis_5m['signals']:
                signal['pattern_priority'] = 0
                all_signals_5m_brief.append(signal)
        
        if all_signals_5m_brief:
            # 为简要版本也获取订单簿止损
            for signal in all_signals_5m_brief:
                if not signal.get('orderbook_stop_loss'):
                    ob_stop_loss, ob_info = get_orderbook_stop_loss(
                        signal['entry'], signal['type'], current_price
                    )
                    if ob_stop_loss:
                        signal['orderbook_stop_loss'] = ob_stop_loss
                        signal['orderbook_info'] = ob_info
            
            def signal_score_brief(s):
                priority = s.get('pattern_priority', 0) * 10
                strength = 3 if s['strength'] == 'strong' else 2 if s['strength'] == 'medium' else 1
                return priority + strength
            
            best_signal_5m = max(all_signals_5m_brief, key=signal_score_brief)
            brief_plan.extend(format_signal_brief(best_signal_5m, '5分钟', klines_5m))
        else:
            brief_plan.append("无明确信号")
            brief_plan.append("")
    else:
        brief_plan.append("无法分析")
        brief_plan.append("")
    
    brief_plan.append("---")
    brief_plan.append("")
    brief_plan.append("## 15分钟信号")
    brief_plan.append("")
    if analysis_15m:
        if analysis_15m['is_garbage_time']:
            brief_plan.append("⚠️ 垃圾时间，建议等待突破")
            brief_plan.append("")
        
        all_signals_15m_brief = []
        if chart_pattern_signals_15m:
            all_signals_15m_brief.extend(chart_pattern_signals_15m)
        if top_trader_patterns_15m and top_trader_patterns_15m.get('all_signals'):
            for signal in top_trader_patterns_15m['all_signals']:
                if signal.get('entry') and signal.get('stop_loss'):
                    risk = abs(signal['entry'] - signal['stop_loss'])
                    take_profit_1 = signal['entry'] + (risk * 2 if signal['type'] == 'long' else -risk * 2) if risk > 0 else (signal['entry'] * 1.02 if signal['type'] == 'long' else signal['entry'] * 0.98)
                    take_profit_2 = signal['entry'] + (risk * 3 if signal['type'] == 'long' else -risk * 3) if risk > 0 else (signal['entry'] * 1.04 if signal['type'] == 'long' else signal['entry'] * 0.96)
                    all_signals_15m_brief.append({
                        'type': signal['type'],
                        'strength': 'strong' if signal.get('strength', 0) > 75 else 'medium',
                        'entry': signal['entry'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit_1': take_profit_1,
                        'take_profit_2': take_profit_2,
                        'entry_model': signal.get('entry_model', f"顶级交易员形态-{signal.get('name', '未知')}"),
                        'reason': signal.get('reason', f"识别到{signal.get('name', '形态')}"),
                        'pattern_priority': 1,
                        'orderbook_stop_loss': None,
                        'orderbook_info': None
                    })
        if bullish_patterns_15m and bullish_patterns_15m.get('patterns'):
            for pattern in bullish_patterns_15m['patterns']:
                risk = abs(pattern['entry'] - pattern['stop_loss'])
                take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
                take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
                all_signals_15m_brief.append({
                    'type': 'long',
                    'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                    'entry': pattern['entry'],
                    'stop_loss': pattern['stop_loss'],
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'entry_model': f"看涨形态-{pattern['name']}",
                    'reason': pattern['description'],
                    'pattern_priority': 1,
                    'orderbook_stop_loss': None,
                    'orderbook_info': None
                })
        if analysis_15m.get('signals'):
            for signal in analysis_15m['signals']:
                signal['pattern_priority'] = 0
                all_signals_15m_brief.append(signal)
        
        if all_signals_15m_brief:
            # 为简要版本也获取订单簿止损
            for signal in all_signals_15m_brief:
                if not signal.get('orderbook_stop_loss'):
                    ob_stop_loss, ob_info = get_orderbook_stop_loss(
                        signal['entry'], signal['type'], current_price
                    )
                    if ob_stop_loss:
                        signal['orderbook_stop_loss'] = ob_stop_loss
                        signal['orderbook_info'] = ob_info
            
            def signal_score_brief(s):
                priority = s.get('pattern_priority', 0) * 10
                strength = 3 if s['strength'] == 'strong' else 2 if s['strength'] == 'medium' else 1
                return priority + strength
            
            best_signal_15m = max(all_signals_15m_brief, key=signal_score_brief)
            brief_plan.extend(format_signal_brief(best_signal_15m, '15分钟', klines_15m))
        else:
            brief_plan.append("无明确信号")
            brief_plan.append("")
    else:
        brief_plan.append("无法分析")
        brief_plan.append("")
    
    brief_plan.append("---")
    brief_plan.append("")
    brief_plan.append("## 1小时信号")
    brief_plan.append("")
    if analysis_1h:
        if analysis_1h['is_garbage_time']:
            brief_plan.append("⚠️ 垃圾时间，建议等待突破")
            brief_plan.append("")
        
        all_signals_1h_brief = []
        if chart_pattern_signals_1h:
            all_signals_1h_brief.extend(chart_pattern_signals_1h)
        if top_trader_patterns_1h and top_trader_patterns_1h.get('all_signals'):
            for signal in top_trader_patterns_1h['all_signals']:
                if signal.get('entry') and signal.get('stop_loss'):
                    risk = abs(signal['entry'] - signal['stop_loss'])
                    take_profit_1 = signal['entry'] + (risk * 2 if signal['type'] == 'long' else -risk * 2) if risk > 0 else (signal['entry'] * 1.02 if signal['type'] == 'long' else signal['entry'] * 0.98)
                    take_profit_2 = signal['entry'] + (risk * 3 if signal['type'] == 'long' else -risk * 3) if risk > 0 else (signal['entry'] * 1.04 if signal['type'] == 'long' else signal['entry'] * 0.96)
                    all_signals_1h_brief.append({
                        'type': signal['type'],
                        'strength': 'strong' if signal.get('strength', 0) > 75 else 'medium',
                        'entry': signal['entry'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit_1': take_profit_1,
                        'take_profit_2': take_profit_2,
                        'entry_model': signal.get('entry_model', f"顶级交易员形态-{signal.get('name', '未知')}"),
                        'reason': signal.get('reason', f"识别到{signal.get('name', '形态')}"),
                        'pattern_priority': 1,
                        'orderbook_stop_loss': None,
                        'orderbook_info': None
                    })
        if bullish_patterns_1h and bullish_patterns_1h.get('patterns'):
            for pattern in bullish_patterns_1h['patterns']:
                risk = abs(pattern['entry'] - pattern['stop_loss'])
                take_profit_1 = pattern['entry'] + risk * 2 if risk > 0 else pattern['entry'] * 1.02
                take_profit_2 = pattern['entry'] + risk * 3 if risk > 0 else pattern['entry'] * 1.04
                all_signals_1h_brief.append({
                    'type': 'long',
                    'strength': 'strong' if pattern['strength'] > 75 else 'medium',
                    'entry': pattern['entry'],
                    'stop_loss': pattern['stop_loss'],
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'entry_model': f"看涨形态-{pattern['name']}",
                    'reason': pattern['description'],
                    'pattern_priority': 1,
                    'orderbook_stop_loss': None,
                    'orderbook_info': None
                })
        if analysis_1h and analysis_1h.get('signals'):
            for signal in analysis_1h['signals']:
                signal['pattern_priority'] = 0
                all_signals_1h_brief.append(signal)
        
        if all_signals_1h_brief:
            # 为简要版本也获取订单簿止损
            for signal in all_signals_1h_brief:
                if not signal.get('orderbook_stop_loss'):
                    ob_stop_loss, ob_info = get_orderbook_stop_loss(
                        signal['entry'], signal['type'], current_price
                    )
                    if ob_stop_loss:
                        signal['orderbook_stop_loss'] = ob_stop_loss
                        signal['orderbook_info'] = ob_info
            
            def signal_score_brief(s):
                priority = s.get('pattern_priority', 0) * 10
                strength = 3 if s['strength'] == 'strong' else 2 if s['strength'] == 'medium' else 1
                return priority + strength
            
            best_signal_1h = max(all_signals_1h_brief, key=signal_score_brief)
            brief_plan.extend(format_signal_brief(best_signal_1h, '1小时', klines_1h))
        else:
            brief_plan.append("无明确信号")
            brief_plan.append("")
    else:
        brief_plan.append("无法分析")
        brief_plan.append("")
    
    brief_plan.append("---")
    brief_plan.append("")
    brief_plan.append("**免责声明**: 本交易信号基于De.交易系统自动生成，仅供参考。交易有风险，入市需谨慎。")
    
    # 输出计划
    output = "\n".join(plan)
    brief_output = "\n".join(brief_plan)
    
    try:
        print(output)
    except UnicodeEncodeError:
        pass
    
    # 保存到文件（如果通过统一系统调用，会使用统一系统的输出目录）
    from pathlib import Path
    output_dir = Path.cwd()  # 使用当前工作目录，统一系统会设置
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存详细版本
    filename_full = output_dir / f"BTC_de_signals_{timestamp}.md"
    with open(filename_full, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n详细版交易信号已保存到: {filename_full}", file=sys.stderr)
    
    # 保存简要版本
    filename_brief = output_dir / f"BTC_de_signals_简要_{timestamp}.md"
    with open(filename_brief, 'w', encoding='utf-8') as f:
        f.write(brief_output)
    print(f"简要版交易信号已保存到: {filename_brief}", file=sys.stderr)

if __name__ == '__main__':
    generate_trading_plan()

