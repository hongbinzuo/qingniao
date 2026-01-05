#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用多标的价格时序库（Sherlock 专用，不与 De. 的 BTC 时序库混用）。

DB 位置（Windows 本地）：src/data/sherlock_prices.duckdb

表结构（单表存多TF与交易所）：
- ohlcv(exchange TEXT, symbol TEXT, timeframe TEXT, timestamp BIGINT,
        open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE,
        created_at TEXT,
        PRIMARY KEY(exchange, symbol, timeframe, timestamp))

功能：
- ensure()：建库建表/索引
- upsert_klines(exchange, symbol, timeframe, candles)
- latest_ts(exchange, symbol, timeframe) -> int | None
- load_klines(exchange, symbol, timeframe, limit) -> list[dict]

注意：
- 外部可选择先从远端API拉取，再写库；拉失败时可从本地库读取兜底。
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


DB_FILE = Path(__file__).parent / 'data' / 'sherlock_prices.duckdb'


def _conn():
    import duckdb
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_FILE))


def ensure():
    con = _conn()
    con.execute('''
        CREATE TABLE IF NOT EXISTS ohlcv (
            exchange TEXT,
            symbol TEXT,
            timeframe TEXT,
            timestamp BIGINT,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            created_at TEXT,
            PRIMARY KEY(exchange, symbol, timeframe, timestamp)
        )
    ''')
    con.execute('CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_tf ON ohlcv(symbol, timeframe)')
    con.close()


def upsert_klines(exchange: str, symbol: str, timeframe: str, candles: List[Dict[str, Any]]) -> int:
    if not candles:
        return 0
    ensure()
    con = _conn()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    inserted = 0
    for k in candles:
        try:
            ts = int(k['timestamp'])
            con.execute('''
                INSERT OR IGNORE INTO ohlcv(exchange, symbol, timeframe, timestamp, open, high, low, close, volume, created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            ''', [exchange, symbol, timeframe, ts, float(k['open']), float(k['high']), float(k['low']), float(k['close']), float(k.get('volume') or 0.0), now])
            inserted += con.execute('SELECT changes()').fetchone()[0]
        except Exception:
            continue
    con.commit(); con.close()
    return inserted


def latest_ts(exchange: str, symbol: str, timeframe: str) -> Optional[int]:
    try:
        ensure()
        con = _conn()
        row = con.execute('''SELECT MAX(timestamp) FROM ohlcv WHERE exchange=? AND symbol=? AND timeframe=?''', [exchange, symbol, timeframe]).fetchone()
        con.close()
        return int(row[0]) if row and row[0] is not None else None
    except Exception:
        return None


def load_klines(exchange: str, symbol: str, timeframe: str, limit: int = 600) -> List[Dict[str, Any]]:
    try:
        ensure()
        con = _conn()
        rows = con.execute('''
            SELECT timestamp, open, high, low, close, volume
            FROM ohlcv
            WHERE exchange=? AND symbol=? AND timeframe=?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', [exchange, symbol, timeframe, int(limit)]).fetchall()
        con.close()
        rows.reverse()
        return [{'timestamp': int(r[0]), 'open': float(r[1]), 'high': float(r[2]), 'low': float(r[3]), 'close': float(r[4]), 'volume': float(r[5])} for r in rows]
    except Exception:
        return []

