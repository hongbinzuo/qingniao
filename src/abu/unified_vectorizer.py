#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Feature Vectorizer - ABU System
Converts both live K-line features and Brooks pattern JSONB to 32-dim vectors

Vector Schema (32 dimensions):
  [0-2]   Direction (bullish, neutral, bearish) - one-hot
  [3]     Strength (0.0-1.0)
  [4-6]   EMA relation (above, at, below) - one-hot
  [7]     EMA slope (-1.0 to 1.0)
  [8-12]  Market cycle (accumulation, markup, distribution, markdown, range) - one-hot
  [13-19] K-line patterns (7 common patterns) - multi-hot
  [20-31] Pattern type (12 pattern families) - one-hot
"""

from typing import Dict, List, Optional, Tuple

import numpy as np

# Pattern family mapping (dims 20-31)
PATTERN_FAMILIES = [
    "trend",  # 20
    "channel",  # 21
    "triangle",  # 22
    "wedge",  # 23
    "range",  # 24
    "breakout",  # 25
    "reversal",  # 26
    "gap",  # 27
    "double_top_bottom",  # 28
    "head_shoulders",  # 29
    "flag_pennant",  # 30
    "other",  # 31
]

# K-line pattern mapping (dims 13-19)
KLINE_PATTERNS = [
    "engulfing",  # 13
    "inside_bar",  # 14
    "outside_bar",  # 15
    "pin_bar",  # 16
    "doji",  # 17
    "hammer",  # 18
    "shooting_star",  # 19
]

# Market cycle mapping (dims 8-12)
MARKET_CYCLES = [
    "accumulation",  # 8
    "markup",  # 9
    "distribution",  # 10
    "markdown",  # 11
    "range",  # 12
]


class UnifiedVectorizer:
    """Convert features to unified 32-dim vectors"""

    def __init__(self):
        self.dim = 32

    def vectorize_brooks_pattern(
        self,
        pattern_features: Dict,
        market_context: Dict,
        metadata: Optional[Dict] = None,
    ) -> np.ndarray:
        """
        Convert Brooks pattern JSONB to 32-dim vector

        Args:
            pattern_features: {primary, direction, secondary, complexity}
            market_context: {cycle, maturity, timeframe}
            metadata: {expected_outcome, win_probability, etc.}

        Returns:
            32-dim numpy array
        """
        vec = np.zeros(self.dim, dtype=np.float32)

        # [0-2] Direction from pattern_features.direction
        direction = (pattern_features.get("direction") or "neutral").lower()
        vec[0:3] = self._encode_direction(direction)

        # [3] Strength from market_context.maturity
        maturity = (market_context.get("maturity") or "").lower()
        vec[3] = self._maturity_to_strength(maturity)

        # [4-6] EMA relation - infer from direction and cycle
        cycle = (market_context.get("cycle") or "").lower()
        vec[4:7] = self._infer_ema_relation(direction, cycle)

        # [7] EMA slope - infer from direction
        vec[7] = self._direction_to_slope(direction)

        # [8-12] Market cycle from market_context.cycle
        vec[8:13] = self._encode_market_cycle(cycle)

        # [13-19] K-line patterns - infer from pattern type
        primary = (pattern_features.get("primary") or "").lower()
        vec[13:20] = self._infer_kline_patterns(primary, direction)

        # [20-31] Pattern family from pattern_features.primary
        vec[20:32] = self._encode_pattern_family(primary)

        return vec

    def _encode_pattern_family(self, primary: str) -> np.ndarray:
        """Encode pattern family as one-hot"""
        vec = np.zeros(12, dtype=np.float32)

        try:
            idx = PATTERN_FAMILIES.index(primary)
            vec[idx] = 1.0
        except ValueError:
            vec[11] = 1.0  # "other"

        return vec

    def _infer_kline_patterns(self, primary: str, direction: str) -> np.ndarray:
        """Infer K-line patterns from Brooks pattern type"""
        vec = np.zeros(7, dtype=np.float32)

        # Map Brooks patterns to likely K-line patterns
        if primary == "reversal":
            if direction in ("long", "bull", "bullish"):
                vec[5] = 0.7  # hammer
            else:
                vec[6] = 0.7  # shooting_star
        elif primary == "breakout":
            vec[0] = 0.6  # engulfing
        elif primary == "range":
            vec[4] = 0.5  # doji
        elif primary == "gap":
            vec[2] = 0.5  # outside_bar

        return vec

    def vectorize_live_kline(
        self,
        trend_features: Dict,
        ema_features: Dict,
        pattern_features: Dict,
        market_context: Optional[Dict] = None,
    ) -> np.ndarray:
        """
        Convert live K-line features to 32-dim vector

        Args:
            trend_features: {direction, strength, delta}
            ema_features: {relation, slope, distance}
            pattern_features: {detected patterns dict}
            market_context: {cycle, volatility, etc.}

        Returns:
            32-dim numpy array
        """
        vec = np.zeros(self.dim, dtype=np.float32)

        # [0-2] Direction from trend
        direction = trend_features.get("direction", "neutral")
        vec[0:3] = self._encode_direction(direction)

        # [3] Strength from trend
        vec[3] = float(trend_features.get("strength", 0.5))

        # [4-6] EMA relation
        ema_rel = ema_features.get("relation", "at")
        vec[4:7] = self._encode_ema_relation_direct(ema_rel)

        # [7] EMA slope
        vec[7] = float(ema_features.get("slope", 0.0))

        # [8-12] Market cycle
        if market_context:
            cycle = market_context.get("cycle", "range")
            vec[8:13] = self._encode_market_cycle(cycle)
        else:
            vec[12] = 1.0  # default to range

        # [13-19] K-line patterns from detected patterns
        vec[13:20] = self._encode_kline_patterns_direct(pattern_features)

        # [20-31] Pattern type - infer from strongest pattern
        primary_pattern = self._infer_primary_pattern(pattern_features)
        vec[20:32] = self._encode_pattern_family(primary_pattern)

        return vec

    def _encode_ema_relation_direct(self, relation: str) -> np.ndarray:
        """Encode EMA relation directly"""
        vec = np.zeros(3, dtype=np.float32)

        if relation in ("above", "over"):
            vec[0] = 1.0
        elif relation in ("below", "under"):
            vec[2] = 1.0
        else:
            vec[1] = 1.0  # at

        return vec

    def _encode_kline_patterns_direct(self, patterns: Dict) -> np.ndarray:
        """Encode detected K-line patterns as multi-hot"""
        vec = np.zeros(7, dtype=np.float32)

        for i, pattern_name in enumerate(KLINE_PATTERNS):
            if patterns.get(pattern_name, False):
                vec[i] = 1.0

        return vec

    def _infer_primary_pattern(self, patterns: Dict) -> str:
        """Infer primary pattern from detected patterns"""
        # Simple heuristic: if reversal patterns detected, classify as reversal
        if patterns.get("hammer") or patterns.get("shooting_star"):
            return "reversal"
        elif patterns.get("engulfing"):
            return "breakout"
        elif patterns.get("doji"):
            return "range"
        else:
            return "trend"

    def _encode_direction(self, direction: str) -> np.ndarray:
        """Encode direction as one-hot [bullish, neutral, bearish]"""
        vec = np.zeros(3, dtype=np.float32)

        if direction in ("long", "bull", "bullish", "up"):
            vec[0] = 1.0  # bullish
        elif direction in ("short", "bear", "bearish", "down"):
            vec[2] = 1.0  # bearish
        else:
            vec[1] = 1.0  # neutral

        return vec

    def _maturity_to_strength(self, maturity: str) -> float:
        """Convert maturity to strength score"""
        maturity_map = {
            "early": 0.3,
            "developing": 0.5,
            "mature": 0.8,
            "late": 0.6,
            "exhausted": 0.4,
        }
        return maturity_map.get(maturity, 0.5)

    def _infer_ema_relation(self, direction: str, cycle: str) -> np.ndarray:
        """Infer EMA relation from direction and cycle"""
        vec = np.zeros(3, dtype=np.float32)

        # Bullish patterns typically above EMA
        if direction in ("long", "bull", "bullish", "up"):
            vec[0] = 0.7  # above
            vec[1] = 0.3  # at
        # Bearish patterns typically below EMA
        elif direction in ("short", "bear", "bearish", "down"):
            vec[2] = 0.7  # below
            vec[1] = 0.3  # at
        # Neutral patterns at EMA
        else:
            vec[1] = 1.0  # at

        return vec

    def _direction_to_slope(self, direction: str) -> float:
        """Convert direction to EMA slope"""
        if direction in ("long", "bull", "bullish", "up"):
            return 0.5  # positive slope
        elif direction in ("short", "bear", "bearish", "down"):
            return -0.5  # negative slope
        else:
            return 0.0  # flat

    def _encode_market_cycle(self, cycle: str) -> np.ndarray:
        """Encode market cycle as one-hot"""
        vec = np.zeros(5, dtype=np.float32)

        cycle_map = {
            "accumulation": 0,
            "markup": 1,
            "distribution": 2,
            "markdown": 3,
            "range": 4,
        }

        idx = cycle_map.get(cycle, 4)  # default to range
        vec[idx] = 1.0

        return vec
