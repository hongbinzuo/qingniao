import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
print('conv_total', con.execute('SELECT COUNT(*) FROM conversations').fetchone()[0])
print('conv_with_price', con.execute('SELECT COUNT(*) FROM conversations WHERE btc_price IS NOT NULL').fetchone()[0])
print('conv_time_range', con.execute('SELECT MIN(timestamp), MAX(timestamp) FROM conversations').fetchone())
# recent price-linked
rows=con.execute("SELECT id, timestamp, btc_price, substr(coalesce(trader_message,user_message,''),1,40) FROM conversations WHERE btc_price IS NOT NULL ORDER BY id DESC LIMIT 5").fetchall()
print('recent_price_linked', rows)
con.close()
