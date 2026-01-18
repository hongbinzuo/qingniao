import duckdb
DB = r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb'
con = duckdb.connect(DB)
con.execute('DELETE FROM trade_records WHERE id=25')
con.close()
print('deleted id=25')

