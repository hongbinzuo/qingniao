import sys
sys.path.insert(0, 'src')
from db_manager_trader import TraderDBManager
from pathlib import Path

db = TraderDBManager('abu')
conn = db._get_connection()

# 检查有clip的文件
recs = conn.execute("SELECT id, image_path FROM pattern_library WHERE image_path LIKE '%clip%' LIMIT 5").fetchall()
print("包含clip的路径:")
for r in recs:
    print(f"ID={r[0]}, 路径={r[1]}")

# 检查前几条记录
recs2 = conn.execute("SELECT id, image_path FROM pattern_library LIMIT 10").fetchall()
print("\n前10条记录:")
for r in recs2:
    p = Path(r[1]) if r[1] else None
    exists = p.exists() if p else False
    print(f"ID={r[0]}, 路径={r[1][:60] if r[1] else 'N/A'}, 存在={exists}")

db.close()



