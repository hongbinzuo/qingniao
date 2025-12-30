#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests

# 获取ticker
r = requests.get('https://api.gateio.ws/api/v4/spot/tickers', params={'currency_pair': 'BEAT_USDT'}, timeout=10)
print("Ticker数据:")
print(r.json())
print()

# 获取K线
r2 = requests.get('https://api.gateio.ws/api/v4/spot/candlesticks', params={'currency_pair': 'BEAT_USDT', 'interval': '1h', 'limit': 3}, timeout=10)
data = r2.json()
print("最新3根K线（原始数据）:")
for i, k in enumerate(data[-3:]):
    print(f"Kline {i}: {k}")
    print(f"  索引0(timestamp): {k[0]}")
    print(f"  索引1(volume): {k[1]}")
    print(f"  索引2(close): {k[2]}")
    print(f"  索引3(high): {k[3]}")
    print(f"  索引4(low): {k[4]}")
    print(f"  索引5(open): {k[5]}")
    print()




