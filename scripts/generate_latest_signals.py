"""
Generate latest BTC trading signals for multiple timeframes
"""

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

# Import required modules
import numpy as np
import requests

from abu.unified_vectorizer import UnifiedVectorizer
from abu.vector_pattern_matcher import VectorPatternMatcher
from db_manager_trader import TraderDBManager


def fetch_live_klines(symbol="BTC_USDT", interval="5m", limit=100):
    """Fetch live K-line data from Gate.io"""
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {"currency_pair": symbol, "interval": interval, "limit": limit}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        return data
    except Exception as e:
        print(f"[ERROR] Failed to fetch K-lines: {e}")
        return None


def calculate_ema(prices, period=20):
    """Calculate EMA"""
    prices = np.array(prices)
    ema = np.zeros_like(prices)
    multiplier = 2 / (period + 1)
    ema[0] = prices[0]

    for i in range(1, len(prices)):
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]

    return ema


def calculate_atr(highs, lows, closes, period=14):
    """Calculate ATR"""
    tr = []
    for i in range(1, len(closes)):
        high_low = highs[i] - lows[i]
        high_close = abs(highs[i] - closes[i - 1])
        low_close = abs(lows[i] - closes[i - 1])
        tr.append(max(high_low, high_close, low_close))

    return np.mean(tr[-period:]) if len(tr) >= period else np.mean(tr)


def analyze_timeframe(interval):
    """Analyze a single timeframe and generate signal"""
    print(f"\n{'=' * 80}")
    print(f"Analyzing {interval} timeframe...")
    print(f"{'=' * 80}")

    # Fetch data
    klines = fetch_live_klines(interval=interval, limit=100)
    if not klines:
        print(f"[ERROR] No data for {interval}")
        return None
