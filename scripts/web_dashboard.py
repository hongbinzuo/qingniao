#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Railway Web Dashboard - Monitor Abu Scanner Status

Simple web interface to view:
- Scanner running status
- Recent signals
- Signal auditing status (TP/SL outcomes)
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
from flask import Flask, jsonify, render_template, request
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

app = Flask(__name__, template_folder=str(ROOT / "templates"))


# Database connection
def get_db_connection():
    """Get PostgreSQL connection"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # Fallback to PG_* variables
        host = os.getenv("PG_HOST", "localhost")
        port = os.getenv("PG_PORT", "5432")
        database = os.getenv("PG_DATABASE", "qingniao_abu")
        user = os.getenv("PG_USER", "abu_user")
        password = os.getenv("PG_PASSWORD", "")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


@app.route("/")
def index():
    """Main dashboard page"""
    return render_template("dashboard.html")


@app.route("/api/status")
def get_status():
    """Get scanner running status"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get latest signal timestamp
        cur.execute("""
            SELECT MAX(created_at) as last_signal_time,
                   COUNT(*) as total_signals_24h
            FROM trading_signals
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        result = cur.fetchone()

        last_signal_time = result["last_signal_time"]
        is_running = False
        status_message = "Unknown"

        if last_signal_time:
            time_diff = datetime.now() - last_signal_time.replace(tzinfo=None)
            if time_diff < timedelta(minutes=30):
                is_running = True
                status_message = "Running"
            else:
                status_message = f"Stopped (last signal {int(time_diff.total_seconds() / 60)} min ago)"
        else:
            status_message = "No signals yet"

        cur.close()
        conn.close()

        return jsonify(
            {
                "running": is_running,
                "status": status_message,
                "last_signal_time": last_signal_time.isoformat()
                if last_signal_time
                else None,
                "signals_24h": result["total_signals_24h"],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/signals")
def get_signals():
    """Get recent signals"""
    try:
        limit = int(request.args.get("limit", 50))
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
                id,
                symbol,
                timeframe,
                direction,
                entry_price,
                stop_loss,
                take_profit,
                signal_mode,
                pattern_score,
                vector_match_score,
                created_at
            FROM trading_signals
            ORDER BY created_at DESC
            LIMIT %s
        """,
            (limit,),
        )

        signals = cur.fetchall()
        cur.close()
        conn.close()

        return jsonify({"signals": [dict(s) for s in signals], "count": len(signals)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/auditing')
def get_auditing_status():
    """Get signal auditing status (TP/SL outcomes)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get evaluation statistics
        cur.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE outcome = 'full_tp') as full_tp,
                COUNT(*) FILTER (WHERE outcome = 'partial_tp') as partial_tp,
                COUNT(*) FILTER (WHERE outcome = 'stopped') as stopped,
                COUNT(*) FILTER (WHERE outcome = 'running') as running,
                COUNT(*) as total
            FROM signal_evaluations
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        
        stats = cur.fetchone()
        cur.close()
        conn.close()
        
        return jsonify({
            'full_tp': stats['full_tp'] or 0,
            'partial_tp': stats['partial_tp'] or 0,
            'stopped': stats['stopped'] or 0,
            'running': stats['running'] or 0,
            'total': stats['total'] or 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
