#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查最新信号"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from db_manager_trader import TraderDBManager

db = TraderDBManager('abu')
conn = db._get_connection()

latest = conn.execute('SELECT MAX(signal_time) FROM trading_signals').fetchone()[0]
count = conn.execute('SELECT COUNT(*) FROM trading_signals WHERE signal_time=?', [latest]).fetchone()[0]

print(f"最新信号时间: {latest}")
print(f"信号数量: {count}")

samples = conn.execute('SELECT symbol, signal_type, entry_price, score FROM trading_signals WHERE signal_time=? LIMIT 10', [latest]).fetchall()
print("\n前10个信号样本:")
for r in samples:
    print(f"  {r[0]} {r[1]} Entry={r[2]:.4f} Score={r[3]:.2f}")

db.close()



