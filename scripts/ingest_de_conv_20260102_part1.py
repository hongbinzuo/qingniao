#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from add_de_conversation import add_conversation


def main():
    msgs = [
        ("2026-01-02 16:34:00", "牛回\n这把如果突破89能追点\n骗了很多次了"),
        ("2026-01-02 16:56:00", "五分钟算\n止损88888\n加仓部分止损120点\n止损不能宽，8815有缺口，开盘前补一下也很正常"),
        ("2026-01-02 17:54:00", "看盘前涨到那\n我加的仓，现在已经过安全了，挂上了保险"),
    ]
    ids = []
    for ts, text in msgs:
        cid, _, _ = add_conversation(ts, text, source='discord')
        ids.append(cid)
        print('✓ add conv', cid, ts)
    print('done', ids)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()

