#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC Trading Signal Generator - 5m and 15m"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from datetime import datetime

import requests

from abu.unified_vectorizer import UnifiedVectorizer
from abu.vector_pattern_matcher import VectorPatternMatcher
from db_manager_trader import TraderDBManager


def analyze(interval):
    # Fetch data
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {"currency_pair": "BTC_USDT", "interval": interval, "limit": 100}
    klines = requests.get(url, params=params, timeout=10).json()

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

    # Vector matching
    db = TraderDBManager("abu")
    index_path = ROOT / "data" / "vectors" / "brooks_patterns_32d.ann"
    id_map_path = ROOT / "data" / "vectors" / "brooks_patterns_id_map.json"
    matcher = VectorPatternMatcher(str(index_path), str(id_map_path), db)
    vectorizer = UnifiedVectorizer()

    query_vec = vectorizer.vectorize_live_kline(
        trend_features={
            "direction": direction,
            "strength": min(abs(price_vs_ema) * 10, 1.0),
        },
        ema_features={
            "relation": "above" if price_vs_ema > 0 else "below",
            "slope": price_vs_ema,
        },
        pattern_features={"engulfing": False, "hammer": False},
    )
    patterns, distances = matcher.find_similar_patterns(query_vec, k=5)
    outcomes = matcher.aggregate_outcomes(patterns, distances)

    # Calculate stops and targets
    atr = sum([h - l for h, l in zip(highs[-14:], lows[-14:])]) / 14

    return {
        "interval": interval,
        "price": price,
        "ema": ema,
        "price_vs_ema": price_vs_ema,
        "direction": direction,
        "atr": atr,
        "patterns": patterns,
        "distances": distances,
        "outcomes": outcomes,
    }


# Main
print("=" * 80)
print("BTC TRADING SIGNALS - 5M, 15M & 1H TIMEFRAMES")
print("=" * 80)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

for tf in ["5m", "15m", "1h"]:
    result = analyze(tf)

    print(f"\n{'=' * 80}")
    print(f"TIMEFRAME: {tf.upper()}")
    print("=" * 80)

    print(f"\n[MARKET ANALYSIS]")
    print(f"  Current Price: ${result['price']:.2f}")
    print(f"  EMA-20: ${result['ema']:.2f}")
    print(f"  Price vs EMA: {result['price_vs_ema']:.2%}")
    print(f"  Direction: {result['direction'].upper()}")
    print(f"  ATR(14): ${result['atr']:.2f}")

    print(f"\n[VECTOR PATTERN ANALYSIS]")
    print(f"  Win Probability: {result['outcomes']['win_probability']:.1%}")
    print(f"  Risk/Reward: {result['outcomes']['typical_rr']:.2f}")
    print(f"  Confidence: {result['outcomes']['confidence']:.1%}")
    print(f"  Consensus: {result['outcomes']['consensus_direction'].upper()}")

    print(f"\n[TOP 5 SIMILAR PATTERNS]")
    for i, (p, d) in enumerate(zip(result["patterns"], result["distances"]), 1):
        sim = (1 - d / 2) * 100
        print(
            f"  {i}. [ID:{p['id']}] {p['pattern_features'].get('primary')}/{p['pattern_features'].get('direction')} (sim:{sim:.1f}%)"
        )

    # Trading signal
    consensus = result["outcomes"]["consensus_direction"]
    win_prob = result["outcomes"]["win_probability"]
    rr = result["outcomes"]["typical_rr"]
    atr = result["atr"]
    price = result["price"]

    print(f"\n[TRADING SIGNAL]")
    if win_prob >= 0.6 and result["outcomes"]["confidence"] > 0.15:
        signal = (
            "LONG"
            if consensus == "bullish"
            else "SHORT"
            if consensus == "bearish"
            else "NO SIGNAL"
        )
        stop = (
            price - (atr * 1.5)
            if signal == "LONG"
            else price + (atr * 1.5)
            if signal == "SHORT"
            else 0
        )
        target = (
            price + (atr * rr * 1.5)
            if signal == "LONG"
            else price - (atr * rr * 1.5)
            if signal == "SHORT"
            else 0
        )
        print(f"  Signal: {signal}")
        print(f"  Entry: ${price:.2f}")
        print(f"  Stop Loss: ${stop:.2f} ({abs(stop - price) / price:.2%})")
        print(f"  Target: ${target:.2f} ({abs(target - price) / price:.2%})")
        print(f"  Risk/Reward: 1:{rr:.2f}")
    else:
        print(f"  Signal: NO SIGNAL (Low confidence or win probability)")
