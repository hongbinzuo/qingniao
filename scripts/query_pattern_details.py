"""
Query detailed information for specific pattern IDs from PostgreSQL
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Add src to path
sys.path.insert(0, str(ROOT / "src"))

from db_manager_trader import TraderDBManager


def query_pattern_details(pattern_ids):
    """Query detailed information for given pattern IDs"""

    db = TraderDBManager()

    print("=" * 80)
    print("PATTERN DETAILS QUERY")
    print("=" * 80)
    print()

    for pid in pattern_ids:
        print(f"\n{'=' * 80}")
        print(f"PATTERN ID: {pid}")
        print(f"{'=' * 80}")

        # Query pattern details from pattern_library table
        query = """
        SELECT
            id,
            pattern_name,
            pattern_type,
            direction,
            source_page,
            source_pdf,
            image_path,
            text_description,
            gemini_annotation_json,
            chart_features_json,
            key_features,
            timeframe_hint,
            confidence,
            ebook_references,
            context_text
        FROM pattern_library
        WHERE id = %s
        """

        try:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (pid,))
            result = cursor.fetchone()

            if result:
                print(f"\n[BASIC INFORMATION]")
                print(f"  ID: {result[0]}")
                print(f"  Pattern Name: {result[1]}")
                print(f"  Pattern Type: {result[2]}")
                print(f"  Direction: {result[3]}")
                print(f"  Source Page: {result[4]}")
                print(f"  Source PDF: {result[5]}")
                print(f"  Image Path: {result[6]}")

                # Extract image number from image path if available
                if result[6]:
                    import re

                    match = re.search(r"(\d+)", result[6])
                    if match:
                        print(f"  Image Number: {match.group(1)}")

                print(f"\n[DESCRIPTION]")
                if result[7]:
                    print(f"  {result[7][:500]}...")

                print(f"\n[KEY FEATURES]")
                if result[10]:
                    print(f"  {result[10]}")

                print(f"\n[TIMEFRAME]")
                print(f"  {result[11]}")

                print(f"\n[CONFIDENCE]")
                print(f"  {result[12]}")

                if result[13]:
                    print(f"\n[EBOOK REFERENCES]")
                    print(f"  {result[13]}")

                if result[14]:
                    print(f"\n[CONTEXT]")
                    print(f"  {result[14][:300]}...")
            else:
                print(f"  [NOT FOUND] Pattern ID {pid} not in database")

            cursor.close()
            db.return_connection(conn)

        except Exception as e:
            print(f"  [ERROR] {e}")

    print(f"\n{'=' * 80}")
    print("QUERY COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    pattern_ids = [111, 757, 916, 1336, 1055]
    query_pattern_details(pattern_ids)
