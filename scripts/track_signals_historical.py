"""
Historical Signal Tracker - Check signals against ALL historical price data
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


class HistoricalSignalTracker:
    def __init__(self):
        self.tracking_file = ROOT / "data" / "signal_tracking.json"
        self.signals = self.load_signals()

    def load_signals(self):
        if self.tracking_file.exists():
            with open(self.tracking_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_signals(self):
        with open(self.tracking_file, "w", encoding="utf-8") as f:
            json.dump(self.signals, f, indent=2, ensure_ascii=False)

    def get_historical_klines(self, symbol, interval, from_time, to_time=None):
        if to_time is None:
            to_time = int(time.time())

        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            "currency_pair": symbol,
            "interval": interval,
            "from": from_time,
            "to": to_time,
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            return response.json()
        except Exception as e:
            print(f"[ERROR] Failed to fetch K-lines: {e}")
            return []

    def check_signal_against_history(self, signal):
        created_time = datetime.fromisoformat(signal["created_at"])
        from_timestamp = int(created_time.timestamp())

        interval_map = {"5m": "5m", "15m": "15m", "1h": "1h"}
        interval = interval_map.get(signal["timeframe"], "5m")

        print(
            f"\nSignal #{signal['signal_id']}: {signal['timeframe']} {signal['direction']}"
        )
        print(f"  Fetching {interval} data from {created_time}...")

        klines = self.get_historical_klines(signal["symbol"], interval, from_timestamp)

        if not klines:
            print(f"  No data available")
            return signal

        entry = signal["entry_price"]
        stop = signal["stop_loss"]
        target = signal["target_price"]
        direction = signal["direction"]

        print(f"  Checking {len(klines)} candles...")
        print(f"  Entry: ${entry:,.2f}, Stop: ${stop:,.2f}, Target: ${target:,.2f}")

        for candle in klines:
            timestamp = int(candle[0])
            high = float(candle[3])
            low = float(candle[4])
            close = float(candle[2])
            candle_time = datetime.fromtimestamp(timestamp)

            # Check if stop or target hit
            if direction == "LONG":
                if low <= stop:
                    signal["status"] = "stopped"
                    signal["exit_price"] = stop
                    signal["exit_time"] = candle_time.isoformat()
                    signal["pnl_percent"] = round(((stop - entry) / entry) * 100, 2)
                    print(f"  STOP HIT at {candle_time}: ${low:,.2f} <= ${stop:,.2f}")
                    return signal
                elif high >= target:
                    signal["status"] = "target_hit"
                    signal["exit_price"] = target
                    signal["exit_time"] = candle_time.isoformat()
                    signal["pnl_percent"] = round(((target - entry) / entry) * 100, 2)
                    print(
                        f"  TARGET HIT at {candle_time}: ${high:,.2f} >= ${target:,.2f}"
                    )
                    return signal
            else:  # SHORT
                if high >= stop:
                    signal["status"] = "stopped"
                    signal["exit_price"] = stop
                    signal["exit_time"] = candle_time.isoformat()
                    signal["pnl_percent"] = round(((entry - stop) / entry) * 100, 2)
                    print(f"  STOP HIT at {candle_time}: ${high:,.2f} >= ${stop:,.2f}")
                    return signal
                elif low <= target:
                    signal["status"] = "target_hit"
                    signal["exit_price"] = target
                    signal["exit_time"] = candle_time.isoformat()
                    signal["pnl_percent"] = round(((entry - target) / entry) * 100, 2)
                    print(
                        f"  TARGET HIT at {candle_time}: ${low:,.2f} <= ${target:,.2f}"
                    )
                    return signal

        # Still active
        last_close = float(klines[-1][2])
        if direction == "LONG":
            signal["pnl_percent"] = round(((last_close - entry) / entry) * 100, 2)
        else:
            signal["pnl_percent"] = round(((entry - last_close) / entry) * 100, 2)

        signal["current_price"] = last_close
        print(
            f"  STILL ACTIVE: Current ${last_close:,.2f}, PnL {signal['pnl_percent']:+.2f}%"
        )
        return signal


def check_all_signals():
    tracker = HistoricalSignalTracker()

    print("=" * 80)
    print("HISTORICAL SIGNAL TRACKING")
    print("=" * 80)

    for signal in tracker.signals:
        if signal["status"] == "active":
            updated = tracker.check_signal_against_history(signal)
            signal.update(updated)

    tracker.save_signals()

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    for signal in tracker.signals:
        status_icon = (
            "✅"
            if signal["status"] == "target_hit"
            else "❌"
            if signal["status"] == "stopped"
            else "🔄"
        )
        print(
            f"\n{status_icon} Signal #{signal['signal_id']}: {signal['timeframe']} {signal['direction']}"
        )
        print(f"  Status: {signal['status'].upper()}")
        print(f"  PnL: {signal.get('pnl_percent', 0):+.2f}%")
        if signal.get("exit_time"):
            print(f"  Exit Time: {signal['exit_time']}")


if __name__ == "__main__":
    check_all_signals()
