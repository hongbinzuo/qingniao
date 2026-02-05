#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qingniao-Abu Detectors (15m/1h)

Lightweight price-action detectors designed for 15m scan:
- inside_bar: last candle's range inside previous candle.
- engulfing: bullish/bearish body engulf.
- pin_bar: long wick vs body and total range.
- key_levels: proximity to round/structural levels (recent HH/LL and round steps).

All detectors return a list[dict] of candidate entries with:
  {
    'pattern': 'InsideBar'|'Engulfing'|'PinBar'|'KeyLevel',
    'type': 'long'|'short',
    'entry': float,
    'stop_loss': float,
    'take_profit_1': float,
    'take_profit_2': float,
    'reason': str,
    'score_hint': float
  }
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple


def _calc_atr(kl: List[Dict], period: int = 14) -> float:
    """Calculate Average True Range."""
    if len(kl) < 2:
        return 0.0
    trs = []
    for i in range(1, len(kl)):
        h, l, pc = kl[i]["high"], kl[i]["low"], kl[i - 1]["close"]
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if not trs:
        return 0.0
    return sum(trs[-period:]) / min(period, len(trs))


def _rr_pack(
    entry: float, sl: float, typ: str, r_mult1: float = 1.0, r_mult2: float = 2.0
) -> Tuple[float, float]:
    risk = abs(entry - sl)
    if risk <= 0:
        return entry, entry
    if typ == "long":
        return entry + r_mult1 * risk, entry + r_mult2 * risk
    else:
        return entry - r_mult1 * risk, entry - r_mult2 * risk


def _calc_ema(values: List[float], period: int) -> float:
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


def _get_trend(kl: List[Dict], fast: int = 8, slow: int = 21) -> str:
    """Get trend direction: 'up', 'down', or 'neutral'."""
    if len(kl) < slow:
        return "neutral"
    closes = [k["close"] for k in kl]
    ema_fast = _calc_ema(closes, fast)
    ema_slow = _calc_ema(closes, slow)
    if ema_fast > ema_slow * 1.001:
        return "up"
    elif ema_fast < ema_slow * 0.999:
        return "down"
    return "neutral"


def _round_step(price: float) -> float:
    if price <= 0:
        return 0.01
    import math

    p = abs(price)
    if p >= 10000:
        return 100.0
    if p >= 1000:
        return 50.0
    if p >= 100:
        return 10.0
    if p >= 10:
        return 1.0
    if p >= 1:
        return 0.1
    return 0.01


def _nearest_round(price: float) -> float:
    step = _round_step(price)
    if step <= 0:
        return price
    return round(price / step) * step


def _recent_hh_ll(
    kl: List[Dict], lookback: int = 20
) -> Tuple[Optional[float], Optional[float]]:
    if not kl:
        return None, None
    seg = kl[-lookback:]
    hh = max(x["high"] for x in seg) if seg else None
    ll = min(x["low"] for x in seg) if seg else None
    return hh, ll


def detect_inside_bar(kl: List[Dict]) -> List[Dict]:
    if len(kl) < 2:
        return []
    a = kl[-2]
    b = kl[-1]
    out: List[Dict] = []
    if b["high"] <= a["high"] and b["low"] >= a["low"]:
        # Calculate ATR for alternative stop loss
        atr = _calc_atr(kl)
        atr_mult = 1.5

        # Long signal
        entry_long = b["close"]
        sl_brooks = a["low"]  # Brooks: mother bar low
        sl_atr = entry_long - atr * atr_mult
        tp1, tp2 = _rr_pack(entry_long, sl_brooks, "long")
        tp1_atr, tp2_atr = _rr_pack(entry_long, sl_atr, "long")
        out.append(
            {
                "pattern": "InsideBar",
                "type": "long",
                "entry": float(entry_long),
                "stop_loss": float(sl_brooks),
                "stop_loss_atr": float(sl_atr),
                "take_profit_1": float(tp1),
                "take_profit_2": float(tp2),
                "take_profit_1_atr": float(tp1_atr),
                "take_profit_2_atr": float(tp2_atr),
                "reason": "Inside bar (break-up)",
                "score_hint": 0.6,
            }
        )

        # Short signal
        entry_short = b["close"]
        sl_brooks_short = a["high"]  # Brooks: mother bar high
        sl_atr_short = entry_short + atr * atr_mult
        tp1s, tp2s = _rr_pack(entry_short, sl_brooks_short, "short")
        tp1s_atr, tp2s_atr = _rr_pack(entry_short, sl_atr_short, "short")
        out.append(
            {
                "pattern": "InsideBar",
                "type": "short",
                "entry": float(entry_short),
                "stop_loss": float(sl_brooks_short),
                "stop_loss_atr": float(sl_atr_short),
                "take_profit_1": float(tp1s),
                "take_profit_2": float(tp2s),
                "take_profit_1_atr": float(tp1s_atr),
                "take_profit_2_atr": float(tp2s_atr),
                "reason": "Inside bar (break-down)",
                "score_hint": 0.6,
            }
        )
    return out


def detect_engulfing(kl: List[Dict]) -> List[Dict]:
    if len(kl) < 2:
        return []
    p = kl[-2]
    c = kl[-1]
    out: List[Dict] = []

    # Calculate ATR for wider stops
    atr = _calc_atr(kl)
    atr_mult = 1.5

    if c["close"] > c["open"] and p["close"] < p["open"]:
        if (c["close"] >= p["open"]) and (c["open"] <= p["close"]):
            entry = c["close"]
            sl_pattern = min(c["low"], p["low"])
            sl_atr = entry - atr * atr_mult
            # Use wider of pattern SL or ATR SL
            sl = min(sl_pattern, sl_atr)
            tp1, tp2 = _rr_pack(entry, sl, "long")
            out.append(
                {
                    "pattern": "Engulfing",
                    "type": "long",
                    "entry": float(entry),
                    "stop_loss": float(sl),
                    "take_profit_1": float(tp1),
                    "take_profit_2": float(tp2),
                    "reason": "Bullish engulfing",
                    "score_hint": 0.8,
                }
            )
    if c["close"] < c["open"] and p["close"] > p["open"]:
        if (c["close"] <= p["open"]) and (c["open"] >= p["close"]):
            entry = c["close"]
            sl_pattern = max(c["high"], p["high"])
            sl_atr = entry + atr * atr_mult
            # Use wider of pattern SL or ATR SL
            sl = max(sl_pattern, sl_atr)
            tp1, tp2 = _rr_pack(entry, sl, "short")
            out.append(
                {
                    "pattern": "Engulfing",
                    "type": "short",
                    "entry": float(entry),
                    "stop_loss": float(sl),
                    "take_profit_1": float(tp1),
                    "take_profit_2": float(tp2),
                    "reason": "Bearish engulfing",
                    "score_hint": 0.8,
                }
            )
    return out


def detect_pin_bar(
    kl: List[Dict], wick_ratio: float = 1.5, body_max_frac: float = 0.4
) -> List[Dict]:
    if not kl:
        return []
    c = kl[-1]
    o, h, l, cl = c["open"], c["high"], c["low"], c["close"]
    body = abs(cl - o)
    rng = max(h - l, 1e-9)
    upper = h - max(o, cl)
    lower = min(o, cl) - l
    out: List[Dict] = []

    # Calculate ATR for wider stops
    atr = _calc_atr(kl)
    atr_mult = 1.5

    if lower > wick_ratio * body and (body / rng) <= body_max_frac:
        entry = cl
        sl_pattern = l
        sl_atr = entry - atr * atr_mult
        # Use wider of pattern SL or ATR SL
        sl = min(sl_pattern, sl_atr)
        tp1, tp2 = _rr_pack(entry, sl, "long")
        out.append(
            {
                "pattern": "PinBar",
                "type": "long",
                "entry": float(entry),
                "stop_loss": float(sl),
                "take_profit_1": float(tp1),
                "take_profit_2": float(tp2),
                "reason": "Bullish pin-bar",
                "score_hint": 0.5,
            }
        )
    if upper > wick_ratio * body and (body / rng) <= body_max_frac:
        entry = cl
        sl_pattern = h
        sl_atr = entry + atr * atr_mult
        # Use wider of pattern SL or ATR SL
        sl = max(sl_pattern, sl_atr)
        tp1, tp2 = _rr_pack(entry, sl, "short")
        out.append(
            {
                "pattern": "PinBar",
                "type": "short",
                "entry": float(entry),
                "stop_loss": float(sl),
                "take_profit_1": float(tp1),
                "take_profit_2": float(tp2),
                "reason": "Bearish pin-bar",
                "score_hint": 0.5,
            }
        )
    return out


def detect_key_levels(
    kl: List[Dict], tol_pct: float = 0.003, lookback: int = 20
) -> List[Dict]:
    if not kl:
        return []
    c = kl[-1]
    price = c["close"]
    hh, ll = _recent_hh_ll(kl, lookback)
    round_lv = _nearest_round(price)
    out: List[Dict] = []

    def _near(a: float, b: float) -> bool:
        if a is None or b is None or a <= 0:
            return False
        return abs(b - a) / a <= tol_pct

    notes = []
    if hh and _near(hh, price):
        notes.append("near_HH")
    if ll and _near(ll, price):
        notes.append("near_LL")
    if round_lv and _near(round_lv, price):
        notes.append("near_round")
    if not notes:
        return []
    sl_long = min([x["low"] for x in kl[-3:]])
    tp1, tp2 = _rr_pack(price, sl_long, "long")
    out.append(
        {
            "pattern": "KeyLevel",
            "type": "long",
            "entry": float(price),
            "stop_loss": float(sl_long),
            "take_profit_1": float(tp1),
            "take_profit_2": float(tp2),
            "reason": " / ".join(notes) + " (long)",
            "score_hint": 0.3,
        }
    )
    sl_short = max([x["high"] for x in kl[-3:]])
    tp1s, tp2s = _rr_pack(price, sl_short, "short")
    out.append(
        {
            "pattern": "KeyLevel",
            "type": "short",
            "entry": float(price),
            "stop_loss": float(sl_short),
            "take_profit_1": float(tp1s),
            "take_profit_2": float(tp2s),
            "reason": " / ".join(notes) + " (short)",
            "score_hint": 0.3,
        }
    )
    return out


def detect_all_15m(kl: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    out.extend(detect_inside_bar(kl))
    out.extend(detect_engulfing(kl))
    out.extend(detect_pin_bar(kl))
    # KeyLevel disabled - 100% SL hit rate in backtest
    # out.extend(detect_key_levels(kl))

    # Apply trend filter to reduce long bias (78% SL rate for longs)
    trend = _get_trend(kl)
    filtered = []
    for s in out:
        # Only take longs in uptrend or neutral, shorts in downtrend or neutral
        if s["type"] == "long" and trend == "down":
            continue
        if s["type"] == "short" and trend == "up":
            continue
        filtered.append(s)

    dedup = {}
    for s in filtered:
        key = (s["type"], round(s["entry"] / 0.001))
        if key not in dedup or dedup[key]["score_hint"] < s["score_hint"]:
            dedup[key] = s
    return list(dedup.values())


def detect_all_1h(kl: List[Dict]) -> List[Dict]:
    """Stricter detectors for 1h timeframe to reduce noise."""
    out: List[Dict] = []
    out.extend(detect_inside_bar(kl))
    out.extend(detect_engulfing(kl))
    out.extend(detect_pin_bar(kl, wick_ratio=2.0, body_max_frac=0.35))
    # KeyLevel disabled - 100% SL hit rate in backtest
    # out.extend(detect_key_levels(kl, tol_pct=0.004, lookback=30))

    # Apply trend filter
    trend = _get_trend(kl)
    filtered = []
    for s in out:
        if s["type"] == "long" and trend == "down":
            continue
        if s["type"] == "short" and trend == "up":
            continue
        filtered.append(s)

    dedup = {}
    for s in filtered:
        key = (s["type"], round(s["entry"] / 0.001))
        if key not in dedup or dedup[key]["score_hint"] < s["score_hint"]:
            dedup[key] = s
    return list(dedup.values())
