#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证信号评估逻辑
检查是否从信号生成时间开始正确获取和对比价格
"""

import requests
import sys
from datetime import datetime
from typing import Dict, List

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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
                    # Gate.io返回的时间戳是秒，需要转换为毫秒
                    ts = int(k[0])
                    if ts < 1e10:
                        ts = ts * 1000
                    klines.append({
                        'timestamp': ts,
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

def verify_signal_evaluation():
    """验证信号评估逻辑"""
    
    # 信号生成时间（北京时间）
    signal_time = datetime(2025, 12, 29, 10, 55, 44)
    signal_timestamp = int(signal_time.timestamp() * 1000)
    
    print("=" * 80)
    print("信号评估验证")
    print("=" * 80)
    print(f"信号生成时间（北京时间）: {signal_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"信号生成时间戳（毫秒）: {signal_timestamp}")
    print(f"信号生成时间戳（秒）: {signal_timestamp / 1000}")
    print()
    
    # 信号数据
    signals = [
        {
            'timeframe': '5m',
            'type': 'long',
            'entry': 88093,
            'stop_loss': 87800,
            'take_profit_1': 89531,
            'take_profit_2': 90250,
            'model': '反转形态-三重底',
            'strength': 'strong'
        },
        {
            'timeframe': '15m',
            'type': 'long',
            'entry': 89335,
            'stop_loss': 89067,
            'take_profit_1': 89465,
            'take_profit_2': 89600,
            'model': '区间突破',
            'strength': 'strong'
        },
        {
            'timeframe': '1h',
            'type': 'short',
            'entry': 89090,
            'stop_loss': 91054,
            'take_profit_1': 88353,
            'take_profit_2': 87461,
            'model': '阻力位回落',
            'strength': 'medium'
        }
    ]
    
    for signal in signals:
        timeframe = signal['timeframe']
        print(f"\n{'=' * 80}")
        print(f"验证信号: {timeframe} {signal['type'].upper()}")
        print(f"{'=' * 80}")
        print(f"入场: ${signal['entry']:,.2f}")
        print(f"止损: ${signal['stop_loss']:,.2f}")
        print(f"止盈1: ${signal['take_profit_1']:,.2f}")
        print(f"止盈2: ${signal['take_profit_2']:,.2f}")
        print()
        
        # 获取K线数据
        klines = get_btc_kline_gateio(timeframe, limit=200)
        if not klines:
            print(f"❌ 无法获取{timeframe}K线数据")
            continue
        
        print(f"获取到 {len(klines)} 根K线")
        print()
        
        # 找到信号时间对应的K线索引
        start_idx = 0
        min_diff = float('inf')
        for i, k in enumerate(klines):
            diff = abs(k['timestamp'] - signal_timestamp)
            if diff < min_diff:
                min_diff = diff
                start_idx = i
            if k['timestamp'] >= signal_timestamp:
                start_idx = i
                break
        
        print(f"信号生成时间: {datetime.fromtimestamp(signal_timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"开始检查的K线索引: {start_idx}")
        if start_idx < len(klines):
            first_k = klines[start_idx]
            first_k_time = datetime.fromtimestamp(first_k['timestamp']/1000)
            print(f"第一根K线时间: {first_k_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"第一根K线价格范围: ${first_k['low']:,.2f} - ${first_k['high']:,.2f}")
            print(f"时间差: {(first_k['timestamp'] - signal_timestamp) / 1000 / 60:.1f} 分钟")
        print()
        
        # 显示前10根K线的详细信息
        print("前10根K线详情（从信号生成时间开始）:")
        print("-" * 80)
        print(f"{'时间':<20} {'开盘':<12} {'最高':<12} {'最低':<12} {'收盘':<12} {'入场':<8} {'止盈1':<8} {'止损':<8}")
        print("-" * 80)
        
        for i in range(start_idx, min(start_idx + 10, len(klines))):
            k = klines[i]
            k_time = datetime.fromtimestamp(k['timestamp']/1000)
            
            # 检查是否触及各个价格
            entry_hit = "✅" if (signal['type'] == 'long' and k['low'] <= signal['entry'] * 1.001) or (signal['type'] == 'short' and k['high'] >= signal['entry'] * 0.999) else ""
            tp1_hit = "✅" if (signal['type'] == 'long' and k['high'] >= signal['take_profit_1']) or (signal['type'] == 'short' and k['low'] <= signal['take_profit_1']) else ""
            stop_hit = "❌" if (signal['type'] == 'long' and k['low'] <= signal['stop_loss']) or (signal['type'] == 'short' and k['high'] >= signal['stop_loss']) else ""
            
            print(f"{k_time.strftime('%Y-%m-%d %H:%M:%S'):<20} "
                  f"${k['open']:>10,.2f} ${k['high']:>10,.2f} ${k['low']:>10,.2f} ${k['close']:>10,.2f} "
                  f"{entry_hit:<8} {tp1_hit:<8} {stop_hit:<8}")
        
        print()
        
        # 检查入场价是否在信号生成时就已经被触及
        if start_idx > 0:
            prev_k = klines[start_idx - 1]
            prev_k_time = datetime.fromtimestamp(prev_k['timestamp']/1000)
            print(f"信号生成前的最后一根K线:")
            print(f"  时间: {prev_k_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  价格范围: ${prev_k['low']:,.2f} - ${prev_k['high']:,.2f}")
            
            if signal['type'] == 'long':
                if prev_k['low'] <= signal['entry'] * 1.001:
                    print(f"  ⚠️ 入场价 ${signal['entry']:,.2f} 在信号生成前已被触及！")
                if prev_k['high'] >= signal['take_profit_1']:
                    print(f"  ⚠️ 止盈1 ${signal['take_profit_1']:,.2f} 在信号生成前已被触及！")
            else:  # short
                if prev_k['high'] >= signal['entry'] * 0.999:
                    print(f"  ⚠️ 入场价 ${signal['entry']:,.2f} 在信号生成前已被触及！")
                if prev_k['low'] <= signal['take_profit_1']:
                    print(f"  ⚠️ 止盈1 ${signal['take_profit_1']:,.2f} 在信号生成前已被触及！")
        
        print()

if __name__ == "__main__":
    verify_signal_evaluation()


