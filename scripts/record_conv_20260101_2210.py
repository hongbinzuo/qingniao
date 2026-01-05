#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from add_de_conversation import add_conversation

# De. — 2026-01-01 22:10 多条消息
items = [
    ('2026-01-01 22:10', '没有', ''),
    ('2026-01-01 22:10', '哈哈哈', ''),
    ('2026-01-01 22:10', '还有忍辱负重以为能赢的10倍杠杆没死', ''),
    ('2026-01-01 22:10', '要把913-926这波的十倍杠杆清完', ''),
]
ids=[]
for ts, tmsg, umsg in items:
    cid, strategy_info, evaluation_info = add_conversation(ts, tmsg, user_message=umsg, source='discord')
    ids.append(cid)
print('OK ids:', ids)
