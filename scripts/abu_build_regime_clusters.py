#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build 36-class regime clusters from 1h market samples."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import numpy as np
except Exception:
    np = None

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.kline_feature_extractor import extract_basic_kline_features  # type: ignore
from abu.market_cache import MarketDataCache, TIMEFRAME_SECONDS  # type: ignore
from abu.market_context import _calculate_overlap_ratio, _classify_regime_36  # type: ignore
from abu.regime_cluster_model import FEATURE_NAMES, build_feature_vector  # type: ignore

FIXED_MARKETCAP = [
    "BTC", "ETH", "SOL", "BNB", "XRP", "TRX", "DOGE", "BCH", "ADA", "XLM",
    "LINK", "ZEC", "SUI", "HBAR", "AVAX", "LTC", "SHIB", "WLFI", "UNI",
    "TON", "DOT", "TAO", "TRUMP", "AAVE", "WLD", "PEPE", "NEAR", "ICP", "ETC",
    "ONDO", "ASTER", "FIL", "SKY", "ARB", "PUMP", "ENA", "POL", "OP",
    "APT", "ATOM", "ZRO", "RENDER", "ALGO", "QNT", "ENS", "VET", "DASH",
    "VIRTUAL", "BONK", "AXS", "SEI", "PENGU", "MORPHO", "CAKE", "FET", "XTZ",
    "JUP", "CRV", "NEXO", "PENDLE", "RAY", "STX", "LDO", "CHZ"
]


def _parse_symbols_file(path: Path) -> List[str]:
    symbols = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        symbols.append(text.upper())
    return symbols


def _std(values: List[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def _compute_symbol_stats(klines: List[Dict]) -> Dict[str, float]:
    closes = [float(k.get("close") or 0.0) for k in klines]
    volumes = [float(k.get("volume") or 0.0) for k in klines]
    returns = []
    for i in range(1, len(closes)):
        if closes[i - 1] <= 0:
            continue
        returns.append((closes[i] / closes[i - 1]) - 1.0)
    return {
        "avg_volume": sum(volumes) / len(volumes) if volumes else 0.0,
        "volatility": _std(returns),
    }


def _tertile_thresholds(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    values_sorted = sorted(values)
    n = len(values_sorted)
    low_idx = max(0, int(n * 0.33) - 1)
    high_idx = max(low_idx, int(n * 0.66) - 1)
    return values_sorted[low_idx], values_sorted[high_idx]


def _assign_tier(value: float, low_cut: float, high_cut: float) -> str:
    if value <= low_cut:
        return "low"
    if value >= high_cut:
        return "high"
    return "mid"


def _balanced_sample(bins: Dict[Tuple[str, ...], List[str]], total: int, seed: int) -> List[str]:
    if total <= 0 or not bins:
        return []
    rng = random.Random(seed)
    items = [(key, list(vals)) for key, vals in bins.items() if vals]
    if not items:
        return []
    for _, vals in items:
        rng.shuffle(vals)

    base = max(1, total // len(items)) if total >= len(items) else 1
    selected: List[str] = []
    remainders: List[str] = []
    for key, vals in items:
        take = min(len(vals), base)
        selected.extend(vals[:take])
        remainders.extend(vals[take:])

    remaining = total - len(selected)
    if remaining > 0 and remainders:
        rng.shuffle(remainders)
        selected.extend(remainders[:remaining])
    return selected[:total]


def _select_universe(
    base: List[str],
    top_count: int,
    mid_count: int,
    small_count: int,
) -> Tuple[List[str], List[str], List[str], List[str]]:
    top = base[: max(0, top_count)]
    rest = base[len(top):]
    mid = []
    if mid_count > 0 and rest:
        start = max(0, len(rest) // 2 - mid_count // 2)
        mid = rest[start : start + mid_count]
    small = rest[-small_count:] if small_count > 0 else []
    combined = []
    for group in (top, mid, small):
        for sym in group:
            if sym not in combined:
                combined.append(sym)
    return top, mid, small, combined


def _load_klines_cached(
    cache: MarketDataCache,
    symbol: str,
    timeframe: str,
    limit: int,
    exchange: str,
    allow_fetch: bool,
) -> List[Dict]:
    if allow_fetch:
        klines, _stats = cache.get_klines(symbol, timeframe, limit, exchange=exchange)
        return klines
    if not getattr(cache, "_duckdb_enabled", False):
        return []
    return cache._fetch_cached(symbol, timeframe, limit, exchange)


def _kmeans(data: "np.ndarray", k: int, seed: int, max_iter: int) -> Tuple["np.ndarray", "np.ndarray", float]:
    rng = np.random.default_rng(seed)
    n_samples = data.shape[0]
    if n_samples < k:
        raise ValueError("not enough samples for k-means")
    centroids = data[rng.choice(n_samples, k, replace=False)].copy()
    labels = np.zeros(n_samples, dtype=np.int32)
    for _ in range(max_iter):
        dists = np.sum((data[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
        new_labels = np.argmin(dists, axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for idx in range(k):
            mask = labels == idx
            if not mask.any():
                centroids[idx] = data[rng.integers(0, n_samples)]
            else:
                centroids[idx] = data[mask].mean(axis=0)
    inertia = float(np.sum((data - centroids[labels]) ** 2))
    return centroids, labels, inertia


def main() -> int:
    if np is None:
        print("numpy is required for clustering. Please install numpy first.")
        return 2

    parser = argparse.ArgumentParser(description="Build 36-class regime clusters (1h)")
    parser.add_argument("--timeframe", type=str, default="1h")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--top-count", type=int, default=10)
    parser.add_argument("--mid-count", type=int, default=15)
    parser.add_argument("--small-count", type=int, default=15)
    parser.add_argument("--symbol-file", type=str, default="")
    parser.add_argument("--extra-symbols", type=str, default="")
    parser.add_argument("--exclude-symbols", type=str, default="")
    parser.add_argument("--lookback", type=int, default=50)
    parser.add_argument("--overlap-lookback", type=int, default=20)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--k", type=int, default=36)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-iter", type=int, default=60)
    parser.add_argument("--allow-fetch", action="store_true")
    parser.add_argument("--exchange", type=str, default="gate")
    parser.add_argument("--db-path", type=str, default="")
    parser.add_argument("--max-samples", type=int, default=0)
    parser.add_argument("--output", type=str, default="")
    parser.add_argument("--save-assignments", type=str, default="")
    args = parser.parse_args()

    timeframe = args.timeframe
    seconds = TIMEFRAME_SECONDS.get(timeframe)
    if not seconds:
        print(f"unsupported timeframe: {timeframe}")
        return 2

    base = FIXED_MARKETCAP
    if args.symbol_file:
        symbol_path = Path(args.symbol_file)
        if not symbol_path.exists():
            print(f"symbol file not found: {symbol_path}")
            return 2
        base = _parse_symbols_file(symbol_path)

    top = base[: max(0, args.top_count)]
    rest = base[len(top):]

    extra = [s.strip().upper() for s in args.extra_symbols.split(",") if s.strip()]
    for sym in extra:
        if sym not in top and sym not in rest:
            rest.append(sym)
    exclude = {s.strip().upper() for s in args.exclude_symbols.split(",") if s.strip()}
    if exclude:
        top = [s for s in top if s not in exclude]
        rest = [s for s in rest if s not in exclude]

    if not top and not rest:
        print("no symbols selected")
        return 2

    bars_needed = int(args.days * 86400 / seconds)
    limit = max(args.lookback + 1, bars_needed + args.lookback)
    start_ts = int(time.time()) - int(args.days * 86400)

    output_dir = ROOT / "outputs" / "regime"
    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = Path(args.db_path) if args.db_path else output_dir / f"regime_ohlcv_{timeframe}.duckdb"
    cache = MarketDataCache(db_path=db_path, default_exchange=args.exchange)

    symbol_stats: Dict[str, Dict[str, float]] = {}
    klines_by_symbol: Dict[str, List[Dict]] = {}
    skipped: List[str] = []

    for symbol in top + rest:
        klines = _load_klines_cached(
            cache,
            symbol,
            timeframe,
            limit,
            args.exchange,
            args.allow_fetch,
        )
        if not klines:
            skipped.append(symbol)
            continue
        klines = [k for k in klines if k.get("timestamp", 0) >= start_ts]
        if len(klines) < args.lookback + 1:
            skipped.append(symbol)
            continue
        klines_by_symbol[symbol] = klines
        symbol_stats[symbol] = _compute_symbol_stats(klines)

    if not top and not rest:
        print("no symbols available after filtering")
        return 2

    rest_stats = {s: symbol_stats[s] for s in rest if s in symbol_stats}
    if rest and not rest_stats:
        print("no stats for mid/small universe; enable --allow-fetch or check cache")
        return 2

    vol_values = [v.get("volatility", 0.0) for v in rest_stats.values()]
    volume_values = [v.get("avg_volume", 0.0) for v in rest_stats.values()]
    vol_low, vol_high = _tertile_thresholds(vol_values)
    volume_low, volume_high = _tertile_thresholds(volume_values)

    tiers: Dict[str, Dict[str, str]] = {}
    for sym, stats in rest_stats.items():
        tiers[sym] = {
            "volatility": _assign_tier(stats.get("volatility", 0.0), vol_low, vol_high),
            "volume": _assign_tier(stats.get("avg_volume", 0.0), volume_low, volume_high),
        }

    mid_bins: Dict[Tuple[str, ...], List[str]] = defaultdict(list)
    small_bins: Dict[Tuple[str, ...], List[str]] = defaultdict(list)
    for sym in rest_stats:
        vol_tier = tiers[sym]["volatility"]
        volu_tier = tiers[sym]["volume"]
        if volu_tier in ("mid", "high"):
            mid_bins[(volu_tier, vol_tier)].append(sym)
        else:
            small_bins[(volu_tier, vol_tier)].append(sym)

    mid = _balanced_sample(mid_bins, args.mid_count, args.seed)
    small = _balanced_sample(small_bins, args.small_count, args.seed + 1)

    universe = []
    for group in (top, mid, small):
        for sym in group:
            if sym not in universe:
                universe.append(sym)

    feature_rows: List[List[float]] = []
    rule_labels: List[str] = []
    meta_rows: List[Tuple[str, int]] = []
    per_symbol_counts: Dict[str, int] = defaultdict(int)

    for symbol in universe:
        klines = klines_by_symbol.get(symbol)
        if not klines:
            skipped.append(symbol)
            continue
        start_idx = args.lookback - 1
        for i in range(start_idx, len(klines), max(1, args.stride)):
            window = klines[: i + 1]
            features = extract_basic_kline_features(window, lookback=args.lookback)
            if not features:
                continue
            overlap_ratio = _calculate_overlap_ratio(window, lookback=args.overlap_lookback)
            vec = build_feature_vector(features, overlap_ratio)
            regime = _classify_regime_36(features, overlap_ratio).get("label") or "unknown"
            feature_rows.append(vec)
            rule_labels.append(regime)
            per_symbol_counts[symbol] += 1
            if args.save_assignments:
                meta_rows.append((symbol, int(window[-1]["timestamp"])))

    if not feature_rows:
        print("no samples collected")
        return 2

    if args.max_samples and len(feature_rows) > args.max_samples:
        indices = list(range(len(feature_rows)))
        random.Random(args.seed).shuffle(indices)
        indices = indices[: args.max_samples]
        feature_rows = [feature_rows[i] for i in indices]
        rule_labels = [rule_labels[i] for i in indices]
        if meta_rows:
            meta_rows = [meta_rows[i] for i in indices]

    data = np.array(feature_rows, dtype=np.float64)
    mean = data.mean(axis=0)
    std = data.std(axis=0)
    std = np.where(std == 0.0, 1.0, std)
    data = (data - mean) / std

    centroids, labels, inertia = _kmeans(data, args.k, args.seed, args.max_iter)

    cluster_counts: Dict[int, Counter] = defaultdict(Counter)
    for idx, label in enumerate(rule_labels):
        cluster_counts[int(labels[idx])][label] += 1

    cluster_labels: Dict[str, Dict[str, object]] = {}
    for i in range(args.k):
        counts = cluster_counts.get(i, Counter())
        top_label = counts.most_common(1)[0][0] if counts else "unknown"
        cluster_labels[str(i)] = {
            "label": top_label,
            "size": int(sum(counts.values())),
            "counts": dict(counts),
        }

    output_path = Path(args.output) if args.output else output_dir / f"regime_36_clusters_{timeframe}.json"

    payload = {
        "generated_at": datetime.now().isoformat(),
        "timeframe": timeframe,
        "days": args.days,
        "lookback": args.lookback,
        "overlap_lookback": args.overlap_lookback,
        "symbols": {
            "top": top,
            "mid": mid,
            "small": small,
            "all": universe,
            "skipped": skipped,
            "tiers": tiers,
            "selection_method": "stratified_volatility_volume",
        },
        "feature_names": list(FEATURE_NAMES),
        "feature_stats": {
            "mean": mean.tolist(),
            "std": std.tolist(),
        },
        "kmeans": {
            "k": args.k,
            "centroids": centroids.tolist(),
            "inertia": inertia,
            "max_iter": args.max_iter,
            "seed": args.seed,
        },
        "cluster_labels": cluster_labels,
        "samples": {
            "total": int(len(feature_rows)),
            "per_symbol": dict(per_symbol_counts),
        },
    }

    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"saved: {output_path}")

    if args.save_assignments and meta_rows:
        assign_path = Path(args.save_assignments)
        assign_path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["symbol,timestamp,cluster,regime_36"]
        for (symbol, ts), cluster, regime in zip(meta_rows, labels.tolist(), rule_labels):
            lines.append(f"{symbol},{ts},{cluster},{regime}")
        assign_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"assignments saved: {assign_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
