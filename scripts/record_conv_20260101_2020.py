#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from add_de_conversation import add_conversation

items = [
    ('2026-01-01 20:20', '上去空就完事儿了', ''),
    ('2026-01-01 20:21', '等下次黄金大涨的时候，也许就是大饼见底的时候', ''),
    ('2026-01-01 20:52', '', '88000现在都是马里亚纳海沟了'),
    ('2026-01-01 21:57', '不会，现在这个走势，后面打针的方向就是上涨的反方向', ''),
    ('2026-01-01 21:58', '', '894才能看涨吧'),
    ('2026-01-01 21:58', '目前像是小吸筹的样子', ''),
    ('2026-01-01 21:59', '894我多单都要止盈了', ''),
]
ids=[]
for ts, tmsg, umsg in items:
    cid, strategy_info, evaluation_info = add_conversation(ts, tmsg, user_message=umsg, source='discord')
    ids.append(cid)
print('OK ids:', ids)
