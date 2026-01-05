import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
rows=con.execute('SELECT id,timestamp,direction,leverage,entry_price,profit_pct,tech_labels FROM trade_records ORDER BY id DESC LIMIT 6').fetchall()
print(rows)
con.close()
