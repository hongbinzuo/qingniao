#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
录入一条 De. 对话（时间+消息），用于无确认快速落库。
用法（Windows）:
  python scripts\record_de_conversation_once.py "01:35" "这么走..."
"""
import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from add_de_conversation import add_conversation


def main():
    if len(sys.argv) < 3:
        print('usage: record_de_conversation_once.py <time> <message> [source]')
        sys.exit(2)
    ts = sys.argv[1]
    msg = ' '.join(sys.argv[2:-1]) if len(sys.argv) > 3 else sys.argv[2]
    source = sys.argv[-1] if len(sys.argv) > 3 else 'discord'
    cid, strategy_info, evaluation_info = add_conversation(ts, msg, user_message=None, source=source)
    print(f'OK id={cid}')

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

