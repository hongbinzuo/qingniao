#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试价格关联"""

import sys
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager
import duckdb

db = TraderDBManager('de')
conn = db._get_connection()

# 获取一个没有价格的观点
vp = conn.execute('''
    SELECT id, timestamp
    FROM trader_viewpoints
    WHERE btc_price IS NULL AND timestamp IS NOT NULL
    LIMIT 1
''').fetchone()

if vp:
    vp_id, vp_timestamp = vp[0], vp[1]
    print(f"测试观点 ID: {vp_id}")
    print(f"时间戳: {vp_timestamp}")
    
    # 解析时间戳
    try:
        dt = datetime.fromisoformat(vp_timestamp.replace('Z', '+00:00'))
        # 时间戳应该是UTC时间戳，但价格数据库可能使用的是本地时间戳
        # 检查价格数据库的时间戳格式
        ts_utc = int(dt.timestamp())
        # 如果有时区偏移（+08:00），减去8小时
        if '+08:00' in vp_timestamp or dt.tzinfo:
            ts = ts_utc - 8 * 3600  # 减去8小时
        else:
            ts = ts_utc
        print(f"UTC时间戳: {ts_utc}")
        print(f"调整后时间戳: {ts}")
        print(f"日期时间: {dt}")
    except Exception as e:
        print(f"解析失败: {e}")
        sys.exit(1)
    
    # 查询价格
    price_db = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
    if price_db.exists():
        price_conn = duckdb.connect(str(price_db))
        
        # 检查价格数据范围
        price_range = price_conn.execute('''
            SELECT MIN(timestamp) as min_ts, MAX(timestamp) as max_ts
            FROM btc_price_5m
        ''').fetchone()
        
        print(f"价格数据范围: {price_range[0]} - {price_range[1]}")
        print(f"目标时间戳: {ts}")
        
        # 使用datetime字段查询
        dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        print(f"查询日期时间: {dt_str}")
        
        price_result = price_conn.execute('''
            SELECT close, datetime
            FROM btc_price_5m
            WHERE datetime <= ? AND datetime >= datetime(?, '-1 day')
            ORDER BY datetime DESC
            LIMIT 1
        ''', [dt_str, dt_str]).fetchone()
        
        if price_result:
            price, price_dt = price_result[0], price_result[1]
            print(f"找到价格: {price} (日期时间: {price_dt})")
        else:
            print("未找到价格")
            # 尝试查找最近的数据
            recent = price_conn.execute('SELECT datetime, close FROM btc_price_5m ORDER BY datetime DESC LIMIT 1').fetchone()
            if recent:
                print(f"最近的价格数据: {recent[1]} ({recent[0]})")
        
        price_conn.close()
    else:
        print(f"价格数据库不存在: {price_db}")

db.close()

