#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Basic K-line feature extraction for Brooks-style constraints and pattern scoring."""
from __future__ import annotations
from typing import List, Dict, Tuple


def _safe_pct(numer: float, denom: float) -> float:
    if denom == 0:
        return 0.0
    return numer / denom


def _ema(values: List[float], period: int) -> float:
    if not values:
        return 0.0
    k = 2 / (period + 1)
    ema_val = values[0]
    for value in values:
        ema_val = value * k + ema_val * (1 - k)
    return ema_val


def _detect_kline_features(klines: List[Dict]) -> List[str]:
    if not klines:
        return []
    recent = klines[-5:] if len(klines) >= 5 else klines
    features = []
    for i in range(1, len(recent)):
        last = recent[i]
        prev = recent[i - 1]

        if last['close'] > last['open'] and prev['close'] < prev['open']:
            if last['open'] < prev['close'] and last['close'] > prev['open']:
                features.append('bullish_engulfing')
        elif last['close'] < last['open'] and prev['close'] > prev['open']:
            if last['open'] > prev['close'] and last['close'] < prev['open']:
                features.append('bearish_engulfing')

        body = abs(last['close'] - last['open'])
        rng = max(last['high'] - last['low'], 1e-9)
        upper = last['high'] - max(last['open'], last['close'])
        lower = min(last['open'], last['close']) - last['low']
        body_ratio = body / rng

        if body_ratio < 0.3:
            if upper > lower * 2:
                features.append('bearish_pin_bar')
            elif lower > upper * 2:
                features.append('bullish_pin_bar')

        if last['high'] < prev['high'] and last['low'] > prev['low']:
            features.append('inside_bar')

    return list(set(features))


def _find_local_extrema(values: List[float], window: int, mode: str) -> List[Tuple[int, float]]:
    extrema: List[Tuple[int, float]] = []
    if len(values) < window * 2 + 1:
        return extrema
    for i in range(window, len(values) - window):
        seg = values[i - window : i + window + 1]
        if mode == 'min':
            if values[i] == min(seg):
                extrema.append((i, values[i]))
        else:
            if values[i] == max(seg):
                extrema.append((i, values[i]))
    return extrema


def _detect_double_bottom(lows: List[float], tolerance: float = 0.01, min_separation: int = 5) -> bool:
    mins = _find_local_extrema(lows, window=2, mode='min')
    if len(mins) < 2:
        return False
    (i1, v1), (i2, v2) = mins[-2], mins[-1]
    if i2 - i1 < min_separation:
        return False
    denom = max(v1, v2, 1e-9)
    return abs(v1 - v2) / denom <= tolerance


def _detect_double_top(highs: List[float], tolerance: float = 0.01, min_separation: int = 5) -> bool:
    maxs = _find_local_extrema(highs, window=2, mode='max')
    if len(maxs) < 2:
        return False
    (i1, v1), (i2, v2) = maxs[-2], maxs[-1]
    if i2 - i1 < min_separation:
        return False
    denom = max(v1, v2, 1e-9)
    return abs(v1 - v2) / denom <= tolerance


def extract_basic_kline_features(klines: List[Dict], lookback: int = 50) -> Dict[str, object]:
    if not klines or len(klines) < 10:
        return {}

    recent = klines[-lookback:] if len(klines) > lookback else klines
    closes = [k['close'] for k in recent]
    highs = [k['high'] for k in recent]
    lows = [k['low'] for k in recent]

    close0 = closes[0]
    close_last = closes[-1]

    trend_delta = _safe_pct(close_last - close0, close0)
    abs_strength = abs(trend_delta)
    if abs_strength < 0.003:
        trend_direction = 'neutral'
    else:
        trend_direction = 'bullish' if trend_delta > 0 else 'bearish'

    ranges = [(h - l) for h, l in zip(highs, lows)]
    avg_range = sum(ranges) / len(ranges) if ranges else 0.0
    volatility = _safe_pct(avg_range, close_last)

    range_high = max(highs)
    range_low = min(lows)
    range_pct = _safe_pct(range_high - range_low, close_last)

    prev_high = max(highs[:-1]) if len(highs) > 1 else range_high
    prev_low = min(lows[:-1]) if len(lows) > 1 else range_low

    breakout_up = close_last > prev_high * 1.001
    breakout_down = close_last < prev_low * 0.999

    if trend_direction == 'bullish' and prev_high > 0:
        pullback_depth_pct = _safe_pct(prev_high - close_last, prev_high)
    elif trend_direction == 'bearish' and prev_low > 0:
        pullback_depth_pct = _safe_pct(close_last - prev_low, prev_low)
    else:
        pullback_depth_pct = 0.0

    range_high_dist_pct = _safe_pct(abs(range_high - close_last), close_last)
    range_low_dist_pct = _safe_pct(abs(close_last - range_low), close_last)

    range_mode = range_pct <= 0.03 and abs_strength <= 0.012

    ema_20 = _ema(closes, 20)
    dist_to_ema_pct = _safe_pct(abs(close_last - ema_20), ema_20)

    kline_features = _detect_kline_features(recent)

    swing_highs = _find_local_extrema(highs[-30:], window=2, mode='max')
    swing_lows = _find_local_extrema(lows[-30:], window=2, mode='min')

    return {
        'trend_direction': trend_direction,
        'trend_strength': abs_strength,
        'trend_delta': trend_delta,
        'volatility': volatility,
        'range_pct': range_pct,
        'range_high_dist_pct': range_high_dist_pct,
        'range_low_dist_pct': range_low_dist_pct,
        'range_mode': range_mode,
        'ema_20': ema_20,
        'dist_to_ema_pct': dist_to_ema_pct,
        'breakout_up': breakout_up,
        'breakout_down': breakout_down,
        'pullback_depth_pct': pullback_depth_pct,
        'kline_features': kline_features,
        'double_bottom': _detect_double_bottom(lows[-30:]),
        'double_top': _detect_double_top(highs[-30:]),
        'swing_high_count': len(swing_highs),
        'swing_low_count': len(swing_lows),
        'last_close': close_last,
    }
