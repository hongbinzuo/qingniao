#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K线数据库访问模块（Python）

用于从Go获取的K线数据库中读取数据
"""

from __future__ import annotations
import duckdb
from pathlib import Path
from typing import List, Dict, Optional

# 默认数据库路径
DEFAULT_DB_PATH = Path(__file__).parent.parent / 'data' / 'kline_data' / 'klines.duckdb'


def load_klines(symbol: str, timeframe: str, limit: int = 200, 
                exchange: str = 'gate', db_path: Optional[Path] = None) -> List[Dict]:
    """
    从数据库加载K线数据
    
    Args:
        symbol: 币种（如'BTC'）
        timeframe: 时间框架（如'15m'）
        limit: 获取的K线数量
        exchange: 交易所（默认'gate'）
        db_path: 数据库文件路径（默认使用DEFAULT_DB_PATH）
    
    Returns:
        K线数据列表（按时间从早到晚排序）
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    if not db_path.exists():
        return []
    
    try:
        conn = duckdb.connect(str(db_path))
        
        query = '''
            SELECT timestamp, open, high, low, close, volume
            FROM klines
            WHERE exchange = ? AND symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT ?
        '''
        rows = conn.execute(query, [exchange, symbol, timeframe, limit]).fetchall()
        conn.close()
        
        # 转换为字典列表（从早到晚）
        rows.reverse()
        return [
            {
                'timestamp': int(r[0]),
                'open': float(r[1]),
                'high': float(r[2]),
                'low': float(r[3]),
                'close': float(r[4]),
                'volume': float(r[5])
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Error loading klines: {e}", file=__import__('sys').stderr)
        return []


def get_latest_timestamp(symbol: str, timeframe: str, 
                        exchange: str = 'gate', db_path: Optional[Path] = None) -> Optional[int]:
    """
    获取数据库中最新的时间戳
    
    Args:
        symbol: 币种（如'BTC'）
        timeframe: 时间框架（如'15m'）
        exchange: 交易所（默认'gate'）
        db_path: 数据库文件路径（默认使用DEFAULT_DB_PATH）
    
    Returns:
        最新时间戳（秒），如果不存在返回None
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    if not db_path.exists():
        return None
    
    try:
        conn = duckdb.connect(str(db_path))
        
        query = '''
            SELECT MAX(timestamp)
            FROM klines
            WHERE exchange = ? AND symbol = ? AND timeframe = ?
        '''
        result = conn.execute(query, [exchange, symbol, timeframe]).fetchone()
        conn.close()
        
        if result and result[0] is not None:
            return int(result[0])
        return None
    except Exception as e:
        print(f"Error getting latest timestamp: {e}", file=__import__('sys').stderr)
        return None


def get_klines_count(symbol: str, timeframe: str, 
                    exchange: str = 'gate', db_path: Optional[Path] = None) -> int:
    """
    获取数据库中的K线数量
    
    Args:
        symbol: 币种（如'BTC'）
        timeframe: 时间框架（如'15m'）
        exchange: 交易所（默认'gate'）
        db_path: 数据库文件路径（默认使用DEFAULT_DB_PATH）
    
    Returns:
        K线数量
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    if not db_path.exists():
        return 0
    
    try:
        conn = duckdb.connect(str(db_path))
        
        query = '''
            SELECT COUNT(*)
            FROM klines
            WHERE exchange = ? AND symbol = ? AND timeframe = ?
        '''
        result = conn.execute(query, [exchange, symbol, timeframe]).fetchone()
        conn.close()
        
        return int(result[0]) if result else 0
    except Exception as e:
        print(f"Error getting klines count: {e}", file=__import__('sys').stderr)
        return 0


if __name__ == '__main__':
    # 测试
    import sys
    
    symbol = 'BTC'
    timeframe = '15m'
    
    print(f"Loading klines for {symbol} {timeframe}...")
    klines = load_klines(symbol, timeframe, limit=10)
    print(f"Loaded {len(klines)} klines")
    
    if klines:
        print(f"First kline: {klines[0]}")
        print(f"Last kline: {klines[-1]}")
    
    latest_ts = get_latest_timestamp(symbol, timeframe)
    print(f"Latest timestamp: {latest_ts}")
    
    count = get_klines_count(symbol, timeframe)
    print(f"Total klines: {count}")



