#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试币安合约API修复
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
import requests

def test_binance_futures():
    """测试币安合约API"""
    print("=" * 80)
    print("测试币安合约API修复")
    print("=" * 80)
    print()
    
    # 1. 直接测试币安合约API
    try:
        r = requests.get('https://fapi.binance.com/fapi/v1/ticker/price?symbol=XMRUSDT', timeout=10)
        if r.status_code == 200:
            futures_price = float(r.json()['price'])
            print(f"✓ 币安合约API当前价格: {futures_price:.4f} USDT")
        else:
            print(f"❌ 币安合约API请求失败: {r.status_code}")
            futures_price = None
    except Exception as e:
        print(f"❌ 币安合约API请求异常: {e}")
        futures_price = None
    
    print()
    
    # 2. 测试修复后的get_kline_binance函数
    print("=" * 80)
    print("测试修复后的get_kline_binance函数")
    print("=" * 80)
    print()
    
    try:
        klines = get_kline_binance('XMR', '15m', 10)
        if klines:
            latest = klines[-1]
            print(f"✓ 成功获取XMR合约K线数据（15m，最新1根）:")
            print(f"  收盘价: {latest['close']:.4f} USDT")
            print(f"  开盘价: {latest['open']:.4f} USDT")
            print(f"  最高价: {latest['high']:.4f} USDT")
            print(f"  最低价: {latest['low']:.4f} USDT")
            kline_price = latest['close']
        else:
            print("❌ K线数据为空")
            kline_price = None
    except Exception as e:
        print(f"❌ 获取K线数据失败: {e}")
        import traceback
        traceback.print_exc()
        kline_price = None
    
    print()
    print("=" * 80)
    print("价格对比")
    print("=" * 80)
    print()
    
    if futures_price and kline_price:
        diff = abs(futures_price - kline_price)
        diff_pct = (diff / futures_price) * 100
        print(f"合约API价格: {futures_price:.4f} USDT")
        print(f"K线数据价格: {kline_price:.4f} USDT")
        print(f"价格差异: {diff:.4f} USDT ({diff_pct:.2f}%)")
        if diff_pct < 1:
            print("✓ 价格匹配，修复成功！")
        else:
            print("⚠️  价格差异较大，可能需要检查")
    else:
        print("⚠️  无法对比价格")


if __name__ == '__main__':
    test_binance_futures()



