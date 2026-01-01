#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询 De. 对话（conversations 表）
- 总条数、时间范围
- 最近 10 条（时间、来源、是否含交易信息）
"""
import sys
import duckdb
from pathlib import Path
from datetime import datetime

DB_PATH = r"C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb"

def main():
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        print(f"❌ 无法连接数据库: {e}")
        sys.exit(1)
    try:
        total = con.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        rng = con.execute("SELECT MIN(timestamp), MAX(timestamp) FROM conversations").fetchone()
        print("="*80)
        print("表: conversations | 文件:", DB_PATH)
        print("总条数:", total)
        if rng and rng[0] and rng[1]:
            print("时间范围:", rng[0], "~", rng[1])
        print("="*80)
        rows = con.execute(
            """
            SELECT id, timestamp, source, has_trading_info, substr(coalesce(trader_message,''),1,60) AS msg
            FROM conversations
            ORDER BY timestamp DESC
            LIMIT 10
            """
        ).fetchall()
        for r in rows:
            print(f"- #{r[0]} [{r[1]}] {r[2]} | trade_info={r[3]} | {r[4]}")
    except Exception as e:
        print("❌ 查询失败:", e)
    finally:
        con.close()

if __name__=='__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()
