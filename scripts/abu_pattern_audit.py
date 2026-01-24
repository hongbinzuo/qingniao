#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run ABU pattern library audit and write a Markdown report."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.pattern_audit import run_pattern_audit  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser(description="ABU pattern library audit")
    parser.add_argument("--since-days", type=int, default=30)
    parser.add_argument("--min-confidence", type=float, default=0.3)
    parser.add_argument("--max-duplicates", type=int, default=20)
    parser.add_argument("--max-unused", type=int, default=50)
    args = parser.parse_args()

    report = run_pattern_audit(
        trader_id="abu",
        output_dir=ROOT / "outputs" / "trading_signals",
        since_days=args.since_days,
        min_confidence=args.min_confidence,
        max_duplicates=args.max_duplicates,
        max_unused=args.max_unused,
    )
    if report:
        print(f"✓ Wrote: {report}")
        return 0
    print("[WARN] Pattern audit skipped (pattern library unavailable)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
