#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Normalize vision-analysis JSON outputs to a controlled schema and vocabulary
with raw fallback for out-of-vocabulary terms.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "outputs" / "abu_deep_analysis" / "json"
DEFAULT_OUTPUT = ROOT / "outputs" / "abu_deep_analysis" / "clean_json"

NULL_LITERALS = {"unknown", "n/a", "na", "null", "none", ""}

ALLOWED_SLIDE_TYPE = {"chart", "separator", "text", "unknown"}
ALLOWED_TIMEFRAME = {"1m", "5m", "15m", "30m", "1h", "4h", "1D", "1W", "1M"}
ALLOWED_MARKET = {"ES", "NQ", "YM", "BTC", "ETH", "FX", "unknown"}
ALLOWED_MARKET_CYCLE = {"trend", "trading_range", "spike_channel", "tight_channel", "climactic"}
ALLOWED_TREND_MATURITY = {"early", "middle", "late", "climactic"}
ALLOWED_DIRECTION = {"long", "short", "neutral"}
ALLOWED_EMA_RELATION = {"above", "below", "crossing"}
ALLOWED_EMA_SLOPE = {"up", "down", "flat"}
ALLOWED_BODY_GAP = {"yes", "no"}
ALLOWED_OVERLAP = {"low", "medium", "high"}
ALLOWED_FOLLOW_THROUGH = {"strong", "weak", "mixed"}
ALLOWED_SETUP = {"setup", "signal", "entry"}

ALLOWED_PATTERN_FAMILY = {
    "triangle",
    "wedge",
    "gap",
    "breakout",
    "reversal",
    "trend",
    "range",
    "double_top_bottom",
}
ALLOWED_PATTERN_TYPE = {"triangle", "wedge", "gap", "breakout", "trend", "range", "reversal"}
ALLOWED_PATTERN_NAME = {
    "Nested Expanding Triangle",
    "Expanding Triangle",
    "Wedge Top",
    "Truncated Wedge Bottom",
    "Bull Measuring Gap",
    "Exhaustion Gap",
    "Small Pullback Bull Trend",
    "Bull Trend",
    "Double Bottom",
    "Double Top",
}
ALLOWED_PATTERN_STATUS = {"confirmed", "suspected", "failed", "invalidated"}

ALLOWED_KLINE_FEATURE = {
    "double_bottom",
    "double_top",
    "engulfing",
    "inside_bar",
    "outside_bar",
    "gap",
    "doji",
}
ALLOWED_OCR_QUALITY = {"good", "fair", "poor"}
ALLOWED_VISIBILITY = {"full", "partial", "poor"}

DATE_WORD_RE = re.compile(
    r"\b(jan(uary)?|feb(ruary)?|mar(ch)?|apr(il)?|may|jun(e)?|jul(y)?|aug(ust)?|"
    r"sep(tember)?|oct(ober)?|nov(ember)?|dec(ember)?|monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)

DATE_NUM_RE = re.compile(r"\b\d{1,2}\b")

CHART_HINT_RE = re.compile(
    r"\b(trend|wedge|triangle|gap|double|bull|bear|breakout|channel|range|ema|measuring)\b",
    re.IGNORECASE,
)

SHORT_PHRASE_MAP = {
    "db": "double bottom",
    "dt": "double top",
    "mm": "measured move",
}

PATTERN_NAME_ALIASES = {
    "nested expanding triangle": "Nested Expanding Triangle",
    "expanding triangle": "Expanding Triangle",
    "wedge top": "Wedge Top",
    "truncated wedge bottom": "Truncated Wedge Bottom",
    "bull measuring gap": "Bull Measuring Gap",
    "exhaustion gap": "Exhaustion Gap",
    "small pullback bull trend": "Small Pullback Bull Trend",
    "bull trend": "Bull Trend",
    "double bottom": "Double Bottom",
    "double top": "Double Top",
}

PATTERN_NAME_TO_TYPE = {
    "Nested Expanding Triangle": ("triangle", "triangle"),
    "Expanding Triangle": ("triangle", "triangle"),
    "Wedge Top": ("wedge", "wedge"),
    "Truncated Wedge Bottom": ("wedge", "wedge"),
    "Bull Measuring Gap": ("gap", "gap"),
    "Exhaustion Gap": ("gap", "gap"),
    "Small Pullback Bull Trend": ("trend", "trend"),
    "Bull Trend": ("trend", "trend"),
    "Double Bottom": ("double_top_bottom", "reversal"),
    "Double Top": ("double_top_bottom", "reversal"),
}


def _normalize_null(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.lower() in NULL_LITERALS:
            return None
        return stripped
    return value


def _normalize_enum(value: Any, allowed: Iterable[str]) -> Optional[str]:
    value = _normalize_null(value)
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    for item in allowed:
        if value == item:
            return item
        if value.lower() == item.lower():
            return item
    return None


def _normalize_direction(value: Any) -> Optional[str]:
    value = _normalize_null(value)
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered in {"bull", "bullish", "long", "buy"}:
        return "long"
    if lowered in {"bear", "bearish", "short", "sell"}:
        return "short"
    if lowered in {"neutral", "sideways"}:
        return "neutral"
    return _normalize_enum(value, ALLOWED_DIRECTION)


def _normalize_timeframe(value: Any) -> Optional[str]:
    value = _normalize_null(value)
    if value is None:
        return None
    if isinstance(value, str):
        raw = value.strip()
        lowered = raw.lower()
        if lowered in {"1m", "5m", "15m", "30m", "1h", "4h"}:
            return lowered
        if raw in ALLOWED_TIMEFRAME:
            return raw
        if "min" in lowered:
            match = re.search(r"(\d+)", lowered)
            if match:
                candidate = f"{match.group(1)}m"
                return candidate if candidate in ALLOWED_TIMEFRAME else None
        if "hour" in lowered or lowered.endswith("h"):
            match = re.search(r"(\d+)", lowered)
            if match:
                candidate = f"{match.group(1)}h"
                return candidate if candidate in ALLOWED_TIMEFRAME else None
        if "day" in lowered:
            return "1D"
        if "week" in lowered:
            return "1W"
        if "month" in lowered or raw.endswith("M"):
            return "1M"
        if raw == "1M":
            return "1M"
    return None


def _clamp_confidence(value: Any, default: float) -> float:
    if value is None:
        return default
    try:
        score = float(value)
    except (TypeError, ValueError):
        return default
    if score != score:
        return default
    return max(0.0, min(1.0, score))


def _clean_text_list(value: Any) -> List[str]:
    items: List[str] = []
    if isinstance(value, list):
        items = [v for v in value if isinstance(v, str)]
    elif isinstance(value, str):
        items = [value]
    cleaned: List[str] = []
    seen = set()
    for item in items:
        norm = " ".join(item.strip().split())
        if not norm:
            continue
        lowered = norm.lower()
        norm = SHORT_PHRASE_MAP.get(lowered, norm)
        key = norm.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(norm)
    return cleaned


def _assign_raw(raw_out: Dict[str, Any], keys: List[str], value: Any) -> None:
    value = _normalize_null(value)
    if value is None:
        return
    cursor = raw_out
    for key in keys[:-1]:
        if key not in cursor or not isinstance(cursor[key], dict):
            cursor[key] = {}
        cursor = cursor[key]
    if keys[-1] not in cursor:
        cursor[keys[-1]] = value


def _record_raw_unknown(raw_out: Dict[str, Any], keys: List[str], raw_value: Any, normalized_value: Any) -> None:
    if normalized_value is None:
        _assign_raw(raw_out, keys, raw_value)


def _is_separator_slide(summary: Optional[str], annotations: List[str]) -> bool:
    texts = []
    if summary:
        texts.append(summary)
    texts.extend(annotations)
    if not texts:
        return False
    for text in texts:
        if CHART_HINT_RE.search(text or ""):
            return False
    date_like = [text for text in texts if DATE_WORD_RE.search(text or "")]
    if date_like:
        return True
    if all(DATE_NUM_RE.search(text or "") for text in texts if text):
        return True
    return False


def _normalize_pattern_name(value: Any) -> Optional[str]:
    value = _normalize_null(value)
    if value is None or not isinstance(value, str):
        return None
    lowered = value.lower()
    for key, canonical in PATTERN_NAME_ALIASES.items():
        if key in lowered:
            return canonical
    return None


def _infer_pattern_status(raw_name: Optional[str], invalidations: List[str]) -> Optional[str]:
    if invalidations:
        return "invalidated"
    if not raw_name:
        return None
    lowered = raw_name.lower()
    if "invalid" in lowered:
        return "invalidated"
    if "failed" in lowered:
        return "failed"
    return None


def _normalize_feature(value: Any) -> Optional[str]:
    value = _normalize_null(value)
    if value is None or not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    alias = SHORT_PHRASE_MAP.get(lowered)
    if alias:
        lowered = alias.replace(" ", "_")
    lowered = lowered.replace(" ", "_")
    if lowered in ALLOWED_KLINE_FEATURE:
        return lowered
    return None


def _coerce_number_list(value: Any) -> List[float]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        try:
            result.append(float(item))
        except (TypeError, ValueError):
            continue
    return result


def _clean_pattern_item(
    item: Dict[str, Any],
    fallback_direction: Optional[str],
    invalidations: List[str],
) -> Optional[Dict[str, Any]]:
    raw_info = copy.deepcopy(item.get("raw")) if isinstance(item.get("raw"), dict) else {}
    raw_name = _normalize_null(item.get("pattern_name"))
    pattern_name = _normalize_pattern_name(raw_name)
    _record_raw_unknown(raw_info, ["pattern_name"], raw_name, pattern_name)

    raw_type = item.get("pattern_type")
    pattern_type = _normalize_enum(raw_type, ALLOWED_PATTERN_TYPE)
    _record_raw_unknown(raw_info, ["pattern_type"], raw_type, pattern_type)

    raw_family = item.get("pattern_family")
    pattern_family = _normalize_enum(raw_family, ALLOWED_PATTERN_FAMILY)
    _record_raw_unknown(raw_info, ["pattern_family"], raw_family, pattern_family)

    if pattern_name and pattern_name in PATTERN_NAME_TO_TYPE:
        inferred_family, inferred_type = PATTERN_NAME_TO_TYPE[pattern_name]
        if not pattern_family:
            pattern_family = inferred_family
        if not pattern_type:
            pattern_type = inferred_type

    if not pattern_family and pattern_type:
        if pattern_type == "triangle":
            pattern_family = "triangle"
        elif pattern_type == "wedge":
            pattern_family = "wedge"
        elif pattern_type == "gap":
            pattern_family = "gap"
        elif pattern_type == "breakout":
            pattern_family = "breakout"
        elif pattern_type == "trend":
            pattern_family = "trend"
        elif pattern_type == "range":
            pattern_family = "range"
        elif pattern_type == "reversal":
            pattern_family = "reversal"

    raw_direction = item.get("direction_bias")
    pattern_direction = _normalize_direction(raw_direction) or fallback_direction
    if pattern_direction is None:
        _record_raw_unknown(raw_info, ["direction_bias"], raw_direction, pattern_direction)

    raw_status = item.get("status")
    pattern_status = _normalize_enum(raw_status, ALLOWED_PATTERN_STATUS)
    if pattern_status is None:
        pattern_status = _normalize_enum(_infer_pattern_status(raw_name, invalidations), ALLOWED_PATTERN_STATUS)
    if pattern_status is None:
        _record_raw_unknown(raw_info, ["status"], raw_status, pattern_status)

    pattern_conf = _clamp_confidence(item.get("confidence"), 0.6 if pattern_name or pattern_type else 0.0)
    pattern_evidence = _clean_text_list(item.get("evidence"))

    if not any([pattern_name, pattern_type, pattern_family, pattern_direction, pattern_status, pattern_evidence, raw_info]):
        return None

    pattern = {
        "pattern_family": pattern_family,
        "pattern_type": pattern_type,
        "pattern_name": pattern_name,
        "direction_bias": pattern_direction,
        "status": pattern_status,
        "confidence": pattern_conf,
        "evidence": pattern_evidence,
    }
    if raw_info:
        pattern["raw"] = raw_info
    return pattern


def _make_separator_record(
    image_id: Optional[str],
    page: Any,
    annotations: List[str],
    summary: Optional[str],
    raw_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "image_id": image_id,
        "page": page,
        "slide_type": "separator",
        "timeframe_hint": None,
        "market": None,
        "chart": None,
        "patterns": None,
        "bar_by_bar": None,
        "counting": None,
        "kline_features": None,
        "key_levels": None,
        "targets_probabilities": None,
        "confirmations": None,
        "invalidations": None,
        "annotations_text": annotations,
        "summary": summary,
        "quality": None,
        "raw": raw_info or None,
    }


def clean_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    image_id = _normalize_null(raw.get("image_id"))
    if image_id is None and isinstance(raw.get("image"), str):
        image_id = raw.get("image")
    page = _normalize_null(raw.get("page"))
    summary = _normalize_null(raw.get("summary"))
    annotations = _clean_text_list(raw.get("annotations_text"))
    raw_out = copy.deepcopy(raw.get("raw")) if isinstance(raw.get("raw"), dict) else {}

    slide_type_raw = raw.get("slide_type")
    slide_type = _normalize_enum(slide_type_raw, ALLOWED_SLIDE_TYPE)
    if slide_type == "unknown":
        slide_type = None
    if slide_type is None and _is_separator_slide(summary, annotations):
        slide_type = "separator"
    _record_raw_unknown(raw_out, ["slide_type"], slide_type_raw, slide_type)

    if slide_type == "separator":
        return _make_separator_record(image_id, page, annotations, summary, raw_out)

    timeframe_raw = raw.get("timeframe_hint")
    timeframe = _normalize_timeframe(timeframe_raw)
    _record_raw_unknown(raw_out, ["timeframe_hint"], timeframe_raw, timeframe)
    market_raw = raw.get("market")
    market = _normalize_enum(market_raw, ALLOWED_MARKET)
    if market == "unknown":
        market = None
    _record_raw_unknown(raw_out, ["market"], market_raw, market)

    context = raw.get("context") if isinstance(raw.get("context"), dict) else {}
    market_cycle_raw = context.get("market_cycle")
    market_cycle = _normalize_enum(market_cycle_raw, ALLOWED_MARKET_CYCLE)
    _record_raw_unknown(raw_out, ["chart", "market_cycle"], market_cycle_raw, market_cycle)
    trend_maturity_raw = context.get("trend_maturity")
    trend_maturity = _normalize_enum(trend_maturity_raw, ALLOWED_TREND_MATURITY)
    _record_raw_unknown(raw_out, ["chart", "trend_maturity"], trend_maturity_raw, trend_maturity)

    direction_raw = raw.get("direction_bias")
    direction_bias = _normalize_direction(direction_raw)
    _record_raw_unknown(raw_out, ["chart", "direction_bias"], direction_raw, direction_bias)
    ema_raw = raw.get("ema_20") if isinstance(raw.get("ema_20"), dict) else {}
    ema_exists = ema_raw.get("exists")
    if isinstance(ema_exists, str):
        ema_exists = True if ema_exists.strip().lower() == "true" else False if ema_exists.strip().lower() == "false" else None
    if not isinstance(ema_exists, bool):
        ema_exists = None
    ema_relation_raw = ema_raw.get("relation")
    ema_relation = _normalize_enum(ema_relation_raw, ALLOWED_EMA_RELATION)
    _record_raw_unknown(raw_out, ["ema_20", "relation"], ema_relation_raw, ema_relation)
    ema_slope_raw = ema_raw.get("slope")
    ema_slope = _normalize_enum(ema_slope_raw, ALLOWED_EMA_SLOPE)
    _record_raw_unknown(raw_out, ["ema_20", "slope"], ema_slope_raw, ema_slope)
    ema_conf = _clamp_confidence(ema_raw.get("confidence"), 0.6 if ema_exists is not None else 0.0)

    bar_raw = raw.get("bar_by_bar") if isinstance(raw.get("bar_by_bar"), dict) else {}
    bar_body_gap_raw = bar_raw.get("body_gap")
    bar_body_gap = _normalize_enum(bar_body_gap_raw, ALLOWED_BODY_GAP)
    _record_raw_unknown(raw_out, ["bar_by_bar", "body_gap"], bar_body_gap_raw, bar_body_gap)
    bar_overlap_raw = bar_raw.get("overlap_level")
    bar_overlap = _normalize_enum(bar_overlap_raw, ALLOWED_OVERLAP)
    _record_raw_unknown(raw_out, ["bar_by_bar", "overlap_level"], bar_overlap_raw, bar_overlap)
    bar_follow_raw = bar_raw.get("follow_through")
    bar_follow = _normalize_enum(bar_follow_raw, ALLOWED_FOLLOW_THROUGH)
    _record_raw_unknown(raw_out, ["bar_by_bar", "follow_through"], bar_follow_raw, bar_follow)
    bar_setup_raw = bar_raw.get("setup_signal_entry")
    bar_setup = _normalize_enum(bar_setup_raw, ALLOWED_SETUP)
    _record_raw_unknown(raw_out, ["bar_by_bar", "setup_signal_entry"], bar_setup_raw, bar_setup)
    bar_conf = _clamp_confidence(bar_raw.get("confidence"), 0.6 if any([bar_body_gap, bar_overlap, bar_follow, bar_setup]) else 0.0)

    count_raw = raw.get("counting") if isinstance(raw.get("counting"), dict) else {}
    leg_count = count_raw.get("leg_count")
    hl_count = count_raw.get("hl_count")
    bar_number = count_raw.get("bar_number")
    for key in ("leg_count", "hl_count", "bar_number"):
        value = count_raw.get(key)
        if isinstance(value, str) and value.isdigit():
            count_raw[key] = int(value)
    leg_count = count_raw.get("leg_count") if isinstance(count_raw.get("leg_count"), (int, float)) else None
    hl_count = count_raw.get("hl_count") if isinstance(count_raw.get("hl_count"), (int, float)) else None
    bar_number = count_raw.get("bar_number") if isinstance(count_raw.get("bar_number"), (int, float)) else None
    count_conf = _clamp_confidence(count_raw.get("confidence"), 0.6 if any([leg_count, hl_count, bar_number]) else 0.0)

    kline_features_raw = raw.get("kline_features")
    kline_features: List[Dict[str, Any]] = []
    unknown_features: List[str] = []
    if isinstance(kline_features_raw, list):
        for feat in kline_features_raw:
            raw_feat = feat.get("feature") if isinstance(feat, dict) else feat
            norm_feat = _normalize_feature(raw_feat)
            if norm_feat:
                kline_features.append({"feature": norm_feat, "confidence": 0.6})
            else:
                raw_value = _normalize_null(raw_feat)
                if isinstance(raw_value, str):
                    unknown_features.append(raw_value)
    elif isinstance(kline_features_raw, str):
        norm_feat = _normalize_feature(kline_features_raw)
        if norm_feat:
            kline_features.append({"feature": norm_feat, "confidence": 0.6})
        else:
            raw_value = _normalize_null(kline_features_raw)
            if isinstance(raw_value, str):
                unknown_features.append(raw_value)

    if unknown_features:
        deduped: List[str] = []
        seen = set()
        for feat in unknown_features:
            key = feat.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(feat)
        _assign_raw(raw_out, ["kline_features"], deduped)

    key_levels_raw = raw.get("key_levels") if isinstance(raw.get("key_levels"), dict) else {}
    support = _coerce_number_list(key_levels_raw.get("support"))
    resistance = _coerce_number_list(key_levels_raw.get("resistance"))
    key_levels_conf = _clamp_confidence(key_levels_raw.get("confidence"), 0.6 if (support or resistance) else 0.0)

    targets_raw = raw.get("targets_probabilities")
    targets: List[Dict[str, Any]] = []
    if isinstance(targets_raw, list):
        for item in targets_raw:
            if not isinstance(item, dict):
                continue
            target = _normalize_null(item.get("target"))
            prob = item.get("probability")
            try:
                prob_f = float(prob)
            except (TypeError, ValueError):
                prob_f = None
            if target or prob_f is not None:
                targets.append({"target": target, "probability": prob_f})

    confirmations = _clean_text_list(raw.get("confirmations"))
    invalidations = _clean_text_list(raw.get("invalidations"))

    patterns: List[Dict[str, Any]] = []
    raw_patterns = raw.get("patterns")
    if isinstance(raw_patterns, list):
        for item in raw_patterns:
            if not isinstance(item, dict):
                continue
            pattern = _clean_pattern_item(item, direction_bias, invalidations)
            if pattern:
                patterns.append(pattern)

    if not patterns:
        seed = {
            "pattern_name": raw.get("pattern_name"),
            "pattern_type": raw.get("pattern_type"),
            "pattern_family": raw.get("pattern_family"),
            "direction_bias": raw.get("direction_bias"),
            "status": raw.get("pattern_status"),
            "confidence": raw.get("pattern_confidence"),
            "evidence": raw.get("pattern_evidence") or raw.get("annotations_text"),
            "raw": raw.get("pattern_raw") if isinstance(raw.get("pattern_raw"), dict) else None,
        }
        pattern = _clean_pattern_item(seed, direction_bias, invalidations)
        if pattern:
            patterns.append(pattern)

    if patterns:
        patterns = sorted(patterns, key=lambda item: item.get("confidence", 0.0), reverse=True)[:2]

    summary_clean = summary
    if summary_clean and len(summary_clean) > 360:
        summary_clean = summary_clean[:357] + "..."

    quality_raw = raw.get("quality") if isinstance(raw.get("quality"), dict) else {}
    ocr_quality_raw = quality_raw.get("ocr_quality")
    ocr_quality = _normalize_enum(ocr_quality_raw, ALLOWED_OCR_QUALITY)
    _record_raw_unknown(raw_out, ["quality", "ocr_quality"], ocr_quality_raw, ocr_quality)
    visibility_raw = quality_raw.get("chart_visibility")
    visibility = _normalize_enum(visibility_raw, ALLOWED_VISIBILITY)
    _record_raw_unknown(raw_out, ["quality", "chart_visibility"], visibility_raw, visibility)
    notes = _normalize_null(quality_raw.get("notes"))
    raw_info = raw_out or None

    return {
        "image_id": image_id,
        "page": page,
        "slide_type": slide_type or "chart",
        "timeframe_hint": timeframe,
        "market": market,
        "chart": {
            "market_cycle": market_cycle,
            "trend_maturity": trend_maturity,
            "direction_bias": direction_bias,
            "ema_20": {
                "exists": ema_exists,
                "relation": ema_relation,
                "slope": ema_slope,
                "confidence": ema_conf,
            },
        },
        "patterns": patterns,
        "bar_by_bar": {
            "body_gap": bar_body_gap,
            "overlap_level": bar_overlap,
            "follow_through": bar_follow,
            "setup_signal_entry": bar_setup,
            "confidence": bar_conf,
        },
        "counting": {
            "leg_count": leg_count,
            "hl_count": hl_count,
            "bar_number": bar_number,
            "confidence": count_conf,
        },
        "kline_features": kline_features,
        "key_levels": {
            "support": support,
            "resistance": resistance,
            "confidence": key_levels_conf,
        },
        "targets_probabilities": targets,
        "confirmations": confirmations,
        "invalidations": invalidations,
        "annotations_text": annotations,
        "summary": summary_clean,
        "quality": {
            "ocr_quality": ocr_quality,
            "chart_visibility": visibility,
            "notes": notes,
        },
        "raw": raw_info,
    }


def _load_json(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)


def _write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False))
            fh.write("\n")


def _clean_payload(payload: Any) -> Tuple[Any, int]:
    if isinstance(payload, list):
        cleaned = [clean_record(item) for item in payload if isinstance(item, dict)]
        return cleaned, len(cleaned)
    if isinstance(payload, dict):
        return clean_record(payload), 1
    return None, 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean vision-analysis JSON outputs.")
    parser.add_argument("--input", type=str, default=str(DEFAULT_INPUT), help="Input JSON file or directory.")
    parser.add_argument("--output", type=str, default=str(DEFAULT_OUTPUT), help="Output directory or file.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if input_path.is_dir():
        files = sorted(input_path.glob("*.json")) + sorted(input_path.glob("*.jsonl"))
        if not files:
            print(f"No JSON files found in {input_path}")
            return
        total = 0
        for file_path in files:
            if file_path.suffix == ".jsonl":
                cleaned_iter = (clean_record(obj) for obj in _iter_jsonl(file_path))
                out_file = output_path / file_path.name
                _write_jsonl(out_file, cleaned_iter)
                total += 1
            else:
                try:
                    payload = _load_json(file_path)
                except json.JSONDecodeError:
                    print(f"Skip invalid JSON: {file_path}")
                    continue
                cleaned, count = _clean_payload(payload)
                if cleaned is None:
                    print(f"Skip unsupported JSON structure: {file_path}")
                    continue
                out_file = output_path / file_path.name
                _write_json(out_file, cleaned)
                total += count
        print(f"Cleaned records written to {output_path} (items: {total})")
        return

    if input_path.suffix == ".jsonl":
        cleaned_iter = (clean_record(obj) for obj in _iter_jsonl(input_path))
        out_file = output_path if output_path.suffix else output_path / input_path.name
        _write_jsonl(out_file, cleaned_iter)
        print(f"Cleaned JSONL written to {out_file}")
        return

    try:
        payload = _load_json(input_path)
    except json.JSONDecodeError:
        print(f"Invalid JSON: {input_path}")
        return
    cleaned, _ = _clean_payload(payload)
    if cleaned is None:
        print(f"Unsupported JSON structure: {input_path}")
        return
    out_file = output_path
    if out_file.is_dir() or out_file.suffix == "":
        out_file = out_file / input_path.name
    _write_json(out_file, cleaned)
    print(f"Cleaned JSON written to {out_file}")


if __name__ == "__main__":
    main()
