"""Prototype: Sequence-based pattern detection.

Instead of single candle patterns, detect multi-candle sequences like:
- Downtrend → Exhaustion → Reversal → Confirmation
- Consolidation → Breakout → Pullback → Continuation
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import duckdb

from src.ml_backtest.config import DB_PATH


def classify_candle(kline, prev_kline=None):
    """Classify a single candle into a phase/type."""
    o, h, l, c = kline["open"], kline["high"], kline["low"], kline["close"]

    body = abs(c - o)
    range_size = h - l
    body_ratio = body / range_size if range_size > 0 else 0

    is_green = c > o
    body_pct = body / o * 100

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # Classify by body size
    if body_pct < 0.3:
        size = "DOJI"  # Indecision
    elif body_pct < 0.8:
        size = "SMALL"
    elif body_pct < 1.5:
        size = "MEDIUM"
    else:
        size = "BIG"

    # Classify by direction
    direction = "UP" if is_green else "DOWN"

    # Check for rejection wicks
    if lower_wick > body * 2:
        wick_type = "HAMMER"  # Bullish rejection
    elif upper_wick > body * 2:
        wick_type = "SHOOTER"  # Bearish rejection
    else:
        wick_type = "NORMAL"

    return {
        "direction": direction,
        "size": size,
        "wick": wick_type,
        "body_pct": body_pct,
        "code": f"{direction[0]}{size[0]}",  # e.g., "UB" = Up Big
    }


def encode_sequence(klines, window=7):
    """Encode last N candles into a sequence string."""
    if len(klines) < window:
        return None

    recent = klines[-window:]
    codes = []

    for i, k in enumerate(recent):
        prev = recent[i - 1] if i > 0 else None
        info = classify_candle(k, prev)
        codes.append(info["code"])

    return "".join(codes)


# Load sample data
print("Loading BTC 4h klines...")
conn = duckdb.connect(str(DB_PATH), read_only=True)
result = conn.execute("""
    SELECT timestamp, open, high, low, close, volume
    FROM ml_backtest_klines
    WHERE symbol='BTC' AND timeframe='4h'
    ORDER BY timestamp
""").fetchall()
conn.close()

klines = [
    {
        "timestamp": r[0],
        "open": r[1],
        "high": r[2],
        "low": r[3],
        "close": r[4],
        "volume": r[5],
    }
    for r in result
]

print(f"Loaded {len(klines)} klines")
print("\nSample sequence encodings:")
print("-" * 50)

# Show some sequence examples
for i in range(10, min(20, len(klines))):
    window = klines[i - 7 : i]
    seq = encode_sequence(klines[:i], window=7)
    last = klines[i - 1]
    print(f"Candle {i}: {seq} | Close: {last['close']:.0f}")
