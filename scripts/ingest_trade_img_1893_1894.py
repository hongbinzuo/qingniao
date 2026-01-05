#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from generate_btc_de_signals import (
    get_btc_kline_gateio,
    get_btc_kline_bitget,
    analyze_timeframe,
)


def near(x: float, y: float, pct: float = 0.2) -> bool:
    try:
        return abs(x - y) / y * 100 < pct
    except Exception:
        return False


def label_trade(entry: float, direction: str, current_price: float) -> list[str]:
    labels: list[str] = []
    k15 = get_btc_kline_gateio('15m', 200) or get_btc_kline_bitget('15m', 200)
    k1h = get_btc_kline_gateio('1h', 200) or get_btc_kline_bitget('1h', 200)
    for kl, tf in ((k15, '15m'), (k1h, '1h')):
        if not kl:
            continue
        a = analyze_timeframe(kl, '15分钟' if tf == '15m' else '1小时', current_price)
        if not a:
            continue
        oa = a.get('ote_analysis') or {}
        f618 = oa.get('fib_618'); f786 = oa.get('fib_786')
        if f618 and f786:
            lo, hi = (min(f618, f786), max(f618, f786))
            if lo <= entry <= hi:
                if 'OTE' not in labels: labels.append('OTE')
            elif near(entry, f618) or near(entry, f786):
                if 'OTE邻近' not in labels: labels.append('OTE邻近')
        e144, e169 = a.get('ema_144'), a.get('ema_169')
        if (e144 and near(entry, e144)) or (e169 and near(entry, e169)):
            if 'Vegas邻近' not in labels: labels.append('Vegas邻近')
        vwap = a.get('vwap')
        if vwap and near(entry, vwap):
            if 'VWAP邻近' not in labels: labels.append('VWAP邻近')
        sr = a.get('support_resistance') or {}
        arr = (sr.get('support') or []) if direction == 'long' else (sr.get('resistance') or [])
        for p in arr[:5]:
            try:
                if abs(entry - float(p)) / entry * 100 < 0.2:
                    if 'SR邻近' not in labels: labels.append('SR邻近')
                    break
            except Exception:
                pass
    return labels


def add_one(ts: str, direction: str, lev: int, entry: float, cur: float, pnl_pct: float, shot: str) -> int:
    db = TraderDBManager('de')
    tid = db.add_trade_record(
        timestamp=ts,
        symbol='BTC/USDT',
        direction=direction,
        leverage=lev,
        entry_price=entry,
        exit_price=None,
        profit_pct=pnl_pct,
        profit_usdt=None,
        strategy='real_trade',
        screenshot_path=shot,
        text_content=f'截图录入；当前价 {cur:.1f}；显示收益 {pnl_pct:.2f}%（{lev}x）。',
        source='screenshot'
    )
    labels = []
    try:
        labels = label_trade(entry, direction, cur)
    except Exception:
        labels = []
    if labels:
        db.add_viewpoint(
            content=(f'De.交易技术归因 | trade#{tid} | {direction.upper()} | entry ${entry:,.1f} | 技术: {", ".join(labels)}'),
            timestamp=ts, source='tech-label', category='label', tags=['tech','label'], related_trade_id=tid, btc_price=cur
        )
        try:
            con = db._get_connection(); import json as _j
            con.execute('UPDATE trade_records SET tech_labels=? WHERE id=?', [_j.dumps(labels, ensure_ascii=False), tid]); con.commit()
        except Exception:
            pass
    db.close()
    print(f'✓ trade#{tid} 录入，labels={labels}')
    return tid


def main():
    # IMG_1893 多单
    t1 = add_one('2026-01-02 12:48:00', 'long', 15, 88193.9, 88660.4, 7.89, r'C:\\Users\\zuoho\\Pictures\\IMG_1893.jpg')
    # IMG_1894 空单
    t2 = add_one('2026-01-02 12:50:00', 'short', 15, 88843.7, 88681.5, 2.55, r'C:\\Users\\zuoho\\Pictures\\IMG_1894.jpg')
    print('结果: ', t1, t2)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()

