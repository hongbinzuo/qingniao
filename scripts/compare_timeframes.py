"""Compare signal quality across 15m, 1h, and 4h timeframes."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json

from src.ml_backtest.config import DATA_DIR

print("=" * 70)
print("TIMEFRAME COMPARISON: 15m vs 1h vs 4h")
print("=" * 70)

# Load labeled signals for all timeframes
print("\nLoading labeled signals...")
with open(DATA_DIR / "labeled_signals.json", "r") as f:
    signals_15m = json.load(f)
with open(DATA_DIR / "labeled_signals_1h.json", "r") as f:
    signals_1h = json.load(f)
with open(DATA_DIR / "labeled_signals_4h.json", "r") as f:
    signals_4h = json.load(f)

print(f"  15m: {len(signals_15m)} signals")
print(f"  1h:  {len(signals_1h)} signals")
print(f"  4h:  {len(signals_4h)} signals")


# Calculate statistics for each timeframe
def calculate_stats(signals, timeframe_name):
    """Calculate outcome statistics."""
    outcomes = {}
    for sig in signals:
        outcome = sig.get("outcome", "UNKNOWN")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1

    total = len(signals)
    sl_hit = outcomes.get("SL_HIT", 0)
    tp1_hit = outcomes.get("TP1_HIT", 0)
    tp2_hit = outcomes.get("TP2_HIT", 0)
    expired = outcomes.get("EXPIRED", 0)

    # Success = TP1 or TP2 hit
    success = tp1_hit + tp2_hit
    success_rate = (success / total * 100) if total > 0 else 0
    sl_rate = (sl_hit / total * 100) if total > 0 else 0

    return {
        "timeframe": timeframe_name,
        "total": total,
        "sl_hit": sl_hit,
        "tp1_hit": tp1_hit,
        "tp2_hit": tp2_hit,
        "expired": expired,
        "success": success,
        "success_rate": success_rate,
        "sl_rate": sl_rate,
    }


stats_15m = calculate_stats(signals_15m, "15m")
stats_1h = calculate_stats(signals_1h, "1h")
stats_4h = calculate_stats(signals_4h, "4h")

print("\n" + "=" * 70)
print("OUTCOME DISTRIBUTION")
print("=" * 70)

# Print detailed outcome table
print(
    f"\n{'Timeframe':<10} {'Total':>7} {'SL_HIT':>7} {'TP1_HIT':>8} {'TP2_HIT':>8} {'EXPIRED':>8}"
)
print("-" * 70)
for stats in [stats_15m, stats_1h, stats_4h]:
    print(
        f"{stats['timeframe']:<10} {stats['total']:>7} "
        f"{stats['sl_hit']:>7} {stats['tp1_hit']:>8} "
        f"{stats['tp2_hit']:>8} {stats['expired']:>8}"
    )

print("\n" + "=" * 70)
print("SUCCESS RATES (TP1 or TP2 Hit)")
print("=" * 70)

print(
    f"\n{'Timeframe':<10} {'Success Rate':>15} {'SL Hit Rate':>15} {'Expired Rate':>15}"
)
print("-" * 70)
for stats in [stats_15m, stats_1h, stats_4h]:
    expired_rate = (
        (stats["expired"] / stats["total"] * 100) if stats["total"] > 0 else 0
    )
    print(
        f"{stats['timeframe']:<10} {stats['success_rate']:>14.1f}% "
        f"{stats['sl_rate']:>14.1f}% {expired_rate:>14.1f}%"
    )

print("\n" + "=" * 70)
print("KEY FINDINGS")
print("=" * 70)

# Compare success rates
best_success = max([stats_15m, stats_1h, stats_4h], key=lambda x: x["success_rate"])
worst_sl = min([stats_15m, stats_1h, stats_4h], key=lambda x: x["sl_rate"])

print(
    f"\n✓ Best Success Rate: {best_success['timeframe']} ({best_success['success_rate']:.1f}%)"
)
print(f"✓ Lowest SL Hit Rate: {worst_sl['timeframe']} ({worst_sl['sl_rate']:.1f}%)")

# Calculate improvement
improvement_1h = stats_1h["success_rate"] - stats_15m["success_rate"]
improvement_4h = stats_4h["success_rate"] - stats_15m["success_rate"]

print(f"\nImprovement over 15m baseline:")
print(f"  1h:  {improvement_1h:+.1f} percentage points")
print(f"  4h:  {improvement_4h:+.1f} percentage points")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)

if best_success["timeframe"] == "15m":
    print("\n15m timeframe produces the best signals.")
elif best_success["timeframe"] == "1h":
    print("\n1h timeframe produces significantly better signals than 15m.")
    print("Recommendation: Use 1h timeframe for signal generation.")
else:
    print("\n4h timeframe produces the best signals.")
    print("Recommendation: Use 4h timeframe for signal generation.")

print("\n" + "=" * 70)
