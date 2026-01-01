#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从对话/观点中抽取“影子交易”样本，并结合当时K线/指标生成特征，导出 CSV。

用途：为概率校准与技术组合统计提供原始样本。

特性
- 读取 DuckDB（de）中的 conversations / trader_viewpoints（带交易相关关键词）
- 提取：方向（多/空）、参考价（优先btc_price/提及价/缓存价）、关键词（OTE/0.618/0.786/883/Vegas/VWAP等）
- 生成特征：是否在 OTE，距 SR 最近百分比，多周期偏向（15m/1h Vegas 通道上下）、VWAP 相对位置
- 生成结果标签（可选）：未来 15m/1h 的最大/最小偏移（%），以及是否触达 +0.5%/-0.5%
- 支持离线（--offline）：仅使用本地缓存/时序库，不请求网络

输出
- trading_signals/.datasets/shadow_trades_YYYYMMDD_HHMMSS.csv

注意
- 若本机 Python 未安装 duckdb，将无法读取数据库；仅保存空数据或提示。
- 若无本地时序库/缓存，结果字段可能为空；可后续补足。
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import re
import csv

try:
    from db_manager_trader import TraderDBManager
except Exception:
    TraderDBManager = None


def _safe_duck():
    try:
        import duckdb  # noqa
        return True
    except Exception:
        return False


def _keywords(text: str) -> List[str]:
    if not text:
        return []
    ks = []
    t = text.lower()
    for k in ['ote', '0.618', '0.786', '883', 'vegas', 'vwap', 'pinbar', '吞没', '回撤', '突破', '支撑', '阻力']:
        if k in t:
            ks.append(k)
    return ks


def _infer_direction(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    if ('做多' in t) or ('多' in t) or ('long' in t):
        return 'long'
    if ('做空' in t) or ('空' in t) or ('short' in t):
        return 'short'
    return None


def _extract_price(text: str) -> Optional[float]:
    if not text:
        return None
    # 支持 88k / 88,300 / 88300 等
    m = re.search(r"(\d{2,3}(?:,\d{3})*(?:\.\d+)?|\d{2,3}k)", text.lower())
    if not m:
        return None
    s = m.group(1).replace(',', '')
    if s.endswith('k'):
        try:
            return float(s[:-1]) * 1000
        except Exception:
            return None
    try:
        return float(s)
    except Exception:
        return None


def _analysis_features(kl: List[Dict], tf_name_cn: str, current_price: float) -> Dict[str, Any]:
    # 复用现有分析
    try:
        from generate_btc_de_signals import analyze_timeframe
        a = analyze_timeframe(kl, tf_name_cn, current_price)
        feat = {}
        oa = (a or {}).get('ote_analysis') or {}
        feat['in_ote'] = bool(oa.get('in_ote_zone'))
        if oa:
            feat['fib_618'] = oa.get('fib_618')
            feat['fib_786'] = oa.get('fib_786')
        sr = (a or {}).get('support_resistance') or {}
        feat['sr_support_top3'] = (sr.get('support') or [])[:3]
        feat['sr_resist_top3'] = (sr.get('resistance') or [])[:3]
        ema144, ema169 = (a or {}).get('ema_144'), (a or {}).get('ema_169')
        if ema144 and ema169:
            lo, hi = min(ema144, ema169), max(ema144, ema169)
            feat['vegas_side'] = 'above' if current_price > hi else ('below' if current_price < lo else 'inside')
        vwap = (a or {}).get('vwap')
        if vwap:
            feat['vwap_side'] = 'above' if current_price > vwap else 'below'
        return feat
    except Exception:
        return {}


def _future_move(times: List[Dict], base_ts: int, base_price: float, horizon_sec: int) -> Optional[float]:
    # times: list of {'ts': int, 'price': float} ordered asc
    # 返回未来窗口内相对涨跌幅最大绝对值（正为上涨最大幅，负为下跌最大幅）
    import bisect
    if not times:
        return None
    t0 = base_ts
    t1 = base_ts + horizon_sec
    ts = [x['ts'] for x in times]
    i = bisect.bisect_left(ts, t0)
    j = bisect.bisect_left(ts, t1)
    if i >= len(times):
        return None
    window = times[i:j+1]
    if not window:
        return None
    highs = max(x['price'] for x in window)
    lows = min(x['price'] for x in window)
    up = (highs - base_price) / base_price * 100
    dn = (lows - base_price) / base_price * 100
    # 返回幅度绝对值更大者
    return up if abs(up) >= abs(dn) else dn


def main():
    import argparse
    ap = argparse.ArgumentParser(description='构建影子交易样本数据集')
    ap.add_argument('--limit', type=int, default=200, help='最多抽取 N 条对话/观点（默认200）')
    ap.add_argument('--offline', action='store_true', help='仅使用本地缓存/时序库，不请求网络')
    args = ap.parse_args()

    if TraderDBManager is None or not _safe_duck():
        print('❌ 本机缺少 duckdb，无法读取数据库；仅创建空数据集占位。')
        rows = []
    else:
        db = TraderDBManager('de')
        con = db._get_connection()
        # 优先 conversations（带 has_trading_info 或含关键字），其次 viewpoints
        sql = (
            """
            SELECT 'conv' AS src, id, timestamp, COALESCE(extracted_content, user_message || '\n' || trader_message) AS text, btc_price
            FROM conversations
            WHERE (has_trading_info = 1 OR LOWER(COALESCE(extracted_content,'')) LIKE '%btc%' OR LOWER(COALESCE(user_message,'')) LIKE '%btc%' OR LOWER(COALESCE(trader_message,'')) LIKE '%btc%')
            ORDER BY timestamp DESC
            LIMIT ?
            """
        )
        try:
            rows = con.execute(sql, [args.limit]).fetchall()
        except Exception as e:
            print('查询 conversations 失败:', e)
            rows = []
        # 兜底从 viewpoints 追加
        try:
            sql2 = (
                """
                SELECT 'vp' AS src, id, timestamp, content AS text, btc_price
                FROM trader_viewpoints
                WHERE LOWER(COALESCE(content,'')) LIKE '%btc%'
                ORDER BY timestamp DESC
                LIMIT ?
                """
            )
            vp_rows = con.execute(sql2, [args.limit//2]).fetchall()
            rows.extend(vp_rows)
        except Exception:
            pass

    # 价格与K线来源（离线优先）
    from btc_price_cache import get_price_cache
    cache = get_price_cache()

    # 尝试加载 5m timeseries（离线）
    ts_series: List[Dict] = []
    try:
        ts_conn = cache._get_timeseries_connection()
        if ts_conn:
            rs = ts_conn.execute('SELECT timestamp, close FROM btc_price_5m ORDER BY timestamp').fetchall()
            ts_series = [{'ts': int(t), 'price': float(p)} for t,p in rs]
    except Exception:
        ts_series = []

    # 输出 CSV
    outdir = Path('trading_signals') / '.datasets'
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f'shadow_trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    cols = [
        'src','id','timestamp','direction','ref_price','keywords','in_ote','fib_618','fib_786','sr_support_top3','sr_resist_top3','vegas_side','vwap_side','future_15m','future_1h'
    ]
    with out.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for src, rid, ts, text, btc_price in rows:
            kw = _keywords(text or '')
            direction = _infer_direction(text or '')
            ref_price = None
            # 优先字段价，其次文本价，其次缓存价
            if isinstance(btc_price, (int,float)):
                ref_price = float(btc_price)
            if ref_price is None:
                p2 = _extract_price(text or '')
                if p2:
                    ref_price = p2
            if ref_price is None:
                ref_price = cache.get_price_with_fallback(ts, use_api=not args.offline)

            # 取 15m/1h 片段并做特征
            feat = {}
            try:
                from generate_btc_de_signals import get_btc_kline_gateio, get_btc_kline_bitget
                k15 = get_btc_kline_gateio('15m', 200) or get_btc_kline_bitget('15m', 200)
                k1h = get_btc_kline_gateio('1h', 200) or get_btc_kline_bitget('1h', 200)
            except Exception:
                k15 = k1h = None
            if ref_price and k15:
                feat.update(_analysis_features(k15, '15分钟', ref_price))
            if not feat and ref_price and k1h:
                feat.update(_analysis_features(k1h, '1小时', ref_price))

            # 未来波动（离线 timeseries 可计算）
            fut15 = fut1h = None
            if ts_series and ref_price:
                # 解析 ts 为 unix 秒（cache 内部可用工具，但我们简化）
                try:
                    from datetime import datetime
                    import time
                    if isinstance(ts, str):
                        # 尝试常见格式
                        for fmt in ('%Y-%m-%d %H:%M:%S','%Y/%m/%d %H:%M:%S','%Y-%m-%d %H:%M'):
                            try:
                                base_ts = int(datetime.strptime(ts, fmt).timestamp())
                                break
                            except Exception:
                                base_ts = None
                        if base_ts is None:
                            base_ts = int(time.time())
                    else:
                        base_ts = int(ts)
                except Exception:
                    base_ts = None
                if base_ts:
                    fut15 = _future_move(ts_series, base_ts, ref_price, 15*60)
                    fut1h = _future_move(ts_series, base_ts, ref_price, 60*60)

            row = {
                'src': src,
                'id': rid,
                'timestamp': ts,
                'direction': direction or '',
                'ref_price': f"{ref_price:.2f}" if ref_price else '',
                'keywords': ','.join(kw),
                'in_ote': feat.get('in_ote',''),
                'fib_618': feat.get('fib_618',''),
                'fib_786': feat.get('fib_786',''),
                'sr_support_top3': '|'.join(str(int(x)) for x in (feat.get('sr_support_top3') or [])),
                'sr_resist_top3': '|'.join(str(int(x)) for x in (feat.get('sr_resist_top3') or [])),
                'vegas_side': feat.get('vegas_side',''),
                'vwap_side': feat.get('vwap_side',''),
                'future_15m': f"{fut15:.2f}" if isinstance(fut15,(int,float)) else '',
                'future_1h': f"{fut1h:.2f}" if isinstance(fut1h,(int,float)) else '',
            }
            w.writerow(row)

    print('✓ 数据集已生成:', out)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

