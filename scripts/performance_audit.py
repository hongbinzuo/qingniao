#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Performance Audit Report
Evaluate recent signals against historical candles to estimate outcomes.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager  # type: ignore
from abu.market_cache import MarketDataCache, TIMEFRAME_SECONDS  # type: ignore


def _parse_dt(value: object) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _normalize_symbol(symbol: str) -> str:
    sym = str(symbol or "").upper().strip()
    if sym.endswith("_USDT"):
        sym = sym.replace("_USDT", "")
    if sym.endswith("USDT") and len(sym) > 4:
        sym = sym.replace("USDT", "")
    sym = sym.replace("-", "").replace("/", "")
    return sym


def _calc_pnl(direction: str, entry: float, exit_price: float) -> float:
    if entry <= 0:
        return 0.0
    if direction == "long":
        return (exit_price - entry) / entry * 100.0
    return (entry - exit_price) / entry * 100.0


def _fetch_klines(
    cache: MarketDataCache,
    symbol: str,
    timeframe: str,
    start_ts: int,
    end_ts: Optional[int],
) -> List[Dict]:
    if timeframe not in TIMEFRAME_SECONDS:
        return []
    klines, _ = cache._fetch_gate_klines_paged(
        symbol, timeframe, limit=1000, from_ts=start_ts, to_ts=end_ts
    )
    return klines


def _evaluate_signal(
    signal: Dict,
    klines: List[Dict],
) -> Dict[str, object]:
    direction = str(signal.get("signal_type") or "").lower()
    entry = float(signal.get("entry_price") or 0.0)
    stop = float(signal.get("stop_loss") or 0.0)
    tp1 = float(signal.get("take_profit_1") or 0.0)
    tp2 = float(signal.get("take_profit_2") or 0.0)

    if direction not in ("long", "short") or entry <= 0 or stop <= 0:
        return {"status": "invalid", "pnl": 0.0}

    for k in klines:
        high = float(k.get("high") or 0.0)
        low = float(k.get("low") or 0.0)
        ts = int(k.get("timestamp") or 0)
        hit_time = datetime.fromtimestamp(ts).isoformat() if ts else None

        if direction == "long":
            if low <= stop:
                return {
                    "status": "stopped",
                    "hit_time": hit_time,
                    "exit_price": stop,
                    "pnl": _calc_pnl(direction, entry, stop),
                }
            if tp2 > 0 and high >= tp2:
                return {
                    "status": "tp2",
                    "hit_time": hit_time,
                    "exit_price": tp2,
                    "pnl": _calc_pnl(direction, entry, tp2),
                }
            if tp1 > 0 and high >= tp1:
                return {
                    "status": "tp1",
                    "hit_time": hit_time,
                    "exit_price": tp1,
                    "pnl": _calc_pnl(direction, entry, tp1),
                }
        else:
            if high >= stop:
                return {
                    "status": "stopped",
                    "hit_time": hit_time,
                    "exit_price": stop,
                    "pnl": _calc_pnl(direction, entry, stop),
                }
            if tp2 > 0 and low <= tp2:
                return {
                    "status": "tp2",
                    "hit_time": hit_time,
                    "exit_price": tp2,
                    "pnl": _calc_pnl(direction, entry, tp2),
                }
            if tp1 > 0 and low <= tp1:
                return {
                    "status": "tp1",
                    "hit_time": hit_time,
                    "exit_price": tp1,
                    "pnl": _calc_pnl(direction, entry, tp1),
                }

    if klines:
        last_close = float(klines[-1].get("close") or 0.0)
        return {
            "status": "active",
            "pnl": _calc_pnl(direction, entry, last_close),
        }

    return {"status": "no_data", "pnl": 0.0}


def _group_stats(results: List[Dict]) -> Dict[str, Dict[str, int]]:
    grouped: Dict[str, Dict[str, int]] = {}
    for r in results:
        tf = r.get("timeframe") or "unknown"
        status = r.get("status") or "unknown"
        bucket = grouped.setdefault(tf, {})
        bucket[status] = bucket.get(status, 0) + 1
    return grouped


def main() -> None:
    parser = argparse.ArgumentParser(description="Performance audit report")
    parser.add_argument(
        "--hours",
        type=float,
        default=4.0,
        help="Lookback window in hours (default: 4)",
    )
    parser.add_argument(
        "--max-signals",
        type=int,
        default=200,
        help="Max number of signals to evaluate (default: 200)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(ROOT / "outputs" / "audit_reports"),
        help="Output directory for report",
    )

    args = parser.parse_args()
    hours = max(float(args.hours), 0.1)
    max_signals = max(int(args.max_signals), 1)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cutoff = datetime.now() - timedelta(hours=hours)
    days = max(1, int(hours // 24) + 1)

    db = TraderDBManager("abu")
    signals = db.get_trading_signals(system_name="abu", limit=max_signals, days=days)

    recent: List[Dict] = []
    for s in signals:
        ts = _parse_dt(s.get("signal_time")) or _parse_dt(s.get("created_at"))
        if ts and ts >= cutoff:
            recent.append(s)

    cache = MarketDataCache(default_exchange="gate")
    results: List[Dict] = []
    end_ts = int(datetime.now().timestamp())

    for s in recent:
        tf = str(s.get("timeframe") or "").lower()
        ts = _parse_dt(s.get("signal_time")) or _parse_dt(s.get("created_at"))
        if not ts:
            continue
        start_ts = int(ts.timestamp())
        symbol = _normalize_symbol(s.get("symbol") or "")
        if not symbol:
            continue

        klines = _fetch_klines(cache, symbol, tf, start_ts, end_ts)
        outcome = _evaluate_signal(s, klines)
        results.append(
            {
                "symbol": symbol,
                "timeframe": tf,
                "status": outcome.get("status"),
                "pnl": outcome.get("pnl"),
            }
        )

    total = len(results)
    wins = sum(1 for r in results if r["status"] in ("tp1", "tp2"))
    losses = sum(1 for r in results if r["status"] == "stopped")
    active = sum(1 for r in results if r["status"] == "active")
    invalid = sum(1 for r in results if r["status"] in ("invalid", "no_data"))
    closed = wins + losses
    win_rate = (wins / closed * 100.0) if closed else 0.0

    grouped = _group_stats(results)

    lines: List[str] = []
    lines.append("# Performance Audit Report")
    lines.append("")
    lines.append(f"- Window: last {hours:.2f} hours")
    lines.append(f"- Signals analyzed: {total}")
    lines.append(f"- Wins (TP1/TP2): {wins}")
    lines.append(f"- Losses (Stopped): {losses}")
    lines.append(f"- Active: {active}")
    lines.append(f"- Invalid/No data: {invalid}")
    lines.append(f"- Win rate (closed only): {win_rate:.2f}%")
    lines.append("")
    lines.append("## By Timeframe")
    if grouped:
        for tf in sorted(grouped.keys()):
            stats = grouped[tf]
            stats_str = ", ".join(f"{k}={v}" for k, v in sorted(stats.items()))
            lines.append(f"- {tf}: {stats_str}")
    else:
        lines.append("- No data")
    lines.append("")
    lines.append("## Notes")
    lines.append("- Uses Gate spot candles and signal_time as start.")
    lines.append("- If stop and target hit in same candle, stop is counted (conservative).")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"performance_report_{timestamp}.txt"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(report_path)


if __name__ == "__main__":
    main()
