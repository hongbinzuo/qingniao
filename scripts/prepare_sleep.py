#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepare-for-sleep routine:
- Flush pending conversations to DB
- Run incremental learner (conversations)
- Learn today from local K-lines (5m/15m/1h)
- Echo current status (latest signals, bracket, counts, recent reports)

Usage:
  python scripts/prepare_sleep.py
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def run_py(script: str):
    p = subprocess.run([sys.executable, str(ROOT/script)], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    print(f'== {script} ==')
    if p.stdout:
        print(p.stdout.strip())
    if p.stderr:
        print(p.stderr.strip())

def main():
    # 1) Flush any pending conversations (if any)
    run_py(Path('scripts')/'flush_pending_conversations.py')
    # 2) Incremental learner on conversations
    run_py(Path('scripts')/'run_incremental_learner.py')
    # 3) Learn today from K-lines (local DuckDB)
    run_py(Path('scripts')/'learn_today_from_kline.py')
    # 4) Echo status
    run_py(Path('scripts')/'echo_status.py')
    print('Prepared for sleep. You can close the lid safely.')

if __name__ == '__main__':
    main()

