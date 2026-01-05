#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
from datetime import datetime

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def main():
    db = TraderDBManager('sherlock')
    # 按已知ID=2标记为参考（reference），如需通用可查询最新一条
    db.update_signal_status(2, 'reference')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    db.add_viewpoint(content='标记: PIEVERSE/USDT 设为参考信号（rating 6/10，不作为主要信号）',
                     timestamp=ts, source='sherlock', category='flag', tags=['reference'])
    db.close()
    print('✓ 标记完成: sig#2 -> reference')

if __name__=='__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()
