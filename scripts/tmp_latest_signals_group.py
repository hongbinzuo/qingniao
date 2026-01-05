#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import duckdb
DB = r"C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb"
con = duckdb.connect(DB, read_only=True)
row = con.execute("SELECT MAX(signal_time) FROM trading_signals").fetchone()
if not row or not row[0]:
    print('NONE')
    con.close()
    raise SystemExit(0)
last = row[0]
rows = con.execute(
    """
    SELECT timeframe, signal_type, entry_price, stop_loss, take_profit_1, take_profit_2, entry_model, strength, risk_reward_ratio
    FROM trading_signals WHERE signal_time = ? ORDER BY timeframe
    """, [last]
).fetchall()
print('LAST_TIME', last)
for r in rows:
    tf, stype, e, sl, tp1, tp2, model, strength, rr = r
    print(f"- {tf} {stype} | E={e:.2f} SL={sl:.2f} TP1={tp1 or 0:.2f} TP2={tp2 or 0:.2f} | {model or ''} {strength or ''} | RR={rr if rr is not None else 'N/A'}")
con.close()
