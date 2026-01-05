import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
row=con.execute('SELECT id,timestamp,symbol,direction,leverage,entry_price,exit_price,profit_pct,tech_labels FROM trade_records ORDER BY id DESC LIMIT 1').fetchone()
print(row)
con.close()
