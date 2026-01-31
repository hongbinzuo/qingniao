#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch-run the heuristic chart recognizer over extracted Abu images.

Inputs
- data/abu/images/*  (from scripts/pa_ingest_pdf.py)

Outputs
- outputs/abu_chart_features.jsonl   (one JSON per image)
- optional ROI debug images under outputs/abu_debug/

Usage
  py -3 scripts\abu\abu_chart_batch.py --limit 200 --debug-dir outputs/abu_debug

Requires
- pip install opencv-python numpy
- (optional OCR) pip install pytesseract  and OS-level Tesseract if needed
"""
from __future__ import annotations
import sys, json
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
IMG_DIR = ROOT / 'data' / 'abu' / 'images'
OUT = ROOT / 'outputs' / 'abu_chart_features.jsonl'


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Batch chart recognizer')
    ap.add_argument('--images-dir', type=str, default=str(IMG_DIR))
    ap.add_argument('--out', type=str, default=str(OUT))
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--debug-dir', type=str, default=None, help='Save ROI debug images')
    args = ap.parse_args()

    images: List[Path] = sorted([*Path(args.images_dir).glob('*.png'), *Path(args.images_dir).glob('*.jpg')])
    if args.limit and args.limit > 0:
        images = images[:args.limit]
    print(f'[CHART] images={len(images)} out={args.out}')

    # lazy import recognizer
    from importlib.util import spec_from_file_location, module_from_spec
    rec_path = ROOT / 'scripts' / 'abu_chart_recognizer.py'
    spec = spec_from_file_location('abu_chart_recognizer', str(rec_path))
    if spec is None or spec.loader is None:
        print('Cannot import abu_chart_recognizer')
        return 2
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    dbgdir = Path(args.debug_dir) if args.debug_dir else None
    if dbgdir:
        dbgdir.mkdir(parents=True, exist_ok=True)

    done = 0
    with outp.open('w', encoding='utf-8') as w:
        for i, p in enumerate(images, 1):
            dbg = None
            if dbgdir:
                dbg = str(dbgdir / (p.stem + '_roi.png'))
            try:
                res = mod.analyze(str(p), debug_out=dbg)
                rec = {'image': str(p), **res}
            except Exception as e:
                rec = {'image': str(p), 'error': str(e)}
            w.write(json.dumps(rec, ensure_ascii=False) + '\n')
            done += 1
            if i % 20 == 0 or i == len(images):
                print(f'[CHART] progress: {i}/{len(images)}')

    print(f'[CHART] Done. Wrote -> {outp} items={done}')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print('Batch failed:', e)
        sys.exit(1)

