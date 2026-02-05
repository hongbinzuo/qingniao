#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询最新 ABU 交易计划（PostgreSQL）

用法:
  python scripts/abu/query_latest_abu_plans.py --limit 20
  python scripts/abu/query_latest_abu_plans.py --symbol BTC --timeframe 15m
  python scripts/abu/query_latest_abu_plans.py --format json --include-notes
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from db_manager_trader import TraderDBManager
except Exception:
    from src.db_manager_trader import TraderDBManager  # type: ignore


def _safe_json(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    try:
        return json.loads(json.dumps(val, default=str, ensure_ascii=False))
    except Exception:
        return str(val)


def _rows_to_dicts(cur, rows) -> List[Dict[str, Any]]:
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    cols = [d[0] for d in cur.description] if hasattr(cur, "description") and cur.description else None
    if not cols:
        return [{"row": row} for row in rows]
    return [dict(zip(cols, row)) for row in rows]


def _build_query(include_notes: bool, symbol: Optional[str], timeframe: Optional[str], status: Optional[str]) -> Dict[str, Any]:
    fields = [
        "id",
        "signal_time",
        "timeframe",
        "symbol",
        "signal_type",
        "entry_price",
        "stop_loss",
        "take_profit_1",
        "take_profit_2",
        "risk_reward_ratio",
        "score",
        "status",
        "created_at",
    ]
    if include_notes:
        fields.append("notes")

    where = ["system_name = %s"]
    params: List[Any] = ["abu"]
    if symbol:
        where.append("symbol = %s")
        params.append(symbol.upper())
    if timeframe:
        where.append("timeframe = %s")
        params.append(timeframe)
    if status:
        where.append("status = %s")
        params.append(status)

    query = f"""
        SELECT {", ".join(fields)}
        FROM trading_signals
        WHERE {" AND ".join(where)}
        ORDER BY signal_time DESC NULLS LAST, created_at DESC
        LIMIT %s
    """
    return {"query": query, "params": params}


def _format_text(rows: List[Dict[str, Any]], include_notes: bool) -> str:
    lines: List[str] = []
    for row in rows:
        line = (
            f"[{row.get('id')}] {row.get('symbol')} {row.get('timeframe')} "
            f"{(row.get('signal_type') or '').upper()} "
            f"entry={row.get('entry_price')} "
            f"sl={row.get('stop_loss')} "
            f"tp1={row.get('take_profit_1')} "
            f"rr={row.get('risk_reward_ratio')} "
            f"score={row.get('score')} "
            f"status={row.get('status')} "
            f"time={row.get('signal_time')}"
        )
        lines.append(line)
        if include_notes and row.get("notes"):
            notes = _safe_json(row.get("notes"))
            if isinstance(notes, dict):
                summary = notes.get("gemini_plan_summary")
                if summary:
                    lines.append(f"  gemini_plan_summary: {summary}")
            else:
                lines.append(f"  notes: {notes}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="查询最新 ABU 交易计划（PostgreSQL）")
    parser.add_argument("--limit", type=int, default=20, help="返回条数")
    parser.add_argument("--symbol", type=str, default="", help="币种 (如 BTC)")
    parser.add_argument("--timeframe", type=str, default="", help="时间框架 (如 15m/1h/4h)")
    parser.add_argument("--status", type=str, default="", help="状态 (如 pending)")
    parser.add_argument("--format", type=str, default="text", choices=["text", "json"], help="输出格式")
    parser.add_argument("--include-notes", action="store_true", help="输出 notes 字段")
    args = parser.parse_args()

    db = TraderDBManager("abu")
    conn = db._get_connection(read_only=True)
    try:
        q = _build_query(args.include_notes, args.symbol.strip() or None, args.timeframe.strip() or None, args.status.strip() or None)
        cur = conn.execute(q["query"], tuple(q["params"] + [args.limit]))
        rows = _rows_to_dicts(cur, cur.fetchall())
        if not rows:
            print("❌ 未找到记录")
            return 1
        if args.format == "json":
            if args.include_notes:
                for row in rows:
                    if "notes" in row:
                        row["notes"] = _safe_json(row.get("notes"))
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            print(_format_text(rows, args.include_notes))
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
