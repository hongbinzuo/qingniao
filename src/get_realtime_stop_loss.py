#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时订单簿止损查询工具
用法：
  python get_realtime_stop_loss.py BTC long sl
  python get_realtime_stop_loss.py BTC long sl 86000
  python get_realtime_stop_loss.py BTC short sl 90000
"""

import requests
import sys
import json
from pathlib import Path
from datetime import datetime

# 读取系统参数（学习改进后的参数）
def load_system_parameters():
    """加载系统参数"""
    params_file = Path(__file__).parent.parent / "trading_signals" / ".ml_models" / "system_parameters.json"
    if params_file.exists():
        try:
            return json.loads(params_file.read_text(encoding='utf-8'))
        except:
            pass
    # 默认参数
    return {
        'min_stop_distances': {
            'low_volatility': 0.4,  # 学习改进后：从0.3%提高到0.4%
            'medium_volatility': 0.5,
            'high_volatility': 0.8
        }
    }

# 获取最小止损距离（根据波动率）
def get_min_stop_distance(volatility_level='low'):
    """根据波动率水平获取最小止损距离"""
    params = load_system_parameters()
    min_distances = params.get('min_stop_distances', {})
    
    # 映射波动率水平
    vol_map = {
        'low': 'low_volatility',
        'medium': 'medium_volatility',
        'high': 'high_volatility',
        'very_high': 'high_volatility'
    }
    
    vol_key = vol_map.get(volatility_level, 'low_volatility')
    return min_distances.get(vol_key, 0.4)  # 默认0.4%（学习改进后的值）

def get_order_book_binance(symbol='BTCUSDT', limit=50):
    """从Binance获取订单簿数据"""
    try:
        url = "https://api.binance.com/api/v3/depth"
        params = {'symbol': symbol, 'limit': min(limit, 100)}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('bids') and data.get('asks'):
                bids = [(float(b[0]), float(b[1])) for b in data.get('bids', [])]
                asks = [(float(a[0]), float(a[1])) for a in data.get('asks', [])]
                if bids and asks:
                    return {'bids': bids, 'asks': asks, 'timestamp': data.get('lastUpdateId', 0)}
    except:
        pass
    return None

def get_order_book_bybit(symbol='BTCUSDT', limit=50):
    """从Bybit获取订单簿数据"""
    try:
        url = "https://api.bybit.com/v5/market/orderbook"
        params = {'category': 'spot', 'symbol': symbol, 'limit': min(limit, 200)}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0 and data.get('result'):
                result = data['result']
                bids = [(float(b[0]), float(b[1])) for b in result.get('b', [])]
                asks = [(float(a[0]), float(a[1])) for a in result.get('a', [])]
                if bids and asks:
                    return {'bids': bids, 'asks': asks, 'timestamp': result.get('ts', 0)}
    except:
        pass
    return None

def get_order_book_okx(symbol='BTC-USDT', limit=50):
    """从OKX获取订单簿数据"""
    try:
        url = "https://www.okx.com/api/v5/market/books"
        params = {'instId': symbol, 'sz': min(limit, 400)}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '0' and data.get('data'):
                order_data = data['data'][0]
                bids = [(float(b[0]), float(b[1])) for b in order_data.get('bids', [])]
                asks = [(float(a[0]), float(a[1])) for a in order_data.get('asks', [])]
                if bids and asks:
                    return {'bids': bids, 'asks': asks, 'timestamp': int(order_data.get('ts', 0))}
    except:
        pass
    return None

def get_order_book_gateio(symbol='BTC_USDT', limit=50):
    """从Gate.io获取订单簿数据"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/order_book"
        params = {'currency_pair': symbol, 'limit': limit, 'interval': '0'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and data.get('bids') and data.get('asks'):
                bids = [(float(b[0]), float(b[1])) for b in data.get('bids', [])]
                asks = [(float(a[0]), float(a[1])) for a in data.get('asks', [])]
                if bids and asks:
                    return {'bids': bids, 'asks': asks, 'timestamp': data.get('t', 0)}
    except:
        pass
    return None

def get_order_book_with_retry(symbol='BTC', limit=50):
    """获取订单簿，带重试机制，尝试多个交易所"""
    # 根据币种确定交易对
    symbol_map = {
        'BTC': ('BTCUSDT', 'BTC-USDT', 'BTC_USDT'),
        'ETH': ('ETHUSDT', 'ETH-USDT', 'ETH_USDT'),
        'BNB': ('BNBUSDT', 'BNB-USDT', 'BNB_USDT'),
    }
    
    symbols = symbol_map.get(symbol.upper(), ('BTCUSDT', 'BTC-USDT', 'BTC_USDT'))
    binance_symbol, okx_symbol, gateio_symbol = symbols
    
    exchanges = [
        ('Binance', lambda: get_order_book_binance(binance_symbol, limit)),
        ('Bybit', lambda: get_order_book_bybit(binance_symbol, limit)),
        ('OKX', lambda: get_order_book_okx(okx_symbol, limit)),
        ('Gate.io', lambda: get_order_book_gateio(gateio_symbol, limit)),
    ]
    
    for exchange_name, get_func in exchanges:
        try:
            result = get_func()
            if result and result.get('bids') and result.get('asks'):
                if len(result['bids']) > 0 and len(result['asks']) > 0:
                    return result, exchange_name
        except:
            continue
    
    return None, None

def get_current_price(symbol='BTC'):
    """获取当前价格"""
    try:
        symbol_map = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT', 'BNB': 'BNBUSDT'}
        trading_pair = symbol_map.get(symbol.upper(), 'BTCUSDT')
        
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {'symbol': trading_pair}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return float(data.get('price', 0))
    except:
        pass
    return None

def analyze_liquidity_zones(order_book, current_price):
    """分析订单簿，识别流动性密集区和稀疏区"""
    if not order_book:
        return None
    
    bids = order_book.get('bids', [])
    asks = order_book.get('asks', [])
    
    if not bids or not asks:
        return None
    
    # 将价格聚合到整数档位（BTC以100为单位）
    bid_zones = {}  # {价格档位: 总挂单量}
    ask_zones = {}
    
    # 分析买单
    for price, amount in bids:
        if price > 0 and amount > 0:
            # BTC价格聚合到百位
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
    
    # 识别流动性密集区（挂单量大的区域）
    avg_bid_volume = sum(bid_zones.values()) / len(bid_zones) if bid_zones else 0
    dense_bid_zones = [(price, vol) for price, vol in bid_zones.items() 
                      if vol > avg_bid_volume * 1.5]  # 超过平均1.5倍为密集区
    
    avg_ask_volume = sum(ask_zones.values()) / len(ask_zones) if ask_zones else 0
    dense_ask_zones = [(price, vol) for price, vol in ask_zones.items() 
                      if vol > avg_ask_volume * 1.5]
    
    # 识别流动性稀疏区（挂单量小的区域）
    sparse_bid_zones = [(price, vol) for price, vol in bid_zones.items() 
                       if vol < avg_bid_volume * 0.5]  # 低于平均0.5倍为稀疏区
    
    sparse_ask_zones = [(price, vol) for price, vol in ask_zones.items() 
                       if vol < avg_ask_volume * 0.5]
    
    return {
        'bid_zones': bid_zones,
        'ask_zones': ask_zones,
        'dense_bid_zones': sorted(dense_bid_zones, key=lambda x: x[0], reverse=True),  # 从高到低
        'dense_ask_zones': sorted(dense_ask_zones, key=lambda x: x[0]),  # 从低到高
        'sparse_bid_zones': sorted(sparse_bid_zones, key=lambda x: x[0], reverse=True),
        'sparse_ask_zones': sorted(sparse_ask_zones, key=lambda x: x[0]),
        'current_price': current_price
    }

def calculate_stop_loss_by_orderbook(entry_price, signal_type, order_book, current_price):
    """基于实时订单簿流动性分析计算止损"""
    if not order_book or not current_price:
        return None, None
    
    bids = order_book.get('bids', [])
    asks = order_book.get('asks', [])
    
    if not bids or not asks:
        return None, None
    
    # 先进行流动性分析
    liquidity_analysis = analyze_liquidity_zones(order_book, current_price)
    
    if signal_type == 'long':
        # 找到入场价下方的买单
        below_entry = [(price, amount) for price, amount in bids if price < entry_price]
        
        # 如果入场价下方没有买单（入场价低于当前价格），基于当前价格附近的订单簿数据
        if not below_entry:
            # 找到当前价格下方的买单
            below_current = [(price, amount) for price, amount in bids if price < current_price]
            if below_current:
                # 找到挂单量最小的价格（稀疏区）
                below_current.sort(key=lambda x: (x[1], -x[0]))  # 按挂单量升序，价格降序
                sparse_price, sparse_vol = below_current[0]
                
                # 在入场价和稀疏区价格之间设置止损
                # 如果稀疏区价格高于入场价，需要找到入场价下方的实际订单簿价格
                if sparse_price > entry_price:
                    # 找到入场价下方的所有实际订单簿价格
                    below_entry_prices = [price for price, amount in bids if price < entry_price]
                    if below_entry_prices:
                        # 使用入场价下方最近的实际价格（真正的基于订单簿！）
                        stop_loss_price = max(below_entry_prices)
                        is_from_orderbook = True
                        source_info = f'入场价下方最近实际订单簿价格${stop_loss_price:,.2f}'
                    else:
                        # 如果入场价下方确实没有价格（入场价太低），
                        # 找到当前价格下方挂单量最小的价格，然后在其下方设置止损
                        # 但止损必须低于入场价
                        if sparse_price > entry_price:
                            # 在入场价下方找一个合理的止损位置
                            # 基于订单簿，找到入场价下方最近的价格档位
                            # 将价格聚合到百位，找到入场价下方的档位
                            entry_rounded = round(entry_price / 100) * 100
                            below_entry_zones = [round(p / 100) * 100 for p, a in bids 
                                                if round(p / 100) * 100 < entry_rounded]
                            if below_entry_zones:
                                # 使用入场价下方最近的价格档位（真正的基于订单簿！）
                                stop_loss_price = max(below_entry_zones)
                                is_from_orderbook = True
                                source_info = f'入场价下方最近价格档位${stop_loss_price:,.0f}（基于订单簿价格聚合）'
                            else:
                                # 如果还是没有，基于订单簿的价格分布来设置止损
                                # 找到所有买单价格，计算价格分布
                                all_bid_prices = [price for price, amount in bids]
                                if all_bid_prices:
                                    min_bid = min(all_bid_prices)
                                    max_bid = max(all_bid_prices)
                                    # 计算价格间隔（订单簿中的典型价格间隔）
                                    if len(all_bid_prices) > 1:
                                        price_intervals = [abs(all_bid_prices[i] - all_bid_prices[i+1]) 
                                                          for i in range(len(all_bid_prices)-1)]
                                        avg_interval = sum(price_intervals) / len(price_intervals) if price_intervals else 10
                                    else:
                                        avg_interval = 10  # 默认间隔
                                    
                                    # 在入场价下方，基于订单簿的实际价格档位设置止损（不是计算出来的！）
                                    # 将订单簿价格聚合到整数档位，找到入场价下方的实际价格档位
                                    price_zones = {}
                                    for price, amount in bids:
                                        # BTC价格聚合到百位
                                        rounded = round(price / 100) * 100
                                        if rounded not in price_zones:
                                            price_zones[rounded] = []
                                        price_zones[rounded].append((price, amount))
                                    
                                    # 找到入场价下方的所有价格档位
                                    entry_rounded = round(entry_price / 100) * 100
                                    below_zones = [zone for zone in price_zones.keys() if zone < entry_rounded]
                                    
                                    if below_zones:
                                        # 找到入场价下方最近的价格档位
                                        nearest_zone = max(below_zones)
                                        # 在该档位内，找到挂单量最小的实际价格（稀疏区）
                                        zone_prices = price_zones[nearest_zone]
                                        zone_prices.sort(key=lambda x: x[1])  # 按挂单量升序
                                        sparse_price_in_zone, sparse_vol = zone_prices[0]
                                        
                                        # 直接使用稀疏区的实际价格作为止损（真正的基于订单簿！）
                                        stop_loss_price = sparse_price_in_zone
                                        is_from_orderbook = True
                                        source_info = f'入场价下方价格档位${nearest_zone:,.0f}内的稀疏区实际价格${sparse_price_in_zone:,.2f}（挂单量{sparse_vol:.4f} BTC）'
                                    else:
                                        # 如果入场价下方没有价格档位，基于订单簿价格分布推断
                                        if price_zones:
                                            # 找到所有价格档位，计算价格间隔
                                            all_zones = sorted(price_zones.keys())
                                            if len(all_zones) > 1:
                                                zone_intervals = [all_zones[i+1] - all_zones[i] for i in range(len(all_zones)-1)]
                                                avg_zone_interval = sum(zone_intervals) / len(zone_intervals) if zone_intervals else 100
                                            else:
                                                avg_zone_interval = 100
                                            
                                            # 找到最低的价格档位
                                            lowest_zone = min(all_zones)
                                            # 在该档位内找挂单量最小的价格
                                            lowest_zone_prices = price_zones[lowest_zone]
                                            lowest_zone_prices.sort(key=lambda x: x[1])
                                            lowest_sparse_price, lowest_sparse_vol = lowest_zone_prices[0]
                                            
                                            # 基于价格档位间隔，推断入场价下方的合理价格档位
                                            entry_rounded = round(entry_price / 100) * 100
                                            zones_below = int((entry_rounded - lowest_zone) / avg_zone_interval) if entry_rounded > lowest_zone else 3
                                            inferred_zone = entry_rounded - (zones_below * avg_zone_interval)
                                            
                                            # 使用推断的档位，但确保在入场价下方
                                            if inferred_zone < entry_price:
                                                stop_loss_price = inferred_zone
                                                is_from_orderbook = True
                                                source_info = f'基于订单簿价格分布推断：最低档位${lowest_zone:,.0f}，推断入场价下方档位${inferred_zone:,.0f}（基于订单簿价格间隔{avg_zone_interval:.0f}）'
                                            else:
                                                # 如果推断的档位高于入场价，使用最低档位的稀疏区价格
                                                if lowest_sparse_price < entry_price:
                                                    stop_loss_price = lowest_sparse_price
                                                    is_from_orderbook = True
                                                    source_info = f'基于订单簿：最低价格档位${lowest_zone:,.0f}内的稀疏区实际价格${lowest_sparse_price:,.2f}（挂单量{lowest_sparse_vol:.4f} BTC）'
                                                else:
                                                    # 最后备用：使用入场价下方0.5%（非订单簿）
                                                    stop_loss_price = entry_price * 0.995
                                                    is_from_orderbook = False
                                                    source_info = f'备用方案：入场价下方0.5%（非订单簿实际价格）'
                                        else:
                                            # 如果订单簿为空，使用入场价下方0.5%（非订单簿）
                                            stop_loss_price = entry_price * 0.995
                                            is_from_orderbook = False
                                            source_info = f'备用方案：入场价下方0.5%（非订单簿实际价格）'
                                else:
                                    # 如果订单簿为空，使用入场价下方0.5%（最后备用）
                                    stop_loss_price = entry_price * 0.995
                        else:
                            stop_loss_price = entry_price * 0.995
                else:
                    # 稀疏区价格低于入场价，直接使用稀疏区价格（真正的基于订单簿！）
                    stop_loss_price = sparse_price
                    is_from_orderbook = True
                    source_info = f'当前价格下方稀疏区实际价格${sparse_price:,.2f}（挂单量{sparse_vol:.4f} BTC）'
                
                distance = entry_price - stop_loss_price
                distance_pct = (distance / entry_price) * 100
                
                return stop_loss_price, {
                    'sparse_zone': sparse_price,
                    'sparse_volume': sparse_vol,
                    'distance': distance,
                    'distance_pct': distance_pct,
                    'is_from_orderbook': is_from_orderbook,
                    'source_info': source_info,
                    'reason': f'基于实时订单簿：入场价${entry_price:,.0f}低于当前价格${current_price:,.0f}，{source_info}'
                }
            else:
                # 如果当前价格下方也没有买单，使用入场价下方0.5%（非订单簿）
                stop_loss_price = entry_price * 0.995
                distance = entry_price - stop_loss_price
                distance_pct = (distance / entry_price) * 100
                return stop_loss_price, {
                    'distance': distance,
                    'distance_pct': distance_pct,
                    'is_from_orderbook': False,
                    'source_info': '备用方案：入场价下方0.5%（非订单簿实际价格）',
                    'reason': f'基于实时订单簿：入场价${entry_price:,.0f}低于当前价格${current_price:,.0f}，使用入场价下方0.5%（非订单簿实际价格）'
                }
        
        # 保存below_entry供后续使用
        below_entry_all = below_entry
        
        # 初始化最终结果变量
        final_stop_loss = None
        final_info = None
        
        # 最简单的方案：直接使用入场价下方最近的买单价格作为止损参考
        # 找到挂单量最小的价格（稀疏区）或最近的价格
        below_entry_sorted = sorted(below_entry, key=lambda x: (x[1], -x[0]))  # 按挂单量升序，价格降序
        sparse_price, sparse_vol = below_entry_sorted[0]  # 挂单量最小的
        
        # 直接使用稀疏区的实际价格作为止损（不是百分比！）
        stop_loss_price = sparse_price
        distance = entry_price - stop_loss_price
        distance_pct = (distance / entry_price) * 100
        
        # 直接使用稀疏区的实际价格作为止损（不是百分比！）
        # 这是最基础的方案，确保总能返回结果
        final_stop_loss = sparse_price
        final_info = {
            'sparse_zone': sparse_price,
            'sparse_volume': sparse_vol,
            'distance': distance,
            'distance_pct': distance_pct,
            'is_from_orderbook': True,
            'source_info': f'入场价下方稀疏区实际价格${sparse_price:,.2f}（挂单量{sparse_vol:.4f} BTC）',
            'reason': f'基于实时订单簿：入场价下方稀疏区${sparse_price:,.2f}（挂单量{sparse_vol:.4f} BTC，距离{distance_pct:.2f}%）'
        }
        # 如果流动性分析成功，使用流动性分析
        if liquidity_analysis:
            # 做多止损：放在买单密集区（支撑位）下方，但在流动性稀疏区
            dense_bid_zones = liquidity_analysis.get('dense_bid_zones', [])  # [(价格, 挂单量), ...]
            sparse_bid_zones = liquidity_analysis.get('sparse_bid_zones', [])
            
            # 找到入场价下方的买单密集区（支撑位）
            support_zones = [(price, vol) for price, vol in dense_bid_zones if price < entry_price]
            
            if support_zones:
                # 找到最近的支撑位（价格最高的密集区）
                nearest_support_price, support_volume = max(support_zones, key=lambda x: x[0])
                
                # 在支撑位下方找流动性稀疏区（适合止损）
                sparse_below = [(price, vol) for price, vol in sparse_bid_zones 
                              if price < nearest_support_price]
            
                if sparse_below:
                    # 选择支撑位下方最近的稀疏区作为止损
                    stop_loss_price, _ = max(sparse_below, key=lambda x: x[0])
                    distance = entry_price - stop_loss_price
                    distance_pct = (distance / entry_price) * 100
                    
                    # 确保止损距离合理（min_stop_pct%-3%）
                    min_stop_pct = get_min_stop_distance('low')  # 默认使用低波动率的最小止损距离
                    if min_stop_pct <= distance_pct <= 3.0:
                        return stop_loss_price, {
                            'support_zone': nearest_support_price,
                            'support_volume': support_volume,
                            'sparse_zone': stop_loss_price,
                            'distance': distance,
                            'distance_pct': distance_pct,
                            'is_from_orderbook': True,
                            'source_info': f'支撑位${nearest_support_price:,.0f}下方稀疏区实际价格${stop_loss_price:,.0f}',
                            'reason': f'基于实时订单簿流动性分析：支撑位${nearest_support_price:,.0f}（挂单量{support_volume:.2f}），下方稀疏区${stop_loss_price:,.0f}'
                        }
                
                # 如果没有稀疏区，在支撑位下方找订单簿中的实际价格档位
                # 找到支撑位下方的所有价格档位
                bid_zones = liquidity_analysis.get('bid_zones', {})
                below_support_prices = [price for price in bid_zones.keys() if price < nearest_support_price]
                if below_support_prices:
                    # 使用支撑位下方最近的实际价格档位作为止损（不是百分比！）
                    nearest_below_zone = max(below_support_prices)
                    stop_loss_price = nearest_below_zone
                    distance = entry_price - stop_loss_price
                    distance_pct = (distance / entry_price) * 100
                    
                    if 0.2 <= distance_pct <= 3.0:
                        return stop_loss_price, {
                            'support_zone': nearest_support_price,
                            'support_volume': support_volume,
                            'distance': distance,
                            'distance_pct': distance_pct,
                            'is_from_orderbook': True,
                            'source_info': f'支撑位${nearest_support_price:,.0f}下方实际价格档位${nearest_below_zone:,.0f}',
                            'reason': f'基于实时订单簿流动性分析：支撑位${nearest_support_price:,.0f}（挂单量{support_volume:.2f}），下方实际价格档位${nearest_below_zone:,.0f}'
                        }
        
        # 如果没有找到密集区，基于订单簿原始数据找关键价位
        # 找到入场价下方挂单量最大的几个价位
        below_entry = [(price, amount) for price, amount in bids if price < entry_price]
        if below_entry:
            # 按挂单量排序，找挂单量大的价位作为支撑
            below_entry.sort(key=lambda x: x[1], reverse=True)
            # 取挂单量最大的前3个，选择价格最高的作为支撑
            top_supports = sorted([x for x in below_entry[:3]], key=lambda x: x[0], reverse=True)
            if top_supports:
                support_price, support_amount = top_supports[0]
                # 在支撑位下方找订单簿中的实际价格档位（不是百分比计算！）
                # 找到支撑位下方的所有价格档位
                if liquidity_analysis:
                    bid_zones = liquidity_analysis.get('bid_zones', {})
                else:
                    # 如果没有流动性分析，直接从原始订单簿找
                    bid_zones = {}
                    for price, amount in bids:
                        rounded = round(price / 100) * 100
                        if rounded not in bid_zones:
                            bid_zones[rounded] = 0
                        bid_zones[rounded] += amount
                below_support = [(price, vol) for price, vol in bid_zones.items() 
                               if price < support_price]
                
                if below_support:
                    # 找到支撑位下方挂单量最小的价格档位（稀疏区）
                    below_support.sort(key=lambda x: (x[1], -x[0]))  # 按挂单量升序，价格降序
                    sparse_price, sparse_vol = below_support[0]  # 挂单量最小的
                    
                    # 直接使用稀疏区的价格作为止损（不是百分比！）
                    stop_loss_price = sparse_price
                    distance = entry_price - stop_loss_price
                    distance_pct = (distance / entry_price) * 100
                    
                    if 0.2 <= distance_pct <= 3.0:
                        return stop_loss_price, {
                            'support_zone': support_price,
                            'support_volume': support_amount,
                            'sparse_zone': sparse_price,
                            'sparse_volume': sparse_vol,
                            'distance': distance,
                            'distance_pct': distance_pct,
                            'is_from_orderbook': True,
                            'source_info': f'支撑位${support_price:,.0f}下方稀疏区实际价格${sparse_price:,.0f}（挂单量{sparse_vol:.2f}）',
                            'reason': f'基于实时订单簿：支撑位${support_price:,.0f}（挂单量{support_amount:.2f}），下方稀疏区${sparse_price:,.0f}（挂单量{sparse_vol:.2f}）'
                        }
                
                # 如果没有找到稀疏区，在支撑位下方找一个实际存在的价格档位
                # 找到支撑位下方最近的价格档位
                below_support_prices = [price for price in bid_zones.keys() if price < support_price]
                if below_support_prices:
                    nearest_below = max(below_support_prices)  # 支撑位下方最近的价格
                    stop_loss_price = nearest_below
                    distance = entry_price - stop_loss_price
                    distance_pct = (distance / entry_price) * 100
                    
                    if 0.2 <= distance_pct <= 3.0:
                        return stop_loss_price, {
                            'support_zone': support_price,
                            'support_volume': support_amount,
                            'distance': distance,
                            'distance_pct': distance_pct,
                            'is_from_orderbook': True,
                            'source_info': f'支撑位${support_price:,.0f}下方最近实际价格档位${nearest_below:,.0f}',
                            'reason': f'基于实时订单簿：支撑位${support_price:,.0f}（挂单量{support_amount:.2f}），下方最近价格档位${nearest_below:,.0f}'
                        }
        
        # 最后的备用方案：直接基于订单簿原始价格（不是聚合后的档位）
        # 找到入场价下方的所有买单，按挂单量排序
        below_entry = [(price, amount) for price, amount in bids if price < entry_price]
        
        if below_entry:
            # 找到挂单量最小的价格（稀疏区）
            below_entry.sort(key=lambda x: (x[1], -x[0]))  # 按挂单量升序，价格降序
            sparse_price, sparse_vol = below_entry[0]  # 挂单量最小的
            
            # 直接使用稀疏区的实际价格作为止损（不是百分比！）
            stop_loss_price = sparse_price
            distance = entry_price - stop_loss_price
            distance_pct = (distance / entry_price) * 100
            
            # 如果距离合理，使用稀疏区价格（至少min_stop_pct%，最多5%）
            min_stop_pct = get_min_stop_distance('low')  # 默认使用低波动率的最小止损距离
            if min_stop_pct <= distance_pct <= 5.0:  # 最小min_stop_pct%，避免太近被扫止损
                return stop_loss_price, {
                    'sparse_zone': sparse_price,
                    'sparse_volume': sparse_vol,
                    'distance': distance,
                    'distance_pct': distance_pct,
                    'is_from_orderbook': True,
                    'source_info': f'入场价下方稀疏区实际价格${sparse_price:,.2f}（挂单量{sparse_vol:.4f} BTC）',
                    'reason': f'基于实时订单簿：入场价下方稀疏区${sparse_price:,.2f}（挂单量{sparse_vol:.4f} BTC）'
                }
            
            # 如果稀疏区距离太远，找入场价下方挂单量较大的价格作为支撑
            below_entry.sort(key=lambda x: (x[1], -x[0]), reverse=True)  # 按挂单量降序
            if len(below_entry) > 0:
                # 找挂单量最大的几个，选择价格较高的作为支撑
                top_supports = sorted(below_entry[:min(5, len(below_entry))], 
                                     key=lambda x: x[0], reverse=True)
                if top_supports:
                    support_price, support_amount = top_supports[0]
                    # 在支撑位下方找一个实际存在的买单价格
                    below_support = [p for p, a in bids if p < support_price]
                    if below_support:
                        stop_loss_price = max(below_support)  # 支撑位下方最近的实际价格
                        distance = entry_price - stop_loss_price
                        distance_pct = (distance / entry_price) * 100
                        
                        min_stop_pct = get_min_stop_distance('low')  # 默认使用低波动率的最小止损距离
                        if min_stop_pct <= distance_pct <= 5.0:  # 最小min_stop_pct%
                            return stop_loss_price, {
                                'support_zone': support_price,
                                'support_volume': support_amount,
                                'distance': distance,
                                'distance_pct': distance_pct,
                                'is_from_orderbook': True,
                                'source_info': f'支撑位${support_price:,.2f}下方实际价格${stop_loss_price:,.2f}',
                                'reason': f'基于实时订单簿：支撑位${support_price:,.2f}（挂单量{support_amount:.4f} BTC），下方实际价格${stop_loss_price:,.2f}'
                            }
        
        # 如果以上所有方案都失败，使用之前保存的基础方案（确保总能返回）
        # final_stop_loss 和 final_info 已经在函数开始处设置，确保有值
        print(f"DEBUG: 使用基础方案，final_stop_loss={final_stop_loss}, final_info={final_info is not None}", file=sys.stderr)
        # 检查基础方案的止损距离是否合理
        if final_stop_loss and final_info:
            distance_pct = final_info.get('distance_pct', 0)
            # 从系统参数读取最小止损距离（学习改进后的参数）
            # 默认使用低波动率的最小止损距离（0.4%）
            min_stop_pct = get_min_stop_distance('low')
            if distance_pct < min_stop_pct:
                min_stop_distance = entry_price * (min_stop_pct / 100)  # 至少min_stop_pct%
                adjusted_stop_loss = entry_price - min_stop_distance
                adjusted_distance = entry_price - adjusted_stop_loss
                adjusted_distance_pct = (adjusted_distance / entry_price) * 100
                
                print(f"DEBUG: 止损距离太近({distance_pct:.2f}%)，调整到至少{min_stop_pct:.2f}%: ${adjusted_stop_loss:,.2f}", file=sys.stderr)
                
                final_info['distance'] = adjusted_distance
                final_info['distance_pct'] = adjusted_distance_pct
                final_info['is_from_orderbook'] = False  # 调整后的止损不是订单簿实际价格
                final_info['source_info'] = f'止损距离太近，已调整到至少{min_stop_pct:.2f}%（原订单簿止损：${final_stop_loss:,.2f}，距离{distance_pct:.2f}%）'
                final_info['reason'] = f'基于实时订单簿：原止损距离{distance_pct:.2f}%太近，已调整到至少{min_stop_pct:.2f}%：${adjusted_stop_loss:,.2f}'
                
                return adjusted_stop_loss, final_info
            
            return final_stop_loss, final_info
        
        # 如果基础方案也没有，使用入场价下方最近的价格（确保总能返回）
        if below_entry_all:
            below_entry_all.sort(reverse=True)  # 按价格降序
            nearest_below_price, nearest_below_amount = below_entry_all[0]
            print(f"DEBUG: 使用最近价格方案: {nearest_below_price}", file=sys.stderr)
            return nearest_below_price, {
                'support_zone': nearest_below_price,
                'support_volume': nearest_below_amount,
                'distance': entry_price - nearest_below_price,
                'distance_pct': ((entry_price - nearest_below_price) / entry_price) * 100,
                'is_from_orderbook': True,
                'source_info': f'入场价下方最近实际买单价格${nearest_below_price:,.2f}（挂单量{nearest_below_amount:.4f} BTC）',
                'reason': f'基于实时订单簿：入场价下方最近实际买单价格${nearest_below_price:,.2f}（挂单量{nearest_below_amount:.4f} BTC）'
            }
        
        print("DEBUG: 所有方案都失败", file=sys.stderr)
        return None, None
    
    elif signal_type == 'short':
        # 做空止损：放在卖单密集区（阻力位）上方，但在流动性稀疏区
        dense_ask_zones = liquidity_analysis['dense_ask_zones']  # [(价格, 挂单量), ...]
        sparse_ask_zones = liquidity_analysis['sparse_ask_zones']
        
        # 找到入场价上方的卖单密集区（阻力位）
        resistance_zones = [(price, vol) for price, vol in dense_ask_zones if price > entry_price]
        
        if resistance_zones:
            # 找到最近的阻力位（价格最低的密集区）
            nearest_resistance_price, resistance_volume = min(resistance_zones, key=lambda x: x[0])
            
            # 在阻力位上方找流动性稀疏区（适合止损）
            sparse_above = [(price, vol) for price, vol in sparse_ask_zones 
                          if price > nearest_resistance_price]
            
            if sparse_above:
                # 选择阻力位上方最近的稀疏区作为止损
                stop_loss_price, _ = min(sparse_above, key=lambda x: x[0])
                distance = stop_loss_price - entry_price
                distance_pct = (distance / entry_price) * 100
                
                # 确保止损距离合理（min_stop_pct%-3%）
                min_stop_pct = get_min_stop_distance('low')  # 默认使用低波动率的最小止损距离
                if min_stop_pct <= distance_pct <= 3.0:
                    return stop_loss_price, {
                        'resistance_zone': nearest_resistance_price,
                        'resistance_volume': resistance_volume,
                        'sparse_zone': stop_loss_price,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'is_from_orderbook': True,
                        'source_info': f'阻力位${nearest_resistance_price:,.0f}上方稀疏区实际价格${stop_loss_price:,.0f}',
                        'reason': f'基于实时订单簿流动性分析：阻力位${nearest_resistance_price:,.0f}（挂单量{resistance_volume:.2f}），上方稀疏区${stop_loss_price:,.0f}'
                    }
            
            # 如果没有稀疏区，在阻力位上方找订单簿中的实际价格档位
            ask_zones = liquidity_analysis.get('ask_zones', {})
            above_resistance_prices = [price for price in ask_zones.keys() if price > nearest_resistance_price]
            if above_resistance_prices:
                # 使用阻力位上方最近的实际价格档位作为止损（不是百分比！）
                nearest_above_zone = min(above_resistance_prices)
                stop_loss_price = nearest_above_zone
                is_from_orderbook = True
                source_info = f'阻力位${nearest_resistance_price:,.0f}上方实际价格档位${nearest_above_zone:,.0f}'
            else:
                # 如果阻力位上方没有价格档位，使用阻力位上方0.2%-0.5%（非订单簿）
                if resistance_volume > liquidity_analysis['ask_zones'].get(nearest_resistance_price, 0) * 2:
                    stop_loss_price = nearest_resistance_price * 1.002  # 上方0.2%
                else:
                    stop_loss_price = nearest_resistance_price * 1.005  # 上方0.5%
                is_from_orderbook = False
                source_info = f'备用方案：阻力位${nearest_resistance_price:,.0f}上方0.2%-0.5%（非订单簿实际价格）'
            
            distance = stop_loss_price - entry_price
            distance_pct = (distance / entry_price) * 100
            
            if distance_pct <= 3.0:
                return stop_loss_price, {
                    'resistance_zone': nearest_resistance_price,
                    'resistance_volume': resistance_volume,
                    'distance': distance,
                    'distance_pct': distance_pct,
                    'is_from_orderbook': is_from_orderbook,
                    'source_info': source_info,
                    'reason': f'基于实时订单簿流动性分析：阻力位${nearest_resistance_price:,.0f}（挂单量{resistance_volume:.2f}）上方，{source_info}'
                }
        
        # 如果没有找到密集区，基于订单簿原始数据找关键价位
        above_entry = [(price, amount) for price, amount in asks if price > entry_price]
        
        # 如果入场价上方没有卖单（入场价超出订单簿范围），使用当前价格附近的订单簿数据
        if not above_entry:
            # 找到当前价格上方的卖单（作为参考）
            above_current = [(price, amount) for price, amount in asks if price > current_price]
            if above_current and len(above_current) > 0:
                # 找到挂单量最大的作为阻力位
                above_current.sort(key=lambda x: x[1], reverse=True)
                top_resistances = sorted([x for x in above_current[:3]], key=lambda x: x[0])
                if top_resistances:
                    resistance_price, resistance_amount = top_resistances[0]
                    # 计算入场价相对于当前价格的偏移
                    price_offset = entry_price - current_price
                    # 在阻力位上方，加上相同的偏移量
                    estimated_stop_loss = resistance_price + price_offset
                    # 确保止损在入场价上方，且至少min_stop_pct%
                    min_stop_pct = get_min_stop_distance('low')  # 默认使用低波动率的最小止损距离
                    distance = estimated_stop_loss - entry_price
                    distance_pct = (distance / entry_price) * 100
                    
                    # 如果距离太近，调整到至少min_stop_pct%
                    if distance_pct < min_stop_pct:
                        estimated_stop_loss = entry_price * (1 + min_stop_pct / 100)  # 至少min_stop_pct%
                        distance = estimated_stop_loss - entry_price
                        distance_pct = (distance / entry_price) * 100
                    
                    # 如果距离太远，调整到最多3%
                    if distance_pct > 3.0:
                        estimated_stop_loss = entry_price * 1.03  # 最多3%
                        distance = estimated_stop_loss - entry_price
                        distance_pct = (distance / entry_price) * 100
                    
                    # 无论距离是否在范围内，都返回（已经调整到合理范围）
                    return estimated_stop_loss, {
                        'resistance_zone': resistance_price,
                        'resistance_volume': resistance_amount,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'is_from_orderbook': False,  # 这是估算值
                        'source_info': f'基于当前价格附近阻力位${resistance_price:,.0f}估算（入场价超出订单簿范围）',
                        'reason': f'入场价${entry_price:,.0f}超出订单簿范围，基于当前价格附近阻力位${resistance_price:,.0f}（挂单量{resistance_amount:.4f} BTC）估算止损'
                    }
        
        if above_entry:
            # 按挂单量排序，找挂单量大的价位作为阻力
            above_entry.sort(key=lambda x: x[1], reverse=True)
            top_resistances = sorted([x for x in above_entry[:3]], key=lambda x: x[0])
            if top_resistances:
                resistance_price, resistance_amount = top_resistances[0]
                # 在阻力位上方找订单簿中的实际价格档位
                ask_zones = {}
                for price, amount in asks:
                    rounded = round(price / 100) * 100
                    if rounded not in ask_zones:
                        ask_zones[rounded] = 0
                    ask_zones[rounded] += amount
                
                above_resistance = [price for price in ask_zones.keys() if price > resistance_price]
                if above_resistance:
                    # 使用阻力位上方最近的实际价格档位作为止损（不是百分比！）
                    nearest_above_zone = min(above_resistance)
                    stop_loss_price = nearest_above_zone
                    is_from_orderbook = True
                    source_info = f'阻力位${resistance_price:,.0f}上方实际价格档位${nearest_above_zone:,.0f}'
                else:
                    # 如果阻力位上方没有价格档位，使用阻力位上方min_stop_pct%（非订单簿）
                    min_stop_pct = get_min_stop_distance('low')  # 默认使用低波动率的最小止损距离
                    stop_loss_price = resistance_price * (1 + min_stop_pct / 100)  # 阻力位上方min_stop_pct%
                    is_from_orderbook = False
                    source_info = f'备用方案：阻力位${resistance_price:,.0f}上方{min_stop_pct:.2f}%（非订单簿实际价格）'
                
                distance = stop_loss_price - entry_price
                distance_pct = (distance / entry_price) * 100
                
                min_stop_pct = get_min_stop_distance('low')  # 默认使用低波动率的最小止损距离
                if min_stop_pct <= distance_pct <= 3.0:
                    return stop_loss_price, {
                        'resistance_zone': resistance_price,
                        'resistance_volume': resistance_amount,
                        'distance': distance,
                        'distance_pct': distance_pct,
                        'is_from_orderbook': is_from_orderbook,
                        'source_info': source_info,
                        'reason': f'基于实时订单簿：入场价上方最大挂单量${resistance_price:,.0f}（挂单量{resistance_amount:.4f}）上方，{source_info}'
                    }
    
    return None, None

def print_stop_loss_result(symbol, signal_type, entry_price, stop_loss, info, exchange_name, current_price):
    """打印止损结果"""
    print("\n" + "="*70)
    print(f"【实时订单簿止损建议】")
    print("="*70)
    print(f"币种: {symbol.upper()}")
    print(f"方向: {'做多' if signal_type == 'long' else '做空'}")
    print(f"入场价: ${entry_price:,.2f}")
    print(f"当前价格: ${current_price:,.2f}")
    print(f"数据来源: {exchange_name}")
    print()
    
    if stop_loss and info:
        # 明确标注是否基于订单簿
        is_from_orderbook = info.get('is_from_orderbook', True)
        orderbook_status = "[基于订单簿实际价格]" if is_from_orderbook else "[非订单簿实际价格-备用方案]"
        
        print(f"[OK] **建议止损价**: ${stop_loss:,.2f}")
        print(f"   {orderbook_status}")
        print(f"   止损距离: {info['distance']:.0f}点（{info['distance_pct']:.2f}%）")
        print(f"   止损理由: {info['reason']}")
        
        # 显示来源信息
        if 'source_info' in info:
            print(f"   价格来源: {info['source_info']}")
        
        if 'support_zone' in info:
            print(f"   支撑位: ${info['support_zone']:,.2f}")
        elif 'resistance_zone' in info:
            print(f"   阻力位: ${info['resistance_zone']:,.2f}")
        
        if 'sparse_zone' in info:
            print(f"   稀疏区: ${info['sparse_zone']:,.2f}")
            if 'sparse_volume' in info:
                print(f"   稀疏区挂单量: {info['sparse_volume']:.4f} BTC")
    else:
        print("[X] 无法基于订单簿计算止损，建议手动观察订单簿设置")
    
    print()
    print("="*70)
    print()

def main():
    """主函数"""
    if len(sys.argv) < 3:
        print("\n" + "="*70)
        print("实时订单簿止损查询工具")
        print("="*70)
        print("\n用法:")
        print("  python get_realtime_stop_loss.py <币种> <方向> sl [入场价]")
        print("\n示例:")
        print("  python get_realtime_stop_loss.py BTC long sl")
        print("  python get_realtime_stop_loss.py BTC long sl 86000")
        print("  python get_realtime_stop_loss.py BTC short sl 90000")
        print("  python get_realtime_stop_loss.py ETH long sl 2500")
        print("\n参数说明:")
        print("  <币种>: BTC, ETH, BNB 等")
        print("  <方向>: long (做多) 或 short (做空)")
        print("  sl: 止损查询标识（固定）")
        print("  [入场价]: 可选，如果不提供则使用当前价格")
        print("\n" + "="*70)
        return
    
    symbol = sys.argv[1].upper()
    signal_type = sys.argv[2].lower()
    command = sys.argv[3].lower() if len(sys.argv) > 3 else ''
    
    if signal_type not in ['long', 'short']:
        print(f"[X] 错误：方向必须是 'long' 或 'short'，当前为 '{signal_type}'")
        return
    
    if command != 'sl':
        print(f"[X] 错误：命令必须是 'sl'，当前为 '{command}'")
        return
    
    # 获取入场价（如果提供）
    entry_price = None
    if len(sys.argv) > 4:
        try:
            entry_price = float(sys.argv[4])
        except:
            print(f"[X] 错误：入场价格式不正确: {sys.argv[4]}")
            return
    
    # 获取当前价格
    print(f"正在获取{symbol}当前价格...", file=sys.stderr)
    current_price = get_current_price(symbol)
    if not current_price:
        print("[X] 无法获取当前价格")
        return
    
    # 如果没有提供入场价，使用当前价格
    if not entry_price:
        entry_price = current_price
    
    # 获取实时订单簿
    print(f"正在获取{symbol}实时订单簿...", file=sys.stderr)
    order_book, exchange_name = get_order_book_with_retry(symbol, limit=50)
    
    if not order_book:
        print("[X] 无法获取实时订单簿数据")
        return
    
    # 计算止损
    stop_loss, info = calculate_stop_loss_by_orderbook(
        entry_price, signal_type, order_book, current_price
    )
    
    # 打印结果
    print_stop_loss_result(symbol, signal_type, entry_price, stop_loss, info, exchange_name, current_price)

if __name__ == '__main__':
    main()

