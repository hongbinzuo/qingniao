"""Analyze which sequences lead to successful vs failed signals."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json
from collections import defaultdict

import duckdb

from src.ml_backtest.config import DATA_DIR, DB_PATH


def classify_candle(kline):
    """Classify candle into code."""
    o, h, l, c = kline["open"], kline["high"], kline["low"], kline["close"]

    body = abs(c - o)
    body_pct = body / o * 100
    is_green = c > o

    # Size classification
    if body_pct < 0.3:
        size = "D"  # Doji
    elif body_pct < 0.8:
        size = "S"  # Small
    elif body_pct < 1.5:
        size = "M"  # Medium
    else:
        size = "B"  # Big

    direction = "U" if is_green else "D"
    return f"{direction}{size}"


def get_sequence_before_signal(klines, signal_time, window=7):
    """Get the candle sequence before a signal."""
    # Find candles before signal time
    before = [k for k in klines if k["timestamp"] < signal_time]
    if len(before) < window:
        return None

    recent = before[-window:]
    codes = [classify_candle(k) for k in recent]
    return "".join(codes)


# Load klines
print("Loading klines...")
conn = duckdb.connect(str(DB_PATH), read_only=True)

klines_by_symbol = {}
result = conn.execute("""
    SELECT symbol, timestamp, open, high, low, close
    FROM ml_backtest_klines
    WHERE timeframe='4h'
    ORDER BY symbol, timestamp
""").fetchall()
conn.close()

for r in result:
    sym = r[0]
    if sym not in klines_by_symbol:
        klines_by_symbol[sym] = []
    klines_by_symbol[sym].append(
        {"timestamp": r[1], "open": r[2], "high": r[3], "low": r[4], "close": r[5]}
    )

print(f"Loaded klines for {len(klines_by_symbol)} symbols")
