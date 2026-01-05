#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库迁移（分库分表增强版）：
- 为每个交易员数据库补齐 execution_plans / order_legs / order_fills / indicator_snapshots / system_configs 表与索引。
重复运行安全（IF NOT EXISTS）。
"""
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import duckdb
from database_design_v2 import DB_DIR, TRADERS


DDL = [
    '''CREATE TABLE IF NOT EXISTS execution_plans (
           id INTEGER PRIMARY KEY,
           signal_id INTEGER NOT NULL,
           plan_json TEXT,
           created_at TEXT NOT NULL,
           updated_at TEXT
       )''',
    '''CREATE TABLE IF NOT EXISTS order_legs (
           id INTEGER PRIMARY KEY,
           plan_id INTEGER NOT NULL,
           leg_index INTEGER,
           leg_type TEXT,
           frac REAL,
           price REAL,
           ttl_bars INTEGER,
           tf TEXT,
           status TEXT DEFAULT 'pending',
           created_at TEXT NOT NULL,
           updated_at TEXT
       )''',
    '''CREATE TABLE IF NOT EXISTS order_fills (
           id INTEGER PRIMARY KEY,
           leg_id INTEGER NOT NULL,
           fill_time TEXT NOT NULL,
           price REAL,
           qty_frac REAL,
           fee_bps REAL,
           is_taker INTEGER DEFAULT 1,
           note TEXT,
           created_at TEXT NOT NULL
       )''',
    '''CREATE TABLE IF NOT EXISTS indicator_snapshots (
           id INTEGER PRIMARY KEY,
           timestamp TEXT NOT NULL,
           symbol TEXT,
           timeframe TEXT,
           indicator_name TEXT,
           data TEXT,
           created_at TEXT NOT NULL
       )''',
    '''CREATE TABLE IF NOT EXISTS system_configs (
           id INTEGER PRIMARY KEY,
           name TEXT NOT NULL,
           version TEXT,
           config_json TEXT,
           enabled INTEGER DEFAULT 1,
           created_at TEXT NOT NULL,
           updated_at TEXT
       )''',
    'CREATE INDEX IF NOT EXISTS idx_exec_plans_signal_id ON execution_plans(signal_id)',
    'CREATE INDEX IF NOT EXISTS idx_order_legs_plan_id ON order_legs(plan_id)',
    'CREATE INDEX IF NOT EXISTS idx_fills_leg_id ON order_fills(leg_id)',
    'CREATE INDEX IF NOT EXISTS idx_indicator_snapshots_ts ON indicator_snapshots(timestamp)'
]

# Add sherlock_hits DDL
DDL_HITS = [
    '''CREATE TABLE IF NOT EXISTS sherlock_hits (
           id INTEGER PRIMARY KEY,
           computed_at TEXT NOT NULL,
           symbol TEXT NOT NULL,
           tf TEXT,
           exchange TEXT,
           score REAL,
           tags TEXT,
           details_json TEXT,
           tvem_anchor TEXT,
           ema_n INTEGER,
           sigma_k REAL,
           tvem_line REAL,
           upper REAL,
           lower REAL,
           position TEXT,
           created_at TEXT NOT NULL
       )''',
    'CREATE INDEX IF NOT EXISTS idx_hits_time ON sherlock_hits(computed_at)',
    'CREATE INDEX IF NOT EXISTS idx_hits_symbol ON sherlock_hits(symbol)'
]


def migrate_one(db_file: Path):
    con = duckdb.connect(str(db_file))
    for ddl in DDL:
        con.execute(ddl)
    for ddl in DDL_HITS:
        con.execute(ddl)
    con.commit()
    con.close()


def main():
    for trader_id in TRADERS.keys():
        db = DB_DIR / f'qingniao_{trader_id}.duckdb'
        if db.exists():
            try:
                migrate_one(db)
                print('✓ migrated', db)
            except Exception as e:
                print('⚠️ migrate failed', db, e)
        else:
            print('skip (not found):', db)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
