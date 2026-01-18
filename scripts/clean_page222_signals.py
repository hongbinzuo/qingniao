#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理所有来自第222页的信号（仓位管理教学，不是交易模式）
"""
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

def clean_page222_signals():
    """清理所有来自第222页的信号"""
    print("=" * 80)
    print("清理来自第222页的信号（仓位管理教学）")
    print("=" * 80)
    print()
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 查询所有包含"page 222"或"page_222"的信号
    rows = conn.execute("""
        SELECT id, symbol, signal_type, entry_price, stop_loss, take_profit_1,
               entry_model, notes, signal_time, timeframe
        FROM trading_signals
        WHERE notes LIKE '%page 222%' 
           OR notes LIKE '%page_222%'
           OR entry_model LIKE '%page 222%'
           OR entry_model LIKE '%page_222%'
        ORDER BY signal_time DESC, id DESC
    """).fetchall()
    
    if not rows:
        print("✓ 未找到来自第222页的信号")
        db.close()
        return
    
    print(f"📊 找到 {len(rows)} 个来自第222页的信号:")
    print()
    
    signals_to_delete = []
    for r in rows:
        sig_id, symbol, sig_type, entry, sl, tp1, model, notes, sig_time, tf = r
        signals_to_delete.append(sig_id)
        print(f"  - ID {sig_id}: {symbol} {sig_type} | Entry: {entry:.4f} | SL: {sl:.4f} | "
              f"时间框架: {tf} | 时间: {sig_time}")
    
    print()
    print(f"将删除 {len(signals_to_delete)} 个信号")
    
    # 直接删除（第222页是仓位管理教学，不应作为交易模式）
    placeholders = ','.join(['?' for _ in signals_to_delete])
    conn.execute(f"DELETE FROM trading_signals WHERE id IN ({placeholders})", signals_to_delete)
    conn.commit()
    print(f"\n✓ 已删除 {len(signals_to_delete)} 个来自第222页的信号")
    
    db.close()

if __name__ == '__main__':
    clean_page222_signals()

