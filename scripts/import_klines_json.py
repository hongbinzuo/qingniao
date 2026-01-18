#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线数据导入脚本（从JSON导入到DuckDB）

使用Go程序获取数据（输出JSON），然后使用此脚本导入数据库
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import duckdb

# 数据库路径
DB_PATH = ROOT / 'data' / 'kline_data' / 'klines.duckdb'


def ensure_database():
    """初始化数据库和表"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = duckdb.connect(str(DB_PATH))
    
    # 创建表
    conn.execute('''
        CREATE TABLE IF NOT EXISTS klines (
            timestamp BIGINT NOT NULL,
            exchange TEXT NOT NULL,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            open DOUBLE NOT NULL,
            high DOUBLE NOT NULL,
            low DOUBLE NOT NULL,
            close DOUBLE NOT NULL,
            volume DOUBLE NOT NULL,
            created_at TEXT,
            PRIMARY KEY (timestamp, exchange, symbol, timeframe)
        )
    ''')
    
    # 创建索引
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_klines_symbol_tf ON klines(symbol, timeframe)",
        "CREATE INDEX IF NOT EXISTS idx_klines_timestamp ON klines(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_klines_exchange_symbol_tf ON klines(exchange, symbol, timeframe)",
    ]
    
    for idx_sql in indexes:
        try:
            conn.execute(idx_sql)
        except Exception as e:
            print(f"Warning: failed to create index: {e}", file=sys.stderr)
    
    conn.close()


def get_latest_timestamp(exchange: str, symbol: str, timeframe: str) -> Optional[int]:
    """获取最新的时间戳"""
    try:
        conn = duckdb.connect(str(DB_PATH))
        result = conn.execute('''
            SELECT MAX(timestamp)
            FROM klines
            WHERE exchange = ? AND symbol = ? AND timeframe = ?
        ''', [exchange, symbol, timeframe]).fetchone()
        conn.close()
        
        if result and result[0] is not None:
            return int(result[0])
        return None
    except Exception:
        return None


def import_json_file(json_file: str, exchange: str = 'gate') -> Dict:
    """从JSON文件导入K线数据"""
    ensure_database()
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'results' not in data:
        print(f"Error: invalid JSON format", file=sys.stderr)
        return {'success': 0, 'failed': 0, 'inserted': 0}
    
    conn = duckdb.connect(str(DB_PATH))
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    total_inserted = 0
    success_count = 0
    failed_count = 0
    
    for result in data['results']:
        symbol = result.get('symbol', '')
        timeframe = result.get('timeframe', '')
        
        if 'error' in result and result['error']:
            print(f"[FAIL] {symbol}: {result['error']}", file=sys.stderr)
            failed_count += 1
            continue
        
        klines = result.get('klines', [])
        if not klines:
            continue
        
        inserted = 0
        for kline in klines:
            try:
                conn.execute('''
                    INSERT INTO klines (timestamp, exchange, symbol, timeframe, 
                                       open, high, low, close, volume, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (timestamp, exchange, symbol, timeframe) DO NOTHING
                ''', [
                    int(kline['timestamp']),
                    exchange,
                    symbol,
                    timeframe,
                    float(kline['open']),
                    float(kline['high']),
                    float(kline['low']),
                    float(kline['close']),
                    float(kline['volume']),
                    now
                ])
                inserted += 1
            except Exception as e:
                print(f"Warning: failed to insert {symbol} {kline['timestamp']}: {e}", file=sys.stderr)
        
        total_inserted += inserted
        success_count += 1
        print(f"[OK] {symbol}: inserted {inserted} klines")
    
    conn.close()
    
    return {
        'success': success_count,
        'failed': failed_count,
        'inserted': total_inserted
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Import K-line data from JSON to DuckDB')
    parser.add_argument('json_file', help='JSON file from Go fetcher')
    parser.add_argument('--exchange', default='gate', help='Exchange name (default: gate)')
    parser.add_argument('--db', help='Database path (default: data/kline_data/klines.duckdb)')
    
    args = parser.parse_args()
    
    global DB_PATH
    if args.db:
        DB_PATH = Path(args.db)
    
    if not Path(args.json_file).exists():
        print(f"Error: JSON file not found: {args.json_file}", file=sys.stderr)
        return 1
    
    print(f"Importing from {args.json_file}...")
    result = import_json_file(args.json_file, args.exchange)
    
    print()
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Failed: {result['failed']}")
    print(f"Total inserted: {result['inserted']} klines")
    print("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

