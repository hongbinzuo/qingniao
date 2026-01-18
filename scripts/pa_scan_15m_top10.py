#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qingniao-Abu Top10 PA scanner (Gate, 5m/15m)

- K-line numeric detectors produce trade_ready candidates
- Brooks constraints filter/score
- Unified pattern library (Gemini + Cursor + Brooks) provides alignment score
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import argparse
import requests

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.detectors import detect_all_15m  # type: ignore
from abu.ranker import score_candidate  # type: ignore
from abu.kline_feature_extractor import extract_basic_kline_features  # type: ignore
from abu.brooks_pattern_constraints import BrooksPatternConstraints  # type: ignore
from db_manager_trader import TraderDBManager  # type: ignore

try:
    from abu.unified_pattern_library import UnifiedPatternLibrary  # type: ignore
    PATTERN_LIB_AVAILABLE = True
except Exception:
    UnifiedPatternLibrary = None
    PATTERN_LIB_AVAILABLE = False

EXCL = set(['USDT', 'USDC', 'DAI', 'BUSD', 'FDUSD', 'TUSD', 'PYUSD', 'USDE', 'GUSD', 'EURT'])
KLINES_PER_DAY = {
    '5m': 288,
    '15m': 96,
    '1h': 24,
}
DEFAULT_DAYS = {
    '5m': 2,
    '15m': 7,
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
MIN_STOP_PCT = {'5m': 0.015, '15m': 0.015}


def _is_excluded_symbol(symbol: str) -> bool:
    sym = symbol.upper()
    if sym in EXCL:
        return True
    if sym.startswith(('USD', 'USDT', 'USDC')):
        return True
    if sym.endswith(LEVERAGED_SUFFIXES):
        return True
    return False


def get_top_coins(limit: int) -> List[str]:
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
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
        return symbols
    except Exception:
        return []


def get_kline_gateio(symbol: str, timeframe: str, limit: int) -> List[Dict]:
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h'}
        interval = tf_map.get(timeframe, '15m')
        pair = f"{symbol}_USDT"
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {'currency_pair': pair, 'interval': interval, 'limit': limit}
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            return []
        data = resp.json()
        if not data:
            return []
        data.reverse()
        klines = []
        for k in data:
            klines.append({
                'timestamp': int(k[0]),
                'open': float(k[5]),
                'high': float(k[3]),
                'low': float(k[4]),
                'close': float(k[2]),
                'volume': float(k[1])
            })
        return klines
    except Exception:
        return []


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


def _is_valid_trade(cand: Dict, timeframe: str) -> bool:
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
    min_stop = MIN_STOP_PCT.get(timeframe, 0.0)
    if min_stop > 0:
        stop_dist = abs(entry - stop) / entry
        if stop_dist < min_stop:
            return False
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


def score_with_pattern_library(pattern_library, query_features: Dict, candidate_types: List[str]) -> Tuple[float, Optional[str], float]:
    best_score = 0.0
    best_name = None
    best_brooks = 0.0
    types_to_try = candidate_types or [query_features.get('pattern_type') or '']

    for ptype in types_to_try:
        if not ptype:
            continue
        q = dict(query_features)
        q['pattern_type'] = ptype
        try:
            matches = pattern_library.search_patterns(
                query_features=q,
                sources=['gemini_flash', 'cursor_ai', 'brooks_rule'],
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
        if matches:
            pattern = matches[0].get('pattern') or {}
            name = pattern.get('pattern_name')

        brooks_score = max((m.get('similarity', 0.0) for m in matches if m.get('source') == 'brooks_rule'), default=0.0)

        if score > best_score:
            best_score = score
            best_name = name
            best_brooks = brooks_score

    return best_score, best_name, best_brooks


def main() -> None:
    ap = argparse.ArgumentParser(description='Qingniao-PA Top scanner (Gate)')
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--timeframe', type=str, default='15m', choices=['5m', '15m'])
    ap.add_argument('--days', type=int, default=None)
    ap.add_argument('--write-db', type=int, default=1)
    args = ap.parse_args()

    days = args.days if args.days is not None else DEFAULT_DAYS.get(args.timeframe, 7)
    limit = min(1000, KLINES_PER_DAY.get(args.timeframe, 96) * max(days, 1))

    symbols = get_top_coins(max(args.top, 10))
    if not symbols:
        return

    pattern_library = None
    if PATTERN_LIB_AVAILABLE:
        try:
            pattern_library = UnifiedPatternLibrary('abu')
            pattern_library.load_all_patterns()
        except Exception:
            pattern_library = None

    constraints = BrooksPatternConstraints()

    results: List[Dict] = []
    for sym in symbols:
        kl = get_kline_gateio(sym, args.timeframe, limit)
        if not kl or len(kl) < 50:
            continue

        candidates = detect_all_15m(kl)
        if not candidates:
            continue

        k1h = get_kline_gateio(sym, '1h', 240)

        features = extract_basic_kline_features(kl)
        if not features:
            continue

        for cand in candidates:
            if not cand.get('entry') or not cand.get('stop_loss') or not cand.get('take_profit_1'):
                continue
            if not _is_valid_trade(cand, args.timeframe):
                continue

            query_features = build_query_features(cand, features)
            pattern_candidates = _pattern_type_candidates(cand, features)
            pattern_score = 0.0
            best_match = None
            brooks_score = 0.0
            if pattern_library is not None:
                pattern_score, best_match, brooks_score = score_with_pattern_library(
                    pattern_library,
                    query_features,
                    pattern_candidates
                )

            base_pattern = cand.get('pattern') or ''
            hint = PATTERN_RULE_HINTS.get(base_pattern, '')
            if best_match:
                pattern_key = best_match
            elif hint:
                pattern_key = f"{base_pattern} {hint}"
            else:
                pattern_key = base_pattern

            constraint = constraints.evaluate(features, pattern_key, direction=cand.get('type'))
            if constraint.status == 'fail':
                continue

            base_score = score_candidate(cand, k1h)
            final_score = base_score + (pattern_score * 0.6) + constraint.score_adjust

            enriched = dict(cand)
            enriched['_score'] = final_score
            enriched['_pattern_score'] = pattern_score
            enriched['_brooks_score'] = brooks_score
            enriched['_brooks_status'] = constraint.status
            enriched['_brooks_rule'] = constraint.rule_name
            enriched['_brooks_reasons'] = ';'.join(constraint.reasons)
            enriched['_pattern_match'] = best_match
            enriched['symbol'] = sym
            enriched['timeframe'] = args.timeframe
            results.append(enriched)

    if not results:
        return

    results.sort(key=lambda x: x.get('_score', 0), reverse=True)
    top = results[:max(1, args.top)]

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
                    signal_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    timeframe=args.timeframe,
                    signal_type=r['type'],
                    symbol=r['symbol'],
                    entry_price=r['entry'],
                    stop_loss=r['stop_loss'],
                    take_profit_1=r.get('take_profit_1'),
                    take_profit_2=r.get('take_profit_2'),
                    entry_model=f"PA/{r.get('pattern')}",
                    strength='medium',
                    risk_reward_ratio=None,
                    volatility_level=None,
                    system_name='abu',
                    score=float(r.get('_score') or 0.0),
                    notes=notes,
                    entry_lower=None,
                    entry_upper=None,
                    stop_distance_points=None,
                    tp_rule=None,
                    stop_rule=None,
                    bracket_note=None
                )
            except Exception:
                pass
        db.close()

    output_dir = ROOT / 'outputs' / 'trading_signals'
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    out = output_dir / f"ABU_top{args.top}_{args.timeframe}_{timestamp}.md"

    lines = [
        f"# Abu Top{args.top} ({args.timeframe})",
        '',
        '| # | Symbol | Type | Entry | SL | TP1 | TP2 | Score | PatternScore | Brooks | Match | Reason |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---|---|---|'
    ]
    for i, r in enumerate(top, 1):
        lines.append(
            "| {idx} | {symbol} | {typ} | {entry:.4f} | {sl:.4f} | {tp1:.4f} | {tp2:.4f} | {score:.2f} | {pscore:.2f} | {brooks} | {match} | {reason} |".format(
                idx=i,
                symbol=r['symbol'],
                typ=r['type'],
                entry=r['entry'],
                sl=r['stop_loss'],
                tp1=float(r.get('take_profit_1') or 0.0),
                tp2=float(r.get('take_profit_2') or 0.0),
                score=float(r.get('_score') or 0.0),
                pscore=float(r.get('_pattern_score') or 0.0),
                brooks=r.get('_brooks_status') or '-',
                match=r.get('_pattern_match') or '-',
                reason=(r.get('reason') or '').replace('\n', ' ')
            )
        )

    out.write_text('\n'.join(lines), encoding='utf-8')
    print('✓ Wrote:', out)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
