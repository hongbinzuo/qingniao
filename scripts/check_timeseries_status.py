#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import duckdb, os
from datetime import datetime
DB = os.path.join(os.getcwd(), 'src', 'data', 'btc_price_timeseries.duckdb')
try:
    con = duckdb.connect(DB, read_only=True)
except Exception as e:
    print('❌ cannot open timeseries db:', e)
    raise SystemExit(1)

def latest(ts_table):
    try:
        row = con.execute(f"SELECT MAX(timestamp) FROM {ts_table}").fetchone()
        if not row or not row[0]:
            return None
        ts = int(row[0])
        return ts, datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return None

for tf in ['5m','15m','1h','4h','1d']:
    t = latest(f'btc_price_{tf}')
    if t:
        print(f'{tf}: {t[0]} -> {t[1]}')
    else:
        print(f'{tf}: no data')
con.close()
