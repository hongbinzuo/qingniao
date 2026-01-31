#!/usr/bin/env python3
"""Analyze better entry for 1H BTC SHORT signal"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import requests

# Fetch 1H data
url = "https://api.gateio.ws/api/v4/spot/candlesticks"
params = {"currency_pair": "BTC_USDT", "interval": "1h", "limit": 100}
r = requests.get(url, params=params, timeout=10)
klines = r.json()

# Extract data
closes = [float(k[2]) for k in klines]
highs = [float(k[3]) for k in klines]
lows = [float(k[4]) for k in klines]
volumes = [float(k[6]) for k in klines]

current_price = closes[-1]

print("=" * 60)
print("1H BTC SHORT - ENTRY ANALYSIS")
print("=" * 60)
print(f"\nCurrent Price: ${current_price:,.2f}")

# Calculate EMA-20
ema20 = closes[0]
for c in closes[1:]:
    ema20 = ema20 * 0.9 + c * 0.1

print(f"EMA-20: ${ema20:,.2f}")
print(f"Distance from EMA: {((current_price - ema20) / ema20) * 100:+.2f}%")

# Find recent swing highs (resistance levels)
print("\n--- RESISTANCE LEVELS (Potential Pullback Entries) ---")
recent_highs = highs[-20:]
resistance_levels = []
for i in range(1, len(recent_highs) - 1):
    if recent_highs[i] > recent_highs[i - 1] and recent_highs[i] > recent_highs[i + 1]:
        resistance_levels.append(recent_highs[i])

# Filter resistance above current price
resistance_above = [r for r in resistance_levels if r > current_price]
resistance_above.sort()

if resistance_above:
    for i, level in enumerate(resistance_above[:3], 1):
        pct = ((level - current_price) / current_price) * 100
        print(f"{i}. ${level:,.2f} (+{pct:.2f}%)")
else:
    print("No clear resistance found above current price")

# ATR for stop placement
tr = []
for i in range(1, len(closes)):
    tr.append(
        max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    )
atr = sum(tr[-14:]) / 14

print(f"\n--- ENTRY RECOMMENDATIONS ---")
print(f"\n1. IMMEDIATE (Aggressive): ${current_price:,.2f}")
print(f"   Stop: ${current_price + atr * 1.5:,.2f}")
print(f"   Target: ${current_price - atr * 2.5:,.2f}")

if resistance_above:
    best_entry = resistance_above[0]
    print(f"\n2. PULLBACK (Better): ${best_entry:,.2f}")
    print(f"   Stop: ${best_entry + atr * 1.5:,.2f}")
    print(f"   Target: ${best_entry - atr * 2.5:,.2f}")
    print(
        f"   Wait for: +{((best_entry - current_price) / current_price) * 100:.2f}% pullback"
    )
atr = sum(tr[-14:]) / 14
