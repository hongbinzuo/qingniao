#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flush staged trade records from trading_signals/.pending_trades/*.jsonl into DuckDB (de).

Each JSON line example:
  {
    "timestamp": "2026-01-04 10:44:00",
    "symbol": "BTC/USDT",
    "direction": "short",
    "entry_price": 90100.0,
    "exit_price": 90588.0,
    "strategy": "bracket_short",
    "screenshot_path": "C:\\Users\\zuoho\\Pictures\\IMG_1908.jpg",
    "text_content": "De. 挂单区间 90000–90200；止损 90588；该单已止损。截图: IMG_1908.jpg",
    "timeframe": "15m",
    "stop_distance_points": 488.0,
    "tp_rule": "1R_take_profit",
    "stop_rule": "break_even_after_1R",
    "source": "manual"
  }

On success, files are moved to .done/; failures stay for next retry.
"""
from __future__ import annotations
from pathlib import Path
import sys, json, shutil

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager  # type: ignore


def main():
    pend = ROOT / 'trading_signals' / '.pending_trades'
    done = pend / '.done'
    pend.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)

    files = sorted(pend.glob('pending_trades_*.jsonl'))
    if not files:
        print('No pending trade files.')
        return

    db = TraderDBManager('de')
    con = db._get_connection()
    total = 0

    for fp in files:
        ok_file = True
        try:
            lines = fp.read_text(encoding='utf-8').splitlines()
        except Exception as e:
            print(f'[read-error] {fp.name}: {e}', file=sys.stderr)
            ok_file = False
            lines = []
        for i, ln in enumerate(lines, 1):
            if not ln.strip():
                continue
            try:
                rec = json.loads(ln)
            except Exception as e:
                print(f'[json-error] {fp.name}:{i}: {e}', file=sys.stderr)
                ok_file = False
                continue
            try:
                tid = db.add_trade_record(
                    timestamp=rec.get('timestamp'),
                    symbol=rec.get('symbol') or 'BTC/USDT',
                    direction=rec.get('direction'),
                    leverage=rec.get('leverage'),
                    entry_price=rec.get('entry_price'),
                    exit_price=rec.get('exit_price'),
                    profit_pct=rec.get('profit_pct'),
                    profit_usdt=rec.get('profit_usdt'),
                    strategy=rec.get('strategy'),
                    screenshot_path=rec.get('screenshot_path'),
                    text_content=rec.get('text_content'),
                    source=rec.get('source') or 'manual',
                )
                # Optional post fields
                sets = []
                vals = []
                if rec.get('stop_distance_points') is not None:
                    sets.append('stop_distance_points=?'); vals.append(float(rec['stop_distance_points']))
                if rec.get('tp_rule'):
                    sets.append('tp_rule=?'); vals.append(rec['tp_rule'])
                if rec.get('stop_rule'):
                    sets.append('stop_rule=?'); vals.append(rec['stop_rule'])
                if rec.get('timeframe'):
                    sets.append('timeframe=?'); vals.append(rec['timeframe'])
                if sets:
                    vals.append(tid)
                    con.execute(f"UPDATE trade_records SET {', '.join(sets)} WHERE id=?", vals)
                con.commit()
                total += 1
            except Exception as e:
                ok_file = False
                print(f'[insert-error] {fp.name}:{i}: {e}', file=sys.stderr)
        if ok_file:
            try:
                shutil.move(str(fp), str(done / fp.name))
            except Exception as e:
                print(f'[warn] move {fp} failed: {e}', file=sys.stderr)

    db.close()
    print(f'✓ flushed {total} trades.')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

