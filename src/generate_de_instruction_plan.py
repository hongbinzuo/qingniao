#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据De.交易指令生成详细交易计划
指令：明天低多，多在863下面损一次，85附近再多一次，新低止损
"""

import requests
import sys
from datetime import datetime

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
    
    # 备用：Bitget
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

def get_btc_kline_gateio(timeframe='1h', limit=200):
    """从Gate.io获取BTC K线数据"""
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h', '1d': '1d'}
        interval = tf_map.get(timeframe, '1h')
        
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

def get_order_book_gateio(limit=50):
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
            if data and data.get('bids') and data.get('asks'):
                bids = [(float(b[0]), float(b[1])) for b in data.get('bids', [])]
                asks = [(float(a[0]), float(a[1])) for a in data.get('asks', [])]
                if bids and asks:
                    return {
                        'bids': bids,
                        'asks': asks,
                        'timestamp': data.get('t', 0)
                    }
    except Exception as e:
        pass  # 静默失败，尝试下一个
    return None

def get_order_book_bitget(limit=50):
    """从Bitget获取BTC订单簿数据"""
    try:
        url = "https://api.bitget.com/api/spot/v1/market/depth"
        params = {
            'symbol': 'BTCUSDT',
            'limit': limit,
            'type': 'step0'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                order_data = data['data']
                bids = [(float(b[0]), float(b[1])) for b in order_data.get('bids', [])]
                asks = [(float(a[0]), float(a[1])) for a in order_data.get('asks', [])]
                if bids and asks:
                    return {
                        'bids': bids,
                        'asks': asks,
                        'timestamp': order_data.get('ts', 0)
                    }
    except Exception as e:
        pass
    return None

def get_order_book_binance(limit=50):
    """从Binance获取BTC订单簿数据（最可靠的备用方案）"""
    try:
        url = "https://api.binance.com/api/v3/depth"
        params = {
            'symbol': 'BTCUSDT',
            'limit': min(limit, 100)  # Binance最大支持100
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('bids') and data.get('asks'):
                bids = [(float(b[0]), float(b[1])) for b in data.get('bids', [])]
                asks = [(float(a[0]), float(a[1])) for a in data.get('asks', [])]
                if bids and asks:
                    return {
                        'bids': bids,
                        'asks': asks,
                        'timestamp': data.get('lastUpdateId', 0)
                    }
    except Exception as e:
        pass
    return None

def get_order_book_bybit(limit=50):
    """从Bybit获取BTC订单簿数据"""
    try:
        url = "https://api.bybit.com/v5/market/orderbook"
        params = {
            'category': 'spot',
            'symbol': 'BTCUSDT',
            'limit': min(limit, 200)  # Bybit最大支持200
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0 and data.get('result'):
                result = data['result']
                bids = [(float(b[0]), float(b[1])) for b in result.get('b', [])]
                asks = [(float(a[0]), float(a[1])) for a in result.get('a', [])]
                if bids and asks:
                    return {
                        'bids': bids,
                        'asks': asks,
                        'timestamp': result.get('ts', 0)
                    }
    except Exception as e:
        pass
    return None

def get_order_book_okx(limit=50):
    """从OKX获取BTC订单簿数据"""
    try:
        url = "https://www.okx.com/api/v5/market/books"
        params = {
            'instId': 'BTC-USDT',
            'sz': min(limit, 400)  # OKX最大支持400
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0' and data.get('data'):
                order_data = data['data'][0]
                bids = [(float(b[0]), float(b[1])) for b in order_data.get('bids', [])]
                asks = [(float(a[0]), float(a[1])) for a in order_data.get('asks', [])]
                if bids and asks:
                    return {
                        'bids': bids,
                        'asks': asks,
                        'timestamp': int(order_data.get('ts', 0))
                    }
    except Exception as e:
        pass
    return None

def get_order_book_with_retry(limit=50, max_retries=2):
    """获取订单簿，带重试机制，尝试多个交易所"""
    exchanges = [
        ('Binance', get_order_book_binance),
        ('Bybit', get_order_book_bybit),
        ('OKX', get_order_book_okx),
        ('Gate.io', get_order_book_gateio),
        ('Bitget', get_order_book_bitget),
    ]
    
    for exchange_name, get_func in exchanges:
        for attempt in range(max_retries):
            try:
                result = get_func(limit)
                if result and result.get('bids') and result.get('asks'):
                    if len(result['bids']) > 0 and len(result['asks']) > 0:
                        print(f"成功从{exchange_name}获取订单簿数据", file=sys.stderr)
                        return result
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"{exchange_name}获取失败（已重试{max_retries}次）", file=sys.stderr)
                else:
                    import time
                    time.sleep(0.5)  # 短暂等待后重试
                continue
    
    print("所有交易所订单簿获取均失败", file=sys.stderr)
    return None

def analyze_liquidity_zones(order_book, current_price):
    """分析订单簿，识别流动性区域"""
    if not order_book or 'bids' not in order_book or 'asks' not in order_book:
        return None
    
    bids = order_book.get('bids', [])
    asks = order_book.get('asks', [])
    
    if not bids or not asks:
        return None
    
    # 计算每个价格档位的总挂单量
    bid_zones = {}
    ask_zones = {}
    
    # 分析买单
    for price, amount in bids:
        if price > 0 and amount > 0:
            rounded_price = round(price / 100) * 100
            if rounded_price not in bid_zones:
                bid_zones[rounded_price] = 0
            bid_zones[rounded_price] += amount
    
    # 分析卖单
    for price, amount in asks:
        if price > 0 and amount > 0:
            rounded_price = round(price / 100) * 100
            if rounded_price not in ask_zones:
                ask_zones[rounded_price] = 0
            ask_zones[rounded_price] += amount
    
    if not bid_zones or not ask_zones:
        return None
    
    # 识别流动性密集区
    avg_bid_volume = sum(bid_zones.values()) / len(bid_zones) if bid_zones else 0
    dense_bid_zones = [price for price, vol in bid_zones.items() if vol > avg_bid_volume * 1.5] if avg_bid_volume > 0 else []
    
    avg_ask_volume = sum(ask_zones.values()) / len(ask_zones) if ask_zones else 0
    dense_ask_zones = [price for price, vol in ask_zones.items() if vol > avg_ask_volume * 1.5] if avg_ask_volume > 0 else []
    
    # 识别流动性稀疏区
    sparse_bid_zones = [price for price, vol in bid_zones.items() if vol < avg_bid_volume * 0.5] if avg_bid_volume > 0 and bid_zones else []
    sparse_ask_zones = [price for price, vol in ask_zones.items() if vol < avg_ask_volume * 0.5] if avg_ask_volume > 0 and ask_zones else []
    
    return {
        'bid_zones': bid_zones,  # 所有买单区域（用于备用分析）
        'ask_zones': ask_zones,  # 所有卖单区域
        'dense_bid_zones': sorted(dense_bid_zones, reverse=True),
        'dense_ask_zones': sorted(dense_ask_zones),
        'sparse_bid_zones': sorted(sparse_bid_zones, reverse=True),
        'sparse_ask_zones': sorted(sparse_ask_zones),
        'current_price': current_price
    }

def suggest_stop_loss_by_liquidity(entry_price, signal_type, liquidity_analysis):
    """根据实时订单簿流动性分析给出止损建议"""
    if not liquidity_analysis:
        return None, None
    
    if signal_type == 'long':
        # 做多止损：放在买单密集区下方，但在流动性稀疏区
        dense_bid_zones = liquidity_analysis.get('dense_bid_zones', [])
        sparse_bid_zones = liquidity_analysis.get('sparse_bid_zones', [])
        current_price = liquidity_analysis.get('current_price', entry_price)
        
        # 找到入场价下方的买单密集区（支撑位）
        support_zones = [zone for zone in dense_bid_zones if zone < entry_price]
        
        if support_zones:
            nearest_support = max(support_zones)  # 最近的支撑位
            
            # 在支撑位下方找流动性稀疏区（适合止损）
            sparse_below = [zone for zone in sparse_bid_zones if zone < nearest_support]
            
            if sparse_below:
                # 选择支撑位下方最近的稀疏区
                stop_loss = max(sparse_below)
                distance = entry_price - stop_loss
                distance_pct = (distance / entry_price) * 100
                
                # 确保止损距离合理（0.5%-3%）
                if 0.5 <= distance_pct <= 3.0:
                    return stop_loss, {
                        'source': 'liquidity',
                        'support_zone': nearest_support,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'reason': f'基于实时订单簿：支撑位${nearest_support:,.0f}下方，流动性稀疏区${stop_loss:,.0f}'
                    }
                elif distance_pct < 0.5:
                    # 如果太近，放在支撑位下方一点
                    stop_loss = nearest_support * 0.995
                    distance = entry_price - stop_loss
                    distance_pct = (distance / entry_price) * 100
                    return stop_loss, {
                        'source': 'liquidity',
                        'support_zone': nearest_support,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'reason': f'基于实时订单簿：支撑位${nearest_support:,.0f}下方0.5%'
                    }
            else:
                # 如果没有稀疏区，放在支撑位下方
                stop_loss = nearest_support * 0.995
                distance = entry_price - stop_loss
                distance_pct = (distance / entry_price) * 100
                if distance_pct <= 3.0:
                    return stop_loss, {
                        'source': 'liquidity',
                        'support_zone': nearest_support,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'reason': f'基于实时订单簿：支撑位${nearest_support:,.0f}下方0.5%'
                    }
        
        # 如果没有找到密集区，基于订单簿中的买单价格分布给出建议
        # 找到入场价下方最近的买单价格作为参考
        if 'bid_zones' in liquidity_analysis:
            bid_zones = liquidity_analysis['bid_zones']
            if bid_zones:
                # 找到入场价下方的所有买单价格
                below_entry = [price for price in bid_zones.keys() if price < entry_price]
                if below_entry:
                    # 选择入场价下方最近的买单价格，在其下方设置止损
                    nearest_bid = max(below_entry)
                    stop_loss = nearest_bid * 0.998  # 在最近买单下方0.2%
                    distance = entry_price - stop_loss
                    distance_pct = (distance / entry_price) * 100
                    
                    # 确保止损距离合理（0.3%-2%）
                    if 0.3 <= distance_pct <= 2.0:
                        return stop_loss, {
                            'source': 'liquidity',
                            'support_zone': nearest_bid,
                            'distance': distance,
                            'distance_pct': distance_pct,
                            'reason': f'基于实时订单簿：入场价下方最近买单${nearest_bid:,.0f}下方0.2%'
                        }
    
    return None, None

def get_year_open_price(klines_1d):
    """获取年开盘价格（今年第一天的开盘价）"""
    if not klines_1d:
        return None
    
    from datetime import datetime
    
    # 获取当前年份
    current_year = datetime.now().year
    
    # K线数据是正序的（最早的在前，最新的在后），从前往后找今年最早的数据
    first_jan_open = None  # 1月最早的数据
    first_year_open = None  # 今年最早的数据
    
    for kline in klines_1d:
        # 将时间戳转换为日期
        kline_date = datetime.fromtimestamp(kline['timestamp'])
        
        if kline_date.year == current_year:
            # 记录今年最早的数据
            if first_year_open is None:
                first_year_open = kline['open']
            
            # 如果是1月1日，直接返回
            if kline_date.month == 1 and kline_date.day == 1:
                return kline['open']
            
            # 记录1月最早的数据
            if kline_date.month == 1 and first_jan_open is None:
                first_jan_open = kline['open']
    
    # 优先返回1月最早的数据，如果没有则返回今年最早的数据
    return first_jan_open if first_jan_open is not None else first_year_open

def find_recent_low(klines, lookback=50):
    """查找最近的低点"""
    if not klines or len(klines) < lookback:
        lookback = len(klines)
    
    recent_klines = klines[-lookback:]
    lows = [k['low'] for k in recent_klines]
    return min(lows) if lows else None

def generate_trading_plan():
    """生成交易计划"""
    print("正在获取BTC市场数据...", file=sys.stderr)
    
    # 获取当前价格
    current_price = get_btc_current_price()
    
    # 获取K线数据（用于分析年线等）
    klines_1h = get_btc_kline_gateio('1h', 200)
    klines_1d = get_btc_kline_gateio('1d', 365)  # 年线需要日线数据
    
    if not current_price:
        print("无法获取当前价格，使用默认值", file=sys.stderr)
        current_price = 86000  # 假设价格
    
    # 获取年开盘价格（年线）
    year_open_price = None
    if klines_1d:
        year_open_price = get_year_open_price(klines_1d)
    
    # 查找最近低点
    recent_low = None
    if klines_1h:
        recent_low = find_recent_low(klines_1h, 50)
    
    # 生成交易计划
    plan = []
    plan.append("# De. 交易计划")
    plan.append("")
    plan.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    plan.append(f"**当前价格**: ${current_price:,.2f}  ")
    if year_open_price:
        plan.append(f"**年线（年开盘价）**: ${year_open_price:,.2f}  ")
        distance_pct = ((current_price - year_open_price) / year_open_price * 100)
        if distance_pct > 0:
            plan.append(f"**年线距离**: 上方{distance_pct:.2f}%  ")
        else:
            plan.append(f"**年线距离**: 下方{abs(distance_pct):.2f}%  ")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    
    plan.append("## 📋 交易指令")
    plan.append("")
    plan.append("**De.**")
    plan.append("")
    plan.append("明天低多，多在863下面损一次，85附近再多一次，新低止损")
    plan.append("")
    plan.append("感受一下年线拉伸的力量，如果垮，两把加起来亏千把点")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    
    plan.append("## 🎯 交易计划")
    plan.append("")
    
    # 第一次入场
    plan.append("### 第一次入场（主头寸）")
    plan.append("")
    plan.append("**入场策略**: 在863下方做多")
    plan.append("")
    
    # 计算入场价格（863下方，假设是86000左右，需要根据实际价格调整）
    entry_1 = 86000  # 假设863指的是86300，下方就是86000附近
    if current_price < 87000:
        # 如果当前价格在863附近，入场价可以设置在863下方
        entry_1 = 86000
    else:
        # 如果价格较高，需要等待回调
        entry_1 = 86000
    
    plan.append(f"- **挂单入场**: ${entry_1:,.0f}（863下方）")
    plan.append(f"- **止损位置**: ${86300:,.0f}下方（863下方）")
    plan.append("")
    
    # 获取实时订单簿并计算止损（使用多交易所重试机制）
    print("正在获取实时订单簿数据（第一次入场）...", file=sys.stderr)
    order_book = get_order_book_with_retry(limit=50)
    
    stop_loss_1 = None
    stop_loss_1_info = None
    
    if order_book and current_price:
        liquidity_analysis = analyze_liquidity_zones(order_book, current_price)
        if liquidity_analysis:
            stop_loss_1, stop_loss_1_info = suggest_stop_loss_by_liquidity(entry_1, 'long', liquidity_analysis)
        
        # 如果流动性分析没有给出建议，直接基于订单簿原始数据
        if not stop_loss_1 and order_book.get('bids'):
            bids = order_book['bids']
            # 找到入场价或当前价格下方的买单（取较小值作为参考价）
            reference_price = min(entry_1, current_price)
            below_reference = [(price, amount) for price, amount in bids if price < reference_price]
            
            if below_reference:
                # 找到参考价下方最近的买单价格
                below_reference.sort(reverse=True)  # 从高到低排序
                nearest_bid_price = below_reference[0][0]
                # 在最近买单下方设置止损（0.3%-1%）
                stop_loss_1 = nearest_bid_price * 0.997  # 下方0.3%
                distance = entry_1 - stop_loss_1
                distance_pct = (distance / entry_1) * 100
                if 0.3 <= distance_pct <= 2.0:
                    stop_loss_1_info = {
                        'source': 'liquidity',
                        'support_zone': nearest_bid_price,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'reason': f'基于实时订单簿：参考价下方最近买单${nearest_bid_price:,.0f}下方0.3%'
                    }
            else:
                # 如果入场价下方没有买单，基于当前价格附近的订单簿数据
                below_current = [(price, amount) for price, amount in bids if price < current_price]
                if below_current:
                    below_current.sort(reverse=True)
                    nearest_bid = below_current[0][0]
                    # 在入场价和最近买单之间设置止损
                    stop_loss_1 = entry_1 * 0.995  # 入场价下方0.5%
                    distance = entry_1 - stop_loss_1
                    distance_pct = (distance / entry_1) * 100
                    stop_loss_1_info = {
                        'source': 'liquidity',
                        'support_zone': nearest_bid,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'reason': f'基于实时订单簿：当前价格${current_price:,.0f}附近买单${nearest_bid:,.0f}，入场价下方0.5%'
                    }
    
    plan.append("**止损设置（基于实时订单簿）**:")
    plan.append("- 止损必须设置在863下方")
    plan.append("- 头寸接到就要立即设置止损（必须设置）")
    plan.append("")
    
    if stop_loss_1 and stop_loss_1_info:
        plan.append(f"- **实时订单簿止损**: ${stop_loss_1:,.0f}")
        plan.append(f"  - 止损距离: {stop_loss_1_info['distance']:.0f}点（{stop_loss_1_info['distance_pct']:.2f}%）")
        plan.append(f"  - 止损理由: {stop_loss_1_info['reason']}")
        if 'support_zone' in stop_loss_1_info:
            plan.append(f"  - 支撑位: ${stop_loss_1_info['support_zone']:,.0f}")
    else:
        # 如果无法获取订单簿，使用保守止损
        stop_loss_1 = entry_1 * 0.985  # 1.5%止损
        plan.append(f"- **建议止损价**: ${stop_loss_1:,.0f}（入场价下方1.5%，请观察实时订单簿）")
        plan.append("  - ⚠️ 无法获取实时订单簿，建议手动观察订单簿设置止损")
    plan.append("")
    
    # 第二次入场
    plan.append("### 第二次入场（加仓）")
    plan.append("")
    plan.append("**入场策略**: 在85附近再次做多")
    plan.append("")
    
    # 85可能指的是85000附近
    entry_2 = 85000
    plan.append(f"- **挂单入场**: ${entry_2:,.0f}（85附近）")
    plan.append(f"- **止损位置**: 新低止损")
    plan.append("")
    
    # 获取实时订单簿并计算止损（第二次入场，使用多交易所重试机制）
    print("正在获取实时订单簿数据（第二次入场）...", file=sys.stderr)
    order_book_2 = get_order_book_with_retry(limit=50)
    
    stop_loss_2 = None
    stop_loss_2_info = None
    
    if order_book_2 and current_price:
        liquidity_analysis_2 = analyze_liquidity_zones(order_book_2, current_price)
        if liquidity_analysis_2:
            stop_loss_2, stop_loss_2_info = suggest_stop_loss_by_liquidity(entry_2, 'long', liquidity_analysis_2)
        
        # 如果流动性分析没有给出建议，直接基于订单簿原始数据
        if not stop_loss_2 and order_book_2.get('bids'):
            bids = order_book_2['bids']
            # 找到入场价或当前价格下方的买单（取较小值作为参考价）
            reference_price = min(entry_2, current_price)
            below_reference = [(price, amount) for price, amount in bids if price < reference_price]
            
            if below_reference:
                # 找到参考价下方最近的买单价格
                below_reference.sort(reverse=True)  # 从高到低排序
                nearest_bid_price = below_reference[0][0]
                # 在最近买单下方设置止损（0.3%-1%）
                stop_loss_2 = nearest_bid_price * 0.997  # 下方0.3%
                distance = entry_2 - stop_loss_2
                distance_pct = (distance / entry_2) * 100
                if 0.3 <= distance_pct <= 2.0:
                    stop_loss_2_info = {
                        'source': 'liquidity',
                        'support_zone': nearest_bid_price,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'reason': f'基于实时订单簿：参考价下方最近买单${nearest_bid_price:,.0f}下方0.3%'
                    }
            else:
                # 如果入场价下方没有买单，基于当前价格附近的订单簿数据
                below_current = [(price, amount) for price, amount in bids if price < current_price]
                if below_current:
                    below_current.sort(reverse=True)
                    nearest_bid = below_current[0][0]
                    # 在入场价和最近买单之间设置止损
                    stop_loss_2 = entry_2 * 0.995  # 入场价下方0.5%
                    distance = entry_2 - stop_loss_2
                    distance_pct = (distance / entry_2) * 100
                    stop_loss_2_info = {
                        'source': 'liquidity',
                        'support_zone': nearest_bid,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'reason': f'基于实时订单簿：当前价格${current_price:,.0f}附近买单${nearest_bid:,.0f}，入场价下方0.5%'
                    }
    
    plan.append("**止损设置（基于实时订单簿 + 新低）**:")
    plan.append("- 止损必须设置在新低下方")
    plan.append("- 如果价格创新低，止损也要相应调整")
    plan.append("- 头寸接到就要立即设置止损（必须设置）")
    plan.append("")
    
    # 结合新低和实时订单簿
    if stop_loss_2 and stop_loss_2_info:
        # 如果实时订单簿有建议，且新低存在，取两者中更合理的
        if recent_low:
            new_low_stop = recent_low * 0.995  # 新低下方0.5%
            # 选择更接近入场价的止损（更紧的止损）
            if new_low_stop < entry_2 and new_low_stop > stop_loss_2:
                stop_loss_2 = new_low_stop
                stop_loss_2_info['reason'] = f'基于新低${recent_low:,.0f}和实时订单簿，取更紧的止损'
        
        plan.append(f"- **实时订单簿止损**: ${stop_loss_2:,.0f}")
        plan.append(f"  - 止损距离: {stop_loss_2_info['distance']:.0f}点（{stop_loss_2_info['distance_pct']:.2f}%）")
        plan.append(f"  - 止损理由: {stop_loss_2_info['reason']}")
        if 'support_zone' in stop_loss_2_info:
            plan.append(f"  - 支撑位: ${stop_loss_2_info['support_zone']:,.0f}")
        if recent_low:
            plan.append(f"  - 最近低点: ${recent_low:,.0f}")
    elif recent_low:
        # 如果无法获取订单簿，使用新低止损
        stop_loss_2 = recent_low * 0.995
        if stop_loss_2 > entry_2:
            stop_loss_2 = entry_2 * 0.985  # 如果新低止损高于入场价，使用1.5%止损
        plan.append(f"- **新低止损价**: ${stop_loss_2:,.0f}（基于最近低点${recent_low:,.0f}，入场价下方{((entry_2 - stop_loss_2) / entry_2 * 100):.1f}%）")
        plan.append("  - ⚠️ 无法获取实时订单簿，建议手动观察订单簿设置止损")
    else:
        # 如果都没有，使用保守止损
        stop_loss_2 = entry_2 * 0.985  # 1.5%止损
        plan.append(f"- **建议止损价**: ${stop_loss_2:,.0f}（入场价下方1.5%，请观察实时订单簿）")
        plan.append("  - ⚠️ 无法获取实时订单簿和新低数据，建议手动观察订单簿设置止损")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    
    plan.append("## ⚠️ 风险提示")
    plan.append("")
    plan.append("### 年线支撑分析")
    plan.append("")
    if year_open_price:
        if current_price > year_open_price:
            plan.append(f"- ✅ **当前价格在年线上方**: ${current_price:,.0f} > ${year_open_price:,.0f}")
            plan.append("- 年线（年开盘价）作为重要支撑，如果价格回踩年线附近，可能获得支撑")
        else:
            plan.append(f"- ⚠️ **当前价格在年线下方**: ${current_price:,.0f} < ${year_open_price:,.0f}")
            plan.append("- 年线（年开盘价）已被跌破，需要谨慎观察")
        
        plan.append("")
        plan.append("- **年线位置（年开盘价）**: ${:,.0f}".format(year_open_price))
        distance_pct = ((current_price - year_open_price) / year_open_price * 100)
        if distance_pct > 0:
            plan.append("- **年线距离**: 上方{:.2f}%".format(distance_pct))
        else:
            plan.append("- **年线距离**: 下方{:.2f}%".format(abs(distance_pct)))
        plan.append("")
    
    plan.append("### 最大风险")
    plan.append("")
    plan.append("- ⚠️ **如果年线垮掉，两把头寸加起来可能亏损约1000点**")
    plan.append("- 需要密切关注年线支撑的有效性")
    plan.append("- 如果价格跌破年线且无法收回，考虑及时止损")
    plan.append("")
    
    # 计算潜在亏损（以点为单位，假设1点=1美元）
    if entry_1 and entry_2 and stop_loss_1 and stop_loss_2:
        loss_1 = entry_1 - stop_loss_1  # 第一次入场的潜在亏损
        loss_2 = entry_2 - stop_loss_2  # 第二次入场的潜在亏损
        # 如果两个头寸都止损，总亏损是两者之和
        total_loss_points = loss_1 + loss_2
        plan.append(f"- **潜在最大亏损**: 约{total_loss_points:.0f}点")
        plan.append(f"  - 头寸1（${entry_1:,.0f}）: {loss_1:.0f}点（{((loss_1/entry_1)*100):.1f}%）")
        plan.append(f"  - 头寸2（${entry_2:,.0f}）: {loss_2:.0f}点（{((loss_2/entry_2)*100):.1f}%）")
        plan.append(f"  - 合计: {total_loss_points:.0f}点")
        plan.append("")
    
    plan.append("---")
    plan.append("")
    
    plan.append("## 📊 仓位管理")
    plan.append("")
    plan.append("### 逐仓模式")
    plan.append("")
    plan.append("- ✅ **必须使用逐仓模式**")
    plan.append("- 每个头寸独立设置止损（一比归一比）")
    plan.append("- 头寸接到就要立即设置止损（必须设置）")
    plan.append("")
    
    plan.append("### 仓位分配建议")
    plan.append("")
    plan.append("- **第一次入场（主头寸）**: 建议仓位60-70%")
    plan.append("- **第二次入场（加仓）**: 建议仓位30-40%")
    plan.append("- **总风险**: 控制在账户资金的2-3%")
    plan.append("")
    
    plan.append("### 止盈策略")
    plan.append("")
    plan.append("- **分批止盈**: 50% + 50%")
    plan.append("- **第一目标**: 入场价上方2-3%")
    plan.append("- **第二目标**: 入场价上方4-6%")
    plan.append("- **移动止损**: 盈利400点后移动止损到入场价（保本）")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    
    plan.append("## ✅ 交易检查清单")
    plan.append("")
    plan.append("### 入场前检查")
    plan.append("")
    plan.append("□ 价格是否回落到863下方？")
    plan.append("□ 是否在年线附近获得支撑？")
    plan.append("□ 是否设置了逐仓模式？")
    plan.append("□ 是否准备好挂单？")
    plan.append("")
    
    plan.append("### 入场后检查")
    plan.append("")
    plan.append("□ 头寸接到后是否立即设置了止损？")
    plan.append("□ 止损位置是否合理（2-3%）？")
    plan.append("□ 是否关注年线支撑的有效性？")
    plan.append("□ 是否准备好第二次入场（85附近）？")
    plan.append("")
    
    plan.append("### 持仓中检查")
    plan.append("")
    plan.append("□ 年线是否仍然有效支撑？")
    plan.append("□ 如果价格创新低，是否调整了止损？")
    plan.append("□ 是否达到第一止盈目标？")
    plan.append("□ 盈利400点后是否移动止损到保本？")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    
    plan.append("## 📝 注意事项")
    plan.append("")
    plan.append("1. **年线是关键支撑**: 感受年线拉伸的力量，如果年线垮掉，需要及时止损")
    plan.append("2. **止损必须设置**: 头寸接到就要设置止损，不能等待")
    plan.append("3. **一比归一比**: 每个头寸独立设置止损，不能合并")
    plan.append("4. **新低止损**: 第二次入场的止损要设置在新低下方，如果价格创新低，止损也要调整")
    plan.append("5. **风险控制**: 两把头寸加起来可能亏损约1000点，需要控制仓位大小")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    
    plan.append("**免责声明**: 本交易计划基于De.交易指令自动生成，仅供参考。交易有风险，入市需谨慎。")
    plan.append("")
    
    # 输出计划
    output = "\n".join(plan)
    
    # 保存到文件
    filename = f"De_trading_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    
    # 输出到控制台（避免emoji编码问题）
    try:
        print(output)
    except UnicodeEncodeError:
        # 如果输出失败，只输出文件名
        pass
    
    print(f"\n交易计划已保存到: {filename}", file=sys.stderr)
    
    return filename

if __name__ == '__main__':
    generate_trading_plan()

