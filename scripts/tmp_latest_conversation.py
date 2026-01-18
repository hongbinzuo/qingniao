#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick helper: print the latest conversation timestamp for De. DB (DuckDB).
Run with Windows Python for DuckDB availability:
  py -3 scripts\tmp_latest_conversation.py
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager  # type: ignore


def main():
    db = TraderDBManager('de')
    con = db._get_connection()
    try:
        row = con.execute("SELECT MAX(timestamp) FROM conversations").fetchone()
        last = row[0] if row else None
        print(last or 'N/A')
    finally:
        db.close()


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

