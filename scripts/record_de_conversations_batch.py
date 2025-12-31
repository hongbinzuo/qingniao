#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量录入 De. 对话（用于从外部文本/记录导入）
本脚本内置一组会话（可按需修改 items），运行一次即写入数据库与文件日志系统。
"""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from add_de_conversation import add_conversation


def main():
    items = [
        ('00:53', '挂上保本了\n突破不了88加仓空\n一帮kol 看coinbase 的做多指标，都在多\n所以咱们空，他们爆了再多', None),
        ('00:55', None, '好\n哈哈哈\n夺笋啊'),
        ('00:55', '最近的881\n突破不了，就继续空\n突破883再多，可以吃上9万+', None),
        ('00:56', None, 'trump又要发币了'),
        ('00:56', None, '收到'),
        ('00:57', '只看大饼，然后等黄金坑\n2026做好这两个，够了', None),
    ]
    ids = []
    for ts, trader_msg, user_msg in items:
        trader_msg = trader_msg or ''
        cid, strategy_info, evaluation_info = add_conversation(ts, trader_msg, user_message=user_msg, source='discord')
        ids.append(cid)
    print('✓ 已录入会话ID: ', ids)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
