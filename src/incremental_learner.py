#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Incremental learner for De. conversations.
Parses newly inserted conversations, aggregates price levels, biases and rules,
and writes a compact learning report + viewpoint. Maintains a state file to
avoid duplicate processing.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

from db_manager_trader import TraderDBManager

STATE_FILE = Path("trading_signals")/".learning_reports"/".inc_state.json"
OUTDIR = Path("trading_signals")/".learning_reports"
OUTDIR.mkdir(parents=True, exist_ok=True)


def _normalize_price_token(num: int) -> int | None:
    if 10000 <= num <= 99999:
        val = num
    elif 1000 <= num <= 9999:
        val = num * 10
    elif 100 <= num <= 999:
        val = num * 100
    else:
        return None
    # BTC rough guard
    if 60000 <= val <= 120000:
        return val
    return None


def _parse_message(msg: str) -> Dict:
    """Very light parser for Chinese trading conversation."""
    out: Dict = {"levels": [], "flags": set(), "bias": []}
    if not msg:
        return out
    # numbers
    for m in re.finditer(r"(?<!\d)(\d{3,5})(?!\d)", msg):
        val = _normalize_price_token(int(m.group(1)))
        if val is not None:
            out["levels"].append(val)
    # bias cues
    if "空头结构" in msg or "做空" in msg or "空空空" in msg:
        out["bias"].append("short")
    if "多头结构" in msg or "做多" in msg or "低多" in msg:
        out["bias"].append("long")
    # rules cues
    for k in ("垃圾时间", "OTE", "0.618", "0.786", "止损", "目标", "Vegas", "VWAP"):
        if k in msg:
            out["flags"].add(k)
    return out


def _load_state() -> Dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8") or "{}")
    except Exception:
        return {}


def _save_state(st: Dict):
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def learn_incremental(trader_id: str = "de") -> Dict:
    """Process new conversations since last checkpoint; write report + viewpoint."""
    st = _load_state()
    last_id = int(st.get("last_conv_id") or 0)
    db = TraderDBManager(trader_id)
    con = db._get_connection()
    rows = con.execute(
        "SELECT id, timestamp, trader_message FROM conversations WHERE id > ? ORDER BY id",
        [last_id],
    ).fetchall()
    if not rows:
        db.close()
        return {"updated": False, "count": 0, "last_id": last_id}

    levels: List[int] = []
    flags: Dict[str, int] = {}
    bias_ct = {"long": 0, "short": 0}
    first_ts = rows[0][1]
    last_ts = rows[-1][1]

    for cid, ts, msg in rows:
        p = _parse_message(msg or "")
        for v in p["levels"]:
            levels.append(v)
        for f in p["flags"]:
            flags[f] = flags.get(f, 0) + 1
        for b in p["bias"]:
            if b in bias_ct:
                bias_ct[b] += 1
        last_id = cid

    # dedup while preserving order
    dedup_levels: List[int] = []
    seen = set()
    for v in levels:
        if v not in seen:
            seen.add(v)
            dedup_levels.append(v)

    # summary lines
    lines: List[str] = []
    lines.append("# 增量学习（De. 对话）")
    lines.append("")
    lines.append(f"时间段: {first_ts} → {last_ts}")
    lines.append(f"样本数: {len(rows)}")
    lines.append("")
    if dedup_levels:
        show = ", ".join(f"${x:,}" for x in dedup_levels[:12])
        lines.append(f"观点价位: {show}")
    if flags:
        topf = ", ".join(f"{k}×{flags[k]}" for k in sorted(flags, key=lambda x: -flags[x])[:8])
        lines.append(f"要素: {topf}")
    lines.append(f"偏向: long={bias_ct['long']} / short={bias_ct['short']}")
    lines.append("")

    # store
    out = OUTDIR / f"learn_incremental_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    out.write_text("\n".join(lines), encoding="utf-8")

    # viewpoint
    try:
        brief_lv = ", ".join(f"${x:,}" for x in dedup_levels[:6])
        db.add_viewpoint(
            content=f"对话增量学习 | levels: {brief_lv} | bias L/S: {bias_ct['long']}/{bias_ct['short']}",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source="learn",
            category="learning",
            tags=["learn","conv","de"],
        )
    except Exception:
        pass

    db.close()
    _save_state({"last_conv_id": last_id, "last_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    return {"updated": True, "count": len(rows), "last_id": last_id}


if __name__ == "__main__":
    res = learn_incremental("de")
    print("OK", json.dumps(res, ensure_ascii=False))

