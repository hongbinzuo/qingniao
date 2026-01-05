import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
rows=con.execute("""
SELECT timeframe, signal_type, ROUND(entry_price,6) entry, ROUND(stop_loss,6) stop, COUNT(*) c,
       MIN(created_at) first_ts, MAX(created_at) last_ts
FROM trading_signals
WHERE DATE(created_at)=CURRENT_DATE
GROUP BY 1,2,3,4
HAVING COUNT(*)>1
ORDER BY c DESC
""").fetchall()
print('DUPES_TODAY', rows)
con.close()
