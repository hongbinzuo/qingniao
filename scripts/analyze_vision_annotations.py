#!/usr/bin/env python3
import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


NULLISH_STRINGS = {"", "null", "none"}


def is_nullish(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in NULLISH_STRINGS:
        return True
    return False


def iter_records(root: Path) -> Iterable[Tuple[Path, Dict[str, Any]]]:
    for path in sorted(root.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    yield path, item
        elif isinstance(data, dict):
            yield path, data


def walk_confidence(node: Any, path: str = "") -> Iterable[Tuple[str, Any]]:
    if isinstance(node, dict):
        for key, value in node.items():
            next_path = f"{path}.{key}" if path else key
            if key == "confidence":
                yield next_path, value
            yield from walk_confidence(value, next_path)
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            next_path = f"{path}[{idx}]"
            yield from walk_confidence(value, next_path)


def canonicalize(text: str) -> str:
    cleaned = text.strip().lower()
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"[()\\[\\],.:;!?]", " ", cleaned)
    cleaned = re.sub(r"\\s+", " ", cleaned).strip()
    return cleaned


def build_taxonomy(values: List[str]) -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    groups: Dict[str, Counter] = defaultdict(Counter)
    for value in values:
        key = canonicalize(value)
        groups[key][value] += 1

    mapping: Dict[str, str] = {}
    canonical_groups: Dict[str, List[str]] = {}
    for key, counter in groups.items():
        variants = [name for name, _ in counter.most_common()]
        canonical = counter.most_common(1)[0][0]
        canonical_groups[canonical] = variants
        for variant in variants:
            mapping[variant] = canonical
    return canonical_groups, mapping


def safe_int(value: Any) -> Tuple[bool, Any]:
    if is_nullish(value):
        return False, None
    if isinstance(value, int):
        return True, value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return True, int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return True, int(stripped)
    return False, value


def summarize_distribution(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter()
    for value in values:
        if is_nullish(value):
            counter["<null>"] += 1
        else:
            counter[str(value)] += 1
    return dict(counter.most_common())


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze vision annotation outputs.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("outputs/abu_deep_analysis/clean_json"),
        help="Directory with per-image clean JSON outputs.",
    )
    parser.add_argument(
        "--include-glob",
        type=str,
        default="page_*.json",
        help="Glob pattern to select input files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/abu_deep_analysis/reports"),
        help="Directory to write reports.",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    records: List[Dict[str, Any]] = []
    record_sources: List[str] = []
    parse_errors: List[str] = []

    for path in sorted(input_dir.glob(args.include_glob)):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            parse_errors.append(str(path))
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    records.append(item)
                    record_sources.append(str(path))
        elif isinstance(data, dict):
            records.append(data)
            record_sources.append(str(path))

    total_records = len(records)

    required_fields = ["image_id", "page"]
    missing_required: List[Dict[str, Any]] = []
    for rec, src in zip(records, record_sources):
        missing = [field for field in required_fields if is_nullish(rec.get(field))]
        if missing:
            missing_required.append(
                {"source": src, "image_id": rec.get("image_id"), "missing": missing}
            )

    image_ids = [rec.get("image_id") for rec in records if not is_nullish(rec.get("image_id"))]
    pages = [rec.get("page") for rec in records if not is_nullish(rec.get("page"))]
    duplicate_image_ids = {
        key: count for key, count in Counter(image_ids).items() if count > 1
    }
    duplicate_pages = {
        str(key): count for key, count in Counter(pages).items() if count > 1
    }

    page_type_counts = Counter(type(value).__name__ for value in pages)
    page_parse_failures: List[Any] = []
    for value in pages:
        ok, parsed = safe_int(value)
        if not ok:
            page_parse_failures.append(parsed)

    field_missing_counts: Dict[str, int] = {}
    top_level_fields = [
        "slide_type",
        "timeframe_hint",
        "market",
        "chart",
        "patterns",
        "bar_by_bar",
        "counting",
        "kline_features",
        "key_levels",
        "targets_probabilities",
        "confirmations",
        "invalidations",
        "annotations_text",
        "annotations_structured",
        "summary",
        "ema_interaction",
        "bar_geometry",
        "quality",
        "raw",
    ]
    for field in top_level_fields:
        field_missing_counts[field] = sum(1 for rec in records if is_nullish(rec.get(field)))

    slide_types = summarize_distribution(rec.get("slide_type") for rec in records)
    timeframe_hints = summarize_distribution(rec.get("timeframe_hint") for rec in records)
    markets = summarize_distribution(rec.get("market") for rec in records)

    pattern_entries: List[Dict[str, Any]] = []
    for rec in records:
        patterns = rec.get("patterns") or []
        if isinstance(patterns, list):
            for pat in patterns:
                if isinstance(pat, dict):
                    pattern_entries.append(pat)

    pattern_field_missing = Counter()
    pattern_family_values: List[str] = []
    pattern_type_values: List[str] = []
    pattern_name_values: List[str] = []
    raw_pattern_name_values: List[str] = []
    missing_name_with_raw = 0
    pattern_nullish_counts = Counter()
    for pat in pattern_entries:
        for key in ["pattern_family", "pattern_type", "pattern_name", "status"]:
            value = pat.get(key)
            if is_nullish(value):
                pattern_field_missing[key] += 1
                pattern_nullish_counts[key] += 1
        if not is_nullish(pat.get("pattern_family")):
            pattern_family_values.append(str(pat["pattern_family"]))
        if not is_nullish(pat.get("pattern_type")):
            pattern_type_values.append(str(pat["pattern_type"]))
        if not is_nullish(pat.get("pattern_name")):
            pattern_name_values.append(str(pat["pattern_name"]))
        raw = pat.get("raw")
        raw_name = None
        if isinstance(raw, dict):
            raw_name = raw.get("pattern_name")
        if not is_nullish(raw_name):
            raw_pattern_name_values.append(str(raw_name))
            if is_nullish(pat.get("pattern_name")):
                missing_name_with_raw += 1

    confidence_issues: List[Dict[str, Any]] = []
    for rec, src in zip(records, record_sources):
        for path, value in walk_confidence(rec):
            if isinstance(value, (int, float)):
                if not (0 <= value <= 1):
                    confidence_issues.append(
                        {"source": src, "path": path, "value": value}
                    )

    pattern_stats = {
        "total_patterns": len(pattern_entries),
        "patterns_per_record_avg": round(len(pattern_entries) / total_records, 4) if total_records else 0,
        "pattern_family_counts": dict(Counter(pattern_family_values).most_common()),
        "pattern_type_counts": dict(Counter(pattern_type_values).most_common()),
        "pattern_name_counts": dict(Counter(pattern_name_values).most_common()),
        "raw_pattern_name_counts": dict(Counter(raw_pattern_name_values).most_common()),
        "missing_pattern_name_with_raw": missing_name_with_raw,
        "pattern_field_missing": dict(pattern_field_missing),
        "pattern_nullish_counts": dict(pattern_nullish_counts),
    }

    quality_report = {
        "summary": {
            "total_records": total_records,
            "unique_image_ids": len(set(image_ids)),
            "unique_pages": len(set(str(p) for p in pages)),
            "duplicate_image_ids": duplicate_image_ids,
            "duplicate_pages": duplicate_pages,
            "parse_errors": parse_errors,
        },
        "missing_required_fields": missing_required,
        "field_missing_counts": field_missing_counts,
        "page_type_counts": dict(page_type_counts),
        "page_parse_failures": page_parse_failures,
        "distributions": {
            "slide_type": slide_types,
            "timeframe_hint": timeframe_hints,
            "market": markets,
        },
        "pattern_stats": pattern_stats,
        "confidence_out_of_range": confidence_issues,
    }

    quality_json_path = output_dir / "quality_report.json"
    quality_md_path = output_dir / "quality_report.md"
    quality_json_path.write_text(json.dumps(quality_report, ensure_ascii=False, indent=2))

    lines = []
    lines.append(f"# Vision Annotation Quality Report")
    lines.append("")
    lines.append(f"- Total records: {total_records}")
    lines.append(f"- Unique image_id: {len(set(image_ids))}")
    lines.append(f"- Unique page: {len(set(str(p) for p in pages))}")
    lines.append(f"- Missing required fields: {len(missing_required)}")
    lines.append(f"- Parse errors: {len(parse_errors)}")
    lines.append("")
    lines.append("## Distributions")
    lines.append(f"- slide_type: {dict(Counter(slide_types).most_common(10))}")
    lines.append(f"- timeframe_hint: {dict(Counter(timeframe_hints).most_common(10))}")
    lines.append(f"- market: {dict(Counter(markets).most_common(10))}")
    lines.append("")
    lines.append("## Patterns")
    lines.append(f"- total patterns: {len(pattern_entries)}")
    lines.append(f"- avg patterns/record: {quality_report['pattern_stats']['patterns_per_record_avg']}")
    lines.append(f"- unique pattern_name: {len(pattern_stats['pattern_name_counts'])}")
    lines.append(f"- missing pattern fields: {dict(pattern_field_missing)}")
    lines.append("")
    lines.append("## Confidence Issues")
    lines.append(f"- out of range: {len(confidence_issues)}")
    quality_md_path.write_text("\n".join(lines))

    taxonomy = {}
    for label, values in [
        ("pattern_family", pattern_family_values),
        ("pattern_type", pattern_type_values),
        ("pattern_name", pattern_name_values),
        ("pattern_name_raw", raw_pattern_name_values),
    ]:
        groups, mapping = build_taxonomy(values)
        taxonomy[label] = {
            "canonical_groups": groups,
            "mapping": mapping,
        }

    taxonomy_path = output_dir / "taxonomy_mapping.json"
    taxonomy_path.write_text(json.dumps(taxonomy, ensure_ascii=False, indent=2))

    taxonomy_md_path = output_dir / "taxonomy_report.md"
    name_groups = taxonomy["pattern_name"]["canonical_groups"]
    multi_variant = {k: v for k, v in name_groups.items() if len(v) > 1}
    lines = []
    lines.append("# Vision Annotation Taxonomy Report")
    lines.append("")
    lines.append(f"- Unique pattern_family: {len(taxonomy['pattern_family']['mapping'])}")
    lines.append(f"- Unique pattern_type: {len(taxonomy['pattern_type']['mapping'])}")
    lines.append(f"- Unique pattern_name: {len(taxonomy['pattern_name']['mapping'])}")
    lines.append(f"- Unique raw pattern_name: {len(taxonomy['pattern_name_raw']['mapping'])}")
    lines.append(f"- pattern_name groups with >1 variant: {len(multi_variant)}")
    lines.append("")
    if multi_variant:
        lines.append("## Multi-variant pattern_name groups (top 20)")
        for idx, (canonical, variants) in enumerate(sorted(multi_variant.items())[:20], 1):
            lines.append(f"{idx}. {canonical}: {variants}")
    taxonomy_md_path.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
