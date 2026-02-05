"""Simple test of Bitget API fetching."""

import time
from datetime import datetime

import requests


def date_to_ts(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())


def fetch_bitget_simple(symbol: str, timeframe: str, start_ms: int, end_ms: int):
    """Simplified Bitget fetch with debugging."""
    url = "https://api.bitget.com/api/v2/spot/market/candles"
    pair = f"{symbol}USDT"

    all_klines = []
    seen_timestamps = set()
    current_end = None

    print(f"Fetching {symbol} {timeframe}...")
    print(f"  Start: {start_ms} ({datetime.fromtimestamp(start_ms / 1000)})")
    print(f"  End: {end_ms} ({datetime.fromtimestamp(end_ms / 1000)})")

    for iteration in range(10):  # Max 10 iterations
        params = {
            "symbol": pair,
            "granularity": timeframe,
            "limit": "1000",
        }
        if current_end:
            params["endTime"] = str(current_end)

        print(
            f"  Iteration {iteration + 1}: endTime={current_end or 'None'}",
            end=" ",
            flush=True,
        )

        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                print(f"Bad status: {resp.status_code}")
                break

            data = resp.json()
            if data.get("code") != "00000":
                print(f"Bad code: {data.get('code')}")
                break

            candles = data.get("data", [])
            if not candles:
                print("No candles")
                break

            oldest_ts = int(candles[-1][0])
            newest_ts = int(candles[0][0])

            new_count = 0
            for c in candles:
                ts = int(c[0])
                if ts in seen_timestamps:
                    continue
                seen_timestamps.add(ts)

                if start_ms <= ts <= end_ms:
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
                    new_count += 1

            print(f"-> {len(candles)} candles, {new_count} new in range")

            if oldest_ts <= start_ms:
                print("  Reached start time")
                break

            if new_count == 0:
                print("  No new klines, stopping")
                break

            current_end = oldest_ts - 1
            time.sleep(0.2)

        except Exception as e:
            print(f"Error: {e}")
            break

    all_klines.sort(key=lambda x: x["timestamp"])
    return all_klines


# Test
start_ts = date_to_ts("2025-10-13")
end_ts = date_to_ts("2026-01-11")

print("=" * 60)
start_time = time.time()
klines = fetch_bitget_simple("BTC", "1h", start_ts * 1000, end_ts * 1000)
elapsed = time.time() - start_time

print("=" * 60)
print(f"Total: {len(klines)} klines in {elapsed:.1f}s")
if klines:
    first_dt = datetime.fromtimestamp(klines[0]["timestamp"])
    last_dt = datetime.fromtimestamp(klines[-1]["timestamp"])
    print(f"First: {first_dt}")
    print(f"Last: {last_dt}")
