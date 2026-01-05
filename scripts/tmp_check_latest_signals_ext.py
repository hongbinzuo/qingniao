import duckdb
con=duckdb.connect(r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb', read_only=True)
rows=con.execute("SELECT id, signal_time, timeframe, signal_type, entry_price, entry_lower, entry_upper, stop_loss, take_profit_1, take_profit_2, entry_model FROM trading_signals ORDER BY id DESC LIMIT 6").fetchall()
for r in rows:
    print(r)
con.close()
