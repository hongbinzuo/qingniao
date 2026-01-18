#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查ATOM信号和当前价格"""
import sys
import requests
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

# 获取当前价格
try:
    r = requests.get('https://fapi.binance.com/fapi/v1/ticker/price', 
                     params={'symbol': 'ATOMUSDT'}, timeout=10)
    current_price = float(r.json()['price'])
    print(f"ATOM当前价格: {current_price:.4f} USDT")
except Exception as e:
    print(f"获取价格失败: {e}")
    current_price = None

# 查询数据库中的ATOM信号
db = TraderDBManager('abu')
conn = db._get_connection()

print("\n数据库中的ATOM信号:")
print("=" * 80)

rows = conn.execute("""
    SELECT id, signal_type, entry_price, stop_loss, take_profit_1, 
           entry_model, notes, signal_time
    FROM trading_signals 
    WHERE symbol='ATOM' AND timeframe='15m'
    ORDER BY id DESC 
    LIMIT 10
""").fetchall()

for r in rows:
    sig_id, sig_type, entry, sl, tp1, model, notes, sig_time = r
    print(f"\n信号ID: {sig_id}")
    print(f"  时间: {sig_time}")
    print(f"  方向: {sig_type}")
    print(f"  入场: {entry:.4f}")
    print(f"  止损: {sl:.4f}")
    print(f"  止盈1: {tp1:.4f}")
    print(f"  模型: {model}")
    print(f"  备注: {notes[:100] if notes else 'N/A'}")
    
    if current_price:
        if sig_type.upper() == 'SHORT':
            if current_price >= sl:
                print(f"  ⚠️  当前价格 {current_price:.4f} >= 止损 {sl:.4f} (已止损)")
            else:
                distance_to_sl = ((sl - current_price) / entry) * 100
                print(f"  📊 距离止损: {distance_to_sl:.2f}% ({sl - current_price:.4f})")
        elif sig_type.upper() == 'LONG':
            if current_price <= sl:
                print(f"  ⚠️  当前价格 {current_price:.4f} <= 止损 {sl:.4f} (已止损)")
            else:
                distance_to_sl = ((current_price - sl) / entry) * 100
                print(f"  📊 距离止损: {distance_to_sl:.2f}% ({current_price - sl:.4f})")

db.close()



