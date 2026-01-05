import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
q = """
WITH stopped AS (
  SELECT s.id, s.signal_time, s.timeframe, s.signal_type,
         s.entry_price, s.stop_loss,
         CASE WHEN s.signal_type='long'
              THEN (s.entry_price - s.stop_loss) / s.entry_price * 100
              ELSE (s.stop_loss - s.entry_price) / s.entry_price * 100 END AS stop_dist_pct,
         e.evaluation_time
  FROM trading_signals s
  JOIN signal_evaluations e ON e.signal_id = s.id
  WHERE e.result='stopped'
)
SELECT timeframe,
       COUNT(*) AS cnt,
       ROUND(AVG(stop_dist_pct),3) AS avg_pct,
       ROUND(quantile_cont(stop_dist_pct,0.5),3) AS p50,
       ROUND(quantile_cont(stop_dist_pct,0.25),3) AS p25,
       ROUND(quantile_cont(stop_dist_pct,0.75),3) AS p75
FROM stopped
GROUP BY 1
ORDER BY 1;
"""
print('SL_DIST_BY_TF')
for row in con.execute(q).fetchall():
    print(row)
q2 = """
SELECT DATE(signal_time) d, COUNT(*)
FROM trading_signals s JOIN signal_evaluations e ON e.signal_id=s.id AND e.result='stopped'
GROUP BY 1 ORDER BY 1;
"""
print('SL_BY_DATE')
for row in con.execute(q2).fetchall():
    print(row)
q3 = """
SELECT MIN(evaluation_time), MAX(evaluation_time) FROM signal_evaluations WHERE result='stopped';
"""
print('SL_EVAL_RANGE', con.execute(q3).fetchone())
con.close()
