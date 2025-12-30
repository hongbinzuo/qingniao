#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主力资金流入流出分析工具
通过多种方式分析币种的主力资金流向
"""

import requests
import sys
import time
from datetime import datetime, timedelta
from collections import defaultdict

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def get_trades_gateio(symbol='BTC', limit=100):
    """从Gate.io获取最近交易数据（包含大单）"""
    try:
        pair = f'{symbol}_USDT'
        url = "https://api.gateio.ws/api/v4/spot/trades"
        params = {
            'currency_pair': pair,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            trades = []
            for trade in data:
                trades.append({
                    'id': trade.get('id', ''),
                    'price': float(trade.get('price', 0)),
                    'amount': float(trade.get('amount', 0)),
                    'total': float(trade.get('price', 0)) * float(trade.get('amount', 0)),
                    'side': trade.get('side', ''),  # 'buy' or 'sell'
                    'timestamp': int(trade.get('create_time', 0)),
                    'exchange': 'Gate.io'
                })
            return trades
    except Exception as e:
        pass
    return None

def get_trades_binance(symbol='BTC', limit=100):
    """从Binance获取最近交易数据"""
    try:
        symbol_map = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'BNB': 'BNBUSDT'
        }
        symbol_str = symbol_map.get(symbol, f'{symbol}USDT')
        
        url = "https://api.binance.com/api/v3/trades"
        params = {
            'symbol': symbol_str,
            'limit': min(limit, 1000)
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            trades = []
            for trade in data:
                # Binance返回的是最新交易，isBuyerMaker表示maker是买方
                # 如果isBuyerMaker=True，说明是卖单（卖方是maker）
                # 如果isBuyerMaker=False，说明是买单（买方是maker）
                is_buyer_maker = trade.get('isBuyerMaker', False)
                side = 'sell' if is_buyer_maker else 'buy'
                
                trades.append({
                    'id': trade.get('id', ''),
                    'price': float(trade.get('price', 0)),
                    'amount': float(trade.get('qty', 0)),
                    'total': float(trade.get('price', 0)) * float(trade.get('qty', 0)),
                    'side': side,
                    'timestamp': int(trade.get('time', 0)) // 1000,  # Binance返回毫秒
                    'exchange': 'Binance'
                })
            return trades
    except Exception as e:
        pass
    return None

def get_trades_coinbase(symbol='BTC', limit=100):
    """从Coinbase获取最近交易数据"""
    try:
        symbol_map = {
            'BTC': 'BTC-USD',
            'ETH': 'ETH-USD',
            'BNB': 'BNB-USD'
        }
        symbol_str = symbol_map.get(symbol, f'{symbol}-USD')
        
        url = f"https://api.exchange.coinbase.com/products/{symbol_str}/trades"
        params = {
            'limit': min(limit, 100)
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            trades = []
            for trade in data:
                # Coinbase格式: [time, trade_id, price, size, side]
                # side: 'buy' or 'sell'
                trades.append({
                    'id': trade[1] if len(trade) > 1 else '',
                    'price': float(trade[2]) if len(trade) > 2 else 0,
                    'amount': float(trade[3]) if len(trade) > 3 else 0,
                    'total': float(trade[2]) * float(trade[3]) if len(trade) > 3 else 0,
                    'side': trade[4].lower() if len(trade) > 4 else 'unknown',
                    'timestamp': trade[0] if len(trade) > 0 else 0,
                    'exchange': 'Coinbase'
                })
            return trades
    except Exception as e:
        pass
    return None

def get_all_exchanges_trades(symbol='BTC', limit_per_exchange=200):
    """从多个交易所获取交易数据"""
    all_trades = []
    
    # Gate.io
    print("  获取Gate.io数据...", end=' ')
    gate_trades = get_trades_gateio(symbol, limit_per_exchange)
    if gate_trades:
        all_trades.extend(gate_trades)
        print(f"✓ {len(gate_trades)}笔")
    else:
        print("✗")
    
    # Binance
    print("  获取Binance数据...", end=' ')
    binance_trades = get_trades_binance(symbol, limit_per_exchange)
    if binance_trades:
        all_trades.extend(binance_trades)
        print(f"✓ {len(binance_trades)}笔")
    else:
        print("✗")
    
    # Coinbase
    print("  获取Coinbase数据...", end=' ')
    coinbase_trades = get_trades_coinbase(symbol, limit_per_exchange)
    if coinbase_trades:
        all_trades.extend(coinbase_trades)
        print(f"✓ {len(coinbase_trades)}笔")
    else:
        print("✗")
    
    # 按时间排序
    all_trades.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return all_trades

def get_orderbook_gateio(symbol='BTC', limit=100):
    """从Gate.io获取订单簿数据"""
    try:
        pair = f'{symbol}_USDT'
        url = "https://api.gateio.ws/api/v4/spot/order_book"
        params = {
            'currency_pair': pair,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            bids = [(float(b[0]), float(b[1])) for b in data.get('bids', [])]
            asks = [(float(a[0]), float(a[1])) for a in data.get('asks', [])]
            return {'bids': bids, 'asks': asks, 'exchange': 'Gate.io'}
    except Exception as e:
        pass
    return None

def get_orderbook_binance(symbol='BTC', limit=100):
    """从Binance获取订单簿数据"""
    try:
        symbol_map = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'BNB': 'BNBUSDT'
        }
        symbol_str = symbol_map.get(symbol, f'{symbol}USDT')
        
        url = "https://api.binance.com/api/v3/depth"
        params = {
            'symbol': symbol_str,
            'limit': min(limit, 100)
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            bids = [(float(b[0]), float(b[1])) for b in data.get('bids', [])]
            asks = [(float(a[0]), float(a[1])) for a in data.get('asks', [])]
            return {'bids': bids, 'asks': asks, 'exchange': 'Binance'}
    except Exception as e:
        pass
    return None

def get_orderbook_coinbase(symbol='BTC', limit=100):
    """从Coinbase获取订单簿数据"""
    try:
        symbol_map = {
            'BTC': 'BTC-USD',
            'ETH': 'ETH-USD',
            'BNB': 'BNB-USD'
        }
        symbol_str = symbol_map.get(symbol, f'{symbol}-USD')
        
        url = f"https://api.exchange.coinbase.com/products/{symbol_str}/book"
        params = {
            'level': 2  # level 2 返回完整的订单簿
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            bids = [(float(b[0]), float(b[1])) for b in data.get('bids', [])[:limit]]
            asks = [(float(a[0]), float(a[1])) for a in data.get('asks', [])[:limit]]
            return {'bids': bids, 'asks': asks, 'exchange': 'Coinbase'}
    except Exception as e:
        pass
    return None

def get_all_exchanges_orderbook(symbol='BTC', limit=100):
    """从多个交易所获取订单簿数据"""
    orderbooks = {}
    
    # Gate.io
    print("  获取Gate.io订单簿...", end=' ')
    gate_ob = get_orderbook_gateio(symbol, limit)
    if gate_ob:
        orderbooks['Gate.io'] = gate_ob
        print("✓")
    else:
        print("✗")
    
    # Binance
    print("  获取Binance订单簿...", end=' ')
    binance_ob = get_orderbook_binance(symbol, limit)
    if binance_ob:
        orderbooks['Binance'] = binance_ob
        print("✓")
    else:
        print("✗")
    
    # Coinbase
    print("  获取Coinbase订单簿...", end=' ')
    coinbase_ob = get_orderbook_coinbase(symbol, limit)
    if coinbase_ob:
        orderbooks['Coinbase'] = coinbase_ob
        print("✓")
    else:
        print("✗")
    
    return orderbooks

def get_ticker_gateio(symbol='BTC'):
    """获取当前价格和24h数据"""
    try:
        pair = f'{symbol}_USDT'
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': pair}
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                ticker = data[0]
                return {
                    'last': float(ticker.get('last', 0)),
                    'volume_24h': float(ticker.get('quote_volume', 0)),
                    'change_24h': float(ticker.get('change_percentage', 0)),
                    'high_24h': float(ticker.get('high_24h', 0)),
                    'low_24h': float(ticker.get('low_24h', 0))
                }
    except Exception as e:
        pass
    return None

def analyze_large_orders(trades, current_price, threshold_percent=1.0):
    """分析大单交易（支持多交易所）"""
    if not trades:
        return None
    
    # 按交易所分组
    trades_by_exchange = {}
    for trade in trades:
        exchange = trade.get('exchange', 'Unknown')
        if exchange not in trades_by_exchange:
            trades_by_exchange[exchange] = []
        trades_by_exchange[exchange].append(trade)
    
    # 计算平均交易金额
    all_amounts = [t['total'] for t in trades]
    avg_amount = sum(all_amounts) / len(all_amounts) if all_amounts else 0
    
    # 大单阈值（超过平均值的N倍）
    large_order_threshold = avg_amount * 5  # 5倍平均值
    
    large_buys = []
    large_sells = []
    exchange_stats = {}
    
    # 按交易所分析
    for exchange, exchange_trades in trades_by_exchange.items():
        exchange_large_buys = []
        exchange_large_sells = []
        
        for trade in exchange_trades:
            if trade['total'] >= large_order_threshold:
                if trade['side'] == 'buy':
                    exchange_large_buys.append(trade)
                    large_buys.append(trade)
                else:
                    exchange_large_sells.append(trade)
                    large_sells.append(trade)
        
        exchange_stats[exchange] = {
            'total_trades': len(exchange_trades),
            'large_buy_count': len(exchange_large_buys),
            'large_sell_count': len(exchange_large_sells),
            'total_large_buy': sum(t['total'] for t in exchange_large_buys),
            'total_large_sell': sum(t['total'] for t in exchange_large_sells),
            'net_flow': sum(t['total'] for t in exchange_large_buys) - sum(t['total'] for t in exchange_large_sells)
        }
    
    # 计算总体大单统计
    total_large_buy = sum(t['total'] for t in large_buys)
    total_large_sell = sum(t['total'] for t in large_sells)
    net_flow = total_large_buy - total_large_sell
    
    return {
        'large_buy_count': len(large_buys),
        'large_sell_count': len(large_sells),
        'total_large_buy': total_large_buy,
        'total_large_sell': total_large_sell,
        'net_flow': net_flow,
        'net_flow_percent': (net_flow / (total_large_buy + total_large_sell) * 100) if (total_large_buy + total_large_sell) > 0 else 0,
        'large_buys': sorted(large_buys, key=lambda x: x['total'], reverse=True)[:10],
        'large_sells': sorted(large_sells, key=lambda x: x['total'], reverse=True)[:10],
        'threshold': large_order_threshold,
        'exchange_stats': exchange_stats
    }

def analyze_orderbook_pressure(orderbooks, current_price):
    """分析订单簿压力（买卖盘对比，支持多交易所）"""
    if not orderbooks:
        return None
    
    all_results = {}
    combined_bid_value = 0
    combined_ask_value = 0
    
    for exchange, orderbook in orderbooks.items():
        bids = orderbook['bids']
        asks = orderbook['asks']
        
        # 计算买卖盘总量（价格在±2%范围内）
        price_range = current_price * 0.02
        
        bid_volume = sum(amount for price, amount in bids if current_price - price_range <= price <= current_price)
        ask_volume = sum(amount for price, amount in asks if current_price <= price <= current_price + price_range)
        
        # 计算买卖盘金额
        bid_value = sum(price * amount for price, amount in bids if current_price - price_range <= price <= current_price)
        ask_value = sum(price * amount for price, amount in asks if current_price <= price <= current_price + price_range)
        
        combined_bid_value += bid_value
        combined_ask_value += ask_value
        
        # 计算压力比
        pressure_ratio = bid_value / ask_value if ask_value > 0 else 0
        
        # 识别大单挂单（超过平均值的5倍）
        if bids:
            avg_bid = sum(amount for _, amount in bids) / len(bids)
            large_bids = [(p, a) for p, a in bids if a >= avg_bid * 5]
        else:
            large_bids = []
        
        if asks:
            avg_ask = sum(amount for _, amount in asks) / len(asks)
            large_asks = [(p, a) for p, a in asks if a >= avg_ask * 5]
        else:
            large_asks = []
        
        all_results[exchange] = {
            'bid_volume': bid_volume,
            'ask_volume': ask_volume,
            'bid_value': bid_value,
            'ask_value': ask_value,
            'pressure_ratio': pressure_ratio,
            'pressure_signal': 'buy_pressure' if pressure_ratio > 1.5 else 'sell_pressure' if pressure_ratio < 0.67 else 'neutral',
            'large_bids': large_bids[:5],
            'large_asks': large_asks[:5]
        }
    
    # 计算综合压力比
    combined_pressure_ratio = combined_bid_value / combined_ask_value if combined_ask_value > 0 else 0
    
    return {
        'exchanges': all_results,
        'combined_bid_value': combined_bid_value,
        'combined_ask_value': combined_ask_value,
        'combined_pressure_ratio': combined_pressure_ratio,
        'combined_pressure_signal': 'buy_pressure' if combined_pressure_ratio > 1.5 else 'sell_pressure' if combined_pressure_ratio < 0.67 else 'neutral'
    }

def get_volume_profile(trades, time_window_minutes=60):
    """分析成交量分布（识别异常成交量）"""
    if not trades:
        return None
    
    # 按时间窗口分组
    now = datetime.now()
    time_windows = defaultdict(lambda: {'buy': 0, 'sell': 0, 'count': 0})
    
    for trade in trades:
        trade_time = datetime.fromtimestamp(trade['timestamp'])
        minutes_ago = (now - trade_time).total_seconds() / 60
        
        if minutes_ago <= time_window_minutes:
            window = int(minutes_ago / 10)  # 每10分钟一个窗口
            if trade['side'] == 'buy':
                time_windows[window]['buy'] += trade['total']
            else:
                time_windows[window]['sell'] += trade['total']
            time_windows[window]['count'] += 1
    
    # 计算平均成交量
    if time_windows:
        avg_volume = sum(w['buy'] + w['sell'] for w in time_windows.values()) / len(time_windows)
        recent_volume = sum(w['buy'] + w['sell'] for w in list(time_windows.values())[-3:])  # 最近30分钟
        
        return {
            'avg_volume': avg_volume,
            'recent_volume': recent_volume,
            'volume_ratio': recent_volume / avg_volume if avg_volume > 0 else 0,
            'is_abnormal': recent_volume > avg_volume * 2,  # 最近成交量超过平均2倍
            'time_windows': dict(time_windows)
        }
    
    return None

def analyze_capital_flow(symbol='BTC'):
    """综合分析主力资金流向"""
    print(f"正在分析 {symbol} 的主力资金流向...")
    print()
    
    # 获取数据
    print("1. 获取多交易所交易数据...")
    trades = get_all_exchanges_trades(symbol, limit_per_exchange=200)
    if not trades:
        print("✗ 无法获取交易数据")
        return None
    
    print(f"✓ 总共获取到 {len(trades)} 笔交易")
    
    print("2. 获取多交易所订单簿数据...")
    orderbooks = get_all_exchanges_orderbook(symbol, limit=100)
    if not orderbooks:
        print("✗ 无法获取订单簿数据")
    else:
        print(f"✓ 获取到 {len(orderbooks)} 个交易所的订单簿数据")
    
    print("3. 获取价格数据...")
    ticker = get_ticker_gateio(symbol)
    if not ticker:
        print("✗ 无法获取价格数据")
        return None
    
    current_price = ticker['last']
    print(f"✓ 当前价格: ${current_price:,.2f}")
    print()
    
    # 分析大单
    print("4. 分析大单交易...")
    large_orders = analyze_large_orders(trades, current_price)
    
    # 分析订单簿压力
    print("5. 分析订单簿压力...")
    orderbook_pressure = analyze_orderbook_pressure(orderbooks, current_price) if orderbooks else None
    
    # 分析成交量分布
    print("6. 分析成交量分布...")
    volume_profile = get_volume_profile(trades, time_window_minutes=60)
    
    print()
    print("="*70)
    print(f"{symbol} 主力资金流向分析报告")
    print("="*70)
    print()
    
    print(f"【当前价格】: ${current_price:,.2f}")
    print(f"【24h涨跌幅】: {ticker['change_24h']:.2f}%")
    print(f"【24h成交量】: ${ticker['volume_24h']:,.0f}")
    print()
    
    # 大单分析
    if large_orders:
        print("【大单分析 - 综合多交易所】")
        print(f"大买单数量: {large_orders['large_buy_count']} 笔")
        print(f"大卖单数量: {large_orders['large_sell_count']} 笔")
        print(f"大买单总额: ${large_orders['total_large_buy']:,.2f}")
        print(f"大卖单总额: ${large_orders['total_large_sell']:,.2f}")
        print(f"净流入: ${large_orders['net_flow']:,.2f}")
        print(f"净流入占比: {large_orders['net_flow_percent']:.2f}%")
        
        if large_orders['net_flow'] > 0:
            print("📈 **主力资金净流入**")
        elif large_orders['net_flow'] < 0:
            print("📉 **主力资金净流出**")
        else:
            print("➡️ **主力资金平衡**")
        
        print()
        
        # 按交易所显示统计
        if 'exchange_stats' in large_orders:
            print("【各交易所大单统计】")
            for exchange, stats in large_orders['exchange_stats'].items():
                net_flow = stats['net_flow']
                flow_sign = "📈" if net_flow > 0 else "📉" if net_flow < 0 else "➡️"
                print(f"  {exchange}:")
                print(f"    总交易: {stats['total_trades']}笔, 大买单: {stats['large_buy_count']}笔, 大卖单: {stats['large_sell_count']}笔")
                print(f"    大买单总额: ${stats['total_large_buy']:,.2f}, 大卖单总额: ${stats['total_large_sell']:,.2f}")
                print(f"    净流入: {flow_sign} ${net_flow:,.2f}")
            print()
        
        if large_orders['large_buys']:
            print("【前5大买单（所有交易所）】")
            for i, trade in enumerate(large_orders['large_buys'][:5], 1):
                exchange = trade.get('exchange', 'Unknown')
                print(f"  {i}. [{exchange}] 价格: ${trade['price']:,.2f}, 数量: {trade['amount']:.4f}, 金额: ${trade['total']:,.2f}")
            print()
        
        if large_orders['large_sells']:
            print("【前5大卖单（所有交易所）】")
            for i, trade in enumerate(large_orders['large_sells'][:5], 1):
                exchange = trade.get('exchange', 'Unknown')
                print(f"  {i}. [{exchange}] 价格: ${trade['price']:,.2f}, 数量: {trade['amount']:.4f}, 金额: ${trade['total']:,.2f}")
            print()
    
    # 订单簿压力
    if orderbook_pressure:
        print("【订单簿压力分析 - 综合多交易所】")
        print(f"综合买盘金额: ${orderbook_pressure['combined_bid_value']:,.2f}")
        print(f"综合卖盘金额: ${orderbook_pressure['combined_ask_value']:,.2f}")
        print(f"综合压力比: {orderbook_pressure['combined_pressure_ratio']:.2f}")
        
        signal = orderbook_pressure['combined_pressure_signal']
        if signal == 'buy_pressure':
            print("📈 **综合买盘压力大，可能上涨**")
        elif signal == 'sell_pressure':
            print("📉 **综合卖盘压力大，可能下跌**")
        else:
            print("➡️ **综合买卖盘平衡**")
        
        print()
        
        # 按交易所显示
        print("【各交易所订单簿压力】")
        for exchange, result in orderbook_pressure['exchanges'].items():
            signal = result['pressure_signal']
            signal_emoji = "📈" if signal == 'buy_pressure' else "📉" if signal == 'sell_pressure' else "➡️"
            print(f"  {exchange}:")
            print(f"    买盘金额: ${result['bid_value']:,.2f}, 卖盘金额: ${result['ask_value']:,.2f}")
            print(f"    压力比: {result['pressure_ratio']:.2f} {signal_emoji} {signal}")
            
            if result['large_bids']:
                print(f"    大买单挂单: {len(result['large_bids'])}个")
            if result['large_asks']:
                print(f"    大卖单挂单: {len(result['large_asks'])}个")
        print()
    
    # 成交量分析
    if volume_profile:
        print("【成交量分析】")
        print(f"平均成交量: ${volume_profile['avg_volume']:,.2f}")
        print(f"最近成交量: ${volume_profile['recent_volume']:,.2f}")
        print(f"成交量比: {volume_profile['volume_ratio']:.2f}x")
        
        if volume_profile['is_abnormal']:
            print("⚠️ **成交量异常，可能有主力动作**")
        else:
            print("✓ 成交量正常")
        print()
    
    # 综合判断
    print("="*70)
    print("【综合判断】")
    
    signals = []
    
    if large_orders:
        if large_orders['net_flow'] > large_orders['threshold'] * 10:
            signals.append("✅ 大单净流入明显，主力可能在建仓")
        elif large_orders['net_flow'] < -large_orders['threshold'] * 10:
            signals.append("❌ 大单净流出明显，主力可能在出货")
    
    if orderbook_pressure:
        if orderbook_pressure['combined_pressure_ratio'] > 2.0:
            signals.append("✅ 综合买盘压力大，上涨概率较高")
        elif orderbook_pressure['combined_pressure_ratio'] < 0.5:
            signals.append("❌ 综合卖盘压力大，下跌概率较高")
        
        # 检查各交易所一致性
        exchange_signals = [r['pressure_signal'] for r in orderbook_pressure['exchanges'].values()]
        if len(set(exchange_signals)) == 1 and exchange_signals[0] != 'neutral':
            signals.append(f"✅ 所有交易所方向一致: {exchange_signals[0]}")
        elif len(set(exchange_signals)) > 1:
            signals.append("⚠️ 各交易所方向不一致，需谨慎")
    
    if volume_profile and volume_profile['is_abnormal']:
        signals.append("⚠️ 成交量异常，需密切关注")
    
    if signals:
        for signal in signals:
            print(f"  {signal}")
    else:
        print("  ➡️ 无明显主力资金流向信号")
    
    print()
    print("="*70)
    
    return {
        'symbol': symbol,
        'current_price': current_price,
        'ticker': ticker,
        'large_orders': large_orders,
        'orderbook_pressure': orderbook_pressure,
        'volume_profile': volume_profile,
        'signals': signals
    }

def main():
    """主函数"""
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    else:
        symbol = 'BTC'
    
    result = analyze_capital_flow(symbol)
    
    if result:
        # 保存报告
        from pathlib import Path
        Path('outputs').mkdir(exist_ok=True)
        
        filename = f"outputs/{symbol}_主力资金流向_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        md = f"""# {symbol} 主力资金流向分析报告

**生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

---

## 基本信息

- **当前价格**: ${result['current_price']:,.2f}
- **24h涨跌幅**: {result['ticker']['change_24h']:.2f}%
- **24h成交量**: ${result['ticker']['volume_24h']:,.0f}

---

## 大单分析

"""
        
        if result['large_orders']:
            lo = result['large_orders']
            md += f"""
- **大买单数量**: {lo['large_buy_count']} 笔
- **大卖单数量**: {lo['large_sell_count']} 笔
- **大买单总额**: ${lo['total_large_buy']:,.2f}
- **大卖单总额**: ${lo['total_large_sell']:,.2f}
- **净流入**: ${lo['net_flow']:,.2f}
- **净流入占比**: {lo['net_flow_percent']:.2f}%

### 各交易所大单统计

"""
            if 'exchange_stats' in lo:
                for exchange, stats in lo['exchange_stats'].items():
                    net_flow = stats['net_flow']
                    flow_sign = "📈" if net_flow > 0 else "📉" if net_flow < 0 else "➡️"
                    md += f"""
**{exchange}**:
- 总交易: {stats['total_trades']}笔
- 大买单: {stats['large_buy_count']}笔, 大卖单: {stats['large_sell_count']}笔
- 大买单总额: ${stats['total_large_buy']:,.2f}
- 大卖单总额: ${stats['total_large_sell']:,.2f}
- 净流入: {flow_sign} ${net_flow:,.2f}

"""
        
        if result['orderbook_pressure']:
            op = result['orderbook_pressure']
            md += f"""
## 订单簿压力（综合多交易所）

- **综合买盘金额**: ${op['combined_bid_value']:,.2f}
- **综合卖盘金额**: ${op['combined_ask_value']:,.2f}
- **综合压力比**: {op['combined_pressure_ratio']:.2f}
- **综合压力信号**: {op['combined_pressure_signal']}

### 各交易所详情

"""
            for exchange, ex_data in op['exchanges'].items():
                md += f"""
**{exchange}**:
- 买盘金额: ${ex_data['bid_value']:,.2f}
- 卖盘金额: ${ex_data['ask_value']:,.2f}
- 压力比: {ex_data['pressure_ratio']:.2f}
- 压力信号: {ex_data['pressure_signal']}

"""
        
        if result['volume_profile']:
            vp = result['volume_profile']
            md += f"""
## 成交量分析

- **平均成交量**: ${vp['avg_volume']:,.2f}
- **最近成交量**: ${vp['recent_volume']:,.2f}
- **成交量比**: {vp['volume_ratio']:.2f}x
- **是否异常**: {'是' if vp['is_abnormal'] else '否'}

"""
        
        md += """
## 综合判断

"""
        for signal in result['signals']:
            md += f"- {signal}\n"
        
        md += """

---

*本报告仅供参考，不构成投资建议。*

"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(md)
        
        print(f"✓ 报告已保存: {filename}")

if __name__ == '__main__':
    main()

