#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据De.交易系统生成BTC 5分钟、15分钟、1小时交易计划
数据来源：Gate.io / Bitget
"""

import requests
import sys
from datetime import datetime

def get_btc_kline_gateio(timeframe='5m', limit=200):
    """从Gate.io获取BTC K线数据"""
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h'}
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
                return klines
    except Exception as e:
        print(f"Gate.io获取失败: {e}", file=sys.stderr)
    return None

def get_btc_kline_bitget(timeframe='5m', limit=200):
    """从Bitget获取BTC K线数据（备用）"""
    try:
        tf_map = {'5m': '5min', '15m': '15min', '1h': '1hour', '4h': '4hour'}
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
                return klines
    except:
        pass
    return None

def get_btc_current_price():
    """获取BTC当前价格"""
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
    return None

def get_order_book_gateio(limit=20):
    """从Gate.io获取BTC订单簿数据"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/order_book"
        params = {
            'currency_pair': 'BTC_USDT',
            'limit': limit,
            'interval': '0'  # 实时数据
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                bids = [(float(b[0]), float(b[1])) for b in data.get('bids', [])]  # (价格, 数量)
                asks = [(float(a[0]), float(a[1])) for a in data.get('asks', [])]  # (价格, 数量)
                return {
                    'bids': bids,
                    'asks': asks,
                    'timestamp': data.get('t', 0)
                }
    except Exception as e:
        print(f"Gate.io订单簿获取失败: {e}", file=sys.stderr)
    return None

def get_order_book_bitget(limit=20):
    """从Bitget获取BTC订单簿数据（备用）"""
    try:
        url = "https://api.bitget.com/api/spot/v1/market/depth"
        params = {
            'symbol': 'BTCUSDT',
            'limit': limit,
            'type': 'step0'  # 合并深度类型
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                order_data = data['data']
                bids = [(float(b[0]), float(b[1])) for b in order_data.get('bids', [])]
                asks = [(float(a[0]), float(a[1])) for a in order_data.get('asks', [])]
                return {
                    'bids': bids,
                    'asks': asks,
                    'timestamp': order_data.get('ts', 0)
                }
    except Exception as e:
        print(f"Bitget订单簿获取失败: {e}", file=sys.stderr)
    return None

def analyze_liquidity_zones(order_book, current_price):
    """分析订单簿，识别流动性区域（De.规则：密集区上下20%+中间60%不开单）"""
    if not order_book:
        return None
    
    bids = order_book['bids']  # 买单 [(价格, 数量), ...]
    asks = order_book['asks']  # 卖单 [(价格, 数量), ...]
    
    # 计算每个价格档位的总挂单量
    bid_zones = {}  # {价格: 总挂单量}
    ask_zones = {}  # {价格: 总挂单量}
    
    # 分析买单（支撑位）
    for price, amount in bids:
        # 将价格四舍五入到整数（BTC价格通常以整数为单位）
        rounded_price = round(price / 100) * 100  # 四舍五入到百位
        if rounded_price not in bid_zones:
            bid_zones[rounded_price] = 0
        bid_zones[rounded_price] += amount
    
    # 分析卖单（阻力位）
    for price, amount in asks:
        rounded_price = round(price / 100) * 100
        if rounded_price not in ask_zones:
            ask_zones[rounded_price] = 0
        ask_zones[rounded_price] += amount
    
    # 识别流动性密集区（挂单量大的区域）
    # 计算平均挂单量
    if bid_zones:
        avg_bid_volume = sum(bid_zones.values()) / len(bid_zones)
        dense_bid_zones = [price for price, vol in bid_zones.items() if vol > avg_bid_volume * 1.5]
    else:
        dense_bid_zones = []
    
    if ask_zones:
        avg_ask_volume = sum(ask_zones.values()) / len(ask_zones)
        dense_ask_zones = [price for price, vol in ask_zones.items() if vol > avg_ask_volume * 1.5]
    else:
        dense_ask_zones = []
    
    # 识别流动性稀疏区（挂单量小的区域）
    sparse_bid_zones = [price for price, vol in bid_zones.items() if vol < avg_bid_volume * 0.5] if bid_zones else []
    sparse_ask_zones = [price for price, vol in ask_zones.items() if vol < avg_ask_volume * 0.5] if ask_zones else []
    
    # De.规则：为每个密集区设置"不开单区域"（正态分布）
    # 每个密集区周围：上20% + 中间60% + 下20% = 100%不开单区域
    no_trade_bid_zones = []  # 买单密集区的不开单区域列表
    no_trade_ask_zones = []  # 卖单密集区的不开单区域列表
    
    for dense_price in dense_bid_zones:
        # 计算上下20%区域（正态分布）
        upper_20 = dense_price * 1.20  # 上20%
        lower_20 = dense_price * 0.80  # 下20%
        # 中间60%就是 dense_price * 0.80 到 dense_price * 1.20
        no_trade_bid_zones.append({
            'center': dense_price,
            'upper_bound': upper_20,
            'lower_bound': lower_20,
            'no_trade_range': (lower_20, upper_20)  # 整个不开单区域
        })
    
    for dense_price in dense_ask_zones:
        upper_20 = dense_price * 1.20
        lower_20 = dense_price * 0.80
        no_trade_ask_zones.append({
            'center': dense_price,
            'upper_bound': upper_20,
            'lower_bound': lower_20,
            'no_trade_range': (lower_20, upper_20)
        })
    
    return {
        'bid_zones': bid_zones,  # 所有买单区域
        'ask_zones': ask_zones,  # 所有卖单区域
        'dense_bid_zones': sorted(dense_bid_zones, reverse=True),  # 买单密集区（支撑位）
        'dense_ask_zones': sorted(dense_ask_zones),  # 卖单密集区（阻力位）
        'sparse_bid_zones': sorted(sparse_bid_zones, reverse=True),  # 买单稀疏区
        'sparse_ask_zones': sorted(sparse_ask_zones),  # 卖单稀疏区
        'no_trade_bid_zones': no_trade_bid_zones,  # 买单密集区的不开单区域（De.规则）
        'no_trade_ask_zones': no_trade_ask_zones,  # 卖单密集区的不开单区域（De.规则）
        'current_price': current_price
    }

def is_in_no_trade_zone(price, no_trade_zones):
    """检查价格是否在不开单区域内（De.规则）"""
    for zone in no_trade_zones:
        lower, upper = zone['no_trade_range']
        if lower <= price <= upper:
            return True, zone
    return False, None

def suggest_stop_loss_by_liquidity(entry_price, signal_type, liquidity_analysis):
    """根据流动性分析给出止损建议（De.规则：密集区上下20%+中间60%不开单）"""
    if not liquidity_analysis:
        return None, "无法获取订单簿数据"
    
    suggestions = []
    no_trade_bid_zones = liquidity_analysis.get('no_trade_bid_zones', [])
    no_trade_ask_zones = liquidity_analysis.get('no_trade_ask_zones', [])
    
    if signal_type == 'long':
        # 做多止损：放在买单密集区下方，但在流动性稀疏区
        dense_bid_zones = liquidity_analysis['dense_bid_zones']
        sparse_bid_zones = liquidity_analysis['sparse_bid_zones']
        current_price = liquidity_analysis['current_price']
        
        # 找到入场价下方的买单密集区
        support_zones = [zone for zone in dense_bid_zones if zone < entry_price]
        
        if support_zones:
            nearest_support = max(support_zones)  # 最近的支撑位
            
            # 检查入场价是否在不开单区域内
            in_no_trade, no_trade_zone = is_in_no_trade_zone(entry_price, no_trade_bid_zones)
            if in_no_trade:
                # 如果入场价在不开单区域内，止损应该放在不开单区域下方
                stop_loss = no_trade_zone['lower_bound'] * 0.99  # 不开单区域下方1%
                suggestions.append({
                    'stop_loss': stop_loss,
                    'distance': entry_price - stop_loss,
                    'distance_pct': ((entry_price - stop_loss) / entry_price) * 100,
                    'reason': f'入场价在不开单区域内（密集区{no_trade_zone["center"]:.0f}的上下20%+中间60%），止损放在不开单区域下方{stop_loss:.0f}',
                    'support_zone': nearest_support,
                    'no_trade_zone': no_trade_zone
                })
            else:
                # 在支撑位下方找流动性稀疏区，但要避开不开单区域
                sparse_below = [zone for zone in sparse_bid_zones if zone < nearest_support]
                
                # 过滤掉不开单区域内的价格
                valid_sparse = []
                for zone_price in sparse_below:
                    in_zone, _ = is_in_no_trade_zone(zone_price, no_trade_bid_zones)
                    if not in_zone:
                        valid_sparse.append(zone_price)
                
                if valid_sparse:
                    # 选择支撑位下方最近的稀疏区（不在不开单区域内）
                    stop_loss = max(valid_sparse)
                    suggestions.append({
                        'stop_loss': stop_loss,
                        'distance': entry_price - stop_loss,
                        'distance_pct': ((entry_price - stop_loss) / entry_price) * 100,
                        'reason': f'买单密集区在{nearest_support:.0f}，止损放在流动性稀疏区{stop_loss:.0f}（避开不开单区域）',
                        'support_zone': nearest_support
                    })
                else:
                    # 如果没有稀疏区，放在支撑位下方，但要避开不开单区域
                    candidate_stop = nearest_support * 0.98
                    in_zone, zone_info = is_in_no_trade_zone(candidate_stop, no_trade_bid_zones)
                    if in_zone:
                        stop_loss = zone_info['lower_bound'] * 0.99
                    else:
                        stop_loss = candidate_stop
                    suggestions.append({
                        'stop_loss': stop_loss,
                        'distance': entry_price - stop_loss,
                        'distance_pct': ((entry_price - stop_loss) / entry_price) * 100,
                        'reason': f'买单密集区在{nearest_support:.0f}，止损放在{stop_loss:.0f}（避开不开单区域）',
                        'support_zone': nearest_support
                    })
        else:
            # 如果没有明显的支撑位，使用默认止损
            stop_loss = entry_price * 0.985  # 默认1.5%
            suggestions.append({
                'stop_loss': stop_loss,
                'distance': entry_price - stop_loss,
                'distance_pct': 1.5,
                'reason': '未发现明显的买单密集区，使用默认止损（入场价下方1.5%）',
                'support_zone': None
            })
    else:  # short
        # 做空止损：放在卖单密集区上方，但在流动性稀疏区
        dense_ask_zones = liquidity_analysis['dense_ask_zones']
        sparse_ask_zones = liquidity_analysis['sparse_ask_zones']
        current_price = liquidity_analysis['current_price']
        
        # 找到入场价上方的卖单密集区
        resistance_zones = [zone for zone in dense_ask_zones if zone > entry_price]
        
        if resistance_zones:
            nearest_resistance = min(resistance_zones)  # 最近的阻力位
            
            # 检查入场价是否在不开单区域内
            in_no_trade, no_trade_zone = is_in_no_trade_zone(entry_price, no_trade_ask_zones)
            if in_no_trade:
                # 如果入场价在不开单区域内，止损应该放在不开单区域上方
                stop_loss = no_trade_zone['upper_bound'] * 1.01  # 不开单区域上方1%
                suggestions.append({
                    'stop_loss': stop_loss,
                    'distance': stop_loss - entry_price,
                    'distance_pct': ((stop_loss - entry_price) / entry_price) * 100,
                    'reason': f'入场价在不开单区域内（密集区{no_trade_zone["center"]:.0f}的上下20%+中间60%），止损放在不开单区域上方{stop_loss:.0f}',
                    'resistance_zone': nearest_resistance,
                    'no_trade_zone': no_trade_zone
                })
            else:
                # 在阻力位上方找流动性稀疏区，但要避开不开单区域
                sparse_above = [zone for zone in sparse_ask_zones if zone > nearest_resistance]
                
                # 过滤掉不开单区域内的价格
                valid_sparse = []
                for zone_price in sparse_above:
                    in_zone, _ = is_in_no_trade_zone(zone_price, no_trade_ask_zones)
                    if not in_zone:
                        valid_sparse.append(zone_price)
                
                if valid_sparse:
                    # 选择阻力位上方最近的稀疏区（不在不开单区域内）
                    stop_loss = min(valid_sparse)
                    suggestions.append({
                        'stop_loss': stop_loss,
                        'distance': stop_loss - entry_price,
                        'distance_pct': ((stop_loss - entry_price) / entry_price) * 100,
                        'reason': f'卖单密集区在{nearest_resistance:.0f}，止损放在流动性稀疏区{stop_loss:.0f}（避开不开单区域）',
                        'resistance_zone': nearest_resistance
                    })
                else:
                    # 如果没有稀疏区，放在阻力位上方，但要避开不开单区域
                    candidate_stop = nearest_resistance * 1.02
                    in_zone, zone_info = is_in_no_trade_zone(candidate_stop, no_trade_ask_zones)
                    if in_zone:
                        stop_loss = zone_info['upper_bound'] * 1.01
                    else:
                        stop_loss = candidate_stop
                    suggestions.append({
                        'stop_loss': stop_loss,
                        'distance': stop_loss - entry_price,
                        'distance_pct': ((stop_loss - entry_price) / entry_price) * 100,
                        'reason': f'卖单密集区在{nearest_resistance:.0f}，止损放在{stop_loss:.0f}（避开不开单区域）',
                        'resistance_zone': nearest_resistance
                    })
        else:
            # 如果没有明显的阻力位，使用默认止损
            stop_loss = entry_price * 1.015  # 默认1.5%
            suggestions.append({
                'stop_loss': stop_loss,
                'distance': stop_loss - entry_price,
                'distance_pct': 1.5,
                'reason': '未发现明显的卖单密集区，使用默认止损（入场价上方1.5%）',
                'resistance_zone': None
            })
    
    # 返回最佳建议
    if suggestions:
        best = suggestions[0]
        return best['stop_loss'], best
    return None, None

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

def detect_m_top(klines, lookback=50):
    """检测M顶形态（双顶形态）"""
    if len(klines) < 20:
        return None
    
    recent_klines = klines[-lookback:]
    highs = [k['high'] for k in recent_klines]
    
    # 寻找两个相近的高点
    for i in range(10, len(recent_klines) - 10):
        peak1 = recent_klines[i]['high']
        # 寻找第二个高点（在第一个高点之后）
        for j in range(i + 5, len(recent_klines) - 5):
            peak2 = recent_klines[j]['high']
            # 两个高点相近（误差2%以内）
            if abs(peak1 - peak2) / max(peak1, peak2) < 0.02:
                # 检查中间是否有明显的低点（形成M形状）
                middle_lows = [k['low'] for k in recent_klines[i:j+1]]
                middle_low = min(middle_lows)
                # 中间低点应该明显低于两个高点（至少3%）
                if (peak1 - middle_low) / peak1 > 0.03 and (peak2 - middle_low) / peak2 > 0.03:
                    # 计算腰线（两个高点之间的中点）
                    neckline = (peak1 + peak2) / 2
                    return {
                        'type': 'm_top',
                        'peak1': peak1,
                        'peak2': peak2,
                        'neckline': neckline,
                        'middle_low': middle_low,
                        'peak1_index': i,
                        'peak2_index': j,
                        'is_valid': True
                    }
    return None

def detect_w_bottom(klines, lookback=50):
    """检测W底形态（双底形态）"""
    if len(klines) < 20:
        return None
    
    recent_klines = klines[-lookback:]
    lows = [k['low'] for k in recent_klines]
    
    # 寻找两个相近的低点
    for i in range(10, len(recent_klines) - 10):
        bottom1 = recent_klines[i]['low']
        # 寻找第二个低点（在第一个低点之后）
        for j in range(i + 5, len(recent_klines) - 5):
            bottom2 = recent_klines[j]['low']
            # 两个低点相近（误差2%以内）
            if abs(bottom1 - bottom2) / max(bottom1, bottom2) < 0.02:
                # 检查中间是否有明显的高点（形成W形状）
                middle_highs = [k['high'] for k in recent_klines[i:j+1]]
                middle_high = max(middle_highs)
                # 中间高点应该明显高于两个低点（至少3%）
                if (middle_high - bottom1) / bottom1 > 0.03 and (middle_high - bottom2) / bottom2 > 0.03:
                    # 计算腰线（两个低点之间的中点）
                    neckline = (bottom1 + bottom2) / 2
                    return {
                        'type': 'w_bottom',
                        'bottom1': bottom1,
                        'bottom2': bottom2,
                        'neckline': neckline,
                        'middle_high': middle_high,
                        'bottom1_index': i,
                        'bottom2_index': j,
                        'is_valid': True
                    }
    return None

def calculate_fibonacci_retracement(high, low):
    """计算斐波那契回撤位（重点关注618和786）"""
    diff = high - low
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
            'below_618': False
        }
    elif current_price > fib_786:
        return {
            'in_ote_zone': False,
            'fib_618': fib_618,
            'fib_786': fib_786,
            'current_price': current_price,
            'above_786': True,  # 突破786，看涨信号
            'below_618': False
        }
    elif current_price < fib_618:
        return {
            'in_ote_zone': False,
            'fib_618': fib_618,
            'fib_786': fib_786,
            'current_price': current_price,
            'above_786': False,
            'below_618': True  # 跌破618，可能继续下跌
        }
    return None

def check_vegas_breakthrough(klines, ema_144, ema_169, current_price):
    """检查Vegas突破（突破后支撑转换）"""
    if not ema_144 or not ema_169 or len(klines) < 20:
        return False, False
    
    # 检查最近是否有突破
    recent_closes = [k['close'] for k in klines[-20:]]
    recent_highs = [k['high'] for k in klines[-20:]]
    
    # 如果当前价格在Vegas上方，且之前有突破行为
    if current_price > ema_169:
        for i in range(-5, 0):
            if i < -len(klines):
                continue
            if klines[i]['high'] > ema_169 and (i == -1 or klines[i-1]['high'] <= ema_169):
                return True, True  # 突破，且Vegas成为支撑
    elif current_price < ema_144:
        for i in range(-5, 0):
            if i < -len(klines):
                continue
            if klines[i]['low'] < ema_144 and (i == -1 or klines[i-1]['low'] >= ema_144):
                return True, False  # 跌破，且Vegas成为阻力
    
    return False, False

def check_big_bullish_candle(klines):
    """检查大阳K线"""
    if len(klines) < 1:
        return False
    
    last_k = klines[-1]
    candle_body = abs(last_k['close'] - last_k['open'])
    candle_range = last_k['high'] - last_k['low']
    if candle_range > 0:
        body_ratio = candle_body / candle_range
        # 大阳K线：实体占比>70%，且是阳线
        if body_ratio > 0.7 and last_k['close'] > last_k['open']:
            return True
    return False

def identify_support_resistance(klines, current_price):
    """识别支撑阻力位"""
    if not klines or len(klines) < 50:
        return {'support': [], 'resistance': []}
    
    highs = [k['high'] for k in klines[-50:]]
    lows = [k['low'] for k in klines[-50:]]
    
    recent_high = max(highs)
    recent_low = min(lows)
    
    sorted_highs = sorted(set(highs), reverse=True)[:3]
    sorted_lows = sorted(set(lows))[:3]
    
    support = [l for l in sorted_lows if l < current_price]
    resistance = [h for h in sorted_highs if h > current_price]
    
    return {
        'support': support[:3],
        'resistance': resistance[:3]
    }

def check_garbage_time(klines, current_price):
    """检查是否在垃圾时间内"""
    if len(klines) < 20:
        return False, None
    
    recent_highs = [k['high'] for k in klines[-20:]]
    recent_lows = [k['low'] for k in klines[-20:]]
    
    range_high = max(recent_highs)
    range_low = min(recent_lows)
    range_size = range_high - range_low
    range_pct = range_size / current_price if current_price > 0 else 0
    
    if range_pct < 0.02 and range_low < current_price < range_high:
        return True, (range_low, range_high)
    
    return False, None

def analyze_naked_kline(klines, lookback=10):
    """裸K分析：识别看涨/看跌K线形态"""
    if not klines or len(klines) < 3:
        return {'signal': 'neutral', 'patterns': [], 'strength': 0, 'details': {}}
    
    patterns = []
    bullish_score = 0
    bearish_score = 0
    details = {}
    
    # 分析最近几根K线
    recent_klines = klines[-lookback:] if len(klines) >= lookback else klines
    
    for i in range(len(recent_klines) - 2, len(recent_klines)):
        if i < 0:
            continue
        k = recent_klines[i]
        prev_k = recent_klines[i-1] if i > 0 else None
        
        open_price = k['open']
        close_price = k['close']
        high_price = k['high']
        low_price = k['low']
        
        body = abs(close_price - open_price)
        total_range = high_price - low_price
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price
        
        if total_range == 0:
            continue
        
        body_ratio = body / total_range
        upper_shadow_ratio = upper_shadow / total_range if total_range > 0 else 0
        lower_shadow_ratio = lower_shadow / total_range if total_range > 0 else 0
        
        is_bullish = close_price > open_price
        
        # 1. 锤子线/上吊线（Hammer/Hanging Man）
        if lower_shadow_ratio > 0.6 and body_ratio < 0.3 and upper_shadow_ratio < 0.1:
            if is_bullish:
                patterns.append("锤子线（看涨反转）")
                bullish_score += 3
            else:
                patterns.append("上吊线（看跌反转）")
                bearish_score += 2
        
        # 2. 倒锤子线/流星（Inverted Hammer/Shooting Star）
        if upper_shadow_ratio > 0.6 and body_ratio < 0.3 and lower_shadow_ratio < 0.1:
            if is_bullish:
                patterns.append("倒锤子线（看涨反转）")
                bullish_score += 2
            else:
                patterns.append("流星（看跌反转）")
                bearish_score += 3
        
        # 3. 看涨/看跌吞没（Engulfing）
        if prev_k:
            prev_body = abs(prev_k['close'] - prev_k['open'])
            prev_is_bullish = prev_k['close'] > prev_k['open']
            
            if (is_bullish and not prev_is_bullish and 
                close_price > prev_k['open'] and open_price < prev_k['close'] and
                body > prev_body * 1.1):
                patterns.append("看涨吞没")
                bullish_score += 4
            elif (not is_bullish and prev_is_bullish and
                  close_price < prev_k['open'] and open_price > prev_k['close'] and
                  body > prev_body * 1.1):
                patterns.append("看跌吞没")
                bearish_score += 4
        
        # 4. 大阳线/大阴线
        if body_ratio > 0.7:
            if is_bullish:
                patterns.append("大阳线")
                bullish_score += 2
            else:
                patterns.append("大阴线")
                bearish_score += 2
        
        # 5. 十字星（Doji）
        if body_ratio < 0.1:
            patterns.append("十字星（犹豫）")
            # 十字星本身不明确，但结合位置判断
        
        # 6. 看涨/看跌刺穿（Piercing Pattern/Dark Cloud）
        if prev_k and len(recent_klines) > 1:
            prev_close = prev_k['close']
            prev_open = prev_k['open']
            prev_is_bullish = prev_close > prev_open
            
            if (not prev_is_bullish and is_bullish and
                open_price < prev_close and close_price > (prev_open + prev_close) / 2):
                patterns.append("看涨刺穿")
                bullish_score += 3
            elif (prev_is_bullish and not is_bullish and
                  open_price > prev_close and close_price < (prev_open + prev_close) / 2):
                patterns.append("乌云盖顶")
                bearish_score += 3
    
    # 分析最近3根K线的组合形态
    if len(recent_klines) >= 3:
        k1 = recent_klines[-3]
        k2 = recent_klines[-2]
        k3 = recent_klines[-1]
        
        # 晨星（Morning Star）
        if (k1['close'] < k1['open'] and  # 第一根阴线
            abs(k2['close'] - k2['open']) / (k2['high'] - k2['low']) < 0.3 and  # 第二根小实体
            k3['close'] > k3['open'] and  # 第三根阳线
            k3['close'] > (k1['open'] + k1['close']) / 2):  # 第三根收盘价超过第一根中点
            patterns.append("晨星（看涨反转）")
            bullish_score += 5
        
        # 暮星（Evening Star）
        if (k1['close'] > k1['open'] and  # 第一根阳线
            abs(k2['close'] - k2['open']) / (k2['high'] - k2['low']) < 0.3 and  # 第二根小实体
            k3['close'] < k3['open'] and  # 第三根阴线
            k3['close'] < (k1['open'] + k1['close']) / 2):  # 第三根收盘价低于第一根中点
            patterns.append("暮星（看跌反转）")
            bearish_score += 5
    
    # 判断信号
    if bullish_score > bearish_score and bullish_score >= 3:
        signal = 'bullish'
        strength = min(bullish_score, 10)
    elif bearish_score > bullish_score and bearish_score >= 3:
        signal = 'bearish'
        strength = min(bearish_score, 10)
    else:
        signal = 'neutral'
        strength = 0
    
    details = {
        'bullish_score': bullish_score,
        'bearish_score': bearish_score,
        'last_candle': {
            'body_ratio': body_ratio if len(recent_klines) > 0 else 0,
            'is_bullish': is_bullish if len(recent_klines) > 0 else False,
            'upper_shadow_ratio': upper_shadow_ratio if len(recent_klines) > 0 else 0,
            'lower_shadow_ratio': lower_shadow_ratio if len(recent_klines) > 0 else 0
        } if len(recent_klines) > 0 else {}
    }
    
    return {
        'signal': signal,
        'patterns': patterns,
        'strength': strength,
        'details': details
    }

def find_recent_key_levels(klines, current_price, lookback=50):
    """找到最近的关键价位（低点、高点、FVG边界）"""
    if not klines or len(klines) < 10:
        return {'recent_low': None, 'recent_high': None, 'swing_low': None, 'swing_high': None}
    
    recent_klines = klines[-lookback:]
    lows = [k['low'] for k in recent_klines]
    highs = [k['high'] for k in recent_klines]
    
    # 最近的低点和高点
    recent_low = min(lows)
    recent_high = max(highs)
    
    # 寻找摆动低点（swing low）和摆动高点（swing high）
    swing_low = None
    swing_high = None
    
    # 寻找摆动低点：比前后K线都低的点
    for i in range(2, len(recent_klines) - 2):
        if (recent_klines[i]['low'] < recent_klines[i-1]['low'] and 
            recent_klines[i]['low'] < recent_klines[i-2]['low'] and
            recent_klines[i]['low'] < recent_klines[i+1]['low'] and
            recent_klines[i]['low'] < recent_klines[i+2]['low']):
            if swing_low is None or recent_klines[i]['low'] < swing_low:
                swing_low = recent_klines[i]['low']
    
    # 寻找摆动高点：比前后K线都高的点
    for i in range(2, len(recent_klines) - 2):
        if (recent_klines[i]['high'] > recent_klines[i-1]['high'] and 
            recent_klines[i]['high'] > recent_klines[i-2]['high'] and
            recent_klines[i]['high'] > recent_klines[i+1]['high'] and
            recent_klines[i]['high'] > recent_klines[i+2]['high']):
            if swing_high is None or recent_klines[i]['high'] > swing_high:
                swing_high = recent_klines[i]['high']
    
    return {
        'recent_low': recent_low,
        'recent_high': recent_high,
        'swing_low': swing_low,
        'swing_high': swing_high
    }

def calculate_three_tier_stop_loss(entry_price, signal_type, klines, fvgs, sr, key_levels, ema_144=None, ema_169=None, current_price=None):
    """
    三级止损系统（优化版）：
    1. 实时流动性止损（优先级最高）
    2. 技术位止损（Vegas通道、支撑阻力等，允许0.8%-3%）
    3. 默认止损（1.5%-3%，保守设置）
    
    返回: (stop_loss, source, info)
    - stop_loss: 止损价格
    - source: 止损来源（'liquidity', 'technical', 'default'）
    - info: 详细信息
    """
    # 第一优先级：实时流动性止损
    if current_price:
        order_book = get_order_book_gateio(limit=50)
        if not order_book:
            order_book = get_order_book_bitget(limit=50)
        
        if order_book:
            liquidity_analysis = analyze_liquidity_zones(order_book, current_price)
            if liquidity_analysis:
                liquidity_stop, liquidity_info = suggest_stop_loss_by_liquidity(
                    entry_price, signal_type, liquidity_analysis
                )
                if liquidity_stop and is_valid_stop_loss_distance(liquidity_stop, entry_price, signal_type):
                    return liquidity_stop, 'liquidity', liquidity_info
    
    # 第二优先级：技术位止损
    technical_stop, technical_info = calculate_technical_stop_loss(
        entry_price, signal_type, klines, fvgs, sr, key_levels, ema_144, ema_169
    )
    if technical_stop and is_valid_stop_loss_distance(technical_stop, entry_price, signal_type):
        return technical_stop, 'technical', technical_info
    
    # 第三优先级：默认止损
    default_stop = calculate_default_stop_loss(entry_price, signal_type)
    return default_stop, 'default', {'reason': '使用默认止损（保守设置）'}

def is_valid_stop_loss_distance(stop_loss, entry_price, signal_type):
    """验证止损距离是否合理（0.8%-3%）"""
    if signal_type == 'long':
        distance = entry_price - stop_loss
        distance_pct = distance / entry_price
        return 0.008 <= distance_pct <= 0.03
    else:
        distance = stop_loss - entry_price
        distance_pct = distance / entry_price
        return 0.008 <= distance_pct <= 0.03

def calculate_technical_stop_loss(entry_price, signal_type, klines, fvgs, sr, key_levels, ema_144=None, ema_169=None):
    """计算技术位止损（允许0.8%-3%）"""
    if signal_type == 'long':
        stop_candidates = []
        
        # 1. 最近的摆动低点下方
        if key_levels['swing_low'] and key_levels['swing_low'] < entry_price:
            stop_candidates.append(('swing_low', key_levels['swing_low'] * 0.995))
        
        # 2. 最近低点下方
        if key_levels['recent_low'] and key_levels['recent_low'] < entry_price:
            stop_candidates.append(('recent_low', key_levels['recent_low'] * 0.995))
        
        # 3. FVG下沿下方
        for fvg in fvgs:
            if fvg['type'] == 'bullish' and fvg['low'] < entry_price:
                stop_candidates.append(('fvg', fvg['low'] * 0.99))
        
        # 4. 支撑位下方
        if sr['support']:
            nearest_support = max([s for s in sr['support'] if s < entry_price], default=None)
            if nearest_support:
                stop_candidates.append(('support', nearest_support * 0.98))
        
        # 5. Vegas通道下方（如果价格在Vegas上方）
        if ema_144 and ema_169 and entry_price > ema_169:
            stop_candidates.append(('vegas', ema_144 * 0.995))
        
        if stop_candidates:
            valid_stops = [(name, price) for name, price in stop_candidates if price < entry_price]
            if valid_stops:
                best_name, best_stop = max(valid_stops, key=lambda x: x[1])  # 选择最高的止损
                
                # 对于技术位止损，允许0.8%-3%
                distance = entry_price - best_stop
                distance_pct = distance / entry_price
                
                # 检查是否是Vegas通道止损
                is_vegas = best_name == 'vegas'
                
                if is_vegas:
                    # Vegas通道止损：允许0.8%-3%
                    min_distance = entry_price * 0.008
                    max_distance = entry_price * 0.03
                else:
                    # 其他技术位止损：允许1.0%-3%
                    min_distance = entry_price * 0.01
                    max_distance = entry_price * 0.03
                
                if distance < min_distance:
                    best_stop = entry_price - min_distance
                elif distance > max_distance:
                    best_stop = entry_price - max_distance
                
                return best_stop, {'source': best_name, 'reason': f'基于{best_name}的技术位止损'}
        
        return None, None
    else:  # short
        stop_candidates = []
        
        # 1. 最近的摆动高点上方的
        if key_levels['swing_high'] and key_levels['swing_high'] > entry_price:
            stop_candidates.append(('swing_high', key_levels['swing_high'] * 1.005))
        
        # 2. 最近高点上方的
        if key_levels['recent_high'] and key_levels['recent_high'] > entry_price:
            stop_candidates.append(('recent_high', key_levels['recent_high'] * 1.005))
        
        # 3. FVG上沿上方
        for fvg in fvgs:
            if fvg['type'] == 'bearish' and fvg['high'] > entry_price:
                stop_candidates.append(('fvg', fvg['high'] * 1.01))
        
        # 4. 阻力位上方
        if sr['resistance']:
            nearest_resistance = min([r for r in sr['resistance'] if r > entry_price], default=None)
            if nearest_resistance:
                stop_candidates.append(('resistance', nearest_resistance * 1.02))
        
        # 5. Vegas通道上方（如果价格在Vegas下方）
        if ema_144 and ema_169 and entry_price < ema_144:
            stop_candidates.append(('vegas', ema_169 * 1.005))
        
        if stop_candidates:
            valid_stops = [(name, price) for name, price in stop_candidates if price > entry_price]
            if valid_stops:
                best_name, best_stop = min(valid_stops, key=lambda x: x[1])  # 选择最低的止损
                
                # 对于技术位止损，允许0.8%-3%
                distance = best_stop - entry_price
                distance_pct = distance / entry_price
                
                # 检查是否是Vegas通道止损
                is_vegas = best_name == 'vegas'
                
                if is_vegas:
                    # Vegas通道止损：允许0.8%-3%
                    min_distance = entry_price * 0.008
                    max_distance = entry_price * 0.03
                else:
                    # 其他技术位止损：允许1.0%-3%
                    min_distance = entry_price * 0.01
                    max_distance = entry_price * 0.03
                
                if distance < min_distance:
                    best_stop = entry_price + min_distance
                elif distance > max_distance:
                    best_stop = entry_price + max_distance
                
                return best_stop, {'source': best_name, 'reason': f'基于{best_name}的技术位止损'}
        
        return None, None

def calculate_default_stop_loss(entry_price, signal_type):
    """计算默认止损（保守设置：1.5%-3%）"""
    if signal_type == 'long':
        return entry_price * 0.985  # 1.5%
    else:
        return entry_price * 1.015  # 1.5%

def calculate_smart_stop_loss(entry_price, signal_type, klines, fvgs, sr, key_levels, ema_144=None, ema_169=None):
    """智能计算止损位置，基于关键位（2-3%或几百点）- 保持向后兼容"""
    # 使用新的三级止损系统
    stop_loss, source, info = calculate_three_tier_stop_loss(
        entry_price, signal_type, klines, fvgs, sr, key_levels, ema_144, ema_169
    )
    return stop_loss
    if signal_type == 'long':
        # 做多止损：放在关键位下方
        stop_candidates = []
        
        # 1. 最近的摆动低点下方
        if key_levels['swing_low'] and key_levels['swing_low'] < entry_price:
            stop_candidates.append(key_levels['swing_low'] * 0.995)  # 低点下方0.5%
        
        # 2. 最近低点下方
        if key_levels['recent_low'] and key_levels['recent_low'] < entry_price:
            stop_candidates.append(key_levels['recent_low'] * 0.995)
        
        # 3. FVG下沿下方
        for fvg in fvgs:
            if fvg['type'] == 'bullish' and fvg['low'] < entry_price:
                stop_candidates.append(fvg['low'] * 0.99)  # FVG下沿下方1%
        
        # 4. 支撑位下方
        if sr['support']:
            nearest_support = max([s for s in sr['support'] if s < entry_price], default=None)
            if nearest_support:
                stop_candidates.append(nearest_support * 0.98)  # 支撑下方2%
        
        # 5. Vegas通道下方（如果价格在Vegas上方）
        if ema_144 and ema_169 and entry_price > ema_169:
            stop_candidates.append(ema_144 * 0.995)  # Vegas下沿下方0.5%
        
        # 选择最合理的止损（不能太远，通常2-3%或几百点）
        if stop_candidates:
            # 选择最接近入场价但低于入场价的止损
            valid_stops = [s for s in stop_candidates if s < entry_price]
            if valid_stops:
                stop_loss = max(valid_stops)  # 选择最高的止损（最接近入场价）
                # 确保止损距离合理（至少1.5%，最多3%）
                min_stop_distance = entry_price * 0.015  # 至少1.5%，避免太紧
                max_stop_distance = entry_price * 0.03  # 最多3%，避免太远
                stop_distance = entry_price - stop_loss
                if stop_distance < min_stop_distance:
                    # 如果止损太紧，放宽到至少1.5%
                    stop_loss = entry_price - min_stop_distance
                elif stop_distance > max_stop_distance:
                    # 如果止损太远，收紧到最多3%
                    stop_loss = entry_price - max_stop_distance
                return stop_loss
        
        # 默认止损：入场价下方至少1.5%（避免太紧）
        return entry_price * 0.985
    
    else:  # short
        # 做空止损：放在关键位上方
        stop_candidates = []
        
        # 1. 最近的摆动高点上方的
        if key_levels['swing_high'] and key_levels['swing_high'] > entry_price:
            stop_candidates.append(key_levels['swing_high'] * 1.005)  # 高点上方的0.5%
        
        # 2. 最近高点上方的
        if key_levels['recent_high'] and key_levels['recent_high'] > entry_price:
            stop_candidates.append(key_levels['recent_high'] * 1.005)
        
        # 3. FVG上沿上方
        for fvg in fvgs:
            if fvg['type'] == 'bearish' and fvg['high'] > entry_price:
                stop_candidates.append(fvg['high'] * 1.01)  # FVG上沿上方1%
        
        # 4. 阻力位上方
        if sr['resistance']:
            nearest_resistance = min([r for r in sr['resistance'] if r > entry_price], default=None)
            if nearest_resistance:
                stop_candidates.append(nearest_resistance * 1.02)  # 阻力上方2%
        
        # 5. Vegas通道上方（如果价格在Vegas下方）
        if ema_144 and ema_169 and entry_price < ema_144:
            stop_candidates.append(ema_169 * 1.005)  # Vegas上沿上方0.5%
        
        # 选择最合理的止损
        if stop_candidates:
            # 选择最接近入场价但高于入场价的止损
            valid_stops = [s for s in stop_candidates if s > entry_price]
            if valid_stops:
                stop_loss = min(valid_stops)  # 选择最低的止损（最接近入场价）
                stop_distance = stop_loss - entry_price
                stop_distance_pct = (stop_distance / entry_price) * 100
                
                # 优化：对于技术位止损（如Vegas通道），允许更紧的止损
                # 检查是否是Vegas通道止损
                is_vegas_stop = False
                if ema_169:
                    vegas_stop = ema_169 * 1.005
                    if abs(stop_loss - vegas_stop) / vegas_stop < 0.01:  # 在1%误差内
                        is_vegas_stop = True
                
                # 如果止损距离合理（至少0.8%，最多3%）
                min_stop_distance = entry_price * 0.008  # 至少0.8%（对于技术位止损）
                min_stop_distance_strict = entry_price * 0.015  # 至少1.5%（对于非技术位止损）
                max_stop_distance = entry_price * 0.03  # 最多3%，避免太远
                
                if is_vegas_stop:
                    # Vegas通道止损：允许0.8%-3%
                    if stop_distance < min_stop_distance:
                        # 如果止损太紧（小于0.8%），放宽到0.8%
                        stop_loss = entry_price + min_stop_distance
                    elif stop_distance > max_stop_distance:
                        # 如果止损太远，收紧到最多3%
                        stop_loss = entry_price + max_stop_distance
                else:
                    # 非技术位止损：至少1.5%
                    if stop_distance < min_stop_distance_strict:
                        # 如果止损太紧，放宽到至少1.5%
                        stop_loss = entry_price + min_stop_distance_strict
                    elif stop_distance > max_stop_distance:
                        # 如果止损太远，收紧到最多3%
                        stop_loss = entry_price + max_stop_distance
                return stop_loss
        
        # 默认止损：入场价上方至少1.5%（避免太紧）
        return entry_price * 1.015

def validate_signal(signal, current_price):
    """验证信号的合理性"""
    if not signal:
        return False, "信号为空"
    
    entry = signal.get('entry', 0)
    stop_loss = signal.get('stop_loss', 0)
    take_profit_1 = signal.get('take_profit_1', 0)
    take_profit_2 = signal.get('take_profit_2', 0)
    signal_type = signal.get('type', '')
    
    # 1. 检查入场价与当前价格的关系
    if signal_type == 'long':
        # 做多：入场价应该低于当前价格（等待回调）
        if entry >= current_price * 1.01:  # 允许1%的误差
            return False, f"做多入场价{entry:.0f}不应高于或等于当前价格{current_price:.0f}"
        # 入场价不应该太低（低于当前价格超过5%）
        if entry < current_price * 0.95:
            return False, f"做多入场价{entry:.0f}太低，低于当前价格超过5%"
        # 止损应该在入场价下方
        if stop_loss >= entry:
            return False, f"做多止损{stop_loss:.0f}应该在入场价{entry:.0f}下方"
        # 止盈应该在入场价上方
        if take_profit_1 <= entry or take_profit_2 <= entry:
            return False, f"做多止盈应该在入场价{entry:.0f}上方"
        # 止盈应该递增
        if take_profit_1 >= take_profit_2:
            return False, f"做多第二止盈{take_profit_2:.0f}应该大于第一止盈{take_profit_1:.0f}"
    
    elif signal_type == 'short':
        # 做空：入场价应该高于当前价格（等待反弹）
        if entry <= current_price * 0.99:  # 允许1%的误差
            return False, f"做空入场价{entry:.0f}不应低于或等于当前价格{current_price:.0f}"
        # 入场价不应该太高（高于当前价格超过5%）
        if entry > current_price * 1.05:
            return False, f"做空入场价{entry:.0f}太高，高于当前价格超过5%"
        # 止损应该在入场价上方
        if stop_loss <= entry:
            return False, f"做空止损{stop_loss:.0f}应该在入场价{entry:.0f}上方"
        # 止盈应该在入场价下方
        if take_profit_1 >= entry or take_profit_2 >= entry:
            return False, f"做空止盈应该在入场价{entry:.0f}下方"
        # 止盈应该递减
        if take_profit_1 <= take_profit_2:
            return False, f"做空第二止盈{take_profit_2:.0f}应该小于第一止盈{take_profit_1:.0f}"
    
    # 2. 检查止损距离（至少1%，最多5%）
    if signal_type == 'long':
        stop_distance = (entry - stop_loss) / entry
        if stop_distance < 0.01:  # 至少1%
            return False, f"做多止损距离{stop_distance*100:.1f}%太小，至少1%"
        if stop_distance > 0.05:  # 最多5%
            return False, f"做多止损距离{stop_distance*100:.1f}%太大，最多5%"
    else:
        stop_distance = (stop_loss - entry) / entry
        if stop_distance < 0.01:  # 至少1%
            return False, f"做空止损距离{stop_distance*100:.1f}%太小，至少1%"
        if stop_distance > 0.05:  # 最多5%
            return False, f"做空止损距离{stop_distance*100:.1f}%太大，最多5%"
    
    # 3. 检查盈亏比（至少1:2）
    if signal_type == 'long':
        risk = entry - stop_loss
        reward_1 = take_profit_1 - entry
        reward_2 = take_profit_2 - entry
        if risk > 0:
            rr_1 = reward_1 / risk
            rr_2 = reward_2 / risk
            if rr_1 < 1.5:  # 至少1:1.5
                return False, f"做多第一止盈盈亏比{rr_1:.1f}太小，至少1:1.5"
            if rr_2 < 2.0:  # 至少1:2
                return False, f"做多第二止盈盈亏比{rr_2:.1f}太小，至少1:2"
    else:
        risk = stop_loss - entry
        reward_1 = entry - take_profit_1
        reward_2 = entry - take_profit_2
        if risk > 0:
            rr_1 = reward_1 / risk
            rr_2 = reward_2 / risk
            if rr_1 < 1.5:  # 至少1:1.5
                return False, f"做空第一止盈盈亏比{rr_1:.1f}太小，至少1:1.5"
            if rr_2 < 2.0:  # 至少1:2
                return False, f"做空第二止盈盈亏比{rr_2:.1f}太小，至少1:2"
    
    return True, "信号验证通过"

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
    
    # 找到最近的关键价位
    key_levels = find_recent_key_levels(klines, current_price)
    
    # 检查垃圾时间
    is_garbage, garbage_range = check_garbage_time(klines, current_price)
    
    # 检查Vegas突破
    is_breakthrough, is_support = check_vegas_breakthrough(klines, ema_144, ema_169, current_price)
    
    # 检查大阳K线
    is_big_bullish = check_big_bullish_candle(klines)
    
    # 裸K分析
    naked_kline = analyze_naked_kline(klines)
    
    # M顶/W底形态识别
    m_top = detect_m_top(klines, lookback=50)
    w_bottom = detect_w_bottom(klines, lookback=50)
    
    # 786斐波那契回撤位分析（OTE区间）
    ote_analysis = check_ote_zone(klines, current_price, lookback=50)
    
    # 分析信号
    signals = []
    
    # 1. FVG信号（优先级最高）
    for fvg in fvgs:
        if fvg['type'] == 'bullish' and current_price < fvg['high']:
            entry = fvg['low'] * 1.002  # FVG下沿上方0.2%，挂单等待
            # 使用三级止损系统
            stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'long', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )
            # 优化盈亏比：确保至少1:2.5，目标1:3或更高
            risk = entry - stop_loss
            if risk > 0:
                take_profit_1 = entry + risk * 2.5  # 1:2.5盈亏比
                take_profit_2 = entry + risk * 3.5  # 1:3.5盈亏比
            else:
                take_profit_1 = fvg['high'] * 1.01
                take_profit_2 = fvg['high'] * 1.02
            signal = {
                'type': 'long',
                'strength': 'strong',
                'entry': entry,
                'stop_loss': stop_loss,
                'stop_loss_source': stop_source,  # 止损来源
                'stop_loss_info': stop_info,  # 止损详细信息
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'reason': f'FVG做多机会，挂单在{entry:.0f}等待回填'
            }
            
            # 三层确认机制
            try:
                from signal_confirmation import confirm_signal_with_three_layers
                market_data_for_confirm = {
                    'current_price': current_price,
                    'ema_144': ema_144,
                    'ema_169': ema_169,
                    'vwap': vwap,
                    'rsi': rsi
                }
                signal = confirm_signal_with_three_layers(signal, market_data_for_confirm, klines, naked_kline)
            except ImportError:
                pass  # 如果确认模块不存在，跳过
            
            is_valid, error_msg = validate_signal(signal, current_price)
            if is_valid:
                signals.append(signal)
            else:
                print(f"FVG做多信号验证失败: {error_msg}", file=sys.stderr)
        elif fvg['type'] == 'bearish' and current_price > fvg['low']:
            # 使用三级止损系统
            stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'short', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )
            # 做空：在FVG上方做空，止损放在FVG上方
            # 看跌FVG：low是下沿（较低价格），high是上沿（较高价格）
            # 只有当价格在FVG上沿附近时，才考虑做空
            # 如果当前价格已经远高于FVG上沿（超过2%），说明价格已经大幅上涨，不应该做空
            price_distance_from_fvg_high = (current_price - fvg['high']) / fvg['high']
            
            if current_price > fvg['high'] and price_distance_from_fvg_high < 0.02:
                # 价格在FVG上沿上方，但距离不超过2%，等待回调到FVG上沿附近做空
                entry = fvg['high'] * 1.002  # FVG上沿上方0.2%，等待回调
            elif current_price <= fvg['high'] and current_price >= fvg['low']:
                # 价格在FVG内部，不应该做空（FVG正在被回填）
                continue
            else:
                # 价格已经远高于FVG上沿（超过2%），或者价格在FVG下方，不应该做空
                continue
            
            # 使用三级止损系统
            stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'short', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )
            # 优化盈亏比：确保至少1:2.5，目标1:3或更高
            risk = stop_loss - entry
            if risk > 0:
                take_profit_1 = entry - risk * 2.5  # 1:2.5盈亏比
                take_profit_2 = entry - risk * 3.5  # 1:3.5盈亏比
            else:
                take_profit_1 = fvg['low'] * 0.99
                take_profit_2 = fvg['low'] * 0.98
            signal = {
                'type': 'short',
                'strength': 'strong',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'reason': f'FVG做空机会，挂单在{entry:.0f}等待回填'
            }
            is_valid, error_msg = validate_signal(signal, current_price)
            if is_valid:
                signals.append(signal)
            else:
                print(f"FVG做空信号验证失败: {error_msg}", file=sys.stderr)
    
    # 2. 支撑阻力信号（改进：等待反弹确认后再入场）
    if sr['support']:
        nearest_support = max(sr['support'])
        # 检查价格是否从支撑位反弹（而不是在支撑位附近就入场）
        # 条件1：价格曾经接近或跌破支撑位
        # 条件2：价格现在在支撑位上方，且出现反弹迹象
        recent_lows = [k['low'] for k in klines[-10:]]
        recent_closes = [k['close'] for k in klines[-5:]]
        
        # 检查是否从支撑位反弹
        touched_support = min(recent_lows) <= nearest_support * 1.005
        price_above_support = current_price > nearest_support * 1.01  # 价格在支撑位上方1%以上
        is_bouncing = len(recent_closes) >= 2 and recent_closes[-1] > recent_closes[-2]  # 最近出现反弹
        
        # 只有在价格从支撑位反弹确认后才入场
        if touched_support and price_above_support and is_bouncing:
            # 入场价：挂单在支撑位上方（等待回调）
            # 优化：如果当前价格已经远离支撑位，入场价应该设置在更合理的位置
            # 1. 如果当前价格比支撑位高超过2%，考虑回调到支撑位上方1-1.5%
            # 2. 如果Vegas通道在支撑位上方，考虑回调到Vegas通道附近
            price_distance_from_support = (current_price - nearest_support) / nearest_support
            
            # 优先考虑回调到Vegas通道附近（如果Vegas在支撑位上方）
            if ema_169 and ema_169 > nearest_support * 1.01:
                # Vegas通道在支撑位上方，考虑回调到Vegas通道附近
                entry = ema_169 * 0.998  # Vegas通道下方0.2%，等待回调
            elif price_distance_from_support > 0.02:  # 当前价格比支撑位高超过2%
                # 价格已经反弹较多，入场价设置在支撑位上方1.5%，等待回调
                entry = nearest_support * 1.015  # 支撑位上方1.5%，更合理的回调位置
            else:
                # 价格刚反弹，入场价设置在支撑位上方1%
                entry = nearest_support * 1.01  # 支撑位上方1%，挂单等待
            # 使用三级止损系统
            stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'long', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )
            # 如果技术位止损太紧，至少放在支撑位下方3%
            if stop_source == 'technical' and stop_loss > nearest_support * 0.97:
                stop_loss = nearest_support * 0.97
                stop_info = {'source': 'support', 'reason': f'基于支撑位{nearest_support:.0f}的止损'}
            
            # 优化盈亏比：确保至少1:2，目标1:3或更高
            risk = entry - stop_loss
            if risk > 0:
                take_profit_1 = entry + risk * 2.5  # 1:2.5盈亏比
                take_profit_2 = entry + risk * 3.5  # 1:3.5盈亏比
                # 如果信号强度高，进一步提升盈亏比
                if is_big_bullish or (naked_kline.get('patterns')):
                    take_profit_1 = entry + risk * 3  # 1:3盈亏比
                    take_profit_2 = entry + risk * 4  # 1:4盈亏比
            else:
                take_profit_1 = entry * 1.025
                take_profit_2 = entry * 1.035
            
            signal = {
                'type': 'long',
                'strength': 'medium',
                'entry': entry,
                'stop_loss': stop_loss,
                'stop_loss_source': stop_source,  # 止损来源
                'stop_loss_info': stop_info,  # 止损详细信息
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'reason': f'价格从支撑位{nearest_support:.0f}反弹确认，挂单在{entry:.0f}等待回调'
            }
            
            # 三层确认机制
            try:
                from signal_confirmation import confirm_signal_with_three_layers
                market_data_for_confirm = {
                    'current_price': current_price,
                    'ema_144': ema_144,
                    'ema_169': ema_169,
                    'vwap': vwap,
                    'rsi': rsi
                }
                signal = confirm_signal_with_three_layers(signal, market_data_for_confirm, klines, naked_kline)
            except ImportError:
                pass  # 如果确认模块不存在，跳过
            
            is_valid, error_msg = validate_signal(signal, current_price)
            if is_valid:
                signals.append(signal)
            else:
                print(f"支撑位做多信号验证失败: {error_msg}", file=sys.stderr)
    
    if sr['resistance']:
        nearest_resistance = min(sr['resistance'])
        # 检查价格是否从阻力位回落（而不是在阻力位附近就入场）
        recent_highs = [k['high'] for k in klines[-10:]]
        recent_closes = [k['close'] for k in klines[-5:]]
        
        # 检查是否从阻力位回落
        touched_resistance = max(recent_highs) >= nearest_resistance * 0.995
        price_below_resistance = current_price < nearest_resistance * 0.99  # 价格在阻力位下方1%以下
        is_rejecting = len(recent_closes) >= 2 and recent_closes[-1] < recent_closes[-2]  # 最近出现回落
        
        # 只有在价格从阻力位回落确认后才入场
        if touched_resistance and price_below_resistance and is_rejecting:
            # 入场价：挂单在阻力位下方（等待反弹）
            entry = nearest_resistance * 0.995  # 阻力位下方0.5%，挂单等待
            # 使用三级止损系统
            stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'short', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )
            # 如果技术位止损太紧，至少放在阻力位上方3%
            if stop_source == 'technical' and stop_loss < nearest_resistance * 1.03:
                stop_loss = nearest_resistance * 1.03
                stop_info = {'source': 'resistance', 'reason': f'基于阻力位{nearest_resistance:.0f}的止损'}
            
            # 优化盈亏比：确保至少1:2，目标1:3或更高
            risk = stop_loss - entry
            if risk > 0:
                take_profit_1 = entry - risk * 2.5  # 1:2.5盈亏比
                take_profit_2 = entry - risk * 3.5  # 1:3.5盈亏比
                # 如果信号强度高，进一步提升盈亏比
                if naked_kline.get('patterns'):
                    take_profit_1 = entry - risk * 3  # 1:3盈亏比
                    take_profit_2 = entry - risk * 4  # 1:4盈亏比
            else:
                take_profit_1 = entry * 0.975
                take_profit_2 = entry * 0.965
            
            signal = {
                'type': 'short',
                'strength': 'medium',
                'entry': entry,
                'stop_loss': stop_loss,
                'stop_loss_source': stop_source,  # 止损来源
                'stop_loss_info': stop_info,  # 止损详细信息
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'reason': f'价格从阻力位{nearest_resistance:.0f}回落确认，挂单在{entry:.0f}等待反弹'
            }
            
            # 三层确认机制
            try:
                from signal_confirmation import confirm_signal_with_three_layers
                market_data_for_confirm = {
                    'current_price': current_price,
                    'ema_144': ema_144,
                    'ema_169': ema_169,
                    'vwap': vwap,
                    'rsi': rsi
                }
                signal = confirm_signal_with_three_layers(signal, market_data_for_confirm, klines, naked_kline)
            except ImportError:
                pass  # 如果确认模块不存在，跳过
            
            is_valid, error_msg = validate_signal(signal, current_price)
            if is_valid:
                signals.append(signal)
            else:
                print(f"阻力位做空信号验证失败: {error_msg}", file=sys.stderr)
    
    # 3. Vegas通道信号（包含突破后支撑转换）
    if ema_144 and ema_169:
        if current_price > ema_169:
            if is_breakthrough and is_support:
                # 突破后支撑转换：Vegas成为支撑
                entry = ema_169 * 1.002
                # 使用三级止损系统
                stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                    entry, 'long', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
                )
                # 优化盈亏比：确保至少1:2.5，目标1:3或更高
                risk = entry - stop_loss
                if risk > 0:
                    if is_big_bullish:
                        take_profit_1 = entry + risk * 3  # 1:3盈亏比（大阳K线）
                        take_profit_2 = entry + risk * 4  # 1:4盈亏比
                    else:
                        take_profit_1 = entry + risk * 2.5  # 1:2.5盈亏比
                        take_profit_2 = entry + risk * 3.5  # 1:3.5盈亏比
                else:
                    take_profit_1 = current_price * 1.025
                    take_profit_2 = current_price * 1.035
                
                signal = {
                    'type': 'long',
                    'strength': 'strong' if is_big_bullish else 'medium',
                    'entry': entry,
                    'stop_loss': stop_loss,
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'reason': f'价格突破Vegas通道后，Vegas成为支撑，回踩不破做多（{"大阳K线，不着急止盈" if is_big_bullish else ""}）'
                }
                is_valid, error_msg = validate_signal(signal, current_price)
                if is_valid:
                    signals.append(signal)
                else:
                    print(f"Vegas突破做多信号验证失败: {error_msg}", file=sys.stderr)
            elif current_price > ema_144 * 1.01:
                # 价格在Vegas上方，等待回调确认后再入场
                # 检查是否从Vegas反弹
                recent_lows = [k['low'] for k in klines[-5:]]
                recent_closes = [k['close'] for k in klines[-3:]]
                touched_vegas = min(recent_lows) <= ema_169 * 1.005
                is_bouncing = len(recent_closes) >= 2 and recent_closes[-1] > recent_closes[-2]
                
                # 只有在从Vegas反弹确认后才入场
                if touched_vegas and is_bouncing:
                    entry = current_price * 1.001  # 略高于当前价，等待确认
                    # 使用三级止损系统
                    stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                        entry, 'long', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
                    )
                    # 对于Vegas通道信号，优先使用Vegas通道下方的止损
                    if ema_144 and stop_source != 'liquidity':
                        vegas_stop = ema_144 * 0.995  # Vegas下方0.5%
                        if abs(stop_loss - vegas_stop) / vegas_stop > 0.01:  # 如果止损不是Vegas止损
                            stop_loss = vegas_stop
                            stop_source = 'technical'
                            stop_info = {'source': 'vegas', 'reason': f'基于Vegas通道{ema_144:.0f}的止损'}
                    # 优化盈亏比：确保至少1:2.5
                    risk = entry - stop_loss
                    if risk > 0:
                        take_profit_1 = entry + risk * 2.5  # 1:2.5盈亏比
                        take_profit_2 = entry + risk * 3.5  # 1:3.5盈亏比
                    else:
                        take_profit_1 = ema_169 * 1.02
                        take_profit_2 = current_price * 1.02
                    signal = {
                        'type': 'long',
                        'strength': 'medium',
                        'entry': entry,
                        'stop_loss': stop_loss,
                        'take_profit_1': take_profit_1,
                        'take_profit_2': take_profit_2,
                        'reason': f'价格在Vegas通道上方，从Vegas反弹确认，等待回调入场'
                    }
                    is_valid, error_msg = validate_signal(signal, current_price)
                    if is_valid:
                        signals.append(signal)
                    else:
                        print(f"Vegas反弹做多信号验证失败: {error_msg}", file=sys.stderr)
        elif current_price < ema_144:
            if is_breakthrough and not is_support:
                # 跌破后阻力转换：Vegas成为阻力
                entry = ema_144 * 0.998  # Vegas上方0.2%，挂单等待反弹
                # 使用三级止损系统
                stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                    entry, 'short', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
                )
                # 对于Vegas通道信号，优先使用Vegas通道上方的止损
                if ema_169 and stop_source != 'liquidity':
                    vegas_stop = ema_169 * 1.01  # Vegas上方1%
                    if abs(stop_loss - vegas_stop) / vegas_stop > 0.01:  # 如果止损不是Vegas止损
                        stop_loss = vegas_stop
                        stop_source = 'technical'
                        stop_info = {'source': 'vegas', 'reason': f'基于Vegas通道{ema_169:.0f}的止损'}
                # 优化盈亏比：确保至少1:2.5，目标1:3或更高
                risk = stop_loss - entry
                if risk > 0:
                    take_profit_1 = entry - risk * 2.5  # 1:2.5盈亏比
                    take_profit_2 = entry - risk * 3.5  # 1:3.5盈亏比
                else:
                    take_profit_1 = current_price - (ema_144 - current_price) * 0.5
                    take_profit_2 = current_price - (ema_144 - current_price) * 1.5
                signal = {
                    'type': 'short',
                    'strength': 'medium',
                    'entry': entry,
                    'stop_loss': stop_loss,
                    'take_profit_1': take_profit_1,
                    'take_profit_2': take_profit_2,
                    'reason': f'价格跌破Vegas通道后，Vegas成为阻力，挂单在{entry:.0f}等待反弹'
                }
                is_valid, error_msg = validate_signal(signal, current_price)
                if is_valid:
                    signals.append(signal)
                else:
                    print(f"Vegas跌破做空信号验证失败: {error_msg}", file=sys.stderr)
            elif current_price < ema_169 * 0.99:
                # 价格在Vegas下方，等待反弹确认后再入场
                # 检查是否从Vegas回落
                recent_highs = [k['high'] for k in klines[-5:]]
                recent_closes = [k['close'] for k in klines[-3:]]
                touched_vegas = max(recent_highs) >= ema_144 * 0.995
                is_rejecting = len(recent_closes) >= 2 and recent_closes[-1] < recent_closes[-2]
                
                # 只有在从Vegas回落确认后才入场
                if touched_vegas and is_rejecting:
                    entry = ema_144 * 0.997  # Vegas下方0.3%，挂单等待反弹
                    # 使用三级止损系统
                    stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                        entry, 'short', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
                    )
                    # 对于Vegas通道信号，优先使用Vegas通道上方的止损
                    if ema_169 and stop_source != 'liquidity':
                        vegas_stop = ema_169 * 1.01  # Vegas上方1%
                        if abs(stop_loss - vegas_stop) / vegas_stop > 0.01:  # 如果止损不是Vegas止损
                            stop_loss = vegas_stop
                            stop_source = 'technical'
                            stop_info = {'source': 'vegas', 'reason': f'基于Vegas通道{ema_169:.0f}的止损'}
                    # 优化盈亏比：确保至少1:2.5
                    risk = stop_loss - entry
                    if risk > 0:
                        take_profit_1 = entry - risk * 2.5  # 1:2.5盈亏比
                        take_profit_2 = entry - risk * 3.5  # 1:3.5盈亏比
                    else:
                        take_profit_1 = ema_144 * 0.98
                        take_profit_2 = current_price * 0.98
                    signal = {
                        'type': 'short',
                        'strength': 'medium',
                        'entry': entry,
                        'stop_loss': stop_loss,
                        'take_profit_1': take_profit_1,
                        'take_profit_2': take_profit_2,
                        'reason': f'价格在Vegas通道下方，从Vegas回落确认，等待反弹入场'
                    }
                    is_valid, error_msg = validate_signal(signal, current_price)
                    if is_valid:
                        signals.append(signal)
                    else:
                        print(f"Vegas回落做空信号验证失败: {error_msg}", file=sys.stderr)
    
    # 4. M顶/W底形态信号（De.规则：15分钟M顶很好看）
    if m_top and m_top['is_valid']:
        # M顶做空：回踩到M顶的腰线位置，实体K线收在腰线下方
        neckline = m_top['neckline']
        recent_closes = [k['close'] for k in klines[-5:]]
        # 检查价格是否在腰线附近，且最近收盘价在腰线下方
        if abs(current_price - neckline) / neckline < 0.01 and recent_closes[-1] < neckline:
            entry = neckline * 1.002  # 腰线上方0.2%，等待反弹
            # 使用三级止损系统
            stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'short', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )
            # 止损至少放在M顶高点上方
            if stop_loss < m_top['peak1'] * 1.01:
                stop_loss = m_top['peak1'] * 1.01
                stop_info = {'source': 'm_top', 'reason': f'基于M顶高点{m_top["peak1"]:.0f}的止损'}
            
            # 优化盈亏比
            risk = stop_loss - entry
            if risk > 0:
                take_profit_1 = entry - risk * 2.5  # 1:2.5盈亏比
                take_profit_2 = entry - risk * 3.5  # 1:3.5盈亏比
            else:
                take_profit_1 = m_top['middle_low'] * 0.99
                take_profit_2 = m_top['middle_low'] * 0.98
            
            signal = {
                'type': 'short',
                'strength': 'strong',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'reason': f'M顶形态确认，回踩到腰线{neckline:.0f}附近，等待反弹做空'
            }
            is_valid, error_msg = validate_signal(signal, current_price)
            if is_valid:
                signals.append(signal)
            else:
                print(f"M顶做空信号验证失败: {error_msg}", file=sys.stderr)
    
    if w_bottom and w_bottom['is_valid']:
        # W底做多：反弹到W底的腰线位置，实体K线收在腰线上方
        neckline = w_bottom['neckline']
        recent_closes = [k['close'] for k in klines[-5:]]
        # 检查价格是否在腰线附近，且最近收盘价在腰线上方
        if abs(current_price - neckline) / neckline < 0.01 and recent_closes[-1] > neckline:
            entry = neckline * 0.998  # 腰线下方0.2%，等待回调
            # 使用三级止损系统
            stop_loss, stop_source, stop_info = calculate_three_tier_stop_loss(
                entry, 'long', klines, fvgs, sr, key_levels, ema_144, ema_169, current_price
            )
            # 止损至少放在W底低点下方
            if stop_loss > w_bottom['bottom1'] * 0.99:
                stop_loss = w_bottom['bottom1'] * 0.99
                stop_info = {'source': 'w_bottom', 'reason': f'基于W底低点{w_bottom["bottom1"]:.0f}的止损'}
            
            # 优化盈亏比
            risk = entry - stop_loss
            if risk > 0:
                take_profit_1 = entry + risk * 2.5  # 1:2.5盈亏比
                take_profit_2 = entry + risk * 3.5  # 1:3.5盈亏比
            else:
                take_profit_1 = w_bottom['middle_high'] * 1.01
                take_profit_2 = w_bottom['middle_high'] * 1.02
            
            signal = {
                'type': 'long',
                'strength': 'strong',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'reason': f'W底形态确认，反弹到腰线{neckline:.0f}附近，等待回调做多'
            }
            is_valid, error_msg = validate_signal(signal, current_price)
            if is_valid:
                signals.append(signal)
            else:
                print(f"W底做多信号验证失败: {error_msg}", file=sys.stderr)
    
    # 5. 786斐波那契回撤位分析（De.规则：看空有w底，看反弹，后面也没突破786）
    if ote_analysis:
        # 如果W底反弹后没有突破786，可能是看空信号
        if w_bottom and w_bottom['is_valid'] and ote_analysis.get('below_618'):
            # W底反弹后没有突破786，可能是看空信号
            if current_price < ote_analysis['fib_786']:
                # 可以考虑做空，但需要其他确认信号（如M顶）
                if m_top and m_top['is_valid']:
                    # M顶 + W底反弹未破786 = 强烈看空信号
                    pass
    
    return {
        'timeframe': timeframe_name,
        'current_price': current_price,
        'ema_144': ema_144,
        'ema_169': ema_169,
        'vwap': vwap,
        'rsi': rsi,
        'fvgs': fvgs,
        'support_resistance': sr,
        'm_top': m_top,
        'w_bottom': w_bottom,
        'ote_analysis': ote_analysis,
        'key_levels': key_levels,
        'is_garbage_time': is_garbage,
        'garbage_range': garbage_range,
        'is_breakthrough': is_breakthrough,
        'is_support': is_support,
        'is_big_bullish': is_big_bullish,
        'naked_kline': naked_kline,
        'signals': signals
    }

def generate_detailed_explanation(signal, analysis):
    """生成详细的技术分析说明"""
    explanation = []
    explanation.append("")
    explanation.append("### 详细分析")
    explanation.append("")
    
    # 技术指标
    explanation.append("**技术指标**:")
    if analysis['ema_144'] and analysis['ema_169']:
        explanation.append(f"- Vegas通道: EMA144=${analysis['ema_144']:,.0f}, EMA169=${analysis['ema_169']:,.0f}")
        if signal['type'] == 'long':
            if analysis['current_price'] > analysis['ema_169']:
                explanation.append(f"  - 当前价格在Vegas通道上方，趋势偏多")
            elif analysis['current_price'] > analysis['ema_144']:
                explanation.append(f"  - 当前价格在Vegas通道内，接近上沿")
        else:
            if analysis['current_price'] < analysis['ema_144']:
                explanation.append(f"  - 当前价格在Vegas通道下方，趋势偏空")
            elif analysis['current_price'] < analysis['ema_169']:
                explanation.append(f"  - 当前价格在Vegas通道内，接近下沿")
    
    if analysis['vwap']:
        explanation.append(f"- VWAP: ${analysis['vwap']:,.0f}")
        if signal['type'] == 'long':
            if analysis['current_price'] > analysis['vwap']:
                explanation.append(f"  - 价格在VWAP上方，多头占优")
            else:
                explanation.append(f"  - 价格在VWAP下方，等待突破VWAP")
        else:
            if analysis['current_price'] < analysis['vwap']:
                explanation.append(f"  - 价格在VWAP下方，空头占优")
            else:
                explanation.append(f"  - 价格在VWAP上方，等待跌破VWAP")
    
    if analysis['rsi']:
        explanation.append(f"- RSI: {analysis['rsi']:.1f}")
        if analysis['rsi'] > 70:
            explanation.append(f"  - RSI超买，{signal['type'] == 'short' and '适合做空' or '做多需谨慎'}")
        elif analysis['rsi'] < 30:
            explanation.append(f"  - RSI超卖，{signal['type'] == 'long' and '适合做多' or '做空需谨慎'}")
        else:
            explanation.append(f"  - RSI中性区域")
    
    explanation.append("")
    
    # 关键价位
    explanation.append("**关键价位**:")
    if analysis['key_levels']['swing_low']:
        explanation.append(f"- 最近摆动低点: ${analysis['key_levels']['swing_low']:,.0f}")
    if analysis['key_levels']['swing_high']:
        explanation.append(f"- 最近摆动高点: ${analysis['key_levels']['swing_high']:,.0f}")
    if analysis['key_levels']['recent_low']:
        explanation.append(f"- 最近低点: ${analysis['key_levels']['recent_low']:,.0f}")
    if analysis['key_levels']['recent_high']:
        explanation.append(f"- 最近高点: ${analysis['key_levels']['recent_high']:,.0f}")
    
    if analysis['support_resistance']['support']:
        explanation.append(f"- 支撑位: {', '.join([f'${s:,.0f}' for s in analysis['support_resistance']['support'][:3]])}")
    if analysis['support_resistance']['resistance']:
        explanation.append(f"- 阻力位: {', '.join([f'${r:,.0f}' for r in analysis['support_resistance']['resistance'][:3]])}")
    
    if analysis['fvgs']:
        explanation.append(f"- FVG区间: {len(analysis['fvgs'])}个")
        for fvg in analysis['fvgs'][:2]:
            fvg_type = "看涨" if fvg['type'] == 'bullish' else "看跌"
            explanation.append(f"  - {fvg_type}FVG: ${fvg['low']:,.0f} - ${fvg['high']:,.0f}")
    
    explanation.append("")
    
    # 入场逻辑
    explanation.append("**入场逻辑**:")
    explanation.append(f"- {signal['reason']}")
    explanation.append("")
    explanation.append("**入场方式**：")
    explanation.append("- **模型+裸K**：使用价格行为模型、市场结构模型识别交易机会，结合裸K线分析确认入场时机")
    explanation.append("- **挂单入场**：所有入场价均为挂单价格，等待价格回调/反弹到挂单价位自动成交，不追涨杀跌")
    explanation.append("")
    explanation.append("**入场确认**：")
    if signal['type'] == 'long':
        explanation.append(f"- 参考入场价: ${signal['entry']:,.0f}（等待价格回调到此位置）")
        explanation.append("- 使用模型识别交易机会")
        explanation.append("- 使用裸K确认入场时机（观察K线形态、价格行为）")
        if analysis['is_breakthrough'] and analysis['is_support']:
            explanation.append(f"- Vegas突破后支撑转换：价格突破Vegas通道后，Vegas成为支撑，回踩不破做多")
        if analysis['is_big_bullish']:
            explanation.append(f"- 出现大阳K线：不着急止盈，挂保本止损，目标更大利润")
        if analysis.get('naked_kline'):
            naked = analysis['naked_kline']
            if naked.get('patterns'):
                explanation.append(f"- 裸K形态: {', '.join(naked['patterns'][:3])}")
    else:
        explanation.append(f"- 参考入场价: ${signal['entry']:,.0f}（等待价格反弹到此位置）")
        explanation.append("- 使用模型识别交易机会")
        explanation.append("- 使用裸K确认入场时机（观察K线形态、价格行为）")
        if analysis['is_breakthrough'] and not analysis['is_support']:
            explanation.append(f"- Vegas跌破后阻力转换：价格跌破Vegas通道后，Vegas成为阻力，反弹不破做空")
        if analysis.get('naked_kline'):
            naked = analysis['naked_kline']
            if naked.get('patterns'):
                explanation.append(f"- 裸K形态: {', '.join(naked['patterns'][:3])}")
    
    explanation.append("")
    
    # 止损设置（基于实时流动性）
    explanation.append("**止损设置（基于实时流动性）**:")
    
    # 获取实时订单簿
    liquidity_stop_loss = None
    liquidity_info = None
    order_book = get_order_book_gateio(limit=50)
    if not order_book:
        order_book = get_order_book_bitget(limit=50)
    
    if order_book:
        # 分析流动性
        liquidity_analysis = analyze_liquidity_zones(order_book, analysis['current_price'])
        
        if liquidity_analysis:
            # 根据流动性给出止损建议
            liquidity_stop_loss, liquidity_info = suggest_stop_loss_by_liquidity(
                signal['entry'], signal['type'], liquidity_analysis
            )
            
            if liquidity_stop_loss:
                explanation.append(f"- **基于实时流动性的止损**: ${liquidity_stop_loss:,.0f}")
                if liquidity_info:
                    explanation.append(f"- 止损距离: {liquidity_info['distance']:.0f}点（{liquidity_info['distance_pct']:.2f}%）")
                    explanation.append(f"- 止损理由: {liquidity_info['reason']}")
                    if signal['type'] == 'long' and liquidity_info.get('support_zone'):
                        explanation.append(f"- 买单密集区（支撑）: ${liquidity_info['support_zone']:,.0f}")
                    elif signal['type'] == 'short' and liquidity_info.get('resistance_zone'):
                        explanation.append(f"- 卖单密集区（阻力）: ${liquidity_info['resistance_zone']:,.0f}")
                explanation.append("")
                
                # 显示流动性区域信息
                explanation.append("**实时流动性分析**:")
                if signal['type'] == 'long':
                    if liquidity_analysis['dense_bid_zones']:
                        explanation.append(f"- 买单密集区（支撑位）: {', '.join([f'${z:,.0f}' for z in liquidity_analysis['dense_bid_zones'][:5]])}")
                    if liquidity_analysis['sparse_bid_zones']:
                        explanation.append(f"- 买单稀疏区（适合止损）: {', '.join([f'${z:,.0f}' for z in liquidity_analysis['sparse_bid_zones'][:5]])}")
                    # 显示不开单区域（De.规则）
                    if liquidity_analysis.get('no_trade_bid_zones'):
                        explanation.append("")
                        explanation.append("**不开单区域（De.规则：密集区上下20%+中间60%）**:")
                        for zone in liquidity_analysis['no_trade_bid_zones'][:3]:
                            explanation.append(f"- 密集区${zone['center']:,.0f}的不开单区域: ${zone['lower_bound']:,.0f} - ${zone['upper_bound']:,.0f}")
                else:
                    if liquidity_analysis['dense_ask_zones']:
                        explanation.append(f"- 卖单密集区（阻力位）: {', '.join([f'${z:,.0f}' for z in liquidity_analysis['dense_ask_zones'][:5]])}")
                    if liquidity_analysis['sparse_ask_zones']:
                        explanation.append(f"- 卖单稀疏区（适合止损）: {', '.join([f'${z:,.0f}' for z in liquidity_analysis['sparse_ask_zones'][:5]])}")
                    # 显示不开单区域（De.规则）
                    if liquidity_analysis.get('no_trade_ask_zones'):
                        explanation.append("")
                        explanation.append("**不开单区域（De.规则：密集区上下20%+中间60%）**:")
                        for zone in liquidity_analysis['no_trade_ask_zones'][:3]:
                            explanation.append(f"- 密集区${zone['center']:,.0f}的不开单区域: ${zone['lower_bound']:,.0f} - ${zone['upper_bound']:,.0f}")
                explanation.append("")
            else:
                explanation.append("- ⚠️ 无法根据流动性给出止损建议，请手动观察订单簿")
                explanation.append("")
        else:
            explanation.append("- ⚠️ 无法分析流动性，请手动观察订单簿")
            explanation.append("")
    else:
        explanation.append("- ⚠️ 无法获取实时订单簿，请手动观察订单簿")
        explanation.append("")
    
    # 技术指标参考止损
    stop_distance = abs(signal['entry'] - signal['stop_loss'])
    stop_pct = (stop_distance / signal['entry']) * 100
    explanation.append("**技术指标参考止损**（仅供参考）:")
    explanation.append(f"- 参考止损价: ${signal['stop_loss']:,.0f}")
    explanation.append(f"- 参考止损距离: {stop_distance:.0f}点（{stop_pct:.2f}%）")
    explanation.append("")
    explanation.append("**重要提醒**：")
    explanation.append("- 技术指标止损仅供参考，实际止损应基于实时订单簿")
    explanation.append("- **优先使用基于实时流动性的止损**")
    explanation.append("- 止损基于实时流动性，没有固定规则")
    explanation.append("- 止损是省钱，不要害怕止损")
    explanation.append("- 头寸接到就要设置止损（必须设置）")
    explanation.append("- 所有入场价均为挂单价格，等待价格到达挂单价位自动成交")
    explanation.append("")
    
    # 止盈设置
    explanation.append("**止盈设置**:")
    tp1_distance = abs(signal['take_profit_1'] - signal['entry'])
    tp2_distance = abs(signal['take_profit_2'] - signal['entry'])
    tp1_pct = (tp1_distance / signal['entry']) * 100
    tp2_pct = (tp2_distance / signal['entry']) * 100
    explanation.append(f"- 第一目标: ${signal['take_profit_1']:,.0f}（{tp1_distance:.0f}点，{tp1_pct:.2f}%，平仓50%）")
    explanation.append(f"- 第二目标: ${signal['take_profit_2']:,.0f}（{tp2_distance:.0f}点，{tp2_pct:.2f}%，平仓50%）")
    
    # 使用流动性止损或技术指标止损计算盈亏比（流动性止损已在上面获取）
    actual_stop_loss = liquidity_stop_loss if liquidity_stop_loss else signal['stop_loss']
    actual_stop_distance = abs(signal['entry'] - actual_stop_loss)
    
    if signal['type'] == 'long':
        risk_reward_1 = tp1_distance / actual_stop_distance if actual_stop_distance > 0 else 0
        risk_reward_2 = tp2_distance / actual_stop_distance if actual_stop_distance > 0 else 0
        explanation.append(f"- 风险回报比: 第一目标1:{risk_reward_1:.1f}, 第二目标1:{risk_reward_2:.1f}")
        if risk_reward_1 >= 2.5 and risk_reward_2 >= 3.5:
            explanation.append("  ✅ 盈亏比已优化，达到至少1:2.5的目标")
        if analysis['is_big_bullish']:
            explanation.append(f"- 大阳K线策略: 盈利400点后移动止损到入场价（保本），目标更大利润")
    else:
        risk_reward_1 = tp1_distance / actual_stop_distance if actual_stop_distance > 0 else 0
        risk_reward_2 = tp2_distance / actual_stop_distance if actual_stop_distance > 0 else 0
        explanation.append(f"- 风险回报比: 第一目标1:{risk_reward_1:.1f}, 第二目标1:{risk_reward_2:.1f}")
        if risk_reward_1 >= 2.5 and risk_reward_2 >= 3.5:
            explanation.append("  ✅ 盈亏比已优化，达到至少1:2.5的目标")
    
    explanation.append("")
    
    # 风险提示
    explanation.append("**风险提示**:")
    if analysis['is_garbage_time']:
        explanation.append(f"- ⚠️ 当前处于垃圾时间，价格在${analysis['garbage_range'][0]:,.0f}-${analysis['garbage_range'][1]:,.0f}区间震荡，建议等待突破")
    explanation.append(f"- 使用逐仓模式，每个头寸独立设置止损")
    explanation.append(f"- 如果止损，可以继续进头寸或反手")
    explanation.append(f"- 盈利400点后移动止损到入场价（保本）")
    explanation.append("")
    
    return "\n".join(explanation)

def generate_trading_plan():
    """生成交易计划"""
    print("正在获取BTC市场数据...", file=sys.stderr)
    
    # 获取数据
    current_price = get_btc_current_price()
    klines_5m = get_btc_kline_gateio('5m', 200)
    klines_15m = get_btc_kline_gateio('15m', 200)
    klines_1h = get_btc_kline_gateio('1h', 200)
    
    if not klines_5m:
        print("尝试从Bitget获取数据...", file=sys.stderr)
        klines_5m = get_btc_kline_bitget('5m', 200)
        klines_15m = get_btc_kline_bitget('15m', 200)
        klines_1h = get_btc_kline_bitget('1h', 200)
        if not current_price:
            current_price = get_btc_current_price()
    
    if not current_price or not klines_5m or not klines_15m or not klines_1h:
        print("无法获取市场数据", file=sys.stderr)
        return
    
    # 使用最新K线价格
    if abs(klines_1h[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_1h[-1]['close']
    
    # 分析各时间框架
    analysis_5m = analyze_timeframe(klines_5m, '5分钟', current_price)
    analysis_15m = analyze_timeframe(klines_15m, '15分钟', current_price)
    analysis_1h = analyze_timeframe(klines_1h, '1小时', current_price)
    
    # 生成交易计划（简化版，只显示信号）
    plan = []
    plan.append("# BTC 交易信号（De.交易系统）")
    plan.append("")
    plan.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    plan.append(f"**当前价格**: ${current_price:,.2f}  ")
    plan.append("")
    
    # 一、5分钟交易信号
    plan.append("## 5分钟")
    plan.append("")
    
    if analysis_5m:
        if analysis_5m['is_garbage_time']:
            plan.append("⚠️ **垃圾时间**: 建议等待突破")
            plan.append(f"   区间: ${analysis_5m['garbage_range'][0]:,.0f} - ${analysis_5m['garbage_range'][1]:,.0f}")
            plan.append("")
        
        if analysis_5m['signals']:
            # 分别显示做多和做空信号
            long_signals = [s for s in analysis_5m['signals'] if s['type'] == 'long']
            short_signals = [s for s in analysis_5m['signals'] if s['type'] == 'short']
            
            if long_signals:
                best_long = max(long_signals, key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
                strength = "强" if best_long['strength'] == 'strong' else "中" if best_long['strength'] == 'medium' else "弱"
                plan.append(f"**做多** ({strength})")
                # 获取实时流动性止损
                order_book = get_order_book_gateio(limit=50)
                if not order_book:
                    order_book = get_order_book_bitget(limit=50)
                liquidity_stop_loss = None
                if order_book:
                    liquidity_analysis = analyze_liquidity_zones(order_book, analysis_5m['current_price'])
                    if liquidity_analysis:
                        liquidity_stop_loss, _ = suggest_stop_loss_by_liquidity(best_long['entry'], 'long', liquidity_analysis)
                if liquidity_stop_loss:
                    plan.append(f"挂单入场: ${best_long['entry']:,.0f} | 止损: ${liquidity_stop_loss:,.0f}（基于实时流动性）")
                else:
                    plan.append(f"挂单入场: ${best_long['entry']:,.0f} | 止损: ${best_long['stop_loss']:,.0f}（技术指标参考，请观察订单簿）")
                plan.append(f"止盈: ${best_long['take_profit_1']:,.0f} (50%) / ${best_long['take_profit_2']:,.0f} (50%)")
                plan.append(f"理由: {best_long['reason']}")
                plan.append(generate_detailed_explanation(best_long, analysis_5m))
                plan.append("")
            
            if short_signals:
                best_short = max(short_signals, key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
                strength = "强" if best_short['strength'] == 'strong' else "中" if best_short['strength'] == 'medium' else "弱"
                plan.append(f"**做空** ({strength})")
                # 获取实时流动性止损
                order_book = get_order_book_gateio(limit=50)
                if not order_book:
                    order_book = get_order_book_bitget(limit=50)
                liquidity_stop_loss = None
                if order_book:
                    liquidity_analysis = analyze_liquidity_zones(order_book, analysis_5m['current_price'])
                    if liquidity_analysis:
                        liquidity_stop_loss, _ = suggest_stop_loss_by_liquidity(best_short['entry'], 'short', liquidity_analysis)
                if liquidity_stop_loss:
                    plan.append(f"挂单入场: ${best_short['entry']:,.0f} | 止损: ${liquidity_stop_loss:,.0f}（基于实时流动性）")
                else:
                    plan.append(f"挂单入场: ${best_short['entry']:,.0f} | 止损: ${best_short['stop_loss']:,.0f}（技术指标参考，请观察订单簿）")
                plan.append(f"止盈: ${best_short['take_profit_1']:,.0f} (50%) / ${best_short['take_profit_2']:,.0f} (50%)")
                plan.append(f"理由: {best_short['reason']}")
                plan.append(generate_detailed_explanation(best_short, analysis_5m))
                plan.append("")
            
            if not long_signals and not short_signals:
                plan.append("无明确信号，观望")
                plan.append("")
        else:
            plan.append("无明确信号，观望")
            plan.append("")
    
    # 二、15分钟交易信号
    plan.append("## 15分钟")
    plan.append("")
    
    if analysis_15m:
        if analysis_15m['is_garbage_time']:
            plan.append("⚠️ **垃圾时间**: 建议等待突破")
            plan.append(f"   区间: ${analysis_15m['garbage_range'][0]:,.0f} - ${analysis_15m['garbage_range'][1]:,.0f}")
            plan.append("")
        
        if analysis_15m['signals']:
            # 分别显示做多和做空信号
            long_signals = [s for s in analysis_15m['signals'] if s['type'] == 'long']
            short_signals = [s for s in analysis_15m['signals'] if s['type'] == 'short']
            
            if long_signals:
                best_long = max(long_signals, key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
                strength = "强" if best_long['strength'] == 'strong' else "中" if best_long['strength'] == 'medium' else "弱"
                plan.append(f"**做多** ({strength})")
                # 获取实时流动性止损
                order_book = get_order_book_gateio(limit=50)
                if not order_book:
                    order_book = get_order_book_bitget(limit=50)
                liquidity_stop_loss = None
                if order_book:
                    liquidity_analysis = analyze_liquidity_zones(order_book, analysis_5m['current_price'])
                    if liquidity_analysis:
                        liquidity_stop_loss, _ = suggest_stop_loss_by_liquidity(best_long['entry'], 'long', liquidity_analysis)
                if liquidity_stop_loss:
                    plan.append(f"挂单入场: ${best_long['entry']:,.0f} | 止损: ${liquidity_stop_loss:,.0f}（基于实时流动性）")
                else:
                    plan.append(f"挂单入场: ${best_long['entry']:,.0f} | 止损: ${best_long['stop_loss']:,.0f}（技术指标参考，请观察订单簿）")
                plan.append(f"止盈: ${best_long['take_profit_1']:,.0f} (50%) / ${best_long['take_profit_2']:,.0f} (50%)")
                plan.append(f"理由: {best_long['reason']}")
                plan.append(generate_detailed_explanation(best_long, analysis_15m))
                plan.append("")
            
            if short_signals:
                best_short = max(short_signals, key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
                strength = "强" if best_short['strength'] == 'strong' else "中" if best_short['strength'] == 'medium' else "弱"
                plan.append(f"**做空** ({strength})")
                # 获取实时流动性止损
                order_book = get_order_book_gateio(limit=50)
                if not order_book:
                    order_book = get_order_book_bitget(limit=50)
                liquidity_stop_loss = None
                if order_book:
                    liquidity_analysis = analyze_liquidity_zones(order_book, analysis_5m['current_price'])
                    if liquidity_analysis:
                        liquidity_stop_loss, _ = suggest_stop_loss_by_liquidity(best_short['entry'], 'short', liquidity_analysis)
                if liquidity_stop_loss:
                    plan.append(f"挂单入场: ${best_short['entry']:,.0f} | 止损: ${liquidity_stop_loss:,.0f}（基于实时流动性）")
                else:
                    plan.append(f"挂单入场: ${best_short['entry']:,.0f} | 止损: ${best_short['stop_loss']:,.0f}（技术指标参考，请观察订单簿）")
                plan.append(f"止盈: ${best_short['take_profit_1']:,.0f} (50%) / ${best_short['take_profit_2']:,.0f} (50%)")
                plan.append(f"理由: {best_short['reason']}")
                plan.append(generate_detailed_explanation(best_short, analysis_15m))
                plan.append("")
            
            if not long_signals and not short_signals:
                plan.append("无明确信号，观望")
                plan.append("")
        else:
            plan.append("无明确信号，观望")
            plan.append("")
    
    # 三、1小时交易信号
    plan.append("## 1小时")
    plan.append("")
    
    if analysis_1h:
        if analysis_1h['is_garbage_time']:
            plan.append("⚠️ **垃圾时间**: 建议等待突破")
            plan.append(f"   区间: ${analysis_1h['garbage_range'][0]:,.0f} - ${analysis_1h['garbage_range'][1]:,.0f}")
            plan.append("")
        
        if analysis_1h['signals']:
            # 分别显示做多和做空信号
            long_signals = [s for s in analysis_1h['signals'] if s['type'] == 'long']
            short_signals = [s for s in analysis_1h['signals'] if s['type'] == 'short']
            
            if long_signals:
                best_long = max(long_signals, key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
                strength = "强" if best_long['strength'] == 'strong' else "中" if best_long['strength'] == 'medium' else "弱"
                
                # 检查5/15分钟是否同频
                tf_5m_long = analysis_5m and analysis_5m['signals'] and any(s['type'] == 'long' for s in analysis_5m['signals'])
                tf_15m_long = analysis_15m and analysis_15m['signals'] and any(s['type'] == 'long' for s in analysis_15m['signals'])
                is_resonance = tf_5m_long and tf_15m_long
                
                plan.append(f"**做多** ({strength})")
                if is_resonance:
                    plan.append("   ✅ **多时间框架共振**: 1小时+5分钟+15分钟同频，信号最稳，可以吃最稳的那一段")
                else:
                    plan.append("   ⚠️ **5/15分钟不同频**: 等待5/15分钟同频后再入场")
                # 获取实时流动性止损
                order_book = get_order_book_gateio(limit=50)
                if not order_book:
                    order_book = get_order_book_bitget(limit=50)
                liquidity_stop_loss = None
                if order_book:
                    liquidity_analysis = analyze_liquidity_zones(order_book, analysis_5m['current_price'])
                    if liquidity_analysis:
                        liquidity_stop_loss, _ = suggest_stop_loss_by_liquidity(best_long['entry'], 'long', liquidity_analysis)
                if liquidity_stop_loss:
                    plan.append(f"挂单入场: ${best_long['entry']:,.0f} | 止损: ${liquidity_stop_loss:,.0f}（基于实时流动性）")
                else:
                    plan.append(f"挂单入场: ${best_long['entry']:,.0f} | 止损: ${best_long['stop_loss']:,.0f}（技术指标参考，请观察订单簿）")
                plan.append(f"止盈: ${best_long['take_profit_1']:,.0f} (50%) / ${best_long['take_profit_2']:,.0f} (50%)")
                plan.append(f"理由: {best_long['reason']}")
                plan.append(generate_detailed_explanation(best_long, analysis_1h))
                plan.append("")
            
            if short_signals:
                best_short = max(short_signals, key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
                strength = "强" if best_short['strength'] == 'strong' else "中" if best_short['strength'] == 'medium' else "弱"
                
                # 检查5/15分钟是否同频
                tf_5m_short = analysis_5m and analysis_5m['signals'] and any(s['type'] == 'short' for s in analysis_5m['signals'])
                tf_15m_short = analysis_15m and analysis_15m['signals'] and any(s['type'] == 'short' for s in analysis_15m['signals'])
                is_resonance = tf_5m_short and tf_15m_short
                
                plan.append(f"**做空** ({strength})")
                if is_resonance:
                    plan.append("   ✅ **多时间框架共振**: 1小时+5分钟+15分钟同频，信号最稳，可以吃最稳的那一段")
                else:
                    plan.append("   ⚠️ **5/15分钟不同频**: 等待5/15分钟同频后再入场")
                # 获取实时流动性止损
                order_book = get_order_book_gateio(limit=50)
                if not order_book:
                    order_book = get_order_book_bitget(limit=50)
                liquidity_stop_loss = None
                if order_book:
                    liquidity_analysis = analyze_liquidity_zones(order_book, analysis_5m['current_price'])
                    if liquidity_analysis:
                        liquidity_stop_loss, _ = suggest_stop_loss_by_liquidity(best_short['entry'], 'short', liquidity_analysis)
                if liquidity_stop_loss:
                    plan.append(f"挂单入场: ${best_short['entry']:,.0f} | 止损: ${liquidity_stop_loss:,.0f}（基于实时流动性）")
                else:
                    plan.append(f"挂单入场: ${best_short['entry']:,.0f} | 止损: ${best_short['stop_loss']:,.0f}（技术指标参考，请观察订单簿）")
                plan.append(f"止盈: ${best_short['take_profit_1']:,.0f} (50%) / ${best_short['take_profit_2']:,.0f} (50%)")
                plan.append(f"理由: {best_short['reason']}")
                plan.append(generate_detailed_explanation(best_short, analysis_1h))
                plan.append("")
            
            if not long_signals and not short_signals:
                plan.append("无明确信号，观望")
                plan.append("")
        else:
            plan.append("无明确信号，观望")
            plan.append("")
    
    # 结束，不显示详细分析
    plan.append("")
    plan.append("---")
    plan.append("")
    plan.append("*基于De.交易系统自动生成*")
    
    # 输出计划
    output = "\n".join(plan)
    try:
        print(output)
    except UnicodeEncodeError:
        pass
    
    # 保存到文件
    filename = f"BTC_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"[OK] 交易信号已生成并保存", file=sys.stderr)
    print(f"[文件] 文件名: {filename}", file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)
    return
    
    # 以下代码不再执行（保留以防需要）
    if False:
        # 5分钟详细分析
        if analysis_5m:
            plan.append("#### 5分钟级别")
        plan.append("")
        plan.append(f"**当前价格**: ${analysis_5m['current_price']:,.2f}")
        plan.append("")
        if analysis_5m['ema_144'] and analysis_5m['ema_169']:
            plan.append(f"**Vegas通道**:")
            plan.append(f"  - EMA144: ${analysis_5m['ema_144']:,.2f}")
            plan.append(f"  - EMA169: ${analysis_5m['ema_169']:,.2f}")
            if analysis_5m['is_breakthrough'] and analysis_5m['is_support']:
                plan.append("  → 价格突破Vegas通道，Vegas成为支撑")
            elif current_price > analysis_5m['ema_169']:
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
        if analysis_5m['is_big_bullish']:
            plan.append("**大阳K线**: ✅ 已确认，不着急止盈")
            plan.append("")
    
    # 15分钟详细分析
    if analysis_15m:
        plan.append("#### 15分钟级别")
        plan.append("")
        plan.append(f"**当前价格**: ${analysis_15m['current_price']:,.2f}")
        plan.append("")
        if analysis_15m['ema_144'] and analysis_15m['ema_169']:
            plan.append(f"**Vegas通道**:")
            plan.append(f"  - EMA144: ${analysis_15m['ema_144']:,.2f}")
            plan.append(f"  - EMA169: ${analysis_15m['ema_169']:,.2f}")
            if analysis_15m['is_breakthrough'] and analysis_15m['is_support']:
                plan.append("  → 价格突破Vegas通道，Vegas成为支撑")
            elif current_price > analysis_15m['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif current_price < analysis_15m['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
            plan.append("")
        if analysis_15m['vwap']:
            plan.append(f"**VWAP**: ${analysis_15m['vwap']:,.2f}")
            plan.append("")
        if analysis_15m['rsi']:
            plan.append(f"**RSI**: {analysis_15m['rsi']:.1f}")
            plan.append("")
    
    # 1小时详细分析
    if analysis_1h:
        plan.append("#### 1小时级别")
        plan.append("")
        plan.append(f"**当前价格**: ${analysis_1h['current_price']:,.2f}")
        plan.append("")
        if analysis_1h['ema_144'] and analysis_1h['ema_169']:
            plan.append(f"**Vegas通道**:")
            plan.append(f"  - EMA144: ${analysis_1h['ema_144']:,.2f}")
            plan.append(f"  - EMA169: ${analysis_1h['ema_169']:,.2f}")
            if analysis_1h['is_breakthrough'] and analysis_1h['is_support']:
                plan.append("  → 价格突破Vegas通道，Vegas成为支撑")
            elif current_price > analysis_1h['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif current_price < analysis_1h['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
            plan.append("")
        if analysis_1h['vwap']:
            plan.append(f"**VWAP**: ${analysis_1h['vwap']:,.2f}")
            plan.append("")
        if analysis_1h['rsi']:
            plan.append(f"**RSI**: {analysis_1h['rsi']:.1f}")
            plan.append("")
    
    plan.append("### 4.3 De.交易系统核心规则")
    plan.append("")
    plan.append("**止损设置**:")
    plan.append("- ✅ 头寸接到就要设置止损（必须设置）")
    plan.append("- ✅ 一比归一比（每个头寸独立设置止损）")
    plan.append("- ✅ 止损是省钱，不要害怕止损")
    plan.append("- ✅ 止损要合理，不能太远（如876就该走了）")
    plan.append("")
    plan.append("**头寸管理**:")
    plan.append("- ✅ 每一单都是逐仓（isolated margin）")
    plan.append("- ✅ 止损后可以继续进头寸或反手")
    plan.append("- ✅ 加仓在盈利后（反转信号加仓）")
    plan.append("- ✅ 区间分批建仓（如FVG区间858-866分三次进）")
    plan.append("")
    plan.append("**盈利管理**:")
    plan.append("- ✅ 盈利400点后移动止损到入场价（保本）")
    plan.append("- ✅ 即使止损也吃了400点（因为已经保本）")
    plan.append("- ✅ 用400点去博弈1200点（在盈利基础上博弈）")
    plan.append("- ✅ 大阳K线不着急止盈，可以持有更久")
    plan.append("")
    plan.append("**Vegas突破**:")
    plan.append("- ✅ 价格突破Vegas通道后，Vegas成为支撑/阻力")
    plan.append("- ✅ 回补Vegas不破，继续做多/做空")
    plan.append("")
    
    # 五、交易执行检查清单
    plan.append("## 五、交易执行检查清单")
    plan.append("")
    plan.append("**入场前**:")
    plan.append("□ 是否在垃圾时间内？（如果是，等待突破）")
    plan.append("□ 是否有FVG机会？")
    plan.append("□ 是否突破Vegas通道？（突破后Vegas成为支撑/阻力）")
    plan.append("□ 多时间框架Vegas是否确认？（5分钟、15分钟、1小时）")
    plan.append("□ 是否有明确的支撑/阻力位？")
    plan.append("□ RSI是否在合理区域？")
    plan.append("")
    plan.append("**头寸管理**:")
    plan.append("□ 是否设置为逐仓模式？（必须逐仓）")
    plan.append("□ 是否立即设置了止损？（头寸接到就要设置）")
    plan.append("□ 止损是否合理？（不能太远，如876就该走了）")
    plan.append("□ 是否一比归一比？（每个头寸独立设置止损）")
    plan.append("")
    plan.append("**风险管理**:")
    plan.append("□ 已设置止损（窄止损2-3%，止损是省钱）")
    plan.append("□ 已设置分批止盈（50%+50%）")
    plan.append("□ 仓位大小已计算（风险2-3%）")
    plan.append("□ 盈亏比≥2:1")
    plan.append("□ 盈利400点后是否移动止损到保本？")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    plan.append("**免责声明**: 本交易计划基于De.交易系统自动生成，仅供参考。交易有风险，入市需谨慎。")
    
    # 输出计划
    output = "\n".join(plan)
    try:
        print(output)
    except UnicodeEncodeError:
        pass
    
    # 保存到文件
    filename = f"BTC_multi_tf_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n交易计划已保存到: {filename}", file=sys.stderr)

def query_btc_1h_naked_kline():
    """查询BTC 1小时实时价格和裸K分析"""
    print("正在获取BTC 1小时实时数据...", file=sys.stderr)
    
    # 获取数据
    current_price = get_btc_current_price()
    klines_1h = get_btc_kline_gateio('1h', 50)
    
    if not klines_1h:
        print("尝试从Bitget获取数据...", file=sys.stderr)
        klines_1h = get_btc_kline_bitget('1h', 50)
        if not current_price:
            current_price = get_btc_current_price()
    
    if not current_price or not klines_1h:
        print("无法获取市场数据", file=sys.stderr)
        return
    
    # 使用最新K线价格
    if abs(klines_1h[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_1h[-1]['close']
    
    # 裸K分析
    naked_kline = analyze_naked_kline(klines_1h)
    
    # 分析1小时时间框架
    analysis_1h = analyze_timeframe(klines_1h, '1小时', current_price)
    
    # 生成报告
    report = []
    report.append("# BTC 1小时裸K分析")
    report.append("")
    report.append(f"**查询时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**当前价格**: ${current_price:,.2f}")
    report.append("")
    
    # 裸K分析结果
    report.append("## 裸K分析结果")
    report.append("")
    
    if naked_kline['signal'] == 'bullish':
        report.append("✅ **看涨信号**")
        report.append(f"- 信号强度: {naked_kline['strength']}/10")
        report.append(f"- 看涨得分: {naked_kline['details']['bullish_score']}")
        report.append(f"- 看跌得分: {naked_kline['details']['bearish_score']}")
    elif naked_kline['signal'] == 'bearish':
        report.append("❌ **看跌信号**")
        report.append(f"- 信号强度: {naked_kline['strength']}/10")
        report.append(f"- 看涨得分: {naked_kline['details']['bullish_score']}")
        report.append(f"- 看跌得分: {naked_kline['details']['bearish_score']}")
    else:
        report.append("⚪ **中性信号**")
        report.append(f"- 看涨得分: {naked_kline['details']['bullish_score']}")
        report.append(f"- 看跌得分: {naked_kline['details']['bearish_score']}")
    
    report.append("")
    
    # 识别的K线形态
    if naked_kline['patterns']:
        report.append("**识别的K线形态**:")
        for pattern in naked_kline['patterns']:
            report.append(f"- {pattern}")
    else:
        report.append("**识别的K线形态**: 无明显形态")
    
    report.append("")
    
    # 最新K线详情
    if naked_kline['details'].get('last_candle'):
        last_candle = naked_kline['details']['last_candle']
        report.append("**最新K线详情**:")
        report.append(f"- 实体占比: {last_candle['body_ratio']*100:.1f}%")
        report.append(f"- 上影线占比: {last_candle['upper_shadow_ratio']*100:.1f}%")
        report.append(f"- 下影线占比: {last_candle['lower_shadow_ratio']*100:.1f}%")
        report.append(f"- 是否阳线: {'是' if last_candle['is_bullish'] else '否'}")
        report.append("")
    
    # 技术指标
    if analysis_1h:
        report.append("## 技术指标")
        report.append("")
        if analysis_1h['ema_144'] and analysis_1h['ema_169']:
            report.append(f"**Vegas通道**:")
            report.append(f"- EMA144: ${analysis_1h['ema_144']:,.2f}")
            report.append(f"- EMA169: ${analysis_1h['ema_169']:,.2f}")
            if current_price > analysis_1h['ema_169']:
                report.append(f"- 当前价格在Vegas通道上方，趋势偏多")
            elif current_price < analysis_1h['ema_144']:
                report.append(f"- 当前价格在Vegas通道下方，趋势偏空")
            else:
                report.append(f"- 当前价格在Vegas通道内")
            report.append("")
        
        if analysis_1h['vwap']:
            report.append(f"**VWAP**: ${analysis_1h['vwap']:,.2f}")
            if current_price > analysis_1h['vwap']:
                report.append(f"- 价格在VWAP上方，多头占优")
            else:
                report.append(f"- 价格在VWAP下方，空头占优")
            report.append("")
        
        if analysis_1h['rsi']:
            report.append(f"**RSI**: {analysis_1h['rsi']:.1f}")
            if analysis_1h['rsi'] > 70:
                report.append(f"- RSI超买，可能回调")
            elif analysis_1h['rsi'] < 30:
                report.append(f"- RSI超卖，可能反弹")
            else:
                report.append(f"- RSI中性区域")
            report.append("")
    
    # 交易建议
    report.append("## 交易建议")
    report.append("")
    if naked_kline['signal'] == 'bullish' and naked_kline['strength'] >= 5:
        report.append("✅ **强烈看涨**: 建议关注做多机会")
        if analysis_1h and analysis_1h['signals']:
            long_signals = [s for s in analysis_1h['signals'] if s['type'] == 'long']
            if long_signals:
                best_long = max(long_signals, key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
                report.append(f"- 建议入场: ${best_long['entry']:,.0f}")
                report.append(f"- 建议止损: ${best_long['stop_loss']:,.0f}")
                report.append(f"- 建议止盈: ${best_long['take_profit_1']:,.0f} / ${best_long['take_profit_2']:,.0f}")
    elif naked_kline['signal'] == 'bullish':
        report.append("⚠️ **温和看涨**: 可关注做多机会，但需等待确认")
    elif naked_kline['signal'] == 'bearish' and naked_kline['strength'] >= 5:
        report.append("❌ **强烈看跌**: 建议关注做空机会")
    elif naked_kline['signal'] == 'bearish':
        report.append("⚠️ **温和看跌**: 可关注做空机会，但需等待确认")
    else:
        report.append("⚪ **中性**: 建议观望，等待明确信号")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("*基于De.交易系统裸K分析*")
    
    # 输出报告
    output = "\n".join(report)
    try:
        print(output)
    except UnicodeEncodeError:
        pass
    
    # 保存到文件
    filename = f"BTC_1h_naked_kline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(output)
        print(f"\n报告已保存到: {filename}", file=sys.stderr)
    except Exception as e:
        print(f"保存文件失败: {e}", file=sys.stderr)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '1h_naked':
        query_btc_1h_naked_kline()
    else:
        generate_trading_plan()


