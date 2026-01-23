#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Estimate TP/SL probabilities from feedback statistics."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except Exception:
    TraderDBManager = None
    DB_AVAILABLE = False


@dataclass
class ProbabilityEstimate:
    p_tp1: float
    p_tp2: float  # conditional on TP1
    p_sl: float
    sample_size: int
    weight: float
    source: str
    scope: str


class SignalProbabilityEstimator:
    """Fetch empirical probabilities from signal_evaluations."""

    def __init__(self, trader_id: str = "abu", min_samples: int = 20, use_database: bool = True) -> None:
        self.trader_id = trader_id
        self.min_samples = min_samples
        self.use_database = use_database and DB_AVAILABLE
        if self.use_database:
            try:
                self.db = TraderDBManager(trader_id)
            except Exception:
                self.db = None
                self.use_database = False
        else:
            self.db = None
        self._cache: Dict[Tuple[Optional[str], Optional[str], Optional[str]], ProbabilityEstimate] = {}

    def _query_stats(self, where_clause: str, params: Tuple[object, ...]) -> Optional[Tuple[int, int, int, int]]:
        if not self.db:
            return None
        sql = f"""
            SELECT
                SUM(CASE WHEN COALESCE(se.missed::int, 0) = 0 THEN 1 ELSE 0 END) AS total,
                SUM(CASE WHEN COALESCE(se.missed::int, 0) = 0 AND COALESCE(se.take_profit_1_hit::int, 0) = 1 THEN 1 ELSE 0 END) AS tp1,
                SUM(CASE WHEN COALESCE(se.missed::int, 0) = 0 AND COALESCE(se.take_profit_2_hit::int, 0) = 1 THEN 1 ELSE 0 END) AS tp2,
                SUM(CASE WHEN COALESCE(se.missed::int, 0) = 0 AND COALESCE(se.stop_loss_hit::int, 0) = 1 THEN 1 ELSE 0 END) AS sl
            FROM signal_evaluations se
            JOIN trading_signals ts ON ts.id = se.signal_id
            WHERE ts.system_name = %s
            {where_clause}
        """
        conn = self.db._get_connection(read_only=True)
        try:
            row = conn.execute(sql, params).fetchone()
        finally:
            conn.close()
        if not row:
            return None
        total = int(row[0] or 0)
        tp1 = int(row[1] or 0)
        tp2 = int(row[2] or 0)
        sl = int(row[3] or 0)
        return total, tp1, tp2, sl

    def _build_estimate(self, total: int, tp1: int, tp2: int, sl: int, scope: str) -> ProbabilityEstimate:
        p_tp1 = tp1 / total if total > 0 else 0.0
        p_tp2 = tp2 / tp1 if tp1 > 0 else 0.0
        p_sl = sl / total if total > 0 else 0.0
        weight = min(1.0, total / max(1, self.min_samples))
        return ProbabilityEstimate(
            p_tp1=p_tp1,
            p_tp2=p_tp2,
            p_sl=p_sl,
            sample_size=total,
            weight=weight,
            source="feedback",
            scope=scope,
        )

    def estimate(
        self,
        symbol: Optional[str],
        timeframe: Optional[str],
        entry_model: Optional[str] = None,
    ) -> Optional[ProbabilityEstimate]:
        cache_key = (symbol, timeframe, entry_model)
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.use_database:
            return None

        scopes = []
        if entry_model:
            scopes.append(("pattern", "AND ts.entry_model = %s AND ts.timeframe = %s", (entry_model, timeframe)))
        if symbol and timeframe:
            scopes.append(("symbol", "AND ts.symbol = %s AND ts.timeframe = %s", (symbol, timeframe)))
        if timeframe:
            scopes.append(("timeframe", "AND ts.timeframe = %s", (timeframe,)))

        best: Optional[ProbabilityEstimate] = None
        for scope, clause, extra_params in scopes:
            params = (self.trader_id,) + extra_params
            stats = self._query_stats(clause, params)
            if not stats:
                continue
            total, tp1, tp2, sl = stats
            if total <= 0:
                continue
            estimate = self._build_estimate(total, tp1, tp2, sl, scope)
            if total >= self.min_samples:
                self._cache[cache_key] = estimate
                return estimate
            if best is None or total > best.sample_size:
                best = estimate

        if best:
            self._cache[cache_key] = best
        return best
