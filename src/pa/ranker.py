#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Tuple


def ema(xs: List[float], n: int) -> float | None:
    if not xs:
        return None
    k = 2/(n+1)
    e = xs[0]
    for x in xs:
        e = x*k + e*(1-k)
    return e


def trend_backing(k1h: List[Dict]) -> str:
    if not k1h or len(k1h) < 200:
        return 'neutral'
    closes = [x['close'] for x in k1h]
    e200 = ema(closes, 200) or closes[-1]
    price = closes[-1]
    if price > e200:
        return 'bull'
    if price < e200:
        return 'bear'
    return 'neutral'


def score_candidate(c: Dict, k1h: List[Dict]) -> float:
    base = c.get('score_hint') or 0.0
    # RR estimate weight
    e = float(c['entry']); sl = float(c['stop_loss'])
    risk = abs(e - sl)
    rr1 = 0.0
    tp1 = float(c.get('take_profit_1') or e)
    if risk > 0:
        rr1 = abs(tp1 - e) / risk
    rr_score = max(0.0, min(2.0, rr1)) * 0.6
    # trend confluence
    tb = trend_backing(k1h)
    conf = 0.0
    if tb == 'bull' and c['type'] == 'long':
        conf = 0.6
    elif tb == 'bear' and c['type'] == 'short':
        conf = 0.6
    else:
        conf = 0.2
    return base + rr_score + conf


def rank_and_pick(cands: List[Dict], k1h: List[Dict], topn: int = 10) -> List[Dict]:
    if not cands:
        return []
    scored = []
    for c in cands:
        s = score_candidate(c, k1h)
        c2 = dict(c)
        c2['_score'] = s
        scored.append(c2)
    scored.sort(key=lambda x: x['_score'], reverse=True)
    return scored[:topn]

