#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Annotate extracted Abu images with Gemini (Vision) and write JSONL.

Inputs
- data/abu/images/*.png|jpg  (from scripts/pa_ingest_pdf.py)
- data/abu/raw_pages.jsonl   (for contextual text; we read window +/-K pages)

Outputs
- outputs/abu_gemini_annotations.jsonl
- outputs/.cache/abu_gemini/  (per-image cache by sha1)

Usage
  py -3 scripts\abu_gemini_annotate.py --limit 50 --model gemini-1.5-flash
  py -3 scripts\abu_gemini_annotate.py --context-window 2 --sleep-ms 200

Env
- GEMINI_API_KEY  (required)
- GEMINI_MODEL    (optional; default gemini-1.5-flash)
"""
from __future__ import annotations
import os, sys, json, time, hashlib
from pathlib import Path
from typing import Dict, Any, List

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / 'data' / 'abu' / 'images'
PAGES_JSONL = ROOT / 'data' / 'abu' / 'raw_pages.jsonl'
OUT = ROOT / 'outputs' / 'abu_gemini_annotations.jsonl'
CACHE = ROOT / 'outputs' / '.cache' / 'abu_gemini'


def sha1_of_file(p: Path, nbytes: int = 65536) -> str:
    h = hashlib.sha1()
    with p.open('rb') as f:
        while True:
            b = f.read(nbytes)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_pages() -> Dict[int, Dict[str, Any]]:
    pages: Dict[int, Dict[str, Any]] = {}
    if not PAGES_JSONL.exists():
        return pages
    with PAGES_JSONL.open('r', encoding='utf-8') as f:
        for ln in f:
            try:
                r = json.loads(ln)
            except Exception:
                continue
            pg = int(r.get('page') or 0)
            pages[pg] = r
    return pages


PROMPT = (
    "You are a price-action trading tutor. Given a chart image from a trading book, "
    "extract structured signals relevant for pattern-based reasoning. Keep it concise and JSON-only.\n"
    "Fields:\n"
    "- pattern: short name (e.g., 'Bullish Engulfing', 'Head and Shoulders', 'Trendline Break')\n"
    "- timeframe_hint: if any in the image (e.g., 15m, 1h)\n"
    "- direction: long/short/neutral\n"
    "- key_features: [ ... ]  # bullets like 'higher lows', 'break of structure', 'FVG fill', 'volume spike'\n"
    "- annotations: [ {label, text?} ]  # labels found in the image (like A/B/C, entry/stop notes)\n"
    "- confidence: 0..1\n"
    "If context_text is provided, use it to refine the pattern name and direction.\n"
    "Respond with a single JSON object only."
)


def annotate_image(model: str, key: str, img_path: Path, context_text: str | None) -> Dict[str, Any]:
    import google.generativeai as genai
    from PIL import Image

    genai.configure(api_key=key)
    m = genai.GenerativeModel(model)
    img = Image.open(str(img_path))
    parts: List[Any] = [
        {"text": PROMPT},
        img,
    ]
    if context_text:
        parts.append({"text": f"context_text:\n{context_text[:4000]}"})
    try:
        resp = m.generate_content(parts)
        txt = resp.text or '{}'  # type: ignore[attr-defined]
    except Exception as e:
        return {"error": str(e)}
    try:
        data = json.loads(txt)
    except Exception:
        data = {"raw": txt}
    return data


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Annotate Abu images using Gemini Vision')
    ap.add_argument('--model', type=str, default=os.environ.get('GEMINI_MODEL', 'gemini-1.5-pro'))
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--context-window', type=int, default=2)
    ap.add_argument('--sleep-ms', type=int, default=0)
    args = ap.parse_args()

    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        print('GEMINI_API_KEY not set', file=sys.stderr)
        return 2

    pages = load_pages()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    imgs = sorted([p for p in IMAGES_DIR.glob('*.png')] + [p for p in IMAGES_DIR.glob('*.jpg')])
    if args.limit and args.limit > 0:
        imgs = imgs[:args.limit]
    print(f'[GEMINI] Found {len(imgs)} images to annotate; model={args.model}', flush=True)

    with OUT.open('a', encoding='utf-8') as w:
        for i, p in enumerate(imgs, 1):
            h = sha1_of_file(p)
            cfile = CACHE / f'{h}.json'
            if cfile.exists():
                try:
                    cached = json.loads(cfile.read_text(encoding='utf-8'))
                    rec = {"image": str(p), "sha1": h, "result": cached, "cached": True}
                    w.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    if i % 10 == 0:
                        print(f'[GEMINI] progress: {i}/{len(imgs)} (cache)', flush=True)
                    continue
                except Exception:
                    pass
            # infer page number from filename (pattern: page_XXXX_img_..)
            m = None
            try:
                stem = p.stem
                import re
                m = re.search(r'page_(\d+)_', stem)
            except Exception:
                m = None
            pg = int(m.group(1)) if m else None
            context = None
            if pg and args.context_window >= 0:
                buf: List[str] = []
                for off in range(-args.context_window, args.context_window + 1):
                    if off == 0:  # include page itself
                        pass
                    q = pages.get(pg + off)
                    if not q:
                        continue
                    t = (q.get('text') or '')
                    if t:
                        buf.append(t)
                context = '\n'.join(buf)

            data = annotate_image(args.model, key, p, context)
            rec = {"image": str(p), "sha1": h, "page": pg, "result": data}
            w.write(json.dumps(rec, ensure_ascii=False) + '\n')
            try:
                cfile.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            except Exception:
                pass
            if i % 10 == 0:
                print(f'[GEMINI] progress: {i}/{len(imgs)}', flush=True)
            if args.sleep_ms:
                time.sleep(max(0, args.sleep_ms) / 1000.0)

    print(f'[GEMINI] Done. Wrote -> {OUT}', flush=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print('Annotate failed:', e)
        sys.exit(1)
