#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试信号生成问题
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from generate_comprehensive_trading_plans import get_kline_binance

def test_klines():
    """测试K线数据获取"""
    print("=" * 80)
    print("测试K线数据获取")
    print("=" * 80)
    print()
    
    symbols = ['BTC', 'ETH', 'XMR', 'APT']
    
    for symbol in symbols:
        print(f"测试 {symbol}...")
        try:
            klines_15m = get_kline_binance(symbol, '15m', 50)
            if klines_15m:
                print(f"  ✓ 获取到 {len(klines_15m)} 根K线")
                print(f"  最新价格: {klines_15m[-1]['close']:.4f}")
                print(f"  时间戳: {klines_15m[-1]['timestamp']}")
            else:
                print(f"  ❌ 未获取到K线数据")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
        print()

if __name__ == '__main__':
    test_klines()



