#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from auto_sync_prices_for_evaluation import (
    get_timeseries_connection,
    create_table_if_not_exists,
    get_latest_timestamp,
    sync_prices_for_timeframe,
)


def main():
    conn = get_timeseries_connection()
    if not conn:
        print('❌ 无法连接时序数据库')
        return
    tfs = ['5m','15m','1h','4h','1d']
    now = int(datetime.now().timestamp())
    for tf in tfs:
        create_table_if_not_exists(conn, tf)
        latest = get_latest_timestamp(conn, tf)
        # 如无数据，从30天前开始
        start = latest if latest else int((datetime.now() - timedelta(days=30)).timestamp())
        print(f'同步 {tf}: {datetime.fromtimestamp(start)} -> {datetime.fromtimestamp(now)}')
        sync_prices_for_timeframe(conn, tf, start, now, verbose=True)
    conn.close()
    print('✓ 同步完成')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()

