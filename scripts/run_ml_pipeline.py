"""Run full ML backtest pipeline - Phase 2-5 - OPTIMIZED with concurrency."""

import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import duckdb

from src.ml_backtest.config import DATA_DIR, DB_PATH
from src.ml_backtest.outcome_labeler import label_all_signals
from src.ml_backtest.signal_generator import generate_signals_for_klines


def load_klines_from_db(symbol: str, timeframe: str = "15m"):
    """Load klines from DuckDB - READ ONLY mode for concurrent access."""
    # Use read_only=True to allow multiple processes to access simultaneously
    conn = duckdb.connect(str(DB_PATH), read_only=True)
    rows = conn.execute(
        "SELECT timestamp, open, high, low, close, volume FROM ml_backtest_klines "
        "WHERE symbol = ? AND timeframe = ? ORDER BY timestamp",
        [symbol, timeframe],
    ).fetchall()
    conn.close()

    return [
        {
            "timestamp": r[0],
            "open": r[1],
            "high": r[2],
            "low": r[3],
            "close": r[4],
            "volume": r[5],
            "symbol": symbol,  # Add symbol to kline data
        }
        for r in rows
    ]


def process_coin_signals(symbol: str, timeframe: str = "15m"):
    """Process a single coin - generate signals (for parallel execution)."""
    klines = load_klines_from_db(symbol, timeframe)
    if not klines:
        return symbol, [], 0

    signals = generate_signals_for_klines(klines, symbol, timeframe)
    return symbol, signals, len(klines)


def process_coin_labeling(symbol: str, signals: list, timeframe: str = "15m"):
    """Label outcomes for a single coin (for parallel execution)."""
    if not signals:
        return symbol, []

    klines = load_klines_from_db(symbol, timeframe)
    labeled = label_all_signals(signals, klines, timeframe)

    outcomes = {}
    for s in labeled:
        o = s.get("outcome", "UNKNOWN")
        outcomes[o] = outcomes.get(o, 0) + 1

    return symbol, labeled, outcomes


def run_pipeline():
    """Run full ML backtest pipeline."""
    symbols = ["BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "AVAX", "LINK"]
    timeframe = "15m"

    print("=" * 50)
    print("ML BACKTEST PIPELINE (OPTIMIZED - PARALLEL)")
    print("=" * 50)

    # Phase 2: Generate signals (PARALLEL)
    print("\n[Phase 2] Generating signals (parallel processing)...")
    all_signals = []

    # Use ProcessPoolExecutor for true parallelism (bypasses GIL)
    with ProcessPoolExecutor(max_workers=4) as executor:
        # Submit all coin processing tasks
        future_to_symbol = {
            executor.submit(process_coin_signals, sym, timeframe): sym
            for sym in symbols
        }

        # Collect results as they complete
        for future in as_completed(future_to_symbol):
            symbol, signals, kline_count = future.result()
            if kline_count == 0:
                print(f"  {symbol}: no klines")
            else:
                print(f"  {symbol}: {kline_count} klines -> {len(signals)} signals")
                all_signals.extend(signals)

    print(f"\nTotal signals: {len(all_signals)}")

    if not all_signals:
        print("No signals generated!")
        return

    # Phase 3: Label outcomes (PARALLEL)
    print("\n[Phase 3] Labeling outcomes (parallel processing)...")

    # Group signals by symbol
    signals_by_symbol = {}
    for sig in all_signals:
        sym = sig.get("symbol")
        if sym not in signals_by_symbol:
            signals_by_symbol[sym] = []
        signals_by_symbol[sym].append(sig)

    all_labeled = []

    # Use ProcessPoolExecutor for parallel labeling
    with ProcessPoolExecutor(max_workers=4) as executor:
        future_to_symbol = {
            executor.submit(process_coin_labeling, sym, sigs, timeframe): sym
            for sym, sigs in signals_by_symbol.items()
        }

        for future in as_completed(future_to_symbol):
            symbol, labeled, outcomes = future.result()
            if labeled:
                print(f"  {symbol}: {outcomes}")
                all_labeled.extend(labeled)

    # Summary
    print("\n" + "-" * 40)
    print("OUTCOME SUMMARY:")
    outcomes = {}
    for s in all_labeled:
        o = s.get("outcome", "UNKNOWN")
        outcomes[o] = outcomes.get(o, 0) + 1

    for o, cnt in sorted(outcomes.items()):
        pct = cnt / len(all_labeled) * 100
        print(f"  {o}: {cnt} ({pct:.1f}%)")

    # Save to JSON
    output_file = DATA_DIR / "labeled_signals.json"
    with open(output_file, "w") as f:
        json.dump(all_labeled, f, indent=2)
    print(f"\nSaved {len(all_labeled)} signals to {output_file}")

    return all_labeled


if __name__ == "__main__":
    run_pipeline()
