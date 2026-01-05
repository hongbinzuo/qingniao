#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Sherlock universe list from local sources.
- Scans outputs/dream/*.json/.md for symbols (ABC/USDT or bare A-Z0-9 tokens)
- Scans outputs/sherlock/scan_strong_*.md for Symbols column
- Falls back to a curated core list if nothing found

Writes: config/sherlock_universe.txt (one base per line, upper-case)
"""
from __future__ import annotations
import re, json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'config' / 'sherlock_universe.txt'

CORE = [
    'BTC','ETH','SOL','BNB','XRP','ADA','AVAX','DOGE','LINK','DOT',
    'MATIC','TON','TRX','ATOM','SUI','APT','ARB','OP','NEAR','PEPE',
    'SEI','TIA','INJ','AAVE','UNI','RUNE','ETC','FIL','ICP','XLM',
    'SATS','ORDI','PYTH','ALT','AEVO','WIF','JUP','POL','ENA','RENDER',
]

def _yield_files(pats: Iterable[str]):
    for pat in pats:
        for p in ROOT.glob(pat):
            if p.is_file():
                yield p

def _sym_from_text(txt: str) -> list[str]:
    out: list[str] = []
    # explicit pairs ABC/USDT
    for m in re.finditer(r"\b([A-Za-z0-9][A-Za-z0-9._\-]{1,14})\s*/\s*(USDT|USDC|USD)\b", txt):
        out.append(m.group(1).upper())
    # bare bases (avoid common words)
    if not out:
        for m in re.finditer(r"\b([A-Z0-9]{2,10})\b", txt):
            b = m.group(1).upper()
            if b in {'USDT','USDC','USD','TP','SL','MA','EMA','MACD','RSI','VWAP','TVEM'}:
                continue
            if b.isdigit():
                continue
            out.append(b)
    # dedup keep order
    seen=set(); res=[]
    for s in out:
        if s not in seen:
            seen.add(s); res.append(s)
    return res

def _collect_from_dream() -> set[str]:
    bases: set[str] = set()
    for p in _yield_files(['outputs/dream/*.json','outputs/dream/*.md']):
        try:
            if p.suffix.lower()=='.json':
                data = json.loads(p.read_text(encoding='utf-8', errors='ignore'))
                # common shapes: list of dicts or {messages:[]}
                items = []
                if isinstance(data, dict) and isinstance(data.get('messages'), list):
                    items = data['messages']
                elif isinstance(data, list):
                    items = data
                for it in items:
                    txt = ''
                    if isinstance(it, dict):
                        txt = (it.get('text') or it.get('content') or it.get('trader_message') or '')
                        if not isinstance(txt, str):
                            try:
                                txt = json.dumps(txt, ensure_ascii=False)
                            except Exception:
                                txt = str(txt)
                    elif isinstance(it, str):
                        txt = it
                    for s in _sym_from_text(txt):
                        bases.add(s)
            else:
                txt = p.read_text(encoding='utf-8', errors='ignore')
                for s in _sym_from_text(txt):
                    bases.add(s)
        except Exception:
            continue
    return bases

def _collect_from_sherlock_md() -> set[str]:
    bases: set[str] = set()
    for p in _yield_files(['outputs/sherlock/scan_strong_*.md']):
        try:
            for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
                # table row like: | 1 | BTC | 45000.0 | 80 | 60.1 | 备注 |
                cols = [c.strip() for c in line.strip().split('|') if c.strip()]
                if len(cols)>=2 and cols[0].isdigit():
                    sym = cols[1].upper()
                    if re.fullmatch(r'[A-Z0-9]{2,15}', sym):
                        bases.add(sym)
        except Exception:
            continue
    return bases

def main():
    bases = set(CORE)
    bases |= _collect_from_dream()
    bases |= _collect_from_sherlock_md()
    # write out
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(sorted(bases)), encoding='utf-8')
    print(f"✓ Universe saved: {OUT} ({len(bases)} symbols)")

if __name__ == '__main__':
    try:
        import sys
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass
    main()

