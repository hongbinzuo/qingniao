#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 trading_signals/.pending_conversations/*.jsonl 批量写入 DuckDB（de）。
每行 JSON 形如：{"timestamp":"YYYY-mm-dd HH:MM","trader_message":"...","user_message":"..."}
写入成功后移动到 .done/ 目录；失败保持原样，便于下次重试。
"""
from __future__ import annotations
from pathlib import Path
import sys, json, shutil

SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from add_de_conversation import add_conversation


def main():
    pend = Path('trading_signals') / '.pending_conversations'
    done = pend / '.done'
    pend.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)

    files = sorted(pend.glob('pending_*.jsonl'))
    if not files:
        print('No pending files.')
        return
    total = 0
    for fp in files:
        ok = True
        try:
            lines = fp.read_text(encoding='utf-8').splitlines()
            for ln in lines:
                if not ln.strip():
                    continue
                try:
                    rec = json.loads(ln)
                    ts = rec.get('timestamp')
                    tmsg = rec.get('trader_message') or ''
                    umsg = rec.get('user_message') or ''
                    add_conversation(ts, tmsg, user_message=umsg, source='discord')
                    total += 1
                except Exception as e:
                    print(f'[skip] {fp.name} line error: {e}', file=sys.stderr)
                    ok = False
        except Exception as e:
            print(f'[error] read {fp} failed: {e}', file=sys.stderr)
            ok = False
        if ok:
            try:
                shutil.move(str(fp), str(done / fp.name))
            except Exception as e:
                print(f'[warn] move {fp} failed: {e}', file=sys.stderr)
    print(f'✓ flushed {total} conversations.')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    try:
        main()
    except Exception as e:
        print(f'flush failed: {e}', file=sys.stderr)
