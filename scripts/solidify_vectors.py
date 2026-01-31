#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vector Solidification Script - ABU System v3.0

Purpose: Audit and enhance the 1000 Brooks pattern vectors
- Add outcome labels (expected_outcome, win_probability, typical_rr)
- Normalize vector dimensions to 32-dim
- Fill missing fields with proper defaults
- Validate consistency across all patterns

Usage:
    python scripts/solidify_vectors.py --audit-only
    python scripts/solidify_vectors.py --fix --dry-run
    python scripts/solidify_vectors.py --fix --commit
"""

import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
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


# Pattern outcome mapping based on Brooks theory
PATTERN_OUTCOMES = {
    # Trend Continuation Patterns
    "Small Pullback Bull Trend": {
        "expected_outcome": "bullish_continuation",
        "win_probability": 0.65,
        "typical_rr": 2.0,
        "invalidation": "break_below_ema",
    },
    "Small Pullback Bear Trend": {
        "expected_outcome": "bearish_continuation",
        "win_probability": 0.65,
        "typical_rr": 2.0,
        "invalidation": "break_above_ema",
    },
    "Tight Bull Channel": {
        "expected_outcome": "bullish_continuation",
        "win_probability": 0.70,
        "typical_rr": 1.5,
        "invalidation": "break_below_channel",
    },
    "Tight Bear Channel": {
        "expected_outcome": "bearish_continuation",
        "win_probability": 0.70,
        "typical_rr": 1.5,
        "invalidation": "break_above_channel",
    },
    # Reversal Patterns
    "Double Bottom": {
        "expected_outcome": "bullish_reversal",
        "win_probability": 0.55,
        "typical_rr": 2.5,
        "invalidation": "break_below_second_low",
    },
    "Double Top": {
        "expected_outcome": "bearish_reversal",
        "win_probability": 0.55,
        "typical_rr": 2.5,
        "invalidation": "break_above_second_high",
    },
    "Major Trend Reversal": {
        "expected_outcome": "trend_reversal",
        "win_probability": 0.50,
        "typical_rr": 3.0,
        "invalidation": "failed_reversal_bar",
    },
    # Breakout Patterns
    "Triangle Breakout": {
        "expected_outcome": "breakout_continuation",
        "win_probability": 0.60,
        "typical_rr": 2.0,
        "invalidation": "failed_breakout",
    },
    "Wedge Breakout": {
        "expected_outcome": "breakout_continuation",
        "win_probability": 0.58,
        "typical_rr": 2.5,
        "invalidation": "return_to_wedge",
    },
    # Gap Patterns
    "Measuring Gap": {
        "expected_outcome": "trend_continuation",
        "win_probability": 0.68,
        "typical_rr": 2.0,
        "invalidation": "gap_fill",
    },
    "Exhaustion Gap": {
        "expected_outcome": "trend_exhaustion",
        "win_probability": 0.52,
        "typical_rr": 1.5,
        "invalidation": "continuation_after_gap",
    },
    # Trading Range Patterns
    "Trading Range": {
        "expected_outcome": "range_bound",
        "win_probability": 0.50,
        "typical_rr": 1.0,
        "invalidation": "breakout_either_side",
    },
}

# Default outcome for unknown patterns
DEFAULT_OUTCOME = {
    "expected_outcome": "unknown",
    "win_probability": 0.50,
    "typical_rr": 1.5,
    "invalidation": "pattern_invalidated",
}


class VectorSolidifier:
    """Solidify and enhance Brooks pattern vectors"""

    def __init__(self, trader_id: str = "abu"):
        if not DB_AVAILABLE:
            raise RuntimeError("Database not available")

        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)

        # Statistics
        self.stats = {
            "total_patterns": 0,
            "missing_outcome": 0,
            "missing_win_prob": 0,
            "missing_rr": 0,
            "missing_direction": 0,
            "inconsistent_vectors": 0,
            "patterns_by_type": defaultdict(int),
            "patterns_by_outcome": defaultdict(int),
        }

    def audit_patterns(self) -> Dict:
        """Audit current pattern library for missing fields"""
        print("\n" + "=" * 80)
        print("AUDIT: Brooks Pattern Library")
        print("=" * 80)

        conn = self.db._get_connection()

        try:
            # Get all patterns
            patterns = conn.execute("""
                SELECT
                    pattern_id,
                    pattern_name,
                    pattern_type,
                    direction,
                    confidence,
                    structured_features
                FROM pattern_library
                ORDER BY page
            """).fetchall()

            self.stats["total_patterns"] = len(patterns)
            print(f"\nTotal patterns: {len(patterns)}")

            # Analyze each pattern
            issues = []
            for p in patterns:
                pattern_id = p["pattern_id"]
                pattern_name = p["pattern_name"]
                pattern_type = p["pattern_type"]
                direction = p["direction"]
                features = p["structured_features"] or {}

                # Track pattern types
                if pattern_type:
                    self.stats["patterns_by_type"][pattern_type] += 1

                # Check for missing fields
                pattern_issues = []

                if not features.get("expected_outcome"):
                    self.stats["missing_outcome"] += 1
                    pattern_issues.append("missing_outcome")

                if not features.get("win_probability"):
                    self.stats["missing_win_prob"] += 1
                    pattern_issues.append("missing_win_probability")

                if not features.get("typical_rr"):
                    self.stats["missing_rr"] += 1
                    pattern_issues.append("missing_typical_rr")

                if not direction:
                    self.stats["missing_direction"] += 1
                    pattern_issues.append("missing_direction")

                if pattern_issues:
                    issues.append(
                        {
                            "pattern_id": pattern_id,
                            "pattern_name": pattern_name,
                            "issues": pattern_issues,
                        }
                    )

            # Print summary
            print("\n" + "-" * 80)
            print("AUDIT SUMMARY")
            print("-" * 80)
            print(
                f"Missing outcome labels:      {self.stats['missing_outcome']:4d} / {len(patterns)}"
            )
            print(
                f"Missing win probability:     {self.stats['missing_win_prob']:4d} / {len(patterns)}"
            )
            print(
                f"Missing typical RR:          {self.stats['missing_rr']:4d} / {len(patterns)}"
            )
            print(
                f"Missing direction:           {self.stats['missing_direction']:4d} / {len(patterns)}"
            )

            print("\n" + "-" * 80)
            print("PATTERNS BY TYPE")
            print("-" * 80)
            for ptype, count in sorted(
                self.stats["patterns_by_type"].items(), key=lambda x: -x[1]
            ):
                print(f"  {ptype:30s}: {count:4d}")

            # Show sample issues
            if issues:
                print("\n" + "-" * 80)
                print(f"SAMPLE ISSUES (showing first 10 of {len(issues)})")
                print("-" * 80)
                for issue in issues[:10]:
                    print(f"  {issue['pattern_id']:20s} {issue['pattern_name']:40s}")
                    print(f"    Issues: {', '.join(issue['issues'])}")

            return self.stats

        finally:
            conn.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Solidify Brooks pattern vectors")
    parser.add_argument(
        "--audit-only", action="store_true", help="Only audit, do not fix"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Fix patterns by adding outcome labels"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run (do not commit changes)"
    )
    parser.add_argument(
        "--commit", action="store_true", help="Commit changes to database"
    )

    args = parser.parse_args()

    solidifier = VectorSolidifier("abu")

    # Always run audit first
    stats = solidifier.audit_patterns()

    # Fix if requested
    if args.fix:
        dry_run = not args.commit
        fixed = solidifier.fix_patterns(dry_run=dry_run)

        if dry_run:
            print("\n" + "=" * 80)
            print("DRY RUN COMPLETE - No changes committed")
            print("Run with --commit to apply changes")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print(f"COMMITTED {fixed} pattern updates to database")
            print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())

    def infer_outcome_from_pattern(
        self, pattern_name: str, direction: str, pattern_type: str
    ) -> Dict:
        """Infer outcome labels from pattern name and type"""
        # Try exact match first
        if pattern_name in PATTERN_OUTCOMES:
            return PATTERN_OUTCOMES[pattern_name].copy()

        # Try partial match
        pattern_lower = pattern_name.lower() if pattern_name else ""

        # Trend continuation patterns
        if "small pullback" in pattern_lower or "small pb" in pattern_lower:
            if "bull" in pattern_lower or direction == "long":
                return PATTERN_OUTCOMES["Small Pullback Bull Trend"].copy()
            elif "bear" in pattern_lower or direction == "short":
                return PATTERN_OUTCOMES["Small Pullback Bear Trend"].copy()

        # Channel patterns
        if "tight" in pattern_lower and "channel" in pattern_lower:
            if "bull" in pattern_lower or direction == "long":
                return PATTERN_OUTCOMES["Tight Bull Channel"].copy()
            elif "bear" in pattern_lower or direction == "short":
                return PATTERN_OUTCOMES["Tight Bear Channel"].copy()

        # Default based on direction
        outcome = DEFAULT_OUTCOME.copy()
        if direction == "long":
            outcome["expected_outcome"] = "bullish_unknown"
        elif direction == "short":
            outcome["expected_outcome"] = "bearish_unknown"

        return outcome

    def fix_patterns(self, dry_run: bool = True) -> int:
        """Fix patterns by adding missing outcome labels"""
        print("\n" + "=" * 80)
        print(f"FIX: Adding outcome labels (dry_run={dry_run})")
        print("=" * 80)

        conn = self.db._get_connection()
        fixed_count = 0

        try:
            patterns = conn.execute("""
                SELECT
                    pattern_id,
                    pattern_name,
                    pattern_type,
                    direction,
                    structured_features
                FROM pattern_library
                ORDER BY page
            """).fetchall()

            for p in patterns:
                pattern_id = p["pattern_id"]
                pattern_name = p["pattern_name"]
                pattern_type = p["pattern_type"]
                direction = p["direction"]
                features = p["structured_features"] or {}

                # Check if needs fixing
                needs_fix = (
                    not features.get("expected_outcome")
                    or not features.get("win_probability")
                    or not features.get("typical_rr")
                )

                if not needs_fix:
                    continue

                # Infer outcome
                outcome = self.infer_outcome_from_pattern(
                    pattern_name, direction, pattern_type
                )

                # Update features
                features["expected_outcome"] = outcome["expected_outcome"]
                features["win_probability"] = outcome["win_probability"]
                features["typical_rr"] = outcome["typical_rr"]
                features["invalidation_condition"] = outcome["invalidation"]

                if not dry_run:
                    conn.execute(
                        """
                        UPDATE pattern_library
                        SET structured_features = %s
                        WHERE pattern_id = %s
                    """,
                        (json.dumps(features), pattern_id),
                    )

                fixed_count += 1

                if fixed_count <= 10:
                    print(f"  [{fixed_count}] {pattern_name}")
                    print(f"      Outcome: {outcome['expected_outcome']}")
                    print(f"      Win Prob: {outcome['win_probability']:.2f}")

            if not dry_run:
                conn.commit()

            print(f"\nFixed {fixed_count} patterns")
            return fixed_count

        finally:
            conn.close()
