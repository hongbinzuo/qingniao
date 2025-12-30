#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成LUNA2（Terra 2.0）15分钟和1小时做多做空交易信号
结合De.交易系统和山寨币策略
数据来源：Gate.io / Bitget
"""

import requests
import sys
from datetime import datetime

def get_kline_gateio(symbol='LUNA2', timeframe='15m', limit=200):
    """从Gate.io获取K线数据"""
    try:
        tf_map = {
            '15m': '15m',
            '1h': '1h',
            '4h': '4h'
        }
        interval = tf_map.get(timeframe, '15m')
        
        # 尝试多种交易对格式
        pairs = [f'{symbol}_USDT', f'{symbol}USDT', 'LUNA_USDT', 'LUNAUSDT', 'LUNA2_USDT', 'LUNA2USDT']
        
        for pair in pairs:
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': pair,
                'interval': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data:
                    data.reverse()
                    klines = []
                    for k in data:
                        klines.append({
                            'timestamp': int(k[0]),
                            'open': float(k[5]),
                            'high': float(k[3]),
                            'low': float(k[4]),
                            'close': float(k[2]),
                            'volume': float(k[1])
                        })
                    return klines, pair
    except Exception as e:
        print(f"Gate.io获取失败: {e}", file=sys.stderr)
    return None, None

def get_kline_bitget(symbol='LUNA2', timeframe='15m', limit=200):
    """从Bitget获取K线数据"""
    try:
        tf_map = {
            '15m': '15min',
            '1h': '1hour',
            '4h': '4hour'
        }
        interval = tf_map.get(timeframe, '15min')
        
        symbols = [f'{symbol}USDT', f'{symbol}_USDT', 'LUNAUSDT', 'LUNA_USDT', 'LUNA2USDT', 'LUNA2_USDT']
        
        for sym in symbols:
            url = "https://api.bitget.com/api/spot/v1/market/candles"
            params = {
                'symbol': sym,
                'granularity': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '00000' and data.get('data'):
                    klines_data = data['data']
                    klines_data.reverse()
                    klines = []
                    for k in klines_data:
                        klines.append({
                            'timestamp': int(k[0]) // 1000,
                            'open': float(k[1]),
                            'high': float(k[3]),
                            'low': float(k[4]),
                            'close': float(k[2]),
                            'volume': float(k[5])
                        })
                    return klines, sym
    except Exception as e:
        print(f"Bitget获取失败: {e}", file=sys.stderr)
    return None, None

def get_kline_bybit(symbol='LUNA2', timeframe='15m', limit=200):
    """从Bybit获取K线数据"""
    try:
        tf_map = {
            '15m': '15',
            '1h': '60',
            '4h': '240'
        }
        interval = tf_map.get(timeframe, '15')
        
        # Bybit使用不同的交易对格式
        symbols = ['LUNA2USDT', 'LUNAUSDT']
        
        for sym in symbols:
            url = "https://api.bybit.com/v5/market/kline"
            params = {
                'category': 'spot',
                'symbol': sym,
                'interval': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0 and data.get('result') and data['result'].get('list'):
                    klines_data = data['result']['list']
                    # Bybit返回的是从新到旧，需要反转
                    klines_data.reverse()
                    klines = []
                    for k in klines_data:
                        # Bybit格式: [startTime, open, high, low, close, volume, turnover]
                        klines.append({
                            'timestamp': int(k[0]) // 1000,  # 转换为秒
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4]),
                            'volume': float(k[5])
                        })
                    return klines, sym
    except Exception as e:
        print(f"Bybit获取失败: {e}", file=sys.stderr)
    return None, None

def get_current_price(symbol='LUNA2'):
    """获取当前价格（优先Bybit）"""
    # 优先尝试Bybit
    symbols = ['LUNA2USDT', 'LUNAUSDT']
    for sym in symbols:
        try:
            url = "https://api.bybit.com/v5/market/tickers"
            params = {
                'category': 'spot',
                'symbol': sym
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0 and data.get('result') and data['result'].get('list'):
                    ticker_list = data['result']['list']
                    if ticker_list and len(ticker_list) > 0:
                        return float(ticker_list[0]['lastPrice']), sym, 'bybit'
        except Exception as e:
            print(f"Bybit价格获取失败: {e}", file=sys.stderr)
            pass
    
    # 备用：尝试Gate.io
    pairs = [f'{symbol}_USDT', f'{symbol}USDT', 'LUNA_USDT', 'LUNAUSDT', 'LUNA2_USDT', 'LUNA2USDT']
    for pair in pairs:
        try:
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            params = {'currency_pair': pair}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]['last']), pair, 'gateio'
        except:
            pass
    
    # 备用：尝试Bitget
    symbols = [f'{symbol}USDT', f'{symbol}_USDT', 'LUNAUSDT', 'LUNA_USDT', 'LUNA2USDT', 'LUNA2_USDT']
    for sym in symbols:
        try:
            url = "https://api.bitget.com/api/v2/spot/market/ticker"
            params = {'symbol': sym}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '00000' and data.get('data'):
                    return float(data['data']['last']), sym, 'bitget'
        except:
            pass
    
    return None, None, None

def calculate_ema(prices, period):
    """计算EMA"""
    if len(prices) < period:
        return None
    multiplier = 2.0 / (period + 1)
    ema = [prices[0]]
    for i in range(1, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    return ema[-1]

def calculate_sma(prices, period):
    """计算SMA"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

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
        
        # 上涨FVG
        if prev['high'] < curr['low']:
            fvgs.append({
                'type': 'bullish',
                'low': prev['high'],
                'high': curr['low'],
                'price': (prev['high'] + curr['low']) / 2,
                'index': i
            })
        
        # 下跌FVG
        if prev['low'] > curr['high']:
            fvgs.append({
                'type': 'bearish',
                'low': curr['high'],
                'high': prev['low'],
                'price': (curr['high'] + prev['low']) / 2,
                'index': i
            })
    
    return fvgs[-5:]

def identify_support_resistance(klines, current_price):
    """识别支撑阻力位"""
    if not klines or len(klines) < 50:
        return {'support': [], 'resistance': []}
    
    highs = [k['high'] for k in klines[-50:]]
    lows = [k['low'] for k in klines[-50:]]
    
    sorted_highs = sorted(set(highs), reverse=True)[:3]
    sorted_lows = sorted(set(lows))[:3]
    
    support = [l for l in sorted_lows if l < current_price]
    resistance = [h for h in sorted_highs if h > current_price]
    
    return {
        'support': support[:3],
        'resistance': resistance[:3]
    }

def check_vegas_breakthrough(klines, ema_144, ema_169, current_price):
    """检查Vegas突破"""
    if not ema_144 or not ema_169 or len(klines) < 20:
        return False, False
    
    recent_closes = [k['close'] for k in klines[-20:]]
    recent_highs = [k['high'] for k in klines[-20:]]
    
    if current_price > ema_169:
        for i in range(-5, 0):
            if i < -len(klines):
                continue
            if klines[i]['high'] > ema_169 and (i == -1 or klines[i-1]['high'] <= ema_169):
                return True, True
    elif current_price < ema_144:
        for i in range(-5, 0):
            if i < -len(klines):
                continue
            if klines[i]['low'] < ema_144 and (i == -1 or klines[i-1]['low'] >= ema_144):
                return True, False
    
    return False, False

def check_big_candle(klines, bullish=True):
    """检查大K线"""
    if len(klines) < 1:
        return False
    
    last_k = klines[-1]
    candle_body = abs(last_k['close'] - last_k['open'])
    candle_range = last_k['high'] - last_k['low']
    if candle_range > 0:
        body_ratio = candle_body / candle_range
        if bullish:
            return body_ratio > 0.7 and last_k['close'] > last_k['open']
        else:
            return body_ratio > 0.7 and last_k['close'] < last_k['open']
    return False

def analyze_timeframe(klines, timeframe_name, current_price):
    """分析单个时间框架，生成做多做空信号"""
    if not klines or len(klines) < 50:
        return None
    
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # 计算技术指标
    ema_144 = calculate_ema(closes, 144) if len(closes) >= 144 else None
    ema_169 = calculate_ema(closes, 169) if len(closes) >= 169 else None
    ema_20 = calculate_ema(closes, 20) if len(closes) >= 20 else None
    ema_50 = calculate_ema(closes, 50) if len(closes) >= 50 else None
    vwap = calculate_vwap(klines[-100:])
    rsi = calculate_rsi(closes)
    
    # 识别FVG
    fvgs = identify_fvg(klines[-50:])
    
    # 识别支撑阻力
    sr = identify_support_resistance(klines, current_price)
    
    # 检查Vegas突破
    is_breakthrough, is_support = check_vegas_breakthrough(klines, ema_144, ema_169, current_price)
    
    # 检查大K线
    is_big_bullish = check_big_candle(klines, bullish=True)
    is_big_bearish = check_big_candle(klines, bullish=False)
    
    # 分析信号
    long_signals = []
    short_signals = []
    
    # 1. Vegas通道信号
    if ema_144 and ema_169:
        if current_price > ema_169:
            if is_breakthrough and is_support:
                # 突破后支撑转换
                entry = ema_169 * 1.002
                stop_loss = ema_169 * 0.98
                if is_big_bullish:
                    take_profit_1 = current_price + (current_price - ema_169) * 0.5
                    take_profit_2 = current_price + (current_price - ema_169) * 1.5
                    strength = 'strong'
                else:
                    take_profit_1 = current_price * 1.02
                    take_profit_2 = current_price * 1.05
                    strength = 'medium'
                
                long_signals.append({
                    'type': 'long',
                    'strength': strength,
                    'entry': entry,
                    'stop_loss': stop_loss,
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'reason': f'价格突破Vegas通道后，Vegas成为支撑，回踩不破做多（{"大阳K线" if is_big_bullish else ""}）'
                })
            else:
                # 价格在Vegas上方
                long_signals.append({
                    'type': 'long',
                    'strength': 'medium',
                    'entry': ema_144 * 1.005,
                    'stop_loss': ema_144 * 0.98,
                    'take_profit_1': ema_169 * 1.02,
                    'take_profit_2': current_price * 1.02,
                    'reason': f'价格在Vegas通道上方，回调到{ema_144:.4f}做多'
                })
        elif current_price < ema_144:
            # 价格在Vegas下方
            short_signals.append({
                'type': 'short',
                'strength': 'medium',
                'entry': ema_169 * 0.995,
                'stop_loss': ema_169 * 1.02,
                'take_profit_1': ema_144 * 0.98,
                'take_profit_2': current_price * 0.98,
                'reason': f'价格在Vegas通道下方，反弹到{ema_169:.4f}做空'
            })
    
    # 2. FVG信号
    for fvg in fvgs:
        if fvg['type'] == 'bullish' and current_price < fvg['price']:
            long_signals.append({
                'type': 'long',
                'strength': 'strong',
                'entry': fvg['low'] * 0.99,
                'stop_loss': fvg['low'] * 0.97,
                'take_profit_1': fvg['high'] * 1.01,
                'take_profit_2': fvg['high'] * 1.02,
                'reason': f'FVG做多机会，价格可能回填到{fvg["high"]:.4f}'
            })
        elif fvg['type'] == 'bearish' and current_price > fvg['price']:
            short_signals.append({
                'type': 'short',
                'strength': 'strong',
                'entry': fvg['high'] * 1.01,
                'stop_loss': fvg['high'] * 1.03,
                'take_profit_1': fvg['low'] * 0.99,
                'take_profit_2': fvg['low'] * 0.98,
                'reason': f'FVG做空机会，价格可能回填到{fvg["low"]:.4f}'
            })
    
    # 3. 支撑阻力信号
    if sr['support']:
        nearest_support = max(sr['support'])
        if current_price < nearest_support * 1.01:
            long_signals.append({
                'type': 'long',
                'strength': 'medium',
                'entry': nearest_support * 1.002,
                'stop_loss': nearest_support * 0.98,
                'take_profit_1': current_price * 1.01,
                'take_profit_2': current_price * 1.02,
                'reason': f'价格接近支撑位{nearest_support:.4f}，可能反弹'
            })
    
    if sr['resistance']:
        nearest_resistance = min(sr['resistance'])
        if current_price > nearest_resistance * 0.99:
            short_signals.append({
                'type': 'short',
                'strength': 'medium',
                'entry': nearest_resistance * 0.998,
                'stop_loss': nearest_resistance * 1.02,
                'take_profit_1': current_price * 0.99,
                'take_profit_2': current_price * 0.98,
                'reason': f'价格接近阻力位{nearest_resistance:.4f}，可能回落'
            })
    
    # 4. RSI信号
    if rsi:
        if rsi < 30:
            # 超卖，可能反弹
            if sr['support']:
                nearest_support = max(sr['support'])
                long_signals.append({
                    'type': 'long',
                    'strength': 'medium',
                    'entry': current_price * 1.001,
                    'stop_loss': nearest_support * 0.98,
                    'take_profit_1': current_price * 1.02,
                    'take_profit_2': current_price * 1.03,
                    'reason': f'RSI超卖({rsi:.1f})，可能反弹'
                })
        elif rsi > 70:
            # 超买，可能回调
            if sr['resistance']:
                nearest_resistance = min(sr['resistance'])
                short_signals.append({
                    'type': 'short',
                    'strength': 'medium',
                    'entry': current_price * 0.999,
                    'stop_loss': nearest_resistance * 1.02,
                    'take_profit_1': current_price * 0.98,
                    'take_profit_2': current_price * 0.97,
                    'reason': f'RSI超买({rsi:.1f})，可能回调'
                })
    
    # 5. 趋势信号（EMA排列）
    if ema_20 and ema_50:
        if current_price > ema_20 > ema_50:
            # 上升趋势
            long_signals.append({
                'type': 'long',
                'strength': 'medium',
                'entry': ema_20 * 1.002,
                'stop_loss': ema_20 * 0.98,
                'take_profit_1': current_price * 1.02,
                'take_profit_2': current_price * 1.04,
                'reason': f'上升趋势，价格>EMA20>EMA50，回调到EMA20做多'
            })
        elif current_price < ema_20 < ema_50:
            # 下降趋势
            short_signals.append({
                'type': 'short',
                'strength': 'medium',
                'entry': ema_20 * 0.998,
                'stop_loss': ema_20 * 1.02,
                'take_profit_1': current_price * 0.98,
                'take_profit_2': current_price * 0.96,
                'reason': f'下降趋势，价格<EMA20<EMA50，反弹到EMA20做空'
            })
    
    return {
        'timeframe': timeframe_name,
        'current_price': current_price,
        'ema_144': ema_144,
        'ema_169': ema_169,
        'ema_20': ema_20,
        'ema_50': ema_50,
        'vwap': vwap,
        'rsi': rsi,
        'fvgs': fvgs,
        'support_resistance': sr,
        'is_breakthrough': is_breakthrough,
        'is_support': is_support,
        'long_signals': long_signals,
        'short_signals': short_signals
    }

def generate_trading_signals():
    """生成交易信号"""
    print("正在获取LUNA2市场数据...", file=sys.stderr)
    
    # 获取数据（优先Bybit）
    current_price, price_pair, exchange = get_current_price('LUNA2')
    
    # 优先从Bybit获取K线数据
    klines_15m, pair_15m = get_kline_bybit('LUNA2', '15m', 200)
    if not klines_15m:
        klines_15m, pair_15m = get_kline_gateio('LUNA2', '15m', 200)
    if not klines_15m:
        klines_15m, pair_15m = get_kline_bitget('LUNA2', '15m', 200)
    
    klines_1h, pair_1h = get_kline_bybit('LUNA2', '1h', 200)
    if not klines_1h:
        klines_1h, pair_1h = get_kline_gateio('LUNA2', '1h', 200)
    if not klines_1h:
        klines_1h, pair_1h = get_kline_bitget('LUNA2', '1h', 200)
    
    if not current_price or not klines_15m or not klines_1h:
        print("无法获取LUNA2数据，请确认币种名称", file=sys.stderr)
        return
    
    # 使用最新K线价格
    if abs(klines_1h[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_1h[-1]['close']
    
    # 分析各时间框架
    analysis_15m = analyze_timeframe(klines_15m, '15分钟', current_price)
    analysis_1h = analyze_timeframe(klines_1h, '1小时', current_price)
    
    # 生成报告
    report = []
    report.append("# LUNA2 交易信号（De.交易系统）")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report.append(f"**当前价格**: ${current_price:,.6f}  ")
    report.append(f"**数据来源**: {exchange or 'Gate.io/Bitget'} ({price_pair or pair_1h})  ")
    report.append("")
    
    # 一、15分钟交易信号
    report.append("## 一、15分钟交易信号")
    report.append("")
    
    if analysis_15m:
        # 做多信号
        if analysis_15m['long_signals']:
            best_long = max(analysis_15m['long_signals'], key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
            strength_cn = {'strong': '强', 'medium': '中', 'weak': '弱'}[best_long['strength']]
            
            report.append(f"### 做多信号 ({strength_cn})")
            report.append("")
            report.append(f"**入场**: ${best_long['entry']:,.6f}  ")
            report.append(f"**止损**: ${best_long['stop_loss']:,.6f}  ")
            report.append(f"**止盈1**: ${best_long['take_profit_1']:,.6f} (50%)  ")
            report.append(f"**止盈2**: ${best_long['take_profit_2']:,.6f} (50%)  ")
            report.append(f"**理由**: {best_long['reason']}  ")
            report.append("")
        else:
            report.append("### 做多信号")
            report.append("")
            report.append("无明确做多信号，观望  ")
            report.append("")
        
        # 做空信号
        if analysis_15m['short_signals']:
            best_short = max(analysis_15m['short_signals'], key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
            strength_cn = {'strong': '强', 'medium': '中', 'weak': '弱'}[best_short['strength']]
            
            report.append(f"### 做空信号 ({strength_cn})")
            report.append("")
            report.append(f"**入场**: ${best_short['entry']:,.6f}  ")
            report.append(f"**止损**: ${best_short['stop_loss']:,.6f}  ")
            report.append(f"**止盈1**: ${best_short['take_profit_1']:,.6f} (50%)  ")
            report.append(f"**止盈2**: ${best_short['take_profit_2']:,.6f} (50%)  ")
            report.append(f"**理由**: {best_short['reason']}  ")
            report.append("")
        else:
            report.append("### 做空信号")
            report.append("")
            report.append("无明确做空信号，观望  ")
            report.append("")
    
    # 二、1小时交易信号
    report.append("## 二、1小时交易信号")
    report.append("")
    
    if analysis_1h:
        # 做多信号
        if analysis_1h['long_signals']:
            best_long = max(analysis_1h['long_signals'], key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
            strength_cn = {'strong': '强', 'medium': '中', 'weak': '弱'}[best_long['strength']]
            
            report.append(f"### 做多信号 ({strength_cn})")
            report.append("")
            report.append(f"**入场**: ${best_long['entry']:,.6f}  ")
            report.append(f"**止损**: ${best_long['stop_loss']:,.6f}  ")
            report.append(f"**止盈1**: ${best_long['take_profit_1']:,.6f} (50%)  ")
            report.append(f"**止盈2**: ${best_long['take_profit_2']:,.6f} (50%)  ")
            report.append(f"**理由**: {best_long['reason']}  ")
            report.append("")
        else:
            report.append("### 做多信号")
            report.append("")
            report.append("无明确做多信号，观望  ")
            report.append("")
        
        # 做空信号
        if analysis_1h['short_signals']:
            best_short = max(analysis_1h['short_signals'], key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
            strength_cn = {'strong': '强', 'medium': '中', 'weak': '弱'}[best_short['strength']]
            
            report.append(f"### 做空信号 ({strength_cn})")
            report.append("")
            report.append(f"**入场**: ${best_short['entry']:,.6f}  ")
            report.append(f"**止损**: ${best_short['stop_loss']:,.6f}  ")
            report.append(f"**止盈1**: ${best_short['take_profit_1']:,.6f} (50%)  ")
            report.append(f"**止盈2**: ${best_short['take_profit_2']:,.6f} (50%)  ")
            report.append(f"**理由**: {best_short['reason']}  ")
            report.append("")
        else:
            report.append("### 做空信号")
            report.append("")
            report.append("无明确做空信号，观望  ")
            report.append("")
    
    # 三、详细技术分析
    report.append("---")
    report.append("")
    report.append("## 三、详细技术分析说明")
    report.append("")
    
    # 15分钟详细分析
    if analysis_15m:
        report.append("### 3.1 15分钟级别技术指标")
        report.append("")
        report.append(f"**当前价格**: ${analysis_15m['current_price']:,.6f}  ")
        report.append("")
        
        if analysis_15m['ema_144'] and analysis_15m['ema_169']:
            report.append(f"**Vegas通道**:")
            report.append(f"  - EMA144: ${analysis_15m['ema_144']:,.6f}  ")
            report.append(f"  - EMA169: ${analysis_15m['ema_169']:,.6f}  ")
            if current_price > analysis_15m['ema_169']:
                report.append("  → 价格在通道上方，偏多  ")
            elif current_price < analysis_15m['ema_144']:
                report.append("  → 价格在通道下方，偏空  ")
            else:
                report.append("  → 价格在通道内，震荡  ")
            report.append("")
        
        if analysis_15m['ema_20'] and analysis_15m['ema_50']:
            report.append(f"**趋势均线**:")
            report.append(f"  - EMA20: ${analysis_15m['ema_20']:,.6f}  ")
            report.append(f"  - EMA50: ${analysis_15m['ema_50']:,.6f}  ")
            if current_price > analysis_15m['ema_20'] > analysis_15m['ema_50']:
                report.append("  → 上升趋势  ")
            elif current_price < analysis_15m['ema_20'] < analysis_15m['ema_50']:
                report.append("  → 下降趋势  ")
            else:
                report.append("  → 震荡趋势  ")
            report.append("")
        
        if analysis_15m['vwap']:
            report.append(f"**VWAP**: ${analysis_15m['vwap']:,.6f}  ")
            if current_price > analysis_15m['vwap']:
                report.append("  → 价格在VWAP上方，VWAP作为支撑  ")
            else:
                report.append("  → 价格在VWAP下方，VWAP作为阻力  ")
            report.append("")
        
        if analysis_15m['rsi']:
            report.append(f"**RSI**: {analysis_15m['rsi']:.1f}  ")
            if analysis_15m['rsi'] > 70:
                report.append("  → 超买区域，可能回调  ")
            elif analysis_15m['rsi'] < 30:
                report.append("  → 超卖区域，可能反弹  ")
            else:
                report.append("  → 正常区域  ")
            report.append("")
        
        if analysis_15m['fvgs']:
            report.append(f"**FVG**: 发现{len(analysis_15m['fvgs'])}个FVG  ")
            for fvg in analysis_15m['fvgs'][-3:]:
                fvg_type = "上涨" if fvg['type'] == 'bullish' else "下跌"
                report.append(f"  - {fvg_type}FVG: ${fvg['low']:,.6f} - ${fvg['high']:,.6f}  ")
            report.append("")
        
        if analysis_15m['support_resistance']['support']:
            report.append("**支撑位**:")
            for i, sup in enumerate(analysis_15m['support_resistance']['support'][:3], 1):
                report.append(f"  - 支撑{i}: ${sup:,.6f}  ")
            report.append("")
        
        if analysis_15m['support_resistance']['resistance']:
            report.append("**阻力位**:")
            for i, res in enumerate(analysis_15m['support_resistance']['resistance'][:3], 1):
                report.append(f"  - 阻力{i}: ${res:,.6f}  ")
            report.append("")
    
    # 1小时详细分析
    if analysis_1h:
        report.append("### 3.2 1小时级别技术指标")
        report.append("")
        report.append(f"**当前价格**: ${analysis_1h['current_price']:,.6f}  ")
        report.append("")
        
        if analysis_1h['ema_144'] and analysis_1h['ema_169']:
            report.append(f"**Vegas通道**:")
            report.append(f"  - EMA144: ${analysis_1h['ema_144']:,.6f}  ")
            report.append(f"  - EMA169: ${analysis_1h['ema_169']:,.6f}  ")
            report.append("")
        
        if analysis_1h['rsi']:
            report.append(f"**RSI**: {analysis_1h['rsi']:.1f}  ")
            report.append("")
    
    # 四、信号强度说明
    report.append("## 四、信号强度说明")
    report.append("")
    report.append("**信号强度评级**:")
    report.append("- **强**: 高可靠性信号，通常来自：")
    report.append("  - FVG信号（价格缺口，通常会被回填）")
    report.append("  - Vegas突破后支撑转换（突破后Vegas成为支撑/阻力）")
    report.append("  - 大阳/大阴K线 + 突破信号")
    report.append("")
    report.append("- **中**: 中等可靠性信号，通常来自：")
    report.append("  - Vegas通道信号（价格在EMA144/169通道附近）")
    report.append("  - 支撑阻力信号（价格接近历史支撑/阻力位）")
    report.append("  - RSI超买/超卖信号")
    report.append("  - 趋势信号（EMA排列）")
    report.append("")
    report.append("- **弱**: 较低可靠性信号，通常来自：")
    report.append("  - 单一技术指标信号")
    report.append("  - 未确认的信号")
    report.append("")
    
    # 五、交易执行检查清单
    report.append("## 五、交易执行检查清单")
    report.append("")
    report.append("**入场前**:")
    report.append("□ 是否确认信号强度？")
    report.append("□ 是否有FVG机会？")
    report.append("□ 是否突破Vegas通道？（突破后Vegas成为支撑/阻力）")
    report.append("□ 多时间框架是否确认？（15分钟、1小时）")
    report.append("□ 是否有明确的支撑/阻力位？")
    report.append("□ RSI是否在合理区域？")
    report.append("")
    report.append("**头寸管理**:")
    report.append("□ 是否设置为逐仓模式？（必须逐仓）")
    report.append("□ 是否立即设置了止损？（头寸接到就要设置）")
    report.append("□ 止损是否合理？（2-3%）")
    report.append("□ 是否一比归一比？（每个头寸独立设置止损）")
    report.append("")
    report.append("**风险管理**:")
    report.append("□ 已设置止损（窄止损2-3%，止损是省钱）")
    report.append("□ 已设置分批止盈（50%+50%）")
    report.append("□ 仓位大小已计算（风险2-3%）")
    report.append("□ 盈亏比≥2:1")
    report.append("□ 盈利2-3%后是否移动止损到保本？")
    report.append("")
    
    report.append("---")
    report.append("")
    report.append("**免责声明**: 本交易信号基于De.交易系统自动生成，仅供参考。交易有风险，入市需谨慎。")
    
    # 输出报告
    output = "\n".join(report)
    try:
        print(output)
    except UnicodeEncodeError:
        pass
    
    # 保存到文件
    filename = f"LUNA2_trading_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n交易信号已保存到: {filename}", file=sys.stderr)

if __name__ == '__main__':
    generate_trading_signals()

