#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Health Check Script - Monitors scanner health and alerts if issues detected

Checks:
1. Scanner is generating signals regularly
2. Database connection is working
3. Last signal timestamp is recent

Run this periodically (e.g., via cron or Railway scheduled job)
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def get_db_connection():
    """Get PostgreSQL connection"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        host = os.getenv("PG_HOST", "localhost")
        port = os.getenv("PG_PORT", "5432")
        database = os.getenv("PG_DATABASE", "qingniao_abu")
        user = os.getenv("PG_USER", "abu_user")
        password = os.getenv("PG_PASSWORD", "")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def check_scanner_health():
    """Check if scanner is healthy"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Check last signal time
        cur.execute("""
            SELECT MAX(created_at) as last_signal_time,
                   COUNT(*) as signals_24h
            FROM trading_signals
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        result = cur.fetchone()

        last_signal_time = result["last_signal_time"]
        signals_24h = result["signals_24h"]

        # Health status
        status = {"healthy": True, "warnings": [], "errors": []}

        # Check 1: No signals in last 2 days
        if last_signal_time:
            time_since_last = datetime.now() - last_signal_time.replace(tzinfo=None)
            hours_since_last = time_since_last.total_seconds() / 3600

            if hours_since_last > 48:
                status["healthy"] = False
                status["errors"].append(
                    f"CRITICAL: No signals for {hours_since_last:.1f} hours (2+ days)"
                )
            elif hours_since_last > 24:
                status["warnings"].append(
                    f"WARNING: No signals for {hours_since_last:.1f} hours (1+ day)"
                )
        else:
            status["healthy"] = False
            status["errors"].append("CRITICAL: No signals found in database")

        # Check 2: Very few signals in 24h (might indicate issue)
        if signals_24h < 5:
            status["warnings"].append(
                f"WARNING: Only {signals_24h} signals in last 24h (expected ~10-20)"
            )

        cur.close()
        conn.close()

        return status

    except Exception as e:
        return {
            "healthy": False,
            "warnings": [],
            "errors": [f"CRITICAL: Database connection failed: {str(e)}"],
        }


if __name__ == "__main__":
    print("=" * 70)
    print("Abu Scanner Health Check")
    print("=" * 70)
    print()

    status = check_scanner_health()

    if status["healthy"]:
        print("✓ Scanner is HEALTHY")
    else:
        print("✗ Scanner has ISSUES")

    print()

    if status["errors"]:
        print("ERRORS:")
        for error in status["errors"]:
            print(f"  ✗ {error}")
        print()

    if status["warnings"]:
        print("WARNINGS:")
        for warning in status["warnings"]:
            print(f"  ⚠ {warning}")
        print()

    # Exit with error code if unhealthy
    sys.exit(0 if status["healthy"] else 1)
