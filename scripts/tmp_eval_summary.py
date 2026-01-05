import duckdb
con=duckdb.connect('src\\data\\qingniao_de.duckdb')
rows=con.execute("SELECT result, COUNT(*) FROM signal_evaluations GROUP BY result ORDER BY COUNT(*) DESC").fetchall()
print('eval_result_counts', rows)
# link to how many evaluations link to signals after date
rows2=con.execute("SELECT MIN(evaluation_time), MAX(evaluation_time) FROM signal_evaluations").fetchall()
print('eval_time_range', rows2)
con.close()
