#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查价格数据状态
"""

import sys
from pathlib import Path
from datetime import datetime

try:
    import duckdb
except ImportError:
    print("需要安装duckdb: pip install duckdb")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
TS_FILE = ROOT / 'data' / 'btc_price_timeseries.duckdb'

if not TS_FILE.exists():
    print("❌ 价格数据库文件不存在")
    print(f"   路径: {TS_FILE}")
    sys.exit(1)

conn = duckdb.connect(str(TS_FILE))

print("=" * 80)
print("价格数据状态检查")
print("=" * 80)
print()

timeframes = ['5m', '15m', '1h', '4h', '1d']
current_time = datetime.now()

for tf in timeframes:
    table_name = f"btc_price_{tf}"
    
    try:
        # 检查表是否存在
        tables = conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        
        if table_name not in table_names:
            print(f"{tf:>4}: ❌ 表不存在")
            continue
        
        # 检查数据量
        count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        
        if count == 0:
            print(f"{tf:>4}: ⚠️  表存在但无数据")
            continue
        
        # 获取最新时间戳
        latest_ts = conn.execute(f"SELECT MAX(timestamp) FROM {table_name}").fetchone()[0]
        
        if latest_ts:
            latest_dt = datetime.fromtimestamp(int(latest_ts))
            time_diff = current_time - latest_dt
            hours_diff = time_diff.total_seconds() / 3600
            
            status = "✅" if hours_diff < 2 else "⚠️ " if hours_diff < 24 else "❌"
            
            print(f"{tf:>4}: {status} 最新数据: {latest_dt.strftime('%Y-%m-%d %H:%M:%S')} "
                  f"(距今 {hours_diff:.1f} 小时, 共 {count} 条)")
        else:
            print(f"{tf:>4}: ⚠️  无法获取最新时间戳")
    
    except Exception as e:
        print(f"{tf:>4}: ❌ 检查失败: {e}")

print()
print("=" * 80)
print("建议: 如果数据不是最新的，运行以下命令同步:")
print("  python src/sync_btc_prices_daily.py")
print("=" * 80)

conn.close()
