#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Echo key runtime status for De. system after reboot.
- Falcon state (running/last_run/files)
- Latest signal_time group + items
- Latest bracket signal (DeBracketShort)
- Pending/eval counts
- Recent learning/eval reports
"""
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT/'trading_signals'/'/.falcon_state.json'
DB = str(ROOT/'src'/'data'/'qingniao_de.duckdb')
LRDIR = ROOT/'trading_signals'/'/.learning_reports'

def echo_state():
    if STATE.exists():
        try:
            st = json.loads(STATE.read_text(encoding='utf-8'))
            print(f"Falcon: running={st.get('running')} last_ok={st.get('last_ok')} last_run={st.get('last_run')} pid={st.get('pid')}")
            lfs = st.get('last_files') or []
            if lfs:
                print('Recent files:'); [print(f'- {x}') for x in lfs[:4]]
        except Exception as e:
            print(f"Falcon: state read failed: {e}")
    else:
        print('Falcon: no state file (not started yet)')

def echo_db():
    try:
        con = duckdb.connect(DB, read_only=True)
    except Exception as e:
        print(f'DB open failed: {e}')
        return
    try:
        row = con.execute("SELECT MAX(signal_time) FROM trading_signals").fetchone()
        last = row[0] if row else None
        if last:
            print(f'Latest signals at: {last}')
            rows = con.execute(
                "SELECT timeframe, signal_type, entry_price, stop_loss, take_profit_1, take_profit_2, entry_model, strength, risk_reward_ratio "
                "FROM trading_signals WHERE signal_time=? ORDER BY timeframe",
                [last]
            ).fetchall()
            for r in rows:
                tf, stype, e, sl, tp1, tp2, model, strength, rr = r
                rr_disp = f"{rr:.2f}" if rr is not None else 'N/A'
                print(f"- {tf} {stype} | E={e:.2f} SL={sl:.2f} TP1={tp1 or 0:.2f} TP2={tp2 or 0:.2f} | {model or ''} {strength or ''} | RR={rr_disp}")
        # bracket
        br = con.execute(
            "SELECT id, signal_time, timeframe, entry_lower, entry_upper, entry_price, stop_loss, take_profit_1 "
            "FROM trading_signals WHERE entry_model='DeBracketShort' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if br:
            i, stime, tf, lo, up, mid, sl, tp1 = br
            print(f"Bracket: id#{i} [{stime}] {tf} | {int(lo):,}-{int(up):,} (mid {int(mid):,}) SL {int(sl):,} TP1 {int(tp1):,}")
        # counts
        sig_cnt = con.execute("SELECT COUNT(*) FROM trading_signals").fetchone()[0]
        ev_cnt = con.execute("SELECT COUNT(*) FROM signal_evaluations").fetchone()[0]
        pend = con.execute("SELECT COUNT(*) FROM trading_signals WHERE status='pending'").fetchone()[0]
        print(f"Counts: signals={sig_cnt} evals={ev_cnt} pending={pend}")
    finally:
        con.close()

def echo_reports():
    if not LRDIR.exists():
        return
    files = sorted(LRDIR.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    if files:
        print('Recent reports:'); [print(f'- {p.name}') for p in files]

if __name__ == '__main__':
    echo_state()
    echo_db()
    echo_reports()

