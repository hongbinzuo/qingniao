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
    """Get database URL from environment.

    Prefer DATABASE_URL, fallback to PG_* variables if provided.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url

    host = os.getenv("PG_HOST")
    port = os.getenv("PG_PORT")
    database = os.getenv("PG_DATABASE")
    user = os.getenv("PG_USER")
    password = os.getenv("PG_PASSWORD", "")

    if all([host, port, database, user]):
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"

    print("ERROR: DATABASE_URL or PG_* environment variables not set")
    print("Usage: export DATABASE_URL='postgresql://user:pass@host:port/db'")
    sys.exit(1)


def create_tables(conn):
    """Create all necessary tables (aligned with Abu/Postgres schema)."""
    cursor = conn.cursor()

    print("Creating trading_signals table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trading_signals (
            id SERIAL PRIMARY KEY,
            signal_time TIMESTAMP NOT NULL,
            timeframe VARCHAR(10),
            symbol VARCHAR(20),
            signal_type VARCHAR(10),
            entry_price NUMERIC(20, 8),
            stop_loss NUMERIC(20, 8),
            take_profit_1 NUMERIC(20, 8),
            take_profit_2 NUMERIC(20, 8),
            entry_model TEXT,
            strength VARCHAR(20),
            risk_reward_ratio NUMERIC(10, 2),
            volatility_level VARCHAR(20),
            system_name VARCHAR(50),
            score NUMERIC(10, 2),
            notes TEXT,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,

            -- 信号反馈相关字段
            entry_time TIMESTAMP,
            exit_time TIMESTAMP,
            exit_price NUMERIC(20, 8),
            exit_reason TEXT,
            pnl_pct NUMERIC(10, 4),
            breakeven_stop_set BOOLEAN DEFAULT FALSE,
            quick_tp_reached BOOLEAN DEFAULT FALSE,
            last_check_time TIMESTAMP,
            check_count INTEGER DEFAULT 0,
            entry_price_actual NUMERIC(20, 8)
        )
    """
    )

    print("Creating trading_signals indexes...")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trading_signals(symbol)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_signals_status ON trading_signals(status)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_signals_created_at ON trading_signals(created_at)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_signals_timeframe ON trading_signals(timeframe)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_signals_system ON trading_signals(system_name)"
    )
    print("✓ trading_signals table created")

    print("Creating signal_evaluations table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS signal_evaluations (
            id SERIAL PRIMARY KEY,
            signal_id INTEGER NOT NULL,
            evaluation_time TIMESTAMP NOT NULL,
            result VARCHAR(20),
            actual_entry_price NUMERIC(20, 8),
            actual_exit_price NUMERIC(20, 8),
            actual_profit_pct NUMERIC(10, 4),
            actual_profit_usdt NUMERIC(20, 8),
            stop_loss_hit BOOLEAN DEFAULT FALSE,
            take_profit_1_hit BOOLEAN DEFAULT FALSE,
            take_profit_2_hit BOOLEAN DEFAULT FALSE,
            missed BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (signal_id) REFERENCES trading_signals(id) ON DELETE CASCADE
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_evaluations_signal_id ON signal_evaluations(signal_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_evaluations_time ON signal_evaluations(evaluation_time)"
    )
    print("✓ signal_evaluations table created")

    print("Creating pattern_library table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS pattern_library (
            id SERIAL PRIMARY KEY,
            pattern_name TEXT,
            pattern_type TEXT,
            source_page INTEGER,
            source_pdf TEXT,
            image_path TEXT,
            context_text TEXT,
            gemini_annotation_json TEXT,
            chart_features_json TEXT,
            timeframe_hint TEXT,
            direction TEXT,
            key_features TEXT,
            confidence DOUBLE PRECISION,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            ebook_references TEXT,
            text_description TEXT
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pattern_type ON pattern_library(pattern_type)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pattern_name ON pattern_library(pattern_name)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_pattern_source_page ON pattern_library(source_page)"
    )
    print("✓ pattern_library table created")

    print("Creating ml_optimization_results table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS ml_optimization_results (
            id SERIAL PRIMARY KEY,
            model_type VARCHAR(50),
            parameters_json TEXT,
            metrics_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_ml_model_type ON ml_optimization_results(model_type)"
    )
    print("✓ ml_optimization_results table created")

    print("Creating system_configs table...")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS system_configs (
            id SERIAL PRIMARY KEY,
            config_key VARCHAR(100) UNIQUE NOT NULL,
            config_value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_config_key ON system_configs(config_key)"
    )
    print("✓ system_configs table created")

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
