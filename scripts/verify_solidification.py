#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick verification of solidified vectors"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

db = TraderDBManager("abu")
conn = db._get_connection()

try:
    rows = conn.execute("""
        SELECT id, pattern_features, metadata
        FROM pattern_vectors
        LIMIT 10
    """).fetchall()

    print("\n" + "=" * 80)
    print("SAMPLE VECTORS (First 10)")
    print("=" * 80)

    for row in rows:
        vec_id = row[0]
        pf = row[1] or {}
        meta = row[2] or {}

        print(f"\nVector ID: {vec_id}")
        print(
            f"  Pattern: {pf.get('primary', 'unknown')} / {pf.get('direction', 'unknown')}"
        )
        print(f"  Expected Outcome: {meta.get('expected_outcome', 'MISSING')}")
        print(f"  Win Probability: {meta.get('win_probability', 'MISSING')}")
        print(f"  Typical RR: {meta.get('typical_rr', 'MISSING')}")

finally:
    conn.close()
