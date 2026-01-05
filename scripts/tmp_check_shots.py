import duckdb
DB = r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb'
con = duckdb.connect(DB, read_only=True)
q = (
    "SELECT id, timestamp, direction, leverage, entry_price, profit_pct, screenshot_path "
    "FROM trade_records "
    "WHERE screenshot_path LIKE '%IMG_1892.jpg' OR screenshot_path LIKE '%IMG_1893.jpg' OR "
    "      screenshot_path LIKE '%IMG_1894.jpg' OR screenshot_path LIKE '%IMG_1900.jpg' "
    "ORDER BY id"
)
rows = con.execute(q).fetchall()
for r in rows:
    print(r)
con.close()
