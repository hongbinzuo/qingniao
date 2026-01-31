#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Continuous PA Scanner - Run locally for several hours
Scans every 15 minutes and writes signals to database
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_DIR / "continuous_scan.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def run_scan(timeframe: str, top: int, exchange_mode: str) -> bool:
    """Run a single scan iteration"""
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
            exchange_mode,
        ]

        logger.info(
            f"Starting scan: {timeframe} timeframe, top {top} coins, exchange: {exchange_mode}"
        )

        result = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout per scan
        )

        if result.returncode == 0:
            logger.info(f"✓ Scan completed successfully")
            # Log any signals found
            if (
                "signals found" in result.stdout.lower()
                or "candidate" in result.stdout.lower()
            ):
                logger.info(f"Output preview: {result.stdout[:500]}")
            return True
        else:
            logger.error(f"✗ Scan failed with code {result.returncode}")
            logger.error(f"Error: {result.stderr[:500]}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("✗ Scan timed out after 10 minutes")
        return False
    except Exception as e:
        logger.error(f"✗ Scan error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Continuous PA Scanner")
    parser.add_argument(
        "--timeframe",
        default="15m",
        choices=["5m", "15m", "1h"],
        help="Timeframe to scan (default: 15m)",
    )
    parser.add_argument(
        "--top", type=int, default=20, help="Number of top coins to scan (default: 20)"
    )
    parser.add_argument(
        "--interval", type=int, default=15, help="Minutes between scans (default: 15)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=180,
        help="Total duration in minutes (default: 180 = 3 hours)",
    )
    parser.add_argument(
        "--exchange",
        default="gate",
        choices=["gate", "bybit", "bitget", "split"],
        help="Exchange to use (default: gate)",
    )

    args = parser.parse_args()

    start_time = datetime.now()
    end_time_minutes = args.duration
    scan_count = 0
    success_count = 0

    logger.info("=" * 60)
    logger.info("CONTINUOUS PA SCANNER STARTED")
    logger.info(f"Timeframe: {args.timeframe}")
    logger.info(f"Top coins: {args.top}")
    logger.info(f"Exchange: {args.exchange}")
    logger.info(f"Scan interval: {args.interval} minutes")
    logger.info(f"Duration: {args.duration} minutes ({args.duration / 60:.1f} hours)")
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        while True:
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60

            if elapsed_minutes >= end_time_minutes:
                logger.info(f"Duration limit reached ({args.duration} minutes)")
                break

            scan_count += 1
            logger.info(f"\n{'=' * 60}")
            logger.info(
                f"SCAN #{scan_count} - Elapsed: {elapsed_minutes:.1f}/{args.duration} min"
            )
            logger.info(f"{'=' * 60}")

            success = run_scan(args.timeframe, args.top, args.exchange)
            if success:
                success_count += 1

            # Calculate next scan time
            remaining_minutes = end_time_minutes - elapsed_minutes
            if remaining_minutes < args.interval:
                logger.info(
                    f"Not enough time for another scan (remaining: {remaining_minutes:.1f} min)"
                )
                break

            logger.info(f"Waiting {args.interval} minutes until next scan...")
            time.sleep(args.interval * 60)

    except KeyboardInterrupt:
        logger.info("\n\nScan interrupted by user (Ctrl+C)")

    # Final summary
    elapsed_total = (datetime.now() - start_time).total_seconds() / 60
    logger.info("\n" + "=" * 60)
    logger.info("CONTINUOUS SCAN SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total scans: {scan_count}")
    logger.info(f"Successful: {success_count}")
    logger.info(f"Failed: {scan_count - success_count}")
    logger.info(
        f"Success rate: {success_count / scan_count * 100:.1f}%"
        if scan_count > 0
        else "N/A"
    )
    logger.info(
        f"Total duration: {elapsed_total:.1f} minutes ({elapsed_total / 60:.2f} hours)"
    )
    logger.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
