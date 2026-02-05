#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate BTC signals for 5m, 15m, 1h"""

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
    print(f"{'=' * 80}\n")

    # Fetch data
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

    # ATR
    tr = []
    for i in range(1, len(closes)):
        tr.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )
    atr = sum(tr[-14:]) / 14 if len(tr) >= 14 else sum(tr) / len(tr)

    print(f"Price: ${price:,.2f}")
    print(f"EMA-20: ${ema:,.2f}")
    print(f"Price vs EMA: {price_vs_ema:+.2%}")
    print(f"Direction: {direction.upper()}")
    print(f"ATR: ${atr:,.2f}\n")

    # Vector matching
    db = TraderDBManager()
    index_path = ROOT / "data" / "vectors" / "brooks_patterns_32d.ann"
    id_map_path = ROOT / "data" / "vector_index" / "pattern_mapping.json"
    vectorizer = UnifiedVectorizer()
    matcher = VectorPatternMatcher(str(index_path), str(id_map_path), db)

    query_vec = vectorizer.vectorize_live_kline(
        trend_features={"direction": direction, "strength": abs(price_vs_ema)},
        ema_features={
            "relation": "above" if price_vs_ema > 0 else "below",
            "slope": price_vs_ema,
        },
        pattern_features={"engulfing": False, "hammer": False},
    )

    patterns, distances = matcher.find_similar_patterns(query_vec, k=5)
    result = matcher.aggregate_outcomes(patterns, distances)

    print(f"Pattern Similarity: {result['avg_similarity'] * 100:.1f}%")
    print(f"Win Probability: {result['outcomes']['win_prob'] * 100:.0f}%")
    print(f"Risk/Reward: {result['outcomes']['avg_rr']:.2f}")
    print(f"Consensus: {result['outcomes']['consensus'].upper()}\n")

    # Generate trading signal
    consensus = result["outcomes"]["consensus"]
    win_prob = result["outcomes"]["win_prob"]
    rr = result["outcomes"]["avg_rr"]

    if win_prob >= 0.6 and result["outcomes"]["confidence"] > 0.15:
        signal = "LONG" if consensus == "bullish" else "SHORT"
        stop = price - (atr * 1.5) if signal == "LONG" else price + (atr * 1.5)
        target = (
            price + (atr * rr * 1.5) if signal == "LONG" else price - (atr * rr * 1.5)
        )

        print(f"SIGNAL: {signal}")
        print(f"  Entry: ${price:,.2f}")
        print(f"  Stop: ${stop:,.2f}")
        print(f"  Target: ${target:,.2f}")
        print(f"  Risk: {abs((stop - price) / price) * 100:.2f}%")
        print(f"  Reward: {abs((target - price) / price) * 100:.2f}%")
    else:
        print(f"NO SIGNAL (Low confidence)")


if __name__ == "__main__":
    for interval in ["5m", "15m", "1h"]:
        generate_signal(interval)
