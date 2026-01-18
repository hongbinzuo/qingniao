#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De. watcher (skeleton): each N minutes fetch price snapshot, generate tactics gated by persona,
and write signals to DB (using scripts/falcon.py generation path as reference).
"""
from __future__ import annotations
import sys, time
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from persona_config import load_persona  # type: ignore
from de_tactics import build_bracket_short, build_confirm_long, build_confirm_short  # type: ignore
from generate_btc_de_signals import get_btc_kline_gateio, get_btc_kline_bitget, analyze_timeframe, validate_signal  # type: ignore
from volatility_analyzer import calculate_risk_reward_ratio  # type: ignore
from db_manager_trader import TraderDBManager  # type: ignore
from realtime_feed import get_snapshot  # type: ignore

def main(interval_sec: int = 300):
    db = TraderDBManager('de')
    while True:
        try:
            snap = get_snapshot()
            cp = snap.get('mid')
            k5 = get_btc_kline_gateio('5m', 200) or get_btc_kline_bitget('5m', 200)
            k15 = get_btc_kline_gateio('15m', 200) or get_btc_kline_bitget('15m', 200)
            if not cp or not k5 or not k15:
                time.sleep(interval_sec); continue
            persona = load_persona()
            cands = []
            # 高阶 gating：4h/1h 趋势 + OTE + 5m 拒绝（针对空）
            # 若强多（价格在1h Vegas上方且高于VWAP），禁用挂空；若震荡/偏空，挂空可用
            tf_map = {'5m':'5m','15m':'15m','1h':'1h','4h':'4h'}
            a1h = get_btc_kline_gateio('1h', 200) or get_btc_kline_bitget('1h', 200)
            # 简化：用价格相对1h近段均值作为趋势指示（代替Vegas/VWAP）
            strong_bull = False
            if a1h:
                closes = [x['close'] for x in a1h[-55:]]
                ma = sum(closes)/len(closes)
                strong_bull = cp > ma
            if persona.get('allow_bracket_short', True) and not strong_bull:
                br = build_bracket_short(cp)
                rr = calculate_risk_reward_ratio(br['entry'], br['stop_loss'], br['take_profit_1'], br['take_profit_2'], 'short')
                if rr.get('avg_rr_ratio', 0) >= 1.5:
                    cands.append(('15m', br))
            if persona.get('allow_confirm_long', True):
                cl = build_confirm_long(cp, k15, k5, default_stop_pts=float(persona.get('default_stop_pts_15m', 400)))
                if cl:
                    cands.append(('15m', cl))
            # 确认空（对称于确认多）
            cs = build_confirm_short(cp, k15, k5, default_stop_pts=float(persona.get('default_stop_pts_15m', 400)))
            if cs and not strong_bull:
                cands.append(('15m', cs))

            # 现有系统能力的实时聚合（5m/15m 各取一条最佳）
            for tf, kl in [('5m', k5), ('15m', k15)]:
                try:
                    ana = analyze_timeframe(kl, '5分钟' if tf=='5m' else '15分钟', cp)
                    if not ana or not ana.get('signals'):
                        continue
                    filtered = []
                    for s in ana['signals']:
                        text = (s.get('entry_model','') or '') + ' ' + (s.get('reason','') or '')
                        if any(kw in text for kw in ['突破','breakout','区间突破']):
                            continue
                        ok, _ = validate_signal(s, cp, tolerance_pct=0.003)
                        if not ok:
                            continue
                        rr = calculate_risk_reward_ratio(s['entry'], s['stop_loss'], s['take_profit_1'], s['take_profit_2'], s['type'])
                        s['_rr'] = rr
                        filtered.append(s)
                    if not filtered:
                        continue
                    def score(x):
                        strength = 3 if x.get('strength')=='strong' else 2 if x.get('strength')=='medium' else 1
                        return (x['_rr'].get('avg_rr_ratio',0)*0.6 + strength*0.2)
                    best = sorted(filtered, key=score, reverse=True)[0]
                    if strong_bull and best.get('type')=='short':
                        continue
                    cands.append((tf, {
                        'type': best['type'], 'strength': best.get('strength'), 'entry': best['entry'],
                        'stop_loss': best['stop_loss'], 'take_profit_1': best['take_profit_1'], 'take_profit_2': best['take_profit_2'],
                        'entry_model': best.get('entry_model') or 'Aggregator', 'reason': best.get('reason'),
                        'stop_rule': 'as_is', 'tp_rule': 'as_is', 'stop_distance_points': abs(best['entry']-best['stop_loss'])
                    }))
                except Exception:
                    pass
            # write cands into trading_signals table (dedupe logic lives in falcon; here keep minimal)
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            for tf, s in cands:
                try:
                    db.add_trading_signal(
                        signal_time=now, timeframe=tf, signal_type=s.get('type'), entry_price=s.get('entry'),
                        stop_loss=s.get('stop_loss'), take_profit_1=s.get('take_profit_1'), take_profit_2=s.get('take_profit_2'),
                        entry_model=s.get('entry_model'), strength=s.get('strength'), risk_reward_ratio=None,
                        system_name='de_watcher', entry_lower=s.get('entry_lower'), entry_upper=s.get('entry_upper'),
                        stop_distance_points=s.get('stop_distance_points'), tp_rule=s.get('tp_rule'), stop_rule=s.get('stop_rule'),
                        bracket_note=s.get('bracket_note'),
                    )
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(interval_sec)

if __name__ == '__main__':
    main()
