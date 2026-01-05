#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from add_de_conversation import add_conversation

items = [
    ('2026-01-02 22:11', '8895补的，我895移动走了；目前多单均价来到88382', ''),
    ('2026-01-02 22:12', '这个缺口也许下来不只会补一下，顺便扫个损也不错；或者回踩89继续涨也行；878', ''),
    ('2026-01-02 22:13', '(图片) IMG_1895.jpg', ''),
    ('2026-01-02 22:16', '不支棱我就先空为敬；CME 缺口', ''),
    ('2026-01-02 22:17', '', 'John说缓慢升到阻力位做空，急跌插针加仓再做多；截图：Screenshot_20260102_221552_Telegram.jpg'),
    ('2026-01-02 22:19', '多头陷阱概率大，继续看89的反应', ''),
    ('2026-01-02 22:20', '价格横盘，指标跌的不行了，跌破修复范围了（肉眼看的）；看完跌了300点', ''),
    ('2026-01-02 22:21', '', '暴跌了；我在898和3057空；这一会一千点了'),
    ('2026-01-02 22:22', '800点了；就说喝酒误事', ''),
    ('2026-01-02 22:25', '扫了个假损；这是扫韭菜的损，技术党的损在885下面；这里最好也是来个假反弹', ''),
    ('2026-01-02 22:27', '让技术党加一波仓，然后再扫下来；这是我的秘诀', ''),
    ('2026-01-02 22:30', '用庄家思维看技术，而不是跟随技术做技术；最近研究这个，真的强的可怕', ''),
    ('2026-01-02 22:36', '8815补缺口；缺口区间8815-8855', ''),
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

