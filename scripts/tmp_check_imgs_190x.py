import duckdb
DB = r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb'
con = duckdb.connect(DB, read_only=True)
imgs = [
    r'IMG_1900.jpg', r'IMG_1901.png', r'IMG_1903.png', r'IMG_1904.png', r'IMG_1905.png'
]
for name in imgs:
    rows = con.execute("SELECT id, timestamp, direction, leverage, entry_price, profit_pct, screenshot_path FROM trade_records WHERE screenshot_path LIKE ? ORDER BY id", ['%'+name]).fetchall()
    print(name, '=>', rows if rows else 'NOT_FOUND')
con.close()
