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
from de_tactics import build_bracket_short, build_confirm_long  # type: ignore
from generate_btc_de_signals import get_btc_kline_gateio, get_btc_kline_bitget  # type: ignore
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
            if persona.get('allow_bracket_short', True):
                br = build_bracket_short(cp)
                rr = calculate_risk_reward_ratio(br['entry'], br['stop_loss'], br['take_profit_1'], br['take_profit_2'], 'short')
                if rr.get('avg_rr_ratio', 0) >= 1.5:
                    cands.append(('15m', br))
            if persona.get('allow_confirm_long', True):
                cl = build_confirm_long(cp, k15, k5, default_stop_pts=float(persona.get('default_stop_pts_15m', 400)))
                if cl:
                    cands.append(('15m', cl))
            # write cands into trading_signals table (dedupe logic lives in falcon; here keep minimal)
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            for tf, s in cands:
                try:
                    db.add_trading_signal(
                        signal_time=now, timeframe=tf, signal_type=s.get('type'), entry_price=s.get('entry'),
                        stop_loss=s.get('stop_loss'), take_profit_1=s.get('take_profit_1'), take_profit_2=s.get('take_profit_2'),
                        entry_model=s.get('entry_model'), strength=s.get('strength'), risk_reward_ratio=None,
                        system_name='de', entry_lower=s.get('entry_lower'), entry_upper=s.get('entry_upper'),
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

