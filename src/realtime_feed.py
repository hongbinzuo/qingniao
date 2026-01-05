#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Minimal polling-based realtime feed (WS-ready skeleton) for BTCUSDT.
Writes recent prices into local DuckDB timeseries if available; otherwise returns snapshots.
"""
from __future__ import annotations
import time, requests
from typing import Optional, Dict

def get_price_binance() -> Optional[float]:
    try:
        r = requests.get('https://api.binance.com/api/v3/ticker/price', params={'symbol':'BTCUSDT'}, timeout=8)
        d = r.json()
        if d and d.get('price'):
            return float(d['price'])
    except Exception:
        return None
    return None

def get_price_gate() -> Optional[float]:
    try:
        r = requests.get('https://api.gateio.ws/api/v4/spot/tickers', params={'currency_pair':'BTC_USDT'}, timeout=8)
        d = r.json()
        if isinstance(d, list) and d:
            return float(d[0]['last'])
    except Exception:
        return None
    return None

def get_snapshot() -> Dict:
    ps = [p for p in (get_price_gate(), get_price_binance()) if isinstance(p,(int,float))]
    mid = sorted(ps)[len(ps)//2] if ps else None
    return {'binance': ps[-1] if ps else None, 'gate': ps[0] if ps else None, 'mid': mid}

if __name__ == '__main__':
    print(get_snapshot())

