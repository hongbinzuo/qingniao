#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from add_de_conversation import add_conversation

items = [
    ('2026-01-02 22:36', '刚看过盘面的点位，然后猜测怎么杀', ''),
    ('2026-01-02 22:36', '', '这里要跌到哪'),
    ('2026-01-02 22:36', '8815补缺口', ''),
    ('2026-01-02 22:37', '', '挂单去'),
    ('2026-01-02 22:37', '缺口区间8815-8855；目前可以说补了', ''),
    ('2026-01-02 22:38', '', '这就补完了？'),
    ('2026-01-02 22:38', '885下面扫损成功？', ''),
    ('2026-01-02 22:38', '', '刚扫了885'),
    ('2026-01-02 22:39', '那这把突破又能多了；89', ''),
]

def main():
    ids=[]
    for ts, tmsg, umsg in items:
        cid, strategy_info, evaluation_info = add_conversation(ts, tmsg, user_message=umsg, source='discord')
        ids.append(cid)
    print('OK ids:', ids)

if __name__=='__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()

