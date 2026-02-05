"""
Check pattern IDs in database and vector index mapping
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from db_manager_trader import TraderDBManager


def check_patterns():
    db = TraderDBManager()

    print("=" * 80)
    print("CHECKING PATTERN IDS")
    print("=" * 80)

    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Check total patterns
        cursor.execute("SELECT COUNT(*) FROM pattern_library")
        total = cursor.fetchone()[0]
        print(f"\nTotal patterns in database: {total}")

        # Check ID range
        cursor.execute(
            "SELECT MIN(id), MAX(id) FROM pattern_library WHERE id IS NOT NULL AND id::text ~ '^[0-9]+$'"
        )
        result = cursor.fetchone()
        if result and result[0]:
            print(f"ID range: {result[0]} to {result[1]}")

        # Sample some IDs
        cursor.execute(
            "SELECT id, pattern_name, direction FROM pattern_library WHERE id IS NOT NULL LIMIT 10"
        )
        rows = cursor.fetchall()
        print(f"\nSample patterns:")
        for row in rows:
            print(f"  ID {row[0]}: {row[1]} ({row[2]})")

        cursor.close()
        db.return_connection(conn)

    except Exception as e:
        print(f"[ERROR] {e}")

    # Check vector index ID mapping
    print(f"\n{'=' * 80}")
    print("CHECKING VECTOR INDEX ID MAPPING")
    print(f"{'=' * 80}")

    id_map_path = ROOT / "data" / "abu_vector_id_map.json"
    if id_map_path.exists():
        with open(id_map_path, "r") as f:
            id_map = json.load(f)

        print(f"\nVector index entries: {len(id_map)}")
        print(f"\nSample mappings (first 10):")
        for i, (annoy_idx, pattern_id) in enumerate(list(id_map.items())[:10]):
            print(f"  Annoy[{annoy_idx}] -> Pattern ID: {pattern_id}")

        # Check if our target IDs are in the mapping
        print(f"\nChecking target pattern IDs:")
        target_ids = [111, 757, 916, 1336, 1055]
        for tid in target_ids:
            found = str(tid) in id_map.values()
            print(f"  ID {tid}: {'FOUND' if found else 'NOT FOUND'}")
    else:
        print(f"\n[ERROR] ID map file not found: {id_map_path}")


if __name__ == "__main__":
    check_patterns()
