#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import io

# Windows UTF-8输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

print("🚀 开始币种K线分析测试")
print("="*50)

symbols = ['H', 'BANK', 'SOON', 'BLESS', 'COAI', 'MYX', 'BAS']
data = {}

for symbol in symbols:
    print(f"\n正在获取 {symbol} 数据...")
    
    # 测试Gate.io
    try:
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': f'{symbol}_USDT',
            'interval': '1d',
            'limit': 100
        }
        
        response = requests.get(url, params=params, timeout=10)
        print(f"  Gate.io状态码: {response.status_code}")
        
        if response.status_code == 200:
            kline_data = response.json()
            if kline_data:
                df = pd.DataFrame(kline_data, columns=[
                    'timestamp', 'volume', 'close', 'high', 'low', 'open', 'amount'
                ])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df['close'] = df['close'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['open'] = df['open'].astype(float)
                df['volume'] = df['volume'].astype(float)
                
                data[symbol] = df
                print(f"  ✓ {symbol}: 获取到 {len(df)} 条数据")
                print(f"  最新价格: {df['close'].iloc[0]:.4f}")
                print(f"  数据范围: {df['timestamp'].min()} 至 {df['timestamp'].max()}")
            else:
                print(f"  ✗ {symbol}: 无数据")
        else:
            print(f"  ✗ {symbol}: API错误 - {response.text}")
            
    except Exception as e:
        print(f"  ✗ {symbol}: 异常 - {e}")

print(f"\n成功获取 {len(data)} 个币种的数据")

if data:
    # 简单相关性分析
    print("\n开始相关性分析...")
    
    # 准备价格数据
    price_data = {}
    min_length = float('inf')
    
    for symbol, df in data.items():
        price_data[symbol] = df['close'].values
        min_length = min(min_length, len(df))
    
    # 截取相同长度的数据
    for symbol in price_data:
        price_data[symbol] = price_data[symbol][-min_length:]
    
    # 计算相关性
    df_corr = pd.DataFrame(price_data)
    correlation_matrix = df_corr.corr()
    
    print("\n相关性矩阵:")
    print(correlation_matrix.round(3))
    
    # 保存数据
    df_corr.to_csv('crypto_price_data.csv', encoding='utf-8')
    correlation_matrix.to_csv('crypto_correlation_matrix.csv', encoding='utf-8')
    
    print("\n数据已保存:")
    print("- crypto_price_data.csv")
    print("- crypto_correlation_matrix.csv")
    
    # 生成简单图表
    plt.figure(figsize=(12, 8))
    
    for symbol, df in data.items():
        # 标准化价格
        normalized_price = df['close'] / df['close'].iloc[0] * 100
        plt.plot(df['timestamp'], normalized_price, label=symbol, linewidth=2)
    
    plt.title('币种价格走势对比（标准化）', fontsize=16, fontweight='bold')
    plt.xlabel('时间')
    plt.ylabel('标准化价格 (基准=100)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('crypto_price_comparison.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("- crypto_price_comparison.png")

print("\n✅ 分析完成！")



