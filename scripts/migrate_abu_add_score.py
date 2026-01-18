#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensure Abu DB trading_signals has 'score' and 'symbol' columns.
Safe to run multiple times.
"""
from __future__ import annotations
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import duckdb  # type: ignore

DB_FILE = SRC / 'data' / 'qingniao_abu.duckdb'


def ensure_columns():
    if not DB_FILE.exists():
        print(f"Abu DB not found: {DB_FILE}")
        return 1
    con = duckdb.connect(str(DB_FILE))
    cols = {r[1] for r in con.execute("PRAGMA table_info(trading_signals)").fetchall()}
    to_add = []
    if 'symbol' not in cols:
        to_add.append("ALTER TABLE trading_signals ADD COLUMN symbol TEXT;")
    if 'score' not in cols:
        to_add.append("ALTER TABLE trading_signals ADD COLUMN score DOUBLE;")
    if 'notes' not in cols:
        to_add.append("ALTER TABLE trading_signals ADD COLUMN notes TEXT;")
    for sql in to_add:
        con.execute(sql)
    con.close()
    print("OK: ensured columns:", ', '.join([s.split()[-2] for s in to_add]) or 'none needed')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(ensure_columns())
    except Exception as e:
        print('Migration failed:', e)
        sys.exit(2)
