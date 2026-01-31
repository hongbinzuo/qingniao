"""
Search for ABU pattern data in database
"""

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Connect to database
db_path = ROOT / "src" / "data" / "qingniao.db"
conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 80)
print("SEARCHING FOR ABU PATTERNS")
print("=" * 80)

# Check each table for pattern-related data
for table in tables:
    table_name = table[0]
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    print(f"\n{table_name}: {count} rows")

    # Check if this table has pattern-related columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    col_names = [col[1] for col in columns]

    if any(
        "pattern" in col.lower() or "image" in col.lower() or "page" in col.lower()
        for col in col_names
    ):
        print(f"  Potential pattern table! Columns: {', '.join(col_names)}")

        # Show sample data
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
        rows = cursor.fetchall()
        for row in rows:
            print(f"  Sample: {row}")

conn.close()
