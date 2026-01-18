#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import kline JSON batches into PostgreSQL and optionally move files to deleting/.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager  # noqa: E402

try:
    from psycopg2 import sql  # type: ignore
    from psycopg2.extras import execute_values  # type: ignore
except Exception as exc:  # pragma: no cover - environment-specific
    raise SystemExit(f"psycopg2 is required for PostgreSQL import: {exc}") from exc


def _ensure_table(conn, table: str) -> None:
    cur = conn.cursor()
    cur.execute(
        sql.SQL(
            """
            CREATE TABLE IF NOT EXISTS {} (
                timestamp BIGINT NOT NULL,
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (timestamp, exchange, symbol, timeframe)
            )
            """
        ).format(sql.Identifier(table))
    )
    cur.execute(
        sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (symbol, timeframe)").format(
            sql.Identifier(f"idx_{table}_symbol_tf"),
            sql.Identifier(table),
        )
    )
    cur.execute(
        sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} (timestamp)").format(
            sql.Identifier(f"idx_{table}_timestamp"),
            sql.Identifier(table),
        )
    )
    cur.execute(
        sql.SQL(
            "CREATE INDEX IF NOT EXISTS {} ON {} (exchange, symbol, timeframe)"
        ).format(
            sql.Identifier(f"idx_{table}_exchange_symbol_tf"),
            sql.Identifier(table),
        )
    )
    conn.commit()
    cur.close()


def _insert_rows(cur, table: str, rows: List[Tuple[Any, ...]]) -> int:
    if not rows:
        return 0
    query = sql.SQL(
        """
        INSERT INTO {} (
            timestamp, exchange, symbol, timeframe, open, high, low, close, volume
        )
        VALUES %s
        ON CONFLICT (timestamp, exchange, symbol, timeframe) DO NOTHING
        """
    ).format(sql.Identifier(table))
    execute_values(cur, query, rows, page_size=1000)
    return max(cur.rowcount, 0)


def import_json_file(
    path: Path,
    conn,
    table: str,
    exchange: str,
) -> Dict[str, int]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if "results" not in payload:
        raise ValueError("Invalid JSON format: missing results")

    total_rows = 0
    inserted_rows = 0
    skipped_results = 0
    failed_results = 0
    bad_rows = 0

    cur = conn.cursor()

    for result in payload["results"]:
        if not isinstance(result, dict):
            failed_results += 1
            continue
        if result.get("error"):
            failed_results += 1
            continue

        symbol = result.get("symbol")
        timeframe = result.get("timeframe")
        klines = result.get("klines") or []
        if not symbol or not timeframe or not isinstance(klines, list):
            skipped_results += 1
            continue
        if not klines:
            skipped_results += 1
            continue

        rows: List[Tuple[Any, ...]] = []
        for k in klines:
            try:
                rows.append(
                    (
                        int(k["timestamp"]),
                        exchange,
                        symbol,
                        timeframe,
                        float(k["open"]),
                        float(k["high"]),
                        float(k["low"]),
                        float(k["close"]),
                        float(k.get("volume") or 0.0),
                    )
                )
            except Exception:
                bad_rows += 1
                continue

        total_rows += len(rows)
        inserted_rows += _insert_rows(cur, table, rows)

    conn.commit()
    cur.close()

    return {
        "total_rows": total_rows,
        "inserted_rows": inserted_rows,
        "skipped_results": skipped_results,
        "failed_results": failed_results,
        "bad_rows": bad_rows,
    }


def _move_to_deleting(path: Path, deleting_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = deleting_root / stamp
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / path.name
    return path.replace(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import kline JSON into PostgreSQL")
    parser.add_argument("json_files", nargs="+", help="JSON files to import")
    parser.add_argument("--exchange", default="gate", help="Exchange name")
    parser.add_argument("--table", default="klines", help="Target table name")
    parser.add_argument(
        "--move-to-deleting",
        action="store_true",
        help="Move imported files to deleting/ timestamp folder",
    )
    args = parser.parse_args()

    db = TraderDBManager("abu")
    conn = db.get_connection()
    _ensure_table(conn, args.table)

    deleting_root = ROOT / "deleting"
    for file_path in args.json_files:
        path = Path(file_path)
        if not path.exists():
            print(f"[SKIP] not found: {path}", file=sys.stderr)
            continue

        stats = import_json_file(path, conn, args.table, args.exchange)
        print(
            f"[OK] {path.name}: inserted={stats['inserted_rows']} "
            f"total={stats['total_rows']} skipped={stats['skipped_results']} "
            f"failed={stats['failed_results']} bad_rows={stats['bad_rows']}"
        )

        if args.move_to_deleting:
            moved = _move_to_deleting(path, deleting_root)
            print(f"[MOVE] {path} -> {moved}")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
