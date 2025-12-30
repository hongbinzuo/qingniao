#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从API获取历史BTC价格数据并存储到时序库
补充10-11月的数据
"""

import sys
import requests
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def fetch_5m_candles(start_ts: int, end_ts: int) -> List[List]:
    """
    从Gate.io API获取5分钟K线数据
    
    Args:
        start_ts: 开始时间戳（秒）
        end_ts: 结束时间戳（秒）
    
    Returns:
        K线数据列表，格式: [[timestamp, volume, close, high, low, open], ...]
    """
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    all_candles = []
    
    # API限制：最多支持10000个点之前的数据
    # 5分钟K线，10000个点 = 约35天
    # 使用较小的批次，从最新时间往前获取
    current_ts = end_ts
    batch_size = 500 * 300  # 500条 * 5分钟 = 约1.7天的数据
    
    # 从后往前获取（从最新时间往前）
    while current_ts > start_ts:
        batch_start = max(current_ts - batch_size, start_ts)
        
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': '5m',
            'from': str(batch_start),
            'to': str(current_ts),
            'limit': 1000
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
                    print(f"  获取了 {len(data)} 条K线数据 ({datetime.fromtimestamp(batch_start)} 到 {datetime.fromtimestamp(current_ts)})")
                else:
                    print(f"  该时间段无数据，跳过")
                    current_ts = batch_start
                    continue
            elif response.status_code == 400:
                error_msg = response.text
                if "too long ago" in error_msg:
                    print(f"  ⚠️  数据太旧，API不支持，尝试更小的批次...")
                    # 如果数据太旧，尝试更小的批次
                    if batch_size > 100 * 300:
                        batch_size = batch_size // 2
                        continue
                    else:
                        print(f"  ❌ 无法获取更早的数据，停止")
                        break
                else:
                    print(f"  API请求失败: {response.status_code} - {error_msg[:200]}", file=sys.stderr)
                    break
            else:
                print(f"  API请求失败: {response.status_code}", file=sys.stderr)
                break
            
            # 避免请求过快
            time.sleep(0.5)
            current_ts = batch_start
            
        except Exception as e:
            print(f"  获取数据失败: {e}", file=sys.stderr)
            break
    
    # 去重并排序
    if all_candles:
        # 使用timestamp作为key去重
        seen = set()
        unique_candles = []
        for candle in all_candles:
            ts = int(candle[0])
            if ts not in seen:
                seen.add(ts)
                unique_candles.append(candle)
        
        # 按时间戳排序
        unique_candles.sort(key=lambda x: int(x[0]))
        return unique_candles
    
    return []

def store_to_timeseries(candles: List[List], ts_conn):
    """
    将K线数据存储到时序库
    
    Args:
        candles: K线数据列表
        ts_conn: 时序库连接
    """
    if not candles:
        return 0
    
    # 检查表是否存在
    tables = ts_conn.execute("SHOW TABLES").fetchall()
    table_names = [t[0] for t in tables]
    
    if 'btc_price_5m' not in table_names:
        # 创建表（如果不存在）
        ts_conn.execute('''
            CREATE TABLE btc_price_5m (
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
            existing = ts_conn.execute('''
                SELECT COUNT(*) FROM btc_price_5m WHERE timestamp = ?
            ''', [timestamp]).fetchone()[0]
            
            if existing > 0:
                skipped_count += 1
                continue
            
            # 插入数据
            ts_conn.execute('''
                INSERT INTO btc_price_5m 
                (timestamp, datetime, open, high, low, close, volume, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (timestamp, datetime_str, open_price, high, low, close, volume, created_at))
            
            inserted_count += 1
            
        except Exception as e:
            print(f"  插入数据失败: {e}", file=sys.stderr)
            continue
    
    ts_conn.commit()
    return inserted_count, skipped_count

def fetch_1h_candles_for_early_period(start_ts: int, ts_conn):
    """使用1小时K线获取更早的数据，然后插值生成5分钟数据"""
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    
    # 获取1小时K线（支持更长的历史）
    end_ts = int(datetime(2025, 11, 25, 0, 0, 0).timestamp())
    
    params = {
        'currency_pair': 'BTC_USDT',
        'interval': '1h',
        'from': str(start_ts),
        'to': str(end_ts),
        'limit': 1000
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"  获取了 {len(data)} 条1小时K线数据")
                
                # 将1小时K线转换为5分钟K线（使用相同价格）
                inserted = 0
                for candle in data:
                    timestamp_ms = int(candle[0])
                    timestamp_hour = timestamp_ms // 1000
                    volume = float(candle[1])
                    close = float(candle[2])
                    high = float(candle[3])
                    low = float(candle[4])
                    open_price = float(candle[5])
                    
                    # 为每个小时的12个5分钟K线创建数据
                    for minute_offset in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]:
                        ts_5m = timestamp_hour + minute_offset * 60
                        
                        # 检查是否已存在
                        existing = ts_conn.execute('''
                            SELECT COUNT(*) FROM btc_price_5m WHERE timestamp = ?
                        ''', [ts_5m]).fetchone()[0]
                        
                        if existing > 0:
                            continue
                        
                        dt = datetime.fromtimestamp(ts_5m)
                        datetime_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # 使用小时K线的价格（简单插值）
                        ts_5m = timestamp_hour + minute_offset * 60
                        ts_conn.execute('''
                            INSERT INTO btc_price_5m 
                            (timestamp, datetime, open, high, low, close, volume, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (ts_5m, datetime_str, open_price, high, low, close, volume / 12, created_at))
                        inserted += 1
                
                ts_conn.commit()
                print(f"  ✓ 从1小时K线生成了 {inserted} 条5分钟K线数据")
        else:
            print(f"  获取1小时K线失败: {response.status_code}")
    except Exception as e:
        print(f"  获取1小时K线失败: {e}")

def main():
    """主函数"""
    print("=" * 80)
    print("获取历史BTC价格数据（10-11月）")
    print("=" * 80)
    print()
    
    # 连接时序库
    try:
        import duckdb
        ts_file = Path(__file__).parent / "data" / "btc_price_timeseries.duckdb"
        ts_conn = duckdb.connect(str(ts_file))
        print(f"✓ 已连接时序库: {ts_file}")
    except Exception as e:
        print(f"❌ 连接时序库失败: {e}")
        return
    
    # 确定时间范围：2025-10-18 到 2025-11-30
    start_date = datetime(2025, 10, 18, 0, 0, 0)
    end_date = datetime(2025, 11, 30, 23, 59, 59)
    
    start_ts = int(start_date.timestamp())
    end_ts = int(end_date.timestamp())
    
    # 检查已有数据范围
    try:
        result = ts_conn.execute('SELECT MIN(timestamp), MAX(timestamp) FROM btc_price_5m').fetchone()
        if result[0]:
            existing_min = datetime.fromtimestamp(result[0])
            existing_max = datetime.fromtimestamp(result[1])
            print(f"现有数据范围: {existing_min} 到 {existing_max}")
            
            # 如果已有数据从11-30开始，则只需要获取到11-30
            if existing_min.date() <= datetime(2025, 11, 30).date():
                end_date = existing_min - timedelta(minutes=5)  # 到已有数据之前
                print(f"调整结束时间到: {end_date}")
                end_ts = int(end_date.timestamp())
    except:
        pass
    
    # 先尝试用1小时K线获取更早的数据（API支持更长的历史）
    print("尝试使用1小时K线获取更早的数据...")
    fetch_1h_candles_for_early_period(start_ts, ts_conn)
    
    print(f"获取时间范围: {start_date} 到 {end_date}")
    print(f"时间戳范围: {start_ts} 到 {end_ts}")
    print()
    
    # 获取数据
    print("开始从API获取数据...")
    candles = fetch_5m_candles(start_ts, end_ts)
    
    if not candles:
        print("❌ 未获取到任何数据")
        ts_conn.close()
        return
    
    print(f"✓ 总共获取了 {len(candles)} 条K线数据")
    print()
    
    # 存储到数据库
    print("存储到时序库...")
    inserted, skipped = store_to_timeseries(candles, ts_conn)
    
    print()
    print("=" * 80)
    print("完成！")
    print("=" * 80)
    print(f"新增记录: {inserted} 条")
    print(f"跳过记录: {skipped} 条（已存在）")
    print()
    
    # 显示更新后的数据范围
    result = ts_conn.execute('SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM btc_price_5m').fetchone()
    if result[0]:
        min_dt = datetime.fromtimestamp(result[0])
        max_dt = datetime.fromtimestamp(result[1])
        print(f"时序库数据范围: {min_dt} 到 {max_dt}")
        print(f"总记录数: {result[2]}")
    
    ts_conn.close()

if __name__ == '__main__':
    main()

