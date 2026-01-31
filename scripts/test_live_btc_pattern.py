#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live BTC Pattern Matching Test"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import requests

from abu.unified_vectorizer import UnifiedVectorizer
from abu.vector_pattern_matcher import VectorPatternMatcher
from db_manager_trader import TraderDBManager

print("=" * 60)
print("LIVE BTC 15M PATTERN MATCHING TEST")
print("=" * 60)

# Fetch live BTC data
print("\n[1/4] Fetching live BTC 15m data...")
url = "https://api.gateio.ws/api/v4/spot/candlesticks"
params = {"currency_pair": "BTC_USDT", "interval": "15m", "limit": 100}
response = requests.get(url, params=params, timeout=10)
klines = response.json()
print(f"✓ Fetched {len(klines)} candles")

# Extract features
print("\n[2/4] Extracting features...")
recent = klines[-20:]
closes = [float(k[2]) for k in recent]
ema = closes[0]
for c in closes[1:]:
    ema = ema * 0.9 + c * 0.1
price_vs_ema = (closes[-1] - ema) / ema
direction = (
    "bullish"
    if price_vs_ema > 0.01
    else "bearish"
    if price_vs_ema < -0.01
    else "neutral"
)
print(f"✓ Direction: {direction}")
print(f"✓ Price vs EMA: {price_vs_ema:.2%}")
print(f"✓ Current price: ${closes[-1]:.2f}")

# Initialize vector matcher
print("\n[3/4] Loading vector matcher...")
db = TraderDBManager("abu")
index_path = ROOT / "data" / "vectors" / "brooks_patterns_32d.ann"
id_map_path = ROOT / "data" / "vectors" / "brooks_patterns_id_map.json"
matcher = VectorPatternMatcher(str(index_path), str(id_map_path), db)
vectorizer = UnifiedVectorizer()
print("✓ Vector matcher loaded")

# Vectorize and search
print("\n[4/4] Finding similar patterns...")
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

print(f"✓ Found {len(patterns)} similar patterns")
print(f"\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"Win Probability: {outcomes['win_probability']:.1%}")
print(f"Typical RR: {outcomes['typical_rr']:.2f}")
print(f"Confidence: {outcomes['confidence']:.1%}")
print(f"Consensus Direction: {outcomes['consensus_direction']}")
print(f"\nTop 5 Similar Patterns:")
for i, (pattern, dist) in enumerate(zip(patterns, distances), 1):
    pf = pattern["pattern_features"]
    meta = pattern["metadata"]
    mc = pattern["market_context"]
    pattern_id = pattern["id"]
    similarity = (1 - dist / 2) * 100
    print(
        f"  {i}. [ID:{pattern_id}] {pf.get('primary', 'unknown')}/{pf.get('direction', 'unknown')} "
        f"cycle:{mc.get('cycle', 'unknown')} "
        f"(similarity: {similarity:.1f}%, win_prob: {meta.get('win_probability', 0):.1%})"
    )
