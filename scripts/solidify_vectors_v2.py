#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector Solidification Script v2 - ABU System
Works with actual pattern_vectors table schema

Purpose: Add outcome labels to 938 Brooks pattern vectors
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from db_manager_trader import TraderDBManager

    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("[ERROR] db_manager_trader not available")
    sys.exit(1)


# Pattern outcome mapping
PATTERN_OUTCOMES = {
    # Channels
    "channel": {
        "bullish": {"outcome": "bullish_continuation", "win_prob": 0.65, "rr": 2.0},
        "bearish": {"outcome": "bearish_continuation", "win_prob": 0.65, "rr": 2.0},
        "neutral": {"outcome": "range_bound", "win_prob": 0.50, "rr": 1.5},
    },
    # Triangles
    "triangle": {
        "bullish": {"outcome": "bullish_breakout", "win_prob": 0.60, "rr": 2.5},
        "bearish": {"outcome": "bearish_breakout", "win_prob": 0.60, "rr": 2.5},
        "neutral": {"outcome": "breakout_pending", "win_prob": 0.55, "rr": 2.0},
    },
    # Wedges
    "wedge": {
        "bullish": {"outcome": "bullish_reversal", "win_prob": 0.58, "rr": 2.5},
        "bearish": {"outcome": "bearish_reversal", "win_prob": 0.58, "rr": 2.5},
        "neutral": {"outcome": "reversal_pending", "win_prob": 0.52, "rr": 2.0},
    },
    # Gaps
    "gap": {
        "bullish": {"outcome": "bullish_continuation", "win_prob": 0.68, "rr": 2.0},
        "bearish": {"outcome": "bearish_continuation", "win_prob": 0.68, "rr": 2.0},
        "neutral": {"outcome": "gap_fill", "win_prob": 0.50, "rr": 1.5},
    },
    # Breakouts
    "breakout": {
        "bullish": {"outcome": "bullish_breakout", "win_prob": 0.62, "rr": 2.0},
        "bearish": {"outcome": "bearish_breakout", "win_prob": 0.62, "rr": 2.0},
        "neutral": {"outcome": "breakout_pending", "win_prob": 0.55, "rr": 1.8},
    },
    # Trends
    "trend": {
        "bullish": {"outcome": "bullish_continuation", "win_prob": 0.70, "rr": 2.0},
        "bearish": {"outcome": "bearish_continuation", "win_prob": 0.70, "rr": 2.0},
        "neutral": {"outcome": "trend_unclear", "win_prob": 0.50, "rr": 1.5},
    },
    # Reversals
    "reversal": {
        "bullish": {"outcome": "bullish_reversal", "win_prob": 0.55, "rr": 3.0},
        "bearish": {"outcome": "bearish_reversal", "win_prob": 0.55, "rr": 3.0},
        "neutral": {"outcome": "reversal_pending", "win_prob": 0.50, "rr": 2.5},
    },
    # Range
    "range": {
        "bullish": {"outcome": "range_long", "win_prob": 0.50, "rr": 1.0},
        "bearish": {"outcome": "range_short", "win_prob": 0.50, "rr": 1.0},
        "neutral": {"outcome": "range_bound", "win_prob": 0.50, "rr": 1.0},
    },
}

DEFAULT_OUTCOME = {"outcome": "unknown", "win_prob": 0.50, "rr": 1.5}


class VectorSolidifier:
    """Solidify pattern vectors by adding outcome labels"""

    def __init__(self, trader_id: str = "abu"):
        if not DB_AVAILABLE:
            raise RuntimeError("Database not available")

        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.stats = defaultdict(int)

    def infer_outcome(self, pattern_features: Dict, market_context: Dict) -> Dict:
        """Infer outcome from pattern features"""
        primary = (pattern_features.get("primary") or "").lower()
        direction = (pattern_features.get("direction") or "neutral").lower()

        # Normalize direction
        if direction in ("long", "bull", "bullish"):
            direction = "bullish"
        elif direction in ("short", "bear", "bearish"):
            direction = "bearish"
        else:
            direction = "neutral"

        # Get outcome mapping
        if primary in PATTERN_OUTCOMES:
            outcome_map = PATTERN_OUTCOMES[primary].get(direction, DEFAULT_OUTCOME)
        else:
            outcome_map = DEFAULT_OUTCOME.copy()

        return {
            "expected_outcome": outcome_map["outcome"],
            "win_probability": outcome_map["win_prob"],
            "typical_rr": outcome_map["rr"],
            "invalidation_condition": f"{primary}_invalidated",
        }

    def audit_vectors(self) -> Dict:
        """Audit pattern_vectors table"""
        print("\n" + "=" * 80)
        print("AUDIT: Pattern Vectors Table")
        print("=" * 80)

        conn = self.db._get_connection()

        try:
            total = conn.execute("SELECT COUNT(*) FROM pattern_vectors").fetchone()[0]
            self.stats["total"] = total
            print(f"\nTotal vectors: {total}")

            rows = conn.execute("""
                SELECT id, pattern_features, metadata
                FROM pattern_vectors
            """).fetchall()

            for row in rows:
                pf = row[1] or {}
                meta = row[2] or {}

                primary = pf.get("primary", "unknown")
                self.stats[f"type_{primary}"] += 1

                if not meta.get("expected_outcome"):
                    self.stats["missing_outcome"] += 1

            print(f"Missing outcome labels: {self.stats['missing_outcome']} / {total}")
            return dict(self.stats)

        finally:
            conn.close()

    def fix_vectors(self, dry_run: bool = True) -> int:
        """Add outcome labels to vectors missing them"""
        print("\n" + "=" * 80)
        print(f"FIX VECTORS: {'DRY RUN' if dry_run else 'COMMIT MODE'}")
        print("=" * 80)

        conn = self.db._get_connection()
        fixed_count = 0

        try:
            # Fetch all vectors
            rows = conn.execute("""
                SELECT id, pattern_features, market_context, metadata
                FROM pattern_vectors
            """).fetchall()

            # Get a cursor for updates
            cursor = conn.cursor()

            for row in rows:
                vec_id = row[0]
                pf = row[1] or {}
                mc = row[2] or {}
                meta = row[3] or {}

                # Skip if already has outcome
                if meta.get("expected_outcome"):
                    continue

                # Infer outcome
                outcome = self.infer_outcome(pf, mc)

                # Merge with existing metadata
                updated_meta = {**meta, **outcome}

                if not dry_run:
                    cursor.execute(
                        """
                        UPDATE pattern_vectors
                        SET metadata = %s::jsonb
                        WHERE id = %s
                        """,
                        (json.dumps(updated_meta), vec_id),
                    )

                fixed_count += 1

                if fixed_count % 100 == 0:
                    print(f"  Processed {fixed_count} vectors...")

            cursor.close()

            if not dry_run:
                conn.commit()
                print(f"\n✓ Fixed {fixed_count} vectors (committed)")
            else:
                print(f"\n✓ Would fix {fixed_count} vectors (dry run)")

            return fixed_count

        except Exception as e:
            if not dry_run:
                conn.rollback()
            print(f"\n✗ Error: {e}")
            raise

        finally:
            conn.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Solidify Brooks pattern vectors with outcome labels"
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="Only audit, don't fix",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix vectors (dry run by default)",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes to database",
    )

    args = parser.parse_args()

    solidifier = VectorSolidifier(trader_id="abu")

    # Always audit first
    stats = solidifier.audit_vectors()

    # Fix if requested
    if args.fix:
        dry_run = not args.commit
        fixed = solidifier.fix_vectors(dry_run=dry_run)

        # Audit again to verify
        if not dry_run:
            print("\n" + "=" * 80)
            print("POST-FIX AUDIT")
            print("=" * 80)
            solidifier.audit_vectors()

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
