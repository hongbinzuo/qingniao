#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从PostgreSQL生成视觉匹配HTML报告

用法:
  python scripts/abu/generate_vision_report_from_db.py --batch-id 20260205_163531
  python scripts/abu/generate_vision_report_from_db.py --latest
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

import sys
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from db_manager_trader import TraderDBManager
except Exception:
    from src.db_manager_trader import TraderDBManager  # type: ignore


def _safe_json(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return {}


def _resolve_file_path(raw_path: Optional[str]) -> Optional[Path]:
    if not raw_path:
        return None
    try:
        p = Path(raw_path)
        if p.exists():
            return p
    except Exception:
        p = None

    raw = str(raw_path)
    # Windows -> WSL
    if os.name != "nt" and ":" in raw[:3]:
        drive, rest = raw.split(":", 1)
        rest = rest.replace("\\", "/").lstrip("/")
        wsl_path = Path("/mnt") / drive.lower() / rest
        if wsl_path.exists():
            return wsl_path

    # WSL -> Windows
    if os.name == "nt" and raw.startswith("/mnt/"):
        parts = raw.split("/")
        if len(parts) > 3:
            drive = parts[2].upper()
            win_path = drive + ":\\" + "\\".join(parts[3:])
            wp = Path(win_path)
            if wp.exists():
                return wp

    # Relative to repo root
    try:
        rel = ROOT / raw
        if rel.exists():
            return rel
    except Exception:
        pass
    return None


def _fetch_latest_batch_id(conn) -> Optional[str]:
    cur = conn.execute(
        """
        SELECT batch_id
        FROM vision_match_records
        WHERE batch_id IS NOT NULL AND batch_id != ''
        ORDER BY created_at DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return row.get("batch_id")
    if hasattr(cur, "description") and cur.description:
        cols = [d[0] for d in cur.description]
        try:
            mapped = dict(zip(cols, row))
            return mapped.get("batch_id")
        except Exception:
            return row[0]
    return row[0]


def _fetch_records(conn, batch_id: str, limit: int = 2000, accepted_only: bool = True) -> List[Dict[str, Any]]:
    where_clause = "batch_id = %s"
    params: List[Any] = [batch_id]
    if accepted_only:
        where_clause += " AND accepted IS TRUE"
    cur = conn.execute(
        """
        SELECT *
        FROM vision_match_records
        WHERE """ + where_clause + """
        ORDER BY created_at ASC
        LIMIT %s
        """,
        tuple(params + [limit]),
    )
    rows = cur.fetchall()
    records: List[Dict[str, Any]] = []
    cols = [d[0] for d in cur.description] if hasattr(cur, "description") and cur.description else None
    for row in rows:
        if isinstance(row, dict):
            rec = row
        elif cols:
            rec = dict(zip(cols, row))
        else:
            rec = {"row": row}
        rec["vision_result"] = _safe_json(rec.get("vision_result"))
        rec["extra"] = _safe_json(rec.get("extra"))
        records.append(rec)
    return records


def _write_html_report(records: List[Dict[str, Any]], out_dir: Path, batch_id: str) -> Optional[Path]:
    if not records:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / f"assets_{batch_id}"
    assets_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"vision_plan_summary_{batch_id}.html"

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Vision Plan Summary</title>",
        "<style>body{font-family:Arial,sans-serif} .case{margin:24px 0} .imgs{display:flex;gap:16px} img{max-width:48%;height:auto;border:1px solid #ccc} pre{white-space:pre-wrap}</style>",
        "</head><body>",
        f"<h1>Vision Filter Summary - {batch_id}</h1>",
    ]

    for rec in records:
        chart = _resolve_file_path(rec.get("chart_image"))
        pattern = _resolve_file_path(rec.get("pattern_image"))
        chart_copy = None
        pattern_copy = None
        if chart and chart.exists():
            chart_copy = assets_dir / f"{rec.get('symbol','')}_{rec.get('timeframe','')}_chart{chart.suffix or '.png'}"
            if not chart_copy.exists():
                shutil.copy2(chart, chart_copy)
        if pattern and pattern.exists():
            pattern_copy = assets_dir / f"{rec.get('symbol','')}_{rec.get('timeframe','')}_pattern{pattern.suffix or '.png'}"
            if not pattern_copy.exists():
                shutil.copy2(pattern, pattern_copy)

        vr = rec.get("vision_result") or {}
        key_matches = vr.get("key_matches") or []
        differences = vr.get("differences") or []
        reasoning = (vr.get("reasoning") or "").strip()

        pattern_html = (
            f"<img src='{assets_dir.name}/{pattern_copy.name}'>"
            if pattern_copy
            else "<div>Missing pattern image</div>"
        )
        chart_html = (
            f"<img src='{assets_dir.name}/{chart_copy.name}'>"
            if chart_copy
            else "<div>Missing chart image</div>"
        )

        parts.extend(
            [
                "<div class='case'>",
                f"<h2>{rec.get('symbol','')} {rec.get('timeframe','')} | {rec.get('pattern_name','')} | "
                f"algo={rec.get('algorithm_score', 0):.3f} vision={rec.get('vision_score', 0):.3f} "
                f"final={rec.get('final_score', 0):.3f} "
                f"{'✅' if rec.get('accepted') else '❌'}</h2>",
                "<div class='imgs'>",
                f"<div><h3>Pattern</h3>{pattern_html}</div>",
                f"<div><h3>Chart</h3>{chart_html}</div>",
                "</div>",
                "<h3>Key Matches</h3>",
                "<pre>" + "\n".join([f"- {k}" for k in key_matches]) + "</pre>",
                "<h3>Differences</h3>",
                "<pre>" + "\n".join([f"- {d}" for d in differences]) + "</pre>",
                "<h3>Reasoning (truncated)</h3>",
                "<pre>" + (reasoning[:900] + ("..." if len(reasoning) > 900 else "")) + "</pre>",
                "</div>",
            ]
        )

    parts.append("</body></html>")
    html_path.write_text("\n".join(parts), encoding="utf-8")
    return html_path


def _write_top_matches_html(
    records: List[Dict[str, Any]],
    out_dir: Path,
    batch_id: str,
    top_n: int = 5,
) -> Optional[Path]:
    if not records:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / f"top_matches_assets_{batch_id}"
    assets_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"vision_top_matches_{batch_id}.html"

    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for rec in records:
        key = (rec.get("symbol", ""), rec.get("timeframe", ""))
        grouped.setdefault(key, []).append(rec)

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Vision Top Matches</title>",
        "<style>body{font-family:Arial,sans-serif} .case{margin:24px 0} .imgs{display:flex;gap:16px} "
        "img{max-width:48%;height:auto;border:1px solid #ccc} pre{white-space:pre-wrap}</style>",
        "</head><body>",
        f"<h1>Vision Top {top_n} Matches - {batch_id}</h1>",
    ]

    for (symbol, timeframe), recs in grouped.items():
        if not symbol or not timeframe:
            continue
        sorted_recs = sorted(recs, key=lambda r: r.get("final_score", 0.0), reverse=True)[: max(1, top_n)]
        parts.append(f"<h2>{symbol} {timeframe}</h2>")
        for idx, rec in enumerate(sorted_recs, 1):
            pattern = _resolve_file_path(rec.get("pattern_image"))
            chart = _resolve_file_path(rec.get("chart_image"))
            pattern_copy = None
            chart_copy = None
            try:
                if pattern and pattern.exists():
                    pattern_copy = assets_dir / f"{symbol}_{timeframe}_{idx}_pattern{pattern.suffix or '.png'}"
                    if not pattern_copy.exists():
                        shutil.copy2(pattern, pattern_copy)
                if chart and chart.exists():
                    chart_copy = assets_dir / f"{symbol}_{timeframe}_{idx}_chart{chart.suffix or '.png'}"
                    if not chart_copy.exists():
                        shutil.copy2(chart, chart_copy)
            except Exception:
                pattern_copy = pattern_copy if pattern_copy and pattern_copy.exists() else None
                chart_copy = chart_copy if chart_copy and chart_copy.exists() else None

            vr = rec.get("vision_result") or {}
            key_matches = vr.get("key_matches") or []
            differences = vr.get("differences") or []
            reasoning = (vr.get("reasoning") or "").strip()

            pattern_html = (
                f"<img src='{assets_dir.name}/{pattern_copy.name}'>"
                if pattern_copy
                else "<div>Missing pattern image</div>"
            )
            chart_html = (
                f"<img src='{assets_dir.name}/{chart_copy.name}'>"
                if chart_copy
                else "<div>Missing chart image</div>"
            )

            parts.extend(
                [
                    "<div class='case'>",
                    f"<h3>{idx}. {rec.get('pattern_name','')} | "
                    f"algo={rec.get('algorithm_score', 0):.3f} "
                    f"vision={rec.get('vision_score', 0):.3f} "
                    f"final={rec.get('final_score', 0):.3f} "
                    f"{'✅' if rec.get('accepted') else '❌'}</h3>",
                    "<div class='imgs'>",
                    f"<div><h4>Pattern</h4>{pattern_html}</div>",
                    f"<div><h4>Chart</h4>{chart_html}</div>",
                    "</div>",
                    "<h4>Key Matches</h4>",
                    "<pre>" + "\n".join([f"- {k}" for k in key_matches]) + "</pre>",
                    "<h4>Differences</h4>",
                    "<pre>" + "\n".join([f"- {d}" for d in differences]) + "</pre>",
                    "<h4>Reasoning (truncated)</h4>",
                    "<pre>" + (reasoning[:900] + ("..." if len(reasoning) > 900 else "")) + "</pre>",
                    "</div>",
                ]
            )

    parts.append("</body></html>")
    html_path.write_text("\n".join(parts), encoding="utf-8")
    return html_path


def main() -> int:
    parser = argparse.ArgumentParser(description="从PostgreSQL生成视觉匹配HTML报告")
    parser.add_argument("--batch-id", type=str, default="", help="指定batch_id (时间戳)")
    parser.add_argument("--latest", action="store_true", help="使用最新batch")
    parser.add_argument("--limit", type=int, default=2000, help="最多读取记录数")
    parser.add_argument("--include-all", action="store_true", help="summary也包含未通过的匹配（默认只包含交易计划）")
    parser.add_argument("--top-n", type=int, default=5, help="每个symbol/timeframe展示Top N")
    parser.add_argument("--out-dir", type=str, default="outputs/vision_plan_db", help="输出目录")
    args = parser.parse_args()

    db = TraderDBManager("abu")
    conn = db._get_connection(read_only=True)
    try:
        batch_id = args.batch_id.strip()
        if args.latest or not batch_id:
            batch_id = _fetch_latest_batch_id(conn) or ""
        if not batch_id:
            print("[ERROR] 未找到可用batch_id")
            return 1

        summary_records = _fetch_records(conn, batch_id, limit=args.limit, accepted_only=not args.include_all)
        if not summary_records:
            print(f"[ERROR] batch_id={batch_id} 无交易计划记录")
            return 1
        top_records = _fetch_records(conn, batch_id, limit=args.limit, accepted_only=False)
        if not top_records:
            print(f"[ERROR] batch_id={batch_id} 无匹配记录")
            return 1

        out_dir = ROOT / args.out_dir
        html_summary = _write_html_report(summary_records, out_dir, batch_id)
        html_top = _write_top_matches_html(top_records, out_dir, batch_id, top_n=args.top_n)

        if html_summary:
            print(f"[OK] Summary: {html_summary}")
        if html_top:
            print(f"[OK] Top matches: {html_top}")
        return 0
    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
