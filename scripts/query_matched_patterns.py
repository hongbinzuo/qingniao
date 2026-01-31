"""
Query pattern details using the correct approach
The pattern_library table uses integer IDs, but we need to extract the numeric part
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from db_manager_trader import TraderDBManager


def query_matched_patterns():
    """Query details for patterns matched in 1H BTC analysis"""

    # Load pattern mapping
    mapping_path = ROOT / "data" / "vector_index" / "pattern_mapping.json"
    with open(mapping_path, "r") as f:
        pattern_mapping = json.load(f)

    # Annoy indices from 1H BTC analysis
    annoy_indices = [111, 757, 916, 1336, 1055]

    print("=" * 80)
    print("MATCHED PATTERNS FROM 1H BTC ANALYSIS")
    print("=" * 80)
    print()

    # Resolve Annoy indices to pattern IDs
    print("Resolving Annoy indices to pattern IDs:")
    pattern_info = []
    for idx in annoy_indices:
        pattern_id = pattern_mapping.get(str(idx))
        if pattern_id:
            print(f"  Annoy[{idx}] -> {pattern_id}")

            # Extract numeric ID for gemini_flash patterns
            if pattern_id.startswith("gemini_flash_"):
                numeric_id = int(pattern_id.replace("gemini_flash_", ""))
                pattern_info.append((idx, pattern_id, numeric_id, "gemini"))
            elif pattern_id.startswith("brooks_rule_"):
                # Brooks rules: extract the number after brooks_rule_
                match = re.search(r"brooks_rule_(\d+)", pattern_id)
                if match:
                    numeric_id = int(match.group(1))
                    pattern_info.append((idx, pattern_id, numeric_id, "brooks"))
            else:
                pattern_info.append((idx, pattern_id, None, "unknown"))
        else:
            print(f"  Annoy[{idx}] -> NOT FOUND in mapping")

    print()

    # Query database
    db = TraderDBManager()

    for annoy_idx, pattern_id, numeric_id, source in pattern_info:
        print(f"\n{'=' * 80}")
        print(f"PATTERN: Annoy[{annoy_idx}] = {pattern_id}")
        print(f"Source: {source.upper()}, Numeric ID: {numeric_id}")
        print(f"{'=' * 80}")

        if source == "gemini" and numeric_id:
            # Query gemini_flash pattern
            query = """
            SELECT
                id, pattern_name, pattern_type, direction,
                source_page, image_path, text_description,
                key_features, timeframe_hint, confidence
            FROM pattern_library
            WHERE id = %s
            """

            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(query, (numeric_id,))
                result = cursor.fetchone()

                if result:
                    print(f"\n[BASIC INFO]")
                    print(f"  Database ID: {result[0]}")
                    print(f"  Pattern Name: {result[1]}")
                    print(f"  Type: {result[2]}")
                    print(f"  Direction: {result[3]}")
                    print(f"  Source Page: {result[4]}")
                    print(f"  Image Path: {result[5]}")

                    # Extract image number
                    if result[5]:
                        match = re.search(r"(\d+)", result[5])
                        if match:
                            print(f"  IMAGE NUMBER: {match.group(1)}")

                    print(f"\n[DESCRIPTION]")
                    desc = result[6] if result[6] else "N/A"
                    print(f"  {desc[:400]}...")

                    print(f"\n[KEY FEATURES]")
                    print(f"  {result[7] if result[7] else 'N/A'}")

                    print(f"\n[TIMEFRAME]")
                    print(f"  {result[8] if result[8] else 'N/A'}")

                    print(f"\n[CONFIDENCE]")
                    print(f"  {result[9] if result[9] else 'N/A'}")
                else:
                    print(
                        f"  [NOT FOUND] Gemini pattern ID {numeric_id} not in database"
                    )

                cursor.close()
                db.return_connection(conn)

            except Exception as e:
                print(f"  [ERROR] {e}")

        elif source == "brooks":
            # Brooks rules are from ebook_knowledge_base, not pattern_library
            print(f"\n[BROOKS RULE]")
            print(f"  This is a Brooks trading rule from the ebook knowledge base")
            print(f"  Rule Number: {numeric_id}")
            print(f"  Pattern ID: {pattern_id}")
            print(f"  Note: Brooks rules are theoretical patterns, not chart images")

    print(f"\n{'=' * 80}")
    print("QUERY COMPLETE")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    query_matched_patterns()
