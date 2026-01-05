#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from database_design_v2 import DatabaseDesignV2

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    d = DatabaseDesignV2()
    dbfile = d.create_trader_database('sherlock', 'Sherlock')
    print('✓ 已创建 Sherlock 数据库:', dbfile)

