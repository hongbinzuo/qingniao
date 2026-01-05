#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from add_de_conversation import add_conversation

items = [
    # 22:17 观点与定义
    ('2026-01-01 22:17', '', '现在这个日线属于动量陷阱'),
    ('2026-01-01 22:17', '', '动量陷阱就是，动能指标涨，价格不涨'),
    # 22:19 De. 说明
    ('2026-01-01 22:19', '也叫诱多行为，但是在短线上是将计就计，他会涨，但是涨完这一波，没走的或者追的人，最后都要被套（日线的行为)', ''),
]
ids=[]
for ts, tmsg, umsg in items:
    cid, strategy_info, evaluation_info = add_conversation(ts, tmsg, user_message=umsg, source='discord')
    ids.append(cid)
print('OK ids:', ids)
