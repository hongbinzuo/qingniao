#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试5分钟扫描速度"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from scripts.abu_gemini_signal_scanner_enhanced import get_top_coins
from generate_comprehensive_trading_plans import get_kline_binance

# 检查实际币种数量
coins_300 = get_top_coins(300)
print(f"请求300个币种，实际返回: {len(coins_300)}个")
print(f"币种列表: {coins_300[:10]}...")

# 测试5分钟K线获取速度
print("\n测试5分钟K线获取速度:")
start = time.time()
for i, symbol in enumerate(coins_300[:5], 1):
    klines = get_kline_binance(symbol, '5m', 288)
    if klines:
        print(f"{i}. {symbol}: {len(klines)}根K线，耗时{time.time()-start:.2f}秒")
    else:
        print(f"{i}. {symbol}: 获取失败")

print(f"\n5个币种总耗时: {time.time()-start:.2f}秒")
print(f"预估50个币种耗时: {(time.time()-start)/5*50:.2f}秒")



