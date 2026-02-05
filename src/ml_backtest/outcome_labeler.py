"""Outcome labeler for ML backtest."""

from typing import Dict, List, Optional

from .config import TIMEFRAME_CONFIG


def label_signal_outcome(signal: Dict, future_klines: List[Dict]) -> Dict:
    """Label a signal's outcome based on future price action."""
    direction = signal.get("type", "long")
    entry = signal["entry"]
    sl = signal["stop_loss"]
    tp1 = signal["take_profit_1"]
    tp2 = signal["take_profit_2"]

    outcome = "EXPIRED"
    outcome_time = None
    outcome_price = None
    tp1_hit = False

    for k in future_klines:
        high, low = k["high"], k["low"]

        if direction == "long":
            # Check SL first (conservative)
            if low <= sl:
                outcome = "SL_HIT"
                outcome_time = k["timestamp"]
                outcome_price = sl
                break
            # Check TP1 first, then TP2 (TP1 is closer to entry)
            if high >= tp1 and not tp1_hit:
                tp1_hit = True
            if high >= tp2 and tp1_hit:
                outcome = "TP2_HIT"
                outcome_time = k["timestamp"]
                outcome_price = tp2
                break
        else:  # short
            if high >= sl:
                outcome = "SL_HIT"
                outcome_time = k["timestamp"]
                outcome_price = sl
                break
            # Check TP1 first, then TP2 (TP1 is closer to entry)
            if low <= tp1 and not tp1_hit:
                tp1_hit = True
            if low <= tp2 and tp1_hit:
                outcome = "TP2_HIT"
                outcome_time = k["timestamp"]
                outcome_price = tp2
                break

    if outcome == "EXPIRED" and tp1_hit:
        outcome = "TP1_HIT"

    signal["outcome"] = outcome
    signal["outcome_time"] = outcome_time
    signal["outcome_price"] = outcome_price
    return signal


def label_all_signals(
    signals: List[Dict], klines: List[Dict], timeframe: str = "15m"
) -> List[Dict]:
    """Label all signals with outcomes - OPTIMIZED VERSION."""
    config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["15m"])
    expiration_seconds = config["expiration_hours"] * 3600

    # Sort klines by timestamp once (if not already sorted)
    sorted_klines = sorted(klines, key=lambda k: k["timestamp"])

    # Group klines by symbol for faster lookup
    klines_by_symbol = {}
    for k in sorted_klines:
        symbol = k["symbol"]
        if symbol not in klines_by_symbol:
            klines_by_symbol[symbol] = []
        klines_by_symbol[symbol].append(k)

    print(f"  Processing {len(signals)} signals...")
    processed = 0

    for sig in signals:
        signal_time = sig["signal_time"]
        expiration_time = signal_time + expiration_seconds
        symbol = sig["symbol"]

        # Get klines for this symbol only
        symbol_klines = klines_by_symbol.get(symbol, [])

        # Binary search for start index
        start_idx = 0
        for i, k in enumerate(symbol_klines):
            if k["timestamp"] > signal_time:
                start_idx = i
                break

        # Get future klines (only for this symbol, starting from signal time)
        future = []
        for k in symbol_klines[start_idx:]:
            if k["timestamp"] > expiration_time:
                break
            if k["timestamp"] > signal_time:
                future.append(k)

        label_signal_outcome(sig, future)

        processed += 1
        if processed % 500 == 0:
            print(f"    Processed {processed}/{len(signals)} signals...")

    print(f"  Completed labeling {len(signals)} signals")
    return signals
