#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DuckDB-backed OHLCV cache with incremental updates."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time
import requests

try:
    import duckdb  # type: ignore
    DUCKDB_AVAILABLE = True
except Exception:
    duckdb = None
    DUCKDB_AVAILABLE = False

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB = ROOT / "data" / "market_cache" / "ohlcv_cache.duckdb"

TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


@dataclass
class CacheStats:
    fetched: int
    inserted: int
    source: str
    requests: int = 0
    elapsed_ms: int = 0
    errors: int = 0
    last_error: Optional[str] = None


class MarketDataCache:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DEFAULT_DB
        self.error_count = 0
        self.last_error: Optional[str] = None
        if DUCKDB_AVAILABLE:
            self._init_db()

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(str(self.db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol TEXT,
                timeframe TEXT,
                timestamp BIGINT,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                source TEXT
            )
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_ohlcv_key ON ohlcv(symbol, timeframe, timestamp)"
        )
        conn.close()

    def _fetch_cached(self, symbol: str, timeframe: str, limit: int) -> List[Dict]:
        if not DUCKDB_AVAILABLE:
            return []
        conn = duckdb.connect(str(self.db_path))
        try:
            rows = conn.execute(
                """
                SELECT timestamp, open, high, low, close, volume
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                [symbol, timeframe, limit],
            ).fetchall()
        finally:
            conn.close()
        rows = list(reversed(rows))
        return [
            {
                "timestamp": int(r[0]),
                "open": float(r[1]),
                "high": float(r[2]),
                "low": float(r[3]),
                "close": float(r[4]),
                "volume": float(r[5]),
            }
            for r in rows
        ]

    def _get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[int]:
        if not DUCKDB_AVAILABLE:
            return None
        conn = duckdb.connect(str(self.db_path))
        try:
            row = conn.execute(
                """
                SELECT MAX(timestamp)
                FROM ohlcv
                WHERE symbol = ? AND timeframe = ?
                """,
                [symbol, timeframe],
            ).fetchone()
        finally:
            conn.close()
        if not row or row[0] is None:
            return None
        return int(row[0])

    def _insert_rows(self, symbol: str, timeframe: str, rows: List[Dict], source: str) -> int:
        if not DUCKDB_AVAILABLE or not rows:
            return 0
        conn = duckdb.connect(str(self.db_path))
        inserted = 0
        try:
            values = [
                (
                    symbol,
                    timeframe,
                    int(r["timestamp"]),
                    float(r["open"]),
                    float(r["high"]),
                    float(r["low"]),
                    float(r["close"]),
                    float(r.get("volume") or 0.0),
                    source,
                )
                for r in rows
            ]
            conn.executemany(
                """
                INSERT OR IGNORE INTO ohlcv
                (symbol, timeframe, timestamp, open, high, low, close, volume, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            inserted = len(values)
        finally:
            conn.close()
        return inserted

    def _fetch_gate_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> List[Dict]:
        tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
        interval = tf_map.get(timeframe, timeframe)
        pair = f"{symbol}_USDT"
        limit = min(int(limit), 1000)
        params = {"currency_pair": pair, "interval": interval, "limit": limit}
        if from_ts:
            params["from"] = int(from_ts)
        if to_ts:
            params["to"] = int(to_ts)
        try:
            resp = requests.get("https://api.gateio.ws/api/v4/spot/candlesticks", params=params, timeout=20)
            if resp.status_code != 200:
                self.error_count += 1
                self.last_error = f"gate_status_{resp.status_code}"
                return []
            data = resp.json()
        except Exception:
            self.error_count += 1
            self.last_error = "gate_request_error"
            return []
        if not data:
            return []
        data.reverse()
        klines: List[Dict] = []
        for k in data:
            klines.append(
                {
                    "timestamp": int(k[0]),
                    "open": float(k[5]),
                    "high": float(k[3]),
                    "low": float(k[4]),
                    "close": float(k[2]),
                    "volume": float(k[1]),
                }
            )
        return klines

    def _fetch_gate_klines_paged(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> Tuple[List[Dict], int]:
        if from_ts:
            batch = self._fetch_gate_klines(symbol, timeframe, min(limit, 1000), from_ts=from_ts, to_ts=to_ts)
            return batch, 1

        remaining = max(0, int(limit))
        requests = 0
        collected: List[Dict] = []
        current_to = to_ts
        while remaining > 0:
            batch_limit = min(1000, remaining)
            batch = self._fetch_gate_klines(symbol, timeframe, batch_limit, to_ts=current_to)
            requests += 1
            if not batch:
                break
            collected.extend(batch)
            remaining -= len(batch)
            oldest_ts = batch[0]["timestamp"]
            current_to = oldest_ts - 1
            if len(batch) < batch_limit:
                break
        if collected:
            collected.sort(key=lambda x: x["timestamp"])
        return collected, requests

    def get_klines(self, symbol: str, timeframe: str, limit: int) -> Tuple[List[Dict], CacheStats]:
        symbol = symbol.upper()
        start_errors = self.error_count
        if not DUCKDB_AVAILABLE:
            start = time.time()
            klines, reqs = self._fetch_gate_klines_paged(symbol, timeframe, limit)
            elapsed = int((time.time() - start) * 1000)
            errors = self.error_count - start_errors
            last_error = self.last_error if errors > 0 else None
            return klines, CacheStats(
                fetched=len(klines),
                inserted=0,
                source="gate_direct",
                requests=reqs,
                elapsed_ms=elapsed,
                errors=errors,
                last_error=last_error,
            )

        cached = self._fetch_cached(symbol, timeframe, limit)
        last_ts = self._get_last_timestamp(symbol, timeframe)
        fetched = 0
        inserted = 0
        requests = 0
        start = time.time()

        if last_ts:
            from_ts = last_ts + 1
            new_rows, reqs = self._fetch_gate_klines_paged(symbol, timeframe, limit=1000, from_ts=from_ts)
            requests += reqs
            fetched += len(new_rows)
            inserted += self._insert_rows(symbol, timeframe, new_rows, "gate")
        if len(cached) < limit:
            fresh, reqs = self._fetch_gate_klines_paged(symbol, timeframe, limit=limit)
            requests += reqs
            fetched += len(fresh)
            inserted += self._insert_rows(symbol, timeframe, fresh, "gate")

        cached = self._fetch_cached(symbol, timeframe, limit)
        elapsed = int((time.time() - start) * 1000)
        errors = self.error_count - start_errors
        last_error = self.last_error if errors > 0 else None
        return cached, CacheStats(
            fetched=fetched,
            inserted=inserted,
            source="cache",
            requests=requests,
            elapsed_ms=elapsed,
            errors=errors,
            last_error=last_error,
        )
