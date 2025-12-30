#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys

# Windows UTF-8输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

print("🚀 简化版币种K线分析")
print("="*30)

# 测试单个币种
symbol = 'H'
print(f"测试币种: {symbol}")

try:
    print("正在请求Gate.io API...")
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {
        'currency_pair': f'{symbol}_USDT',
        'interval': '1d',
        'limit': 100
    }
    
    response = requests.get(url, params=params, timeout=10)
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"获取到数据: {len(data)}条")
        
        if data:
            print("数据格式检查:")
            print(f"  第一条数据: {data[0]}")
            print(f"  数据列数: {len(data[0])}")
            
            # 根据实际列数创建DataFrame
            if len(data[0]) == 8:
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'volume', 'close', 'high', 'low', 'open', 'amount', 'quote_volume'
                ])
            else:
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'volume', 'close', 'high', 'low', 'open', 'amount'
                ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['open'] = df['open'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            print(f"✓ 成功处理 {len(df)} 条数据")
            print(f"数据范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
            print(f"最新价格: {df['close'].iloc[0]:.4f}")
            
            # 保存数据
            df.to_csv(f'{symbol}_kline_data.csv', index=False)
            print(f"✓ 数据已保存: {symbol}_kline_data.csv")
            
        else:
            print("✗ 无数据")
    else:
        print(f"✗ API错误: {response.text}")
        
except Exception as e:
    print(f"✗ 异常: {e}")

print("测试完成")



