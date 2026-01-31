#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Abu one-click runner (Python) — replaces .bat for better logging and portability.

Steps (with clear logs):
  [1/6] Ensure Abu DB
  [2/6] Migrate columns (score/symbol/notes)
  [3/6] Ensure PyMuPDF (fitz)
  [4/6] Optional: PDF ingest (progress) -> data/abu/raw_pages.jsonl, build -> config/abu_patterns.yaml
  [5/6] Run 15m scan (binance -> gate fallback), write DB + Markdown
  [6/6] Start API (uvicorn) on :8090

Usage (PowerShell / CMD):
  py -3 scripts\\abu\\abu_upgrade_and_run.py --pdf "C:\\path\\book.pdf" --pages 1000
  py -3 scripts\\abu\\abu_upgrade_and_run.py  # skip PDF ingest

Flags:
  --pdf, --pages, --top, --exchange, --port, --no-serve, --no-scan, --no-ingest
Env fallback: PDF_IN, PDF_PAGES if flags omitted.
"""
from __future__ import annotations
import os, sys, subprocess
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
SCRIPTS = ROOT / 'scripts'

# Ensure src on sys.path for db imports
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def _import_from_path(mod_name: str, path: Path):
    """Import a module by file path (works without package __init__)."""
    import importlib.util
    from importlib.machinery import SourceFileLoader
    spec = importlib.util.spec_from_loader(mod_name, SourceFileLoader(mod_name, str(path)))
    if spec is None or spec.loader is None:
        raise ImportError(f'cannot import {mod_name} from {path}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def ensure_pymupdf() -> bool:
    print('[3/6] Ensure PyMuPDF (fitz) ...', flush=True)
    try:
        import fitz  # noqa: F401
        print('  - PyMuPDF already installed; import OK', flush=True)
        return True
    except Exception:
        print('  - Installing PyMuPDF (this may take a while)...', flush=True)
        rc = subprocess.call([sys.executable, '-m', 'pip', 'install', 'pymupdf'])
        if rc != 0:
            print('  WARN: pip install pymupdf failed; PDF ingest will be skipped.', flush=True)
            return False
        try:
            import fitz  # noqa: F401
            print('  - PyMuPDF import OK', flush=True)
            return True
        except Exception as e:  # pragma: no cover
            print('  WARN: PyMuPDF import still failing:', e, flush=True)
            return False


def ensure_abu_db() -> Path:
    print('[1/6] Ensure Abu DB ...', flush=True)
    db_file = SRC / 'data' / 'qingniao_abu.duckdb'
    if db_file.exists():
        print(f'  - Found: {db_file}', flush=True)
        return db_file
    from database_design_v2 import DatabaseDesignV2
    d = DatabaseDesignV2()
    out = d.create_trader_database('abu', 'Abu')
    print(f'  - Created: {out}', flush=True)
    return db_file


def migrate_columns() -> None:
    print('[2/6] Migrate columns (score, symbol, notes) ...', flush=True)
    mod = _import_from_path('migrate_abu_add_score', SCRIPTS / 'migrate_abu_add_score.py')
    try:
        rc = int(mod.ensure_columns())  # type: ignore[attr-defined]
    except Exception:
        rc = 1
    if rc == 0:
        print('  - Migration OK (or already up-to-date)', flush=True)
    else:
        print('  WARN: migration returned non-zero; continue if DB was just created.', flush=True)


def ingest_pdf_if_any(pdf_in: Optional[str], pages: Optional[int]) -> None:
    print('[4/6] Optional: PDF ingest + build Abu library ...', flush=True)
    if not pdf_in:
        # env fallback
        pdf_in = os.environ.get('PDF_IN')
    if not pages:
        envp = os.environ.get('PDF_PAGES')
        pages = int(envp) if envp and envp.isdigit() else None
    if not pdf_in:
        print('  - PDF_IN not set; skip PDF ingest.', flush=True)
        return
    if not Path(pdf_in).exists():
        print(f'  ERROR: PDF_IN does not exist: {pdf_in}', flush=True)
        sys.exit(3)

    ok = ensure_pymupdf()
    if not ok:
        print('  WARN: skipping ingest because PyMuPDF not available', flush=True)
        return

    mod_ing = _import_from_path('pa_ingest_pdf', SCRIPTS / 'pa_ingest_pdf.py')
    target = pages or 500
    print(f'  - Ingesting {target} pages from: {pdf_in}', flush=True)
    try:
        # default output path inside module is data/abu/raw_pages.jsonl; we reuse it
        out_path = str(ROOT / 'data' / 'abu' / 'raw_pages.jsonl')
        cnt = int(mod_ing.extract(pdf_in, out_path, target))  # type: ignore[attr-defined]
        print(f'  - Ingest done, pages={cnt}', flush=True)
    except Exception as e:
        print('  WARN: PDF ingestion failed:', e, flush=True)
        return

    # Build library
    try:
        mod_build = _import_from_path('abu_build_library', SCRIPTS / 'abu_build_library.py')
        in_path = ROOT / 'data' / 'abu' / 'raw_pages.jsonl'
        out_path = ROOT / 'config' / 'abu_patterns.yaml'
        rc = int(mod_build.build(in_path, out_path))  # type: ignore[attr-defined]
        if rc == 0:
            print('  - Build library OK', flush=True)
        else:
            print('  WARN: Build library returned non-zero', flush=True)
    except Exception as e:
        print('  WARN: Build library failed:', e, flush=True)


def run_scan(top: int = 10, exchange: str = 'binance') -> int:
    print('[5/6] Run Abu 15m scan ...', flush=True)
    # Spawn a subprocess to preserve the script's own argparse behavior and logs
    cmd = [sys.executable, str(SCRIPTS / 'pa_scan_15m_top10.py'), '--top', str(int(top)), '--exchange', str(exchange), '--write-db', '1']
    print('  - Exec:', ' '.join(cmd), flush=True)
    return subprocess.call(cmd)


def start_api(port: int = 8090) -> int:
    print('[6/6] Start Qingniao BE API ...', flush=True)
    try:
        import uvicorn  # type: ignore
    except Exception:
        print('  - Installing uvicorn ...', flush=True)
        rc = subprocess.call([sys.executable, '-m', 'pip', 'install', 'uvicorn', 'fastapi', 'pydantic'])
        if rc != 0:
            print('  WARN: failed to install uvicorn/fastapi; skip serving.', flush=True)
            return rc
        import uvicorn  # type: ignore
    # Import the FastAPI app object directly and serve
    api_mod = _import_from_path('qingniao_be_api', SCRIPTS / 'qingniao_be_api.py')
    app = getattr(api_mod, 'app', None)
    if app is None:
        print('  ERROR: cannot find FastAPI app in qingniao_be_api.py', flush=True)
        return 2
    uvicorn.run(app, host='0.0.0.0', port=int(port))
    return 0


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Abu one-click runner (Python)')
    ap.add_argument('--pdf', type=str, default=None, help='PDF path for ingest (optional)')
    ap.add_argument('--pages', type=int, default=None, help='Max pages to ingest (default 500 if pdf given)')
    ap.add_argument('--top', type=int, default=10)
    ap.add_argument('--exchange', type=str, default='binance')
    ap.add_argument('--port', type=int, default=8090)
    ap.add_argument('--no-ingest', action='store_true')
    ap.add_argument('--no-scan', action='store_true')
    ap.add_argument('--no-serve', action='store_true')
    args = ap.parse_args()

    # 1-2: DB ensure + migrate
    ensure_abu_db()
    migrate_columns()

    # 3: Ensure PyMuPDF when needed
    if not args.no_ingest and (args.pdf or os.environ.get('PDF_IN')):
        ensure_pymupdf()
    else:
        print('[3/6] Ensure PyMuPDF (fitz) ...  - skipped (no PDF ingest requested)', flush=True)

    # 4: Ingest + build library (optional)
    if not args.no_ingest:
        ingest_pdf_if_any(args.pdf, args.pages)
    else:
        print('[4/6] Optional: PDF ingest + build Abu library ...  - skipped (--no-ingest)', flush=True)

    # 5: Scan
    if not args.no_scan:
        rc = run_scan(args.top, args.exchange)
        if rc != 0:
            print('  ERROR: Abu scan failed (non-zero exit).', flush=True)
            sys.exit(2)
    else:
        print('[5/6] Run Abu 15m scan ...  - skipped (--no-scan)', flush=True)

    # 6: Serve
    if not args.no_serve:
        start_api(args.port)
    else:
        print('[6/6] Start Qingniao BE API ...  - skipped (--no-serve)', flush=True)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print('Run failed:', e)
        sys.exit(1)

