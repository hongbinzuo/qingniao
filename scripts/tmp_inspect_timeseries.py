import duckdb, os
DB=os.path.join('C:\\Users\\zuoho\\code\\qingniao','data','btc_price_timeseries.duckdb')
con=duckdb.connect(DB, read_only=True)
for t in ['btc_price_5m','btc_price_15m','btc_price_1h']:
    try:
        print('TABLE', t)
        print('SCHEMA', con.execute(f'PRAGMA table_info({t})').fetchall())
        rows=con.execute(f"SELECT * FROM {t} ORDER BY timestamp DESC LIMIT 2").fetchall()
        print('SAMPLE', rows)
    except Exception as e:
        print('ERR', t, e)
print('MAX_1h', con.execute('SELECT MAX(timestamp) FROM btc_price_1h').fetchone())
con.close()
