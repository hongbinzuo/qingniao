#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU 问答式交易建议（CLI）

示例:
  python scripts/abu_query_advisor.py --symbol BTC --timeframe 15m --direction long
  python scripts/abu_query_advisor.py --question "BTC 15m 做多机会？"
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.detectors import detect_all_15m, detect_all_1h  # type: ignore
from abu.best_practice_rules import BestPracticeRulebook  # type: ignore
from abu.signal_probability_estimator import SignalProbabilityEstimator  # type: ignore
from abu.market_cache import MarketDataCache  # type: ignore
from abu.ranker import score_candidate  # type: ignore
from abu.kline_feature_extractor import extract_basic_kline_features  # type: ignore
from abu.brooks_pattern_constraints import BrooksPatternConstraints, ConstraintResult  # type: ignore

try:
    from abu.unified_pattern_library import UnifiedPatternLibrary  # type: ignore
    PATTERN_LIB_AVAILABLE = True
except Exception:
    UnifiedPatternLibrary = None
    PATTERN_LIB_AVAILABLE = False


KLINES_PER_DAY = {"5m": 288, "15m": 96, "1h": 24}
DEFAULT_DAYS = {"5m": 5, "15m": 14, "1h": 45}
MIN_STOP_PCT = {"5m": 0.005, "15m": 0.008, "1h": 0.01}
PATTERN_TYPE_MAP = {
    "InsideBar": "breakout",
    "Engulfing": "reversal",
    "PinBar": "reversal",
    "KeyLevel": "trading_range",
}
PATTERN_SOURCES = ["gemini_pro3"]
USE_BROOKS_RULES = False


def _parse_question(question: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not question:
        return None, None, None
    text = question.strip()
    direction = None
    if any(k in text.lower() for k in ["做多", "多头", "long"]):
        direction = "long"
    if any(k in text.lower() for k in ["做空", "空头", "short"]):
        direction = "short"

    tf_match = re.search(r"\b(1m|5m|15m|30m|1h|4h|1d)\b", text.lower())
    timeframe = tf_match.group(1) if tf_match else None

    symbol = None
    for tok in re.findall(r"\b[A-Z]{2,10}\b", text):
        if tok.lower() in {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}:
            continue
        symbol = tok.upper()
        break
    return symbol, timeframe, direction


def _build_pattern_type(candidate: Dict) -> str:
    base = (candidate.get("pattern") or "").strip()
    if not base:
        return "unknown"
    mapped = PATTERN_TYPE_MAP.get(base, base)
    mapped = str(mapped).strip().lower().replace(" ", "_")
    direction = (candidate.get("type") or "").lower()
    if mapped == "breakout":
        if direction == "long":
            return "bull_breakout"
        if direction == "short":
            return "bear_breakout"
    return mapped or base.lower().replace(" ", "_")


def build_query_features(candidate: Dict, features: Dict[str, object]) -> Dict[str, object]:
    trend_strength = float(features.get("trend_strength") or 0.0)
    volatility = float(features.get("volatility") or 0.0)
    return {
        "pattern_type": _build_pattern_type(candidate),
        "direction": candidate.get("type") or "neutral",
        "kline_features": features.get("kline_features") or [],
        "trend": features.get("trend_direction") or "neutral",
        "market_conditions": {
            "trend_strength": "strong" if trend_strength >= 0.02 else "weak",
            "volatility": "high" if volatility >= 0.01 else "low",
            "trend_direction": features.get("trend_direction") or "neutral",
        },
    }


def estimate_probabilities(
    candidate: Dict,
    features: Dict[str, object],
    pattern_score: Optional[float],
    brooks_score: Optional[float],
    brooks_status: Optional[str],
    empirical: Optional[object] = None,
) -> Tuple[float, float, float, str, int]:
    base = 0.45
    if pattern_score is not None:
        base += 0.25 * float(pattern_score)
    if brooks_score is not None:
        base += 0.2 * float(brooks_score)
    if (brooks_status or "").lower() == "pass":
        base += 0.05

    trend_dir = (features.get("trend_direction") or "").lower()
    direction = (candidate.get("type") or "").lower()
    if trend_dir == "bullish" and direction == "long":
        base += 0.05
    elif trend_dir == "bearish" and direction == "short":
        base += 0.05
    elif trend_dir in ("bullish", "bearish"):
        base -= 0.05

    entry = float(candidate.get("entry") or 0.0)
    stop = float(candidate.get("stop_loss") or 0.0)
    tp1 = float(candidate.get("take_profit_1") or 0.0)
    risk = abs(entry - stop)
    rr1 = abs(tp1 - entry) / risk if risk > 0 else 0.0
    if rr1 >= 1.5:
        base += 0.03
    elif rr1 < 1.0:
        base -= 0.03

    base = max(0.2, min(0.8, base))
    p_tp1 = base
    p_tp2 = max(0.05, min(0.75, base * 0.6))
    p_sl = max(0.2, min(0.8, 1.0 - base))

    source = "heuristic"
    sample_size = 0
    if empirical:
        try:
            weight = float(getattr(empirical, "weight", 1.0))
            p_tp1 = weight * float(getattr(empirical, "p_tp1", p_tp1)) + (1 - weight) * p_tp1
            p_tp2 = weight * float(getattr(empirical, "p_tp2", p_tp2)) + (1 - weight) * p_tp2
            p_sl = weight * float(getattr(empirical, "p_sl", p_sl)) + (1 - weight) * p_sl
            source = getattr(empirical, "source", source)
            sample_size = int(getattr(empirical, "sample_size", 0))
        except Exception:
            pass

    return p_tp1, p_tp2, p_sl, source, sample_size


def _adjust_stop_to_min(cand: Dict, timeframe: str) -> bool:
    entry = float(cand.get("entry") or 0.0)
    stop = float(cand.get("stop_loss") or 0.0)
    if entry <= 0 or stop <= 0:
        return False
    min_stop = MIN_STOP_PCT.get(timeframe, 0.0)
    if min_stop <= 0:
        return False
    stop_dist = abs(entry - stop) / entry
    if stop_dist >= min_stop:
        return False

    direction = (cand.get("type") or "long").lower()
    if direction == "long":
        stop = entry * (1 - min_stop)
        if stop >= entry:
            return False
        risk = entry - stop
        tp1 = entry + risk
        tp2 = entry + 2 * risk
    else:
        stop = entry * (1 + min_stop)
        if stop <= entry:
            return False
        risk = stop - entry
        tp1 = entry - risk
        tp2 = entry - 2 * risk

    cand["stop_loss"] = float(stop)
    cand["take_profit_1"] = float(tp1)
    cand["take_profit_2"] = float(tp2)
    cand["_stop_adjusted"] = True
    reason = (cand.get("reason") or "").strip()
    cand["reason"] = f"{reason} | 调整止损" if reason else "调整止损"
    return True


def _is_valid_trade(cand: Dict, timeframe: str) -> bool:
    entry = float(cand.get("entry") or 0.0)
    stop = float(cand.get("stop_loss") or 0.0)
    tp1 = float(cand.get("take_profit_1") or 0.0)
    tp2_raw = cand.get("take_profit_2")
    tp2 = float(tp2_raw) if tp2_raw not in (None, "") else 0.0
    tp2_present = tp2 > 0
    if entry <= 0 or stop <= 0 or tp1 <= 0:
        return False
    direction = (cand.get("type") or "long").lower()
    if direction == "long":
        if stop >= entry or tp1 <= entry:
            return False
        if tp2_present and tp2 <= tp1:
            return False
    else:
        if stop <= entry or tp1 >= entry:
            return False
        if tp2_present and tp2 >= tp1:
            return False
    if not tp2_present:
        cand["take_profit_2"] = None
    min_stop = MIN_STOP_PCT.get(timeframe, 0.0)
    if min_stop > 0:
        stop_dist = abs(entry - stop) / entry
        if stop_dist < min_stop:
            if not _adjust_stop_to_min(cand, timeframe):
                return False
            entry = float(cand.get("entry") or 0.0)
            stop = float(cand.get("stop_loss") or 0.0)
            tp1 = float(cand.get("take_profit_1") or 0.0)
            tp2_raw = cand.get("take_profit_2")
            tp2 = float(tp2_raw) if tp2_raw not in (None, "") else 0.0
            tp2_present = tp2 > 0
            direction = (cand.get("type") or "long").lower()
            if direction == "long":
                if stop >= entry or tp1 <= entry:
                    return False
                if tp2_present and tp2 <= tp1:
                    return False
            else:
                if stop <= entry or tp1 >= entry:
                    return False
                if tp2_present and tp2 >= tp1:
                    return False
    return True


def _relaxation_notes(rulebook: BestPracticeRulebook, candidate: Dict, features: Dict[str, object], pattern_type: Optional[str]) -> List[str]:
    rules = (rulebook.config or {}).get("rules", {}) if rulebook else {}
    notes: List[str] = []
    direction = (candidate.get("type") or "").lower()
    trend_dir = (features.get("trend_direction") or "").lower()
    trend_strength = float(features.get("trend_strength") or 0.0)
    strong_threshold = float(rules.get("strong_trend_threshold") or 0.0)

    if rules.get("allow_against_trend") and trend_strength >= strong_threshold:
        if (trend_dir == "bullish" and direction == "short") or (trend_dir == "bearish" and direction == "long"):
            notes.append("逆势放宽")

    if not rules.get("require_breakout_confirmation", False):
        ptype = str(pattern_type or "").lower()
        if "breakout" in ptype:
            breakout_up = bool(features.get("breakout_up"))
            breakout_down = bool(features.get("breakout_down"))
            if direction == "long" and not breakout_up:
                notes.append("突破未确认放宽")
            elif direction == "short" and not breakout_down:
                notes.append("突破未确认放宽")

    return notes


def score_with_pattern_library(pattern_library, query_features: Dict) -> Tuple[float, Optional[str], float]:
    if not pattern_library:
        return 0.0, None, 0.0
    try:
        matches = pattern_library.search_patterns(
            query_features=query_features,
            sources=PATTERN_SOURCES,
            top_k=5,
            min_confidence=0.2,
        )
    except Exception:
        return 0.0, None, 0.0
    if not matches:
        return 0.0, None, 0.0
    weight_sum = sum(m.get("weight", 0.0) for m in matches) or 1.0
    score = sum((m.get("similarity", 0.0) * m.get("weight", 0.0)) for m in matches) / weight_sum
    name = (matches[0].get("pattern") or {}).get("pattern_name")
    brooks_score = max((m.get("similarity", 0.0) for m in matches if m.get("source") == "brooks_rule"), default=0.0)
    return score, name, brooks_score


def _trend_summary(features: Dict[str, object]) -> str:
    direction = features.get("trend_direction") or "neutral"
    strength = float(features.get("trend_strength") or 0.0)
    range_mode = bool(features.get("range_mode"))
    if range_mode:
        base = "震荡"
    elif direction == "bullish":
        base = "多头"
    elif direction == "bearish":
        base = "空头"
    else:
        base = "中性"
    if strength >= 0.02:
        level = "强"
    elif strength >= 0.01:
        level = "中"
    else:
        level = "弱"
    return f"{base}({level})"


def main() -> int:
    parser = argparse.ArgumentParser(description="ABU 交易建议问答（CLI）")
    parser.add_argument("--symbol", type=str, default=None)
    parser.add_argument("--timeframe", type=str, default=None, choices=["5m", "15m", "1h"])
    parser.add_argument("--direction", type=str, default=None, choices=["long", "short"])
    parser.add_argument("--question", type=str, default=None)
    parser.add_argument("--days", type=int, default=None)
    args = parser.parse_args()

    sym = args.symbol
    tf = args.timeframe
    direction = args.direction
    if args.question:
        q_sym, q_tf, q_dir = _parse_question(args.question)
        sym = sym or q_sym
        tf = tf or q_tf
        direction = direction or q_dir
    sym = (sym or "").upper()
    tf = (tf or "15m").lower()

    if not sym:
        print("请提供币种，例如 --symbol BTC 或 --question \"BTC 15m 做多机会？\"")
        return 2

    days = args.days if args.days is not None else DEFAULT_DAYS.get(tf, 7)
    limit = min(1000, KLINES_PER_DAY.get(tf, 96) * max(days, 1))

    cache = MarketDataCache(default_exchange="gate")
    kl, _ = cache.get_klines(sym, tf, limit, exchange="gate")
    if not kl or len(kl) < 50:
        print(f"{sym} {tf} K线不足，无法分析")
        return 2

    features = extract_basic_kline_features(kl)
    if not features:
        print(f"{sym} {tf} 特征提取失败")
        return 2

    if tf == "1h":
        candidates = detect_all_1h(kl)
    else:
        candidates = detect_all_15m(kl)

    if direction:
        candidates = [c for c in candidates if (c.get("type") or "").lower() == direction]

    if not candidates:
        print(f"{sym} {tf} 当前未识别到有效形态")
        print(f"- 趋势判断: {_trend_summary(features)}")
        return 0

    k1h, _ = cache.get_klines(sym, "1h", 240, exchange="gate")
    constraints = BrooksPatternConstraints() if USE_BROOKS_RULES else None
    rulebook = BestPracticeRulebook()
    prob_estimator = SignalProbabilityEstimator()

    pattern_library = None
    if PATTERN_LIB_AVAILABLE:
        try:
            pattern_library = UnifiedPatternLibrary("abu")
            pattern_library.load_all_patterns(load_gemini=True, load_cursor_ai=False, load_brooks=False)
        except Exception:
            pattern_library = None

    passed: List[Dict] = []
    filtered_reasons: Dict[str, int] = {}
    for cand in candidates:
        if not _is_valid_trade(cand, tf):
            filtered_reasons["止损/目标不合法"] = filtered_reasons.get("止损/目标不合法", 0) + 1
            continue

        query_features = build_query_features(cand, features)
        pattern_score, best_match, brooks_score = score_with_pattern_library(pattern_library, query_features)
        if not USE_BROOKS_RULES:
            brooks_score = None

        base_pattern = cand.get("pattern") or ""
        pattern_key = best_match or base_pattern
        constraint = ConstraintResult(status="warn", score_adjust=0.0, reasons=["brooks_disabled"], rule_name=None)
        if USE_BROOKS_RULES:
            rule_cfg = (rulebook.config or {}).get("rules", {})
            allowed_status = [str(x).lower() for x in (rule_cfg.get("allowed_brooks_status") or [])]
            allow_brooks_fail = "fail" in allowed_status

            constraint = constraints.evaluate(features, pattern_key, direction=cand.get("type"))
            if constraint.status == "fail" and not allow_brooks_fail:
                filtered_reasons["Brooks约束失败"] = filtered_reasons.get("Brooks约束失败", 0) + 1
                continue
            if constraint.status == "fail" and allow_brooks_fail:
                reason = (cand.get("reason") or "").strip()
                cand["reason"] = f"{reason} | Brooks约束放宽" if reason else "Brooks约束放宽"

        rule_result = rulebook.evaluate(
            cand,
            features,
            pattern_type=query_features.get("pattern_type"),
            pattern_score=pattern_score if pattern_library is not None else None,
            brooks_score=brooks_score,
            brooks_status=constraint.status,
            pattern_match=best_match,
        )
        if not rule_result.passed:
            reason = "最佳实践过滤"
            if rule_result.reasons:
                reason = f"{reason}({';'.join(rule_result.reasons)})"
            filtered_reasons[reason] = filtered_reasons.get(reason, 0) + 1
            continue

        relax_notes = _relaxation_notes(rulebook, cand, features, query_features.get("pattern_type"))
        if relax_notes:
            reason = (cand.get("reason") or "").strip()
            note = " / ".join(relax_notes)
            cand["reason"] = f"{reason} | {note}" if reason else note

        entry_model = f"PA/{base_pattern}" if base_pattern else None
        empirical = prob_estimator.estimate(sym, tf, entry_model=entry_model)
        p_tp1, p_tp2, p_sl, prob_source, prob_samples = estimate_probabilities(
            cand,
            features,
            pattern_score if pattern_library is not None else None,
            brooks_score,
            constraint.status,
            empirical,
        )

        base_score = score_candidate(cand, k1h)
        final_score = base_score + (pattern_score * 0.6) + constraint.score_adjust

        enriched = dict(cand)
        enriched["_score"] = final_score
        enriched["_pattern_score"] = pattern_score
        enriched["_brooks_score"] = brooks_score
        enriched["_brooks_status"] = constraint.status
        enriched["_pattern_match"] = best_match
        enriched["_prob_tp1"] = p_tp1
        enriched["_prob_tp2"] = p_tp2
        enriched["_prob_sl"] = p_sl
        enriched["_prob_source"] = prob_source
        enriched["_prob_samples"] = prob_samples
        passed.append(enriched)

    if not passed:
        print(f"{sym} {tf} 当前没有满足规则的交易建议")
        if filtered_reasons:
            print("- 过滤原因统计:", " | ".join(f"{k}:{v}" for k, v in filtered_reasons.items()))
        print(f"- 趋势判断: {_trend_summary(features)}")
        return 0

    passed.sort(key=lambda x: x.get("_score", 0), reverse=True)
    best = passed[0]
    entry = float(best.get("entry") or 0.0)
    stop = float(best.get("stop_loss") or 0.0)
    tp1 = float(best.get("take_profit_1") or 0.0)
    tp2 = float(best.get("take_profit_2") or 0.0)
    risk = abs(entry - stop)
    rr1 = abs(tp1 - entry) / risk if risk > 0 else 0.0
    prob_tp1 = float(best.get("_prob_tp1") or 0.0) * 100
    prob_tp2 = float(best.get("_prob_tp2") or 0.0) * 100
    prob_sl = float(best.get("_prob_sl") or 0.0) * 100

    print(f"# ABU 交易建议 | {sym} {tf}")
    print(f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"- 趋势判断: {_trend_summary(features)} | 波动={float(features.get('volatility') or 0.0):.2%}")
    print(f"- 形态识别: {best.get('pattern')} | 方向={best.get('type')}")
    if best.get("_pattern_match"):
        print(f"- 模式匹配: {best.get('_pattern_match')} (score={float(best.get('_pattern_score') or 0.0):.2f})")
    print("")
    print("## 参考计划")
    print(f"- 入场: {entry:.4f}")
    print(f"- 止损: {stop:.4f} (止损幅度 {abs(entry - stop) / entry:.2%})")
    print(f"- 目标1: {tp1:.4f} | 目标2: {tp2:.4f}")
    print(f"- RR1: {rr1:.2f}")
    print(f"- 概率估计: P(TP1)={prob_tp1:.1f}% | P(TP2)={prob_tp2:.1f}% | P(SL)={prob_sl:.1f}%")
    print(f"- 概率来源: {best.get('_prob_source')} (样本={best.get('_prob_samples')})")
    if best.get("reason"):
        print(f"- 触发理由: {best.get('reason')}")
    print("")
    print("注: 仅作参考，务必结合自身风控。")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        print(f"运行失败: {exc}")
        sys.exit(1)
