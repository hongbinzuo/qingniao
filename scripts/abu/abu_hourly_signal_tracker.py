#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU 信号定期跟踪器（北京时间）

从指定起始时间起，按固定周期扫描最新价格，判断止盈/部分止盈/止损状态，
并将结果追加写入本地文档：
  outputs/trading_signals/ABU_signal_hourly_tracking.md
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.signal_result_feedback import SignalResultFeedback  # type: ignore
from db_manager_trader import TraderDBManager  # type: ignore

OUTPUT_DIR = ROOT / "outputs" / "trading_signals"
LOG_DIR = ROOT / "logs"


def _format_price(value: Optional[object]) -> str:
    if value is None:
        return "-"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "-"
    abs_num = abs(num)
    if abs_num >= 1:
        return f"{num:.4f}"
    if abs_num >= 0.01:
        return f"{num:.6f}"
    return f"{num:.9f}"


def _bj_tz() -> timezone:
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Asia/Shanghai")
    except Exception:
        return timezone(timedelta(hours=8))


def _parse_start(value: str) -> datetime:
    if not value:
        return datetime(2026, 1, 25, 0, 0, 0, tzinfo=_bj_tz())
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=_bj_tz())
        except Exception:
            continue
    raise ValueError(f"start 格式错误: {value}")


def _next_run_time(now_bj: datetime, interval_minutes: int) -> datetime:
    interval = max(1, int(interval_minutes))
    return now_bj + timedelta(minutes=interval)


def _fetch_active_signals_since(db: TraderDBManager, start_time: datetime) -> List[Dict]:
    start_str = start_time.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
    conn = db._get_connection(read_only=True)
    try:
        cur = conn.execute(
            """
            SELECT id, signal_time, timeframe, symbol, signal_type, entry_price,
                   stop_loss, take_profit_1, take_profit_2, status,
                   entry_time, exit_time, exit_price, exit_reason, pnl_pct,
                   breakeven_stop_set, quick_tp_reached, last_check_time, check_count
            FROM trading_signals
            WHERE system_name = ?
              AND signal_time >= ?
              AND status IN ('pending', 'active', 'partial_tp')
            ORDER BY signal_time ASC
            """,
            ("abu", start_str),
        )
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description] if cur.description else []
    finally:
        conn.close()

    signals: List[Dict] = []
    for row in rows:
        record = dict(zip(cols, row)) if cols else {}
        signal_time = record.get("signal_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        signal = {
            "signal_id": f"{record.get('symbol', 'Unknown')}_{record.get('timeframe', '5m')}_{str(signal_time).replace(':', '').replace(' ', '_')}",
            "db_id": record.get("id"),
            "symbol": str(record.get("symbol") or "Unknown").upper(),
            "timeframe": record.get("timeframe") or "5m",
            "direction": str(record.get("signal_type") or "long").lower(),
            "entry_price": float(record.get("entry_price") or 0),
            "stop_loss": float(record.get("stop_loss") or 0),
            "take_profit_1": float(record.get("take_profit_1") or 0),
            "take_profit_2": float(record.get("take_profit_2") or 0),
            "generated_time": str(signal_time),
            "status": record.get("status") or "pending",
            "entry_time": record.get("entry_time"),
            "exit_time": record.get("exit_time"),
            "exit_price": record.get("exit_price"),
            "exit_reason": record.get("exit_reason"),
            "pnl_pct": record.get("pnl_pct") or 0.0,
            "breakeven_stop_set": bool(record.get("breakeven_stop_set") or False),
            "quick_tp_reached": bool(record.get("quick_tp_reached") or False),
            "last_check_time": record.get("last_check_time"),
            "check_count": record.get("check_count") or 0,
        }
        signals.append(signal)
    return signals


def _write_report(
    output_path: Path,
    run_time: datetime,
    start_time: datetime,
    stats: Dict,
    changed: List[Dict],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not output_path.exists():
        output_path.write_text("# ABU 信号每小时跟踪日志\n\n", encoding="utf-8")

    lines: List[str] = []
    lines.append(f"## 扫描时间: {run_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    lines.append(f"- 跟踪起点: {start_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    lines.append(
        "- 状态统计: "
        f"total={stats.get('total', 0)}, "
        f"pending={stats.get('pending', 0)}, "
        f"active={stats.get('active', 0)}, "
        f"partial_tp={stats.get('partial_tp', 0)}, "
        f"quick_tp={stats.get('quick_tp', 0)}, "
        f"full_tp={stats.get('full_tp', 0)}, "
        f"stopped={stats.get('stopped', 0)}, "
        f"expired={stats.get('expired', 0)}, "
        f"updated={stats.get('updated', 0)}"
    )
    lines.append("")
    lines.append("### 状态变更")
    lines.append("| ID | Symbol | TF | Old | New | Entry | SL | TP1 | TP2 | Exit | PnL% | Reason |")
    lines.append("|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|")
    for row in changed:
        entry_fmt = _format_price(row.get("entry_price"))
        sl_fmt = _format_price(row.get("stop_loss"))
        tp1_fmt = _format_price(row.get("take_profit_1"))
        tp2_fmt = _format_price(row.get("take_profit_2"))
        exit_fmt = _format_price(row.get("exit_price"))
        lines.append(
            "| {id} | {symbol} | {tf} | {old} | {new} | {entry} | {sl} | {tp1} | {tp2} | {exit} | {pnl} | {reason} |".format(
                id=row.get("signal_id"),
                symbol=row.get("symbol"),
                tf=row.get("timeframe"),
                old=row.get("old_status"),
                new=row.get("status"),
                entry=entry_fmt,
                sl=sl_fmt,
                tp1=tp1_fmt,
                tp2=tp2_fmt,
                exit=exit_fmt,
                pnl=f"{float(row.get('pnl_pct') or 0.0):.2f}",
                reason=row.get("exit_reason") or "-",
            )
        )
    lines.append("")

    with output_path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        fh.write("\n")


def _setup_logger(log_file: Path) -> logging.Logger:
    logger = logging.getLogger("abu_hourly_signal_tracker")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(sh)
    return logger


def run_once(start_time: datetime, logger: logging.Logger) -> None:
    feedback = SignalResultFeedback(trader_id="abu", use_database=True, load_on_init=False)
    db = TraderDBManager("abu")
    signals = _fetch_active_signals_since(db, start_time)
    feedback.active_signals = signals

    before: Dict[str, str] = {s["signal_id"]: s.get("status") for s in signals}
    stats = feedback.check_all_signals()
    changed = []
    for s in feedback.active_signals:
        old_status = before.get(s["signal_id"])
        if old_status and old_status != s.get("status"):
            row = dict(s)
            row["old_status"] = old_status
            changed.append(row)

    output_path = OUTPUT_DIR / "ABU_signal_hourly_tracking.md"
    _write_report(output_path, datetime.now(tz=_bj_tz()), start_time, stats, changed)
    logger.info("Tracked %s signals; updated=%s", stats.get("total", 0), stats.get("updated", 0))


def main() -> int:
    parser = argparse.ArgumentParser(description="ABU signals interval tracker (Beijing time)")
    parser.add_argument("--start", type=str, default="2026-01-25 00:00:00", help="Beijing start time")
    parser.add_argument("--interval-minutes", type=int, default=60, help="Run interval in minutes")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    try:
        start_time = _parse_start(args.start)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    logger = _setup_logger(LOG_DIR / "abu_hourly_signal_tracker.log")
    logger.info("Start tracking from %s (Beijing)", start_time.strftime("%Y-%m-%d %H:%M:%S"))

    run_once(start_time, logger)
    if args.once:
        return 0

    while True:
        now_bj = datetime.now(tz=_bj_tz())
        next_run = _next_run_time(now_bj, args.interval_minutes)
        sleep_for = max(1, int((next_run - now_bj).total_seconds()))
        logger.info("Next run at %s (sleep %ss)", next_run.strftime("%Y-%m-%d %H:%M:%S"), sleep_for)
        time.sleep(sleep_for)
        run_once(start_time, logger)


if __name__ == "__main__":
    raise SystemExit(main())
