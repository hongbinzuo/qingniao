#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict
from pathlib import Path
import json


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


def _load_pattern_weights() -> Dict[str, Dict[str, float]]:
    try:
        root = Path(__file__).resolve().parent.parent
        cfg = root / 'config' / 'abu_pattern_weights.yaml'
        if not cfg.exists():
            # also try project root/config
            cfg = Path(__file__).resolve().parents[2] / 'config' / 'abu_pattern_weights.yaml'
        if cfg.exists():
            try:
                import yaml  # type: ignore
                obj = yaml.safe_load(cfg.read_text(encoding='utf-8')) or {}
                return obj.get('weights') or {}
            except Exception:
                pass
    except Exception:
        pass
    return {}


_PAT_WEIGHTS = _load_pattern_weights()


def score_candidate(c: Dict, k1h: List[Dict]) -> float:
    base = c.get('score_hint') or 0.0
    e = float(c['entry']); sl = float(c['stop_loss'])
    risk = abs(e - sl)
    rr1 = 0.0
    tp1 = float(c.get('take_profit_1') or e)
    if risk > 0:
        rr1 = abs(tp1 - e) / risk
    rr_score = max(0.0, min(2.0, rr1)) * 0.6
    tb = trend_backing(k1h)
    conf = 0.0
    if tb == 'bull' and c['type'] == 'long':
        conf = 0.6
    elif tb == 'bear' and c['type'] == 'short':
        conf = 0.6
    else:
        conf = 0.2
    # pattern bonus
    pat = (c.get('pattern') or '').strip()
    typ = (c.get('type') or '').strip()
    bonus = 0.0
    if pat and typ and _PAT_WEIGHTS:
        try:
            bonus = float((_PAT_WEIGHTS.get(pat) or {}).get(typ) or 0.0)
        except Exception:
            bonus = 0.0
    
    # ML评分提升（如果可用）
    ml_boost = 0.0
    if c.get('_ml_available'):
        try:
            from abu.ml_enhancer import calculate_ml_score_boost
            ml_boost = calculate_ml_score_boost(c)
        except Exception:
            pass
    
    return base + rr_score + conf + bonus + ml_boost


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
