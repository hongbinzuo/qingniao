#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qingniao-Abu Top10 PA scanner (Gate/Bybit/Bitget, 5m/15m/1h)

- K-line numeric detectors produce trade_ready candidates
- Brooks constraints filter/score
- Unified pattern library (Gemini + Cursor + Brooks) provides alignment score
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import json
import requests
import threading
import time

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.detectors import detect_all_15m, detect_all_1h  # type: ignore
from abu.best_practice_rules import BestPracticeRulebook  # type: ignore
from abu.signal_probability_estimator import SignalProbabilityEstimator  # type: ignore
from abu.market_cache import MarketDataCache  # type: ignore
from abu.ranker import score_candidate  # type: ignore
from abu.kline_feature_extractor import extract_basic_kline_features  # type: ignore
from abu.brooks_pattern_constraints import BrooksPatternConstraints, ConstraintResult  # type: ignore
from abu.market_context import classify_market_context, context_filter_reason, context_mismatch  # type: ignore
from db_manager_trader import TraderDBManager  # type: ignore

try:
    from abu.unified_pattern_library import UnifiedPatternLibrary  # type: ignore
    PATTERN_LIB_AVAILABLE = True
except Exception:
    UnifiedPatternLibrary = None
    PATTERN_LIB_AVAILABLE = False

try:
    from abu.pattern_audit import run_pattern_audit  # type: ignore
    AUDIT_AVAILABLE = True
except Exception:
    run_pattern_audit = None
    AUDIT_AVAILABLE = False

EXCL = set(['USDT', 'USDC', 'DAI', 'BUSD', 'FDUSD', 'TUSD', 'PYUSD', 'USDE', 'GUSD', 'EURT'])
IGNORE_SYMBOLS = set([
    'AIR', 'AIRUSDT', 'AIR-PERP',
    'RIDE', 'TRALA', 'RIDE-PERP', 'TRALA-PERP', 'RIDEUSDT', 'TRALAUSDT'
])
KLINES_PER_DAY = {
    '5m': 288,
    '15m': 96,
    '1h': 24,
}
DEFAULT_DAYS = {
    '5m': 5,
    '15m': 14,
    '1h': 45,
}
PATTERN_RULE_HINTS = {
    'KeyLevel': 'Trading Range',
    'InsideBar': 'Breakout',
    'PinBar': 'Reversal',
    'Engulfing': 'Engulfing',
}
PATTERN_TYPE_MAP = {
    'InsideBar': 'breakout',
    'Engulfing': 'reversal',
    'PinBar': 'reversal',
    'KeyLevel': 'trading_range',
}
LEVERAGED_SUFFIXES = ('UP', 'DOWN', 'BULL', 'BEAR', '3L', '3S', '5L', '5S', '2L', '2S', '10L', '10S')
MIN_STOP_PCT = {'5m': 0.005, '15m': 0.008, '1h': 0.01}
EMA_DEVIATION_MIN = {'5m': 0.006, '15m': 0.01, '1h': 0.015}
EMA_DEVIATION_PENALTY_MAX = 0.6
STOP_LOOKBACK = {'5m': 10, '15m': 20, '1h': 20}
ATR_BUFFER_MULT = 0.2
ATR_K_TREND = {'5m': 3.0, '15m': 1.2, '1h': 1.2}
ATR_K_COUNTER = {'5m': 3.0, '15m': 1.5, '1h': 1.5}
EXCHANGES = ('gate', 'bybit', 'bitget')
SYMBOL_CACHE_DIR = ROOT / 'data' / 'exchange_symbols'
SYMBOL_CACHE_TTL_HOURS = 12
MOVERS_COUNT = 10
VELO_CACHE_TTL_SEC = 300
VELO_CACHE_DIR = ROOT / 'data' / 'velo_cache'
VELO_GAINERS_URL = (
    "https://velo.xyz/api/m/priceLine"
    "?range=3600000&resolution=1%20minute&filter=Top%20Gainers"
)
EXCHANGE_HEALTH: Dict[str, Dict[str, Optional[str]]] = {}
PATTERN_SOURCES = ['gemini_pro3', 'brooks_rule']
USE_BROOKS_RULES = True
FIXED_MARKETCAP = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'TRX', 'DOGE', 'BCH', 'ADA', 'XLM',
    'LINK', 'ZEC', 'SUI', 'HBAR', 'AVAX', 'LTC', 'SHIB', 'WLFI', 'UNI',
    'TON', 'DOT', 'TAO', 'TRUMP', 'AAVE', 'WLD', 'PEPE', 'NEAR', 'ICP', 'ETC',
    'ONDO', 'ASTER', 'FIL', 'SKY', 'ARB', 'PUMP', 'ENA', 'POL', 'OP',
    'APT', 'ATOM', 'ZRO', 'RENDER', 'ALGO', 'QNT', 'ENS', 'VET', 'DASH',
    'VIRTUAL', 'BONK', 'AXS', 'SEI', 'PENGU', 'MORPHO', 'CAKE', 'FET', 'XTZ',
    'JUP', 'CRV', 'NEXO', 'PENDLE', 'RAY', 'STX', 'LDO', 'CHZ'
]
LAST_TOP_META = {
    'requested': [],
    'returned': [],
    'not_on_gate': [],
    'gate_symbols_empty': False,
    'gate_filter': False,
    'movers_added': [],
    'movers_gainers': [],
    'movers_losers': [],
    'velo_gainers': [],
    'velo_added': [],
}


def _normalize_pattern_type(pattern_type: Optional[str]) -> str:
    if not pattern_type:
        return "unknown"
    text = str(pattern_type).lower()
    if "breakout" in text:
        return "breakout"
    if "reversal" in text:
        return "reversal"
    if "trend" in text:
        return "trend"
    if "range" in text or "trading_range" in text:
        return "trading_range"
    return text


def _format_price(value: Optional[object]) -> str:
    if value is None:
        return "-"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "-"
    abs_num = abs(num)
    if abs_num >= 1:
        return f"{num:.4f}"
    if abs_num >= 0.01:
        return f"{num:.6f}"
    return f"{num:.9f}"


def _ema_deviation_penalty(
    cand: Dict[str, object],
    features: Dict[str, object],
    context_info: Dict[str, object],
    timeframe: str,
) -> tuple[float, Optional[str]]:
    if not context_info or context_info.get('context') != 'broad_channel':
        return 0.0, None
    trend_dir = str(features.get('trend_direction') or '')
    direction = str(cand.get('type') or '')
    if trend_dir not in ('bullish', 'bearish') or direction not in ('long', 'short'):
        return 0.0, None
    countertrend = (trend_dir == 'bullish' and direction == 'short') or (
        trend_dir == 'bearish' and direction == 'long'
    )
    if not countertrend:
        return 0.0, None
    min_dev = EMA_DEVIATION_MIN.get(timeframe, 0.01)
    dist = float(features.get('dist_to_ema_pct') or 0.0)
    if dist >= min_dev:
        return 0.0, None
    ratio = 1.0 - (dist / max(min_dev, 1e-9))
    penalty = max(0.0, min(EMA_DEVIATION_PENALTY_MAX, ratio * EMA_DEVIATION_PENALTY_MAX))
    note = f"EMA乖离不足({dist * 100:.2f}%<{min_dev * 100:.2f}%)"
    return penalty, note


def _is_excluded_symbol(symbol: str) -> bool:
    sym = symbol.upper()
    if sym in IGNORE_SYMBOLS:
        return True
    if sym.endswith('PERP') and sym.replace('-', '').replace('_', '').replace('PERP', '') in ('RIDE', 'TRALA'):
        return True
    if sym in EXCL:
        return True
    if sym.startswith(('USD', 'USDT', 'USDC')):
        return True
    if sym.endswith(LEVERAGED_SUFFIXES):
        return True
    return False


def _fetch_gate_tickers() -> List[Dict]:
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if isinstance(data, list):
            return data
    except Exception:
        return []
    return []


def _fetch_gate_symbols() -> List[str]:
    data = _fetch_gate_tickers()
    if not data:
        return []
    return [
        t['currency_pair'].replace('_USDT', '').upper()
        for t in data
        if t.get('currency_pair', '').endswith('_USDT')
    ]


def _select_top_movers(tickers: List[Dict], count: int = MOVERS_COUNT) -> Tuple[List[str], List[str]]:
    gainers: List[Tuple[float, str]] = []
    losers: List[Tuple[float, str]] = []
    for item in tickers or []:
        pair = item.get('currency_pair') or ''
        if not pair.endswith('_USDT'):
            continue
        symbol = pair.replace('_USDT', '').upper()
        if _is_excluded_symbol(symbol):
            continue
        try:
            change_pct = float(item.get('change_percentage'))
        except Exception:
            continue
        if change_pct >= 0:
            gainers.append((change_pct, symbol))
        else:
            losers.append((change_pct, symbol))
    gainers.sort(key=lambda x: x[0], reverse=True)
    losers.sort(key=lambda x: x[0])
    top_gainers = [s for _, s in gainers[:max(0, count)]]
    top_losers = [s for _, s in losers[:max(0, count)]]
    return top_gainers, top_losers


def _load_velo_cache(ttl_sec: int = VELO_CACHE_TTL_SEC) -> Optional[List[str]]:
    try:
        cache_path = VELO_CACHE_DIR / "velo_gainers_1h.json"
        if not cache_path.exists():
            return None
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        fetched_ts = float(payload.get("fetched_ts") or 0.0)
        if fetched_ts <= 0:
            return None
        if ttl_sec > 0 and (time.time() - fetched_ts) > ttl_sec:
            return None
        symbols = payload.get("symbols") or []
        return [str(s).upper() for s in symbols if s]
    except Exception:
        return None


def _save_velo_cache(symbols: List[str]) -> None:
    try:
        VELO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = VELO_CACHE_DIR / "velo_gainers_1h.json"
        payload = {
            "fetched_ts": time.time(),
            "symbols": symbols,
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    except Exception:
        return None


def _fetch_velo_top_gainers(count: int = MOVERS_COUNT, gate_symbols: Optional[set] = None) -> List[str]:
    cached = _load_velo_cache()
    if cached:
        return cached[:max(0, count)]
    try:
        resp = requests.get(VELO_GAINERS_URL, timeout=20)
    except Exception:
        return []
    if resp.status_code != 200:
        return []
    try:
        payload = resp.json()
    except Exception:
        return []
    rows = payload.get("d") or []
    if not isinstance(rows, list):
        return []

    series: Dict[str, Dict[str, float]] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 3:
            continue
        ts = row[0]
        symbol = str(row[1]).upper() if row[1] else ""
        try:
            price = float(row[2])
        except Exception:
            continue
        if not symbol or price <= 0:
            continue
        if _is_excluded_symbol(symbol):
            continue
        if gate_symbols and symbol not in gate_symbols:
            continue
        rec = series.get(symbol)
        if rec is None:
            series[symbol] = {"min_ts": float(ts), "min_price": price, "max_ts": float(ts), "max_price": price}
        else:
            if float(ts) < rec["min_ts"]:
                rec["min_ts"] = float(ts)
                rec["min_price"] = price
            if float(ts) > rec["max_ts"]:
                rec["max_ts"] = float(ts)
                rec["max_price"] = price

    changes: List[Tuple[float, str]] = []
    for sym, rec in series.items():
        start_price = rec.get("min_price") or 0.0
        end_price = rec.get("max_price") or 0.0
        if start_price <= 0 or end_price <= 0:
            continue
        change_pct = (end_price - start_price) / start_price
        changes.append((change_pct, sym))

    changes.sort(key=lambda x: x[0], reverse=True)
    top = [sym for _, sym in changes[:max(0, count)]]
    if top:
        _save_velo_cache(top)
    return top


def _check_exchange_health(exchange: str, timeout: int = 5) -> bool:
    exchange = (exchange or '').lower()
    try:
        if exchange == 'gate':
            params = {"currency_pair": "BTC_USDT", "interval": "5m", "limit": 1}
            resp = requests.get("https://api.gateio.ws/api/v4/spot/candlesticks", params=params, timeout=timeout)
            ok = resp.status_code == 200
        elif exchange == 'bybit':
            params = {"category": "spot", "symbol": "BTCUSDT", "interval": "5", "limit": 1}
            resp = requests.get("https://api.bybit.com/v5/market/kline", params=params, timeout=timeout)
            ok = resp.status_code == 200
        elif exchange == 'bitget':
            params = {"symbol": "BTCUSDT", "granularity": "300", "limit": 1}
            resp = requests.get("https://api.bitget.com/api/spot/v1/market/candles", params=params, timeout=timeout)
            ok = resp.status_code == 200
        else:
            ok = False
        EXCHANGE_HEALTH[exchange] = {"status": "ok" if ok else "down", "error": None if ok else f"http_{resp.status_code}"}
        return ok
    except Exception as exc:
        EXCHANGE_HEALTH[exchange] = {"status": "down", "error": str(exc)}
        return False


def _load_symbol_cache(exchange: str, ttl_hours: int) -> Optional[set]:
    try:
        cache_path = SYMBOL_CACHE_DIR / f"{exchange}_spot.json"
        if not cache_path.exists():
            return None
        payload = json.loads(cache_path.read_text(encoding='utf-8'))
        fetched_ts = float(payload.get('fetched_ts') or 0.0)
        if fetched_ts <= 0:
            return None
        age_sec = time.time() - fetched_ts
        if ttl_hours > 0 and age_sec > ttl_hours * 3600:
            return None
        symbols = payload.get('symbols') or []
        return set(str(s).upper() for s in symbols if s)
    except Exception:
        return None


def _save_symbol_cache(exchange: str, symbols: List[str]) -> None:
    try:
        SYMBOL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = SYMBOL_CACHE_DIR / f"{exchange}_spot.json"
        payload = {
            "exchange": exchange,
            "fetched_ts": time.time(),
            "symbols": sorted(set(symbols)),
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding='utf-8')
    except Exception:
        return None


def _fetch_bybit_symbols() -> List[str]:
    symbols: List[str] = []
    cursor = ''
    for _ in range(5):
        params = {"category": "spot", "limit": 1000}
        if cursor:
            params["cursor"] = cursor
        try:
            resp = requests.get("https://api.bybit.com/v5/market/instruments-info", params=params, timeout=20)
        except Exception:
            break
        if resp.status_code != 200:
            break
        try:
            data = resp.json()
        except Exception:
            break
        if data.get("retCode") != 0:
            break
        result = data.get("result") or {}
        items = result.get("list") or []
        for item in items:
            symbol = item.get("symbol")
            if not symbol or not symbol.endswith("USDT"):
                continue
            symbols.append(symbol.replace("USDT", "").upper())
        cursor = result.get("nextPageCursor") or ""
        if not cursor:
            break
    return symbols


def _fetch_bitget_symbols() -> List[str]:
    symbols: List[str] = []
    try:
        resp = requests.get("https://api.bitget.com/api/spot/v1/public/products", timeout=20)
    except Exception:
        return symbols
    if resp.status_code != 200:
        return symbols
    try:
        data = resp.json()
    except Exception:
        return symbols
    if data.get("code") not in ("00000", 0, "0", None):
        return symbols
    for item in data.get("data") or []:
        sym = item.get("symbolName") or item.get("symbol") or ""
        if not sym or not sym.endswith("USDT"):
            continue
        symbols.append(sym.replace("USDT", "").upper())
    return symbols


def _load_exchange_symbols(exchange: str, ttl_hours: int) -> Optional[set]:
    cached = _load_symbol_cache(exchange, ttl_hours)
    if cached:
        return cached
    if exchange == "bybit":
        symbols = _fetch_bybit_symbols()
    elif exchange == "bitget":
        symbols = _fetch_bitget_symbols()
    elif exchange == "gate":
        symbols = _fetch_gate_symbols()
    else:
        symbols = []
    if symbols:
        _save_symbol_cache(exchange, symbols)
        return set(symbols)
    return None


def get_top_coins(
    limit: int,
    rank_by: str = 'volume',
    gate_only: bool = False,
    include_movers: bool = True,
    movers_count: int = MOVERS_COUNT,
) -> List[str]:
    rank_by = (rank_by or 'volume').lower()
    LAST_TOP_META.update({
        'requested': [],
        'returned': [],
        'not_on_gate': [],
        'gate_symbols_empty': False,
        'gate_filter': False,
        'movers_added': [],
        'movers_gainers': [],
        'movers_losers': [],
        'velo_gainers': [],
        'velo_added': [],
    })

    if rank_by == 'marketcap':
        symbols = []
        movers_gainers: List[str] = []
        movers_losers: List[str] = []
        velo_gainers: List[str] = []
        if gate_only:
            tickers = _fetch_gate_tickers()
            gate_symbols = set(
                [t['currency_pair'].replace('_USDT', '').upper()
                 for t in tickers if t.get('currency_pair', '').endswith('_USDT')]
            ) if tickers else set()
            not_on_gate = []
            gate_symbols_empty = not gate_symbols
            for symbol in FIXED_MARKETCAP[:max(1, limit)]:
                if _is_excluded_symbol(symbol):
                    continue
                if gate_symbols and symbol not in gate_symbols:
                    not_on_gate.append(symbol)
                    continue
                symbols.append(symbol)
                if len(symbols) >= limit:
                    break
            if include_movers and tickers:
                movers_gainers, movers_losers = _select_top_movers(tickers, movers_count)
                for sym in movers_gainers + movers_losers:
                    if sym in symbols or _is_excluded_symbol(sym):
                        continue
                    if gate_symbols and sym not in gate_symbols:
                        continue
                    symbols.append(sym)
            if include_movers:
                velo_gainers = _fetch_velo_top_gainers(movers_count, gate_symbols if gate_symbols else None)
                for sym in velo_gainers:
                    if sym in symbols or _is_excluded_symbol(sym):
                        continue
                    if gate_symbols and sym not in gate_symbols:
                        continue
                    symbols.append(sym)
            LAST_TOP_META.update({
                'requested': FIXED_MARKETCAP[:max(1, limit)],
                'returned': symbols,
                'not_on_gate': not_on_gate,
                'gate_symbols_empty': gate_symbols_empty,
                'gate_filter': True,
                'movers_added': [s for s in movers_gainers + movers_losers if s in symbols],
                'movers_gainers': movers_gainers,
                'movers_losers': movers_losers,
                'velo_gainers': velo_gainers,
                'velo_added': [s for s in velo_gainers if s in symbols],
            })
            if symbols:
                return symbols
            return FIXED_MARKETCAP[:min(limit, len(FIXED_MARKETCAP))]

        for symbol in FIXED_MARKETCAP[:max(1, limit)]:
            if _is_excluded_symbol(symbol):
                continue
            symbols.append(symbol)
            if len(symbols) >= limit:
                break
        movers_gainers, movers_losers = ([], [])
        velo_gainers = []
        if include_movers:
            tickers = _fetch_gate_tickers()
            movers_gainers, movers_losers = _select_top_movers(tickers, movers_count) if tickers else ([], [])
            for sym in movers_gainers + movers_losers:
                if sym in symbols or _is_excluded_symbol(sym):
                    continue
                symbols.append(sym)
            velo_gainers = _fetch_velo_top_gainers(movers_count)
            for sym in velo_gainers:
                if sym in symbols or _is_excluded_symbol(sym):
                    continue
                symbols.append(sym)
        LAST_TOP_META.update({
            'requested': FIXED_MARKETCAP[:max(1, limit)],
            'returned': symbols,
            'not_on_gate': [],
            'gate_symbols_empty': False,
            'gate_filter': False,
            'movers_added': [s for s in movers_gainers + movers_losers if s in symbols],
            'movers_gainers': movers_gainers,
            'movers_losers': movers_losers,
            'velo_gainers': velo_gainers,
            'velo_added': [s for s in velo_gainers if s in symbols],
        })
        return symbols

    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        movers_gainers, movers_losers = ([], [])
        velo_gainers = []
        usdt_pairs = [t for t in data if t.get('currency_pair', '').endswith('_USDT')]
        usdt_pairs.sort(key=lambda x: float(x.get('quote_volume', 0)), reverse=True)
        symbols = []
        for pair in usdt_pairs:
            symbol = pair['currency_pair'].replace('_USDT', '').upper()
            if _is_excluded_symbol(symbol):
                continue
            symbols.append(symbol)
            if len(symbols) >= limit:
                break
        if include_movers:
            movers_gainers, movers_losers = _select_top_movers(data, movers_count)
            for sym in movers_gainers + movers_losers:
                if sym in symbols or _is_excluded_symbol(sym):
                    continue
                symbols.append(sym)
            gate_symbols = set(symbols)
            velo_gainers = _fetch_velo_top_gainers(movers_count, gate_symbols if gate_symbols else None)
            for sym in velo_gainers:
                if sym in symbols or _is_excluded_symbol(sym):
                    continue
                symbols.append(sym)
        LAST_TOP_META.update({
            'requested': symbols[:max(1, limit)],
            'returned': symbols,
            'not_on_gate': [],
            'gate_symbols_empty': False,
            'gate_filter': False,
            'movers_added': [s for s in movers_gainers + movers_losers if s in symbols],
            'movers_gainers': movers_gainers,
            'movers_losers': movers_losers,
            'velo_gainers': velo_gainers,
            'velo_added': [s for s in velo_gainers if s in symbols],
        })
        return symbols
    except Exception:
        return []


CACHE_LOCK = threading.Lock()
_CACHE_BY_EXCHANGE = {ex: MarketDataCache(default_exchange=ex) for ex in EXCHANGES}
CACHE_STATS = {
    'calls': 0,
    'fetched': 0,
    'inserted': 0,
    'requests': 0,
    'elapsed_ms': 0,
    'errors': 0,
    'last_error': None,
    'sources': {},
}


def get_kline_exchange(symbol: str, timeframe: str, limit: int, exchange: str) -> List[Dict]:
    exchange = (exchange or 'gate').lower()
    cache = _CACHE_BY_EXCHANGE.get(exchange) or _CACHE_BY_EXCHANGE.get('gate')
    if cache is None:
        return []
    try:
        klines, stats = cache.get_klines(symbol, timeframe, limit, exchange=exchange)
        with CACHE_LOCK:
            CACHE_STATS['calls'] += 1
            CACHE_STATS['fetched'] += stats.fetched
            CACHE_STATS['inserted'] += stats.inserted
            CACHE_STATS['requests'] += stats.requests
            CACHE_STATS['elapsed_ms'] += stats.elapsed_ms
            CACHE_STATS['errors'] += stats.errors
            if stats.last_error:
                CACHE_STATS['last_error'] = stats.last_error
            CACHE_STATS['sources'][stats.source] = CACHE_STATS['sources'].get(stats.source, 0) + 1
        return klines
    except Exception:
        with CACHE_LOCK:
            CACHE_STATS['errors'] += 1
            CACHE_STATS['last_error'] = 'cache_exception'
        return []


def split_symbols(
    symbols: List[str],
    exchanges: Tuple[str, ...],
    availability: Optional[Dict[str, Optional[set]]] = None,
) -> Dict[str, List[str]]:
    groups: Dict[str, List[str]] = {ex: [] for ex in exchanges}
    counts: Dict[str, int] = {ex: 0 for ex in exchanges}
    if not exchanges:
        return groups

    for sym in symbols:
        candidates: List[str] = []
        if availability:
            for ex in exchanges:
                ex_set = availability.get(ex)
                if ex_set is None:
                    candidates.append(ex)
                elif sym in ex_set:
                    candidates.append(ex)
            if not candidates and 'gate' in exchanges:
                candidates = ['gate']
        if not candidates:
            candidates = list(exchanges)

        min_count = min(counts.get(k, 0) for k in candidates)
        tied = [k for k in candidates if counts.get(k, 0) == min_count]
        if len(tied) > 1:
            ex = tied[abs(hash(sym)) % len(tied)]
        else:
            ex = tied[0]
        groups[ex].append(sym)
        counts[ex] = counts.get(ex, 0) + 1
    return groups


def _fetch_group_data(
    exchange: str,
    symbols: List[str],
    timeframe: str,
    limit: int,
    limit_1h: int,
    fallback_exchange: Optional[str] = None,
) -> Dict[str, Dict[str, object]]:
    data: Dict[str, Dict[str, object]] = {}
    for sym in symbols:
        assigned = exchange
        used = exchange
        kl = get_kline_exchange(sym, timeframe, limit, exchange)
        if (not kl or len(kl) < 50) and fallback_exchange and exchange != fallback_exchange:
            alt = get_kline_exchange(sym, timeframe, limit, fallback_exchange)
            if alt and len(alt) >= 50:
                kl = alt
                used = fallback_exchange
        k1h = get_kline_exchange(sym, '1h', limit_1h, used) if kl and len(kl) >= 50 else []
        data[sym] = {
            'assigned': assigned,
            'used': used,
            'klines': kl,
            'k1h': k1h,
        }
    return data


def _build_pattern_type(candidate: Dict) -> str:
    base = (candidate.get('pattern') or '').strip()
    if not base:
        return 'unknown'
    mapped = PATTERN_TYPE_MAP.get(base, base)
    mapped = str(mapped).strip().lower().replace(' ', '_')
    direction = (candidate.get('type') or '').lower()
    if mapped == 'breakout':
        if direction == 'long':
            return 'bull_breakout'
        if direction == 'short':
            return 'bear_breakout'
    return mapped or base.lower().replace(' ', '_')


def maybe_run_pattern_audit(
    output_dir: Path,
    period_hours: int,
    since_days: int,
    min_confidence: float,
    max_duplicates: int,
    max_unused: int,
) -> Optional[Path]:
    if not AUDIT_AVAILABLE or period_hours <= 0:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp_path = output_dir / ".abu_pattern_audit_last.json"
    now_ts = time.time()
    last_ts = 0.0
    if stamp_path.exists():
        try:
            data = json.loads(stamp_path.read_text(encoding="utf-8"))
            last_ts = float(data.get("last_ts") or 0.0)
        except Exception:
            last_ts = 0.0
    if last_ts and (now_ts - last_ts) < period_hours * 3600:
        return None

    report = run_pattern_audit(
        trader_id="abu",
        output_dir=output_dir,
        since_days=since_days,
        min_confidence=min_confidence,
        max_duplicates=max_duplicates,
        max_unused=max_unused,
    )
    if report:
        stamp_payload = {
            "last_ts": now_ts,
            "last_run": datetime.now().isoformat(),
            "period_hours": period_hours,
        }
        stamp_path.write_text(json.dumps(stamp_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return report


def build_query_features(candidate: Dict, features: Dict[str, object], pattern_type: Optional[str] = None) -> Dict[str, object]:
    trend_strength = float(features.get('trend_strength') or 0.0)
    volatility = float(features.get('volatility') or 0.0)
    return {
        'pattern_type': pattern_type or _build_pattern_type(candidate),
        'direction': candidate.get('type') or 'neutral',
        'kline_features': features.get('kline_features') or [],
        'trend': features.get('trend_direction') or 'neutral',
        'market_conditions': {
            'trend_strength': 'strong' if trend_strength >= 0.02 else 'weak',
            'volatility': 'high' if volatility >= 0.01 else 'low',
            'trend_direction': features.get('trend_direction') or 'neutral'
        }
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
    if (brooks_status or '').lower() == 'pass':
        base += 0.05

    trend_dir = (features.get('trend_direction') or '').lower()
    direction = (candidate.get('type') or '').lower()
    if trend_dir == 'bullish' and direction == 'long':
        base += 0.05
    elif trend_dir == 'bearish' and direction == 'short':
        base += 0.05
    elif trend_dir in ('bullish', 'bearish'):
        base -= 0.05

    entry = float(candidate.get('entry') or 0.0)
    stop = float(candidate.get('stop_loss') or 0.0)
    tp1 = float(candidate.get('take_profit_1') or 0.0)
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


def _calc_atr(klines: List[Dict], period: int = 14) -> float:
    if not klines or len(klines) < 2:
        return 0.0
    recent = klines[-(period + 1):] if len(klines) > period else klines
    trs: List[float] = []
    for i in range(1, len(recent)):
        prev = recent[i - 1]
        cur = recent[i]
        high = float(cur.get('high', 0.0))
        low = float(cur.get('low', 0.0))
        prev_close = float(prev.get('close', 0.0))
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    if not trs:
        return 0.0
    return sum(trs) / len(trs)


def _structure_stop(
    klines: List[Dict],
    direction: str,
    lookback: int,
    atr: float,
) -> float:
    if not klines:
        return 0.0
    window = klines[-lookback:] if len(klines) > lookback else klines
    if not window:
        return 0.0
    if direction == 'long':
        low = min(float(k.get('low', 0.0)) for k in window)
        return max(0.0, low - atr * ATR_BUFFER_MULT)
    high = max(float(k.get('high', 0.0)) for k in window)
    return high + atr * ATR_BUFFER_MULT


def _adjust_stop_with_rules(
    cand: Dict,
    timeframe: str,
    klines: List[Dict],
    features: Dict[str, object],
) -> Optional[bool]:
    entry = float(cand.get('entry') or 0.0)
    stop = float(cand.get('stop_loss') or 0.0)
    if entry <= 0 or stop <= 0:
        return False
    min_stop = MIN_STOP_PCT.get(timeframe, 0.0)
    direction = (cand.get('type') or 'long').lower()
    trend_dir = str(features.get('trend_direction') or '').lower()
    countertrend = trend_dir in ('bullish', 'bearish') and (
        (trend_dir == 'bullish' and direction == 'short') or (trend_dir == 'bearish' and direction == 'long')
    )
    atr = _calc_atr(klines, period=14)
    atr_pct = (atr / entry) if entry > 0 else 0.0
    k_map = ATR_K_COUNTER if countertrend else ATR_K_TREND
    if isinstance(k_map, dict):
        k = float(k_map.get(timeframe, next(iter(k_map.values()))))
    else:
        k = float(k_map)
    min_stop_pct = max(min_stop, atr_pct * k)
    stop_by_pct = entry * (1 - min_stop_pct) if direction == 'long' else entry * (1 + min_stop_pct)
    struct_stop = _structure_stop(klines, direction, STOP_LOOKBACK.get(timeframe, 20), atr)
    if direction == 'long':
        target_stop = min([s for s in (stop_by_pct, struct_stop) if s > 0], default=stop_by_pct)
        if stop <= target_stop:
            return None
    else:
        target_stop = max([s for s in (stop_by_pct, struct_stop) if s > 0], default=stop_by_pct)
        if stop >= target_stop:
            return None

    stop = target_stop
    if direction == 'long':
        if stop >= entry:
            return False
        risk = entry - stop
        tp1 = entry + risk
        tp2 = entry + 2 * risk
    else:
        if stop <= entry:
            return False
        risk = stop - entry
        tp1 = entry - risk
        tp2 = entry - 2 * risk

    cand['stop_loss'] = float(stop)
    cand['take_profit_1'] = float(tp1)
    cand['take_profit_2'] = float(tp2) if tp2 is not None else None
    cand['_stop_adjusted'] = True
    reason = (cand.get('reason') or '').strip()
    cand['reason'] = f"{reason} | 结构止损" if reason else "结构止损"
    return True


def _is_valid_trade(cand: Dict, timeframe: str, klines: List[Dict], features: Dict[str, object]) -> bool:
    entry = float(cand.get('entry') or 0.0)
    stop = float(cand.get('stop_loss') or 0.0)
    tp1 = float(cand.get('take_profit_1') or 0.0)
    tp2_raw = cand.get('take_profit_2')
    tp2 = float(tp2_raw) if tp2_raw not in (None, '') else 0.0
    tp2_present = tp2 > 0
    if entry <= 0 or stop <= 0 or tp1 <= 0:
        return False
    direction = (cand.get('type') or 'long').lower()
    if direction == 'long':
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
        cand['take_profit_2'] = None
    trend_dir = str(features.get('trend_direction') or '').lower()
    countertrend = trend_dir in ('bullish', 'bearish') and (
        (trend_dir == 'bullish' and direction == 'short') or (trend_dir == 'bearish' and direction == 'long')
    )
    adjusted = _adjust_stop_with_rules(cand, timeframe, klines, features)
    if adjusted is False:
        return False
    if adjusted:
        entry = float(cand.get('entry') or 0.0)
        stop = float(cand.get('stop_loss') or 0.0)
        tp1 = float(cand.get('take_profit_1') or 0.0)
        tp2_raw = cand.get('take_profit_2')
        tp2 = float(tp2_raw) if tp2_raw not in (None, '') else 0.0
        tp2_present = tp2 > 0
        direction = (cand.get('type') or 'long').lower()
        if direction == 'long':
            if stop >= entry or tp1 <= entry:
                return False
            if tp2_present and tp2 <= tp1:
                return False
        else:
            if stop <= entry or tp1 >= entry:
                return False
            if tp2_present and tp2 >= tp1:
                return False
    if countertrend and cand.get('take_profit_2'):
        cand['take_profit_2'] = None
        reason = (cand.get('reason') or '').strip()
        cand['reason'] = f"{reason} | 逆势仅TP1" if reason else "逆势仅TP1"
    return True


def _pattern_type_candidates(candidate: Dict, features: Dict[str, object]) -> List[str]:
    base = (candidate.get('pattern') or '').strip().lower()
    direction = (candidate.get('type') or '').lower()
    candidates = []
    if base in ('insidebar', 'inside bar'):
        if direction == 'long':
            candidates.append('bull_breakout')
        elif direction == 'short':
            candidates.append('bear_breakout')
        candidates.append('breakout')
    elif base in ('engulfing', 'pinbar', 'pin bar'):
        candidates.extend(['reversal', 'major_trend_reversal'])
    elif base == 'keylevel':
        candidates.append('trading_range')
    if features.get('range_mode'):
        candidates.append('trading_range')
    if features.get('double_top'):
        candidates.append('double_top')
    if features.get('double_bottom'):
        candidates.append('double_bottom')
    return list(dict.fromkeys([c for c in candidates if c]))


def _relaxation_notes(rulebook: BestPracticeRulebook, candidate: Dict, features: Dict[str, object], pattern_type: Optional[str]) -> List[str]:
    rules = (rulebook.config or {}).get('rules', {}) if rulebook else {}
    notes: List[str] = []
    direction = (candidate.get('type') or '').lower()
    trend_dir = (features.get('trend_direction') or '').lower()
    trend_strength = float(features.get('trend_strength') or 0.0)
    strong_threshold = float(rules.get('strong_trend_threshold') or 0.0)

    if rules.get('allow_against_trend') and trend_strength >= strong_threshold:
        if (trend_dir == 'bullish' and direction == 'short') or (trend_dir == 'bearish' and direction == 'long'):
            notes.append('逆势放宽')

    if not rules.get('require_breakout_confirmation', False):
        ptype = str(pattern_type or '').lower()
        if 'breakout' in ptype:
            breakout_up = bool(features.get('breakout_up'))
            breakout_down = bool(features.get('breakout_down'))
            if direction == 'long' and not breakout_up:
                notes.append('突破未确认放宽')
            elif direction == 'short' and not breakout_down:
                notes.append('突破未确认放宽')

    range_mode = bool(features.get('range_mode'))
    range_only = [str(x).lower() for x in (rules.get('range_mode_only_patterns') or [])]
    if range_mode and not range_only:
        notes.append('震荡过滤放宽')

    avoid_trend = [str(x).lower() for x in (rules.get('trend_mode_avoid_patterns') or [])]
    norm_type = _normalize_pattern_type(pattern_type)
    if (not range_mode) and norm_type == 'trading_range' and not avoid_trend:
        notes.append('趋势过滤放宽')

    pattern_score = candidate.get('_pattern_score')
    min_pattern = rules.get('min_pattern_score')
    try:
        if pattern_score is not None and min_pattern is not None:
            if float(min_pattern) < 0.2 and float(pattern_score) < 0.2:
                notes.append('匹配阈值放宽')
    except Exception:
        pass

    brooks_score = candidate.get('_brooks_score')
    min_brooks = rules.get('min_brooks_score')
    try:
        if brooks_score is not None and min_brooks is not None:
            if float(min_brooks) < 0.2 and float(brooks_score) < 0.2:
                notes.append('Brooks阈值放宽')
    except Exception:
        pass

    min_rr = rules.get('min_rr')
    try:
        if min_rr is not None and float(min_rr) < 1.0:
            entry = float(candidate.get('entry') or 0.0)
            stop = float(candidate.get('stop_loss') or 0.0)
            tp1 = float(candidate.get('take_profit_1') or 0.0)
            risk = abs(entry - stop)
            rr1 = abs(tp1 - entry) / risk if risk > 0 else 0.0
            if rr1 < 1.0:
                notes.append('RR阈值放宽')
    except Exception:
        pass

    return notes


def score_with_pattern_library(
    pattern_library,
    query_features: Dict,
    candidate_types: List[str]
) -> Tuple[float, Optional[str], float, Optional[str], Optional[str], Optional[object], Optional[str]]:
    best_score = 0.0
    best_name = None
    best_brooks = 0.0
    best_pattern_id = None
    best_image_path = None
    best_page = None
    best_source = None
    types_to_try = candidate_types or [query_features.get('pattern_type') or '']

    for ptype in types_to_try:
        if not ptype:
            continue
        q = dict(query_features)
        q['pattern_type'] = ptype
        try:
            matches = pattern_library.search_patterns(
                query_features=q,
                sources=PATTERN_SOURCES,
                top_k=5,
                min_confidence=0.2
            )
        except Exception:
            continue

        if not matches:
            continue

        weight_sum = sum(m.get('weight', 0.0) for m in matches) or 1.0
        score = sum((m.get('similarity', 0.0) * m.get('weight', 0.0)) for m in matches) / weight_sum

        name = None
        pattern_id = None
        image_path = None
        page_number = None
        source = None
        if matches:
            top_match = matches[0]
            pattern = top_match.get('pattern') or {}
            name = pattern.get('pattern_name')
            pattern_id = top_match.get('pattern_id')
            image_path = pattern.get('image_path')
            page_number = pattern.get('page_number')
            source = top_match.get('source')

        brooks_score = max((m.get('similarity', 0.0) for m in matches if m.get('source') == 'brooks_rule'), default=0.0)

        if score > best_score:
            best_score = score
            best_name = name
            best_brooks = brooks_score
            best_pattern_id = pattern_id
            best_image_path = image_path
            best_page = page_number
            best_source = source

    return best_score, best_name, best_brooks, best_pattern_id, best_image_path, best_page, best_source


def main() -> None:
    ap = argparse.ArgumentParser(description='Qingniao-PA Top scanner (Gate/Bybit/Bitget)')
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--timeframe', type=str, default='15m', choices=['5m', '15m', '1h'])
    ap.add_argument('--rank-by', type=str, default='volume', choices=['volume', 'marketcap'])
    ap.add_argument('--days', type=int, default=None)
    ap.add_argument('--write-db', type=int, default=1)
    ap.add_argument('--exchange-mode', type=str, default='split', choices=['gate', 'bybit', 'bitget', 'split'])
    ap.add_argument('--exchange-fallback', type=int, default=1, choices=[0, 1])
    ap.add_argument('--audit-period-hours', type=int, default=0)
    ap.add_argument('--audit-since-days', type=int, default=30)
    ap.add_argument('--audit-min-confidence', type=float, default=0.3)
    ap.add_argument('--audit-max-duplicates', type=int, default=20)
    ap.add_argument('--audit-max-unused', type=int, default=50)
    ap.add_argument('--context-filter', type=str, default='off', choices=['off', 'brooks', 'regime36', 'both'])
    args = ap.parse_args()

    scan_start = time.time()
    days = args.days if args.days is not None else DEFAULT_DAYS.get(args.timeframe, 7)
    print(f"[INFO] timeframe={args.timeframe} days={days} (建议: 5m=3-5天, 15m=10-14天, 1h=30-60天)")
    limit = min(1000, KLINES_PER_DAY.get(args.timeframe, 96) * max(days, 1))

    gate_only = args.exchange_mode == 'gate'
    if args.rank_by == 'marketcap':
        symbols = get_top_coins(len(FIXED_MARKETCAP), rank_by=args.rank_by, gate_only=gate_only)
    else:
        symbols = get_top_coins(max(args.top, 10), rank_by=args.rank_by, gate_only=gate_only)
    if not symbols:
        return

    pattern_library = None
    pattern_stats: Optional[Dict[str, int]] = None
    if PATTERN_LIB_AVAILABLE:
        try:
            pattern_library = UnifiedPatternLibrary('abu')
            load_gemini = any(str(s).startswith('gemini') for s in PATTERN_SOURCES)
            load_cursor = any(str(s) == 'cursor_ai' for s in PATTERN_SOURCES)
            load_brooks = 'brooks_rule' in PATTERN_SOURCES
            pattern_stats = pattern_library.load_all_patterns(
                load_gemini=load_gemini,
                load_cursor_ai=load_cursor,
                load_brooks=load_brooks,
            )
        except Exception:
            pattern_library = None
            pattern_stats = None

    constraints = BrooksPatternConstraints() if USE_BROOKS_RULES else None
    rulebook = BestPracticeRulebook()
    prob_estimator = SignalProbabilityEstimator()
    context_filter_mode = (args.context_filter or 'off').lower()

    exchange_mode = args.exchange_mode.lower()
    fallback_exchange = 'gate' if args.exchange_fallback and exchange_mode == 'split' else None
    symbol_data: Dict[str, Dict[str, object]] = {}
    assigned_counts: Dict[str, int] = {}
    if exchange_mode == 'split':
        active_exchanges = [ex for ex in EXCHANGES if _check_exchange_health(ex)]
        if 'gate' not in active_exchanges:
            active_exchanges.insert(0, 'gate')
        availability: Dict[str, Optional[set]] = {ex: None for ex in active_exchanges}
        if 'bybit' in availability:
            availability['bybit'] = _load_exchange_symbols('bybit', SYMBOL_CACHE_TTL_HOURS)
        if 'bitget' in availability:
            availability['bitget'] = _load_exchange_symbols('bitget', SYMBOL_CACHE_TTL_HOURS)
        groups = split_symbols(symbols, tuple(active_exchanges), availability=availability)
        assigned_counts = {ex: len(groups.get(ex, [])) for ex in active_exchanges}
        groups = {ex: syms for ex, syms in groups.items() if syms}
        max_workers = max(1, len(groups))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(_fetch_group_data, ex, syms, args.timeframe, limit, 240, fallback_exchange)
                for ex, syms in groups.items()
            ]
            for fut in as_completed(futures):
                symbol_data.update(fut.result())
    else:
        assigned_counts = {exchange_mode: len(symbols)}
        symbol_data = _fetch_group_data(exchange_mode, symbols, args.timeframe, limit, 240, None)

    results: List[Dict] = []
    skip_reasons: Dict[str, set] = {}
    adjusted_stop_count = 0
    gemini_match_count = 0
    gemini_match_set: set = set()
    for sym in symbols:
        payload = symbol_data.get(sym) or {}
        kl = payload.get('klines') if isinstance(payload.get('klines'), list) else []
        k1h = payload.get('k1h') if isinstance(payload.get('k1h'), list) else []
        assigned_exchange = str(payload.get('assigned') or exchange_mode)
        if not kl or len(kl) < 50:
            skip_reasons.setdefault(sym, set()).add(f'K线不足或缺失({assigned_exchange})')
            continue

        if args.timeframe == '1h':
            candidates = detect_all_1h(kl)
        else:
            candidates = detect_all_15m(kl)
        if not candidates:
            skip_reasons.setdefault(sym, set()).add('无候选形态')
            continue

        features = extract_basic_kline_features(kl)
        if not features:
            skip_reasons.setdefault(sym, set()).add('特征提取失败')
            continue
        context_info = classify_market_context(kl, features)
        features['market_context'] = context_info.get('context')
        features['regime_36'] = context_info.get('regime_36')
        features['regime_36_components'] = context_info.get('regime_36_components')

        has_signal = False
        for cand in candidates:
            if not cand.get('entry') or not cand.get('stop_loss') or not cand.get('take_profit_1'):
                skip_reasons.setdefault(sym, set()).add('缺少交易字段')
                continue
            if not _is_valid_trade(cand, args.timeframe, kl, features):
                skip_reasons.setdefault(sym, set()).add('止损/目标不合法')
                continue

            query_features = build_query_features(cand, features)
            if context_filter_mode != 'off':
                filter_reason = context_filter_reason(
                    context_info,
                    query_features.get('pattern_type'),
                    cand.get('type'),
                    context_filter_mode,
                )
                if filter_reason:
                    skip_reasons.setdefault(sym, set()).add(filter_reason)
                    continue
            pattern_candidates = _pattern_type_candidates(cand, features)
            pattern_score = 0.0
            best_match = None
            brooks_score = 0.0
            best_pattern_id = None
            best_image_path = None
            best_page = None
            best_source = None
            if pattern_library is not None:
                pattern_score, best_match, brooks_score, best_pattern_id, best_image_path, best_page, best_source = score_with_pattern_library(
                    pattern_library,
                    query_features,
                    pattern_candidates
                )
                if best_match:
                    gemini_match_count += 1
                    gemini_match_set.add(best_match)
                    mismatch_reason = context_mismatch(context_info, best_match, cand.get('type'))
                    if mismatch_reason:
                        skip_reasons.setdefault(sym, set()).add(mismatch_reason)
                        continue
            if not USE_BROOKS_RULES:
                brooks_score = None

            base_pattern = cand.get('pattern') or ''
            hint = PATTERN_RULE_HINTS.get(base_pattern, '')
            if best_match:
                pattern_key = best_match
            elif hint:
                pattern_key = f"{base_pattern} {hint}"
            else:
                pattern_key = base_pattern

            constraint = ConstraintResult(status='warn', score_adjust=0.0, reasons=['brooks_disabled'], rule_name=None)
            if USE_BROOKS_RULES and constraints is not None:
                rule_cfg = (rulebook.config or {}).get('rules', {})
                allowed_status = [str(x).lower() for x in (rule_cfg.get('allowed_brooks_status') or [])]
                allow_brooks_fail = 'fail' in allowed_status

                constraint = constraints.evaluate(features, pattern_key, direction=cand.get('type'))
                if constraint.status == 'fail' and not allow_brooks_fail:
                    skip_reasons.setdefault(sym, set()).add('Brooks约束失败')
                    continue
                if constraint.status == 'fail' and allow_brooks_fail:
                    reason = (cand.get('reason') or '').strip()
                    cand['reason'] = f"{reason} | Brooks约束放宽" if reason else "Brooks约束放宽"

            rule_result = rulebook.evaluate(
                cand,
                features,
                pattern_type=query_features.get('pattern_type'),
                pattern_score=pattern_score if pattern_library is not None else None,
                brooks_score=brooks_score,
                brooks_status=constraint.status,
                pattern_match=best_match,
            )
            if not rule_result.passed:
                reason = '最佳实践过滤'
                if rule_result.reasons:
                    reason = f"{reason}({';'.join(rule_result.reasons)})"
                skip_reasons.setdefault(sym, set()).add(reason)
                continue

            relax_notes = _relaxation_notes(rulebook, cand, features, query_features.get('pattern_type'))
            if relax_notes:
                reason = (cand.get('reason') or '').strip()
                note = " / ".join(relax_notes)
                cand['reason'] = f"{reason} | {note}" if reason else note
            context_label = context_info.get('label')
            if context_label:
                reason = (cand.get('reason') or '').strip()
                cand['reason'] = f"{reason} | Context={context_label}" if reason else f"Context={context_label}"
            regime_label = context_info.get('regime')
            if regime_label:
                reason = (cand.get('reason') or '').strip()
                cand['reason'] = f"{reason} | Regime={regime_label}" if reason else f"Regime={regime_label}"
            regime_36_label = context_info.get('regime_36')
            if regime_36_label:
                reason = (cand.get('reason') or '').strip()
                cand['reason'] = f"{reason} | Regime36={regime_36_label}" if reason else f"Regime36={regime_36_label}"

            entry_model = f"PA/{base_pattern}" if base_pattern else None
            empirical = prob_estimator.estimate(sym, args.timeframe, entry_model=entry_model)
            prob_tp1, prob_tp2, prob_sl, prob_source, prob_samples = estimate_probabilities(
                cand,
                features,
                pattern_score if pattern_library is not None else None,
                brooks_score,
                constraint.status,
                empirical,
            )

            base_score = score_candidate(cand, k1h)
            ema_penalty, ema_note = _ema_deviation_penalty(cand, features, context_info, args.timeframe)
            if ema_note:
                reason = (cand.get('reason') or '').strip()
                cand['reason'] = f"{reason} | {ema_note}" if reason else ema_note
            final_score = base_score + (pattern_score * 0.6) + constraint.score_adjust - ema_penalty

            enriched = dict(cand)
            enriched['_score'] = final_score
            enriched['_pattern_score'] = pattern_score
            enriched['_brooks_score'] = brooks_score
            enriched['_brooks_status'] = constraint.status
            enriched['_brooks_rule'] = constraint.rule_name
            enriched['_brooks_reasons'] = ';'.join(constraint.reasons)
            enriched['_ema_penalty'] = ema_penalty
            enriched['_pattern_match'] = best_match
            enriched['_pattern_match_id'] = best_pattern_id
            enriched['_pattern_match_image'] = best_image_path
            enriched['_pattern_match_page'] = best_page
            enriched['_pattern_match_source'] = best_source
            enriched['_prob_tp1'] = prob_tp1
            enriched['_prob_tp2'] = prob_tp2
            enriched['_prob_sl'] = prob_sl
            enriched['_prob_source'] = prob_source
            enriched['_prob_samples'] = prob_samples
            enriched['symbol'] = sym
            enriched['timeframe'] = args.timeframe
            if cand.get('_stop_adjusted'):
                adjusted_stop_count += 1
            results.append(enriched)
            has_signal = True

        if has_signal and sym in skip_reasons:
            skip_reasons.pop(sym, None)
        elif not has_signal:
            skip_reasons.setdefault(sym, set()).add('无有效信号')

    if results:
        results.sort(key=lambda x: x.get('_score', 0), reverse=True)
    top = results[:args.top] if results else []

    if args.write_db and top:
        db = TraderDBManager('abu')
        for r in top:
            try:
                notes = r.get('reason') or ''
                brooks_note = f"Brooks:{r.get('_brooks_status')}" if r.get('_brooks_status') else ''
                if brooks_note:
                    notes = f"{notes} {brooks_note}".strip()
                if r.get('_pattern_match'):
                    notes = f"{notes} Match:{r.get('_pattern_match')}".strip()

                db.add_trading_signal(
                    {
                        "signal_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "timeframe": args.timeframe,
                        "signal_type": r['type'],
                        "symbol": r['symbol'],
                        "entry_price": r['entry'],
                        "stop_loss": r['stop_loss'],
                        "take_profit_1": r.get('take_profit_1'),
                        "take_profit_2": r.get('take_profit_2'),
                        "entry_model": f"PA/{r.get('pattern')}",
                        "strength": "medium",
                        "risk_reward_ratio": None,
                        "volatility_level": None,
                        "system_name": "abu",
                        "score": float(r.get('_score') or 0.0),
                        "notes": notes,
                        "status": "pending",
                    }
                )
            except Exception as exc:
                print(f"[WARN] 写库失败: {r.get('symbol')} {args.timeframe} {exc}", file=sys.stderr)
        db.close()

    output_dir = ROOT / 'outputs' / 'trading_signals'
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    context_suffix = ""
    if context_filter_mode != "off":
        context_suffix = f"_ctx-{context_filter_mode}"
    out = output_dir / f"ABU_top{args.top}_{args.timeframe}{context_suffix}_{timestamp}.md"

    used_counts: Dict[str, int] = {}
    fallback_count = 0
    for payload in symbol_data.values():
        kl = payload.get('klines')
        if not isinstance(kl, list) or len(kl) < 50:
            continue
        used = str(payload.get('used') or payload.get('assigned') or exchange_mode)
        used_counts[used] = used_counts.get(used, 0) + 1
        if payload.get('assigned') != payload.get('used'):
            fallback_count += 1

    lines = [
        f"# Abu Top{args.top} ({args.timeframe})",
        '',
    ]
    if context_filter_mode != "off":
        lines.append(f"- Context过滤: {context_filter_mode}")
        lines.append("")
    lines.extend([
        '| # | Symbol | Type | Entry | SL | TP1 | TP2 | P(TP1) | P(TP2) | P(SL) | Score | PatternScore | Brooks | Match | Source | PatternId | ImagePath | Page | Reason |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|'
    ])
    for i, r in enumerate(top, 1):
        match_source = r.get('_pattern_match_source') or '-'
        if match_source == 'gemini_flash':
            match_source = 'gemini'
        image_path = r.get('_pattern_match_image')
        image_path = str(image_path).replace('\n', ' ') if image_path else '-'
        match_id = r.get('_pattern_match_id') or '-'
        page = r.get('_pattern_match_page')
        page = str(page) if page not in (None, '') else '-'
        entry_fmt = _format_price(r.get('entry'))
        sl_fmt = _format_price(r.get('stop_loss'))
        tp1_fmt = _format_price(r.get('take_profit_1') if r.get('take_profit_1') is not None else 0.0)
        tp2_fmt = _format_price(r.get('take_profit_2') if r.get('take_profit_2') is not None else 0.0)
        lines.append(
            "| {idx} | {symbol} | {typ} | {entry} | {sl} | {tp1} | {tp2} | {p1} | {p2} | {psl} | {score:.2f} | {pscore:.2f} | {brooks} | {match} | {source} | {match_id} | {image_path} | {page} | {reason} |".format(
                idx=i,
                symbol=r['symbol'],
                typ=r['type'],
                entry=entry_fmt,
                sl=sl_fmt,
                tp1=tp1_fmt,
                tp2=tp2_fmt,
                p1=f"{float(r.get('_prob_tp1') or 0.0) * 100:.1f}%",
                p2=f"{float(r.get('_prob_tp2') or 0.0) * 100:.1f}%",
                psl=f"{float(r.get('_prob_sl') or 0.0) * 100:.1f}%",
                score=float(r.get('_score') or 0.0),
                pscore=float(r.get('_pattern_score') or 0.0),
                brooks=r.get('_brooks_status') or '-',
                match=r.get('_pattern_match') or '-',
                source=match_source,
                match_id=match_id,
                image_path=image_path,
                page=page,
                reason=(r.get('reason') or '').replace('\n', ' ')
            )
        )

    lines.append("")
    scan_elapsed = int(time.time() - scan_start)
    lines.append("## 跳过统计")
    lines.append(f"- 参与扫描: {len(symbols)}")
    if exchange_mode == 'split':
        assigned_line = ", ".join(f"{ex}={assigned_counts.get(ex, 0)}" for ex in EXCHANGES)
        used_line = ", ".join(f"{ex}={used_counts.get(ex, 0)}" for ex in EXCHANGES)
        lines.append(f"- 数据源分配: {assigned_line}")
        lines.append(f"- 实际使用: {used_line} (fallback->gate={fallback_count})")
        if EXCHANGE_HEALTH:
            health_line = ", ".join(
                f"{ex}={info.get('status')}" + (f"({info.get('error')})" if info.get('error') else "")
                for ex, info in EXCHANGE_HEALTH.items()
            )
            lines.append(f"- 交易所健康: {health_line}")
    else:
        lines.append(f"- 数据源: {exchange_mode}")
    lines.append("- 概率说明: P(TP2) 为条件概率（到达TP1后继续到TP2）")
    lines.append("- 概率来源: 优先使用反馈统计（signal_evaluations）；样本不足时与估算值加权")
    rule_flags = []
    rule_cfg = (rulebook.config or {}).get('rules', {})
    if rule_cfg.get('allow_against_trend'):
        rule_flags.append('允许逆势')
    if not rule_cfg.get('require_breakout_confirmation', False):
        rule_flags.append('取消突破确认')
    if USE_BROOKS_RULES:
        if 'fail' in [str(x).lower() for x in (rule_cfg.get('allowed_brooks_status') or [])]:
            rule_flags.append('Brooks约束放宽')
    else:
        rule_flags.append('Brooks禁用')
    if PATTERN_SOURCES == ['gemini_pro3']:
        rule_flags.append('仅Gemini Pro3模式')
    elif PATTERN_SOURCES == ['gemini_pro']:
        rule_flags.append('仅Gemini Pro模式')
    elif PATTERN_SOURCES == ['gemini_flash']:
        rule_flags.append('仅Gemini Flash模式')
    elif PATTERN_SOURCES and all(str(s).startswith('gemini') for s in PATTERN_SOURCES):
        rule_flags.append('仅Gemini模式')
    if rule_flags:
        lines.append(f"- 规则放宽: {', '.join(rule_flags)}")
    if PATTERN_SOURCES and any(str(s).startswith('gemini') for s in PATTERN_SOURCES):
        lines.append(f"- Gemini 模式实际匹配到的数量: {len(gemini_match_set)} (候选匹配次数={gemini_match_count})")
    if pattern_stats:
        lines.append(
            "- Gemini 模式库统计: "
            f"pro3={pattern_stats.get('gemini_pro3', 0)}, "
            f"pro={pattern_stats.get('gemini_pro', 0)}, "
            f"flash={pattern_stats.get('gemini_flash', 0)}, "
            f"total={pattern_stats.get('total', 0)}"
        )
    if CACHE_STATS['calls']:
        sources = ", ".join(f"{k}={v}" for k, v in CACHE_STATS['sources'].items())
        lines.append(
            f"- 缓存统计: 调用={CACHE_STATS['calls']} 拉取={CACHE_STATS['fetched']} 写入={CACHE_STATS['inserted']} 请求={CACHE_STATS['requests']} 耗时={CACHE_STATS['elapsed_ms']}ms 来源({sources})"
        )
        if CACHE_STATS['errors']:
            last_error = CACHE_STATS['last_error'] or '-'
            lines.append(f"- 缓存错误: {CACHE_STATS['errors']} (last={last_error})")
    lines.append(f"- 扫描耗时: {scan_elapsed}s")
    if adjusted_stop_count:
        lines.append(f"- 止损自动调整: {adjusted_stop_count}")
    if args.rank_by == 'marketcap' and LAST_TOP_META.get('gate_filter') and LAST_TOP_META.get('gate_symbols_empty'):
        lines.append("- Gate 列表获取失败，按固定币种直接扫描")
    not_on_gate = LAST_TOP_META.get('not_on_gate') or []
    if LAST_TOP_META.get('gate_filter') and not_on_gate:
        lines.append(f"- Gate 未上币: {', '.join(not_on_gate)}")
    movers_gainers = LAST_TOP_META.get('movers_gainers') or []
    movers_losers = LAST_TOP_META.get('movers_losers') or []
    if movers_gainers:
        lines.append(f"- 涨幅Top{MOVERS_COUNT}: {', '.join(movers_gainers)}")
    if movers_losers:
        lines.append(f"- 跌幅Top{MOVERS_COUNT}: {', '.join(movers_losers)}")
    velo_gainers = LAST_TOP_META.get('velo_gainers') or []
    if velo_gainers:
        lines.append(f"- Velo 1h涨幅Top{MOVERS_COUNT}: {', '.join(velo_gainers)}")
    if skip_reasons:
        reason_map: Dict[str, List[str]] = {}
        for sym, reasons in skip_reasons.items():
            for reason in reasons:
                reason_map.setdefault(reason, []).append(sym)
        for reason, syms in reason_map.items():
            lines.append(f"- {reason}: {', '.join(syms)}")
    else:
        lines.append("- 无")

    out.write_text('\n'.join(lines), encoding='utf-8')
    print('✓ Wrote:', out)

    audit_report = maybe_run_pattern_audit(
        output_dir,
        args.audit_period_hours,
        args.audit_since_days,
        args.audit_min_confidence,
        args.audit_max_duplicates,
        args.audit_max_unused,
    )
    if audit_report:
        print('✓ Audit wrote:', audit_report)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
