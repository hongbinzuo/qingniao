#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Watch a directory for vision batch JSON/JSONL files and ingest them.
"""
from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

import sys

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from ingest_vision_batch import ingest_batch


def _setup_logger(log_file: Path | None) -> logging.Logger:
    logger = logging.getLogger("vision_batch_watcher")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


def _eligible_files(watch_dir: Path, min_age: int) -> List[Path]:
    now = time.time()
    files = list(watch_dir.glob("*.json")) + list(watch_dir.glob("*.jsonl"))
    candidates = []
    for path in sorted(files):
        try:
            if now - path.stat().st_mtime < min_age:
                continue
        except FileNotFoundError:
            continue
        candidates.append(path)
    return candidates


def _move_file(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists():
        stamp = time.strftime("%Y%m%d_%H%M%S")
        dest = dest_dir / f"{src.stem}_{stamp}{src.suffix}"
    src.rename(dest)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch a directory and ingest vision batches.")
    parser.add_argument(
        "--watch-dir",
        default=str(ROOT / "gemini_batch"),
        help="Directory to watch for batch JSON files.",
    )
    parser.add_argument(
        "--processed-dir",
        default=str(ROOT / "outputs" / "abu_deep_analysis" / "processed"),
        help="Directory to move processed batches.",
    )
    parser.add_argument(
        "--failed-dir",
        default=str(ROOT / "outputs" / "abu_deep_analysis" / "failed"),
        help="Directory to move failed batches.",
    )
    parser.add_argument(
        "--raw-dir",
        default=str(ROOT / "outputs" / "abu_deep_analysis" / "json"),
        help="Directory to store per-image raw JSON.",
    )
    parser.add_argument(
        "--clean-dir",
        default=str(ROOT / "outputs" / "abu_deep_analysis" / "clean_json"),
        help="Directory to store per-image cleaned JSON.",
    )
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds.")
    parser.add_argument("--min-age", type=int, default=5, help="Minimum file age in seconds.")
    parser.add_argument("--once", action="store_true", help="Process existing files once and exit.")
    parser.add_argument("--no-skip-existing", dest="skip_existing", action="store_false", default=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--log-file",
        default=str(ROOT / "logs" / "vision_ingest_watcher.log"),
        help="Log file path.",
    )
    args = parser.parse_args()

    watch_dir = Path(args.watch_dir)
    processed_dir = Path(args.processed_dir)
    failed_dir = Path(args.failed_dir)
    raw_dir = Path(args.raw_dir) if args.raw_dir else None
    clean_dir = Path(args.clean_dir) if args.clean_dir else None

    watch_dir.mkdir(parents=True, exist_ok=True)
    logger = _setup_logger(Path(args.log_file) if args.log_file else None)
    logger.info("Watching for batch files in %s", watch_dir)

    while True:
        candidates = _eligible_files(watch_dir, args.min_age)
        if not candidates:
            if args.once:
                logger.info("No pending batches. Exit.")
                break
            time.sleep(args.interval)
            continue

        for path in candidates:
            logger.info("Processing batch: %s", path.name)
            try:
                ingest_batch(
                    input_path=path,
                    raw_dir=raw_dir,
                    clean_dir=clean_dir,
                    skip_existing=args.skip_existing,
                    dry_run=args.dry_run,
                )
                dest = _move_file(path, processed_dir)
                logger.info("Processed -> %s", dest)
            except Exception as exc:
                logger.exception("Failed processing %s: %s", path.name, exc)
                try:
                    dest = _move_file(path, failed_dir)
                    logger.info("Moved to failed -> %s", dest)
                except Exception:
                    logger.exception("Failed to move %s to failed dir", path.name)

        if args.once:
            logger.info("Done.")
            break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
