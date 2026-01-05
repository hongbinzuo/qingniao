#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sherlock 强势币种扫描器（只用较为强势的指标做过滤）

指标与过滤（默认 1h + 4h 背景 + 1d TVEM）：
- 趋势：价格 > 1h Vegas 通道上沿（EMA144/169 高位）；4h 不弱于通道中轴
- 动量：1h RSI > 55 且 < 75（避免过热）；近20根均量上方（放量）
- 相对强度：过去7天相对 BTC 的收益为正（1d 相对收益）
- 结构：近N根出现更高高点/更高低点（HH/HL）
- TVEM：基于 1d EMA@N 与 σ@K（上/下轨），记录 position=above/inside/below

输出：
- outputs/sherlock/scan_strong_YYYYMMDD_HHMMSS.md（Top列表与理由）
- （可选）入库到 qingniao_sherlock.duckdb.sherlock_hits 与 trading_signals（watchlist）

注意：无网络时自动降级（仅输出已拿到的数据），不报错退出。
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 复用通用K线获取
try:
    from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
    from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
    from generate_comprehensive_trading_plans import get_kline_bitget as _get_k_bitget
except Exception:
    _get_k_gate = _get_k_bin = _get_k_bitget = None

from db_manager_trader import TraderDBManager
import json as _json
import requests
try:
    from market_timeseries import upsert_klines as _mts_upsert, load_klines as _mts_load
    HAVE_MTS = True
except Exception:
    HAVE_MTS = False


def _symbols_top50_fallback() -> List[str]:
    return [
        'BTC','ETH','SOL','BNB','XRP','ADA','AVAX','DOGE','LINK','DOT',
        'MATIC','TON','TRX','ATOM','SUI','APT','ARB','OP','NEAR','PEPE',
        'SEI','TIA','INJ','AAVE','UNI','RUNE','ETC','FIL','ICP','XLM'
    ]


def _ema(xs: List[float], n: int) -> List[float]:
    if not xs:
        return []
    k = 2/(n+1)
    out = []
    ema = xs[0]
    for x in xs:
        ema = x*k + ema*(1-k)
        out.append(ema)
    return out


def _rsi(closes: List[float], n: int = 14) -> float | None:
    if len(closes) < n+1:
        return None
    gains = []; losses = []
    for i in range(1, n+1):
        diff = closes[-i] - closes[-i-1]
        gains.append(max(diff,0.0))
        losses.append(max(-diff,0.0))
    avg_gain = sum(gains)/n; avg_loss = sum(losses)/n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain/avg_loss
    return 100 - 100/(1+rs)


def _stddev(xs: List[float]) -> Optional[float]:
    if not xs:
        return None
    m = sum(xs)/len(xs)
    var = sum((x - m) ** 2 for x in xs) / len(xs)
    return var ** 0.5


def _tvem_bands(closes: List[float], n: int = 200, k: float = 0.2) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """计算 TVEM 中线与上下轨
    线：EMA(n)
    σ：最近 n 根对 EMA 残差的标准差；上/下轨 = ema ± k * sigma
    """
    if len(closes) < max(5, n):
        return None, None, None
    ema = _ema(closes, n)
    if not ema:
        return None, None, None
    residuals = [c - e for c, e in zip(closes[-n:], ema[-n:])]
    sigma = _stddev(residuals) or 0.0
    line = ema[-1]
    upper = line + k * sigma
    lower = line - k * sigma
    return line, upper, lower


def _anchor_start(dt: datetime, kind: str = 'month') -> datetime:
    """获取锚点起始时间（UTC）：month|quarter"""
    if kind == 'quarter':
        q_month = ((dt.month - 1) // 3) * 3 + 1
        return datetime(dt.year, q_month, 1, tzinfo=timezone.utc)
    # default month
    return datetime(dt.year, dt.month, 1, tzinfo=timezone.utc)


def _anchored_vwap(kl: List[Dict[str, Any]], kind: str = 'month') -> Optional[float]:
    """计算锚定 VWAP（使用典型价 (H+L+C)/3）从当月/当季起始到最新一根"""
    if not kl:
        return None
    # 规范化时间戳（秒或毫秒）
    def _to_dt(ts: int) -> datetime:
        return datetime.fromtimestamp(ts/1000 if ts > 10**12 else ts, tz=timezone.utc)
    anchor = _anchor_start(_to_dt(int(kl[-1]['timestamp'])), kind)
    num = 0.0
    den = 0.0
    for x in kl:
        dt = _to_dt(int(x['timestamp']))
        if dt < anchor:
            continue
        tp = (float(x['high']) + float(x['low']) + float(x['close'])) / 3.0
        v = float(x.get('volume') or 0.0)
        num += tp * v
        den += v
    if den <= 0:
        return None
    return num / den


def _anchored_vwap_from(kl: List[Dict[str, Any]], anchor_dt: datetime) -> Optional[float]:
    """从指定锚点时间计算 AVWAP（典型价 (H+L+C)/3 加权）"""
    if not kl or not anchor_dt:
        return None
    def _to_dt(ts: int) -> datetime:
        return datetime.fromtimestamp(ts/1000 if ts > 10**12 else ts, tz=timezone.utc)
    num = 0.0
    den = 0.0
    for x in kl:
        dt = _to_dt(int(x['timestamp']))
        if dt < anchor_dt:
            continue
        tp = (float(x['high']) + float(x['low']) + float(x['close'])) / 3.0
        v = float(x.get('volume') or 0.0)
        num += tp * v
        den += v
    if den <= 0:
        return None
    return num / den


def _parse_anchor_dt(anchor_ts: Optional[float], anchor_iso: Optional[str]) -> Optional[datetime]:
    """解析用户提供的 AVWAP 锚点（epoch 秒/毫秒 或 ISO8601，如 2025-01-01T00:00:00Z）"""
    if anchor_ts is not None:
        try:
            ts = float(anchor_ts)
            if ts > 10**12:  # ms
                ts = ts / 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except Exception:
            pass
    if anchor_iso:
        s = anchor_iso.strip()
        try:
            if s.endswith('Z'):
                s = s[:-1]
            # 尝试精确到秒
            dt = datetime.strptime(s, '%Y-%m-%dT%H:%M:%S').replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            try:
                dt = datetime.strptime(s, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None
    return None


def _get_kl_binance_direct(symbol: str, tf: str, limit: int = 300) -> List[Dict[str, Any]]:
    tf_map = {'5m':'5m','15m':'15m','1h':'1h','4h':'4h','1d':'1d'}
    interval = tf_map.get(tf, '1h')
    sym = f'{symbol}USDT'
    try:
        r = requests.get('https://api.binance.com/api/v3/klines', params={'symbol': sym, 'interval': interval, 'limit': limit}, timeout=12)
        if r.status_code == 200:
            data = r.json()
            out=[]
            for k in data:
                out.append({'timestamp': int(k[0]), 'open': float(k[1]), 'high': float(k[2]), 'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])})
            return out
    except Exception:
        return []
    return []


def _get_kl(symbol: str, tf: str, limit: int = 300, exchange: str | None = None) -> List[Dict[str, Any]]:
    # 优先级按 exchange 参数；缺失则 Gate->Binance->Bitget
    providers = []
    if exchange == 'gate':
        providers = [_get_k_gate, _get_k_bin, _get_k_bitget]
    elif exchange == 'bitget':
        providers = [_get_k_bitget, _get_k_gate, _get_k_bin]
    else:
        providers = [_get_k_gate, _get_k_bin, _get_k_bitget]
    for fn in providers:
        if not fn:
            continue
        try:
            kl = fn(symbol=symbol, timeframe=tf, limit=limit)
            if kl:
                # 写入本地价格库（可选）
                try:
                    if HAVE_MTS:
                        ex = exchange or ('gate' if fn is _get_k_gate else 'bitget' if fn is _get_k_bitget else 'binance')
                        _mts_upsert(ex, symbol, tf, kl)
                except Exception:
                    pass
                return kl
        except Exception:
            continue
    # 兜底：直连 Binance K 线
    try:
        b = _get_kl_binance_direct(symbol, tf, limit)
        if b:
            try:
                if HAVE_MTS:
                    _mts_upsert('binance', symbol, tf, b)
            except Exception:
                pass
            return b
    except Exception:
        pass
    # 最后兜底：本地缓存库
    if HAVE_MTS:
        cached = _mts_load(exchange or 'gate', symbol, tf, limit)
        if cached:
            return cached
    return []


def _is_hh_hl(kl: List[Dict[str, Any]], n: int = 5) -> bool:
    if len(kl) < n+2:
        return False
    highs = [x['high'] for x in kl[-(n+2):]]
    lows  = [x['low'] for x in kl[-(n+2):]]
    return max(highs[-n:]) > max(highs[:-n]) and min(lows[-n:]) > min(lows[:-n])


def _avg_vol(kl: List[Dict[str, Any]], n: int = 20) -> float:
    if len(kl) < n:
        return 0.0
    return sum(float(x.get('volume') or 0) for x in kl[-n:]) / n


def _rel_strength_vs_btc(symbol: str, days: int = 7, exchange: str | None = None) -> Optional[float]:
    """计算相对强度（过去 N 天相对 BTC 的超额收益）：symbol_ret - btc_ret"""
    try:
        k_sym = _get_kl(symbol, '1d', max(10, days + 1), exchange)
        k_btc = _get_kl('BTC', '1d', max(10, days + 1), exchange)
        if not k_sym or not k_btc:
            return None
        c_sym = [x['close'] for x in k_sym]
        c_btc = [x['close'] for x in k_btc]
        if len(c_sym) < days + 1 or len(c_btc) < days + 1:
            return None
        r_sym = c_sym[-1] / c_sym[-(days+1)] - 1.0
        r_btc = c_btc[-1] / c_btc[-(days+1)] - 1.0
        return r_sym - r_btc
    except Exception:
        return None


def _scan_one(symbol: str, exchange: str | None = None, min_score: int = 50,
              tvem_n: int = 200, tvem_k: float = 0.2,
              fresh_bars: int | None = None,
              avwap_anchor_dt: Optional[datetime] = None) -> Dict[str, Any] | None:
    # 1h 核心窗口
    k1h = _get_kl(symbol, '1h', 300, exchange)
    if not k1h:
        return None
    # 数据新鲜度（可选）：最后K线距离现在不超过 fresh_bars 根
    if fresh_bars is not None and fresh_bars > 0:
        try:
            last_ts = int(k1h[-1]['timestamp'])
            # 将 now 统一为毫秒时间戳
            now_ts = int(datetime.now(timezone.utc).timestamp() * 1000)
            if now_ts - last_ts > fresh_bars * 60 * 60 * 1000:
                return None
        except Exception:
            pass

    closes = [x['close'] for x in k1h]
    ema144 = _ema(closes, 144)
    ema169 = _ema(closes, 169)
    ema200 = _ema(closes, 200)
    price = closes[-1]
    lo = min(ema144[-1], ema169[-1]) if ema144 and ema169 else (ema200[-1] if ema200 else None)
    hi = max(ema144[-1], ema169[-1]) if ema144 and ema169 else (ema200[-1] if ema200 else None)
    # 趋势条件：强版=价格>Vegas上沿；宽松版=价格>EMA200（若Vegas缺失或未满足时作为备选）
    cond_trend_strict = (hi is not None and price > hi)
    cond_trend_loose  = (ema200 is not None and price > ema200[-1])
    cond_trend = cond_trend_strict or cond_trend_loose
    rsi = _rsi(closes, 14) or 0.0
    cond_rsi = 55 <= rsi <= 75
    vol = float(k1h[-1].get('volume') or 0)
    vavg = _avg_vol(k1h, 20)
    cond_vol = (vavg > 0 and vol > 1.2 * vavg)
    cond_struct = _is_hh_hl(k1h, 5)

    # 4h 背景
    k4h = _get_kl(symbol, '4h', 300, exchange)
    cond_bg = True
    if k4h:
        c4 = [x['close'] for x in k4h]
        e144_4 = _ema(c4, 144); e169_4 = _ema(c4, 169)
        mid4 = ( (e144_4[-1] + e169_4[-1]) / 2 ) if (e144_4 and e169_4) else None
        if mid4 is not None:
            cond_bg = (price >= mid4)

    # 相对强度（过去 N 天相对BTC超额收益）
    rs7 = _rel_strength_vs_btc(symbol, days=7, exchange=exchange)
    cond_rs = (rs7 is not None and rs7 > 0)

    # 1d TVEM（展示与入库）
    k1d = _get_kl(symbol, '1d', 300, exchange)
    tvem_line = tvem_upper = tvem_lower = None
    pos_tvem = None
    if k1d:
        c1d = [x['close'] for x in k1d]
        tvem_line, tvem_upper, tvem_lower = _tvem_bands(c1d, n=tvem_n, k=tvem_k)
        if all(x is not None for x in [tvem_line, tvem_upper, tvem_lower]):
            pos_tvem = 'above' if price > tvem_upper else ('inside' if tvem_lower <= price <= tvem_upper else 'below')

    # 1d EMA12（Sherlock信号使用）
    ema12_1d = None
    if k1d:
        c1d = [x['close'] for x in k1d]
        em = _ema(c1d, 12)
        ema12_1d = em[-1] if em else None

    # 锚定 VWAP：月度/季度（按4h与1d两个框架）
    mvwap_1d = _anchored_vwap(k1d, 'month') if k1d else None
    qvwap_4h = _anchored_vwap(k4h, 'quarter') if k4h else None
    # 自定义 AVWAP（用户提供的锚点）
    avwap1d_custom = _anchored_vwap_from(k1d, avwap_anchor_dt) if (k1d and avwap_anchor_dt) else None
    avwap4h_custom = _anchored_vwap_from(k4h, avwap_anchor_dt) if (k4h and avwap_anchor_dt) else None

    score = 0
    if cond_trend:
        score += 40 if cond_trend_strict else 30
    if cond_rsi:   score += 20
    if cond_vol:   score += 20
    if cond_struct:score += 20
    if not cond_bg: score -= 10
    if cond_rs:    score += 10
    if score < (min_score or 0):
        return None

    vegas_side = ('above' if (hi and price>hi) else 'inside' if (hi and lo and lo<=price<=hi) else 'below')

    return {
        'symbol': symbol,
        'price': price,
        'rsi': rsi,
        'trend': 'above_vegas' if cond_trend else 'neutral',
        'vol_ratio': (vol / vavg) if vavg else None,
        'score': score,
        'notes': [
            '趋势强' if cond_trend else '',
            '动量强' if cond_rsi else '',
            '放量' if cond_vol else '',
            'HH/HL' if cond_struct else '',
            '强于BTC' if cond_rs else '',
        ],
        # position 使用 TVEM 相对位置（用于展示与入库）
        'position': pos_tvem or vegas_side,
        'tvem': {'anchor':'Q','ema_n': tvem_n,'sigma_k': tvem_k, 'line': tvem_line, 'upper': tvem_upper, 'lower': tvem_lower},
        'vegas_side': vegas_side,
        'struct': bool(cond_struct),
        'rs7': rs7,
        'mvwap_1d': mvwap_1d,
        'qvwap_4h': qvwap_4h,
        'ema12_1d': ema12_1d,
        'avwap1d_custom': avwap1d_custom,
        'avwap4h_custom': avwap4h_custom,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Sherlock 强势币筛选')
    ap.add_argument('--limit', type=int, default=50, help='候选币数量（默认50）')
    ap.add_argument('--topn', type=int, default=20, help='输出Top N（默认20）')
    ap.add_argument('--write-db', action='store_true', help='写入Sherlock库的trading_signals（watchlist）')
    ap.add_argument('--exchange', default='gate', choices=['gate','bitget','auto'], help='数据源优先级（默认gate）')
    ap.add_argument('--min-score', type=int, default=50, help='最小得分阈值（默认50）')
    ap.add_argument('--fresh-bars', type=int, default=None, help='数据新鲜度阈值（单位=1h根数，默认None=不校验）')
    ap.add_argument('--tvem-n', type=int, default=200, help='TVEM EMA窗口（默认200）')
    ap.add_argument('--tvem-k', type=float, default=0.2, help='TVEM σ倍数（默认0.2）')
    ap.add_argument('--avwap-anchor-ts', type=float, default=None, help='AVWAP 锚点的Unix时间戳（秒或毫秒）')
    ap.add_argument('--avwap-anchor-iso', type=str, default=None, help='AVWAP 锚点的ISO时间（如 2025-01-01T00:00:00Z）')
    args = ap.parse_args()

    symbols = _symbols_top50_fallback()[:args.limit]
    results = []
    # 解析 AVWAP 锚点（如果提供）
    anchor_dt = _parse_anchor_dt(args.avwap_anchor_ts, args.avwap_anchor_iso)

    for sym in symbols:
        try:
            r = _scan_one(
                sym,
                exchange=None if args.exchange=='auto' else args.exchange,
                min_score=args.min_score,
                tvem_n=args.tvem_n,
                tvem_k=args.tvem_k,
                fresh_bars=args.fresh_bars,
                avwap_anchor_dt=anchor_dt,
            )
            if r:
                results.append(r)
        except Exception:
            continue
    results.sort(key=lambda x: x['score'], reverse=True)
    top = results[:args.topn]

    outdir = Path('outputs') / 'sherlock'
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = outdir / f'scan_strong_{ts}.md'
    lines = [
        f"# Sherlock 强势币筛选 ({ts})",
        '',
        f"共筛到 {len(results)} 个强势候选；展示Top {len(top)}（exchange={args.exchange}）",
        '',
        '| Rank | Symbol | Price | Score | RSI | 备注 |',
        '|---:|---|---:|---:|---:|---|',
    ]
    # 将结果写入 sherlock_hits 表（TopN）
    try:
        db = TraderDBManager('sherlock')
        con = db._get_connection()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for r in top:
            # 生成自增ID
            try:
                next_id = con.execute('SELECT COALESCE(MAX(id),0)+1 FROM sherlock_hits').fetchone()[0]
            except Exception:
                next_id = None
            details = {
                'notes': [x for x in r['notes'] if x],
                'rsi': r['rsi'],
                'vol_ratio': r.get('vol_ratio'),
                'trend': r.get('trend'),
                'position': r.get('position'),
                'tvem': r.get('tvem'),
                'vegas_side': r.get('vegas_side'),
                'struct': r.get('struct'),
                'rs7': r.get('rs7'),
                'mvwap_1d': r.get('mvwap_1d'),
                'qvwap_4h': r.get('qvwap_4h'),
                'ema12_1d': r.get('ema12_1d'),
            }
            if next_id is not None:
                # 防御：r['tvem'] 可能为 None（无 1d 数据时）
                tvem = r.get('tvem') or {}
                con.execute(
                    '''INSERT INTO sherlock_hits(id, computed_at, symbol, tf, exchange, score, tags, details_json, tvem_anchor, ema_n, sigma_k, tvem_line, upper, lower, position, created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    [int(next_id), now, r['symbol'], '1h', args.exchange, float(r['score']), ','.join([x for x in r['notes'] if x]), _json.dumps(details, ensure_ascii=False),
                     'Q', int(args.tvem_n), float(args.tvem_k), tvem.get('line'), tvem.get('upper'), tvem.get('lower'), r.get('position'), now]
                )
            else:
                tvem = r.get('tvem') or {}
                con.execute(
                    '''INSERT INTO sherlock_hits(computed_at, symbol, tf, exchange, score, tags, details_json, tvem_anchor, ema_n, sigma_k, tvem_line, upper, lower, position, created_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    [now, r['symbol'], '1h', args.exchange, float(r['score']), ','.join([x for x in r['notes'] if x]), _json.dumps(details, ensure_ascii=False),
                     'Q', int(args.tvem_n), float(args.tvem_k), tvem.get('line'), tvem.get('upper'), tvem.get('lower'), r.get('position'), now]
                )
        db.close()
    except Exception as e:
        print('⚠️ 写入 sherlock_hits 失败:', e)

    for i, r in enumerate(top, 1):
        notes = '、'.join([x for x in r['notes'] if x])
        lines.append(f"| {i} | {r['symbol']} | {r['price']:.4f} | {r['score']} | {r['rsi']:.1f} | {notes} |")

    # 附：Confluence 说明（快速版）
    if top:
        lines.append('')
        lines.append('## Confluence 说明（快速版）')
        lines.append('')
        for r in top:
            lines.append(f"### {r['symbol']}")
            lines.append(f"- TVEM: anchor=Q, EMA@1D={args.tvem_n}, σ={args.tvem_k}，位置={r.get('position','n/a')}")
            lines.append(f"- 趋势: {r.get('trend')}；Vegas/EMA判定；价格={r['price']:.4f}")
            lines.append(f"- RSI: {r['rsi']:.1f}")
            vr = r.get('vol_ratio')
            if vr is not None:
                lines.append(f"- 量能: 当前/20均量={vr:.2f}x")
            lines.append(f"- 结构: {'HH/HL' if r.get('struct') else '无'}")
            if r.get('rs7') is not None:
                lines.append(f"- 相对强度(7d): {'强于BTC' if (r['rs7']>0) else '弱于/等于BTC'} ({r['rs7']:+.2%})")
            if r.get('vegas_side'):
                lines.append(f"- 1h Vegas 相对位置: {r['vegas_side']}")
            if r.get('avwap1d_custom') is not None:
                lines.append(f"- AVWAP(1d, custom): {r['avwap1d_custom']:.4f}")
            if r.get('avwap4h_custom') is not None:
                lines.append(f"- AVWAP(4h, custom): {r['avwap4h_custom']:.4f}")
            lines.append('')
    out.write_text('\n'.join(lines), encoding='utf-8')
    print('✓ 已生成:', out)

    if args.write_db and top:
        try:
            db = TraderDBManager('sherlock')
            for r in top:
                db.add_trading_signal(
                    signal_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    timeframe='1h',
                    signal_type='watchlist',
                    entry_price=r['price'],
                    stop_loss=None,
                    take_profit_1=None,
                    take_profit_2=None,
                    entry_model='sherlock_strong_filter',
                    strength='strong',
                    risk_reward_ratio=None,
                    volatility_level=None,
                    system_name='sherlock'
                )
            db.close()
            print('✓ 已写入 Sherlock 数据库 watchlist')
        except Exception as e:
            print('⚠️ 写库失败（稍后可重试 --write-db）:', e)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
