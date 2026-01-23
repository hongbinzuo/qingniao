#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helpers for loading and applying vision taxonomy mappings.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TAXONOMY_PATH = ROOT / "outputs" / "abu_deep_analysis" / "reports" / "taxonomy_mapping.json"


def load_taxonomy_mapping(path: Optional[Path] = None) -> Dict[str, Dict[str, str]]:
    mapping_path = path or DEFAULT_TAXONOMY_PATH
    if not mapping_path or not mapping_path.exists():
        return {}
    try:
        payload = json.loads(mapping_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    mapping: Dict[str, Dict[str, str]] = {}
    for key in ("pattern_name", "pattern_name_raw", "pattern_type", "pattern_family"):
        block = payload.get(key)
        if isinstance(block, dict) and isinstance(block.get("mapping"), dict):
            mapping[key] = block["mapping"]
    return mapping


def map_value_strict(value: Optional[str], mapping: Dict[str, str]) -> Optional[str]:
    if value is None or not isinstance(value, str) or not mapping:
        return None
    if value in mapping:
        return mapping[value]
    lowered = value.lower()
    for key, mapped in mapping.items():
        if isinstance(key, str) and key.lower() == lowered:
            return mapped
    return None


def map_value_lenient(value: Optional[str], mapping: Dict[str, str]) -> Optional[str]:
    if value is None or not isinstance(value, str) or not mapping:
        return value
    return map_value_strict(value, mapping) or value
