#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from add_de_conversation import add_conversation

items = [
    ('2026-01-01 22:25', '日线裸k其实也是一样的906一下就是假东西，属于0.6以下了，不够强\n现在是在0.5以下抽空，随他怎么涨8万铁定要到，什么时候到，我不知道，哈哈哈', ''),
    ('2026-01-01 22:28', '中长线观点，短线别被影响\n我873有短多', ''),
    ('2026-01-01 22:29', '', ':emoji_8: :emoji_8: :emoji_8:'),
    ('2026-01-01 22:29', '将计就计\n实框分一下', ''),
    ('2026-01-01 22:29', '', '我82长线多那也要扔了吧\n要到8万的话'),
    ('2026-01-01 22:30', '这波上去扔', ''),
]
ids=[]
for ts, tmsg, umsg in items:
    cid, strategy_info, evaluation_info = add_conversation(ts, tmsg, user_message=umsg, source='discord')
    ids.append(cid)
print('OK ids:', ids)
