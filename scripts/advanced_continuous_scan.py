#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Advanced Continuous PA Scanner
- Multi-timeframe: 5m, 15m, 1h
- Signal modes: aggressive, neutral, conservative
- Audit reports every 4 hours
- Vector match filtering
- Trend following (5m allows counter-trend)
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_DIR / "advanced_scan.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class SignalMode:
    """Signal mode configurations"""

    AGGRESSIVE = {
        "name": "aggressive",
        "min_score": 0.1,
        "min_vector_match": 0.6,
        "context_filter": "off",
        "description": "More signals, lower threshold",
    }
    NEUTRAL = {
        "name": "neutral",
        "min_score": 0.2,
        "min_vector_match": 0.7,
        "context_filter": "brooks",
        "description": "Balanced approach",
    }
    CONSERVATIVE = {
        "name": "conservative",
        "min_score": 0.4,
        "min_vector_match": 0.8,
        "context_filter": "both",
        "description": "High quality signals only",
    }

    @classmethod
    def get_mode(cls, mode_name: str):
        modes = {
            "aggressive": cls.AGGRESSIVE,
            "neutral": cls.NEUTRAL,
            "conservative": cls.CONSERVATIVE,
        }
        return modes.get(mode_name.lower(), cls.NEUTRAL)


def run_scan(
    timeframe: str, top: int, mode: dict, allow_counter_trend: bool = False
) -> dict:
    """Run a single scan for one timeframe"""
    try:
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "pa_scan_main.py"),
            "--timeframe",
            timeframe,
            "--top",
            str(top),
            "--write-db",
            "1",
            "--exchange-mode",
            "gate",
            "--context-filter",
            mode["context_filter"],
            "--min-score",
            str(mode["min_score"]),
            "--min-vector-match",
            str(mode["min_vector_match"]),
            "--trend-mode",
            "allow" if allow_counter_trend else "follow",
            "--include-movers",
            "0",
        ]

        logger.info(f"Scanning {timeframe} [{mode['name']}] - Top {top} coins")
        if allow_counter_trend:
            logger.info(f"  → Counter-trend allowed for {timeframe}")

        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )

        return {
            "success": result.returncode == 0,
            "timeframe": timeframe,
            "mode": mode["name"],
            "output": result.stdout,
            "error": result.stderr,
        }

    except Exception as e:
        logger.error(f"Scan error [{timeframe}]: {e}")
        return {
            "success": False,
            "timeframe": timeframe,
            "mode": mode["name"],
            "error": str(e),
        }


def run_audit_report(hours: float = 1.0) -> bool:
    """Generate performance audit report using historical prices"""
    try:
        logger.info(f"Running performance audit for last {hours} hour(s)...")
        logger.info("  → Checking signals against historical candles (TP1/TP2/SL)")

        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "performance_audit.py"),
            "--hours",
            str(hours),
            "--output-dir",
            str(ROOT / "outputs" / "audit_reports"),
        ]

        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )

        if result.returncode == 0:
            report_path = result.stdout.strip().splitlines()[-1]
            logger.info(f"✓ Audit report saved: {report_path}")
            return True
        else:
            logger.error(f"✗ Audit report failed: {result.stderr[:200]}")
            return False

    except Exception as e:
        logger.error(f"Audit error: {e}")
        return False


def run_multi_timeframe_scan(top: int, mode: dict) -> dict:
    """Run scans across all timeframes"""
    timeframes = ["5m", "15m", "1h"]
    results = {}

    for tf in timeframes:
        allow_counter = tf == "5m"  # Only 5m allows counter-trend
        result = run_scan(tf, top, mode, allow_counter)
        results[tf] = result

        if result["success"]:
            logger.info(f"  ✓ {tf} scan completed")
        else:
            logger.error(f"  ✗ {tf} scan failed")

    return results


def main():
    parser = argparse.ArgumentParser(description="Advanced Continuous PA Scanner")
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top coins (default: 10)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Minutes between scan cycles (default: 15)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=360,
        help="Total duration in minutes (default: 360 = 6 hours)",
    )
    parser.add_argument(
        "--mode",
        default="all",
        choices=["aggressive", "neutral", "conservative", "all"],
        help="Signal mode (default: all)",
    )
    parser.add_argument(
        "--audit-interval",
        type=int,
        default=60,
        help="Minutes between performance audit reports (default: 60 = 1 hour)",
    )

    args = parser.parse_args()

    # Determine which modes to run
    if args.mode == "all":
        modes = [SignalMode.AGGRESSIVE, SignalMode.NEUTRAL, SignalMode.CONSERVATIVE]
    else:
        modes = [SignalMode.get_mode(args.mode)]

    start_time = datetime.now()
    last_audit_time = start_time
    scan_count = 0

    logger.info("=" * 70)
    logger.info("ADVANCED CONTINUOUS PA SCANNER STARTED")
    logger.info(f"Top coins: {args.top}")
    logger.info(f"Timeframes: 5m, 15m, 1h")
    logger.info(f"Signal modes: {', '.join([m['name'] for m in modes])}")
    logger.info("")
    logger.info("Signal Thresholds:")
    for mode in modes:
        logger.info(f"  {mode['name'].upper()}:")
        logger.info(f"    - min_score: {mode['min_score']}")
        logger.info(f"    - min_vector_match: {mode['min_vector_match']}")
        logger.info(f"    - context_filter: {mode['context_filter']}")
    logger.info("")
    logger.info(f"Scan interval: {args.interval} minutes")
    logger.info(
        f"Performance audit: every {args.audit_interval} minutes (uses historical prices)"
    )
    logger.info(f"Duration: {args.duration} minutes ({args.duration / 60:.1f} hours)")
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    try:
        while True:
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60

            if elapsed_minutes >= args.duration:
                logger.info(f"Duration limit reached ({args.duration} minutes)")
                break

            scan_count += 1
            logger.info(f"\n{'=' * 70}")
            logger.info(
                f"SCAN CYCLE #{scan_count} - Elapsed: {elapsed_minutes:.1f}/{args.duration} min"
            )
            logger.info(f"{'=' * 70}")

            # Run scans for each mode
            for mode in modes:
                logger.info(f"\n→ Running {mode['name'].upper()} mode scan")
                results = run_multi_timeframe_scan(args.top, mode)

            # Check if performance audit is due
            time_since_audit = (datetime.now() - last_audit_time).total_seconds() / 60
            if time_since_audit >= args.audit_interval:
                logger.info(
                    f"\n→ Performance audit due (last: {time_since_audit:.1f} min ago)"
                )
                # Audit signals from the last audit interval period
                audit_hours = args.audit_interval / 60.0
                run_audit_report(hours=audit_hours)
                last_audit_time = datetime.now()

            # Calculate next scan time
            remaining_minutes = args.duration - elapsed_minutes
            if remaining_minutes < args.interval:
                logger.info(
                    f"Not enough time for another scan (remaining: {remaining_minutes:.1f} min)"
                )
                break

            logger.info(f"\nWaiting {args.interval} minutes until next scan...")
            time.sleep(args.interval * 60)

    except KeyboardInterrupt:
        logger.info("\n\nScan interrupted by user (Ctrl+C)")

    # Final summary
    elapsed_total = (datetime.now() - start_time).total_seconds() / 60
    logger.info("\n" + "=" * 70)
    logger.info("ADVANCED SCAN SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total scan cycles: {scan_count}")
    logger.info(f"Signal modes: {', '.join([m['name'] for m in modes])}")
    logger.info(
        f"Total duration: {elapsed_total:.1f} minutes ({elapsed_total / 60:.2f} hours)"
    )
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
