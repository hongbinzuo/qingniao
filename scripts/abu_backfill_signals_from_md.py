#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill ABU trading signals from ABU_top*.md into Postgres.
"""
from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import sys

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager  # type: ignore


def _parse_time_from_name(path: Path) -> Optional[str]:
    m = re.search(r"ABU_top\\d+_(\\w+)_([0-9]{8})_([0-9]{4})", path.name)
    if not m:
        return None
    date_part = m.group(2)
    time_part = m.group(3)
    try:
        dt = datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _parse_timeframe_from_name(path: Path) -> Optional[str]:
    m = re.search(r"ABU_top\\d+_(\\w+)_", path.name)
    return m.group(1) if m else None


def _extract_rows(path: Path) -> List[Dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_idx = None
    header = []
    for i, line in enumerate(lines):
        if line.startswith("| #"):
            header_idx = i
            header = [h.strip().lower() for h in line.strip("|").split("|")]
            break
    if header_idx is None:
        return []
    rows = []
    for line in lines[header_idx + 2 :]:
        if not line.startswith("|"):
            break
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != len(header):
            continue
        row = {header[i]: parts[i] for i in range(len(header))}
        rows.append(row)
    return rows


def _to_float(value: str) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _exists(conn, signal_time: str, timeframe: str, symbol: str) -> bool:
    row = conn.execute(
        """
        SELECT id FROM trading_signals
        WHERE system_name = ?
          AND signal_time = ?
          AND timeframe = ?
          AND symbol = ?
        LIMIT 1
        """,
        ("abu", signal_time, timeframe, symbol),
    ).fetchone()
    return bool(row)


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill ABU signals from MD.")
    parser.add_argument("--dir", default=str(ROOT / "outputs" / "trading_signals"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base_dir = Path(args.dir)
    files = sorted(base_dir.glob("ABU_top*_*.md"))
    if not files:
        print("No ABU_top files found.")
        return 1

    db = TraderDBManager("abu")
    conn = db._get_connection(read_only=True)
    inserted = 0
    skipped = 0
    total_rows = 0

    for path in files:
        signal_time = _parse_time_from_name(path)
        timeframe = _parse_timeframe_from_name(path)
        if not signal_time or not timeframe:
            continue
        rows = _extract_rows(path)
        for row in rows:
            total_rows += 1
            symbol = (row.get("symbol") or "").upper()
            if not symbol:
                skipped += 1
                continue
            if _exists(conn, signal_time, timeframe, symbol):
                skipped += 1
                continue

            signal_type = (row.get("type") or "").lower()
            entry = _to_float(row.get("entry") or "")
            sl = _to_float(row.get("sl") or "")
            tp1 = _to_float(row.get("tp1") or "")
            tp2 = _to_float(row.get("tp2") or "")
            match = row.get("match") or ""
            reason = row.get("reason") or ""
            notes = f"Match:{match} Reason:{reason}".strip()
            payload = {
                "signal_time": signal_time,
                "timeframe": timeframe,
                "symbol": symbol,
                "signal_type": signal_type or "long",
                "entry_price": entry or 0.0,
                "stop_loss": sl or 0.0,
                "take_profit_1": tp1 or 0.0,
                "take_profit_2": tp2 or 0.0,
                "entry_model": None,
                "strength": "medium",
                "system_name": "abu",
                "score": None,
                "notes": notes,
                "status": "pending",
            }
            if args.dry_run:
                inserted += 1
            else:
                db.add_trading_signal(payload)
                inserted += 1

    conn.close()
    db.close()
    print(f"rows={total_rows} inserted={inserted} skipped={skipped} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
