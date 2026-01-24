#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pattern library audit: duplicates, low-value, and usage stats."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
import json
import re

try:
    from abu.unified_pattern_library import UnifiedPatternLibrary
    PATTERN_LIB_AVAILABLE = True
except Exception:
    UnifiedPatternLibrary = None
    PATTERN_LIB_AVAILABLE = False

try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except Exception:
    TraderDBManager = None
    DB_AVAILABLE = False


@dataclass
class PatternUsage:
    count: int
    last_seen: Optional[str]


def _normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    txt = str(value).strip().lower()
    txt = re.sub(r"\s+", "_", txt)
    txt = re.sub(r"[^\w]+", "_", txt)
    txt = re.sub(r"_+", "_", txt).strip("_")
    return txt


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
    return None


def _extract_matches(notes: Optional[str]) -> Iterable[str]:
    if not notes:
        return []
    items = []
    for part in str(notes).split():
        if part.startswith("Match:"):
            name = part.split("Match:", 1)[1].strip()
            if name:
                items.append(name)
    return items


def _load_usage_stats(trader_id: str, since_days: int) -> Dict[str, PatternUsage]:
    if not DB_AVAILABLE:
        return {}
    since = None
    if since_days > 0:
        since = datetime.now() - timedelta(days=since_days)

    db = TraderDBManager(trader_id)
    conn = db._get_connection(read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT signal_time, created_at, entry_model, notes
            FROM trading_signals
            WHERE system_name = ?
            """,
            (trader_id,),
        ).fetchall()
    finally:
        conn.close()

    stats: Dict[str, PatternUsage] = {}
    for row in rows:
        signal_time, created_at, entry_model, notes = row
        ts = _parse_dt(signal_time) or _parse_dt(created_at)
        if since and ts and ts < since:
            continue

        for name in _extract_matches(notes):
            key = _normalize_text(name)
            if not key:
                continue
            current = stats.get(key)
            last_seen = ts.isoformat() if ts else None
            if current:
                stats[key] = PatternUsage(current.count + 1, last_seen or current.last_seen)
            else:
                stats[key] = PatternUsage(1, last_seen)

        if entry_model:
            key = _normalize_text(str(entry_model))
            if key:
                current = stats.get(key)
                last_seen = ts.isoformat() if ts else None
                if current:
                    stats[key] = PatternUsage(current.count + 1, last_seen or current.last_seen)
                else:
                    stats[key] = PatternUsage(1, last_seen)
    return stats


def _pattern_key(pattern_name: str, pattern_type: str, direction: str) -> str:
    name = _normalize_text(pattern_name) or _normalize_text(pattern_type) or "unknown"
    ptype = _normalize_text(pattern_type) or "unknown"
    direct = _normalize_text(direction) or "neutral"
    return f"{name}|{ptype}|{direct}"


def _build_low_value_reasons(pattern: object, min_confidence: float) -> List[str]:
    reasons: List[str] = []
    try:
        confidence = float(getattr(pattern, "confidence", 0.0) or 0.0)
    except Exception:
        confidence = 0.0
    if confidence < min_confidence:
        reasons.append("低置信度")

    ptype = str(getattr(pattern, "pattern_type", "") or "").lower()
    if ptype in ("unknown", "informational", "other", "analysis_chart"):
        reasons.append("类型不明")

    pname = str(getattr(pattern, "pattern_name", "") or "").strip()
    if not pname:
        reasons.append("名称缺失")

    features = getattr(pattern, "structured_features", {}) or {}
    if not features:
        reasons.append("特征缺失")
    else:
        key_fields = [features.get("kline_features"), features.get("market_conditions"), features.get("pattern_structure")]
        if all(not v for v in key_fields) and ptype not in ("brooks_rule",):
            reasons.append("结构化信息不足")
    return reasons


def run_pattern_audit(
    trader_id: str = "abu",
    output_dir: Optional[Path] = None,
    since_days: int = 30,
    min_confidence: float = 0.3,
    max_duplicates: int = 20,
    max_unused: int = 50,
) -> Optional[Path]:
    if not PATTERN_LIB_AVAILABLE:
        return None

    output_root = output_dir or (Path(__file__).resolve().parent.parent.parent / "outputs" / "trading_signals")
    output_root.mkdir(parents=True, exist_ok=True)

    pattern_library = UnifiedPatternLibrary(trader_id)
    pattern_library.load_all_patterns()

    patterns = list(pattern_library.patterns.values())
    usage = _load_usage_stats(trader_id, since_days)

    dup_groups: Dict[str, List] = {}
    for pat in patterns:
        key = _pattern_key(pat.pattern_name, pat.pattern_type, pat.direction)
        dup_groups.setdefault(key, []).append(pat)

    duplicates = [(k, v) for k, v in dup_groups.items() if len(v) > 1]
    duplicates.sort(key=lambda item: len(item[1]), reverse=True)

    low_value: List[Tuple[object, List[str]]] = []
    for pat in patterns:
        reasons = _build_low_value_reasons(pat, min_confidence)
        if reasons:
            low_value.append((pat, reasons))

    unused: List[object] = []
    for pat in patterns:
        key = _normalize_text(pat.pattern_name)
        if key and key not in usage:
            unused.append(pat)

    now = datetime.now().strftime("%Y%m%d_%H%M")
    report_path = output_root / f"ABU_pattern_audit_{now}.md"
    lines: List[str] = []
    lines.append("# ABU 模式库审计报告")
    lines.append("")
    lines.append(f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 统计窗口: 最近 {since_days} 天（usage 统计）")
    lines.append(f"- 总模式数: {len(patterns)}")
    lines.append(f"- 重复组数: {len(duplicates)}")
    lines.append(f"- 低价值候选: {len(low_value)}")
    lines.append(f"- 未使用模式: {len(unused)}")
    lines.append("")
    lines.append("## 重复模式（Top）")
    if duplicates:
        for key, items in duplicates[:max_duplicates]:
            sources = ", ".join(sorted(set(p.source for p in items)))
            example = ", ".join(p.pattern_id for p in items[:5])
            lines.append(f"- {key} x{len(items)} | sources={sources} | ids={example}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 低价值候选（Top）")
    if low_value:
        for pat, reasons in low_value[:max_duplicates]:
            pname = pat.pattern_name or pat.pattern_id
            lines.append(f"- {pname} | {pat.source} | {pat.pattern_type} | {pat.direction} | {'/'.join(reasons)}")
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 未使用模式（Top）")
    if unused:
        for pat in unused[:max_unused]:
            pname = pat.pattern_name or pat.pattern_id
            lines.append(f"- {pname} | {pat.source} | {pat.pattern_type} | {pat.direction}")
    else:
        lines.append("- 无")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
