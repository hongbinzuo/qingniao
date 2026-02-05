"""Signal generator for ML backtest - OPTIMIZED."""

import bisect
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from abu.detectors import detect_all_1h, detect_all_15m

from .config import TIMEFRAME_CONFIG


def generate_signals_for_klines(
    klines: List[Dict], symbol: str, timeframe: str = "15m"
) -> List[Dict]:
    """Generate signals at regular intervals - OPTIMIZED with binary search."""
    if len(klines) < 100:
        return []

    config = TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG["15m"])
    interval_hours = config["signal_interval_hours"]
    interval_seconds = interval_hours * 3600

    # Select appropriate detector function based on timeframe
    detector_map = {
        "15m": detect_all_15m,
        "1h": detect_all_1h,
        "4h": detect_all_1h,  # Use 1h detector for 4h (same logic, stricter)
    }
    detector_func = detector_map.get(timeframe, detect_all_15m)

    # Pre-build timestamp list for binary search (O(1) instead of O(n))
    timestamps = [k["timestamp"] for k in klines]

    signals = []
    start_ts = klines[0]["timestamp"]
    end_ts = klines[-1]["timestamp"]

    current_ts = start_ts + 100 * 900  # Skip first 100 candles for lookback

    while current_ts < end_ts:
        # Binary search for index (O(log n) instead of O(n))
        idx = bisect.bisect_right(timestamps, current_ts)

        if idx < 50:
            current_ts += interval_seconds
            continue

        window = klines[:idx]
        detected = detector_func(window)

        for sig in detected:
            sig["symbol"] = symbol
            sig["timeframe"] = timeframe
            sig["signal_time"] = current_ts
            signals.append(sig)

        current_ts += interval_seconds

    return signals
