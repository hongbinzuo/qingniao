#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Best-practice rulebook for ABU signal filtering."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG = ROOT / "config" / "abu_best_practices.yaml"

DEFAULT_RULES = {
    "enabled": True,
    "rules": {
        "require_pattern_match": False,
        "min_pattern_score": 0.2,
        "min_brooks_score": 0.2,
        "allowed_brooks_status": ["pass", "warn"],
        "allow_against_trend": False,
        "strong_trend_threshold": 0.02,
        "range_mode_only_patterns": ["trading_range", "range"],
        "trend_mode_avoid_patterns": ["trading_range"],
        "require_breakout_confirmation": False,
        "max_stop_pct": 0.02,
        "min_rr": 1.0,
    },
}


def _normalize_pattern_type(pattern_type: Optional[str]) -> str:
    if not pattern_type:
        return "unknown"
    text = pattern_type.lower()
    if "breakout" in text:
        return "breakout"
    if "reversal" in text:
        return "reversal"
    if "trend" in text:
        return "trend"
    if "range" in text or "trading_range" in text:
        return "trading_range"
    return text


@dataclass
class RuleResult:
    passed: bool
    reasons: List[str]


class BestPracticeRulebook:
    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path = config_path or DEFAULT_CONFIG
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        config = DEFAULT_RULES
        if not self.config_path.exists():
            return config
        try:
            import yaml  # type: ignore
        except Exception:
            return config
        try:
            loaded = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
            rules = {**config.get("rules", {}), **(loaded.get("rules") or {})}
            return {
                "enabled": loaded.get("enabled", config.get("enabled", True)),
                "rules": rules,
            }
        except Exception:
            return config

    def evaluate(
        self,
        candidate: Dict[str, Any],
        features: Dict[str, Any],
        *,
        pattern_type: Optional[str],
        pattern_score: Optional[float],
        brooks_score: Optional[float],
        brooks_status: Optional[str],
        pattern_match: Optional[str],
    ) -> RuleResult:
        rules = self.config.get("rules", {})
        if not self.config.get("enabled", True):
            return RuleResult(True, [])

        reasons: List[str] = []
        direction = (candidate.get("type") or "").lower()
        entry = float(candidate.get("entry") or 0.0)
        stop = float(candidate.get("stop_loss") or 0.0)
        tp1 = float(candidate.get("take_profit_1") or 0.0)

        if rules.get("require_pattern_match") and not pattern_match:
            reasons.append("missing_pattern_match")
            return RuleResult(False, reasons)

        if pattern_score is not None and pattern_match:
            min_pattern_score = rules.get("min_pattern_score")
            if min_pattern_score is not None and pattern_score < float(min_pattern_score):
                reasons.append("low_pattern_score")
                return RuleResult(False, reasons)

        if brooks_score is not None:
            min_brooks_score = rules.get("min_brooks_score")
            if min_brooks_score is not None and brooks_score < float(min_brooks_score):
                reasons.append("low_brooks_score")
                return RuleResult(False, reasons)

        allowed_status = [str(x).lower() for x in (rules.get("allowed_brooks_status") or [])]
        if allowed_status and brooks_status and brooks_status.lower() not in allowed_status:
            reasons.append("brooks_status_blocked")
            return RuleResult(False, reasons)

        if entry > 0 and stop > 0:
            stop_pct = abs(entry - stop) / entry
            max_stop_pct = rules.get("max_stop_pct")
            if max_stop_pct is not None and stop_pct > float(max_stop_pct):
                reasons.append("stop_pct_too_large")
                return RuleResult(False, reasons)
            min_rr = rules.get("min_rr")
            if min_rr is not None:
                risk = abs(entry - stop)
                rr1 = abs(tp1 - entry) / risk if risk > 0 else 0.0
                if rr1 < float(min_rr):
                    reasons.append("rr_too_low")
                    return RuleResult(False, reasons)

        trend_dir = (features.get("trend_direction") or "").lower()
        trend_strength = float(features.get("trend_strength") or 0.0)
        allow_against = bool(rules.get("allow_against_trend"))
        strong_threshold = float(rules.get("strong_trend_threshold") or 0.0)
        if not allow_against and trend_strength >= strong_threshold:
            if trend_dir == "bullish" and direction == "short":
                reasons.append("against_strong_trend")
                return RuleResult(False, reasons)
            if trend_dir == "bearish" and direction == "long":
                reasons.append("against_strong_trend")
                return RuleResult(False, reasons)

        norm_type = _normalize_pattern_type(pattern_type)
        if features.get("range_mode"):
            allowed_range = [str(x).lower() for x in (rules.get("range_mode_only_patterns") or [])]
            if allowed_range and norm_type not in allowed_range:
                reasons.append("range_mode_filter")
                return RuleResult(False, reasons)
        else:
            avoid_trend = [str(x).lower() for x in (rules.get("trend_mode_avoid_patterns") or [])]
            if avoid_trend and norm_type in avoid_trend:
                reasons.append("trend_mode_filter")
                return RuleResult(False, reasons)

        if rules.get("require_breakout_confirmation"):
            breakout_up = bool(features.get("breakout_up"))
            breakout_down = bool(features.get("breakout_down"))
            if norm_type == "breakout":
                if direction == "long" and not breakout_up:
                    reasons.append("breakout_not_confirmed")
                    return RuleResult(False, reasons)
                if direction == "short" and not breakout_down:
                    reasons.append("breakout_not_confirmed")
                    return RuleResult(False, reasons)

        return RuleResult(True, reasons)
