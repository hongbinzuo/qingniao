#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build an index that links extracted Abu images to page context and pattern candidates.

Inputs
- data/abu/raw_pages.jsonl  (from pa_ingest_pdf.py)
- data/abu/images/*         (from pa_ingest_pdf.py)
- config/abu_patterns.yaml  (optional; source_pages -> candidate patterns)

Outputs
- outputs/abu_index.json
- outputs/abu_gallery.html  (lightweight preview for manual review)

Notes
- This script does NOT require OCR or ML; it's a deterministic association tool.
- Pattern candidates are based on page membership in abu_patterns.yaml.
"""
from __future__ import annotations
import sys, json, re
from pathlib import Path
import os
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parents[2]

RAW = ROOT / 'data' / 'abu' / 'raw_pages.jsonl'
IMG_DIR = ROOT / 'data' / 'abu' / 'images'
CFG = ROOT / 'config' / 'abu_patterns.yaml'
OUT_JSON = ROOT / 'outputs' / 'abu_index.json'
OUT_HTML = ROOT / 'outputs' / 'abu_gallery.html'


def load_pages() -> Dict[int, Dict[str, Any]]:
    pages: Dict[int, Dict[str, Any]] = {}
    if not RAW.exists():
        return pages
    with RAW.open('r', encoding='utf-8') as f:
        for ln in f:
            try:
                r = json.loads(ln)
            except Exception:
                continue
            pg = int(r.get('page') or 0)
            pages[pg] = r
    return pages


def load_patterns() -> Dict[str, List[int]]:
    if not CFG.exists():
        return {}
    try:
        import yaml  # type: ignore
    except Exception:
        # minimal YAML reader: fallback to regex scan of "name" and "source_pages"
        text = CFG.read_text(encoding='utf-8', errors='ignore')
        pat = {}
        blocks = re.split(r'\n\s*-\s+name:', text)
        for b in blocks[1:]:
            try:
                name = b.split("\n", 1)[0].strip().strip("'\"")
                m = re.search(r'source_pages:\s*\[(.*?)\]', b)
                pages = [int(x) for x in (m.group(1) if m else '').split(',') if x.strip().isdigit()]
                pat[name] = pages
            except Exception:
                pass
        return pat
    # normal path with pyyaml if available
    try:
        obj = yaml.safe_load(CFG.read_text(encoding='utf-8')) or {}
    except Exception:
        return {}
    patterns: Dict[str, List[int]] = {}
    for it in obj.get('patterns') or []:
        try:
            name = str(it.get('name'))
            pages = list(map(int, it.get('source_pages') or []))
            patterns[name] = pages
        except Exception:
            continue
    return patterns


def shortlist_context(pages: Dict[int, Dict[str, Any]], pg: int, window: int = 2, max_len: int = 1200) -> str:
    buf: List[str] = []
    for off in range(-window, window + 1):
        q = pages.get(pg + off)
        if not q:
            continue
        t = (q.get('text') or '').strip()
        if t:
            buf.append(f"[p{pg+off}] " + t)
    s = '\n'.join(buf)
    if len(s) > max_len:
        s = s[:max_len] + ' ...'
    return s


def build(window: int = 2) -> int:
    pages = load_pages()
    patterns = load_patterns()
    inv_index: Dict[int, List[str]] = {}
    for name, src_pages in patterns.items():
        for p in src_pages:
            inv_index.setdefault(p, []).append(name)

    images = sorted([*IMG_DIR.glob('*.png'), *IMG_DIR.glob('*.jpg')])
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    items: List[Dict[str, Any]] = []
    for p in images:
        # infer page number from filename pattern: page_XXXX_img_
        m = re.search(r'page_(\d+)_', p.stem)
        pg = int(m.group(1)) if m else None
        ctx = shortlist_context(pages, pg, window=window) if pg else ''
        cands = inv_index.get(pg or -1, [])
        # bbox is inside pages[pg]['images'] if present; try to locate matching path
        bbox = None
        if pg and pg in pages:
            try:
                for im in (pages[pg].get('images') or []):
                    if str(p) == str(im.get('path')):
                        bbox = im.get('bbox')
                        break
            except Exception:
                pass
        items.append({
            'image': str(p),
            'page': pg,
            'bbox': bbox,
            'candidates': cands,
            'context': ctx,
        })

    OUT_JSON.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

    # simple gallery
    html_lines = [
        '<!doctype html>',
        '<meta charset="utf-8"/>',
        '<title>Abu Gallery</title>',
        '<style>body{font-family:sans-serif;background:#111;color:#ddd} .card{display:flex;gap:16px;margin:12px;padding:12px;background:#1b1b1b;border-radius:8px} img{max-width:520px;height:auto;border:1px solid #333} .meta{flex:1} .cand{color:#9fd} .ctx{white-space:pre-wrap;color:#bbb;font-size:12px}</style>',
        '<h2>Abu Gallery (images with context)</h2>'
    ]
    base = OUT_HTML.parent.resolve()
    for it in items[:500]:  # cap for lightweight file
        cands = ', '.join(it.get('candidates') or []) or '(none)'
        html_lines.append('<div class="card">')
        try:
            rel = os.path.relpath(Path(it['image']).resolve(), base).replace('\\', '/')
        except Exception:
            rel = Path(it['image']).as_posix()
        html_lines.append(f"<div><img src='{rel}'/></div>")
        html_lines.append('<div class="meta">')
        html_lines.append(f"<div>page: <b>{it.get('page')}</b> bbox: {it.get('bbox')}</div>")
        html_lines.append(f"<div>candidates: <span class='cand'>{cands}</span></div>")
        html_lines.append(f"<div class='ctx'>{(it.get('context') or '').replace('&','&amp;').replace('<','&lt;')}</div>")
        html_lines.append('</div></div>')
    OUT_HTML.write_text('\n'.join(html_lines), encoding='utf-8')
    print(f'OK: wrote index -> {OUT_JSON}, gallery -> {OUT_HTML}')
    return 0


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Build Abu image-context index + gallery')
    ap.add_argument('--window', type=int, default=2, help='context window in pages (±window)')
    args = ap.parse_args()
    try:
        sys.exit(build(window=args.window))
    except Exception as e:
        print('Build index failed:', e)
        sys.exit(2)
