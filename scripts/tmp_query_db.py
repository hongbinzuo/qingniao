import duckdb, json
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
counts={}
for t in ['conversations','trading_signals','signal_evaluations','trade_records','trader_viewpoints']:
    try:
        counts[t]=con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    except Exception as e:
        counts[t]=str(e)
print('COUNTS', json.dumps(counts, ensure_ascii=False))
try:
    rows=con.execute('SELECT id, symbol, direction, entry_price, stop_loss, take_profit_1, take_profit_2, entry_time, source FROM trade_records ORDER BY id DESC LIMIT 10').fetchall()
    print('SAMPLE_TRADES', rows)
except Exception as e:
    print('SAMPLE_TRADES_ERR', e)
try:
    rows=con.execute('SELECT id, timeframe, signal_type, entry_price, stop_loss, take_profit_1, take_profit_2, signal_time, system_name FROM trading_signals ORDER BY id DESC LIMIT 10').fetchall()
    print('SAMPLE_SIGNALS', rows)
except Exception as e:
    print('SAMPLE_SIGNALS_ERR', e)
try:
    rows=con.execute('SELECT id, signal_id, evaluation_time, result, actual_profit_pct FROM signal_evaluations ORDER BY id DESC LIMIT 10').fetchall()
    print('SAMPLE_EVALS', rows)
except Exception as e:
    print('SAMPLE_EVALS_ERR', e)
con.close()
