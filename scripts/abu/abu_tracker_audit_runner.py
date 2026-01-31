#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU 跟踪 + 回放统一入口

默认:
- tracker: 每 15 分钟
- replay audit: 每 4 小时
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "logs"


def _parse_time(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue
    return None


def _setup_logger() -> logging.Logger:
    logger = logging.getLogger("abu_tracker_audit_runner")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(LOG_DIR / "abu_tracker_audit_runner.log", encoding="utf-8")
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.handlers = []
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def _run_cmd(cmd: list[str], logger: logging.Logger) -> int:
    logger.info("Run: %s", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if proc.stdout:
            logger.info("stdout:\n%s", proc.stdout.strip())
        if proc.stderr:
            logger.warning("stderr:\n%s", proc.stderr.strip())
        return int(proc.returncode or 0)
    except Exception as exc:
        logger.error("command failed: %s", exc)
        return 1


def _tracker_cmd(start: str, interval_min: int) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "scripts" / "abu" / "abu_hourly_signal_tracker.py"),
        "--once",
        "--start",
        start,
        "--interval-minutes",
        str(interval_min),
    ]


def _replay_cmd(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "abu" / "abu_signal_replay_audit.py"),
        "--start",
        args.replay_start,
        "--timeframes",
        args.replay_timeframes,
        "--sample",
        str(args.replay_sample),
        "--precision",
        str(args.replay_precision),
    ]
    if args.replay_no_expiry:
        cmd.append("--no-expiry")
    if args.replay_end:
        cmd.extend(["--end", args.replay_end])
    if args.replay_output:
        cmd.extend(["--output", args.replay_output])
    return cmd


def main() -> int:
    parser = argparse.ArgumentParser(description="ABU tracker + replay audit runner")
    parser.add_argument("--tracker-on", type=int, default=1, choices=[0, 1])
    parser.add_argument("--replay-on", type=int, default=1, choices=[0, 1])
    parser.add_argument("--tracker-interval-minutes", type=int, default=15)
    parser.add_argument("--replay-interval-hours", type=int, default=4)
    parser.add_argument("--tracker-start", type=str, default="2026-01-25 00:00:00")
    parser.add_argument("--replay-start", type=str, default="2026-01-25 00:00:00")
    parser.add_argument("--replay-end", type=str, default="")
    parser.add_argument("--replay-timeframes", type=str, default="5m,15m,1h")
    parser.add_argument("--replay-sample", type=int, default=20)
    parser.add_argument("--replay-precision", type=int, default=9)
    parser.add_argument("--replay-no-expiry", action="store_true")
    parser.add_argument("--replay-output", type=str, default="")
    parser.add_argument("--run-on-start", type=int, default=1, choices=[0, 1])
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    logger = _setup_logger()

    if not _parse_time(args.tracker_start):
        logger.error("invalid --tracker-start")
        return 2
    if not _parse_time(args.replay_start):
        logger.error("invalid --replay-start")
        return 2
    if args.replay_end and not _parse_time(args.replay_end):
        logger.error("invalid --replay-end")
        return 2

    tracker_on = bool(args.tracker_on)
    replay_on = bool(args.replay_on)
    if not tracker_on and not replay_on:
        logger.warning("both tracker and replay are disabled")
        return 0

    tracker_interval = max(1, int(args.tracker_interval_minutes))
    replay_interval = max(1, int(args.replay_interval_hours)) * 3600

    tracker_next = None
    replay_next = None
    if args.run_on_start:
        tracker_next = datetime.now()
        replay_next = datetime.now()

    while True:
        now = datetime.now()
        if tracker_on:
            if tracker_next is None:
                tracker_next = now
            if now >= tracker_next:
                code = _run_cmd(_tracker_cmd(args.tracker_start, tracker_interval), logger)
                logger.info("tracker exit code=%s", code)
                tracker_next = datetime.now() + timedelta(minutes=tracker_interval)

        if replay_on:
            if replay_next is None:
                replay_next = now
            if now >= replay_next:
                code = _run_cmd(_replay_cmd(args), logger)
                logger.info("replay exit code=%s", code)
                replay_next = datetime.now() + timedelta(seconds=replay_interval)

        if args.once:
            return 0

        next_times = [t for t in (tracker_next, replay_next) if t]
        if not next_times:
            time.sleep(5)
            continue
        sleep_for = max(5, int((min(next_times) - datetime.now()).total_seconds()))
        time.sleep(sleep_for)


if __name__ == "__main__":
    raise SystemExit(main())
