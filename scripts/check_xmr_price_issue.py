#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查XMR价格问题
"""
import sys
import requests
from pathlib import Path
from datetime import datetime

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

try:
    from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
    from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
except ImportError:
    _get_k_bin = _get_k_gate = None

def check_xmr_price():
    """检查XMR价格"""
    print("=" * 80)
    print("XMR价格检查")
    print("=" * 80)
    print()
    
    # 1. 从Binance API获取当前价格
    try:
        r = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=XMRUSDT', timeout=10)
        if r.status_code == 200:
            binance_price = float(r.json()['price'])
            print(f"✓ Binance API当前价格: {binance_price:.4f} USDT")
        else:
            print(f"❌ Binance API请求失败: {r.status_code}")
            binance_price = None
    except Exception as e:
        print(f"❌ Binance API请求异常: {e}")
        binance_price = None
    
    # 2. 从Gate.io API获取当前价格
    try:
        r = requests.get('https://api.gateio.ws/api/v4/spot/tickers', 
                        params={'currency_pair': 'XMR_USDT'}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data and len(data) > 0:
                gate_price = float(data[0]['last'])
                print(f"✓ Gate.io API当前价格: {gate_price:.4f} USDT")
            else:
                gate_price = None
        else:
            print(f"❌ Gate.io API请求失败: {r.status_code}")
            gate_price = None
    except Exception as e:
        print(f"❌ Gate.io API请求异常: {e}")
        gate_price = None
    
    print()
    
    # 3. 获取K线数据（15m）
    print("=" * 80)
    print("K线数据检查")
    print("=" * 80)
    print()
    
    # Binance K线
    if _get_k_bin:
        try:
            binance_klines = _get_k_bin(symbol='XMR', timeframe='15m', limit=10)
            if binance_klines:
                latest_kline = binance_klines[-1]
                print(f"✓ Binance K线数据（15m，最新1根）:")
                print(f"  时间: {datetime.fromtimestamp(latest_kline['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  收盘价: {latest_kline['close']:.4f}")
                print(f"  开盘价: {latest_kline['open']:.4f}")
                print(f"  最高价: {latest_kline['high']:.4f}")
                print(f"  最低价: {latest_kline['low']:.4f}")
                binance_kline_price = latest_kline['close']
            else:
                print("❌ Binance K线数据为空")
                binance_kline_price = None
        except Exception as e:
            print(f"❌ Binance K线数据获取失败: {e}")
            binance_kline_price = None
    else:
        print("⚠️  Binance K线函数未导入")
        binance_kline_price = None
    
    print()
    
    # Gate.io K线
    if _get_k_gate:
        try:
            gate_klines = _get_k_gate(symbol='XMR', timeframe='15m', limit=10)
            if gate_klines:
                latest_kline = gate_klines[-1]
                print(f"✓ Gate.io K线数据（15m，最新1根）:")
                print(f"  时间: {datetime.fromtimestamp(latest_kline['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"  收盘价: {latest_kline['close']:.4f}")
                print(f"  开盘价: {latest_kline['open']:.4f}")
                print(f"  最高价: {latest_kline['high']:.4f}")
                print(f"  最低价: {latest_kline['low']:.4f}")
                gate_kline_price = latest_kline['close']
            else:
                print("❌ Gate.io K线数据为空")
                gate_kline_price = None
        except Exception as e:
            print(f"❌ Gate.io K线数据获取失败: {e}")
            gate_kline_price = None
    else:
        print("⚠️  Gate.io K线函数未导入")
        gate_kline_price = None
    
    print()
    print("=" * 80)
    print("价格对比")
    print("=" * 80)
    print()
    
    # 信号中的价格
    signal_price = 118.7000
    print(f"信号中的价格: {signal_price:.4f} USDT")
    print()
    
    if binance_price:
        diff = abs(signal_price - binance_price)
        diff_pct = (diff / binance_price) * 100
        print(f"与Binance API价格差异: {diff:.4f} USDT ({diff_pct:.2f}%)")
        if diff_pct > 1:
            print(f"  ⚠️  价格差异超过1%，可能存在问题")
    
    if gate_price:
        diff = abs(signal_price - gate_price)
        diff_pct = (diff / gate_price) * 100
        print(f"与Gate.io API价格差异: {diff:.4f} USDT ({diff_pct:.2f}%)")
        if diff_pct > 1:
            print(f"  ⚠️  价格差异超过1%，可能存在问题")
    
    if binance_kline_price:
        diff = abs(signal_price - binance_kline_price)
        diff_pct = (diff / binance_kline_price) * 100
        print(f"与Binance K线价格差异: {diff:.4f} USDT ({diff_pct:.2f}%)")
    
    if gate_kline_price:
        diff = abs(signal_price - gate_kline_price)
        diff_pct = (diff / gate_kline_price) * 100
        print(f"与Gate.io K线价格差异: {diff:.4f} USDT ({diff_pct:.2f}%)")
    
    print()
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"信号生成时间: 2026-01-11 10:29:59")


if __name__ == '__main__':
    check_xmr_price()



