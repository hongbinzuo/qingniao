"""Feature engineering for ML backtest."""

import math
from typing import Dict, List, Optional


def calc_atr(klines: List[Dict], period: int = 14) -> float:
    """Calculate ATR."""
    if len(klines) < 2:
        return 0.0
    trs = []
    for i in range(1, len(klines)):
        h, l, pc = klines[i]["high"], klines[i]["low"], klines[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    return sum(trs[-period:]) / min(period, len(trs)) if trs else 0.0


def calc_ema(values: List[float], period: int) -> float:
    """Calculate EMA of last value."""
    if not values:
        return 0.0
    if len(values) < period:
        return sum(values) / len(values)
    mult = 2 / (period + 1)
    ema = sum(values[:period]) / period
    for v in values[period:]:
        ema = v * mult + ema * (1 - mult)
    return ema


def calc_rsi(klines: List[Dict], period: int = 14) -> float:
    """Calculate RSI."""
    if len(klines) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(1, len(klines)):
        delta = klines[i]["close"] - klines[i - 1]["close"]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_volatility(klines: List[Dict], period: int = 20) -> float:
    """Calculate price volatility (std dev of returns)."""
    if len(klines) < 2:
        return 0.0
    returns = []
    for i in range(1, len(klines)):
        if klines[i - 1]["close"] > 0:
            ret = (klines[i]["close"] - klines[i - 1]["close"]) / klines[i - 1]["close"]
            returns.append(ret)
    if len(returns) < 2:
        return 0.0
    recent = returns[-period:]
    mean = sum(recent) / len(recent)
    variance = sum((r - mean) ** 2 for r in recent) / len(recent)
    return math.sqrt(variance)


def calc_trend_strength(klines: List[Dict], period: int = 20) -> float:
    """Calculate trend strength (-1 to 1, negative=downtrend, positive=uptrend)."""
    if len(klines) < period:
        return 0.0
    closes = [k["close"] for k in klines[-period:]]
    ema_fast = calc_ema(closes, 8)
    ema_slow = calc_ema(closes, 20)
    if ema_slow == 0:
        return 0.0
    return (ema_fast - ema_slow) / ema_slow * 100


def calc_volume_ratio(klines: List[Dict], period: int = 20) -> float:
    """Calculate current volume vs average volume ratio."""
    if len(klines) < 2:
        return 1.0
    volumes = [k.get("volume", 0) for k in klines]
    avg_vol = sum(volumes[-period:-1]) / max(1, len(volumes[-period:-1]))
    if avg_vol == 0:
        return 1.0
    return volumes[-1] / avg_vol


def calc_stop_distance_pct(signal: Dict) -> float:
    """Calculate stop loss distance as percentage of entry price."""
    entry = signal.get("entry", 0)
    sl = signal.get("stop_loss", 0)
    if entry == 0:
        return 0.0
    return abs(entry - sl) / entry * 100


def calc_rr_ratio(signal: Dict) -> float:
    """Calculate risk/reward ratio (TP1 distance / SL distance)."""
    entry = signal.get("entry", 0)
    sl = signal.get("stop_loss", 0)
    tp1 = signal.get("tp1", 0)
    sl_dist = abs(entry - sl)
    tp1_dist = abs(tp1 - entry)
    if sl_dist == 0:
        return 0.0
    return tp1_dist / sl_dist


def extract_features(signal: Dict, klines: List[Dict]) -> Dict:
    """Extract all features for a signal."""
    price = signal.get("entry", klines[-1]["close"] if klines else 0)
    atr = calc_atr(klines)
    atr_pct = (atr / price * 100) if price > 0 else 0

    features = {
        # Signal properties
        "pattern": signal.get("pattern", "unknown"),
        "direction": 1 if signal.get("direction") == "long" else 0,
        "stop_distance_pct": calc_stop_distance_pct(signal),
        "rr_ratio": calc_rr_ratio(signal),
        # Market conditions
        "atr_pct": atr_pct,
        "rsi": calc_rsi(klines),
        "volatility": calc_volatility(klines),
        "trend_strength": calc_trend_strength(klines),
        "volume_ratio": calc_volume_ratio(klines),
        # Price position
        "price_vs_ema20": 0.0,
        "price_vs_ema50": 0.0,
    }

    # Calculate price vs EMAs
    if klines and price > 0:
        closes = [k["close"] for k in klines]
        ema20 = calc_ema(closes, 20)
        ema50 = calc_ema(closes, 50)
        if ema20 > 0:
            features["price_vs_ema20"] = (price - ema20) / ema20 * 100
        if ema50 > 0:
            features["price_vs_ema50"] = (price - ema50) / ema50 * 100

    return features
