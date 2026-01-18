#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多币种价格数据同步（快速版）

只同步5分钟和15分钟数据，用于回测。
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

# 需要同步的币种列表（Top 10 + 其他常用币种）
COINS_TO_SYNC = [
    'BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'BNB', 'ADA', 'TRX', 'LINK', 'BCH',
    'DN', 'BREV', 'IP', 'STETH', 'WBTC'
]

# 只同步回测需要的时间框架
TIMEFRAMES = ['5m', '15m']


def get_klines_gateio(symbol: str, timeframe: str, limit: int = 1000) -> List[Dict]:
    """从Gate.io获取K线数据"""
    try:
        tf_map = {'5m': '5m', '15m': '15m'}
        interval = tf_map.get(timeframe, '5m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': f'{symbol}_USDT',
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
                klines = []
                for k in data:
                    klines.append({
                        'timestamp': int(k[0]) // 1000,  # 转换为秒
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
    
    return conn


def sync_coin_data(conn, symbol: str, timeframe: str, days: int = 30):
    """同步单个币种的数据（只同步最近30天）"""
    table_name = f"{symbol.lower()}_price_{timeframe}"
    
    print(f"  {symbol} {timeframe}...", end=' ', flush=True)
    
    # 获取最近30天的数据
    klines = get_klines_gateio(symbol, timeframe, limit=1000)
    
    if not klines:
        print("无数据")
        return 0
    
    # 插入数据
    inserted = 0
    for kline in klines:
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
        except Exception:
            pass
    
    conn.commit()
    print(f"✓ ({inserted} 条)")
    
    return inserted


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("多币种价格数据同步（快速版 - 只同步5m和15m）")
    print("=" * 80)
    print()
    
    # 数据库路径
    db_path = ROOT / 'data' / 'btc_price_timeseries.duckdb'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"数据库: {db_path}")
    print(f"币种数: {len(COINS_TO_SYNC)}")
    print(f"时间框架: {', '.join(TIMEFRAMES)}")
    print(f"数据范围: 最近30天（约1000条K线/币种）")
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
            inserted = sync_coin_data(conn, symbol, timeframe, days=30)
            if inserted:
                total_inserted += inserted
            time.sleep(0.1)  # API限流
    
    # 关闭连接
    conn.close()
    
    print()
    print("=" * 80)
    print("同步完成")
    print("=" * 80)
    print()
    print(f"总插入数据: {total_inserted} 条")
    print(f"数据库文件: {db_path}")
    print()


if __name__ == '__main__':
    main()
