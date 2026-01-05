import duckdb, json
con=duckdb.connect(r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb', read_only=True)
rows=con.execute("SELECT id, timestamp, substr(trader_message,1,30) FROM conversations WHERE date(timestamp)='2026-01-03' ORDER BY id DESC LIMIT 8").fetchall()
print('LAST_CONV', json.dumps(rows, ensure_ascii=False))
cnt=con.execute("SELECT COUNT(*) FROM conversations WHERE date(timestamp)='2026-01-03'").fetchone()[0]
print('COUNT_2026-01-03', cnt)
con.close()
