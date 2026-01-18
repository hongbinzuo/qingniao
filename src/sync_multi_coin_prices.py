#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多币种价格数据同步

从Gate.io获取多个币种的历史价格数据，存储到DuckDB数据库。
"""

import sys
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import duckdb

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 需要同步的币种列表（Top 20 + 其他常用币种）
COINS_TO_SYNC = [
    'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'BNB', 'ADA', 'AVAX', 'TRX', 'LINK',
    'DOT', 'MATIC', 'SHIB', 'UNI', 'LTC', 'BCH', 'ATOM', 'ETC', 'XLM', 'FIL',
    'DN', 'BREV', 'IP', 'STETH', 'WBTC', 'WETH', 'USDC', 'USDT'  # 包括稳定币用于过滤
]

# 时间框架
TIMEFRAMES = ['5m', '15m', '1h', '4h', '1d']


def get_klines_gateio(symbol: str, timeframe: str, start_time: Optional[int] = None, 
                     end_time: Optional[int] = None, limit: int = 1000) -> List[Dict]:
    """
    从Gate.io获取K线数据
    
    Args:
        symbol: 币种符号
        timeframe: 时间框架
        start_time: 开始时间戳（可选）
        end_time: 结束时间戳（可选）
        limit: 返回数量限制
    
    Returns:
        K线数据列表
    """
    try:
        tf_map = {
            '5m': '5m', '15m': '15m', '1h': '1h', 
            '4h': '4h', '1d': '1d'
        }
        interval = tf_map.get(timeframe, '5m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': f'{symbol}_USDT',
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['from'] = start_time
        if end_time:
            params['to'] = end_time
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data:
                klines = []
                for k in data:
                    klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[5]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'close': float(k[2]),
                        'volume': float(k[6]) if len(k) > 6 else 0.0
                    })
                return klines
    except Exception as e:
        print(f"[WARN] 获取K线失败 {symbol} {timeframe}: {e}", file=sys.stderr)
    
    return []


def init_database(db_path: Path):
    """初始化数据库和表"""
    conn = duckdb.connect(str(db_path))
    
    for timeframe in TIMEFRAMES:
        for symbol in COINS_TO_SYNC:
            table_name = f"{symbol.lower()}_price_{timeframe}"
            
            # 创建表（如果不存在）
            conn.execute(f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    timestamp BIGINT PRIMARY KEY,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE
                )
            ''')
            
            # 创建索引
            try:
                conn.execute(f'CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name}(timestamp)')
            except:
                pass  # 索引可能已存在
    
    return conn


def sync_coin_data(conn, symbol: str, timeframe: str, days: int = 90):
    """
    同步单个币种的数据
    
    Args:
        conn: 数据库连接
        symbol: 币种符号
        timeframe: 时间框架
        days: 同步天数
    """
    table_name = f"{symbol.lower()}_price_{timeframe}"
    
    # 获取已有数据的最新时间戳
    try:
        result = conn.execute(f'''
            SELECT MAX(timestamp) as max_ts
            FROM {table_name}
        ''').fetchone()
        last_timestamp = result[0] if result and result[0] else None
    except:
        last_timestamp = None
    
    # 计算开始时间
    if last_timestamp:
        start_time = last_timestamp + 1  # 从最后一条数据之后开始
    else:
        # 如果没有数据，从days天前开始
        start_dt = datetime.now() - timedelta(days=days)
        start_time = int(start_dt.timestamp())
    
    end_time = int(datetime.now().timestamp())
    
    print(f"  同步 {symbol} {timeframe}...", end=' ', flush=True)
    
    # 获取数据
    all_klines = []
    current_start = start_time
    
    while current_start < end_time:
        klines = get_klines_gateio(symbol, timeframe, start_time=current_start, limit=1000)
        if not klines:
            break
        
        all_klines.extend(klines)
        
        if len(klines) < 1000:
            break
        
        # 更新开始时间
        current_start = klines[-1]['timestamp'] + 1
        
        # API限流
        time.sleep(0.1)
    
    if not all_klines:
        print("无数据")
        return
    
    # 插入数据
    inserted = 0
    for kline in all_klines:
        try:
            conn.execute(f'''
                INSERT OR REPLACE INTO {table_name} (timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', [
                kline['timestamp'],
                kline['open'],
                kline['high'],
                kline['low'],
                kline['close'],
                kline['volume']
            ])
            inserted += 1
        except Exception as e:
            # 可能因为主键冲突或其他原因
            pass
    
    conn.commit()
    print(f"✓ ({inserted} 条)")
    
    return inserted


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("多币种价格数据同步")
    print("=" * 80)
    print()
    
    # 数据库路径
    db_path = ROOT / 'data' / 'btc_price_timeseries.duckdb'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"数据库: {db_path}")
    print(f"币种数: {len(COINS_TO_SYNC)}")
    print(f"时间框架: {', '.join(TIMEFRAMES)}")
    print()
    
    # 初始化数据库
    print("1. 初始化数据库...")
    conn = init_database(db_path)
    print("   [OK] 数据库初始化完成")
    print()
    
    # 同步数据
    print("2. 同步价格数据...")
    total_inserted = 0
    
    for i, symbol in enumerate(COINS_TO_SYNC, 1):
        print(f"  [{i}/{len(COINS_TO_SYNC)}] {symbol}")
        for timeframe in TIMEFRAMES:
            inserted = sync_coin_data(conn, symbol, timeframe, days=90)
            if inserted:
                total_inserted += inserted
            time.sleep(0.2)  # API限流
        print()
    
    # 关闭连接
    conn.close()
    
    print("=" * 80)
    print("同步完成")
    print("=" * 80)
    print()
    print(f"总插入数据: {total_inserted} 条")
    print(f"数据库文件: {db_path}")
    print()


if __name__ == '__main__':
    main()
