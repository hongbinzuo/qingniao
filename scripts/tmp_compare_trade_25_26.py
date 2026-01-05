import duckdb
con=duckdb.connect(r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb', read_only=True)
for i in (25,26):
    row=con.execute("SELECT id,timestamp,symbol,direction,entry_price,exit_price,strategy,source,text_content FROM trade_records WHERE id=?", [i]).fetchone()
    print(row)
con.close()
