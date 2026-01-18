#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, json, subprocess, os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
TODOS_DIR = ROOT / 'trading_signals' / '.todos'
SNAP_DIR = ROOT / 'trading_signals' / '.sleep_snapshots'


def find_latest_todo() -> Path | None:
    if not TODOS_DIR.exists():
        return None
    files = sorted(TODOS_DIR.glob('gn_todo_*.json'))
    return files[-1] if files else None


def load_todos(p: Path | None) -> dict:
    if not p or not p.exists():
        # default skeleton
        return {
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'todos': [
                {"task":"start_api", "cmd":"scripts\\start_qingniao_be_api.bat", "port":8090, "status":"pending"},
                {"task":"resume_abu_scan_scheduler", "cmd":"schtasks /Run /TN \"Qingniao-Abu-15m\"", "status":"pending"},
            ]
        }
    try:
        return json.loads(p.read_text(encoding='utf-8') or '{}')
    except Exception:
        return {'created_at': '', 'todos': []}


def save_todos(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def run_cmd_detached(cmd: str) -> int:
    # start new window for long-running tasks (API)
    if os.name == 'nt':
        return subprocess.call(['cmd', '/c', 'start', '', cmd])
    else:
        # best effort on non-Windows
        try:
            subprocess.Popen(cmd, shell=True)
            return 0
        except Exception:
            return 1


def run_cmd_inline(cmd: str) -> int:
    return subprocess.call(cmd, shell=True)


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Wake resume runner for GN TODOs')
    ap.add_argument('--run', action='store_true', help='execute tasks')
    args = ap.parse_args()

    latest = find_latest_todo()
    data = load_todos(latest)
    todos = data.get('todos') or []

    print('Wake TODOs:')
    for i, t in enumerate(todos, 1):
        print(f" {i}. {t.get('task')} | status={t.get('status','pending')} | cmd={t.get('cmd')}")

    if not args.run:
        print('\nHint: run with --run to execute. Example: py -3 scripts\\wake_resume.py --run')
        return 0

    # Execute tasks
    for t in todos:
        task = (t.get('task') or '').lower()
        cmd = t.get('cmd') or ''
        print(f"-> Running: {task}")
        rc = 0
        if task == 'start_api':
            rc = run_cmd_detached(cmd)
        elif task == 'resume_abu_scan_scheduler':
            rc = run_cmd_inline(cmd)
        elif task == 'optional_pdf_ingestion':
            # only run if PDF_IN set
            if os.environ.get('PDF_IN'):
                rc = run_cmd_inline(cmd)
            else:
                print('   skipped (PDF_IN not set)')
                t['status'] = 'skipped'
                continue
        else:
            rc = run_cmd_inline(cmd)
        t['status'] = 'done' if rc == 0 else f'err:{rc}'

    # persist updated statuses to a new file
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = TODOS_DIR / f'gn_todo_resume_{ts}.json'
    save_todos(out, data)

    # quick open page
    if os.name == 'nt':
        subprocess.call(['cmd', '/c', 'start', '', 'http://localhost:8090/abu'])

    print('Done. Updated TODO snapshot:', out)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print('Wake failed:', e)
        sys.exit(2)

