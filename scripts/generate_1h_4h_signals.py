"""Generate signals for 1h and 4h timeframes."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json

import duckdb

from src.ml_backtest.config import DATA_DIR, DB_PATH
from src.ml_backtest.signal_generator import generate_signals_for_klines

symbols = ["BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "AVAX", "LINK"]


def load_klines(symbol: str, timeframe: str):
    """Load klines from database."""
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    result = conn.execute(
        """
        SELECT timestamp, open, high, low, close, volume
        FROM ml_backtest_klines
        WHERE symbol = ? AND timeframe = ?
        ORDER BY timestamp
        """,
        [symbol, timeframe],
    ).fetchall()
    conn.close()

    klines = []
    for row in result:
        klines.append(
            {
                "timestamp": row[0],
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
            }
        )
    return klines


print("=" * 60)
print("GENERATING 1H AND 4H SIGNALS")
print("=" * 60)

# Generate 1h signals
print("\n[1/2] Generating 1h signals...")
all_1h_signals = []
for i, symbol in enumerate(symbols, 1):
    print(f"  [{i}/{len(symbols)}] {symbol}...", end=" ", flush=True)
    try:
        klines = load_klines(symbol, "1h")
        if not klines:
            print("✗ No klines")
            continue

        signals = generate_signals_for_klines(klines, symbol, "1h")
        all_1h_signals.extend(signals)
        print(f"✓ {len(signals)} signals")
    except Exception as e:
        print(f"✗ Error: {e}")

# Save 1h signals
output_1h = DATA_DIR / "signals_1h.json"
with open(output_1h, "w") as f:
    json.dump(all_1h_signals, f, indent=2)
print(f"\nSaved {len(all_1h_signals)} signals to {output_1h}")

# Generate 4h signals
print("\n[2/2] Generating 4h signals...")
all_4h_signals = []
for i, symbol in enumerate(symbols, 1):
    print(f"  [{i}/{len(symbols)}] {symbol}...", end=" ", flush=True)
    try:
        klines = load_klines(symbol, "4h")
        if not klines:
            print("✗ No klines")
            continue

        signals = generate_signals_for_klines(klines, symbol, "4h")
        all_4h_signals.extend(signals)
        print(f"✓ {len(signals)} signals")
    except Exception as e:
        print(f"✗ Error: {e}")

# Save 4h signals
output_4h = DATA_DIR / "signals_4h.json"
with open(output_4h, "w") as f:
    json.dump(all_4h_signals, f, indent=2)
print(f"\nSaved {len(all_4h_signals)} signals to {output_4h}")

print("\n" + "=" * 60)
print("SIGNAL GENERATION COMPLETE")
print("=" * 60)
print(f"\nSummary:")
print(f"  1h signals: {len(all_1h_signals)}")
print(f"  4h signals: {len(all_4h_signals)}")
