"""Label outcomes for 1h and 4h signals."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json
from datetime import datetime

import duckdb

from src.ml_backtest.config import DATA_DIR, DB_PATH, TIMEFRAME_CONFIG


def load_klines_by_symbol(timeframe: str):
    """Load all klines grouped by symbol."""
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    result = conn.execute(
        """
        SELECT symbol, timestamp, open, high, low, close, volume
        FROM ml_backtest_klines
        WHERE timeframe = ?
        ORDER BY symbol, timestamp
        """,
        [timeframe],
    ).fetchall()
    conn.close()

    klines_by_symbol = {}
    for row in result:
        symbol = row[0]
        if symbol not in klines_by_symbol:
            klines_by_symbol[symbol] = []
        klines_by_symbol[symbol].append(
            {
                "timestamp": row[1],
                "open": row[2],
                "high": row[3],
                "low": row[4],
                "close": row[5],
                "volume": row[6],
            }
        )

    return klines_by_symbol


def label_signal_outcome(signal, klines, timeframe):
    """Label a single signal's outcome."""
    config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["15m"])
    expiration_hours = config["expiration_hours"]
    expiration_seconds = expiration_hours * 3600

    entry = signal["entry"]
    sl = signal.get("sl") or signal.get("stop_loss")
    tp1 = signal.get("tp1") or signal.get("take_profit_1")
    tp2 = signal.get("tp2") or signal.get("take_profit_2")
    signal_time = signal["signal_time"]
    direction = signal["type"]

    expiration_time = signal_time + expiration_seconds

    # Find klines after signal time
    future_klines = [k for k in klines if k["timestamp"] > signal_time]

    for kline in future_klines:
        if kline["timestamp"] > expiration_time:
            return "EXPIRED"

        high = kline["high"]
        low = kline["low"]

        if direction == "long":
            # Check SL first
            if low <= sl:
                return "SL_HIT"
            # Check TP2
            if high >= tp2:
                return "TP2_HIT"
            # Check TP1
            if high >= tp1:
                return "TP1_HIT"
        else:  # short
            # Check SL first
            if high >= sl:
                return "SL_HIT"
            # Check TP2
            if low <= tp2:
                return "TP2_HIT"
            # Check TP1
            if low <= tp1:
                return "TP1_HIT"

    return "EXPIRED"


print("=" * 60)
print("LABELING 1H AND 4H SIGNAL OUTCOMES")
print("=" * 60)

# Label 1h signals
print("\n[1/2] Labeling 1h signals...")
signals_1h_file = DATA_DIR / "signals_1h.json"
with open(signals_1h_file, "r") as f:
    signals_1h = json.load(f)

print(f"  Loading 1h klines...")
klines_1h = load_klines_by_symbol("1h")
print(
    f"  Loaded {sum(len(k) for k in klines_1h.values())} klines for {len(klines_1h)} symbols"
)

print(f"  Labeling {len(signals_1h)} signals...")
labeled_1h = []
for i, sig in enumerate(signals_1h, 1):
    if i % 100 == 0:
        print(f"    Progress: {i}/{len(signals_1h)}", end="\r", flush=True)

    symbol = sig["symbol"]
    if symbol not in klines_1h:
        continue

    outcome = label_signal_outcome(sig, klines_1h[symbol], "1h")
    sig["outcome"] = outcome
    labeled_1h.append(sig)

print(f"    Progress: {len(labeled_1h)}/{len(signals_1h)} - Done!")

# Save labeled 1h signals
output_1h = DATA_DIR / "labeled_signals_1h.json"
with open(output_1h, "w") as f:
    json.dump(labeled_1h, f, indent=2)
print(f"  Saved to {output_1h}")

# Calculate 1h statistics
outcomes_1h = {}
for sig in labeled_1h:
    outcome = sig["outcome"]
    outcomes_1h[outcome] = outcomes_1h.get(outcome, 0) + 1

print(f"\n  1h Outcomes:")
for outcome, count in sorted(outcomes_1h.items()):
    pct = count / len(labeled_1h) * 100
    print(f"    {outcome:10} {count:5} ({pct:5.1f}%)")

# Label 4h signals
print("\n[2/2] Labeling 4h signals...")
signals_4h_file = DATA_DIR / "signals_4h.json"
with open(signals_4h_file, "r") as f:
    signals_4h = json.load(f)

print(f"  Loading 4h klines...")
klines_4h = load_klines_by_symbol("4h")
print(
    f"  Loaded {sum(len(k) for k in klines_4h.values())} klines for {len(klines_4h)} symbols"
)

print(f"  Labeling {len(signals_4h)} signals...")
labeled_4h = []
for i, sig in enumerate(signals_4h, 1):
    if i % 100 == 0:
        print(f"    Progress: {i}/{len(signals_4h)}", end="\r", flush=True)

    symbol = sig["symbol"]
    if symbol not in klines_4h:
        continue

    outcome = label_signal_outcome(sig, klines_4h[symbol], "4h")
    sig["outcome"] = outcome
    labeled_4h.append(sig)

print(f"    Progress: {len(labeled_4h)}/{len(signals_4h)} - Done!")

# Save labeled 4h signals
output_4h = DATA_DIR / "labeled_signals_4h.json"
with open(output_4h, "w") as f:
    json.dump(labeled_4h, f, indent=2)
print(f"  Saved to {output_4h}")

# Calculate 4h statistics
outcomes_4h = {}
for sig in labeled_4h:
    outcome = sig["outcome"]
    outcomes_4h[outcome] = outcomes_4h.get(outcome, 0) + 1

print(f"\n  4h Outcomes:")
for outcome, count in sorted(outcomes_4h.items()):
    pct = count / len(labeled_4h) * 100
    print(f"    {outcome:10} {count:5} ({pct:5.1f}%)")

print("\n" + "=" * 60)
print("LABELING COMPLETE")
print("=" * 60)
print(f"\nSummary:")
print(f"  1h: {len(labeled_1h)} signals labeled")
print(f"  4h: {len(labeled_4h)} signals labeled")
