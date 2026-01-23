#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qingniao-Abu Top10 PA scanner (Gate, 5m/15m/1h)

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
MIN_STOP_PCT = {'5m': 0.015, '15m': 0.015, '1h': 0.01}
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
}


def _is_excluded_symbol(symbol: str) -> bool:
    sym = symbol.upper()
    if sym in EXCL:
        return True
    if sym.startswith(('USD', 'USDT', 'USDC')):
        return True
    if sym.endswith(LEVERAGED_SUFFIXES):
        return True
    return False


def _fetch_gate_symbols() -> List[str]:
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [t['currency_pair'].replace('_USDT', '').upper()
                for t in data if t.get('currency_pair', '').endswith('_USDT')]
    except Exception:
        return []


def get_top_coins(limit: int, rank_by: str = 'volume') -> List[str]:
    rank_by = (rank_by or 'volume').lower()
    LAST_TOP_META.update({
        'requested': [],
        'returned': [],
        'not_on_gate': [],
        'gate_symbols_empty': False,
    })

    if rank_by == 'marketcap':
        gate_symbols = set(_fetch_gate_symbols())
        not_on_gate = []
        gate_symbols_empty = not gate_symbols
        symbols = []
        for symbol in FIXED_MARKETCAP[:max(1, limit)]:
            if _is_excluded_symbol(symbol):
                continue
            if gate_symbols and symbol not in gate_symbols:
                not_on_gate.append(symbol)
                continue
            symbols.append(symbol)
            if len(symbols) >= limit:
                break
        LAST_TOP_META.update({
            'requested': FIXED_MARKETCAP[:max(1, limit)],
            'returned': symbols,
            'not_on_gate': not_on_gate,
            'gate_symbols_empty': gate_symbols_empty,
        })
        if symbols:
            return symbols
        return FIXED_MARKETCAP[:min(limit, len(FIXED_MARKETCAP))]

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


_CACHE = MarketDataCache()
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


def get_kline_gateio(symbol: str, timeframe: str, limit: int) -> List[Dict]:
    try:
        klines, stats = _CACHE.get_klines(symbol, timeframe, limit)
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
    ap.add_argument('--timeframe', type=str, default='15m', choices=['5m', '15m', '1h'])
    ap.add_argument('--rank-by', type=str, default='volume', choices=['volume', 'marketcap'])
    ap.add_argument('--days', type=int, default=None)
    ap.add_argument('--write-db', type=int, default=1)
    args = ap.parse_args()

    scan_start = time.time()
    days = args.days if args.days is not None else DEFAULT_DAYS.get(args.timeframe, 7)
    print(f"[INFO] timeframe={args.timeframe} days={days} (建议: 5m=3-5天, 15m=10-14天, 1h=30-60天)")
    limit = min(1000, KLINES_PER_DAY.get(args.timeframe, 96) * max(days, 1))

    if args.rank_by == 'marketcap':
        symbols = get_top_coins(len(FIXED_MARKETCAP), rank_by=args.rank_by)
    else:
        symbols = get_top_coins(max(args.top, 10), rank_by=args.rank_by)
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
    rulebook = BestPracticeRulebook()
    prob_estimator = SignalProbabilityEstimator()

    results: List[Dict] = []
    skip_reasons: Dict[str, set] = {}
    for sym in symbols:
        kl = get_kline_gateio(sym, args.timeframe, limit)
        if not kl or len(kl) < 50:
            skip_reasons.setdefault(sym, set()).add('K线不足或缺失')
            continue

        if args.timeframe == '1h':
            candidates = detect_all_1h(kl)
        else:
            candidates = detect_all_15m(kl)
        if not candidates:
            skip_reasons.setdefault(sym, set()).add('无候选形态')
            continue

        k1h = get_kline_gateio(sym, '1h', 240)

        features = extract_basic_kline_features(kl)
        if not features:
            skip_reasons.setdefault(sym, set()).add('特征提取失败')
            continue

        has_signal = False
        for cand in candidates:
            if not cand.get('entry') or not cand.get('stop_loss') or not cand.get('take_profit_1'):
                skip_reasons.setdefault(sym, set()).add('缺少交易字段')
                continue
            if not _is_valid_trade(cand, args.timeframe):
                skip_reasons.setdefault(sym, set()).add('止损/目标不合法')
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
                skip_reasons.setdefault(sym, set()).add('Brooks约束失败')
                continue

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
            final_score = base_score + (pattern_score * 0.6) + constraint.score_adjust

            enriched = dict(cand)
            enriched['_score'] = final_score
            enriched['_pattern_score'] = pattern_score
            enriched['_brooks_score'] = brooks_score
            enriched['_brooks_status'] = constraint.status
            enriched['_brooks_rule'] = constraint.rule_name
            enriched['_brooks_reasons'] = ';'.join(constraint.reasons)
            enriched['_pattern_match'] = best_match
            enriched['_prob_tp1'] = prob_tp1
            enriched['_prob_tp2'] = prob_tp2
            enriched['_prob_sl'] = prob_sl
            enriched['_prob_source'] = prob_source
            enriched['_prob_samples'] = prob_samples
            enriched['symbol'] = sym
            enriched['timeframe'] = args.timeframe
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
        '| # | Symbol | Type | Entry | SL | TP1 | TP2 | P(TP1) | P(TP2) | P(SL) | Score | PatternScore | Brooks | Match | Reason |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|'
    ]
    for i, r in enumerate(top, 1):
        lines.append(
            "| {idx} | {symbol} | {typ} | {entry:.4f} | {sl:.4f} | {tp1:.4f} | {tp2:.4f} | {p1} | {p2} | {psl} | {score:.2f} | {pscore:.2f} | {brooks} | {match} | {reason} |".format(
                idx=i,
                symbol=r['symbol'],
                typ=r['type'],
                entry=r['entry'],
                sl=r['stop_loss'],
                tp1=float(r.get('take_profit_1') or 0.0),
                tp2=float(r.get('take_profit_2') or 0.0),
                p1=f"{float(r.get('_prob_tp1') or 0.0) * 100:.1f}%",
                p2=f"{float(r.get('_prob_tp2') or 0.0) * 100:.1f}%",
                psl=f"{float(r.get('_prob_sl') or 0.0) * 100:.1f}%",
                score=float(r.get('_score') or 0.0),
                pscore=float(r.get('_pattern_score') or 0.0),
                brooks=r.get('_brooks_status') or '-',
                match=r.get('_pattern_match') or '-',
                reason=(r.get('reason') or '').replace('\n', ' ')
            )
        )

    lines.append("")
    scan_elapsed = int(time.time() - scan_start)
    lines.append("## 跳过统计")
    lines.append(f"- 参与扫描: {len(symbols)}")
    lines.append("- 概率说明: P(TP2) 为条件概率（到达TP1后继续到TP2）")
    lines.append("- 概率来源: 优先使用反馈统计（signal_evaluations）；样本不足时与估算值加权")
    if CACHE_STATS['calls']:
        sources = ", ".join(f"{k}={v}" for k, v in CACHE_STATS['sources'].items())
        lines.append(
            f"- 缓存统计: 调用={CACHE_STATS['calls']} 拉取={CACHE_STATS['fetched']} 写入={CACHE_STATS['inserted']} 请求={CACHE_STATS['requests']} 耗时={CACHE_STATS['elapsed_ms']}ms 来源({sources})"
        )
        if CACHE_STATS['errors']:
            last_error = CACHE_STATS['last_error'] or '-'
            lines.append(f"- 缓存错误: {CACHE_STATS['errors']} (last={last_error})")
    lines.append(f"- 扫描耗时: {scan_elapsed}s")
    if args.rank_by == 'marketcap' and LAST_TOP_META.get('gate_symbols_empty'):
        lines.append("- Gate 列表获取失败，按固定币种直接扫描")
    not_on_gate = LAST_TOP_META.get('not_on_gate') or []
    if not_on_gate:
        lines.append(f"- Gate 未上币: {', '.join(not_on_gate)}")
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


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
