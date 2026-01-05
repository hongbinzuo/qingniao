import duckdb, json
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
rows=con.execute("SELECT COUNT(*), MIN(signal_time), MAX(signal_time) FROM trading_signals WHERE DATE(signal_time)=CURRENT_DATE").fetchone()
print('SIG_TODAY', rows)
rows2=con.execute("SELECT timeframe, signal_type, COUNT(*) c, ROUND(AVG(risk_reward_ratio),2) avg_rr FROM trading_signals WHERE DATE(signal_time)=CURRENT_DATE GROUP BY 1,2 ORDER BY 1,2").fetchall()
print('SIG_TODAY_BREAKDOWN', rows2)
rows3=con.execute("SELECT id, signal_time, timeframe, signal_type, ROUND(risk_reward_ratio,2) rr FROM trading_signals ORDER BY id DESC LIMIT 8").fetchall()
print('SIG_LAST', rows3)
ev=con.execute("SELECT result, COUNT(*) FROM signal_evaluations GROUP BY result").fetchall()
print('EVAL_DIST', ev)
pend=con.execute("SELECT COUNT(*) FROM trading_signals WHERE status='pending'").fetchone()[0]
print('PENDING', pend)
con.close()
