import duckdb
DB = r'C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb'
con = duckdb.connect(DB, read_only=True)
rows = con.execute(
    """
    SELECT id, timestamp, direction, entry_price, exit_price, screenshot_path
    FROM trade_records
    WHERE screenshot_path ILIKE '%IMG_1905%'
       OR screenshot_path ILIKE '%IMG_1906%'
       OR screenshot_path ILIKE '%IMG_1907%'
       OR screenshot_path ILIKE '%IMG_1908%'
    ORDER BY id
    """
).fetchall()
con.close()
print('rows=', len(rows))
for r in rows:
    print(r)

