#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接测试 API 调用
"""

import requests
import json

def test_gateio():
    print("测试 Gate.io API")
    print("-" * 60)
    
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {
        'currency_pair': 'BTC_USDT',
        'interval': '15m',
        'limit': 10
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"状态码: {response.status_code}")
        print(f"响应长度: {len(response.text)} 字节")
        
        if response.status_code == 200:
            data = response.json()
            print(f"数据条数: {len(data) if data else 0}")
            if data:
                print(f"第一条K线: {data[0]}")
                print("[OK] Gate.io API 正常")
            else:
                print("[ERROR] 返回空数据")
        else:
            print(f"[ERROR] 请求失败: {response.text[:200]}")
    except Exception as e:
        print(f"[ERROR] 异常: {e}")

def test_binance():
    print("\n测试 Binance API")
    print("-" * 60)
    
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        'symbol': 'BTCUSDT',
        'interval': '15m',
        'limit': 10
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        print(f"状态码: {response.status_code}")
        print(f"响应长度: {len(response.text)} 字节")
        
        if response.status_code == 200:
            data = response.json()
            print(f"数据条数: {len(data) if data else 0}")
            if data:
                print(f"第一条K线: {data[0][:6]}")  # 只显示前6个字段
                print("[OK] Binance API 正常")
            else:
                print("[ERROR] 返回空数据")
        else:
            print(f"[ERROR] 请求失败: {response.text[:200]}")
    except Exception as e:
        print(f"[ERROR] 异常: {e}")

if __name__ == '__main__':
    test_gateio()
    test_binance()
