#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据用户口径更新 Sherlock 最近三笔信号的结果：
- sig#3 (ZEC/USDT): 仍在挂单（不更新，保持 pending）
- sig#2 (PIEVERSE/USDT): 达到最终止盈（记录评估 tp2_hit）
- sig#1 (A2Z/USDT): 未成交直接拉升（记录评估 missed）
"""
from pathlib import Path
import sys
from datetime import datetime

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager


def main():
    db = TraderDBManager('sherlock')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # sig#2 PIEVERSE -> tp2_hit（直接标记状态，并记录备注）
    try:
        db.update_signal_status(2, 'tp2_hit')
        db.add_viewpoint(content='评估: PIEVERSE/USDT 已达最终止盈（用户口径）；后续回填成交均价与腿明细。',
                         timestamp=now, source='sherlock', category='eval', tags=['tp2_hit'])
    except Exception as e:
        print('[warn] PIEVERSE status update failed:', e)

    # sig#1 A2Z -> missed（直接标记状态，并记录备注）
    try:
        db.update_signal_status(1, 'missed')
        db.add_viewpoint(content='评估: A2Z/USDT 未成交直接起飞（用户口径）；挂单腿后续作废处理。',
                         timestamp=now, source='sherlock', category='eval', tags=['missed'])
    except Exception as e:
        print('[warn] A2Z status update failed:', e)

    db.close()
    print('✓ Sherlock outcomes updated: PIEVERSE=tp2_hit, A2Z=missed, ZEC=pending')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
