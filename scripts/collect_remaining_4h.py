"""Collect remaining 4h klines for coins that are missing."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import time

import duckdb

from src.ml_backtest.config import DB_PATH
from src.ml_backtest.data_collector import date_to_ts, fetch_klines, save_klines

# Skip BTC since it already has 4h data
symbols = ["ETH", "XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "AVAX", "LINK"]
start_date = "2025-11-04"
end_date = "2026-02-02"

start_ts = date_to_ts(start_date)
end_ts = date_to_ts(end_date)

print("=" * 60)
print("COLLECTING REMAINING 4H KLINES")
print("=" * 60)

for i, symbol in enumerate(symbols, 1):
    print(f"[{i}/{len(symbols)}] {symbol}...", end=" ", flush=True)
    try:
        klines = fetch_klines(symbol, "4h", start_ts, end_ts)
        if klines:
            save_klines(symbol, "4h", klines)
            print(f"✓ {len(klines)} klines")
        else:
            print(f"✗ No data")
    except Exception as e:
        print(f"✗ Error: {e}")
    time.sleep(0.5)

print("\n" + "=" * 60)
print("COLLECTION COMPLETE")
print("=" * 60)

# Show summary
conn = duckdb.connect(str(DB_PATH), read_only=True)
result = conn.execute(
    "SELECT timeframe, COUNT(*) FROM ml_backtest_klines GROUP BY timeframe ORDER BY timeframe"
).fetchall()
print("\nDatabase summary:")
for tf, count in result:
    print(f"  {tf}: {count:,} klines")
conn.close()
