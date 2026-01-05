import duckdb, json
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
rows=con.execute("""
SELECT e.id as eval_id, s.id as signal_id, s.signal_time, s.timeframe, s.signal_type, 
       s.entry_price, s.stop_loss, s.take_profit_1, s.take_profit_2,
       e.evaluation_time, e.actual_profit_pct, e.stop_loss_hit, e.take_profit_1_hit, e.take_profit_2_hit, e.missed
FROM signal_evaluations e
JOIN trading_signals s ON s.id=e.signal_id
WHERE e.result='stopped'
ORDER BY e.evaluation_time DESC
LIMIT 2
""").fetchall()
print('EXAMPLES', rows)
con.close()
