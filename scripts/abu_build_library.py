#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a lightweight Abu price-action library from data/abu/raw_pages.jsonl

Heuristics:
- Read per-page text, split lines; treat lines with length 6..64 and not too many digits as headings.
- Collect unique headings and example page numbers.
- Emit config/abu_patterns.yaml with simple stubs for future enhancement.

Safe to run repeatedly; overwrites the YAML.
"""
from __future__ import annotations
from pathlib import Path
import sys, json, re

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'config' / 'abu_patterns.yaml'
SRC = ROOT / 'data' / 'abu' / 'raw_pages.jsonl'


def guess_headings(text: str) -> list[str]:
    lines = [x.strip() for x in text.splitlines()]
    out: list[str] = []
    for ln in lines:
        if not ln: continue
        if len(ln) < 6 or len(ln) > 64: continue
        if sum(ch.isdigit() for ch in ln) > len(ln)//3:  # too many digits
            continue
        if re.match(r'^[A-Za-z0-9 .:/()\-]+$', ln) is None:
            # allow Chinese as well
            pass
        # prefer lines that look like titles
        if ln.endswith(':') or ln.endswith('：'):
            ln = ln[:-1].strip()
        out.append(ln)
    return out


def _filter_blocks(blocks: list, pw: float, ph: float, margin_ratio: float = 0.10) -> list:
    """Drop blocks likely to be header/footer using page size and a margin ratio."""
    if not blocks:
        return []
    top = ph * margin_ratio
    bottom = ph * (1 - margin_ratio)
    kept = []
    for b in blocks:
        try:
            y0 = float(b[1]); y1 = float(b[3])
        except Exception:
            kept.append(b); continue
        # keep if not near header/footer bands
        if y1 <= top or y0 >= bottom:
            continue
        kept.append(b)
    return kept


def build(in_path: Path, out_path: Path, margin_ratio: float = 0.10) -> int:
    if not in_path.exists():
        print(f"raw_pages.jsonl not found: {in_path}")
        return 1
    buckets: dict[str, set[int]] = {}
    cnt = 0
    with in_path.open('r', encoding='utf-8') as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            page = int(rec.get('page') or 0)
            text = rec.get('text') or ''
            # filter watermark/header/footer-like lines using block positions
            blocks = rec.get('blocks') or []
            pw, ph = 0.0, 0.0
            try:
                pw, ph = (rec.get('page_size') or [0, 0])
            except Exception:
                pw, ph = 0.0, 0.0
            fblocks = _filter_blocks(blocks, pw, ph, margin_ratio=margin_ratio)
            # rebuild a lightweight text from kept blocks (if any), fallback to full text
            if fblocks:
                try:
                    kept_lines = [str(b[4]).strip() for b in fblocks if len(b) >= 5 and str(b[4]).strip()]
                    text_for_heading = '\n'.join(kept_lines)
                except Exception:
                    text_for_heading = text
            else:
                text_for_heading = text
            for h in guess_headings(text_for_heading):
                buckets.setdefault(h, set()).add(page)
            cnt += 1
    # write YAML
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as w:
        w.write('# Auto-generated Abu price-action library (stub)\n')
        w.write('version: v0.1\n')
        w.write('patterns:\n')
        for name, pages in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            pgs = sorted(list(pages))[:12]
            w.write(f"  - name: '{name}'\n")
            w.write("    aliases: []\n")
            w.write("    rules: []\n")
            w.write("    notes: ''\n")
            w.write("    source_pages: [" + ', '.join(map(str, pgs)) + "]\n")
    print(f"OK: wrote {out_path} (pages={cnt}, headings={len(buckets)})")
    return 0


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Build Abu library from raw_pages.jsonl with heading filtering')
    ap.add_argument('--in', dest='inp', default=str(SRC))
    ap.add_argument('--out', dest='outp', default=str(OUT))
    ap.add_argument('--margin-ratio', type=float, default=0.10)
    args = ap.parse_args()
    try:
        sys.exit(build(Path(args.inp), Path(args.outp), margin_ratio=args.margin_ratio))
    except Exception as e:
        print('Build library failed:', e)
        sys.exit(2)
