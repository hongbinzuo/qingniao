#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick audit of pattern_library table"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

db = TraderDBManager("abu")
conn = db._get_connection()

# Get count
count = conn.execute("SELECT COUNT(*) FROM pattern_library").fetchone()[0]
print(f"Total patterns: {count}")

# Get sample
sample = conn.execute(
    "SELECT id, pattern_name, pattern_type, direction FROM pattern_library LIMIT 5"
).fetchall()
print("\nSample patterns:")
for row in sample:
    print(f"  ID={row[0]}, Name={row[1]}, Type={row[2]}, Direction={row[3]}")

conn.close()
