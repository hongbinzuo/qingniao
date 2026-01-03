#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB schema migration for bracket/pending signals and bracket evaluation.

Adds optional columns if missing:
  trading_signals: entry_lower, entry_upper, stop_distance_points, tp_rule, stop_rule, bracket_note
  trade_records   : stop_distance_points, tp_rule, stop_rule, timeframe
  signal_evaluations: evaluation_method, rr_to_date, mfe_points, mae_points
"""
import duckdb
from pathlib import Path

DB = Path('src')/'data'/'qingniao_de.duckdb'

def has_col(con, table, col):
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols

def add_col_if_missing(con, table, col, decl):
    if not has_col(con, table, col):
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")

def main():
    con = duckdb.connect(str(DB))
    # trading_signals
    add_col_if_missing(con, 'trading_signals', 'entry_lower', 'REAL')
    add_col_if_missing(con, 'trading_signals', 'entry_upper', 'REAL')
    add_col_if_missing(con, 'trading_signals', 'stop_distance_points', 'REAL')
    add_col_if_missing(con, 'trading_signals', 'tp_rule', 'TEXT')
    add_col_if_missing(con, 'trading_signals', 'stop_rule', 'TEXT')
    add_col_if_missing(con, 'trading_signals', 'bracket_note', 'TEXT')

    # trade_records
    add_col_if_missing(con, 'trade_records', 'stop_distance_points', 'REAL')
    add_col_if_missing(con, 'trade_records', 'tp_rule', 'TEXT')
    add_col_if_missing(con, 'trade_records', 'stop_rule', 'TEXT')
    add_col_if_missing(con, 'trade_records', 'timeframe', 'TEXT')

    # signal_evaluations
    add_col_if_missing(con, 'signal_evaluations', 'evaluation_method', 'TEXT')
    add_col_if_missing(con, 'signal_evaluations', 'rr_to_date', 'REAL')
    add_col_if_missing(con, 'signal_evaluations', 'mfe_points', 'REAL')
    add_col_if_missing(con, 'signal_evaluations', 'mae_points', 'REAL')

    con.close()
    print('migration done')

if __name__ == '__main__':
    main()
