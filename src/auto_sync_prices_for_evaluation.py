#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动补充价格数据用于信号评估
在评估信号前，自动检查并补充缺失的价格数据
"""

import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def get_timeseries_connection():
    """获取时序数据库连接"""
    try:
        import duckdb
        ts_file = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(ts_file))
        return conn
    except Exception as e:
        print(f"❌ 连接时序库失败: {e}", file=sys.stderr)
        return None

def create_table_if_not_exists(conn, timeframe: str):
    """创建表（如果不存在）"""
    table_name = f"btc_price_{timeframe}"
    
    try:
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        
        if table_name not in table_names:
            conn.execute(f'''
                CREATE TABLE {table_name} (
                    timestamp INTEGER PRIMARY KEY,
                    datetime VARCHAR NOT NULL,
                    open FLOAT NOT NULL,
                    high FLOAT NOT NULL,
                    low FLOAT NOT NULL,
                    close FLOAT NOT NULL,
                    volume FLOAT,
                    created_at VARCHAR NOT NULL
                )
            ''')
            conn.commit()
            return True
    except Exception as e:
        print(f"  创建表失败: {e}", file=sys.stderr)
    return False

def get_latest_timestamp(conn, timeframe: str) -> Optional[int]:
    """获取指定时间框架的最新时间戳"""
    table_name = f"btc_price_{timeframe}"
    try:
        result = conn.execute(f'''
            SELECT MAX(timestamp) FROM {table_name}
        ''').fetchone()
        if result and result[0]:
            return int(result[0])
    except:
        pass
    return None

def fetch_candles_from_gateio(timeframe: str, start_ts: int, end_ts: int, limit: int = 1000) -> List[List]:
    """从Gate.io获取K线数据"""
    tf_map = {
        '5m': '5m',
        '15m': '15m',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d'
    }
    interval = tf_map.get(timeframe, '5m')
    
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {
        'currency_pair': 'BTC_USDT',
        'interval': interval,
        'from': start_ts,
        'to': end_ts,
        'limit': limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                # Gate.io返回的是倒序，需要反转
                data.reverse()
                return data
    except Exception as e:
        print(f"  Gate.io获取失败: {e}", file=sys.stderr)
    
    return []

def store_candles(conn, candles: List[List], timeframe: str) -> Tuple[int, int]:
    """将K线数据存储到时序库"""
    if not candles:
        return 0, 0
    
    table_name = f"btc_price_{timeframe}"
    inserted_count = 0
    skipped_count = 0
    
    for candle in candles:
        try:
            # Gate.io格式: [timestamp(s), volume, close, high, low, open]
            timestamp = int(candle[0])
            volume = float(candle[1])
            close = float(candle[2])
            high = float(candle[3])
            low = float(candle[4])
            open_price = float(candle[5])
            
            # 转换为datetime字符串
            dt = datetime.fromtimestamp(timestamp)
            datetime_str = dt.strftime('%Y-%m-%d %H:%M:%S')
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 检查是否已存在
            existing = conn.execute(f'''
                SELECT COUNT(*) FROM {table_name} WHERE timestamp = ?
            ''', [timestamp]).fetchone()[0]
            
            if existing > 0:
                skipped_count += 1
                continue
            
            # 插入数据
            conn.execute(f'''
                INSERT INTO {table_name} 
                (timestamp, datetime, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, datetime_str, open_price, high, low, close, volume, created_at))
            
            inserted_count += 1
            
        except Exception as e:
            print(f"    插入数据失败: {e}", file=sys.stderr)
            continue
    
    conn.commit()
    return inserted_count, skipped_count

def sync_prices_for_timeframe(conn, timeframe: str, start_ts: int, end_ts: int, verbose: bool = True) -> Dict:
    """同步指定时间框架的价格数据"""
    if verbose:
        print(f"  同步 {timeframe} 数据...", file=sys.stderr)
    
    # 创建表（如果不存在）
    create_table_if_not_exists(conn, timeframe)
    
    # 获取最新时间戳
    latest_ts = get_latest_timestamp(conn, timeframe)
    
    # 确定需要同步的时间范围
    sync_start_ts = latest_ts if latest_ts else start_ts
    sync_end_ts = end_ts
    
    if sync_start_ts >= sync_end_ts:
        if verbose:
            print(f"    {timeframe} 数据已是最新", file=sys.stderr)
        return {'inserted': 0, 'skipped': 0, 'status': 'up_to_date'}
    
    # 获取数据
    candles = fetch_candles_from_gateio(timeframe, sync_start_ts, sync_end_ts, limit=1000)
    
    if not candles:
        if verbose:
            print(f"    ⚠️ 未获取到 {timeframe} 数据", file=sys.stderr)
        return {'inserted': 0, 'skipped': 0, 'status': 'no_data'}
    
    # 存储数据
    inserted, skipped = store_candles(conn, candles, timeframe)
    
    if verbose:
        print(f"    ✅ {timeframe}: 插入 {inserted} 条，跳过 {skipped} 条", file=sys.stderr)
    
    return {'inserted': inserted, 'skipped': skipped, 'status': 'success'}

def auto_sync_prices_for_evaluation(signal_time: datetime, timeframes: List[str] = None, 
                                    hours_ahead: int = 24, verbose: bool = True) -> Dict:
    """
    自动补充价格数据用于信号评估
    
    Args:
        signal_time: 信号生成时间
        timeframes: 需要同步的时间框架列表，默认 ['5m', '15m', '1h', '4h', '1d']
        hours_ahead: 同步多少小时后的数据（默认24小时）
        verbose: 是否输出详细信息
    
    Returns:
        同步结果字典
    """
    if timeframes is None:
        timeframes = ['5m', '15m', '1h', '4h', '1d']
    
    conn = get_timeseries_connection()
    if not conn:
        return {'error': '无法连接时序数据库'}
    
    # 计算时间范围
    start_ts = int(signal_time.timestamp())
    end_ts = int((signal_time + timedelta(hours=hours_ahead)).timestamp())
    
    if verbose:
        print(f"📊 自动补充价格数据", file=sys.stderr)
        print(f"  信号时间: {signal_time.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
        print(f"  时间范围: {datetime.fromtimestamp(start_ts).strftime('%Y-%m-%d %H:%M:%S')} ~ {datetime.fromtimestamp(end_ts).strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
        print("", file=sys.stderr)
    
    results = {}
    for tf in timeframes:
        result = sync_prices_for_timeframe(conn, tf, start_ts, end_ts, verbose=verbose)
        results[tf] = result
    
    conn.close()
    
    if verbose:
        total_inserted = sum(r.get('inserted', 0) for r in results.values())
        total_skipped = sum(r.get('skipped', 0) for r in results.values())
        print("", file=sys.stderr)
        print(f"✅ 同步完成: 总计插入 {total_inserted} 条，跳过 {total_skipped} 条", file=sys.stderr)
    
    return results

if __name__ == "__main__":
    # 测试：同步最近24小时的数据
    test_time = datetime.now() - timedelta(days=1)
    auto_sync_prices_for_evaluation(test_time, hours_ahead=24)


