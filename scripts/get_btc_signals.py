#!/usr/bin/env python3
"""Generate Latest BTC Signals - Simple Version"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests


def get_signal(interval):
    print(f"\n{'=' * 60}")
    print(f"BTC {interval.upper()} SIGNAL")
    print(f"{'=' * 60}")

    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params = {"currency_pair": "BTC_USDT", "interval": interval, "limit": 100}
    r = requests.get(url, params=params, timeout=10)
    klines = r.json()

    recent = klines[-20:]
    closes = [float(k[2]) for k in recent]
    highs = [float(k[3]) for k in recent]
    lows = [float(k[4]) for k in recent]

    price = closes[-1]
    ema = closes[0]
    for c in closes[1:]:
        ema = ema * 0.9 + c * 0.1

    pct = (price - ema) / ema
    direction = "BEARISH" if pct < -0.01 else "BULLISH" if pct > 0.01 else "NEUTRAL"

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
    atr = sum(tr[-14:]) / 14

    print(f"\nPrice: ${price:,.2f}")
    print(f"EMA-20: ${ema:,.2f}")
    print(f"Price vs EMA: {pct:+.2%}")
    print(f"Direction: {direction}")
    print(f"ATR: ${atr:,.2f}")

    # Generate signal
    if direction == "BEARISH":
        signal = "SHORT"
        stop = price + (atr * 1.5)
        target = price - (atr * 2.5)
    elif direction == "BULLISH":
        signal = "LONG"
        stop = price - (atr * 1.5)
        target = price + (atr * 2.5)
    else:
        signal = "NO SIGNAL"
        stop = target = 0

    if signal != "NO SIGNAL":
        print(f"\nSIGNAL: {signal}")
        print(f"  Entry: ${price:,.2f}")
        print(f"  Stop: ${stop:,.2f}")
        print(f"  Target: ${target:,.2f}")
        risk = abs((stop - price) / price) * 100
        reward = abs((target - price) / price) * 100
        print(f"  Risk: {risk:.2f}%")
        print(f"  Reward: {reward:.2f}%")
        print(f"  R/R: 1:{reward / risk:.2f}")
    else:
        print(f"\n{signal}")


if __name__ == "__main__":
    for interval in ["5m", "15m", "1h"]:
        get_signal(interval)
