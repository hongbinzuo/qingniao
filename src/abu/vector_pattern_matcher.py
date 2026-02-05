#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector Pattern Matcher - ABU System
Uses Annoy index to find similar Brooks patterns for live K-lines
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from annoy import AnnoyIndex

logger = logging.getLogger(__name__)


class VectorPatternMatcher:
    """Find similar Brooks patterns using vector similarity search"""

    def __init__(self, index_path: str, id_map_path: str, db_manager, dim: int = 32):
        """
        Initialize vector pattern matcher

        Args:
            index_path: Path to Annoy index file
            id_map_path: Path to ID mapping JSON
            db_manager: TraderDBManager instance
            dim: Vector dimension (default: 32)
        """
        self.dim = dim
        self.db = db_manager

        # Load Annoy index
        self.index = AnnoyIndex(dim, "angular")
        self.index.load(str(index_path))

        # Load ID mapping (annoy_idx -> pattern_vector_id)
        with open(id_map_path, "r", encoding="utf-8") as f:
            self.id_map = json.load(f)

        logger.info(f"Loaded vector index: {len(self.id_map)} patterns, {dim}D")

    def find_similar_patterns(
        self, query_vec: np.ndarray, k: int = 10
    ) -> Tuple[List[Dict], List[float]]:
        """
        Find K most similar Brooks patterns

        Args:
            query_vec: 32-dim query vector
            k: Number of neighbors to return

        Returns:
            (patterns, distances) tuple
            - patterns: List of pattern dicts with metadata
            - distances: List of angular distances (0=identical, 2=opposite)
        """
        # Query Annoy index
        indices, distances = self.index.get_nns_by_vector(
            query_vec.tolist(), k, include_distances=True
        )

        # Map Annoy indices to pattern_vector IDs
        pattern_ids = [self.id_map[str(idx)] for idx in indices]

        # Retrieve patterns from database
        patterns = self._get_patterns_by_ids(pattern_ids)

        return patterns, distances

    def _get_patterns_by_ids(self, pattern_ids: List[int]) -> List[Dict]:
        """Retrieve pattern metadata from database"""
        conn = self.db._get_connection()

        try:
            placeholders = ",".join(["%s"] * len(pattern_ids))
            rows = conn.execute(
                f"""
                SELECT id, pattern_features, market_context, metadata
                FROM pattern_vectors
                WHERE id IN ({placeholders})
            """,
                tuple(pattern_ids),
            ).fetchall()

            patterns = []
            for row in rows:
                patterns.append(
                    {
                        "id": row[0],
                        "pattern_features": row[1] or {},
                        "market_context": row[2] or {},
                        "metadata": row[3] or {},
                    }
                )

            return patterns

        finally:
            conn.close()

    def aggregate_outcomes(self, patterns: List[Dict], distances: List[float]) -> Dict:
        """
        Aggregate outcomes from similar patterns

        Args:
            patterns: List of pattern dicts
            distances: Angular distances (0-2)

        Returns:
            Aggregated outcome dict with win_prob, RR, confidence
        """
        if not patterns:
            return {
                "win_probability": 0.5,
                "typical_rr": 1.5,
                "confidence": 0.0,
                "num_matches": 0,
                "consensus_direction": "neutral",
            }

        # Convert distances to similarity weights (1 - distance/2)
        weights = [max(0, 1 - d / 2) for d in distances]
        total_weight = sum(weights)

        if total_weight == 0:
            weights = [1.0] * len(patterns)
            total_weight = len(patterns)

        # Weighted average of win_probability
        win_probs = []
        rrs = []
        directions = []

        for pattern, weight in zip(patterns, weights):
            meta = pattern.get("metadata", {})
            pf = pattern.get("pattern_features", {})

            win_probs.append(meta.get("win_probability", 0.5) * weight)
            rrs.append(meta.get("typical_rr", 1.5) * weight)

            direction = pf.get("direction", "neutral").lower()
            if direction in ("long", "bull", "bullish"):
                directions.append(("bullish", weight))
            elif direction in ("short", "bear", "bearish"):
                directions.append(("bearish", weight))
            else:
                directions.append(("neutral", weight))

        # Calculate weighted averages
        avg_win_prob = sum(win_probs) / total_weight
        avg_rr = sum(rrs) / total_weight

        # Consensus direction (highest weighted vote)
        dir_weights = {"bullish": 0, "bearish": 0, "neutral": 0}
        for direction, weight in directions:
            dir_weights[direction] += weight

        consensus_direction = max(dir_weights, key=dir_weights.get)

        # Confidence = similarity of closest match
        confidence = weights[0] / total_weight if weights else 0.0

        return {
            "win_probability": avg_win_prob,
            "typical_rr": avg_rr,
            "confidence": confidence,
            "num_matches": len(patterns),
            "consensus_direction": consensus_direction,
            "direction_weights": dir_weights,
        }
