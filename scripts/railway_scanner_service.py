#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway Scanner Service - Continuous 24/7 Scanner for Railway Deployment

This service runs continuously on Railway and scans crypto markets for trading signals.
Designed to work with Railway's free PostgreSQL database.
"""

import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
SCAN_INTERVAL_MINUTES = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))
TOP_COINS = int(os.getenv("TOP_COINS", "10"))
TIMEFRAMES = os.getenv("TIMEFRAMES", "5m,15m,1h").split(",")
SIGNAL_MODES = os.getenv("SIGNAL_MODES", "aggressive,neutral,conservative").split(",")

# Signal thresholds
THRESHOLDS = {
    "aggressive": {
        "min_score": float(os.getenv("AGGRESSIVE_MIN_SCORE", "0.1")),
        "min_vector_match": float(os.getenv("AGGRESSIVE_MIN_VECTOR", "0.6")),
        "context_filter": "off",
    },
    "neutral": {
        "min_score": float(os.getenv("NEUTRAL_MIN_SCORE", "0.2")),
        "min_vector_match": float(os.getenv("NEUTRAL_MIN_VECTOR", "0.7")),
        "context_filter": "brooks",
    },
    "conservative": {
        "min_score": float(os.getenv("CONSERVATIVE_MIN_SCORE", "0.4")),
        "min_vector_match": float(os.getenv("CONSERVATIVE_MIN_VECTOR", "0.8")),
        "context_filter": "both",
    },
}

ROOT = Path(__file__).resolve().parent.parent
SCAN_SCRIPT = ROOT / "scripts" / "pa_scan_main.py"


def log_startup_info():
    """Log service configuration at startup"""
    logger.info("=" * 70)
    logger.info("RAILWAY SCANNER SERVICE STARTED")
    logger.info("=" * 70)
    logger.info(f"Scan interval: {SCAN_INTERVAL_MINUTES} minutes")
    logger.info(f"Top coins: {TOP_COINS}")
    logger.info(f"Timeframes: {', '.join(TIMEFRAMES)}")
    logger.info(f"Signal modes: {', '.join(SIGNAL_MODES)}")
    logger.info("")
    logger.info("Signal Thresholds:")
    for mode, config in THRESHOLDS.items():
        logger.info(f"  {mode.upper()}:")
        logger.info(f"    - min_score: {config['min_score']}")
        logger.info(f"    - min_vector_match: {config['min_vector_match']}")
        logger.info(f"    - context_filter: {config['context_filter']}")
    logger.info("")
    logger.info(f"Database: PostgreSQL (Railway)")
    logger.info(f"Start time: {datetime.now()}")
    logger.info("=" * 70)
    logger.info("")


def run_scan(timeframe: str, mode: str, cycle: int) -> bool:
    """Run a single scan for given timeframe and mode"""
    config = THRESHOLDS[mode]

    cmd = [
        sys.executable,
        str(SCAN_SCRIPT),
        "--top",
        str(TOP_COINS),
        "--timeframe",
        timeframe,
        "--min-score",
        str(config["min_score"]),
        "--min-vector-match",
        str(config["min_vector_match"]),
        "--context-filter",
        config["context_filter"],
        "--write-db",
        "1",
    ]

    logger.info(f"  Scanning {timeframe} [{mode}] - Top {TOP_COINS} coins")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            logger.info(f"  ✓ {timeframe} scan completed")
            return True
        else:
            logger.error(f"  ✗ {timeframe} scan failed: {result.stderr[:200]}")
            return False

    except subprocess.TimeoutExpired:
        logger.error(f"  ✗ {timeframe} scan timed out (5 min)")
        return False
    except Exception as e:
        logger.error(f"  ✗ {timeframe} scan error: {str(e)[:200]}")
        return False


def run_scan_cycle(cycle: int):
    """Run one complete scan cycle across all modes and timeframes"""
    logger.info("=" * 70)
    logger.info(f"SCAN CYCLE #{cycle}")
    logger.info("=" * 70)
    logger.info("")

    total_scans = 0
    successful_scans = 0

    for mode in SIGNAL_MODES:
        logger.info(f"→ Running {mode.upper()} mode scan")

        for timeframe in TIMEFRAMES:
            total_scans += 1
            if run_scan(timeframe, mode, cycle):
                successful_scans += 1

        logger.info("")

    logger.info(
        f"Cycle #{cycle} complete: {successful_scans}/{total_scans} scans successful"
    )
    logger.info("")

    return successful_scans, total_scans


def main():
    """Main service loop"""
    log_startup_info()

    cycle = 0
    start_time = time.time()

    while True:
        cycle += 1
        cycle_start = time.time()

        try:
            successful, total = run_scan_cycle(cycle)

            cycle_duration = time.time() - cycle_start
            elapsed_minutes = (time.time() - start_time) / 60

            logger.info(f"Cycle duration: {cycle_duration:.1f}s")
            logger.info(f"Total runtime: {elapsed_minutes:.1f} minutes")
            logger.info(f"Next scan in {SCAN_INTERVAL_MINUTES} minutes")
            logger.info("")

        except KeyboardInterrupt:
            logger.info("Service stopped by user")
            break
        except Exception as e:
            logger.error(f"Cycle error: {str(e)}")
            logger.info("Continuing to next cycle...")

        # Sleep until next scan
        time.sleep(SCAN_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
