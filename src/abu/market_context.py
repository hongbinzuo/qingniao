#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Market structure context classifier (Brooks-style)."""
from __future__ import annotations

from typing import Dict, List, Optional


def _calculate_overlap_ratio(klines: List[Dict], lookback: int = 20) -> float:
    if not klines or len(klines) < 2:
        return 0.0
    window = klines[-lookback:] if len(klines) > lookback else klines
    ratios = []
    for i in range(1, len(window)):
        prev = window[i - 1]
        cur = window[i]
        high = max(float(prev.get("high", 0)), float(cur.get("high", 0)))
        low = min(float(prev.get("low", 0)), float(cur.get("low", 0)))
        span = max(high - low, 1e-9)
        overlap = max(0.0, min(float(prev.get("high", 0)), float(cur.get("high", 0))) -
                      max(float(prev.get("low", 0)), float(cur.get("low", 0))))
        ratios.append(overlap / span)
    return sum(ratios) / len(ratios) if ratios else 0.0


def classify_market_context(klines: List[Dict], features: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    features = features or {}
    trend_strength = float(features.get("trend_strength") or 0.0)
    pullback_depth = float(features.get("pullback_depth_pct") or 0.0)
    range_mode = bool(features.get("range_mode"))
    trend_dir = str(features.get("trend_direction") or "neutral").lower()
    overlap_ratio = _calculate_overlap_ratio(klines, lookback=20)

    context = "broad_channel"
    if trend_strength >= 0.02 and pullback_depth <= 0.008 and overlap_ratio < 0.35:
        context = "strong_trend"
    elif range_mode or overlap_ratio >= 0.55:
        context = "trading_range"

    label = context
    if context == "strong_trend":
        label = "strong_bull_trend" if trend_dir == "bullish" else "strong_bear_trend"

    return {
        "context": context,
        "label": label,
        "trend_direction": trend_dir,
        "trend_strength": trend_strength,
        "pullback_depth_pct": pullback_depth,
        "overlap_ratio": overlap_ratio,
    }


def context_mismatch(context_info: Dict[str, object], pattern_name: Optional[str], direction: Optional[str]) -> Optional[str]:
    if not context_info or not pattern_name:
        return None
    ctx = str(context_info.get("context") or "")
    trend_dir = str(context_info.get("trend_direction") or "")
    name = str(pattern_name).lower()
    dir_lower = str(direction or "").lower()

    strong_trend_patterns = ("small pullback", "bull trend", "bear trend")
    if any(key in name for key in strong_trend_patterns):
        if ctx != "strong_trend":
            return "背景不匹配(通道/震荡)"
        if "bull" in name and trend_dir != "bullish":
            return "背景不匹配(多头趋势不足)"
        if "bear" in name and trend_dir != "bearish":
            return "背景不匹配(空头趋势不足)"
        if dir_lower in ("long", "short") and trend_dir in ("bullish", "bearish"):
            if (dir_lower == "long" and trend_dir != "bullish") or (dir_lower == "short" and trend_dir != "bearish"):
                return "背景不匹配(趋势方向冲突)"

    return None

