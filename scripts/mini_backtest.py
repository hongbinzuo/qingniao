"""Run mini backtest to generate labeled signals for analysis."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime, timedelta, timezone

from src.ml_backtest.data_collector import fetch_klines_gate
from src.ml_backtest.outcome_labeler import label_all_signals
from src.ml_backtest.signal_generator import generate_signals_for_klines


def run_mini_backtest():
    """Run a mini backtest on 3 coins for 2 days."""
    coins = ["BTC", "ETH", "SOL"]
    timeframe = "15m"

    # Use recent 2 days for faster results
    end_time = datetime.now(timezone.utc) - timedelta(days=1)
    start_time = end_time - timedelta(days=2)

    print(f"Mini backtest: {coins}")
    print(f"Period: {start_time.date()} to {end_time.date()}")
    print(f"Timeframe: {timeframe}")

    all_signals = []
    klines_cache = {}

    for coin in coins:
        print(f"\nProcessing {coin}...")

        # Collect klines (timestamps in seconds for Gate.io)
        klines = fetch_klines_gate(
            coin,
            timeframe,
            int(start_time.timestamp()),
            int(end_time.timestamp()),
        )

        if not klines:
            print(f"  No klines for {coin}")
            continue

        print(f"  Collected {len(klines)} klines")
        klines_cache[coin] = klines

        # Generate signals
        signals = generate_signals_for_klines(klines, coin, timeframe)
        print(f"  Generated {len(signals)} signals")

        # Label outcomes
        labeled = label_all_signals(signals, klines, timeframe)
        print(f"  Labeled {len(labeled)} signals")

        all_signals.extend(labeled)

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Total signals: {len(all_signals)}")

    outcomes = {}
    for sig in all_signals:
        o = sig.get("outcome", "UNKNOWN")
        outcomes[o] = outcomes.get(o, 0) + 1

    for outcome, count in sorted(outcomes.items()):
        pct = count / len(all_signals) * 100 if all_signals else 0
        print(f"  {outcome}: {count} ({pct:.1f}%)")

    # Save results
    os.makedirs("data/ml_backtest", exist_ok=True)
    results = {
        "coins": coins,
        "timeframe": timeframe,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "labeled_signals": all_signals,
    }

    with open("data/ml_backtest/mini_backtest_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to data/ml_backtest/mini_backtest_results.json")
    return all_signals


if __name__ == "__main__":
    run_mini_backtest()
