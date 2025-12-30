#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import pandas as pd
import sys

# Windows UTF-8输出
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

print("🚀 测试单个币种数据获取")
print("="*30)

# 测试H币种
symbol = 'H'
print(f"测试币种: {symbol}")

try:
    print("正在请求Gate.io API...")
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {
        'currency_pair': f'{symbol}_USDT',
        'interval': '1d',
        'limit': 10
    }
    
    print(f"请求URL: {url}")
    print(f"参数: {params}")
    
    response = requests.get(url, params=params, timeout=10)
    print(f"响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"获取到数据: {len(data)}条")
        if data:
            print("最新K线数据:")
            print(f"  时间: {data[0][0]}")
            print(f"  开盘: {data[0][5]}")
            print(f"  最高: {data[0][3]}")
            print(f"  最低: {data[0][4]}")
            print(f"  收盘: {data[0][2]}")
            print(f"  成交量: {data[0][1]}")
    else:
        print(f"API错误: {response.text}")
        
except Exception as e:
    print(f"异常: {e}")

print("测试完成")



