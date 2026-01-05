import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
row=con.execute("SELECT COUNT(*), SUM(CASE WHEN risk_reward_ratio>=1.5 THEN 1 ELSE 0 END) FROM trading_signals WHERE DATE(signal_time)=CURRENT_DATE").fetchone()
print('TODAY_GE_1_5', row)
rows=con.execute("SELECT timeframe, SUM(CASE WHEN risk_reward_ratio>=1.5 THEN 1 ELSE 0 END) ge15, COUNT(*) cnt FROM trading_signals WHERE DATE(signal_time)=CURRENT_DATE GROUP BY 1 ORDER BY 1").fetchall()
print('BY_TF_GE1_5', rows)
con.close()
