#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 K 线数据获取
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from generate_comprehensive_trading_plans import get_kline_gateio, get_kline_binance

def test_kline_fetch():
    print("=" * 60)
    print("K线数据获取测试")
    print("=" * 60)
    print()
    
    # 注意：get_kline_* 函数接收的是不带_USDT的符号
    test_symbols = ['BTC', 'ETH', 'SOL']
    
    for symbol in test_symbols:
        print(f"\n测试币种: {symbol}")
        print("-" * 60)
        
        # 测试 Gate.io
        print(f"[1] Gate.io 15m K线（limit=200）...")
        klines = get_kline_gateio(symbol, '15m', 200)
        if klines:
            print(f"   [OK] 获取成功，数据量: {len(klines)} 条")
            print(f"   最新K线时间: {klines[-1][0] if klines else 'N/A'}")
        else:
            print(f"   [ERROR] 获取失败或数据为空")
        
        # 测试 Binance（备用）
        print(f"[2] Binance 15m K线（limit=200）...")
        klines_bn = get_kline_binance(symbol, '15m', 200)
        if klines_bn:
            print(f"   [OK] 获取成功，数据量: {len(klines_bn)} 条")
        else:
            print(f"   [ERROR] 获取失败或数据为空")
        
        # 判断是否满足最小要求（50条）
        if klines and len(klines) >= 50:
            print(f"   [✓] 数据充足，可以进行视觉匹配")
        else:
            print(f"   [✗] 数据不足（需要至少50条）")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == '__main__':
    test_kline_fetch()
