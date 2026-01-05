#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查价格数据库格式"""

import sys
from pathlib import Path
import duckdb

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

price_db = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"

if not price_db.exists():
    print(f"价格数据库不存在: {price_db}")
    sys.exit(1)

conn = duckdb.connect(str(price_db))

# 检查数据范围
print("价格数据库信息:")
print("-" * 60)

# 检查datetime格式
rows = conn.execute('''
    SELECT datetime, close, timestamp
    FROM btc_price_5m
    ORDER BY datetime DESC
    LIMIT 5
''').fetchall()

print("\n最新的5条数据:")
for r in rows:
    print(f"  datetime: {r[0]}, close: {r[1]}, timestamp: {r[2]}")

# 检查2025-10-18的数据
rows = conn.execute('''
    SELECT datetime, close
    FROM btc_price_5m
    WHERE datetime >= '2025-10-17' AND datetime <= '2025-10-19'
    ORDER BY datetime
    LIMIT 5
''').fetchall()

print("\n2025-10-18附近的数据:")
if rows:
    for r in rows:
        print(f"  {r[0]}: {r[1]}")
else:
    print("  未找到数据")

# 检查数据总数
count = conn.execute('SELECT COUNT(*) FROM btc_price_5m').fetchone()[0]
print(f"\n总数据量: {count}")

# 检查时间范围
min_max = conn.execute('SELECT MIN(datetime), MAX(datetime) FROM btc_price_5m').fetchone()
print(f"时间范围: {min_max[0]} 到 {min_max[1]}")

conn.close()



