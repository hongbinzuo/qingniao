#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Real-time ABU monitor: refresh top signals and attach latest prices.

Runs pa_scan_15m_top10.py for 5m/15m, then enriches with Gate tickers.
Outputs:
  - outputs/trading_signals/ABU_realtime_log.md (append)
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs" / "trading_signals"
LOG_DIR = ROOT / "logs"

GATE_TICKERS_URL = "https://api.gateio.ws/api/v4/spot/tickers"
DEFAULT_LOG_MAX_MB = 10
DEFAULT_MD_MAX_MB = 20


def _rotate_file(path: Path, max_mb: int, base_dir: Path) -> None:
    if not path.exists():
        return
    max_bytes = max_mb * 1024 * 1024
    if path.stat().st_size <= max_bytes:
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = base_dir / "deleting" / stamp
    archive_dir.mkdir(parents=True, exist_ok=True)
    path.rename(archive_dir / path.name)


def setup_logger(log_file: Path, max_mb: int) -> logging.Logger:
    logger = logging.getLogger("abu_realtime_monitor")
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _rotate_file(log_file, max_mb, LOG_DIR)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def fetch_gate_tickers() -> Dict[str, float]:
    try:
        resp = requests.get(GATE_TICKERS_URL, timeout=20)
        if resp.status_code != 200:
            return {}
        data = resp.json()
    except Exception:
        return {}

    prices: Dict[str, float] = {}
    for item in data:
        pair = item.get("currency_pair")
        if not pair or not pair.endswith("_USDT"):
            continue
        symbol = pair.replace("_USDT", "").upper()
        try:
            prices[symbol] = float(item.get("last"))
        except (TypeError, ValueError):
            continue
    return prices


def run_scan(
    timeframe: str,
    top: int,
    write_db: int,
    rank_by: str,
    exchange_mode: str,
    audit_period_hours: int,
    audit_since_days: int,
    audit_min_confidence: float,
    audit_max_duplicates: int,
    audit_max_unused: int,
    logger: logging.Logger,
) -> Optional[float]:
    start_ts = time.time()
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "pa_scan_15m_top10.py"),
        "--top",
        str(top),
        "--timeframe",
        timeframe,
        "--rank-by",
        rank_by,
        "--write-db",
        str(write_db),
        "--exchange-mode",
        exchange_mode,
    ]
    if audit_period_hours and audit_period_hours > 0:
        cmd.extend(
            [
                "--audit-period-hours",
                str(audit_period_hours),
                "--audit-since-days",
                str(audit_since_days),
                "--audit-min-confidence",
                str(audit_min_confidence),
                "--audit-max-duplicates",
                str(audit_max_duplicates),
                "--audit-max-unused",
                str(audit_max_unused),
            ]
        )
    logger.info("Scan start: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        logger.error("Scan failed (timeframe=%s), code=%s", timeframe, result.returncode)
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if stdout:
            logger.error("Scan stdout:\n%s", stdout[-4000:])
        if stderr:
            logger.error("Scan stderr:\n%s", stderr[-4000:])
        return None
    return start_ts


def latest_scan_file(timeframe: str, top: int, min_mtime: Optional[float] = None) -> Optional[Path]:
    pattern = f"ABU_top{top}_{timeframe}_*.md"
    files = sorted(OUTPUT_DIR.glob(pattern), key=lambda p: p.stat().st_mtime)
    if min_mtime is not None:
        files = [f for f in files if f.stat().st_mtime >= min_mtime]
    if not files:
        return None
    return files[-1]


def _parse_pct(value: str) -> Optional[float]:
    if value is None:
        return None
    txt = str(value).strip().replace("%", "")
    if txt == "":
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def parse_scan_file(path: Path) -> List[Dict]:
    rows = []
    if not path or not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        if line.startswith("| #"):
            continue
        if line.startswith("|---"):
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) < 12:
            continue
        try:
            if len(parts) >= 15:
                rows.append(
                    {
                        "rank": int(parts[0]),
                        "symbol": parts[1],
                        "type": parts[2],
                        "entry": float(parts[3]),
                        "stop_loss": float(parts[4]),
                        "tp1": float(parts[5]),
                        "tp2": float(parts[6]),
                        "p_tp1": _parse_pct(parts[7]),
                        "p_tp2": _parse_pct(parts[8]),
                        "p_sl": _parse_pct(parts[9]),
                        "score": float(parts[10]),
                        "pattern_score": float(parts[11]),
                        "brooks": parts[12],
                        "match": parts[13],
                        "reason": parts[-1],
                    }
                )
            else:
                rows.append(
                    {
                        "rank": int(parts[0]),
                        "symbol": parts[1],
                        "type": parts[2],
                        "entry": float(parts[3]),
                        "stop_loss": float(parts[4]),
                        "tp1": float(parts[5]),
                        "tp2": float(parts[6]),
                        "score": float(parts[7]),
                        "pattern_score": float(parts[8]),
                        "brooks": parts[9],
                        "match": parts[10],
                        "reason": parts[11],
                    }
                )
        except Exception:
            continue
    return rows


def enrich_with_prices(rows: List[Dict], prices: Dict[str, float]) -> None:
    direction_map = {"long": "多", "short": "空", "neutral": "中性"}
    for row in rows:
        symbol = row.get("symbol")
        price = prices.get(symbol)
        row["current_price"] = price
        entry = row.get("entry")
        triggered = None
        distance_pct = None
        if price is not None and entry:
            if row.get("type", "").lower() == "long":
                triggered = price >= entry
                distance_pct = (price - entry) / entry * 100
            elif row.get("type", "").lower() == "short":
                triggered = price <= entry
                distance_pct = (entry - price) / entry * 100
        row["triggered"] = triggered
        row["distance_pct"] = distance_pct
        direction = (row.get("type") or "").lower()
        row["direction_zh"] = direction_map.get(direction, row.get("type") or "-")


def write_outputs(payload: Dict, top: int, md_max_mb: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    append_path = OUTPUT_DIR / "ABU_realtime_log.md"
    _rotate_file(append_path, md_max_mb, OUTPUT_DIR)

    lines = []
    lines.append(f"## 生成时间: {payload['generated_at']} | Top: {top} | Rank: {payload.get('rank_by')}")
    lines.append("")

    for timeframe, rows in payload["timeframes"].items():
        lines.append(f"### {timeframe}")
        lines.append("| 序号 | 币种 | 方向 | 入场价 | 止损 | 目标1 | 目标2 | TP1概率 | TP2概率 | 止损概率 | 当前价 | 是否触发 | 距离% |")
        lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|")
        for row in rows:
            price = row.get("current_price")
            triggered = row.get("triggered")
            dist = row.get("distance_pct")
            typ = row.get("direction_zh") or row.get("type")
            p_tp1 = row.get("p_tp1")
            p_tp2 = row.get("p_tp2")
            p_sl = row.get("p_sl")
            price_fmt = f"{price:.4f}" if isinstance(price, (int, float)) else "-"
            triggered_fmt = "是" if triggered is True else "否" if triggered is False else "-"
            dist_fmt = f"{dist:.2f}" if isinstance(dist, (int, float)) else "-"
            p1_fmt = f"{p_tp1:.1f}%" if isinstance(p_tp1, (int, float)) else "-"
            p2_fmt = f"{p_tp2:.1f}%" if isinstance(p_tp2, (int, float)) else "-"
            psl_fmt = f"{p_sl:.1f}%" if isinstance(p_sl, (int, float)) else "-"
            lines.append(
                "| {rank} | {symbol} | {typ} | {entry:.4f} | {sl:.4f} | {tp1:.4f} | {tp2:.4f} | {p1} | {p2} | {psl} | {price} | {triggered} | {dist} |".format(
                    rank=row.get("rank"),
                    symbol=row.get("symbol"),
                    typ=typ,
                    entry=row.get("entry"),
                    sl=row.get("stop_loss"),
                    tp1=row.get("tp1"),
                    tp2=row.get("tp2"),
                    p1=p1_fmt,
                    p2=p2_fmt,
                    psl=psl_fmt,
                    price=price_fmt,
                    triggered=triggered_fmt,
                    dist=dist_fmt,
                )
            )
        lines.append("")

    if not append_path.exists():
        append_path.write_text("# ABU 实时监控日志\n\n", encoding="utf-8")
    with append_path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))
        f.write("\n")


def run_once(
    timeframes: List[str],
    top: int,
    write_db: int,
    rank_by: str,
    exchange_mode: str,
    audit_period_hours: int,
    audit_since_days: int,
    audit_min_confidence: float,
    audit_max_duplicates: int,
    audit_max_unused: int,
    md_max_mb: int,
    logger: logging.Logger,
) -> None:
    scan_times: Dict[str, float] = {}
    for tf in timeframes:
        start_ts = run_scan(
            tf,
            top,
            write_db,
            rank_by,
            exchange_mode,
            audit_period_hours,
            audit_since_days,
            audit_min_confidence,
            audit_max_duplicates,
            audit_max_unused,
            logger,
        )
        if start_ts is not None:
            scan_times[tf] = start_ts
            scan_file = latest_scan_file(tf, top, start_ts)
            if not scan_file:
                logger.warning("Scan finished but no output file found (timeframe=%s)", tf)

    prices = fetch_gate_tickers()
    payload = {
        "lang": "zh",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rank_by": rank_by,
        "timeframes": {},
    }
    for tf in timeframes:
        scan_file = latest_scan_file(tf, top, scan_times.get(tf))
        if not scan_file:
            scan_file = latest_scan_file(tf, top, None)
            if scan_file:
                logger.warning("Fallback to previous scan file (timeframe=%s, file=%s)", tf, scan_file.name)
        rows = parse_scan_file(scan_file) if scan_file else []
        enrich_with_prices(rows, prices)
        payload["timeframes"][tf] = rows

    write_outputs(payload, top, md_max_mb)


def main() -> int:
    parser = argparse.ArgumentParser(description="ABU realtime monitor (Gate tickers)")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--timeframes", type=str, default="3m,5m,15m,1h")
    parser.add_argument("--interval", type=int, default=60, help="seconds")
    parser.add_argument("--write-db", type=int, default=1)
    parser.add_argument("--rank-by", type=str, default="marketcap", choices=["volume", "marketcap"])
    parser.add_argument("--exchange-mode", type=str, default="gate", choices=["gate", "bybit", "bitget", "split"])
    parser.add_argument("--audit-period-hours", type=int, default=0)
    parser.add_argument("--audit-since-days", type=int, default=30)
    parser.add_argument("--audit-min-confidence", type=float, default=0.3)
    parser.add_argument("--audit-max-duplicates", type=int, default=20)
    parser.add_argument("--audit-max-unused", type=int, default=50)
    parser.add_argument("--log-max-mb", type=int, default=DEFAULT_LOG_MAX_MB)
    parser.add_argument("--md-max-mb", type=int, default=DEFAULT_MD_MAX_MB)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    timeframes = [t.strip() for t in args.timeframes.split(",") if t.strip()]
    log_file = LOG_DIR / "abu_realtime_monitor.log"
    logger = setup_logger(log_file, args.log_max_mb)

    logger.info(
        "Realtime monitor start: timeframes=%s top=%s interval=%s rank_by=%s exchange_mode=%s",
        timeframes,
        args.top,
        args.interval,
        args.rank_by,
        args.exchange_mode,
    )
    if args.once:
        run_once(
            timeframes,
            args.top,
            args.write_db,
            args.rank_by,
            args.exchange_mode,
            args.audit_period_hours,
            args.audit_since_days,
            args.audit_min_confidence,
            args.audit_max_duplicates,
            args.audit_max_unused,
            args.md_max_mb,
            logger,
        )
        return 0

    while True:
        start = time.time()
        run_once(
            timeframes,
            args.top,
            args.write_db,
            args.rank_by,
            args.exchange_mode,
            args.audit_period_hours,
            args.audit_since_days,
            args.audit_min_confidence,
            args.audit_max_duplicates,
            args.audit_max_unused,
            args.md_max_mb,
            logger,
        )
        elapsed = time.time() - start
        sleep_for = max(1, args.interval - int(elapsed))
        time.sleep(sleep_for)


if __name__ == "__main__":
    raise SystemExit(main())
