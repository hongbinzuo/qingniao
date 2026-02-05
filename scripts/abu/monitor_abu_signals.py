#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU 信号监控器（TP1/TP2/SL 自动审计）

用法:
  python scripts/abu/monitor_abu_signals.py --once
  python scripts/abu/monitor_abu_signals.py --interval 60 --log-file logs/abu_signal_monitor.log
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager  # type: ignore


TF_MAP = {
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
}
TF_MONITOR_MAP = {
    "15m": "5m",
    "1h": "15m",
    "4h": "1h",
}


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


def _safe_json(value: object) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    text = str(value).strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _extract_entry_type(signal: Dict[str, Any]) -> str:
    notes = _safe_json(signal.get("notes"))
    entry_type = notes.get("entry_type") or ""
    if isinstance(entry_type, str) and entry_type:
        return entry_type.lower()
    entry = notes.get("entry") if isinstance(notes.get("entry"), dict) else {}
    entry_type = entry.get("type") if isinstance(entry, dict) else ""
    if isinstance(entry_type, str) and entry_type:
        return entry_type.lower()
    return "market"


def _pair_symbol(symbol: str) -> str:
    sym = str(symbol or "").upper().strip()
    if sym.endswith("_USDT"):
        return sym
    if sym.endswith("USDT"):
        return sym.replace("USDT", "_USDT")
    return f"{sym}_USDT"


def _monitor_timeframe(timeframe: str) -> str:
    tf = str(timeframe or "").lower().strip()
    if not tf:
        return "15m"
    return TF_MONITOR_MAP.get(tf, tf)


def _calc_pnl(direction: str, entry: float, exit_price: float) -> float:
    if entry <= 0:
        return 0.0
    if direction == "long":
        return (exit_price - entry) / entry * 100.0
    return (entry - exit_price) / entry * 100.0


def _fetch_gate_klines(
    symbol_pair: str,
    timeframe: str,
    start_ts: int,
    end_ts: Optional[int],
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    interval = TF_MAP.get(timeframe, timeframe)
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    params: Dict[str, Any] = {
        "currency_pair": symbol_pair,
        "interval": interval,
        "from": int(start_ts),
    }
    if end_ts:
        params["to"] = int(end_ts)
    if limit:
        params["limit"] = int(limit)
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        data = resp.json() or []
        klines: List[Dict[str, Any]] = []
        for k in data:
            try:
                klines.append(
                    {
                        "timestamp": int(k[0]),
                        "volume": float(k[1]),
                        "close": float(k[2]),
                        "high": float(k[3]),
                        "low": float(k[4]),
                        "open": float(k[5]),
                    }
                )
            except Exception:
                continue
        klines.sort(key=lambda x: x.get("timestamp", 0))
        return klines
    except Exception:
        return []


def _evaluate_klines(
    signal: Dict[str, Any],
    klines: List[Dict[str, Any]],
    entry_type: str,
    skip_tp1: bool = False,
) -> Dict[str, Any]:
    direction = str(signal.get("signal_type") or "").lower()
    entry_plan = float(signal.get("entry_price") or 0.0)
    entry_actual = float(signal.get("entry_price_actual") or entry_plan or 0.0)
    stop = float(signal.get("stop_loss") or 0.0)
    tp1 = float(signal.get("take_profit_1") or 0.0)
    tp2 = float(signal.get("take_profit_2") or 0.0)

    if direction not in ("long", "short") or entry_plan <= 0 or stop <= 0:
        return {"status": "invalid"}

    entry_time = _parse_dt(signal.get("entry_time"))
    status = str(signal.get("status") or "").lower()
    entry_filled = bool(entry_time) or status in ("active", "partial_tp", "completed", "stopped")

    for k in klines:
        high = float(k.get("high") or 0.0)
        low = float(k.get("low") or 0.0)
        ts = int(k.get("timestamp") or 0)
        hit_time = datetime.fromtimestamp(ts) if ts else None

        if entry_time and ts and hit_time and entry_time and hit_time < entry_time:
            continue

        if not entry_filled:
            if entry_type == "limit":
                if direction == "long" and low <= entry_plan:
                    entry_filled = True
                elif direction == "short" and high >= entry_plan:
                    entry_filled = True
            elif entry_type == "stop":
                if direction == "long" and high >= entry_plan:
                    entry_filled = True
                elif direction == "short" and low <= entry_plan:
                    entry_filled = True
            else:
                entry_filled = True

            if entry_filled:
                entry_time = hit_time
                entry_actual = entry_plan
            else:
                continue

        if direction == "long":
            if low <= stop:
                return {
                    "status": "stopped",
                    "exit_price": stop,
                    "hit_time": hit_time,
                    "pnl": _calc_pnl(direction, entry_actual, stop),
                    "entry_time": entry_time,
                    "entry_price_actual": entry_actual,
                }
            if tp2 > 0 and high >= tp2:
                return {
                    "status": "tp2",
                    "exit_price": tp2,
                    "hit_time": hit_time,
                    "pnl": _calc_pnl(direction, entry_actual, tp2),
                    "entry_time": entry_time,
                    "entry_price_actual": entry_actual,
                }
            if not skip_tp1 and tp1 > 0 and high >= tp1:
                return {
                    "status": "tp1",
                    "exit_price": tp1,
                    "hit_time": hit_time,
                    "pnl": _calc_pnl(direction, entry_actual, tp1),
                    "entry_time": entry_time,
                    "entry_price_actual": entry_actual,
                }
        else:
            if high >= stop:
                return {
                    "status": "stopped",
                    "exit_price": stop,
                    "hit_time": hit_time,
                    "pnl": _calc_pnl(direction, entry_actual, stop),
                    "entry_time": entry_time,
                    "entry_price_actual": entry_actual,
                }
            if tp2 > 0 and low <= tp2:
                return {
                    "status": "tp2",
                    "exit_price": tp2,
                    "hit_time": hit_time,
                    "pnl": _calc_pnl(direction, entry_actual, tp2),
                    "entry_time": entry_time,
                    "entry_price_actual": entry_actual,
                }
            if not skip_tp1 and tp1 > 0 and low <= tp1:
                return {
                    "status": "tp1",
                    "exit_price": tp1,
                    "hit_time": hit_time,
                    "pnl": _calc_pnl(direction, entry_actual, tp1),
                    "entry_time": entry_time,
                    "entry_price_actual": entry_actual,
                }

    if not entry_filled:
        return {"status": "pending_entry"}

    return {
        "status": "active",
        "entry_time": entry_time,
        "entry_price_actual": entry_actual,
    }


def _log_event(log_path: Path, payload: Dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def _audit_once(
    db: TraderDBManager,
    hours: int,
    system_name: str,
    max_signals: int,
    log_path: Path,
    min_interval_sec: int,
) -> Dict[str, int]:
    signals = db.get_active_signals(hours=hours)
    filtered = [s for s in signals if (not system_name or s.get("system_name") == system_name)]
    if max_signals > 0:
        filtered = filtered[:max_signals]

    now = datetime.now()
    counters = {"checked": 0, "tp1": 0, "tp2": 0, "stopped": 0, "skipped": 0}

    for s in filtered:
        status = str(s.get("status") or "").lower()
        if status in {"completed", "stopped"}:
            counters["skipped"] += 1
            continue

        last_check = _parse_dt(s.get("last_check_time"))
        signal_time = _parse_dt(s.get("signal_time")) or _parse_dt(s.get("created_at"))
        start_dt = last_check or signal_time or (now - timedelta(minutes=5))
        if last_check and (now - last_check).total_seconds() < min_interval_sec:
            counters["skipped"] += 1
            continue
        start_ts = int(start_dt.timestamp())
        end_ts = int(now.timestamp())
        if end_ts <= start_ts:
            counters["skipped"] += 1
            continue

        symbol_pair = _pair_symbol(s.get("symbol") or "")
        tf_signal = str(s.get("timeframe") or "15m").lower()
        tf_monitor = _monitor_timeframe(tf_signal)
        klines = _fetch_gate_klines(symbol_pair, tf_monitor, start_ts, end_ts)
        entry_type = _extract_entry_type(s)
        outcome = _evaluate_klines(
            s,
            klines,
            entry_type=entry_type,
            skip_tp1=(status == "partial_tp"),
        )

        counters["checked"] += 1
        outcome_status = outcome.get("status")
        hit_time = outcome.get("hit_time") or now
        exit_price = outcome.get("exit_price")
        pnl = outcome.get("pnl")

        update_kwargs = {
            "last_check_time": now,
            "check_count": int(s.get("check_count") or 0) + 1,
        }

        if outcome_status in ("tp1", "tp2", "stopped"):
            if outcome_status == "tp1":
                new_status = "partial_tp"
                exit_reason = "tp1"
                counters["tp1"] += 1
                update_kwargs["quick_tp_reached"] = True
            elif outcome_status == "tp2":
                new_status = "completed"
                exit_reason = "tp2"
                counters["tp2"] += 1
            else:
                new_status = "stopped"
                exit_reason = "stop_loss"
                counters["stopped"] += 1

            db.update_signal_status(
                s["id"],
                new_status,
                exit_time=hit_time,
                exit_price=exit_price,
                exit_reason=exit_reason,
                pnl_pct=pnl,
                entry_time=outcome.get("entry_time"),
                entry_price_actual=outcome.get("entry_price_actual"),
                **update_kwargs,
            )

            eval_payload = {
                "signal_id": s["id"],
                "evaluation_time": hit_time,
                "result": outcome_status,
                "actual_exit_price": exit_price,
                "actual_profit_pct": pnl,
                "stop_loss_hit": outcome_status == "stopped",
                "take_profit_1_hit": outcome_status == "tp1",
                "take_profit_2_hit": outcome_status == "tp2",
                "missed": False,
                "notes": f"auto-monitor {symbol_pair} {tf}",
            }
            try:
                db.add_signal_evaluation(eval_payload)
            except Exception:
                pass

            _log_event(
                log_path,
                {
                    "ts": now.isoformat(),
                    "event": outcome_status,
                    "signal_id": s["id"],
                    "symbol": s.get("symbol"),
                    "timeframe": s.get("timeframe"),
                    "monitor_timeframe": tf_monitor,
                    "exit_price": exit_price,
                    "pnl_pct": pnl,
                    "status": new_status,
                },
            )
        else:
            if outcome_status == "pending_entry":
                db.update_signal_status(s["id"], status or "pending", **update_kwargs)
            else:
                new_status = status or "pending"
                entry_time = outcome.get("entry_time")
                entry_price_actual = outcome.get("entry_price_actual")
                if status == "pending" and entry_time:
                    new_status = "active"
                    _log_event(
                        log_path,
                        {
                            "ts": now.isoformat(),
                            "event": "entry",
                            "signal_id": s["id"],
                            "symbol": s.get("symbol"),
                            "timeframe": s.get("timeframe"),
                            "monitor_timeframe": tf_monitor,
                            "entry_price": entry_price_actual,
                        },
                    )
                db.update_signal_status(
                    s["id"],
                    new_status,
                    entry_time=entry_time,
                    entry_price_actual=entry_price_actual,
                    **update_kwargs,
                )

    return counters


def main() -> int:
    parser = argparse.ArgumentParser(description="ABU 信号 TP/SL 自动监控")
    parser.add_argument("--interval", type=int, default=60, help="监控间隔(秒)")
    parser.add_argument("--hours", type=int, default=24, help="只监控最近N小时内的信号")
    parser.add_argument("--max-signals", type=int, default=200, help="单次最多处理数量")
    parser.add_argument("--system", type=str, default="abu", help="系统名称过滤")
    parser.add_argument("--min-interval", type=int, default=20, help="同一信号最短重复检查间隔(秒)")
    parser.add_argument("--log-file", type=str, default="", help="日志输出文件路径")
    parser.add_argument("--once", action="store_true", help="只运行一次")
    args = parser.parse_args()

    log_path = Path(args.log_file) if args.log_file else ROOT / "logs" / "abu_signal_monitor.log"
    db = TraderDBManager("abu")

    while True:
        stats = _audit_once(
            db=db,
            hours=max(args.hours, 1),
            system_name=args.system.strip(),
            max_signals=max(args.max_signals, 1),
            log_path=log_path,
            min_interval_sec=max(args.min_interval, 1),
        )
        _log_event(
            log_path,
            {
                "ts": datetime.now().isoformat(),
                "event": "cycle",
                "checked": stats.get("checked"),
                "tp1": stats.get("tp1"),
                "tp2": stats.get("tp2"),
                "stopped": stats.get("stopped"),
                "skipped": stats.get("skipped"),
            },
        )
        if args.once:
            break
        time.sleep(max(args.interval, 5))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
