#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查1小时信号的入场价格成交可行性
分析1小时K线数据，评估挂单成交可能性
"""

import requests
import sys
from datetime import datetime, timedelta

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def get_btc_kline_1h_gateio(limit=50):
    """获取1小时K线数据"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': '1h',
            'limit': limit
        }
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
                klines = []
                for k in data:
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
        print(f"获取K线失败: {e}", file=sys.stderr)
    return None


def get_btc_kline_1m_around_time(signal_time: datetime, hours_before=2, hours_after=2):
    """获取信号时间前后的1分钟K线"""
    signal_timestamp = int(signal_time.timestamp())
    from_timestamp = signal_timestamp - hours_before * 3600
    to_timestamp = signal_timestamp + hours_after * 3600
    
    try:
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': '1m',
            'from': from_timestamp,
            'to': to_timestamp,
            'limit': 500
        }
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
                klines = []
                for k in data:
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
        print(f"获取1分钟K线失败: {e}", file=sys.stderr)
    return None


def main():
    signal_time = datetime(2025, 12, 30, 14, 22, 27)
    entry_price = 87018
    signal_type = 'long'
    
    print("="*80)
    print("1小时信号入场价格成交可行性分析")
    print("="*80)
    print("")
    print(f"信号生成时间: {signal_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"入场价格: ${entry_price:,.2f}")
    print(f"信号类型: {signal_type.upper()}")
    print("")
    
    # 1. 获取1小时K线数据
    print("1. 分析1小时K线数据...")
    klines_1h = get_btc_kline_1h_gateio(limit=50)
    
    if klines_1h:
        # 找到信号生成时间对应的1小时K线
        signal_timestamp = int(signal_time.timestamp() * 1000)
        signal_kline = None
        signal_kline_idx = -1
        
        for i, k in enumerate(klines_1h):
            k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
            # 找到包含信号时间的1小时K线
            if k['timestamp'] <= signal_timestamp < k['timestamp'] + 3600000:
                signal_kline = k
                signal_kline_idx = i
                break
        
        if signal_kline:
            k_time = datetime.fromtimestamp(signal_kline['timestamp'] / 1000)
            print(f"   ✅ 找到信号对应的1小时K线: {k_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   - 开盘: ${signal_kline['open']:,.2f}")
            print(f"   - 最高: ${signal_kline['high']:,.2f}")
            print(f"   - 最低: ${signal_kline['low']:,.2f}")
            print(f"   - 收盘: ${signal_kline['close']:,.2f}")
            print("")
            
            # 检查入场价是否在1小时K线范围内
            if signal_kline['low'] <= entry_price <= signal_kline['high']:
                print(f"   ✅ 入场价 ${entry_price:,.2f} 在该1小时K线价格范围内")
                print(f"   - 价格范围: ${signal_kline['low']:,.2f} ~ ${signal_kline['high']:,.2f}")
            else:
                if entry_price < signal_kline['low']:
                    diff_pct = ((signal_kline['low'] - entry_price) / entry_price) * 100
                    print(f"   ⚠️ 入场价 ${entry_price:,.2f} 低于该1小时K线最低价 ${signal_kline['low']:,.2f} (偏差 {diff_pct:.2f}%)")
                else:
                    diff_pct = ((entry_price - signal_kline['high']) / entry_price) * 100
                    print(f"   ⚠️ 入场价 ${entry_price:,.2f} 高于该1小时K线最高价 ${signal_kline['high']:,.2f} (偏差 {diff_pct:.2f}%)")
            print("")
            
            # 查看前后几个1小时K线
            print("   前后1小时K线价格范围:")
            for i in range(max(0, signal_kline_idx - 2), min(len(klines_1h), signal_kline_idx + 3)):
                k = klines_1h[i]
                k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
                marker = " <-- 信号时间" if i == signal_kline_idx else ""
                print(f"   {k_time.strftime('%Y-%m-%d %H:%M')}: ${k['low']:,.2f} ~ ${k['high']:,.2f}{marker}")
            print("")
    
    # 2. 获取1分钟K线数据，检查精确价格
    print("2. 分析1分钟K线数据（信号时间前后2小时）...")
    klines_1m = get_btc_kline_1m_around_time(signal_time, hours_before=2, hours_after=2)
    
    if klines_1m:
        print(f"   ✅ 获取到 {len(klines_1m)} 根1分钟K线")
        
        # 找到最低价（做多信号需要价格低于入场价）
        min_price = float('inf')
        min_price_time = None
        max_price = 0
        max_price_time = None
        
        prices_below_entry = []
        
        for k in klines_1m:
            k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
            if k['low'] < min_price:
                min_price = k['low']
                min_price_time = k_time
            if k['high'] > max_price:
                max_price = k['high']
                max_price_time = k_time
            
            # 检查是否有价格低于入场价（做多信号）
            if k['low'] <= entry_price:
                prices_below_entry.append({
                    'time': k_time,
                    'price': k['low'],
                    'high': k['high']
                })
        
        print(f"   - 最低价: ${min_price:,.2f} ({min_price_time.strftime('%Y-%m-%d %H:%M:%S') if min_price_time else 'N/A'})")
        print(f"   - 最高价: ${max_price:,.2f} ({max_price_time.strftime('%Y-%m-%d %H:%M:%S') if max_price_time else 'N/A'})")
        print("")
        
        if prices_below_entry:
            print(f"   ✅ 找到 {len(prices_below_entry)} 个时间点的价格低于或等于入场价 ${entry_price:,.2f}")
            print("   前5个可成交的时间点:")
            for i, p in enumerate(prices_below_entry[:5]):
                print(f"   - {p['time'].strftime('%Y-%m-%d %H:%M:%S')}: 最低 ${p['price']:,.2f}, 最高 ${p['high']:,.2f}")
        else:
            print(f"   ⚠️ 在信号时间前后2小时内，没有价格低于或等于入场价 ${entry_price:,.2f}")
            if min_price_time:
                diff_pct = ((min_price - entry_price) / entry_price) * 100
                print(f"   - 最接近价格: ${min_price:,.2f} ({min_price_time.strftime('%Y-%m-%d %H:%M:%S')})")
                print(f"   - 价格偏差: {diff_pct:+.2f}%")
        print("")
    
    # 3. 总结和建议
    print("="*80)
    print("总结和建议")
    print("="*80)
    print("")
    
    if klines_1m and prices_below_entry:
        print("✅ **可以在入场价格挂单成交**")
        print("")
        print("理由:")
        print(f"- 在信号时间前后2小时内，有 {len(prices_below_entry)} 个时间点的价格达到或低于入场价 ${entry_price:,.2f}")
        print("- 做多信号可以在价格低于或等于入场价时挂单成交")
        print("")
        print("建议:")
        print("- 可以在入场价 $87,018 挂限价买单")
        print("- 如果价格已经高于入场价，可以等待价格回调到入场价附近")
        print("- 或者使用略高于入场价的限价单（如 $87,050）以提高成交概率")
    else:
        print("⚠️ **入场价格可能无法立即成交**")
        print("")
        print("理由:")
        if klines_1m:
            print(f"- 在信号时间前后2小时内，最低价为 ${min_price:,.2f}")
            if min_price > entry_price:
                diff_pct = ((min_price - entry_price) / entry_price) * 100
                print(f"- 入场价 ${entry_price:,.2f} 低于实际最低价 {diff_pct:.2f}%")
        print("")
        print("建议:")
        print("- 如果价格已经高于入场价，可以等待价格回调")
        print(f"- 或者使用略高于当前最低价的限价单（如 ${min_price + 50:,.2f}）")
        print("- 1小时信号通常基于1小时K线计算，入场价可能是该1小时K线的支撑位")
        print("- 如果该支撑位有效，价格可能会回调到该位置")
    print("")


if __name__ == "__main__":
    main()










