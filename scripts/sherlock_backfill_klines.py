#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sherlock 历史K线回填脚本
- 目标：为 Sherlock 所需指标补齐本地缓存（1h/4h/1d，用于 Vegas/RSI/结构/TVEM/相对强度）
- 数据源：gate 优先，其次 binance/bitget，失败则尽力而为
- 落地：src/data/sherlock_prices.duckdb（需安装 duckdb；未安装则仅拉内存不落地）

用法示例：
  python scripts/sherlock_backfill_klines.py --symbols BTC,ETH,SOL --tfs 1h,4h,1d --limit 1200 --exchange gate
  python scripts/sherlock_backfill_klines.py --symbols-file symbols.txt --limit 600
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import List

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
    from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
    from generate_comprehensive_trading_plans import get_kline_bitget as _get_k_bitget
except Exception:
    _get_k_gate = _get_k_bin = _get_k_bitget = None

try:
    from market_timeseries import upsert_klines as _mts_upsert
    HAVE_MTS = True
except Exception:
    HAVE_MTS = False

import requests


def _get_kl_binance_direct(symbol: str, tf: str, limit: int = 300):
    tf_map = {'5m':'5m','15m':'15m','1h':'1h','4h':'4h','1d':'1d'}
    interval = tf_map.get(tf, '1h')
    sym = f'{symbol}USDT'
    try:
        r = requests.get('https://api.binance.com/api/v3/klines', params={'symbol': sym, 'interval': interval, 'limit': limit}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            out = []
            for k in data:
                out.append({'timestamp': int(k[0]), 'open': float(k[1]), 'high': float(k[2]), 'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])})
            return out
    except Exception:
        return []
    return []


def _fetch(symbol: str, tf: str, limit: int, exchange: str) -> int:
    providers = []
    if exchange == 'gate':
        providers = [_get_k_gate, _get_k_bin, _get_k_bitget]
    elif exchange == 'bitget':
        providers = [_get_k_bitget, _get_k_gate, _get_k_bin]
    else:
        providers = [_get_k_gate, _get_k_bin, _get_k_bitget]
    kl = []
    src = None
    for fn in providers:
        if not fn:
            continue
        try:
            k = fn(symbol=symbol, timeframe=tf, limit=limit)
            if k:
                kl = k
                src = 'gate' if fn is _get_k_gate else ('binance' if fn is _get_k_bin else 'bitget')
                break
        except Exception:
            continue
    if not kl:
        kl = _get_kl_binance_direct(symbol, tf, limit)
        src = 'binance'
    if not kl:
        return 0
    if HAVE_MTS:
        try:
            return _mts_upsert(src, symbol, tf, kl)
        except Exception:
            pass
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Sherlock 历史K线回填')
    ap.add_argument('--symbols', default='', help='逗号分隔的币种列表，如 BTC,ETH,SOL')
    ap.add_argument('--symbols-file', default='', help='从文件读取币种列表（每行一个）')
    ap.add_argument('--tfs', default='1h,4h,1d', help='时间框架列表，默认1h,4h,1d')
    ap.add_argument('--limit', type=int, default=600, help='每个TF拉取K线根数（默认600）')
    ap.add_argument('--exchange', default='gate', choices=['gate','bitget','auto'], help='数据源优先级（默认gate）')
    args = ap.parse_args()

    syms: List[str] = []
    if args.symbols:
        syms.extend([s.strip().upper() for s in args.symbols.split(',') if s.strip()])
    if args.symbols_file:
        p = Path(args.symbols_file)
        if p.exists():
            for line in p.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                syms.append(line.upper())
    if not syms:
        # 默认前50兜底
        syms = [
            'BTC','ETH','SOL','BNB','XRP','ADA','AVAX','DOGE','LINK','DOT',
            'MATIC','TON','TRX','ATOM','SUI','APT','ARB','OP','NEAR','PEPE',
            'SEI','TIA','INJ','AAVE','UNI','RUNE','ETC','FIL','ICP','XLM'
        ]

    tfs = [x.strip() for x in args.tfs.split(',') if x.strip()]

    total = 0
    for s in syms:
        for tf in tfs:
            n = _fetch(s, tf, args.limit, 'gate' if args.exchange!='bitget' else 'bitget')
            total += max(0, n)
            print(f"{s} {tf}: +{n} rows")
    print(f"Done. Upserted ~{total} rows (if HAVE_MTS={HAVE_MTS}).")


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
