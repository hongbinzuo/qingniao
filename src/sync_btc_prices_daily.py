#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC价格数据每日同步任务
检查时序数据库的最新时间戳，获取缺失的BTC价格数据并补充
支持时间框架：5分钟、15分钟、1小时、4小时、1天
"""

import sys
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

try:
    from system_logger import get_system_logger
    SYSTEM_LOGGER_AVAILABLE = True
except ImportError:
    SYSTEM_LOGGER_AVAILABLE = False

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 时间框架配置
TIMEFRAMES = {
    '5m': {'interval': '5m', 'seconds': 300},
    '15m': {'interval': '15m', 'seconds': 900},
    '1h': {'interval': '1h', 'seconds': 3600},
    '4h': {'interval': '4h', 'seconds': 14400},
    '1d': {'interval': '1d', 'seconds': 86400}
}

def get_timeseries_connection():
    """获取时序数据库连接"""
    try:
        import duckdb
        ts_file = Path(__file__).parent / "data" / "btc_price_timeseries.duckdb"
        # 如果文件不存在，创建它
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
            print(f"  ✓ 创建表: {table_name}")
            return True
        return False
    except Exception as e:
        print(f"  ❌ 创建表失败 {table_name}: {e}", file=sys.stderr)
        return False

def get_latest_timestamp(conn, timeframe: str) -> Optional[int]:
    """获取指定时间框架表的最新时间戳"""
    table_name = f"btc_price_{timeframe}"
    
    try:
        result = conn.execute(f'''
            SELECT MAX(timestamp) FROM {table_name}
        ''').fetchone()
        
        if result and result[0]:
            return int(result[0])
        return None
    except Exception as e:
        # 表可能不存在
        return None

def fetch_candles(timeframe: str, start_ts: int, end_ts: int, limit: int = 1000) -> List[List]:
    """
    从Gate.io API获取K线数据
    
    Args:
        timeframe: 时间框架 ('5m', '15m', '1h', '4h', '1d')
        start_ts: 开始时间戳（秒）
        end_ts: 结束时间戳（秒）
        limit: 最大获取数量
    
    Returns:
        K线数据列表，格式: [[timestamp(ms), volume, close, high, low, open], ...]
    """
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    interval = TIMEFRAMES[timeframe]['interval']
    
    all_candles = []
    current_ts = end_ts
    
    # 根据时间框架计算批次大小
    tf_seconds = TIMEFRAMES[timeframe]['seconds']
    batch_size = min(500 * tf_seconds, end_ts - start_ts)  # 最多500条K线
    
    while current_ts > start_ts:
        batch_start = max(current_ts - batch_size, start_ts)
        
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': interval,
            'from': str(batch_start),
            'to': str(current_ts),
            'limit': min(limit, 1000)
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data:
                    # K线格式: [timestamp(ms), volume, close, high, low, open]
                    # 按时间戳排序（从旧到新）
                    data.sort(key=lambda x: int(x[0]))
                    all_candles.extend(data)
                    print(f"    获取了 {len(data)} 条K线 ({datetime.fromtimestamp(batch_start)} 到 {datetime.fromtimestamp(current_ts)})")
                else:
                    print(f"    该时间段无数据，跳过")
                    current_ts = batch_start
                    continue
            elif response.status_code == 400:
                error_msg = response.text
                if "too long ago" in error_msg.lower():
                    print(f"    ⚠️  数据太旧，API不支持")
                    break
                else:
                    print(f"    API请求失败: {response.status_code} - {error_msg[:200]}", file=sys.stderr)
                    break
            else:
                print(f"    API请求失败: {response.status_code}", file=sys.stderr)
                break
            
            # 避免请求过快
            time.sleep(0.5)
            current_ts = batch_start
            
        except Exception as e:
            print(f"    获取数据失败: {e}", file=sys.stderr)
            break
    
    # 去重并排序
    if all_candles:
        seen = set()
        unique_candles = []
        for candle in all_candles:
            ts = int(candle[0])
            if ts not in seen:
                seen.add(ts)
                unique_candles.append(candle)
        
        unique_candles.sort(key=lambda x: int(x[0]))
        return unique_candles
    
    return []

def store_candles(conn, candles: List[List], timeframe: str) -> Tuple[int, int]:
    """
    将K线数据存储到时序库
    
    Returns:
        (插入数量, 跳过数量)
    """
    if not candles:
        return 0, 0
    
    table_name = f"btc_price_{timeframe}"
    inserted_count = 0
    skipped_count = 0
    
    for candle in candles:
        try:
            # K线格式: [timestamp(ms), volume, close, high, low, open]
            timestamp_ms = int(candle[0])
            timestamp = timestamp_ms // 1000  # 转换为秒
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

def sync_timeframe(conn, timeframe: str) -> Dict:
    """同步指定时间框架的数据"""
    print(f"\n{'='*60}")
    print(f"同步 {timeframe} 时间框架数据")
    print(f"{'='*60}")
    
    # 确保表存在
    create_table_if_not_exists(conn, timeframe)
    
    # 获取最新时间戳
    latest_ts = get_latest_timestamp(conn, timeframe)
    
    if latest_ts:
        latest_dt = datetime.fromtimestamp(latest_ts)
        print(f"  最新数据时间: {latest_dt}")
        # 从最新时间戳的下一个周期开始
        start_ts = latest_ts + TIMEFRAMES[timeframe]['seconds']
    else:
        print(f"  表中无数据，从7天前开始获取")
        # 如果表为空，获取最近7天的数据
        start_ts = int((datetime.now() - timedelta(days=7)).timestamp())
    
    # 结束时间：当前时间
    end_ts = int(datetime.now().timestamp())
    
    if start_ts >= end_ts:
        print(f"  ✓ 数据已是最新，无需更新")
        return {'timeframe': timeframe, 'inserted': 0, 'skipped': 0, 'status': 'up_to_date'}
    
    start_dt = datetime.fromtimestamp(start_ts)
    end_dt = datetime.fromtimestamp(end_ts)
    print(f"  获取时间范围: {start_dt} 到 {end_dt}")
    
    # 获取数据
    print(f"  正在从API获取数据...")
    candles = fetch_candles(timeframe, start_ts, end_ts)
    
    if not candles:
        print(f"  ⚠️  未获取到任何数据")
        return {'timeframe': timeframe, 'inserted': 0, 'skipped': 0, 'status': 'no_data'}
    
    print(f"  ✓ 获取了 {len(candles)} 条K线数据")
    
    # 存储数据
    print(f"  正在存储到时序库...")
    inserted, skipped = store_candles(conn, candles, timeframe)
    
    print(f"  ✓ 完成: 新增 {inserted} 条，跳过 {skipped} 条（已存在）")
    
    return {
        'timeframe': timeframe,
        'inserted': inserted,
        'skipped': skipped,
        'status': 'success'
    }

def main():
    """主函数"""
    print("=" * 80)
    print("BTC价格数据每日同步任务")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    # 连接时序库
    conn = get_timeseries_connection()
    if not conn:
        print("❌ 无法连接时序库，任务终止")
        return 1
    
    print(f"✓ 已连接时序库")
    print()
    
    # 同步所有时间框架
    results = []
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for timeframe in ['5m', '15m', '1h', '4h', '1d']:
        try:
            result = sync_timeframe(conn, timeframe)
            results.append(result)
            
            # 记录价格同步操作
            if SYSTEM_LOGGER_AVAILABLE:
                get_system_logger().log_price_sync(
                    timeframe=timeframe,
                    records_synced=result.get('inserted', 0),
                    start_time=start_time,
                    end_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    success=result.get('status') in ['success', 'up_to_date'],
                    error=result.get('error')
                )
        except Exception as e:
            print(f"  ❌ 同步 {timeframe} 失败: {e}", file=sys.stderr)
            error_result = {
                'timeframe': timeframe,
                'inserted': 0,
                'skipped': 0,
                'status': 'error',
                'error': str(e)
            }
            results.append(error_result)
            
            # 记录错误
            if SYSTEM_LOGGER_AVAILABLE:
                get_system_logger().log_price_sync(
                    timeframe=timeframe,
                    records_synced=0,
                    start_time=start_time,
                    end_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    success=False,
                    error=str(e)
                )
    
    # 关闭连接
    conn.close()
    
    # 汇总结果
    print()
    print("=" * 80)
    print("同步任务完成")
    print("=" * 80)
    print()
    
    total_inserted = 0
    total_skipped = 0
    
    for result in results:
        timeframe = result['timeframe']
        inserted = result['inserted']
        skipped = result['skipped']
        status = result['status']
        
        total_inserted += inserted
        total_skipped += skipped
        
        status_icon = '✓' if status == 'success' or status == 'up_to_date' else '⚠️'
        print(f"{status_icon} {timeframe:4s}: 新增 {inserted:5d} 条, 跳过 {skipped:5d} 条 - {status}")
    
    print()
    print(f"总计: 新增 {total_inserted} 条, 跳过 {total_skipped} 条")
    print()
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n任务被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 任务执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)




