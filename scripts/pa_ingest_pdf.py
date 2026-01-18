#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PA PDF ingestion (streaming) using PyMuPDF.

Outputs: data/abu/raw_pages.jsonl (JSONL, 1 line per page)
- text: full page plain text (no OCR)
- blocks: simple text blocks from page.get_text('blocks')
- images: exported images with bbox + saved path (embedded or clipped)
- page_size: [width, height]

Progress & robustness
- Start banner with total / target pages
- Progress every N pages (default 10)
- Per-page extraction warning will not abort the whole job

Notes
- If the PDF is a scanned image (no text layer), text will be empty; you may run OCR separately.
- Image bbox is resolved via rawdict when possible; else we rasterize a clip as fallback.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
from typing import Optional

def extract(pdf_path: str,
            out_path: str,
            max_pages: Optional[int] = None,
            images_dir: Optional[str] = None,
            progress_interval: int = 10,
            margin_ratio: float = 0.10) -> int:
    try:
        import fitz  # PyMuPDF
    except Exception as e:
        print('PyMuPDF not installed: pip install pymupdf', file=sys.stderr, flush=True)
        raise
    # Open PDF and determine target page count
    doc = fitz.open(pdf_path)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    total = len(doc)
    target = min(max_pages, total) if max_pages else total
    print(f'[INGEST] Start PDF ingest: file={pdf_path} total_pages={total} target={target} -> {out}', flush=True)
    img_root = Path(images_dir) if images_dir else (out.parent / 'images')
    img_root.mkdir(parents=True, exist_ok=True)
    n = 0
    with out.open('w', encoding='utf-8') as f:
        for i, page in enumerate(doc, 1):
            if i > target:
                break
            try:
                text = page.get_text('text') or ''
                blocks = page.get_text('blocks') or []
            except Exception as e:
                print(f'[WARN] page={i} text extraction failed: {e}', flush=True)
                text, blocks = '', []
            # image boxes
            imgs = []
            try:
                # map xref -> (w,h)
                xmap = {}
                for im in page.get_images(full=True):
                    # (xref, smask, width, height, bpc, colorspace, alt, name)
                    xmap[im[0]] = {'width': im[2], 'height': im[3]}
                # raw blocks for image bbox
                raw = page.get_text('rawdict')
                img_blocks = []
                for b in (raw.get('blocks') or []):
                    if b.get('type') == 1:
                        # Some PyMuPDF versions provide xref under 'image' or 'xref' or 'number'
                        xref = b.get('image') if isinstance(b.get('image'), int) else b.get('xref')
                        if xref is None and 'number' in b and isinstance(b['number'], int):
                            # heuristic fallback
                            xref = b['number']
                        bbox = list(map(float, b.get('bbox') or (0, 0, 0, 0)))
                        img_blocks.append((xref, bbox))
                # export each image block
                import hashlib
                for idx, (xref, bbox) in enumerate(img_blocks, 1):
                    saved_path = None
                    meta = {'xref': int(xref) if isinstance(xref, int) else None,
                            'bbox': bbox,
                            'path': None,
                            'width': None,
                            'height': None,
                            'source': None}
                    if isinstance(xref, int):
                        try:
                            info = doc.extract_image(xref)
                            ext = (info.get('ext') or 'png').lower()
                            data = info.get('image')
                            # stable name: page-idx-xref-hash.ext
                            h = hashlib.sha1(data[:64] if isinstance(data, (bytes, bytearray)) else str(xref).encode()).hexdigest()[:8]
                            fname = f'page_{i:04d}_img_{idx:02d}_x{xref}_{h}.{ext}'
                            p = img_root / fname
                            with p.open('wb') as wf:
                                wf.write(data)
                            meta.update({'path': str(p), 'width': info.get('width'), 'height': info.get('height'), 'source': 'embedded'})
                            saved_path = p
                        except Exception:
                            saved_path = None
                    if saved_path is None:
                        # fallback: rasterize bbox clip
                        try:
                            clip = fitz.Rect(*bbox)
                            pm = page.get_pixmap(clip=clip)
                            fname = f'page_{i:04d}_img_{idx:02d}_clip.png'
                            p = img_root / fname
                            pm.save(str(p))
                            meta.update({'path': str(p), 'width': pm.width, 'height': pm.height, 'source': 'clip'})
                        except Exception as e:
                            print(f'[WARN] page={i} image export failed: {e}', flush=True)
                    imgs.append(meta)
            except Exception as e:
                print(f'[WARN] page={i} image scan failed: {e}', flush=True)
            # page size
            pw, ph = page.rect.width, page.rect.height
            rec = {
                'page': i,
                'page_size': [pw, ph],
                'text': text,
                'blocks': blocks,
                'images': imgs,
            }
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            n += 1
            if i == 1 or i % max(1, int(progress_interval)) == 0 or i == target:
                print(f'[INGEST] progress: {i}/{target} pages (images exported on this page: {len(imgs)})', flush=True)
    doc.close()
    print(f'✓ wrote {n} pages to {out}', flush=True)
    return n


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Ingest PA PDF to jsonl (with progress + image export)')
    ap.add_argument('--pdf', required=True)
    # default renamed to Abu namespace
    ap.add_argument('--out', default=str(Path('data')/'abu'/'raw_pages.jsonl'))
    ap.add_argument('--max-pages', type=int, default=None)
    ap.add_argument('--images-dir', type=str, default=None, help='Directory to save exported images (default: alongside out)')
    ap.add_argument('--progress-interval', type=int, default=10)
    ap.add_argument('--margin-ratio', type=float, default=0.10, help='Reserved for downstream heading filters')
    args = ap.parse_args()
    cnt = extract(args.pdf, args.out, args.max_pages, images_dir=args.images_dir, progress_interval=args.progress_interval, margin_ratio=args.margin_ratio)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
