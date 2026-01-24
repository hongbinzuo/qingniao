#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DuckDB-backed OHLCV cache with incremental updates."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
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
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}
BYBIT_INTERVALS = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "1h": "60",
    "4h": "240",
    "1d": "D",
}
BITGET_GRANULARITY = {
    "1m": "60",
    "3m": "180",
    "5m": "300",
    "15m": "900",
    "1h": "3600",
    "4h": "14400",
    "1d": "86400",
}

DB_LOCK = threading.Lock()


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
    def __init__(self, db_path: Optional[Path] = None, default_exchange: str = "gate") -> None:
        self.db_path = db_path or DEFAULT_DB
        self.default_exchange = (default_exchange or "gate").lower()
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.min_interval = 0.25
        self.min_interval_by_exchange = {
            "gate": 0.25,
            "bybit": 0.2,
            "bitget": 0.2,
        }
        self.max_retries = 3
        self._last_request_ts: Dict[str, float] = {}
        self._duckdb_enabled = DUCKDB_AVAILABLE
        if self._duckdb_enabled:
            try:
                self._init_db()
            except Exception:
                self._duckdb_enabled = False

    def _init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with DB_LOCK:
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
            try:
                conn.execute("DROP INDEX IF EXISTS idx_ohlcv_key")
            except Exception:
                pass
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_ohlcv_key_src ON ohlcv(source, symbol, timeframe, timestamp)"
            )
            conn.close()

    def _fetch_cached(self, symbol: str, timeframe: str, limit: int, source: str) -> List[Dict]:
        if not self._duckdb_enabled:
            return []
        with DB_LOCK:
            conn = duckdb.connect(str(self.db_path))
            try:
                rows = conn.execute(
                    """
                    SELECT timestamp, open, high, low, close, volume
                    FROM ohlcv
                    WHERE symbol = ? AND timeframe = ? AND source = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    [symbol, timeframe, source, limit],
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

    def _get_last_timestamp(self, symbol: str, timeframe: str, source: str) -> Optional[int]:
        if not self._duckdb_enabled:
            return None
        with DB_LOCK:
            conn = duckdb.connect(str(self.db_path))
            try:
                row = conn.execute(
                    """
                    SELECT MAX(timestamp)
                    FROM ohlcv
                    WHERE symbol = ? AND timeframe = ? AND source = ?
                    """,
                    [symbol, timeframe, source],
                ).fetchone()
            finally:
                conn.close()
        if not row or row[0] is None:
            return None
        return int(row[0])

    def _insert_rows(self, symbol: str, timeframe: str, rows: List[Dict], source: str) -> int:
        if not self._duckdb_enabled or not rows:
            return 0
        inserted = 0
        with DB_LOCK:
            conn = duckdb.connect(str(self.db_path))
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

    def _throttle(self, exchange: str) -> None:
        min_interval = self.min_interval_by_exchange.get(exchange, self.min_interval)
        if min_interval <= 0:
            return
        now = time.time()
        last_ts = self._last_request_ts.get(exchange, 0.0)
        gap = now - last_ts
        if gap < min_interval:
            time.sleep(min_interval - gap)
        self._last_request_ts[exchange] = time.time()

    @staticmethod
    def _normalize_ts(value: object) -> int:
        try:
            ts = int(float(value))
        except Exception:
            return 0
        if ts > 1_000_000_000_000:
            return ts // 1000
        if ts > 10_000_000_000:
            return ts // 1000
        return ts

    def _request_gate(self, params: Dict) -> Optional[List]:
        backoff = 1.0
        for attempt in range(self.max_retries + 1):
            self._throttle("gate")
            try:
                resp = requests.get("https://api.gateio.ws/api/v4/spot/candlesticks", params=params, timeout=20)
            except Exception:
                self.error_count += 1
                self.last_error = "gate_request_error"
                if attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return None

            if resp.status_code == 200:
                try:
                    return resp.json()
                except Exception:
                    self.error_count += 1
                    self.last_error = "gate_json_error"
                    return None

            if resp.status_code in (429, 500, 502, 503, 504):
                self.error_count += 1
                self.last_error = f"gate_status_{resp.status_code}"
                if attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
            else:
                self.error_count += 1
                self.last_error = f"gate_status_{resp.status_code}"
            return None
        return None

    def _request_bybit(self, params: Dict) -> Optional[List]:
        backoff = 1.0
        for attempt in range(self.max_retries + 1):
            self._throttle("bybit")
            try:
                resp = requests.get("https://api.bybit.com/v5/market/kline", params=params, timeout=20)
            except Exception:
                self.error_count += 1
                self.last_error = "bybit_request_error"
                if attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return None

            if resp.status_code != 200:
                self.error_count += 1
                self.last_error = f"bybit_status_{resp.status_code}"
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return None

            try:
                data = resp.json()
            except Exception:
                self.error_count += 1
                self.last_error = "bybit_json_error"
                return None

            if data.get("retCode") != 0:
                self.error_count += 1
                self.last_error = f"bybit_ret_{data.get('retCode')}"
                return None
            result = data.get("result") or {}
            return result.get("list") or []
        return None

    def _request_bitget(self, params: Dict) -> Optional[List]:
        backoff = 1.0
        for attempt in range(self.max_retries + 1):
            self._throttle("bitget")
            try:
                resp = requests.get("https://api.bitget.com/api/spot/v1/market/candles", params=params, timeout=20)
            except Exception:
                self.error_count += 1
                self.last_error = "bitget_request_error"
                if attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return None

            if resp.status_code != 200:
                self.error_count += 1
                self.last_error = f"bitget_status_{resp.status_code}"
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                return None

            try:
                data = resp.json()
            except Exception:
                self.error_count += 1
                self.last_error = "bitget_json_error"
                return None

            if isinstance(data, list):
                return data
            if data.get("code") not in (None, "00000", "0", 0):
                self.error_count += 1
                self.last_error = f"bitget_code_{data.get('code')}"
                return None
            return data.get("data") or []
        return None

    def _fetch_gate_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> List[Dict]:
        tf_map = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d"}
        interval = tf_map.get(timeframe, timeframe)
        pair = f"{symbol}_USDT"
        limit = min(int(limit), 1000)
        params = {"currency_pair": pair, "interval": interval, "limit": limit}
        if from_ts:
            params["from"] = int(from_ts)
        if to_ts:
            params["to"] = int(to_ts)
        data = self._request_gate(params)
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

    def _fetch_bybit_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
    ) -> List[Dict]:
        interval = BYBIT_INTERVALS.get(timeframe)
        if not interval:
            return []
        params: Dict[str, object] = {
            "category": "spot",
            "symbol": f"{symbol}USDT",
            "interval": interval,
            "limit": min(int(limit), 1000),
        }
        if start_ms:
            params["start"] = int(start_ms)
        if end_ms:
            params["end"] = int(end_ms)
        data = self._request_bybit(params)
        if not data:
            return []
        klines: List[Dict] = []
        for k in data:
            if not k or len(k) < 6:
                continue
            ts = self._normalize_ts(k[0])
            if ts <= 0:
                continue
            klines.append(
                {
                    "timestamp": ts,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
            )
        if klines:
            klines.sort(key=lambda x: x["timestamp"])
        return klines

    def _fetch_bitget_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
    ) -> List[Dict]:
        granularity = BITGET_GRANULARITY.get(timeframe)
        if not granularity:
            return []
        params: Dict[str, object] = {
            "symbol": f"{symbol}USDT",
            "granularity": granularity,
            "limit": min(int(limit), 1000),
        }
        if start_ms:
            params["startTime"] = int(start_ms)
        if end_ms:
            params["endTime"] = int(end_ms)
        data = self._request_bitget(params)
        if not data:
            return []
        klines: List[Dict] = []
        for k in data:
            if not k or len(k) < 6:
                continue
            ts = self._normalize_ts(k[0])
            if ts <= 0:
                continue
            klines.append(
                {
                    "timestamp": ts,
                    "open": float(k[1]),
                    "high": float(k[3]),
                    "low": float(k[4]),
                    "close": float(k[2]),
                    "volume": float(k[5]),
                }
            )
        if klines:
            klines.sort(key=lambda x: x["timestamp"])
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
            expected = None
            tf_sec = TIMEFRAME_SECONDS.get(timeframe)
            if tf_sec:
                expected = max(0, int((int(time.time()) - from_ts) / tf_sec))
            max_pages = 10
            if expected:
                max_pages = min(50, max(1, expected // 1000 + 2))
            requests = 0
            collected: List[Dict] = []
            current_from = from_ts
            for _ in range(max_pages):
                batch = self._fetch_gate_klines(symbol, timeframe, 1000, from_ts=current_from, to_ts=to_ts)
                requests += 1
                if not batch:
                    break
                collected.extend(batch)
                if len(batch) < 1000:
                    break
                current_from = batch[-1]["timestamp"] + 1
            if collected:
                collected.sort(key=lambda x: x["timestamp"])
            return collected, requests

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

    def _fetch_bybit_klines_paged(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> Tuple[List[Dict], int]:
        if from_ts:
            start_ms = int(from_ts) * 1000
            end_ms = int(to_ts) * 1000 if to_ts else int(time.time()) * 1000
            batch = self._fetch_bybit_klines(symbol, timeframe, 1000, start_ms=start_ms, end_ms=end_ms)
            return batch, 1

        remaining = max(0, int(limit))
        requests = 0
        collected: List[Dict] = []
        current_end = int(to_ts) * 1000 if to_ts else None
        while remaining > 0:
            batch_limit = min(1000, remaining)
            batch = self._fetch_bybit_klines(symbol, timeframe, batch_limit, end_ms=current_end)
            requests += 1
            if not batch:
                break
            collected.extend(batch)
            remaining -= len(batch)
            oldest_ts = batch[0]["timestamp"]
            current_end = int(oldest_ts - 1) * 1000
            if len(batch) < batch_limit:
                break
        if collected:
            collected.sort(key=lambda x: x["timestamp"])
        return collected, requests

    def _fetch_bitget_klines_paged(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
    ) -> Tuple[List[Dict], int]:
        if from_ts:
            start_ms = int(from_ts) * 1000
            end_ms = int(to_ts) * 1000 if to_ts else int(time.time()) * 1000
            batch = self._fetch_bitget_klines(symbol, timeframe, 1000, start_ms=start_ms, end_ms=end_ms)
            return batch, 1

        remaining = max(0, int(limit))
        requests = 0
        collected: List[Dict] = []
        current_end = int(to_ts) * 1000 if to_ts else None
        while remaining > 0:
            batch_limit = min(1000, remaining)
            batch = self._fetch_bitget_klines(symbol, timeframe, batch_limit, end_ms=current_end)
            requests += 1
            if not batch:
                break
            collected.extend(batch)
            remaining -= len(batch)
            oldest_ts = batch[0]["timestamp"]
            current_end = int(oldest_ts - 1) * 1000
            if len(batch) < batch_limit:
                break
        if collected:
            collected.sort(key=lambda x: x["timestamp"])
        return collected, requests

    def get_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        exchange: Optional[str] = None,
    ) -> Tuple[List[Dict], CacheStats]:
        symbol = symbol.upper()
        exchange = (exchange or self.default_exchange or "gate").lower()
        if exchange not in ("gate", "bybit", "bitget"):
            exchange = "gate"

        fetcher = {
            "gate": self._fetch_gate_klines_paged,
            "bybit": self._fetch_bybit_klines_paged,
            "bitget": self._fetch_bitget_klines_paged,
        }.get(exchange, self._fetch_gate_klines_paged)

        start_errors = self.error_count
        if not self._duckdb_enabled:
            start = time.time()
            klines, reqs = fetcher(symbol, timeframe, limit)
            elapsed = int((time.time() - start) * 1000)
            errors = self.error_count - start_errors
            last_error = self.last_error if errors > 0 else None
            return klines, CacheStats(
                fetched=len(klines),
                inserted=0,
                source=f"{exchange}_direct",
                requests=reqs,
                elapsed_ms=elapsed,
                errors=errors,
                last_error=last_error,
            )

        cached = self._fetch_cached(symbol, timeframe, limit, exchange)
        last_ts = self._get_last_timestamp(symbol, timeframe, exchange)
        fetched = 0
        inserted = 0
        requests = 0
        start = time.time()

        if last_ts:
            from_ts = last_ts + 1
            new_rows, reqs = fetcher(symbol, timeframe, limit=1000, from_ts=from_ts)
            requests += reqs
            fetched += len(new_rows)
            inserted += self._insert_rows(symbol, timeframe, new_rows, exchange)
        if len(cached) < limit:
            fresh, reqs = fetcher(symbol, timeframe, limit=limit)
            requests += reqs
            fetched += len(fresh)
            inserted += self._insert_rows(symbol, timeframe, fresh, exchange)

        cached = self._fetch_cached(symbol, timeframe, limit, exchange)
        elapsed = int((time.time() - start) * 1000)
        errors = self.error_count - start_errors
        last_error = self.last_error if errors > 0 else None
        return cached, CacheStats(
            fetched=fetched,
            inserted=inserted,
            source=f"{exchange}_cache",
            requests=requests,
            elapsed_ms=elapsed,
            errors=errors,
            last_error=last_error,
        )
