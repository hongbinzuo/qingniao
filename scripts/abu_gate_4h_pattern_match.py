#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 Gate.io 4H K线进行收益率模式匹配与后验验证。
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import requests


GATE_BASE = "https://api.gateio.ws/api/v4/spot/candlesticks"
DEFAULT_TIME_SCORE_MIN = 0.4
DEFAULT_TIME_WINRATE_MIN = 0.65
DEFAULT_TIME_MIN_COUNT = 20
DEFAULT_MTF_INTERVAL = "1d"


def fetch_gate_candles(symbol: str, interval: str, total: int) -> List[Dict]:
    interval_seconds = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }.get(interval)
    if not interval_seconds:
        raise ValueError(f"Unsupported interval: {interval}")

    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    remaining = total
    current_to = now_ts
    candles: List[Dict] = []

    while remaining > 0:
        batch = min(1000, remaining)
        params = {
            "currency_pair": symbol,
            "interval": interval,
            "to": str(current_to),
            "limit": str(batch),
        }
        resp = requests.get(GATE_BASE, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        data.sort(key=lambda x: int(x[0]))
        for row in data:
            ts = int(row[0])
            candles.append(
                {
                    "ts": ts,
                    "open": float(row[5]),
                    "high": float(row[3]),
                    "low": float(row[4]),
                    "close": float(row[2]),
                    "volume": float(row[1]),
                }
            )
        earliest_ts = int(data[0][0])
        current_to = earliest_ts - interval_seconds
        remaining -= batch

    # 去重排序
    unique = {}
    for c in candles:
        unique[c["ts"]] = c
    ordered = [unique[k] for k in sorted(unique.keys())]
    return ordered


def zscore(series: np.ndarray) -> np.ndarray:
    std = np.std(series)
    if std == 0:
        return np.zeros_like(series)
    return (series - np.mean(series)) / std


def pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    if np.std(a) == 0 or np.std(b) == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def dtw_distance(a: np.ndarray, b: np.ndarray, band: Optional[int] = None) -> float:
    n = len(a)
    m = len(b)
    if band is None:
        band = max(5, int(0.2 * max(n, m)))
    band = max(band, abs(n - m))

    inf = float("inf")
    dtw = np.full((n + 1, m + 1), inf, dtype=float)
    dtw[0, 0] = 0.0

    for i in range(1, n + 1):
        j_start = max(1, i - band)
        j_end = min(m, i + band)
        for j in range(j_start, j_end + 1):
            cost = abs(a[i - 1] - b[j - 1])
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])

    return dtw[n, m] / (n + m)


def segment_corr(a: np.ndarray, b: np.ndarray, segments: int = 3) -> float:
    n = len(a)
    seg_len = n // segments
    if seg_len == 0:
        return 0.0
    scores = []
    for i in range(segments):
        start = i * seg_len
        end = n if i == segments - 1 else (i + 1) * seg_len
        scores.append(pearson_corr(a[start:end], b[start:end]))
    return float(np.mean(scores)) if scores else 0.0


def slope_similarity(a: np.ndarray, b: np.ndarray, segments: int = 3) -> float:
    def slopes(x: np.ndarray) -> List[float]:
        n = len(x)
        seg_len = n // segments
        if seg_len == 0:
            return []
        out = []
        for i in range(segments):
            start = i * seg_len
            end = n if i == segments - 1 else (i + 1) * seg_len
            seg = x[start:end]
            if len(seg) < 2:
                out.append(0.0)
                continue
            out.append((seg[-1] - seg[0]) / (len(seg) - 1))
        return out

    cum_a = np.cumsum(a)
    cum_b = np.cumsum(b)
    sa = slopes(cum_a)
    sb = slopes(cum_b)
    if not sa or not sb:
        return 0.0
    sims = []
    for va, vb in zip(sa, sb):
        denom = max(abs(va), abs(vb), 1e-8)
        sims.append(1.0 - min(1.0, abs(va - vb) / denom))
    return float(np.mean(sims))


def volatility_score(a: np.ndarray, b: np.ndarray) -> float:
    va = float(np.std(a))
    vb = float(np.std(b))
    denom = max(va, vb, 1e-8)
    return 1.0 - min(1.0, abs(va - vb) / denom)


def structure_similarity(target: np.ndarray, window: np.ndarray, segments: int = 3) -> float:
    n = len(target)
    seg_len = n // segments
    if seg_len == 0:
        return 0.0

    def segment_metrics(arr: np.ndarray) -> List[Tuple[float, float]]:
        metrics = []
        for i in range(segments):
            start = i * seg_len
            end = n if i == segments - 1 else (i + 1) * seg_len
            seg = arr[start:end]
            if len(seg) == 0:
                metrics.append((0.0, 0.0))
                continue
            up_ratio = float(np.mean(seg > 0))
            denom = float(np.sum(np.abs(seg))) + 1e-8
            sum_norm = float(np.sum(seg) / denom)
            metrics.append((up_ratio, sum_norm))
        return metrics

    t_metrics = segment_metrics(target)
    w_metrics = segment_metrics(window)
    diffs = []
    for (tu, ts), (wu, ws) in zip(t_metrics, w_metrics):
        diffs.append(abs(tu - wu))
        diffs.append(abs(ts - ws))
    if not diffs:
        return 0.0
    return float(1.0 - min(1.0, float(np.mean(diffs))))


def composite_score(
    target: np.ndarray,
    window: np.ndarray,
    structure_weight: float = 0.0,
) -> Tuple[float, Dict[str, float]]:
    target_z = zscore(target)
    window_z = zscore(window)

    corr = pearson_corr(target_z, window_z)
    seg = segment_corr(target_z, window_z)
    slope = slope_similarity(target_z, window_z)
    vol = volatility_score(target, window)
    dtw = dtw_distance(target_z, window_z)
    dtw_sim = 1.0 / (1.0 + dtw)

    structure_sim = structure_similarity(target_z, window_z) if structure_weight > 0 else 0.0

    base_weight = 1.0 - structure_weight
    score = (
        base_weight * 0.4 * corr
        + base_weight * 0.2 * seg
        + base_weight * 0.15 * slope
        + base_weight * 0.15 * vol
        + base_weight * 0.1 * dtw_sim
        + structure_weight * structure_sim
    )
    details = {
        "corr": corr,
        "seg_corr": seg,
        "slope_sim": slope,
        "vol_score": vol,
        "dtw": dtw,
        "dtw_sim": dtw_sim,
        "structure_sim": structure_sim,
    }
    return score, details


def log_returns(prices: np.ndarray) -> np.ndarray:
    return np.diff(np.log(prices))


def bucketize(values: np.ndarray, quantiles: Tuple[float, float] = (0.33, 0.66)) -> List[int]:
    q1, q2 = np.quantile(values, quantiles)
    buckets = []
    for v in values:
        if v <= q1:
            buckets.append(0)
        elif v <= q2:
            buckets.append(1)
        else:
            buckets.append(2)
    return buckets


def interval_to_hours(interval: str) -> Optional[int]:
    mapping = {
        "1m": 1 / 60,
        "5m": 5 / 60,
        "15m": 15 / 60,
        "1h": 1,
        "4h": 4,
        "1d": 24,
    }
    return mapping.get(interval)


def trend_slope(log_prices: np.ndarray) -> float:
    x = np.arange(len(log_prices), dtype=float)
    if len(log_prices) < 2:
        return 0.0
    slope = np.polyfit(x, log_prices, 1)[0]
    return float(slope)


def scan_breakout_events(
    returns: np.ndarray,
    closes: np.ndarray,
    lookback: int = 20,
    k: float = 2.0,
) -> Tuple[Optional[Tuple[str, int, float, float]], Optional[Tuple[str, int, float, float]]]:
    first_event = None
    last_event = None
    for i in range(lookback, len(returns)):
        window = returns[i - lookback:i]
        std = float(np.std(window))
        if std == 0:
            continue
        current_close = closes[i + 1]
        prev_closes = closes[i - lookback + 1:i + 1]
        prev_high = float(np.max(prev_closes))
        prev_low = float(np.min(prev_closes))
        if returns[i] > k * std and current_close >= prev_high:
            event = ("up_breakout", i, prev_high, prev_low)
        elif returns[i] < -k * std and current_close <= prev_low:
            event = ("down_breakout", i, prev_high, prev_low)
        else:
            continue
        if first_event is None:
            first_event = event
        last_event = event
    return first_event, last_event


def detect_event(returns: np.ndarray, closes: np.ndarray, lookback: int = 20, k: float = 2.0) -> str:
    first_event, _ = scan_breakout_events(returns, closes, lookback=lookback, k=k)
    return first_event[0] if first_event else "none"


def detect_latest_event_index(
    returns: np.ndarray,
    closes: np.ndarray,
    lookback: int = 20,
    k: float = 2.0,
) -> Tuple[str, Optional[int]]:
    _, last_event = scan_breakout_events(returns, closes, lookback=lookback, k=k)
    if not last_event:
        return "none", None
    return last_event[0], last_event[1]


def detect_latest_event_details(
    returns: np.ndarray,
    closes: np.ndarray,
    lookback: int = 20,
    k: float = 2.0,
) -> Tuple[str, Optional[int], Optional[float], Optional[float]]:
    _, last_event = scan_breakout_events(returns, closes, lookback=lookback, k=k)
    if not last_event:
        return "none", None, None, None
    return last_event


def latest_event(returns: np.ndarray, closes: np.ndarray, lookback: int = 20, k: float = 2.0) -> Tuple[str, float, float]:
    if len(returns) < lookback or len(closes) < lookback + 1:
        return "none", float("nan"), float("nan")
    window = returns[-lookback:]
    std = float(np.std(window))
    if std == 0:
        return "none", float("nan"), float("nan")
    current_return = returns[-1]
    prev_closes = closes[-lookback - 1:-1]
    prev_high = float(np.max(prev_closes))
    prev_low = float(np.min(prev_closes))
    current_close = float(closes[-1])
    if current_return > k * std and current_close >= prev_high:
        return "up_breakout", prev_high, prev_low
    if current_return < -k * std and current_close <= prev_low:
        return "down_breakout", prev_high, prev_low
    return "none", prev_high, prev_low


def build_trade_plan(
    candles: List[Dict],
    window: int,
    lookback: int,
    swing: int,
    tp1_rr: float,
    tp2_rr: float,
) -> Dict[str, object]:
    closes = np.array([c["close"] for c in candles], dtype=float)
    highs = np.array([c["high"] for c in candles], dtype=float)
    lows = np.array([c["low"] for c in candles], dtype=float)
    returns = log_returns(closes)

    event_type, prev_high, prev_low = latest_event(returns, closes, lookback=lookback)
    window_prices = closes[-(window + 1):]
    slope = trend_slope(np.log(window_prices + 1e-8))

    direction = "none"
    if event_type == "up_breakout" and slope > 0:
        direction = "long"
    elif event_type == "down_breakout" and slope < 0:
        direction = "short"

    entry = float(closes[-1])
    if direction == "long":
        stop = float(np.min(lows[-swing:]))
    elif direction == "short":
        stop = float(np.max(highs[-swing:]))
    else:
        stop = float("nan")

    risk = abs(entry - stop) if direction in ("long", "short") else float("nan")
    if direction == "long":
        tp1 = entry + tp1_rr * risk
        tp2 = entry + tp2_rr * risk
        entry_condition = f"4h close above {prev_high:.2f}"
    elif direction == "short":
        tp1 = entry - tp1_rr * risk
        tp2 = entry - tp2_rr * risk
        entry_condition = f"4h close below {prev_low:.2f}"
    else:
        tp1 = float("nan")
        tp2 = float("nan")
        entry_condition = "no valid breakout event"

    status = "ready" if direction in ("long", "short") else "standby"
    return {
        "status": status,
        "timeframe": "4h",
        "direction": direction,
        "entry_condition": entry_condition,
        "entry_price": entry,
        "stop_loss": stop,
        "take_profit_1": tp1,
        "take_profit_2": tp2,
        "risk_reward_ratio": tp2_rr if direction in ("long", "short") else float("nan"),
        "signal_origin": "event_regime_match",
        "trend_slope": slope,
        "event_type": event_type,
        "as_of_ts": candles[-1]["ts"],
    }


def build_time_hold_plan(
    candles: List[Dict],
    interval: str,
    future: int,
    best_score: Optional[float],
    summary: Dict[str, float],
    score_min: float,
    winrate_min: float,
    min_count: int,
    slope_sign: int,
    mtf_gate: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    entry_price = float(candles[-1]["close"])
    best_score_value = float(best_score) if best_score is not None else None
    hold_hours = None
    interval_hours = interval_to_hours(interval)
    if interval_hours is not None:
        hold_hours = interval_hours * future

    status = "standby"
    reason = []
    if slope_sign != 1:
        reason.append("trend_slope_non_positive")
    if best_score_value is None or best_score_value < score_min:
        reason.append("score_below_threshold")
    if summary.get("win_rate", 0.0) < winrate_min:
        reason.append("win_rate_below_threshold")
    if summary.get("count", 0) < min_count:
        reason.append("insufficient_samples")

    if mtf_gate:
        mtf_reasons = mtf_gate.get("reasons") or []
        if mtf_gate.get("status") != "ready":
            reason.extend(mtf_reasons if mtf_reasons else ["mtf_not_ready"])

    if not reason:
        status = "ready"

    stat_stop = None
    if "p25" in summary and summary["p25"] < 0:
        stat_stop = entry_price * (1.0 + summary["p25"])

    return {
        "status": status,
        "direction": "long",
        "entry_price": entry_price,
        "hold_candles": future,
        "hold_hours": hold_hours,
        "score_threshold": score_min,
        "win_rate_threshold": winrate_min,
        "sample_threshold": min_count,
        "best_score": best_score_value,
        "summary": summary,
        "stat_stop": stat_stop,
        "reasons": reason,
        "mtf_gate": mtf_gate,
        "as_of_ts": candles[-1]["ts"],
    }


def derive_mtf_settings(
    base_interval: str,
    mtf_interval: str,
    window: int,
    future: int,
    lookback: int,
) -> Optional[Dict[str, int]]:
    base_hours = interval_to_hours(base_interval)
    mtf_hours = interval_to_hours(mtf_interval)
    if not base_hours or not mtf_hours or mtf_hours <= base_hours:
        return None
    factor = mtf_hours / base_hours
    return {
        "window": max(20, int(round(window / factor))),
        "future": max(1, int(round(future / factor))),
        "lookback": max(10, int(round(lookback / factor))),
        "factor": factor,
    }


def build_mtf_gate(
    symbol: str,
    base_interval: str,
    mtf_interval: str,
    window: int,
    future: int,
    lookback: int,
    total: int,
) -> Optional[Dict[str, object]]:
    settings = derive_mtf_settings(base_interval, mtf_interval, window, future, lookback)
    if not settings:
        return None

    mtf_total = max(settings["window"] + settings["future"] + 10, int(round(total / settings["factor"])) + 10)
    candles = fetch_gate_candles(symbol, mtf_interval, mtf_total)
    if len(candles) <= settings["window"] + settings["future"] + 10:
        return {
            "status": "standby",
            "interval": mtf_interval,
            "window": settings["window"],
            "future": settings["future"],
            "lookback": settings["lookback"],
            "event_type": "none",
            "trend_slope": float("nan"),
            "trend_slope_sign": 0,
            "reasons": ["mtf_insufficient_candles"],
            "as_of_ts": candles[-1]["ts"] if candles else None,
        }

    closes = np.array([c["close"] for c in candles], dtype=float)
    returns = log_returns(closes)
    window_closes = closes[-(settings["window"] + 1):]
    target_returns = returns[-settings["window"]:]
    event_type = detect_event(target_returns, window_closes, lookback=settings["lookback"])
    slope = trend_slope(np.log(window_closes + 1e-8))
    slope_sign = 0 if abs(slope) < 1e-8 else (1 if slope > 0 else -1)

    reasons = []
    if slope_sign != 1:
        reasons.append("mtf_trend_slope_non_positive")
    if event_type == "down_breakout":
        reasons.append("mtf_down_breakout")

    status = "ready" if not reasons else "standby"
    return {
        "status": status,
        "interval": mtf_interval,
        "window": settings["window"],
        "future": settings["future"],
        "lookback": settings["lookback"],
        "event_type": event_type,
        "trend_slope": slope,
        "trend_slope_sign": slope_sign,
        "reasons": reasons,
        "as_of_ts": candles[-1]["ts"],
    }


def format_time_hold_plan_cn(plan: Dict[str, object]) -> str:
    def fmt(value: Optional[float], digits: int = 4) -> str:
        if value is None:
            return "N/A"
        try:
            if np.isnan(value):
                return "N/A"
        except TypeError:
            pass
        return f"{value:.{digits}f}"

    reason_map = {
        "trend_slope_non_positive": "4h趋势非正",
        "score_below_threshold": "匹配分数不足",
        "win_rate_below_threshold": "胜率不足",
        "insufficient_samples": "样本数不足",
        "mtf_trend_slope_non_positive": "1d趋势非正",
        "mtf_down_breakout": "1d出现向下突破",
        "mtf_insufficient_candles": "1d数据不足",
        "mtf_not_ready": "1d过滤未通过",
    }

    summary = plan.get("summary") or {}
    reasons = plan.get("reasons") or []
    reason_text = "；".join(reason_map.get(r, r) for r in reasons) if reasons else "无"

    hold_hours = plan.get("hold_hours")
    hold_hours_text = f"{hold_hours:.1f}小时" if isinstance(hold_hours, (int, float)) else "N/A"

    lines = [
        "时间持有计划（中文）",
        f"- 状态: {plan.get('status')}（{('可执行' if plan.get('status') == 'ready' else '待观察')}）",
        f"- 方向: {plan.get('direction')}",
        f"- 入场价: {fmt(plan.get('entry_price'), 2)}",
        f"- 持有周期: {plan.get('hold_candles')} 根 / {hold_hours_text}",
        f"- 统计止损参考: {fmt(plan.get('stat_stop'), 2)}",
        f"- 最佳匹配分: {fmt(plan.get('best_score'))}",
        f"- 阈值: score≥{fmt(plan.get('score_threshold'))}, win_rate≥{fmt(plan.get('win_rate_threshold'))}, samples≥{plan.get('sample_threshold')}",
        (
            "- 统计摘要: "
            f"样本数{summary.get('count', 0)}，胜率{fmt(summary.get('win_rate'))}，"
            f"均值{fmt(summary.get('mean'))}，中位数{fmt(summary.get('median'))}，"
            f"p25={fmt(summary.get('p25'))}，p75={fmt(summary.get('p75'))}"
        ),
        f"- 未达标原因: {reason_text}",
    ]

    mtf_gate = plan.get("mtf_gate") or {}
    if mtf_gate:
        mtf_reasons = mtf_gate.get("reasons") or []
        mtf_reason_text = "；".join(reason_map.get(r, r) for r in mtf_reasons) if mtf_reasons else "无"
        lines.extend(
            [
                f"- 多周期过滤: {mtf_gate.get('interval')} / {mtf_gate.get('status')}",
                f"- 1d事件: {mtf_gate.get('event_type')}，1d趋势斜率: {fmt(mtf_gate.get('trend_slope'))}",
                f"- 1d过滤原因: {mtf_reason_text}",
            ]
        )

    return "\n".join(lines)


def evaluate_trade_outcome(
    highs: np.ndarray,
    lows: np.ndarray,
    entry_idx: int,
    horizon_end: int,
    stop_price: float,
    tp1: float,
    tp2: float,
) -> str:
    for j in range(entry_idx + 1, horizon_end + 1):
        if lows[j] <= stop_price:
            return "stop"
        if highs[j] >= tp2:
            return "tp2"
        if highs[j] >= tp1:
            return "tp1"
    return "stop"


def record_outcome(outcomes: Dict[str, int], returns_list: List[float], outcome: str, tp1_rr: float, tp2_rr: float) -> None:
    outcomes[outcome] += 1
    if outcome == "tp2":
        returns_list.append(tp2_rr)
    elif outcome == "tp1":
        returns_list.append(tp1_rr)
    else:
        returns_list.append(-1.0)


def backtest_long_breakouts(
    candles: List[Dict],
    returns: np.ndarray,
    window: int,
    future: int,
    lookback: int,
    swing: int,
    tp1_rr: float,
    tp2_rr: float,
    vol_buckets: List[int],
    volm_buckets: List[int],
    slope_buckets: List[int],
    slope_sign_list: List[int],
    target_vol_bucket: int,
    target_volm_bucket: int,
    target_slope_bucket: int,
    target_slope_sign: int,
) -> Dict[str, float]:
    closes = np.array([c["close"] for c in candles], dtype=float)
    highs = np.array([c["high"] for c in candles], dtype=float)
    lows = np.array([c["low"] for c in candles], dtype=float)

    total_windows = len(returns) - window - future
    outcomes = {"tp2": 0, "tp1": 0, "stop": 0}
    returns_list = []
    seen_entries = set()
    duplicates = 0

    for i in range(total_windows):
        if vol_buckets[i] != target_vol_bucket:
            continue
        if volm_buckets[i] != target_volm_bucket:
            continue
        if slope_buckets[i] != target_slope_bucket:
            continue
        if slope_sign_list[i] != target_slope_sign:
            continue

        window_returns = returns[i : i + window]
        window_closes = closes[i : i + window + 1]
        event_type, event_idx = detect_latest_event_index(window_returns, window_closes, lookback=lookback)
        if event_type != "up_breakout" or event_idx is None:
            continue

        entry_idx = i + event_idx + 1  # index in closes
        if entry_idx in seen_entries:
            duplicates += 1
            continue
        seen_entries.add(entry_idx)
        entry_price = float(closes[entry_idx])

        stop_start = max(entry_idx - swing + 1, 0)
        stop_price = float(np.min(lows[stop_start:entry_idx + 1]))
        risk = entry_price - stop_price
        if risk <= 0:
            continue

        tp1 = entry_price + tp1_rr * risk
        tp2 = entry_price + tp2_rr * risk

        horizon_end = min(entry_idx + future, len(closes) - 1)
        outcome = evaluate_trade_outcome(highs, lows, entry_idx, horizon_end, stop_price, tp1, tp2)
        record_outcome(outcomes, returns_list, outcome, tp1_rr, tp2_rr)

    total = sum(outcomes.values())
    if total == 0:
        return {"count": 0, "duplicates_skipped": duplicates}

    avg_r = float(np.mean(returns_list))
    return {
        "count": total,
        "duplicates_skipped": duplicates,
        "tp1_win_rate": round((outcomes["tp1"] + outcomes["tp2"]) / total, 4),
        "tp2_win_rate": round(outcomes["tp2"] / total, 4),
        "stop_rate": round(outcomes["stop"] / total, 4),
        "avg_r_multiple": round(avg_r, 4),
    }


def backtest_long_pullback(
    candles: List[Dict],
    returns: np.ndarray,
    window: int,
    future: int,
    lookback: int,
    tp1_rr: float,
    tp2_rr: float,
    pullback_lookahead: int,
    pullback_tolerance: float,
    pullback_max_drop: float,
    vol_buckets: List[int],
    volm_buckets: List[int],
    slope_buckets: List[int],
    slope_sign_list: List[int],
    target_vol_bucket: int,
    target_volm_bucket: int,
    target_slope_bucket: int,
    target_slope_sign: int,
) -> Dict[str, float]:
    closes = np.array([c["close"] for c in candles], dtype=float)
    highs = np.array([c["high"] for c in candles], dtype=float)
    lows = np.array([c["low"] for c in candles], dtype=float)

    total_windows = len(returns) - window - future
    outcomes = {"tp2": 0, "tp1": 0, "stop": 0}
    returns_list = []
    seen_entries = set()
    duplicates = 0

    for i in range(total_windows):
        if vol_buckets[i] != target_vol_bucket:
            continue
        if volm_buckets[i] != target_volm_bucket:
            continue
        if slope_buckets[i] != target_slope_bucket:
            continue
        if slope_sign_list[i] != target_slope_sign:
            continue

        window_returns = returns[i : i + window]
        window_closes = closes[i : i + window + 1]
        event_type, event_idx, prev_high, _ = detect_latest_event_details(
            window_returns,
            window_closes,
            lookback=lookback,
        )
        if event_type != "up_breakout" or event_idx is None or prev_high is None:
            continue

        breakout_idx = i + event_idx + 1
        search_end = min(breakout_idx + pullback_lookahead, len(closes) - 1)
        if breakout_idx >= search_end:
            continue

        low_bound = prev_high * (1.0 - pullback_max_drop)
        high_bound = prev_high * (1.0 + pullback_tolerance)
        entry_idx = None
        for j in range(breakout_idx + 1, search_end + 1):
            if lows[j] < low_bound:
                break
            if lows[j] <= high_bound and closes[j] >= prev_high:
                entry_idx = j
                break

        if entry_idx is None:
            continue
        if entry_idx in seen_entries:
            duplicates += 1
            continue
        seen_entries.add(entry_idx)

        entry_price = float(closes[entry_idx])
        stop_price = float(np.min(lows[breakout_idx : entry_idx + 1]))
        risk = entry_price - stop_price
        if risk <= 0:
            continue

        tp1 = entry_price + tp1_rr * risk
        tp2 = entry_price + tp2_rr * risk

        horizon_end = min(entry_idx + future, len(closes) - 1)
        outcome = evaluate_trade_outcome(highs, lows, entry_idx, horizon_end, stop_price, tp1, tp2)
        record_outcome(outcomes, returns_list, outcome, tp1_rr, tp2_rr)

    total = sum(outcomes.values())
    if total == 0:
        return {"count": 0, "duplicates_skipped": duplicates}

    avg_r = float(np.mean(returns_list))
    return {
        "count": total,
        "duplicates_skipped": duplicates,
        "tp1_win_rate": round((outcomes["tp1"] + outcomes["tp2"]) / total, 4),
        "tp2_win_rate": round(outcomes["tp2"] / total, 4),
        "stop_rate": round(outcomes["stop"] / total, 4),
        "avg_r_multiple": round(avg_r, 4),
    }


def summarize_future(future_returns: List[float]) -> Dict[str, float]:
    arr = np.array(future_returns, dtype=float)
    if len(arr) == 0:
        return {"count": 0, "win_rate": 0.0, "mean": 0.0, "median": 0.0}
    win_rate = float(np.mean(arr > 0))
    return {
        "count": int(len(arr)),
        "win_rate": round(win_rate, 4),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p25": float(np.percentile(arr, 25)),
        "p75": float(np.percentile(arr, 75)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate 4H pattern match with post-validation")
    parser.add_argument("--symbol", default="ETH_USDT", help="Gate currency pair")
    parser.add_argument("--interval", default="4h", help="Interval (default 4h)")
    parser.add_argument("--total", type=int, default=2000, help="Total candles to fetch")
    parser.add_argument("--window", type=int, default=180, help="Match window length")
    parser.add_argument("--future", type=int, default=24, help="Future candles for validation")
    parser.add_argument("--topk", type=int, default=20, help="Top matches for validation")
    parser.add_argument("--mode", choices=["baseline", "regime", "event", "event_regime"], default="event_regime",
                        help="baseline/regime/event")
    parser.add_argument("--plan", action="store_true", help="Print trade plan for latest window")
    parser.add_argument("--plan-lookback", type=int, default=20, help="Breakout lookback")
    parser.add_argument("--plan-swing", type=int, default=12, help="Swing window for stop-loss")
    parser.add_argument("--plan-tp1", type=float, default=1.5, help="TP1 risk multiple")
    parser.add_argument("--plan-tp2", type=float, default=3.0, help="TP2 risk multiple")
    parser.add_argument("--time-hold-plan", action="store_true", help="Print time-hold long plan")
    parser.add_argument("--time-score-min", type=float, default=DEFAULT_TIME_SCORE_MIN, help="Min score for time-hold plan")
    parser.add_argument("--time-winrate-min", type=float, default=DEFAULT_TIME_WINRATE_MIN, help="Min win-rate for time-hold plan")
    parser.add_argument("--time-min-count", type=int, default=DEFAULT_TIME_MIN_COUNT, help="Min samples for time-hold plan")
    parser.add_argument("--time-hold-mtf", dest="time_hold_mtf", action="store_true", help="Enable 4h+1d filter")
    parser.add_argument("--no-time-hold-mtf", dest="time_hold_mtf", action="store_false", help="Disable 4h+1d filter")
    parser.set_defaults(time_hold_mtf=True)
    parser.add_argument("--mtf-interval", default=DEFAULT_MTF_INTERVAL, help="Higher timeframe interval (default 1d)")
    parser.add_argument("--long-backtest", action="store_true", help="Backtest long breakouts only")
    parser.add_argument(
        "--long-backtest-mode",
        choices=["breakout", "pullback"],
        default="breakout",
        help="Long entry style for backtest",
    )
    parser.add_argument("--bt-lookback", type=int, default=20, help="Backtest breakout lookback")
    parser.add_argument("--bt-swing", type=int, default=12, help="Backtest stop-loss swing window")
    parser.add_argument("--bt-tp1", type=float, default=1.5, help="Backtest TP1 risk multiple")
    parser.add_argument("--bt-tp2", type=float, default=3.0, help="Backtest TP2 risk multiple")
    parser.add_argument("--bt-pullback-lookahead", type=int, default=12, help="Pullback max wait candles")
    parser.add_argument("--bt-pullback-tol", type=float, default=0.003, help="Pullback tolerance above level")
    parser.add_argument("--bt-pullback-maxdrop", type=float, default=0.03, help="Pullback max drop below level")
    args = parser.parse_args()

    candles = fetch_gate_candles(args.symbol, args.interval, args.total)
    if len(candles) <= args.window + args.future + 10:
        print("Not enough candles fetched.")
        return 1

    closes = np.array([c["close"] for c in candles], dtype=float)
    volumes = np.array([c["volume"] for c in candles], dtype=float)
    returns = log_returns(closes)

    window = args.window
    future = args.future
    target = returns[-window:]

    # 预计算窗口指标
    total_windows = len(returns) - window - future
    vol_list = []
    volm_list = []
    slope_list = []
    slope_sign_list = []
    for i in range(total_windows):
        win_returns = returns[i : i + window]
        win_vol = float(np.std(win_returns))
        vol_list.append(win_vol)
        win_volm = float(np.mean(volumes[i + 1:i + window + 1]))
        volm_list.append(win_volm)
        win_prices = closes[i : i + window + 1]
        slope = trend_slope(np.log(win_prices + 1e-8))
        slope_list.append(abs(slope))
        slope_sign_list.append(0 if abs(slope) < 1e-8 else (1 if slope > 0 else -1))

    vol_buckets = bucketize(np.array(vol_list))
    volm_buckets = bucketize(np.array(volm_list))
    slope_buckets = bucketize(np.array(slope_list))

    target_vol_bucket = vol_buckets[-1]
    target_volm_bucket = volm_buckets[-1]
    target_slope_bucket = slope_buckets[-1]
    target_slope_sign = slope_sign_list[-1]

    target_event = "none"
    if args.mode in ("event", "event_regime"):
        target_event = detect_event(target, closes[-(window + 1):])

    results = []
    filtered = 0
    for i in range(total_windows):
        if args.mode in ("regime", "event_regime"):
            if vol_buckets[i] != target_vol_bucket:
                continue
            if volm_buckets[i] != target_volm_bucket:
                continue
            if slope_buckets[i] != target_slope_bucket:
                continue
            if slope_sign_list[i] != target_slope_sign:
                continue
        if args.mode in ("event", "event_regime"):
            event_type = detect_event(returns[i : i + window], closes[i : i + window + 1])
            if event_type != target_event:
                continue

        filtered += 1
        hist_window = returns[i : i + window]
        structure_weight = 0.1 if args.mode in ("event", "event_regime") else 0.0
        score, details = composite_score(target, hist_window, structure_weight=structure_weight)
        start_ts = candles[i + 1]["ts"]  # returns index aligns to closes[1:]
        end_ts = candles[i + window]["ts"]
        results.append(
            {
                "index": i,
                "score": score,
                "start_ts": start_ts,
                "end_ts": end_ts,
                **details,
            }
        )

    print(f"Mode: {args.mode}, candidate windows: {filtered}")
    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[: args.topk]

    future_returns = []
    for item in top:
        idx = item["index"]
        fut = returns[idx + window : idx + window + future]
        cum = float(np.exp(np.sum(fut)) - 1.0)
        item["future_return"] = cum
        future_returns.append(cum)

    summary = summarize_future(future_returns)

    best = top[0] if top else None
    if best:
        start_dt = datetime.fromtimestamp(best["start_ts"], tz=timezone.utc)
        end_dt = datetime.fromtimestamp(best["end_ts"], tz=timezone.utc)
        print(f"Best score: {best['score']:.4f}")
        print(f"Best match window: {start_dt} -> {end_dt}")
        print(f"Best metrics: corr={best['corr']:.3f}, seg={best['seg_corr']:.3f}, slope={best['slope_sim']:.3f}, vol={best['vol_score']:.3f}, dtw={best['dtw']:.3f}")

    if top:
        print(f"Top {len(top)} match windows:")
        for idx, item in enumerate(top, start=1):
            start_dt = datetime.fromtimestamp(item["start_ts"], tz=timezone.utc)
            end_dt = datetime.fromtimestamp(item["end_ts"], tz=timezone.utc)
            print(f"{idx:02d}. {start_dt} -> {end_dt} score={item['score']:.4f} future={item['future_return']:.4f}")

    print(f"Post validation (top {len(top)} matches, future {future} candles):")
    print(summary)

    if args.plan:
        plan = build_trade_plan(
            candles,
            window=window,
            lookback=args.plan_lookback,
            swing=args.plan_swing,
            tp1_rr=args.plan_tp1,
            tp2_rr=args.plan_tp2,
        )
        print("Trade plan:")
        print(plan)

    if args.time_hold_plan:
        best_score = top[0]["score"] if top else None
        mtf_gate = None
        if args.time_hold_mtf:
            mtf_gate = build_mtf_gate(
                symbol=args.symbol,
                base_interval=args.interval,
                mtf_interval=args.mtf_interval,
                window=window,
                future=future,
                lookback=args.plan_lookback,
                total=args.total,
            )
        plan = build_time_hold_plan(
            candles=candles,
            interval=args.interval,
            future=future,
            best_score=best_score,
            summary=summary,
            score_min=args.time_score_min,
            winrate_min=args.time_winrate_min,
            min_count=args.time_min_count,
            slope_sign=target_slope_sign,
            mtf_gate=mtf_gate,
        )
        print("Time-hold plan:")
        print(plan)
        print(format_time_hold_plan_cn(plan))

    if args.long_backtest:
        if args.long_backtest_mode == "pullback":
            stats = backtest_long_pullback(
                candles=candles,
                returns=returns,
                window=window,
                future=future,
                lookback=args.bt_lookback,
                tp1_rr=args.bt_tp1,
                tp2_rr=args.bt_tp2,
                pullback_lookahead=args.bt_pullback_lookahead,
                pullback_tolerance=args.bt_pullback_tol,
                pullback_max_drop=args.bt_pullback_maxdrop,
                vol_buckets=vol_buckets,
                volm_buckets=volm_buckets,
                slope_buckets=slope_buckets,
                slope_sign_list=slope_sign_list,
                target_vol_bucket=target_vol_bucket,
                target_volm_bucket=target_volm_bucket,
                target_slope_bucket=target_slope_bucket,
                target_slope_sign=target_slope_sign,
            )
            print("Long pullback backtest (event_regime filtered):")
        else:
            stats = backtest_long_breakouts(
                candles=candles,
                returns=returns,
                window=window,
                future=future,
                lookback=args.bt_lookback,
                swing=args.bt_swing,
                tp1_rr=args.bt_tp1,
                tp2_rr=args.bt_tp2,
                vol_buckets=vol_buckets,
                volm_buckets=volm_buckets,
                slope_buckets=slope_buckets,
                slope_sign_list=slope_sign_list,
                target_vol_bucket=target_vol_bucket,
                target_volm_bucket=target_volm_bucket,
                target_slope_bucket=target_slope_bucket,
                target_slope_sign=target_slope_sign,
            )
            print("Long breakout backtest (event_regime filtered):")
        print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
