"""Data collector for ML backtest - fetches historical klines from Bitget/Bybit."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import duckdb
import requests

from .config import DATA_DIR, DB_PATH, TIME_PERIODS

# Stablecoins to exclude
STABLECOINS = {
    "USDT",
    "USDC",
    "DAI",
    "BUSD",
    "TUSD",
    "USDP",
    "GUSD",
    "FRAX",
    "LUSD",
    "USDD",
}

# Top 10 coins (fixed list for iteration 1)
TOP_10_COINS = ["BTC", "ETH", "XRP", "BNB", "SOL", "DOGE", "ADA", "TRX", "AVAX", "LINK"]


def get_top_coins(limit: int = 10) -> List[str]:
    """Get top coins by market cap from CoinGecko."""
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": limit + 10,
        "page": 1,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            symbols = []
            for coin in data:
                sym = coin.get("symbol", "").upper()
                if sym and sym not in STABLECOINS:
                    symbols.append(sym)
                if len(symbols) >= limit:
                    break
            return symbols
    except Exception as e:
        print(f"CoinGecko error: {e}, using fallback list")
    return TOP_10_COINS[:limit]


def fetch_klines_bitget(
    symbol: str, timeframe: str, start_ms: int, end_ms: int
) -> List[Dict]:
    """Fetch klines from Bitget API (fast, no auth needed)."""
    tf_map = {"15m": "15min", "1h": "1h", "4h": "4h"}
    interval = tf_map.get(timeframe, "15min")
    pair = f"{symbol}USDT"

    url = "https://api.bitget.com/api/v2/spot/market/candles"
    all_klines = []
    seen_timestamps = set()

    # Bitget returns newest first, paginate backwards using endTime
    current_end = end_ms
    max_iterations = 10

    for iteration in range(max_iterations):
        params = {
            "symbol": pair,
            "granularity": interval,
            "endTime": str(current_end),
            "limit": "1000",
        }

        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                break
            data = resp.json()
            if data.get("code") != "00000" or not data.get("data"):
                break

            candles = data["data"]
            if not candles:
                break

            # Bitget returns newest first, oldest is at index -1
            oldest_ts = int(candles[-1][0])

            new_count = 0
            for c in candles:
                ts = int(c[0])

                # Skip duplicates
                if ts in seen_timestamps:
                    continue
                seen_timestamps.add(ts)

                # Only keep klines in target range
                if ts < start_ms or ts > end_ms:
                    continue

                all_klines.append(
                    {
                        "timestamp": ts // 1000,
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5]),
                        "source": "bitget",
                    }
                )
                new_count += 1

            # Stop if reached start time
            if oldest_ts <= start_ms:
                break

            # Stop if no new data
            if new_count == 0:
                break

            # Move back to fetch older data
            current_end = oldest_ts
            time.sleep(0.1)

        except Exception as e:
            print(f"Bitget error {symbol}: {e}")
            break

    all_klines.sort(key=lambda x: x["timestamp"])
    return all_klines


def collect_iteration1(timeframe: str = "15m"):
    """Collect data for Iteration 1: Top 10 coins, recent 3 months."""
    init_db()

    coins = TOP_10_COINS  # Use fixed list instead of CoinGecko
    period = TIME_PERIODS[0]  # recent period

    start_ts = date_to_ts(period["start"])
    end_ts = date_to_ts(period["end"])

    print(f"Iteration 1: {len(coins)} coins, {period['name']}")
    print(f"Period: {period['start']} to {period['end']}")
    print(f"Timeframe: {timeframe}")
    print(f"Coins: {coins}")

    total_klines = 0
    for i, coin in enumerate(coins, 1):
        print(f"\n[{i}/{len(coins)}] Fetching {coin}...")
        klines = fetch_klines(coin, timeframe, start_ts, end_ts)
        if klines:
            save_klines(coin, timeframe, klines)
            total_klines += len(klines)
            print(f"  Saved {len(klines)} klines")
        else:
            print(f"  No data")

    print(f"\nTotal: {total_klines} klines saved to {DB_PATH}")
    return total_klines


def date_to_ts(date_str: str) -> int:
    """Convert date string to timestamp."""
    return int(datetime.strptime(date_str, "%Y-%m-%d").timestamp())


def init_db():
    """Initialize DuckDB with tables."""
    conn = duckdb.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ml_backtest_klines (
            symbol TEXT, timeframe TEXT, timestamp INTEGER,
            open REAL, high REAL, low REAL, close REAL,
            volume REAL, source TEXT,
            PRIMARY KEY (symbol, timeframe, timestamp)
        )
    """)
    conn.close()


def save_klines(symbol: str, timeframe: str, klines: List[Dict]):
    """Save klines to DuckDB."""
    if not klines:
        return
    conn = duckdb.connect(str(DB_PATH))
    for k in klines:
        conn.execute(
            """
            INSERT OR REPLACE INTO ml_backtest_klines
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            [
                symbol,
                timeframe,
                k["timestamp"],
                k["open"],
                k["high"],
                k["low"],
                k["close"],
                k.get("volume", 0),
                k.get("source", "unknown"),
            ],
        )
    conn.close()


def fetch_klines(symbol: str, timeframe: str, start_ts: int, end_ts: int) -> List[Dict]:
    """Fetch klines with Bitget primary, Bybit fallback."""
    start_ms = start_ts * 1000
    end_ms = end_ts * 1000

    klines = fetch_klines_bitget(symbol, timeframe, start_ms, end_ms)
    if not klines:
        print(f"  Bitget failed for {symbol}, trying Bybit...")
        klines = fetch_klines_bybit(symbol, timeframe, start_ms, end_ms)

    return klines


def fetch_klines_bybit(
    symbol: str, timeframe: str, start_ms: int, end_ms: int
) -> List[Dict]:
    """Fetch klines from Bybit API (fallback)."""
    tf_map = {"15m": "15", "1h": "60", "4h": "240"}
    interval = tf_map.get(timeframe, "15")
    pair = f"{symbol}USDT"

    url = "https://api.bybit.com/v5/market/kline"
    all_klines = []
    current_start = start_ms

    while current_start < end_ms:
        params = {
            "category": "spot",
            "symbol": pair,
            "interval": interval,
            "start": str(current_start),
            "end": str(end_ms),
            "limit": "1000",
        }
        try:
            resp = requests.get(url, params=params, timeout=20)
            if resp.status_code != 200:
                break
            data = resp.json()
            if data.get("retCode") != 0 or not data.get("result", {}).get("list"):
                break

            candles = data["result"]["list"]
            for c in candles:
                ts = int(c[0])
                if ts > end_ms:
                    continue
                all_klines.append(
                    {
                        "timestamp": ts // 1000,
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume": float(c[5]),
                        "source": "bybit",
                    }
                )

            if len(candles) < 1000:
                break
            current_start = int(candles[0][0]) + 1
            time.sleep(0.1)
        except Exception as e:
            print(f"Bybit error {symbol}: {e}")
            break

    all_klines.sort(key=lambda x: x["timestamp"])
    return all_klines
