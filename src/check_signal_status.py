#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查信号状态"""

import sys
from signal_tracker import SignalTracker

tracker = SignalTracker()
data = tracker.load_signals()

print('=' * 80)
print('已录入的信号状态')
print('=' * 80)
print()

if not data:
    print('暂无已录入的信号')
    sys.exit(0)

for system_name, signals in data.items():
    print(f'系统: {system_name}')
    print(f'信号数量: {len(signals)}')
    print()
    
    for sig in signals:
        direction = "做多" if sig.get('type') == 'long' else "做空"
        status = sig.get('status', 'unknown')
        status_emoji = {
            'pending': '🔵',
            'active': '🟢',
            'partial_tp': '🟡',
            'stopped': '🔴',
            'full_tp': '✅'
        }.get(status, '⚪')
        
        print(f"{status_emoji} {sig['id']}")
        print(f"  状态: {status}")
        print(f"  类型: {direction} ({sig.get('strength', 'medium')})")
        print(f"  时间框架: {sig.get('timeframe', '未知')}")
        print(f"  模型: {sig.get('entry_model', '未知')}")
        print(f"  入场: ${sig.get('entry', 0):,.0f}")
        print(f"  止损: ${sig.get('stop_loss', 0):,.0f}")
        print(f"  止盈1: ${sig.get('take_profit_1', 0):,.0f}")
        print(f"  止盈2: ${sig.get('take_profit_2', 0):,.0f}")
        print(f"  生成时间: {sig.get('generated_time', '未知')}")
        if sig.get('current_price'):
            print(f"  当前价格: ${sig.get('current_price', 0):,.0f}")
        if sig.get('max_profit') is not None:
            print(f"  最大浮盈: {sig.get('max_profit', 0):.2f}%")
        if sig.get('max_loss') is not None:
            print(f"  最大浮亏: {sig.get('max_loss', 0):.2f}%")
        print()



