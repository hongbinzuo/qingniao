#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qingniao-PA Detectors (15m)

Very lightweight price-action detectors designed for 15m scan:
- inside_bar: last candle's range inside previous candle.
- engulfing: bullish/bearish body engulf.
- pin_bar: long wick vs body and total range.
- key_levels: proximity to round/structural levels (recent HH/LL and round steps).

All detectors return a list[dict] of candidate entries with:
  {
    'pattern': 'InsideBar'|'Engulfing'|'PinBar'|'KeyLevel',
    'type': 'long'|'short',
    'entry': float,              # suggested entry (use current close)
    'stop_loss': float,          # suggested SL
    'take_profit_1': float,      # TP1 (1R by default)
    'take_profit_2': float,      # TP2 (2R by default)
    'reason': str,
    'score_hint': float          # small intrinsic score contribution
  }

Detectors are intentionally conservative (no downsampling/no TA lib deps) and
should be composed with a ranker.
"""
from __future__ import annotations
from typing import List, Dict, Optional, Tuple


def _rr_pack(entry: float, sl: float, typ: str, r_mult1: float = 1.0, r_mult2: float = 2.0) -> Tuple[float, float]:
    """Compute TP1/TP2 as 1R/2R from entry/SL for long/short."""
    risk = abs(entry - sl)
    if risk <= 0:
        return entry, entry
    if typ == 'long':
        return entry + r_mult1 * risk, entry + r_mult2 * risk
    else:
        return entry - r_mult1 * risk, entry - r_mult2 * risk


def _round_step(price: float) -> float:
    """Determine a natural rounding step for symbol at its price scale.
    90k-levels for BTC-like; for alts choose order-of-magnitude based step.
    """
    if price <= 0:
        return 0.01
    import math
    p = abs(price)
    # choose step so about ~100 levels per decade
    exp = math.floor(math.log10(p))
    base = 10 ** exp
    # heuristics: finer for low-priced alts
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


def _recent_hh_ll(kl: List[Dict], lookback: int = 20) -> Tuple[Optional[float], Optional[float]]:
    if not kl:
        return None, None
    seg = kl[-lookback:]
    hh = max(x['high'] for x in seg) if seg else None
    ll = min(x['low'] for x in seg) if seg else None
    return hh, ll


def detect_inside_bar(kl: List[Dict]) -> List[Dict]:
    if len(kl) < 2:
        return []
    a = kl[-2]; b = kl[-1]
    out: List[Dict] = []
    if b['high'] <= a['high'] and b['low'] >= a['low']:
        # breakout ideas either way; bias will be handled by ranker
        entry_long = b['close']
        sl_long = min(b['low'], a['low'])
        tp1, tp2 = _rr_pack(entry_long, sl_long, 'long')
        out.append({
            'pattern': 'InsideBar', 'type': 'long', 'entry': float(entry_long), 'stop_loss': float(sl_long),
            'take_profit_1': float(tp1), 'take_profit_2': float(tp2), 'reason': 'Inside bar (break-up)', 'score_hint': 0.6
        })
        entry_short = b['close']
        sl_short = max(b['high'], a['high'])
        tp1s, tp2s = _rr_pack(entry_short, sl_short, 'short')
        out.append({
            'pattern': 'InsideBar', 'type': 'short', 'entry': float(entry_short), 'stop_loss': float(sl_short),
            'take_profit_1': float(tp1s), 'take_profit_2': float(tp2s), 'reason': 'Inside bar (break-down)', 'score_hint': 0.6
        })
    return out


def detect_engulfing(kl: List[Dict]) -> List[Dict]:
    if len(kl) < 2:
        return []
    p = kl[-2]; c = kl[-1]
    out: List[Dict] = []
    # bullish engulfing: c body up and engulfs p body
    if c['close'] > c['open'] and p['close'] < p['open']:
        if (c['close'] >= p['open']) and (c['open'] <= p['close']):
            entry = c['close']
            sl = min(c['low'], p['low'])
            tp1, tp2 = _rr_pack(entry, sl, 'long')
            out.append({
                'pattern': 'Engulfing', 'type': 'long', 'entry': float(entry), 'stop_loss': float(sl),
                'take_profit_1': float(tp1), 'take_profit_2': float(tp2), 'reason': 'Bullish engulfing', 'score_hint': 0.8
            })
    # bearish engulfing
    if c['close'] < c['open'] and p['close'] > p['open']:
        if (c['close'] <= p['open']) and (c['open'] >= p['close']):
            entry = c['close']
            sl = max(c['high'], p['high'])
            tp1, tp2 = _rr_pack(entry, sl, 'short')
            out.append({
                'pattern': 'Engulfing', 'type': 'short', 'entry': float(entry), 'stop_loss': float(sl),
                'take_profit_1': float(tp1), 'take_profit_2': float(tp2), 'reason': 'Bearish engulfing', 'score_hint': 0.8
            })
    return out


def detect_pin_bar(kl: List[Dict], wick_ratio: float = 1.5, body_max_frac: float = 0.4) -> List[Dict]:
    if not kl:
        return []
    c = kl[-1]
    o, h, l, cl = c['open'], c['high'], c['low'], c['close']
    body = abs(cl - o); rng = max(h - l, 1e-9)
    upper = h - max(o, cl)
    lower = min(o, cl) - l
    out: List[Dict] = []
    # bullish pin: long lower wick, small body
    if lower > wick_ratio * body and (body / rng) <= body_max_frac:
        entry = cl
        sl = l
        tp1, tp2 = _rr_pack(entry, sl, 'long')
        out.append({
            'pattern': 'PinBar', 'type': 'long', 'entry': float(entry), 'stop_loss': float(sl),
            'take_profit_1': float(tp1), 'take_profit_2': float(tp2), 'reason': 'Bullish pin-bar', 'score_hint': 0.5
        })
    # bearish pin: long upper wick
    if upper > wick_ratio * body and (body / rng) <= body_max_frac:
        entry = cl
        sl = h
        tp1, tp2 = _rr_pack(entry, sl, 'short')
        out.append({
            'pattern': 'PinBar', 'type': 'short', 'entry': float(entry), 'stop_loss': float(sl),
            'take_profit_1': float(tp1), 'take_profit_2': float(tp2), 'reason': 'Bearish pin-bar', 'score_hint': 0.5
        })
    return out


def detect_key_levels(kl: List[Dict], tol_pct: float = 0.003) -> List[Dict]:
    """Close to recent HH/LL or round level -> small confluence candidates.
    Not directional by itself; both sides generated, ranker will filter by trend.
    """
    if not kl:
        return []
    c = kl[-1]
    price = c['close']
    hh, ll = _recent_hh_ll(kl, 20)
    round_lv = _nearest_round(price)
    out: List[Dict] = []
    def _near(a: float, b: float) -> bool:
        if a is None or b is None or a <= 0:
            return False
        return abs(b - a) / a <= tol_pct
    notes = []
    if hh and _near(hh, price):
        notes.append('near_HH')
    if ll and _near(ll, price):
        notes.append('near_LL')
    if round_lv and _near(round_lv, price):
        notes.append('near_round')
    if not notes:
        return []
    # Provide both directions (ranker to decide by trend/rr)
    sl_long = min([x['low'] for x in kl[-3:]])
    tp1, tp2 = _rr_pack(price, sl_long, 'long')
    out.append({
        'pattern': 'KeyLevel', 'type': 'long', 'entry': float(price), 'stop_loss': float(sl_long),
        'take_profit_1': float(tp1), 'take_profit_2': float(tp2), 'reason': ' / '.join(notes) + ' (long)', 'score_hint': 0.3
    })
    sl_short = max([x['high'] for x in kl[-3:]])
    tp1s, tp2s = _rr_pack(price, sl_short, 'short')
    out.append({
        'pattern': 'KeyLevel', 'type': 'short', 'entry': float(price), 'stop_loss': float(sl_short),
        'take_profit_1': float(tp1s), 'take_profit_2': float(tp2s), 'reason': ' / '.join(notes) + ' (short)', 'score_hint': 0.3
    })
    return out


def detect_all_15m(kl: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    out.extend(detect_inside_bar(kl))
    out.extend(detect_engulfing(kl))
    out.extend(detect_pin_bar(kl))
    out.extend(detect_key_levels(kl))
    # de-duplicate by (type, entry ~0.1%) keep higher score_hint
    dedup = {}
    for s in out:
        key = (s['type'], round(s['entry'] / 0.001) )
        if key not in dedup or dedup[key]['score_hint'] < s['score_hint']:
            dedup[key] = s
    return list(dedup.values())

