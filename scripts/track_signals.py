"""
Signal Tracking System - Track BTC trading signal performance
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


class SignalTracker:
    """Track trading signal performance"""

    def __init__(self):
        self.tracking_file = ROOT / "data" / "signal_tracking.json"
        self.tracking_file.parent.mkdir(exist_ok=True)
        self.signals = self.load_signals()

    def load_signals(self):
        if self.tracking_file.exists():
            with open(self.tracking_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_signals(self):
        with open(self.tracking_file, "w", encoding="utf-8") as f:
            json.dump(self.signals, f, indent=2, ensure_ascii=False)

    def add_signal(self, signal_data):
        signal_data["signal_id"] = len(self.signals) + 1
        signal_data["created_at"] = datetime.now().isoformat()
        signal_data["status"] = "active"
        signal_data["pnl_percent"] = 0.0
        self.signals.append(signal_data)
        self.save_signals()
        return signal_data["signal_id"]

    def get_current_price(self, symbol="BTC_USDT"):
        try:
            url = f"https://api.gateio.ws/api/v4/spot/tickers?currency_pair={symbol}"
            response = requests.get(url, timeout=10)
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]["last"])
        except Exception as e:
            print(f"[ERROR] Failed to get price: {e}")
        return None

    def update_signal_status(self, signal_id, current_price):
        for signal in self.signals:
            if signal["signal_id"] == signal_id and signal["status"] == "active":
                entry = signal["entry_price"]
                stop = signal["stop_loss"]
                target = signal["target_price"]
                direction = signal["direction"]

                # Calculate PnL
                if direction == "LONG":
                    pnl_percent = ((current_price - entry) / entry) * 100
                else:
                    pnl_percent = ((entry - current_price) / entry) * 100

                signal["current_price"] = current_price
                signal["pnl_percent"] = round(pnl_percent, 2)
                signal["updated_at"] = datetime.now().isoformat()

                # Check stop/target
                if direction == "LONG":
                    if current_price <= stop:
                        signal["status"] = "stopped"
                        signal["exit_price"] = stop
                    elif current_price >= target:
                        signal["status"] = "target_hit"
                        signal["exit_price"] = target
                else:
                    if current_price >= stop:
                        signal["status"] = "stopped"
                        signal["exit_price"] = stop
                    elif current_price <= target:
                        signal["status"] = "target_hit"
                        signal["exit_price"] = target

                self.save_signals()
                return signal
        return None


def add_btc_signals():
    tracker = SignalTracker()

    signals = [
        {
            "symbol": "BTC_USDT",
            "timeframe": "5m",
            "direction": "LONG",
            "entry_price": 83917.40,
            "stop_loss": 83575.51,
            "target_price": 84601.19,
            "risk_reward": 2.00,
            "win_probability": 0.70,
            "pattern_similarity": 60.1,
            "notes": "Counter-trend bounce",
        },
        {
            "symbol": "BTC_USDT",
            "timeframe": "15m",
            "direction": "SHORT",
            "entry_price": 83917.40,
            "stop_loss": 84669.03,
            "target_price": 82488.67,
            "risk_reward": 1.90,
            "win_probability": 0.66,
            "pattern_similarity": 60.4,
            "notes": "Early bearish signs",
        },
        {
            "symbol": "BTC_USDT",
            "timeframe": "1h",
            "direction": "SHORT",
            "entry_price": 83917.30,
            "stop_loss": 85068.24,
            "target_price": 81615.42,
            "risk_reward": 2.00,
            "win_probability": 0.70,
            "pattern_similarity": 84.1,
            "notes": "PRIMARY - Excellent pattern match",
        },
    ]

    for sig in signals:
        tracker.add_signal(sig)

    print(f"Added 3 BTC signals to tracking")
    print(f"File: {tracker.tracking_file}")


def check_signals():
    tracker = SignalTracker()
    price = tracker.get_current_price()

    if not price:
        print("[ERROR] Could not fetch price")
        return

    print("=" * 80)
    print(f"SIGNAL TRACKING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"BTC Price: ${price:,.2f}")
    print("=" * 80)

    for signal in tracker.signals:
        if signal["status"] == "active":
            updated = tracker.update_signal_status(signal["signal_id"], price)
            if updated:
                print(
                    f"\n#{updated['signal_id']}: {updated['timeframe']} {updated['direction']}"
                )
                print(f"  Entry: ${updated['entry_price']:,.2f}")
                print(f"  Current: ${price:,.2f}")
                print(f"  Stop: ${updated['stop_loss']:,.2f}")
                print(f"  Target: ${updated['target_price']:,.2f}")
                print(f"  PnL: {updated['pnl_percent']:+.2f}%")
                print(f"  Status: {updated['status'].upper()}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "add":
        add_btc_signals()
    else:
        check_signals()
