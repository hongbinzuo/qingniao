import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
for t in ['trade_records','trading_signals','signal_evaluations','conversations']:
    try:
        print('SCHEMA', t, con.execute(f"DESCRIBE {t}").fetchall())
    except Exception as e:
        print('SCHEMA_ERR', t, e)
con.close()
