"""Debug script to test kline fetching."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import time
from datetime import datetime

import requests


def date_to_ts(date_str: str) -> int:
    """Convert date string to timestamp."""
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())


def fetch_klines_bitget_debug(symbol: str, timeframe: str, start_ms: int, end_ms: int):
    """Fetch klines from Bitget with debug output."""
    tf_map = {"15m": "15min", "1h": "1h", "4h": "4h"}
    interval = tf_map.get(timeframe, "15min")
    pair = f"{symbol}USDT"

    url = "https://api.bitget.com/api/v2/spot/market/candles"
    all_klines = []

    current_end = None
    iteration = 0
    max_iterations = 10  # Safety limit

    print(f"Fetching {symbol} {timeframe} from {start_ms} to {end_ms}")

    while iteration < max_iterations:
        iteration += 1
        params = {
            "symbol": pair,
            "granularity": interval,
            "limit": "1000",
        }
        if current_end:
            params["endTime"] = str(current_end)

        print(
            f"  Iteration {iteration}: endTime={current_end or 'None'}",
            end=" ",
            flush=True,
        )

        try:
            resp = requests.get(url, params=params, timeout=10)
            print(f"-> {resp.status_code}", end=" ")

            if resp.status_code != 200:
                print("(bad status)")
                break

            data = resp.json()
            code = data.get("code")
            print(f"code={code}", end=" ")

            if code != "00000":
                print("(bad code)")
                break

            candles = data.get("data", [])
            print(f"candles={len(candles)}")

            if not candles:
                print("  No more candles, stopping")
                break

            oldest_ts = int(candles[-1][0])
            newest_ts = int(candles[0][0])

            count_in_range = 0
            for c in candles:
                ts = int(c[0])
                if start_ms <= ts <= end_ms:
                    count_in_range += 1
                    all_klines.append(
                        {
                            "timestamp": ts // 1000,
                            "open": float(c[1]),
                            "high": float(c[2]),
                            "low": float(c[3]),
                            "close": float(c[4]),
                            "volume": float(c[5]),
                        }
                    )

            print(f"    Range: {oldest_ts} to {newest_ts}, in_range={count_in_range}")

            if oldest_ts <= start_ms:
                print("  Reached start time, stopping")
                break

            current_end = oldest_ts - 1
            time.sleep(0.1)

        except Exception as e:
            print(f"ERROR: {e}")
            break

    all_klines.sort(key=lambda x: x["timestamp"])
    return all_klines


# Test
start_ts = date_to_ts("2025-10-13")
end_ts = date_to_ts("2026-01-11")

print("=" * 60)
start_time = time.time()
klines = fetch_klines_bitget_debug("BTC", "1h", start_ts * 1000, end_ts * 1000)
elapsed = time.time() - start_time

print("=" * 60)
print(f"Total: {len(klines)} klines in {elapsed:.1f}s")
if klines:
    print(f"First: {klines[0]['timestamp']}")
    print(f"Last: {klines[-1]['timestamp']}")
