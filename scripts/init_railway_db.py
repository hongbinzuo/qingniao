#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize Railway PostgreSQL Database Schema

This script creates all necessary tables for the Abu trading signal scanner.
Run this once before deploying to Railway.

Usage:
    export DATABASE_URL="postgresql://user:pass@host:port/db"
    python scripts/init_railway_db.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


def get_database_url():
    """Get database URL from environment"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        print("Usage: export DATABASE_URL='postgresql://user:pass@host:port/db'")
        sys.exit(1)
    return db_url


def create_tables(conn):
    """Create all necessary tables"""
    cursor = conn.cursor()

    print("Creating trading_signals table...")

    # Create trading_signals table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trading_signals (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timeframe VARCHAR(10) NOT NULL,
            direction VARCHAR(10) NOT NULL,
            entry_price DECIMAL(20, 8) NOT NULL,
            tp1 DECIMAL(20, 8),
            tp2 DECIMAL(20, 8),
            sl DECIMAL(20, 8),
            confidence DECIMAL(5, 4),
            pattern_type VARCHAR(50),
            signal_mode VARCHAR(20),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    print("✓ trading_signals table created")

    # Create indexes for better query performance
    print("Creating indexes...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_symbol
        ON trading_signals(symbol)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_created_at
        ON trading_signals(created_at DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_timeframe
        ON trading_signals(timeframe)
    """)

    print("✓ Indexes created")

    conn.commit()
    cursor.close()


def main():
    """Main initialization function"""
    print("=" * 70)
    print("Railway PostgreSQL Database Initialization")
    print("=" * 70)
    print("")

    db_url = get_database_url()
    print(f"Connecting to database...")

    try:
        conn = psycopg2.connect(db_url)
        print("✓ Connected successfully")
        print("")

        create_tables(conn)

        conn.close()
        print("")
        print("=" * 70)
        print("✓ Database initialization complete!")
        print("=" * 70)

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
