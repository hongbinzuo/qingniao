#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询 DuckDB（de）中的交易信号与评估结果摘要（Windows Python 运行）
- 显示总数
- 最近 10 条信号
- 最近 10 条评估（含关联的信号关键信息）
"""
import sys
import duckdb
from datetime import datetime

DB_PATH = r"C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb"

def main():
    try:
        # 只读方式，避免被守护进程占用时的写锁冲突
        con = duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        print(f"❌ 无法连接数据库: {e}")
        print("提示: 若提示文件被占用，可先运行 scripts\\falcon_stop.bat 停止，再查询。")
        sys.exit(1)

    # 总数
    try:
        total_signals = con.execute("SELECT COUNT(*) FROM trading_signals").fetchone()[0]
    except Exception:
        total_signals = 0
    try:
        total_evals = con.execute("SELECT COUNT(*) FROM signal_evaluations").fetchone()[0]
    except Exception:
        total_evals = 0

    print("="*80)
    print("数据库: de | 文件:", DB_PATH)
    print("时间:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("总信号数:", total_signals)
    print("总评估数:", total_evals)
    print("="*80)

    # 最近 10 条信号
    print("最近 10 条信号:")
    try:
        rows = con.execute(
            """
            SELECT id, signal_time, timeframe, signal_type, entry_price, stop_loss,
                   take_profit_1, take_profit_2, entry_model, strength, status, created_at
            FROM trading_signals
            ORDER BY signal_time DESC, id DESC
            LIMIT 10
            """
        ).fetchall()
        for r in rows:
            print(f"- #{r[0]} [{r[1]}] {r[2]} {r[3]} | E={r[4]:,.2f} SL={r[5]:,.2f} TP1={r[6] or 0:,.2f} TP2={r[7] or 0:,.2f} | {r[8] or ''} {r[9] or ''} | {r[10]}")
    except Exception as e:
        print("(无法读取 trading_signals):", e)
    print("-"*80)

    # 最近 10 条评估（含关联系统）
    print("最近 10 条评估:")
    try:
        rows = con.execute(
            """
            SELECT e.id, e.signal_id, s.signal_time, s.timeframe, s.signal_type,
                   e.result, e.actual_profit_pct, e.stop_loss_hit, e.take_profit_1_hit, e.take_profit_2_hit,
                   e.evaluation_time
            FROM signal_evaluations e
            JOIN trading_signals s ON e.signal_id = s.id
            ORDER BY e.evaluation_time DESC, e.id DESC
            LIMIT 10
            """
        ).fetchall()
        for r in rows:
            print(f"- eval#{r[0]} sig#{r[1]} [{r[2]}] {r[3]} {r[4]} | 结果={r[5]} | PnL={r[6] if r[6] is not None else 0:+.2f}% | TP1={r[8]} TP2={r[9]} SL={r[7]} | at {r[10]}")
    except Exception as e:
        print("(无法读取 signal_evaluations):", e)

    con.close()

if __name__ == '__main__':
    # Windows 控制台UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
