#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实时订单簿流动性分析工具
根据De.交易系统的实时流动性止损理念，分析订单簿并给出止损建议
"""

import requests
import sys
from datetime import datetime

def get_order_book_gateio(symbol='BTC_USDT', limit=50):
    """从Gate.io获取订单簿数据"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/order_book"
        params = {
            'currency_pair': symbol,
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

def get_order_book_bitget(symbol='BTCUSDT', limit=50):
    """从Bitget获取订单簿数据（备用）"""
    try:
        url = "https://api.bitget.com/api/spot/v1/market/depth"
        params = {
            'symbol': symbol,
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

def get_current_price(symbol='BTC_USDT'):
    """获取当前价格"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': symbol}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['last'])
    except:
        pass
    return None

def analyze_liquidity_zones(order_book, current_price):
    """分析订单簿，识别流动性区域"""
    if not order_book:
        return None
    
    bids = order_book['bids']  # 买单 [(价格, 数量), ...]
    asks = order_book['asks']  # 卖单 [(价格, 数量), ...]
    
    # 计算每个价格档位的总挂单量（按百位四舍五入）
    bid_zones = {}  # {价格: 总挂单量}
    ask_zones = {}  # {价格: 总挂单量}
    
    # 分析买单（支撑位）
    for price, amount in bids:
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
    
    # 计算平均挂单量
    avg_bid_volume = sum(bid_zones.values()) / len(bid_zones) if bid_zones else 0
    avg_ask_volume = sum(ask_zones.values()) / len(ask_zones) if ask_zones else 0
    
    # 识别流动性密集区（挂单量 > 平均值的1.5倍）
    dense_bid_zones = [(price, vol) for price, vol in bid_zones.items() if vol > avg_bid_volume * 1.5]
    dense_ask_zones = [(price, vol) for price, vol in ask_zones.items() if vol > avg_ask_volume * 1.5]
    
    # 识别流动性稀疏区（挂单量 < 平均值的0.5倍）
    sparse_bid_zones = [(price, vol) for price, vol in bid_zones.items() if vol < avg_bid_volume * 0.5]
    sparse_ask_zones = [(price, vol) for price, vol in ask_zones.items() if vol < avg_ask_volume * 0.5]
    
    # 按价格排序
    dense_bid_zones.sort(key=lambda x: x[0], reverse=True)
    dense_ask_zones.sort(key=lambda x: x[0])
    sparse_bid_zones.sort(key=lambda x: x[0], reverse=True)
    sparse_ask_zones.sort(key=lambda x: x[0])
    
    return {
        'bid_zones': bid_zones,
        'ask_zones': ask_zones,
        'dense_bid_zones': dense_bid_zones,  # [(价格, 挂单量), ...]
        'dense_ask_zones': dense_ask_zones,
        'sparse_bid_zones': sparse_bid_zones,
        'sparse_ask_zones': sparse_ask_zones,
        'current_price': current_price,
        'avg_bid_volume': avg_bid_volume,
        'avg_ask_volume': avg_ask_volume
    }

def suggest_stop_loss(entry_price, signal_type, liquidity_analysis):
    """根据流动性分析给出止损建议"""
    if not liquidity_analysis:
        return None, None
    
    if signal_type == 'long':
        # 做多止损：放在买单密集区下方，但在流动性稀疏区
        dense_bid_zones = liquidity_analysis['dense_bid_zones']
        sparse_bid_zones = liquidity_analysis['sparse_bid_zones']
        
        # 找到入场价下方的买单密集区
        support_zones = [(price, vol) for price, vol in dense_bid_zones if price < entry_price]
        
        if support_zones:
            nearest_support, support_vol = max(support_zones, key=lambda x: x[0])  # 最近的支撑位
            # 在支撑位下方找流动性稀疏区
            sparse_below = [(price, vol) for price, vol in sparse_bid_zones if price < nearest_support]
            
            if sparse_below:
                # 选择支撑位下方最近的稀疏区
                stop_loss, _ = max(sparse_below, key=lambda x: x[0])
                return stop_loss, {
                    'stop_loss': stop_loss,
                    'distance': entry_price - stop_loss,
                    'distance_pct': ((entry_price - stop_loss) / entry_price) * 100,
                    'reason': f'买单密集区在${nearest_support:,.0f}（挂单量{support_vol:.2f}），止损放在流动性稀疏区${stop_loss:,.0f}',
                    'support_zone': nearest_support,
                    'support_volume': support_vol
                }
            else:
                # 如果没有稀疏区，放在支撑位下方1-2%
                stop_loss = nearest_support * 0.98
                return stop_loss, {
                    'stop_loss': stop_loss,
                    'distance': entry_price - stop_loss,
                    'distance_pct': ((entry_price - stop_loss) / entry_price) * 100,
                    'reason': f'买单密集区在${nearest_support:,.0f}，止损放在${stop_loss:,.0f}（支撑位下方2%）',
                    'support_zone': nearest_support
                }
        else:
            # 如果没有明显的支撑位，使用默认止损
            stop_loss = entry_price * 0.985  # 默认1.5%
            return stop_loss, {
                'stop_loss': stop_loss,
                'distance': entry_price - stop_loss,
                'distance_pct': 1.5,
                'reason': '未发现明显的买单密集区，使用默认止损（入场价下方1.5%）',
                'support_zone': None
            }
    else:  # short
        # 做空止损：放在卖单密集区上方，但在流动性稀疏区
        dense_ask_zones = liquidity_analysis['dense_ask_zones']
        sparse_ask_zones = liquidity_analysis['sparse_ask_zones']
        
        # 找到入场价上方的卖单密集区
        resistance_zones = [(price, vol) for price, vol in dense_ask_zones if price > entry_price]
        
        if resistance_zones:
            nearest_resistance, resistance_vol = min(resistance_zones, key=lambda x: x[0])  # 最近的阻力位
            # 在阻力位上方找流动性稀疏区
            sparse_above = [(price, vol) for price, vol in sparse_ask_zones if price > nearest_resistance]
            
            if sparse_above:
                # 选择阻力位上方最近的稀疏区
                stop_loss, _ = min(sparse_above, key=lambda x: x[0])
                return stop_loss, {
                    'stop_loss': stop_loss,
                    'distance': stop_loss - entry_price,
                    'distance_pct': ((stop_loss - entry_price) / entry_price) * 100,
                    'reason': f'卖单密集区在${nearest_resistance:,.0f}（挂单量{resistance_vol:.2f}），止损放在流动性稀疏区${stop_loss:,.0f}',
                    'resistance_zone': nearest_resistance,
                    'resistance_volume': resistance_vol
                }
            else:
                # 如果没有稀疏区，放在阻力位上方1-2%
                stop_loss = nearest_resistance * 1.02
                return stop_loss, {
                    'stop_loss': stop_loss,
                    'distance': stop_loss - entry_price,
                    'distance_pct': ((stop_loss - entry_price) / entry_price) * 100,
                    'reason': f'卖单密集区在${nearest_resistance:,.0f}，止损放在${stop_loss:,.0f}（阻力位上方2%）',
                    'resistance_zone': nearest_resistance
                }
        else:
            # 如果没有明显的阻力位，使用默认止损
            stop_loss = entry_price * 1.015  # 默认1.5%
            return stop_loss, {
                'stop_loss': stop_loss,
                'distance': stop_loss - entry_price,
                'distance_pct': 1.5,
                'reason': '未发现明显的卖单密集区，使用默认止损（入场价上方1.5%）',
                'resistance_zone': None
            }

def print_liquidity_analysis(liquidity_analysis, entry_price=None, signal_type=None):
    """打印流动性分析结果"""
    if not liquidity_analysis:
        print("❌ 无法获取订单簿数据")
        return
    
    current_price = liquidity_analysis['current_price']
    print(f"\n{'='*60}")
    print(f"[实时订单簿流动性分析]")
    print(f"{'='*60}")
    print(f"当前价格: ${current_price:,.2f}")
    print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 买单密集区（支撑位）
    print("[买单密集区（支撑位）]：")
    dense_bids = liquidity_analysis['dense_bid_zones'][:10]
    if dense_bids:
        for price, vol in dense_bids:
            distance = current_price - price
            distance_pct = (distance / current_price) * 100
            print(f"  ${price:>10,.0f} | 挂单量: {vol:>10.2f} | 距离: {distance:>8.0f}点 ({distance_pct:>5.2f}%)")
    else:
        print("  未发现明显的买单密集区")
    print()
    
    # 卖单密集区（阻力位）
    print("[卖单密集区（阻力位）]：")
    dense_asks = liquidity_analysis['dense_ask_zones'][:10]
    if dense_asks:
        for price, vol in dense_asks:
            distance = price - current_price
            distance_pct = (distance / current_price) * 100
            print(f"  ${price:>10,.0f} | 挂单量: {vol:>10.2f} | 距离: {distance:>8.0f}点 ({distance_pct:>5.2f}%)")
    else:
        print("  未发现明显的卖单密集区")
    print()
    
    # 买单稀疏区（适合止损）
    print("[买单稀疏区（适合做多止损）]：")
    sparse_bids = liquidity_analysis['sparse_bid_zones'][:10]
    if sparse_bids:
        for price, vol in sparse_bids:
            distance = current_price - price
            distance_pct = (distance / current_price) * 100
            print(f"  ${price:>10,.0f} | 挂单量: {vol:>10.2f} | 距离: {distance:>8.0f}点 ({distance_pct:>5.2f}%)")
    else:
        print("  未发现明显的买单稀疏区")
    print()
    
    # 卖单稀疏区（适合止损）
    print("[卖单稀疏区（适合做空止损）]：")
    sparse_asks = liquidity_analysis['sparse_ask_zones'][:10]
    if sparse_asks:
        for price, vol in sparse_asks:
            distance = price - current_price
            distance_pct = (distance / current_price) * 100
            print(f"  ${price:>10,.0f} | 挂单量: {vol:>10.2f} | 距离: {distance:>8.0f}点 ({distance_pct:>5.2f}%)")
    else:
        print("  未发现明显的卖单稀疏区")
    print()
    
    # 如果提供了入场价和信号类型，给出止损建议
    if entry_price and signal_type:
        print(f"{'='*60}")
        print(f"[止损建议（基于实时流动性）]")
        print(f"{'='*60}")
        print(f"入场价: ${entry_price:,.2f}")
        print(f"信号类型: {'做多' if signal_type == 'long' else '做空'}")
        print()
        
        stop_loss, info = suggest_stop_loss(entry_price, signal_type, liquidity_analysis)
        if stop_loss and info:
            print(f"[建议止损]: ${stop_loss:,.2f}")
            print(f"   止损距离: {info['distance']:.0f}点（{info['distance_pct']:.2f}%）")
            print(f"   止损理由: {info['reason']}")
            if signal_type == 'long' and info.get('support_zone'):
                print(f"   支撑位: ${info['support_zone']:,.0f}")
            elif signal_type == 'short' and info.get('resistance_zone'):
                print(f"   阻力位: ${info['resistance_zone']:,.0f}")
        else:
            print("[X] 无法给出止损建议")
        print()
        print("[重要提醒]：")
        print("- De.的原话：\"我止损都是实时流动性，没有规则\"")
        print("- 此建议仅供参考，实际止损应基于实时订单簿观察")
        print("- 订单簿随时变化，需要实时监控和调整")
        print()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='实时订单簿流动性分析工具')
    parser.add_argument('--symbol', type=str, default='BTC_USDT', help='交易对（默认：BTC_USDT）')
    parser.add_argument('--entry', type=float, help='入场价（可选，用于计算止损）')
    parser.add_argument('--type', type=str, choices=['long', 'short'], help='信号类型：long（做多）或 short（做空）')
    parser.add_argument('--limit', type=int, default=50, help='订单簿深度（默认：50）')
    
    args = parser.parse_args()
    
    # 获取当前价格
    current_price = get_current_price(args.symbol)
    if not current_price:
        print("[X] 无法获取当前价格")
        return
    
    # 获取订单簿
    print("正在获取实时订单簿数据...")
    order_book = get_order_book_gateio(args.symbol, args.limit)
    if not order_book:
        print("Gate.io获取失败，尝试Bitget...")
        symbol_bitget = args.symbol.replace('_', '')
        order_book = get_order_book_bitget(symbol_bitget, args.limit)
    
    if not order_book:
        print("[X] 无法获取订单簿数据")
        return
    
    # 分析流动性
    liquidity_analysis = analyze_liquidity_zones(order_book, current_price)
    
    # 打印分析结果
    print_liquidity_analysis(liquidity_analysis, args.entry, args.type)

if __name__ == '__main__':
    main()

