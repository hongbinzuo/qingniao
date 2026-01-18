#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pull latest decisions from a local NOFX API and insert as trading_signals (system_name='nofx').

Env vars:
  NOFX_API_BASE   default 'http://127.0.0.1:8080'
  NOFX_TOKEN      Bearer token for protected endpoints (required)
  NOFX_TRADER_ID  target trader_id in NOFX (required)
  NOFX_LIMIT      how many latest decision records to pull (default 5)
  DEFAULT_TF      fallback timeframe tag (default '15m')

Mapping:
  For each DecisionRecord.Decisions[]:
    - type: 'long' if action contains 'buy'/'long'; 'short' if 'sell'/'short'
    - entry: price; stop_loss: stop_loss; tp1: take_profit (tp2 left None)
    - strength from confidence: >=70 strong, >=50 medium else weak
    - model: 'NOFX'
    - reason: reasoning
"""
from __future__ import annotations
import os, sys, time
import requests
from typing import Any, Dict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'src'))
from db_manager_trader import TraderDBManager  # type: ignore


def map_strength(conf: int | None) -> str:
    if conf is None: return 'medium'
    try:
        c = int(conf)
        if c >= 70: return 'strong'
        if c >= 50: return 'medium'
        return 'weak'
    except Exception:
        return 'medium'


def decide_type(action: str) -> str | None:
    a = (action or '').lower()
    if 'buy' in a or 'long' in a:
        return 'long'
    if 'sell' in a or 'short' in a:
        return 'short'
    return None


def pull_and_insert() -> int:
    api = os.getenv('NOFX_API_BASE', 'http://127.0.0.1:8080').rstrip('/')
    token = os.getenv('NOFX_TOKEN')
    trader_id = os.getenv('NOFX_TRADER_ID')
    limit = int(os.getenv('NOFX_LIMIT', '5'))
    tf = os.getenv('DEFAULT_TF', '15m')
    if not (token and trader_id):
        print('NOFX_TOKEN and NOFX_TRADER_ID required', file=sys.stderr)
        return 0
    url = f"{api}/api/decisions/latest"
    params = {'trader_id': trader_id, 'limit': str(limit)}
    headers = {'Authorization': f'Bearer {token}'}
    r = requests.get(url, params=params, headers=headers, timeout=15)
    r.raise_for_status()
    records = r.json() if r.headers.get('content-type','').startswith('application/json') else []
    if not isinstance(records, list):
        return 0

    db = TraderDBManager('de')
    conn = db._get_connection()
    writes = 0
    for rec in records:
        # Each record has an array 'decisions'
        for d in rec.get('decisions') or []:
            typ = decide_type(d.get('action') or '')
            if not typ: continue
            entry = d.get('price')
            sl = d.get('stop_loss')
            tp1 = d.get('take_profit')
            if not isinstance(entry, (int,float)) or not isinstance(sl, (int,float)):
                continue
            # day-level dedupe: same tf/type/entry/stop for system_name='nofx'
            try:
                today = time.strftime('%Y-%m-%d 00:00:00')
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM trading_signals WHERE created_at >= ? AND timeframe=? AND signal_type=? AND system_name='nofx' "
                    "AND ABS(entry_price-?) <= 0.5 AND ABS(stop_loss-?) <= 0.5",
                    [today, tf, typ, float(entry), float(sl)]
                ).fetchone()[0]
                if cnt:
                    continue
            except Exception:
                pass
            try:
                db.add_trading_signal(
                    signal_time=rec.get('timestamp') or time.strftime('%Y-%m-%d %H:%M:%S'),
                    timeframe=tf,
                    signal_type=typ,
                    entry_price=float(entry),
                    stop_loss=float(sl),
                    take_profit_1=float(tp1) if isinstance(tp1,(int,float)) else None,
                    take_profit_2=None,
                    entry_model='NOFX',
                    strength=map_strength(d.get('confidence')),
                    risk_reward_ratio=None,
                    volatility_level=None,
                    system_name='nofx',
                    entry_lower=None, entry_upper=None,
                    stop_distance_points=abs(float(entry)-float(sl)),
                    tp_rule=None, stop_rule=None,
                    bracket_note=d.get('reasoning') or None,
                )
                writes += 1
            except Exception as e:
                print('insert failed:', e, file=sys.stderr)
                continue
    db.close()
    print(f'inserted {writes} signals')
    return writes


if __name__ == '__main__':
    try:
        pull_and_insert()
    except Exception as e:
        print('pull failed:', e, file=sys.stderr)
        sys.exit(2)

