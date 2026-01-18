#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ingest vision recognition batches into pattern_library and write clean outputs.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from db_manager_trader import TraderDBManager

try:
    from clean_vision_schema import clean_record
except Exception:
    clean_record = None


def _iter_records(path: Path) -> Iterable[Dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
        return

    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
    elif isinstance(payload, dict):
        yield payload


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _match_pattern_id(conn, image_id: Optional[str], page: Optional[int]) -> Optional[int]:
    if image_id:
        result = conn.execute(
            """
            SELECT id FROM pattern_library
            WHERE image_path LIKE ?
            LIMIT 1
            """,
            (f"%{image_id}%",),
        ).fetchone()
        if result:
            return result[0]

    if page is not None:
        result = conn.execute(
            """
            SELECT id FROM pattern_library
            WHERE source_page = ?
            LIMIT 1
            """,
            (page,),
        ).fetchone()
        if result:
            return result[0]

    return None


def _extract_primary_pattern(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    patterns = record.get("patterns")
    if isinstance(patterns, list) and patterns:
        first = patterns[0]
        if isinstance(first, dict):
            return first
    return None


def _pick_pattern_name(pattern: Optional[Dict[str, Any]]) -> Optional[str]:
    if not pattern:
        return None
    name = pattern.get("pattern_name")
    if name:
        return name
    raw = pattern.get("raw")
    if isinstance(raw, dict):
        raw_name = raw.get("pattern_name")
        if raw_name:
            return raw_name
    return None


def _pick_pattern_type(pattern: Optional[Dict[str, Any]]) -> Optional[str]:
    if not pattern:
        return None
    value = pattern.get("pattern_type") or pattern.get("pattern_family")
    if value:
        return value
    raw = pattern.get("raw")
    if isinstance(raw, dict):
        raw_value = raw.get("pattern_type") or raw.get("pattern_family")
        if raw_value:
            return raw_value
    return None


def _pick_direction(record: Dict[str, Any], pattern: Optional[Dict[str, Any]]) -> Optional[str]:
    chart = record.get("chart") if isinstance(record.get("chart"), dict) else {}
    direction = chart.get("direction_bias")
    if direction:
        return direction
    if pattern:
        value = pattern.get("direction_bias")
        if value:
            return value
        raw = pattern.get("raw")
        if isinstance(raw, dict):
            raw_value = raw.get("direction_bias")
            if raw_value:
                return raw_value
    return None


def _pick_confidence(record: Dict[str, Any], pattern: Optional[Dict[str, Any]]) -> Optional[float]:
    if pattern and isinstance(pattern.get("confidence"), (int, float)):
        return float(pattern["confidence"])
    chart = record.get("chart") if isinstance(record.get("chart"), dict) else {}
    ema = chart.get("ema_20") if isinstance(chart.get("ema_20"), dict) else {}
    if isinstance(ema.get("confidence"), (int, float)):
        return float(ema["confidence"])
    return None


def _extract_kline_features(record: Dict[str, Any]) -> Optional[str]:
    feats = record.get("kline_features")
    if not feats:
        return None
    values: List[str] = []
    if isinstance(feats, list):
        for item in feats:
            if isinstance(item, dict):
                feat = item.get("feature")
                if isinstance(feat, str) and feat:
                    values.append(feat)
            elif isinstance(item, str):
                values.append(item)
    if not values:
        return None
    return json.dumps(values, ensure_ascii=False)


def _parse_page(page_val: Any) -> Optional[int]:
    if isinstance(page_val, int):
        return page_val
    if isinstance(page_val, str) and page_val.isdigit():
        return int(page_val)
    return None


def ingest_batch(
    input_path: Path,
    raw_dir: Optional[Path],
    clean_dir: Optional[Path],
    skip_existing: bool,
    dry_run: bool,
) -> int:
    db = TraderDBManager("abu")
    conn = db._get_connection()

    total = 0
    matched = 0
    updated = 0
    skipped = 0
    errors = 0
    cleaned = 0

    for record in _iter_records(input_path):
        total += 1
        image_id = record.get("image_id") or record.get("image")
        page_num = _parse_page(record.get("page"))
        if raw_dir and image_id:
            _write_json(raw_dir / f"{image_id}.json", record)

        if clean_dir and clean_record:
            clean_payload = clean_record(record)
            if image_id:
                _write_json(clean_dir / f"{image_id}.json", clean_payload)
            cleaned += 1

        pattern_id = _match_pattern_id(conn, image_id, page_num)
        if not pattern_id:
            errors += 1
            continue

        matched += 1

        if skip_existing:
            existing = conn.execute(
                """
                SELECT gemini_annotation_json FROM pattern_library
                WHERE id = ? AND gemini_annotation_json IS NOT NULL
                  AND gemini_annotation_json != ''
                """,
                (pattern_id,),
            ).fetchone()
            if existing:
                skipped += 1
                continue

        pattern = _extract_primary_pattern(record)
        pattern_name = _pick_pattern_name(pattern)
        pattern_type = _pick_pattern_type(pattern)
        direction = _pick_direction(record, pattern)
        confidence = _pick_confidence(record, pattern)
        timeframe_hint = record.get("timeframe_hint")
        key_features = _extract_kline_features(record)

        raw_json = json.dumps(record, ensure_ascii=False)
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not dry_run:
            conn.execute(
                """
                UPDATE pattern_library
                SET gemini_annotation_json = ?,
                    pattern_name = COALESCE(?, pattern_name),
                    pattern_type = COALESCE(?, pattern_type),
                    direction = COALESCE(?, direction),
                    timeframe_hint = COALESCE(?, timeframe_hint),
                    key_features = COALESCE(?, key_features),
                    confidence = COALESCE(?, confidence),
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    raw_json,
                    pattern_name,
                    pattern_type,
                    direction,
                    timeframe_hint,
                    key_features,
                    confidence,
                    updated_at,
                    pattern_id,
                ),
            )
        updated += 1

    if not dry_run:
        conn.commit()
    db.close()

    print("Ingest summary:")
    print(f"  total:   {total}")
    print(f"  matched: {matched}")
    print(f"  updated: {updated}")
    print(f"  skipped: {skipped}")
    print(f"  errors:  {errors}")
    if clean_dir:
        print(f"  cleaned: {cleaned}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest vision batch results into DB.")
    parser.add_argument("--input", required=True, help="Input JSON or JSONL file.")
    parser.add_argument(
        "--raw-dir",
        default=str(ROOT / "outputs" / "abu_deep_analysis" / "json"),
        help="Directory to store raw per-image JSON.",
    )
    parser.add_argument(
        "--clean-dir",
        default=str(ROOT / "outputs" / "abu_deep_analysis" / "clean_json"),
        help="Directory to store cleaned per-image JSON.",
    )
    parser.add_argument("--skip-existing", action="store_true", default=True)
    parser.add_argument("--no-skip-existing", dest="skip_existing", action="store_false")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    raw_dir = Path(args.raw_dir) if args.raw_dir else None
    clean_dir = Path(args.clean_dir) if args.clean_dir else None
    if clean_dir and clean_record is None:
        print("clean_vision_schema not available; skip cleaning.", file=sys.stderr)
        clean_dir = None

    return ingest_batch(
        input_path=input_path,
        raw_dir=raw_dir,
        clean_dir=clean_dir,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
