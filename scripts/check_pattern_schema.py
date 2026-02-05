"""
Check pattern_library table schema and sample data
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Add src to path
sys.path.insert(0, str(ROOT / "src"))

from db_manager_trader import TraderDBManager


def check_table():
    """Check pattern_library table"""

    db = TraderDBManager()

    print("=" * 80)
    print("PATTERN_LIBRARY TABLE CHECK")
    print("=" * 80)

    try:
        conn = db.get_connection()
        cursor = conn.cursor()

        # Get sample row to see columns
        query = "SELECT * FROM pattern_library WHERE id = 111 LIMIT 1"
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            print("\nPattern ID 111 found!")
            print(f"Number of columns: {len(result)}")
            print("\nColumn descriptions:")
            for i, desc in enumerate(cursor.description):
                col_name = desc[0]
                print(f"  [{i}] {col_name}")

            print("\nSample data:")
            for i, (desc, value) in enumerate(zip(cursor.description, result)):
                col_name = desc[0]
                val_str = str(value)[:100] if value else "NULL"
                print(f"  {col_name}: {val_str}")
        else:
            print("\nPattern ID 111 not found")

        cursor.close()
        db.return_connection(conn)

    except Exception as e:
        print(f"[ERROR] {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    check_table()
