"""Deep analysis of successful vs failed signals."""

import json
from pathlib import Path

import duckdb

# Load signals
signals_file = Path("data/ml_backtest/labeled_signals.json")
signals = json.load(open(signals_file))

good = [s for s in signals if s["outcome"] == "TP2_HIT"]
bad = [s for s in signals if s["outcome"] == "SL_HIT"]

print("=" * 60)
print("DEEP ANALYSIS: What Makes Signals Successful?")
print("=" * 60)
print(f"\nGood signals: {len(good)} (31%)")
print(f"Bad signals: {len(bad)} (69%)")

# 1. Risk/Reward Analysis
print("\n" + "=" * 60)
print("1. RISK/REWARD RATIO")
print("=" * 60)


def calc_rr(s):
    entry = s["entry"]
    sl = s["stop_loss"]
    tp2 = s["take_profit_2"]
    risk = abs(sl - entry)
    reward = abs(tp2 - entry)
    return reward / risk if risk > 0 else 0


good_rr = [calc_rr(s) for s in good]
bad_rr = [calc_rr(s) for s in bad]

print(f"Good signals avg R:R: {sum(good_rr) / len(good_rr):.2f}")
print(f"Bad signals avg R:R: {sum(bad_rr) / len(bad_rr):.2f}")

# 2. Time Analysis
print("\n" + "=" * 60)
print("2. TIME OF DAY")
print("=" * 60)

from datetime import datetime


def get_hour(ts):
    return datetime.fromtimestamp(ts).hour


for name, start, end in [
    ("Asian 0-8h", 0, 8),
    ("EU 8-16h", 8, 16),
    ("US 16-24h", 16, 24),
]:
    g = sum(1 for s in good if start <= get_hour(s["signal_time"]) < end)
    b = sum(1 for s in bad if start <= get_hour(s["signal_time"]) < end)
    if g + b > 0:
        print(f"{name}: {g / (g + b) * 100:.1f}% success ({g}/{g + b})")
