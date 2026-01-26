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


def _classify_volatility_regime(
    features: Dict[str, object],
    overlap_ratio: float,
) -> str:
    trend_strength = float(features.get("trend_strength") or 0.0)
    pullback_depth = float(features.get("pullback_depth_pct") or 0.0)
    range_pct = float(features.get("range_pct") or 0.0)
    dist_to_ema_pct = float(features.get("dist_to_ema_pct") or 0.0)

    if overlap_ratio >= 0.6 and range_pct <= 0.02:
        return "narrow_range"
    if overlap_ratio >= 0.45 and range_pct >= 0.04:
        return "wide_range"
    if trend_strength >= 0.02 and pullback_depth <= 0.008 and overlap_ratio < 0.35:
        return "strong_trend"
    if trend_strength >= 0.012 and overlap_ratio < 0.45:
        return "weak_trend"

    rebound_score = max(pullback_depth, dist_to_ema_pct)
    if rebound_score >= 0.015:
        return "strong_rebound"
    if rebound_score >= 0.008:
        return "weak_rebound"
    return "weak_rebound"


def _classify_regime_36(
    features: Dict[str, object],
    overlap_ratio: float,
) -> Dict[str, str]:
    trend_dir = str(features.get("trend_direction") or "neutral").lower()
    direction = "neutral"
    if trend_dir == "bullish":
        direction = "bull"
    elif trend_dir == "bearish":
        direction = "bear"

    trend_strength = float(features.get("trend_strength") or 0.0)
    strength = "strong" if trend_strength >= 0.02 else "weak"

    range_pct = float(features.get("range_pct") or 0.0)
    if range_pct <= 0.02:
        width = "narrow"
    elif range_pct >= 0.05:
        width = "wide"
    else:
        width = "normal"

    range_mode = bool(features.get("range_mode"))
    structure = "choppy" if range_mode or overlap_ratio >= 0.55 else "smooth"

    return {
        "direction": direction,
        "strength": strength,
        "width": width,
        "structure": structure,
        "label": f"{direction}_{strength}_{width}_{structure}",
    }


def classify_market_context(klines: List[Dict], features: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    features = features or {}
    trend_strength = float(features.get("trend_strength") or 0.0)
    pullback_depth = float(features.get("pullback_depth_pct") or 0.0)
    range_mode = bool(features.get("range_mode"))
    trend_dir = str(features.get("trend_direction") or "neutral").lower()
    overlap_ratio = _calculate_overlap_ratio(klines, lookback=20)
    regime = _classify_volatility_regime(features, overlap_ratio)
    regime_36 = _classify_regime_36(features, overlap_ratio)

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
        "regime": regime,
        "regime_36": regime_36.get("label"),
        "regime_36_components": {
            "direction": regime_36.get("direction"),
            "strength": regime_36.get("strength"),
            "width": regime_36.get("width"),
            "structure": regime_36.get("structure"),
        },
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


def _normalize_pattern_type(pattern_type: Optional[str]) -> str:
    if not pattern_type:
        return "unknown"
    text = str(pattern_type).lower()
    if "breakout" in text:
        return "breakout"
    if "reversal" in text:
        return "reversal"
    if "trend" in text:
        return "trend"
    if "range" in text or "trading_range" in text:
        return "trading_range"
    return text


def _parse_regime_36_label(label: Optional[str]) -> Dict[str, str]:
    if not label:
        return {}
    parts = str(label).split("_")
    if len(parts) < 4:
        return {}
    return {
        "direction": parts[0],
        "strength": parts[1],
        "width": parts[2],
        "structure": parts[3],
    }


def context_filter_reason(
    context_info: Dict[str, object],
    pattern_type: Optional[str],
    direction: Optional[str],
    mode: str = "off",
) -> Optional[str]:
    mode = (mode or "off").lower()
    if mode in ("off", "none", "0"):
        return None
    if not context_info:
        return None

    norm_type = _normalize_pattern_type(pattern_type)
    if norm_type == "unknown":
        return None

    direction = (direction or "").lower()
    trend_dir = str(context_info.get("trend_direction") or "").lower()
    ctx = str(context_info.get("context") or "").lower()

    if mode in ("brooks", "both"):
        if ctx == "trading_range" and norm_type in ("trend", "breakout"):
            return "Context过滤(区间禁趋势/突破)"
        if ctx == "strong_trend":
            if trend_dir == "bullish" and direction == "short":
                return "Context过滤(强趋势逆势)"
            if trend_dir == "bearish" and direction == "long":
                return "Context过滤(强趋势逆势)"

    if mode in ("regime36", "both"):
        reg = context_info.get("regime_36_components") or _parse_regime_36_label(
            str(context_info.get("regime_36") or "")
        )
        if not reg:
            return None
        reg_dir = str(reg.get("direction") or "")
        reg_strength = str(reg.get("strength") or "")
        reg_structure = str(reg.get("structure") or "")

        if norm_type in ("trend", "breakout"):
            if reg_dir == "neutral":
                return "Regime36过滤(方向不明)"
            if reg_dir == "bull" and direction == "short":
                return "Regime36过滤(方向冲突)"
            if reg_dir == "bear" and direction == "long":
                return "Regime36过滤(方向冲突)"
            if reg_structure == "choppy":
                return "Regime36过滤(震荡结构)"
        if norm_type in ("trading_range", "reversal"):
            if reg_strength == "strong" and reg_structure == "smooth" and reg_dir in ("bull", "bear"):
                return "Regime36过滤(强趋势非区间)"

    return None
