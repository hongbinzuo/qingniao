"""
Check database tables and schema
"""

import sqlite3
from pathlib import Path

# Connect to database
db_path = Path(__file__).resolve().parent.parent / "src" / "data" / "qingniao.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 80)
print("DATABASE TABLES")
print("=" * 80)
for table in tables:
    print(f"  - {table[0]}")

print("\n" + "=" * 80)
print("TABLE SCHEMAS")
print("=" * 80)

for table in tables:
    table_name = table[0]
    print(f"\n{table_name}:")
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

conn.close()
