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
import time
from datetime import datetime, timedelta
from pathlib import Path

import psycopg2
import requests
from flask import Flask, jsonify, render_template, request
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.kline_feature_extractor import extract_basic_kline_features  # type: ignore
from abu.market_context import classify_market_context  # type: ignore
from generate_comprehensive_trading_plans import get_kline_gateio  # type: ignore

app = Flask(__name__, template_folder=str(ROOT / "templates"))

TREND_CACHE = {}
TREND_CACHE_TTL_SEC = int(os.getenv("TREND_CACHE_TTL_SEC", "60"))


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

def _normalize_symbol(sym: str) -> str:
    return (sym or "").strip().upper()


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _fetch_gate_ticker_price(symbol: str) -> float:
    pair = f"{symbol}_USDT"
    try:
        resp = requests.get(
            "https://api.gateio.ws/api/v4/spot/tickers",
            params={"currency_pair": pair},
            timeout=10,
        )
        if resp.status_code != 200:
            return 0.0
        data = resp.json()
        if isinstance(data, list) and data:
            return _safe_float(data[0].get("last"), 0.0)
    except Exception:
        return 0.0
    return 0.0


def _compute_trend_payload(
    symbol: str, timeframe: str, klines: list, live_price: float = 0.0
) -> dict:
    if not klines or len(klines) < 50:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "error": "kline_insufficient",
        }

    highs = [k.get("high") for k in klines if k.get("high") is not None]
    lows = [k.get("low") for k in klines if k.get("low") is not None]
    last_close = klines[-1].get("close")

    features = extract_basic_kline_features(klines)
    context = classify_market_context(klines, features)

    range_high = max(highs) if highs else None
    range_low = min(lows) if lows else None

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "price": _safe_float(live_price, last_close or 0.0),
        "range_low": _safe_float(range_low, 0.0),
        "range_high": _safe_float(range_high, 0.0),
        "trend_label": context.get("label"),
        "trend_direction": context.get("trend_direction"),
        "trend_strength": _safe_float(context.get("trend_strength"), 0.0),
        "regime_36": context.get("regime_36"),
        "overlap_ratio": _safe_float(context.get("overlap_ratio"), 0.0),
        "range_pct": _safe_float(features.get("range_pct"), 0.0),
        "updated_at": datetime.now().isoformat(),
    }


@app.route("/api/trend")
def get_trend():
    """Get Brooks-style trend + range (4h/1d) for BTC/ETH/SOL."""
    symbols_raw = request.args.get("symbols", "BTC,ETH,SOL")
    tfs_raw = request.args.get("timeframes", "4h,1d")
    symbols = [_normalize_symbol(s) for s in symbols_raw.split(",") if s.strip()]
    timeframes = [tf.strip().lower() for tf in tfs_raw.split(",") if tf.strip()]

    limit_map = {
        "4h": 200,
        "1d": 200,
    }

    now_ts = time.time()
    live_prices = {sym: _fetch_gate_ticker_price(sym) for sym in symbols}
    items = []
    for sym in symbols:
        for tf in timeframes:
            cache_key = f"{sym}:{tf}"
            cached = TREND_CACHE.get(cache_key)
            if cached:
                age = now_ts - cached.get("ts", 0)
                if age <= TREND_CACHE_TTL_SEC:
                    items.append(cached["payload"])
                    continue

            klines = get_kline_gateio(
                symbol=sym, timeframe=tf, limit=limit_map.get(tf, 200)
            )
            payload = _compute_trend_payload(
                sym, tf, klines or [], live_price=live_prices.get(sym, 0.0)
            )
            TREND_CACHE[cache_key] = {"ts": now_ts, "payload": payload}
            items.append(payload)

    return jsonify(
        {
            "symbols": symbols,
            "timeframes": timeframes,
            "items": items,
            "cached_ttl_sec": TREND_CACHE_TTL_SEC,
            "server_time": datetime.now().isoformat(),
        }
    )


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
