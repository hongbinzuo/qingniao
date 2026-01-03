#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluate the latest N real trades using a bracket heuristic suitable for De.

Rules (default):
- timeframe: 5m/15m style; use '15m' if unknown
- stop_distance_points: default 400 (can be 400/600/800); infer from record if present
- take profit rule: 1R; stop rule: break-even after 1R (not simulated here)
- current price: fetched from Gate.io/Binance ticker

Outputs:
- Updates trade_records with stop_distance_points/timeframe/tp_rule/stop_rule if missing
- Writes a markdown summary to trading_signals/.learning_reports/
- Adds a brief viewpoint summary
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime
import duckdb
import requests

DB = r"C:\\Users\\zuoho\\code\\qingniao\\src\\data\\qingniao_de.duckdb"
OUTDIR = Path('trading_signals')/'.learning_reports'
OUTDIR.mkdir(parents=True, exist_ok=True)


def get_current_price() -> float | None:
    # Try Gate.io then Binance
    try:
        r = requests.get("https://api.gateio.ws/api/v4/spot/tickers", params={"currency_pair":"BTC_USDT"}, timeout=12)
        d = r.json()
        if isinstance(d, list) and d:
            return float(d[0]['last'])
    except Exception:
        pass
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol":"BTCUSDT"}, timeout=12)
        d = r.json()
        if d and d.get('price'):
            return float(d['price'])
    except Exception:
        pass
    return None


def main(n: int = 4, default_stop: float = 400.0, default_tf: str = '15m'):
    con = duckdb.connect(DB)
    rows = con.execute(
        """
        SELECT id, timestamp, symbol, direction, entry_price, exit_price, profit_pct, stop_distance_points, timeframe
        FROM trade_records
        WHERE entry_price IS NOT NULL
        ORDER BY id DESC
        LIMIT ?
        """, [n]
    ).fetchall()
    if not rows:
        print('no trades to evaluate')
        con.close()
        return

    cp = get_current_price()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines: list[str] = []
    lines.append('# 最近实盘评估（Bracket 1R / BEP）')
    lines.append('')
    lines.append(f'生成时间: {now} | 当前价: ${cp:,.2f}' if cp else f'生成时间: {now} | 当前价: N/A')
    lines.append('规则: 默认止损点距 400；1R 止盈；达到 1R 后保本（仅报告，不在此脚本内模拟持仓演化）')
    lines.append('')

    updated = 0
    for rid, ts, sym, dire, entry, exitp, pnlpct, stop_pts, tf in rows:
        stop_pts = float(stop_pts) if stop_pts is not None else default_stop
        tf = tf or default_tf
        # Compute bracket
        if dire == 'short':
            sl = entry + stop_pts
            tp1 = entry - stop_pts
        else:
            sl = entry - stop_pts
            tp1 = entry + stop_pts
        # rr to date
        rr = None
        if cp is not None:
            if dire == 'short':
                rr = (entry - cp) / stop_pts
            else:
                rr = (cp - entry) / stop_pts
        hit = (rr is not None and rr >= 1.0)

        lines.append(f'- trade#{rid} [{ts}] {sym} {dire or "?"} | E=${entry:,.1f} SL=${sl:,.1f} TP1=${tp1:,.1f} | stop={stop_pts:.0f} | tf={tf}')
        if rr is not None:
            lines.append(f'  · 当前RR={rr:.2f} | 是否达1R: {"是" if hit else "否"}')
        if pnlpct is not None:
            lines.append(f'  · 录入时显示收益={pnlpct:.2f}%')

        # Update missing fields
        need_update = False
        sets = []
        vals = []
        if tf is not None:
            sets.append('timeframe=?'); vals.append(tf)
        if stop_pts is not None:
            sets.append('stop_distance_points=?'); vals.append(stop_pts)
        sets.append('tp_rule=?'); vals.append('1R_take_profit')
        sets.append('stop_rule=?'); vals.append('break_even_after_1R')
        vals.append(rid)
        con.execute(f"UPDATE trade_records SET {', '.join(sets)} WHERE id=?", vals)
        updated += 1

    # Write report
    out = OUTDIR / f'trade_eval_bracket_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    out.write_text('\n'.join(lines), encoding='utf-8')

    # Viewpoint summary
    try:
        from pathlib import Path
        sys.path.insert(0, str(Path('src')))
        from db_manager_trader import TraderDBManager  # type: ignore
        db = TraderDBManager('de')
        db.add_viewpoint(
            content=f'最近{len(rows)}笔实盘评估：默认400点距，1R止盈；已更新记录并输出报告 {out.name}',
            timestamp=now, source='learn', category='learning', tags=['trade','eval','bracket']
        )
        db.close()
    except Exception:
        pass

    con.close()
    print(f'updated {updated} trades; report={out}')


if __name__ == '__main__':
    main()

