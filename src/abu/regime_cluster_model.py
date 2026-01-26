#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regime cluster model utilities (k-means centroids + feature scaler)."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

FEATURE_NAMES = [
    "trend_strength",
    "trend_delta",
    "volatility",
    "range_pct",
    "range_high_dist_pct",
    "range_low_dist_pct",
    "dist_to_ema_pct",
    "pullback_depth_pct",
    "overlap_ratio",
    "range_mode",
    "breakout_up",
    "breakout_down",
]


def _as_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _as_bool(value: object) -> float:
    return 1.0 if bool(value) else 0.0


def build_feature_vector(
    features: Dict[str, object],
    overlap_ratio: float,
) -> List[float]:
    return [
        _as_float(features.get("trend_strength")),
        _as_float(features.get("trend_delta")),
        _as_float(features.get("volatility")),
        _as_float(features.get("range_pct")),
        _as_float(features.get("range_high_dist_pct")),
        _as_float(features.get("range_low_dist_pct")),
        _as_float(features.get("dist_to_ema_pct")),
        _as_float(features.get("pullback_depth_pct")),
        _as_float(overlap_ratio),
        _as_bool(features.get("range_mode")),
        _as_bool(features.get("breakout_up")),
        _as_bool(features.get("breakout_down")),
    ]


class RegimeClusterModel:
    def __init__(
        self,
        centroids: List[List[float]],
        mean: List[float],
        std: List[float],
        feature_names: Optional[List[str]] = None,
        cluster_labels: Optional[Dict[str, Dict[str, object]]] = None,
    ) -> None:
        self.centroids = centroids
        self.mean = mean
        self.std = std
        self.feature_names = feature_names or list(FEATURE_NAMES)
        self.cluster_labels = cluster_labels or {}

    @classmethod
    def from_json(cls, path: Path) -> "RegimeClusterModel":
        payload = json.loads(path.read_text(encoding="utf-8"))
        kmeans = payload.get("kmeans") or {}
        stats = payload.get("feature_stats") or {}
        return cls(
            centroids=kmeans.get("centroids") or [],
            mean=stats.get("mean") or [],
            std=stats.get("std") or [],
            feature_names=payload.get("feature_names"),
            cluster_labels=payload.get("cluster_labels"),
        )

    def _standardize(self, vec: List[float]) -> List[float]:
        out = []
        for value, mean, std in zip(vec, self.mean, self.std):
            denom = std if std not in (0, 0.0) else 1.0
            out.append((value - mean) / denom)
        return out

    def predict(self, features: Dict[str, object], overlap_ratio: float) -> Tuple[int, float, Optional[str]]:
        if not self.centroids:
            return -1, float("inf"), None
        vec = build_feature_vector(features, overlap_ratio)
        vec = self._standardize(vec)
        best_idx = -1
        best_dist = float("inf")
        for idx, centroid in enumerate(self.centroids):
            dist = 0.0
            for a, b in zip(vec, centroid):
                diff = a - b
                dist += diff * diff
            if dist < best_dist:
                best_dist = dist
                best_idx = idx
        label = None
        if best_idx >= 0:
            label_info = self.cluster_labels.get(str(best_idx)) or {}
            label = label_info.get("label")
        return best_idx, math.sqrt(best_dist), label
