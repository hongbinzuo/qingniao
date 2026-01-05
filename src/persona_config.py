#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Persona config for De. system.

- Stored at config/de_persona.json
  {
    "allow_bracket_short": true,
    "allow_confirm_long": true,
    "no_hang_long": true,
    "default_stop_pts_5m": 400,
    "default_stop_pts_15m": 400,
    "availability": "watching",  # watching | away
    "ttl_bars": 6                  # signal TTL in bars
  }

Utilities to load/save/update flags, with safe defaults.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parent.parent
CONF = ROOT / 'config' / 'de_persona.json'

DEFAULTS: Dict[str, Any] = {
    'allow_bracket_short': True,
    'allow_confirm_long': True,
    'no_hang_long': True,
    'default_stop_pts_5m': 400,
    'default_stop_pts_15m': 400,
    'availability': 'watching',
    'ttl_bars': 6,
}


def load_persona() -> Dict[str, Any]:
    try:
        if CONF.exists():
            data = json.loads(CONF.read_text(encoding='utf-8') or '{}')
        else:
            data = {}
    except Exception:
        data = {}
    out = DEFAULTS.copy()
    out.update({k: data.get(k) for k in DEFAULTS.keys() if k in data})
    return out


def save_persona(p: Dict[str, Any]) -> None:
    CONF.parent.mkdir(parents=True, exist_ok=True)
    data = DEFAULTS.copy()
    data.update(p or {})
    CONF.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def update_from_clues(clues: Dict[str, int]) -> Dict[str, Any]:
    """Very light update from keyword counts parsed in conversations.
    - if mentions of '低多' or '实时' dominate → allow_confirm_long=True
    - if mentions of '不挂单接多'/'不挂多' → no_hang_long=True
    - if mentions around '400'/'800' with '止损' → default_stop_pts set to 400/800
    """
    p = load_persona()
    # long/confirm bias
    if clues.get('低多', 0) + clues.get('实时', 0) >= 2:
        p['allow_confirm_long'] = True
    if clues.get('不挂单接多', 0) + clues.get('不挂多', 0) >= 1:
        p['no_hang_long'] = True
    # stop distance
    if clues.get('止损400', 0) >= 1:
        p['default_stop_pts_5m'] = 400
        p['default_stop_pts_15m'] = 400
    if clues.get('止损800', 0) >= 1:
        p['default_stop_pts_5m'] = 800
        p['default_stop_pts_15m'] = 800
    save_persona(p)
    return p

