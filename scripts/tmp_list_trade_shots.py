import duckdb
con=duckdb.connect(r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb', read_only=True)
rows=con.execute("SELECT id,timestamp,screenshot_path FROM trade_records ORDER BY id DESC LIMIT 10").fetchall()
for r in rows:
    print(r)
con.close()
