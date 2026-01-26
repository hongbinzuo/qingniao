#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU signal replay audit (independent verifier).

Rules:
- Entry on touch (high/low crosses entry price)
- SL has priority if SL and TP are hit in the same bar
- Gate data only
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.market_cache import MarketDataCache  # type: ignore
from db_manager_trader import TraderDBManager  # type: ignore

OUTPUT_DIR = ROOT / "outputs" / "trading_signals"

STATUS_MAP = {
    "pending": "pending",
    "active": "active",
    "partial_tp": "active",
    "full_tp": "completed",
    "stopped": "stopped",
    "missed": "missed",
}


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _fetch_signals(
    db: TraderDBManager,
    start_time: datetime,
    end_time: datetime,
    timeframes: List[str],
) -> List[Dict]:
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    tf_placeholders = ",".join(["?"] * len(timeframes))
    sql = f"""
        SELECT id, signal_time, timeframe, symbol, signal_type,
               entry_price, stop_loss, take_profit_1, take_profit_2, status
        FROM trading_signals
        WHERE system_name = ?
          AND signal_time >= ?
          AND signal_time < ?
          AND timeframe IN ({tf_placeholders})
        ORDER BY signal_time ASC
    """
    params = ["abu", start_str, end_str] + timeframes
    conn = db._get_connection(read_only=True)
    try:
        cur = conn.execute(sql, params)
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description] if cur.description else []
    finally:
        conn.close()
    return [dict(zip(cols, row)) for row in rows]


def _to_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal("0")


def _fmt_decimal(value: Optional[Decimal], precision: int) -> str:
    if value is None:
        return "-"
    quant = Decimal("1").scaleb(-precision)
    return str(value.quantize(quant, rounding=ROUND_HALF_UP))


def _limit_window(
    start_ts: int,
    end_ts: int,
    max_lookback_days: int,
) -> Tuple[int, bool]:
    max_seconds = max(1, int(max_lookback_days)) * 86400
    if end_ts - start_ts <= max_seconds:
        return start_ts, False
    return end_ts - max_seconds, True


def _fetch_1m_klines(
    cache: MarketDataCache,
    symbol: str,
    start_ts: int,
    end_ts: int,
) -> List[Dict]:
    klines, _requests = cache._fetch_gate_klines_paged(
        symbol,
        "1m",
        limit=0,
        from_ts=start_ts,
        to_ts=end_ts,
    )
    return klines


def _replay_signal(
    signal: Dict,
    klines: List[Dict],
    start_ts: int,
    end_ts: int,
    entry_deadline_ts: Optional[int],
    truncated: bool,
    precision: int,
) -> Dict:
    entry = _to_decimal(signal.get("entry_price") or 0.0)
    stop = _to_decimal(signal.get("stop_loss") or 0.0)
    tp1 = _to_decimal(signal.get("take_profit_1") or 0.0)
    tp2 = _to_decimal(signal.get("take_profit_2") or 0.0)
    direction = str(signal.get("signal_type") or "long").lower()

    result = {
        "status": "pending",
        "entry_time": None,
        "exit_time": None,
        "exit_price": None,
        "reason": None,
    }

    if entry <= 0 or stop <= 0 or tp1 <= 0 or direction not in ("long", "short"):
        result["status"] = "invalid"
        result["reason"] = "invalid_signal"
        return result

    if not klines:
        result["status"] = "no_data"
        result["reason"] = "no_klines"
        return result

    earliest_ts = klines[0].get("timestamp", 0)
    if earliest_ts and earliest_ts > start_ts:
        result["status"] = "insufficient_data"
        result["reason"] = "data_gap"
        return result

    status = "pending"
    tp1_hit = False
    entry_ts = None

    for k in klines:
        ts = int(k.get("timestamp", 0))
        if ts < start_ts:
            continue
        if ts > end_ts:
            break
        high = _to_decimal(k.get("high", 0.0))
        low = _to_decimal(k.get("low", 0.0))

        if status == "pending":
            if entry_deadline_ts is not None and ts > entry_deadline_ts:
                if truncated:
                    result["status"] = "insufficient_data"
                    result["reason"] = "truncated_window"
                else:
                    result["status"] = "missed"
                    result["reason"] = "no_entry"
                return result
            if low <= entry <= high:
                status = "active"
                entry_ts = ts
            else:
                continue

        if direction == "long":
            if low <= stop:
                result.update(
                    status="stopped",
                    exit_time=datetime.fromtimestamp(ts).isoformat(),
                    exit_price=_fmt_decimal(stop, precision),
                    reason="stop_loss",
                )
                break
            if tp2 > 0 and high >= tp2:
                result.update(
                    status="full_tp",
                    exit_time=datetime.fromtimestamp(ts).isoformat(),
                    exit_price=_fmt_decimal(tp2, precision),
                    reason="tp2",
                )
                break
            if not tp1_hit and high >= tp1:
                tp1_hit = True
                status = "partial_tp"
        else:
            if high >= stop:
                result.update(
                    status="stopped",
                    exit_time=datetime.fromtimestamp(ts).isoformat(),
                    exit_price=_fmt_decimal(stop, precision),
                    reason="stop_loss",
                )
                break
            if tp2 > 0 and low <= tp2:
                result.update(
                    status="full_tp",
                    exit_time=datetime.fromtimestamp(ts).isoformat(),
                    exit_price=_fmt_decimal(tp2, precision),
                    reason="tp2",
                )
                break
            if not tp1_hit and low <= tp1:
                tp1_hit = True
                status = "partial_tp"

    if result["status"] in ("stopped", "full_tp"):
        result["entry_time"] = datetime.fromtimestamp(entry_ts).isoformat() if entry_ts else None
        return result

    if status == "pending":
        if truncated:
            result["status"] = "insufficient_data"
            result["reason"] = "truncated_window"
        else:
            result["status"] = "missed"
            result["reason"] = "no_entry"
        return result

    result["status"] = status
    result["entry_time"] = datetime.fromtimestamp(entry_ts).isoformat() if entry_ts else None
    result["reason"] = "open_end" if status in ("active", "partial_tp") else None
    return result


def _write_report(path: Path, rows: List[Dict], summary: Dict) -> None:
    lines = []
    lines.append("# ABU signal replay audit\n")
    lines.append(f"- generated_at: {summary.get('generated_at')}")
    lines.append(f"- total: {summary.get('total')}")
    lines.append(f"- matched: {summary.get('matched')}")
    lines.append(f"- mismatched: {summary.get('mismatched')}")
    lines.append(f"- insufficient_data: {summary.get('insufficient_data')}")
    lines.append("")
    lines.append("| ID | Symbol | TF | DB | Replay | Mapped | Match | Reason |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in rows:
        lines.append(
            "| {id} | {symbol} | {tf} | {db} | {replay} | {mapped} | {match} | {reason} |".format(
                id=row.get("id"),
                symbol=row.get("symbol"),
                tf=row.get("timeframe"),
                db=row.get("db_status"),
                replay=row.get("replay_status"),
                mapped=row.get("mapped_status"),
                match=row.get("match"),
                reason=row.get("reason") or "-",
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="ABU signal replay audit (Gate only)")
    parser.add_argument("--start", type=str, default="2026-01-25 00:00:00")
    parser.add_argument("--end", type=str, default="")
    parser.add_argument("--timeframes", type=str, default="5m,15m,1h")
    parser.add_argument("--sample", type=int, default=20)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-lookback-days", type=int, default=7)
    parser.add_argument("--expiry-5m-hours", type=int, default=2)
    parser.add_argument("--expiry-15m-hours", type=int, default=4)
    parser.add_argument("--expiry-1h-hours", type=int, default=4)
    parser.add_argument("--no-expiry", action="store_true")
    parser.add_argument("--precision", type=int, default=9)
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    start_time = _parse_dt(args.start)
    if not start_time:
        print("invalid --start", file=sys.stderr)
        return 2
    end_time = _parse_dt(args.end) if args.end else datetime.now()
    if not end_time:
        print("invalid --end", file=sys.stderr)
        return 2

    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip()]
    if not timeframes:
        print("no timeframes", file=sys.stderr)
        return 2

    db = TraderDBManager("abu")
    rows = _fetch_signals(db, start_time, end_time, timeframes)
    if not rows:
        print("no signals found", file=sys.stderr)
        return 1

    if args.sample and len(rows) > args.sample:
        if args.seed:
            random.seed(args.seed)
        rows = random.sample(rows, args.sample)

    cache = MarketDataCache(default_exchange="gate")
    results = []
    matched = 0
    mismatched = 0
    insufficient = 0

    for record in rows:
        signal_time = _parse_dt(record.get("signal_time"))
        if not signal_time:
            continue
        expiry_hours = args.expiry_15m_hours
        if record.get("timeframe") == "5m":
            expiry_hours = args.expiry_5m_hours
        elif record.get("timeframe") == "1h":
            expiry_hours = args.expiry_1h_hours
        end_ts = int(end_time.timestamp())
        entry_deadline_ts = None
        if not args.no_expiry:
            entry_deadline_ts = int((signal_time + timedelta(hours=expiry_hours)).timestamp())
        start_ts = int(signal_time.timestamp())
        limited_start, truncated = _limit_window(start_ts, end_ts, args.max_lookback_days)
        klines = _fetch_1m_klines(cache, str(record.get("symbol") or "").upper(), limited_start, end_ts)
        replay = _replay_signal(record, klines, start_ts, end_ts, entry_deadline_ts, truncated, args.precision)
        replay_status = replay.get("status")
        mapped = STATUS_MAP.get(replay_status, replay_status)
        db_status = record.get("status")
        match = "Y" if mapped == db_status else "N"
        if match == "Y":
            matched += 1
        else:
            mismatched += 1
        if replay_status in ("insufficient_data", "no_data"):
            insufficient += 1
        results.append(
            {
                "id": record.get("id"),
                "symbol": str(record.get("symbol") or "").upper(),
                "timeframe": record.get("timeframe"),
                "db_status": db_status,
                "replay_status": replay_status,
                "mapped_status": mapped,
                "match": match,
                "reason": replay.get("reason"),
            }
        )

    output_path = Path(args.output) if args.output else (
        OUTPUT_DIR / f"ABU_signal_replay_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(results),
        "matched": matched,
        "mismatched": mismatched,
        "insufficient_data": insufficient,
    }
    _write_report(output_path, results, summary)
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
