#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate Latest BTC Signals for 5m, 15m, 1h"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import requests

from abu.unified_vectorizer import UnifiedVectorizer
from abu.vector_pattern_matcher import VectorPatternMatcher
from db_manager_trader import TraderDBManager


def generate_signal(interval):
    print(f"\n{'=' * 80}")
    print(f"BTC {interval.upper()} SIGNAL")
    print(f"{'=' * 80}")

    # Fetch data
    print(f"\nFetching {interval} data...")
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {"currency_pair": "BTC_USDT", "interval": interval, "limit": 100}
    response = requests.get(url, params=params, timeout=10)
    klines = response.json()

    # Extract features
    recent = klines[-20:]
    closes = [float(k[2]) for k in recent]
    highs = [float(k[3]) for k in recent]
    lows = [float(k[4]) for k in recent]

    ema = closes[0]
    for c in closes[1:]:
        ema = ema * 0.9 + c * 0.1

    price = closes[-1]
    price_vs_ema = (price - ema) / ema
    direction = (
        "bullish"
        if price_vs_ema > 0.01
        else "bearish"
        if price_vs_ema < -0.01
        else "neutral"
    )

    # Calculate ATR
    tr = []
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr.append(max(hl, hc, lc))
    atr = sum(tr[-14:]) / 14 if len(tr) >= 14 else sum(tr) / len(tr)

    print(f"Price: ${price:,.2f}")
    print(f"EMA-20: ${ema:,.2f}")
    print(f"Price vs EMA: {price_vs_ema:+.2%}")
    print(f"Direction: {direction.upper()}")
    print(f"ATR: ${atr:,.2f}")

    # Load vector matcher
    print(f"\nLoading vector matcher...")
    db = TraderDBManager()
    index_path = ROOT / "data" / "vectors" / "brooks_patterns_32d.ann"
    id_map_path = ROOT / "data" / "vector_index" / "pattern_mapping.json"
    vectorizer = UnifiedVectorizer()
    matcher = VectorPatternMatcher(str(index_path), str(id_map_path), db)

    # Vectorize
    print(f"Finding similar patterns...")
    query_vec = vectorizer.vectorize_live_kline(
        trend_features={"direction": direction, "strength": abs(price_vs_ema)},
        ema_features={
            "relation": "above" if price_vs_ema > 0 else "below",
            "slope": price_vs_ema,
        },
        pattern_features={"engulfing": False, "hammer": False},
    )
