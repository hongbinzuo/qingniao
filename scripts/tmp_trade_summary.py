import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
q_total = "SELECT COUNT(*) FROM trade_records"
q_entry = "SELECT COUNT(*) FROM trade_records WHERE entry_price IS NOT NULL"
q_exit = "SELECT COUNT(*) FROM trade_records WHERE exit_price IS NOT NULL"
q_profit = "SELECT COUNT(*) FROM trade_records WHERE profit_pct IS NOT NULL OR profit_usdt IS NOT NULL"
q_recent = "SELECT id, timestamp, symbol, direction, entry_price, exit_price, profit_pct FROM trade_records ORDER BY id DESC LIMIT 5"
print('trade_counts', con.execute(q_total).fetchone()[0], con.execute(q_entry).fetchone()[0], con.execute(q_exit).fetchone()[0], con.execute(q_profit).fetchone()[0])
print('recent', con.execute(q_recent).fetchall())
con.close()
