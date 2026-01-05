import duckdb
con=duckdb.connect(r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb', read_only=True)
rows=con.execute("SELECT id,timestamp,direction,entry_price,exit_price,stop_distance_points,tp_rule,stop_rule,timeframe FROM trade_records ORDER BY id DESC LIMIT 3").fetchall()
for r in rows: print(r)
con.close()
