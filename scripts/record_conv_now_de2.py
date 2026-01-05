#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
from add_de_conversation import add_conversation

msg = '短线看多是逆势多，突破一个level吃一个，吃点就走；跌起来可以用力空'
now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
cid, strategy_info, evaluation_info = add_conversation(now, msg, user_message=None, source='discord')
print(f'OK id={cid} time={now}')
