#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录今天早上的信号评估结果
"""

import sys
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from record_signal_evaluation import record_evaluated_signals
except ImportError:
    print("无法导入记录模块", file=sys.stderr)
    sys.exit(1)

# 评估结果
results = [
    {
        'signal_time': '2025-12-29 10:55:44',
        'timeframe': '5m',
        'type': 'long',
        'entry': 88093,
        'stop_loss': 87800,
        'take_profit_1': 89531,
        'take_profit_2': 90250,
        'model': '反转形态-三重底',
        'strength': 'strong',
        'status': 'stopped',
        'max_profit': 0,
        'max_loss': -0.33,
        'current_price': 87512,
        'current_pnl_pct': -0.66,
        'reached_tp1': False,
        'reached_tp2': False,
        'hit_stop_loss': True
    },
    {
        'signal_time': '2025-12-29 10:55:44',
        'timeframe': '15m',
        'type': 'long',
        'entry': 89335,
        'stop_loss': 89067,
        'take_profit_1': 89465,
        'take_profit_2': 89600,
        'model': '区间突破',
        'strength': 'strong',
        'status': 'stopped',
        'max_profit': 0,
        'max_loss': -0.30,
        'current_price': 87550.9,
        'current_pnl_pct': -2.00,
        'reached_tp1': False,
        'reached_tp2': False,
        'hit_stop_loss': True
    },
    {
        'signal_time': '2025-12-29 10:55:44',
        'timeframe': '1h',
        'type': 'short',
        'entry': 89090,
        'stop_loss': 91054,
        'take_profit_1': 88353,
        'take_profit_2': 87461,
        'model': '阻力位回落',
        'strength': 'medium',
        'status': 'full_tp',
        'max_profit': 1.83,
        'max_loss': -1.46,
        'current_price': 88140.8,
        'current_pnl_pct': 1.07,
        'reached_tp1': True,
        'reached_tp2': True,
        'hit_stop_loss': False
    }
]

if __name__ == "__main__":
    print("正在记录信号评估结果...", file=sys.stderr)
    record_evaluated_signals(results)
    print("\n✅ 信号记录完成！", file=sys.stderr)


