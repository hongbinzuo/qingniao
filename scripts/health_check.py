#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check - Validate runtime prerequisites for batch scanning.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _print(status: bool, label: str, detail: Optional[str] = None) -> None:
    icon = "OK" if status else "FAIL"
    if detail:
        print(f"[{icon}] {label} - {detail}")
    else:
        print(f"[{icon}] {label}")


def check_env() -> bool:
    required = ["PG_HOST", "PG_PORT", "PG_DATABASE", "PG_USER", "PG_PASSWORD"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        _print(False, "Postgres env", f"missing {', '.join(missing)}")
        return False
    _print(True, "Postgres env", "PG_* variables present")
    return True


def check_db() -> bool:
    try:
        from db_manager_trader import TraderDBManager  # type: ignore
    except Exception as exc:
        _print(False, "Postgres driver/import", str(exc))
        return False

    try:
        db = TraderDBManager("abu")
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.execute("SELECT to_regclass('public.trading_signals')")
        row = cur.fetchone()
        table = row[0] if row else None
        cur.close()
        db.return_connection(conn)
    except Exception as exc:
        _print(False, "Postgres connection", str(exc))
        return False

    if not table:
        _print(False, "Postgres schema", "trading_signals table not found")
        return False

    _print(True, "Postgres connection", "trading_signals table found")
    return True


def check_vectors() -> bool:
    index_path = ROOT / "data" / "vectors" / "brooks_patterns_32d.ann"
    id_map_path = ROOT / "data" / "vectors" / "brooks_patterns_id_map.json"
    ok = True
    if not index_path.exists() or index_path.stat().st_size == 0:
        _print(False, "Vector index", str(index_path))
        ok = False
    else:
        _print(True, "Vector index", str(index_path))
    if not id_map_path.exists() or id_map_path.stat().st_size == 0:
        _print(False, "Vector id map", str(id_map_path))
        ok = False
    else:
        _print(True, "Vector id map", str(id_map_path))
    return ok


def check_coincap() -> bool:
    try:
        import requests  # type: ignore
    except Exception as exc:
        _print(False, "CoinCap requests import", str(exc))
        return False
    try:
        resp = requests.get(
            "https://api.coincap.io/v2/assets", params={"limit": 5}, timeout=10
        )
        if resp.status_code != 200:
            _print(False, "CoinCap API", f"status {resp.status_code}")
            return False
        data = resp.json() or {}
        items = data.get("data") or []
        if not items:
            _print(False, "CoinCap API", "empty response")
            return False
    except Exception as exc:
        _print(False, "CoinCap API", str(exc))
        return False
    _print(True, "CoinCap API", "reachable")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Health check for PA scanner")
    parser.add_argument("--skip-db", action="store_true", help="Skip Postgres checks")
    parser.add_argument(
        "--skip-coincap", action="store_true", help="Skip CoinCap API check"
    )
    parser.add_argument(
        "--skip-vectors", action="store_true", help="Skip vector file check"
    )
    args = parser.parse_args()

    print("=" * 72)
    print("PA SCANNER HEALTH CHECK")
    print("=" * 72)

    env_ok = True
    db_ok = True
    vectors_ok = True
    coincap_ok = True

    if not args.skip_db:
        env_ok = check_env()
        if env_ok:
            db_ok = check_db()
    if not args.skip_vectors:
        vectors_ok = check_vectors()
    if not args.skip_coincap:
        coincap_ok = check_coincap()

    overall = all([env_ok, db_ok, vectors_ok, coincap_ok])
    print("-" * 72)
    _print(overall, "Overall", "ready" if overall else "needs attention")
    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    main()
