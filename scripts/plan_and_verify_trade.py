#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为最近一笔（或指定ID）交易生成：
- 执行计划（建议止损/止盈/目标/失效条件）
- 价格回放核验（5m近3天，MFE/MAE、是否命中TP1/TP2/SL）
并写入观点与学习报告。

用法：
  python scripts/plan_and_verify_trade.py          # 处理最近一笔
  python scripts/plan_and_verify_trade.py --id 17  # 指定 trade_id
"""
from __future__ import annotations
import sys, argparse
from pathlib import Path
from datetime import datetime, timedelta

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from generate_btc_de_signals import (
    get_btc_kline_gateio,
    get_btc_kline_bitget,
    analyze_timeframe,
)


def _get_klines(tf: str, limit: int = 1000):
    return get_btc_kline_gateio(tf, limit) or get_btc_kline_bitget(tf, limit)


def propose_plan(direction: str, entry: float, current: float, k15, k1h):
    """生成止损/止盈建议和说明。"""
    plan_lines = []
    labels = []
    # 先做一个环境分析
    a15 = analyze_timeframe(k15, '15分钟', current) if k15 else None
    a1h = analyze_timeframe(k1h, '1小时', current) if k1h else None

    # 取 OTE/Vegas/VWAP/SR
    f618 = f786 = None
    if a15 and a15.get('ote_analysis'):
        oa = a15['ote_analysis']
        f618, f786 = oa.get('fib_618'), oa.get('fib_786')
    e144 = a15.get('ema_144') if a15 else None
    e169 = a15.get('ema_169') if a15 else None
    vwap = a15.get('vwap') if a15 else None
    sr15 = (a15.get('support_resistance') if a15 else {}) or {}

    # 止损：
    if direction == 'long':
        # 优先：0.786下方 + 最近支撑下方
        candidates = []
        if f786:
            candidates.append(f786 * 0.996)
        if sr15.get('support'):
            candidates.append(min(sr15['support']) * 0.997)
        if e169:
            candidates.append(e169 * 0.995)
        stop = min([x for x in candidates if x]) if candidates else entry * 0.98
        risk = entry - stop
        tp1 = entry + risk * 2.5
        tp2 = entry + risk * 3.5
        tgt_note = '以最近阻力/整数位为辅'  # 辅助目标
        if sr15.get('resistance'):
            tp_aux = min(sr15['resistance'])
            if tp_aux and tp_aux < tp2:
                tgt_note = f'辅助目标：{tp_aux:,.0f}'
        plan_lines += [
            f'- 止损: ${stop:,.0f}（0.786/支撑/Vegas下方择优）',
            f'- 止盈: TP1=${tp1:,.0f} (≈1:2.5) | TP2=${tp2:,.0f} (≈1:3.5)，{tgt_note}',
            f'- 失效: 15m 收回 {stop:,.0f} 下方或跌破Vegas并承接不足',
        ]
    else:
        # 做空（未用于本次，但保留）
        candidates = []
        if f786:
            candidates.append(f786 * 1.004)
        if sr15.get('resistance'):
            candidates.append(min(sr15['resistance']) * 1.003)
        if e169:
            candidates.append(e169 * 1.005)
        stop = max([x for x in candidates if x]) if candidates else entry * 1.02
        risk = stop - entry
        tp1 = entry - risk * 2.5
        tp2 = entry - risk * 3.5
        plan_lines += [
            f'- 止损: ${stop:,.0f}（0.786/阻力/Vegas上方择优）',
            f'- 止盈: TP1=${tp1:,.0f} | TP2=${tp2:,.0f}',
            f'- 失效: 15m 收上 {stop:,.0f} 并回踩不破',
        ]
    return stop, tp1, tp2, plan_lines


def verify_after(entry_time: datetime, entry: float, direction: str, stop: float, tp1: float, tp2: float):
    """拉取5m近3天数据，计算是否触及SL/TP，给出MFE/MAE。"""
    k5 = _get_klines('5m', 1000) or []
    if not k5:
        return {'error': 'no_kline'}
    # 过滤 trade 时间之后
    ks = [k for k in k5 if int(k['timestamp']) >= int(entry_time.timestamp())]
    if not ks:
        ks = k5[-200:]
    highs = [k['high'] for k in ks]
    lows = [k['low'] for k in ks]
    times = [int(k['timestamp']) for k in ks]
    hit = {'sl': None, 'tp1': None, 'tp2': None}
    mfe = mae = None
    if direction == 'long':
        mfe = (max(highs) - entry) / entry * 100 if highs else None
        mae = (min(lows) - entry) / entry * 100 if lows else None
        # 命中时间
        for t, h in zip(times, highs):
            if not hit['tp1'] and h >= tp1:
                hit['tp1'] = t
                break
        for t, h in zip(times, highs):
            if not hit['tp2'] and h >= tp2:
                hit['tp2'] = t
                break
        for t, l in zip(times, lows):
            if not hit['sl'] and l <= stop:
                hit['sl'] = t
                break
    else:
        mfe = (entry - min(lows)) / entry * 100 if lows else None
        mae = (entry - max(highs)) / entry * 100 if highs else None
        for t, l in zip(times, lows):
            if not hit['tp1'] and l <= tp1:
                hit['tp1'] = t
                break
        for t, l in zip(times, lows):
            if not hit['tp2'] and l <= tp2:
                hit['tp2'] = t
                break
        for t, h in zip(times, highs):
            if not hit['sl'] and h >= stop:
                hit['sl'] = t
                break
    return {
        'mfe_pct': mfe,
        'mae_pct': mae,
        'hit': hit,
    }


def fmt_ts(ts: int | None):
    if not ts:
        return '-'
    return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--id', type=int, default=None)
    args = ap.parse_args()

    db = TraderDBManager('de')
    con = db._get_connection()
    row = None
    if args.id:
        row = con.execute('SELECT id,timestamp,symbol,direction,leverage,entry_price FROM trade_records WHERE id=?', [args.id]).fetchone()
    else:
        row = con.execute('SELECT id,timestamp,symbol,direction,leverage,entry_price FROM trade_records ORDER BY id DESC LIMIT 1').fetchone()
    if not row:
        print('no trade record')
        return
    tid, ts, symbol, direction, lev, entry = row
    dt = datetime.fromisoformat(ts)

    # 获取行情
    k15 = _get_klines('15m', 200)
    k1h = _get_klines('1h', 200)
    current = k15[-1]['close'] if k15 else (k1h[-1]['close'] if k1h else entry)

    # 计划
    stop, tp1, tp2, plan_lines = propose_plan(direction, float(entry), float(current), k15, k1h)

    # 核验
    vr = verify_after(dt, float(entry), direction, float(stop), float(tp1), float(tp2))

    # 写报告
    outdir = Path('trading_signals') / '.learning_reports'
    outdir.mkdir(parents=True, exist_ok=True)
    md = []
    md.append(f'# 交易执行计划与核验 | trade#{tid}')
    md.append('')
    md.append(f'- 时间: {ts}  标的: {symbol}  方向: {direction.upper()}  杠杆: {lev}x  入场: ${entry:,.1f}')
    md.append('- 建议执行:')
    md.extend([f'  {ln}' for ln in plan_lines])
    md.append('')
    md.append('## 回放核验（5m近3天）')
    if 'error' in vr:
        md.append(f'- 无法获取K线：{vr["error"]}')
    else:
        hit = vr['hit']
        md.append(f'- MFE: {vr["mfe_pct"]:.2f}% | MAE: {vr["mae_pct"]:.2f}%')
        md.append(f'- 命中: TP1={fmt_ts(hit["tp1"])}, TP2={fmt_ts(hit["tp2"])}, SL={fmt_ts(hit["sl"])})')
    out = outdir / f'plan_verify_trade_{tid}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    out.write_text('\n'.join(md), encoding='utf-8')

    # 写观点
    summary = f"trade#{tid} 执行计划: SL ${stop:,.0f}, TP1 ${tp1:,.0f}, TP2 ${tp2:,.0f}; "
    if 'error' not in vr:
        summary += f"回放: MFE {vr['mfe_pct']:.2f}%, MAE {vr['mae_pct']:.2f}%"
    db.add_viewpoint(content=summary, timestamp=ts, source='plan', category='plan', tags=['plan','verify'], related_trade_id=tid)
    db.close()
    print(f"✓ 生成计划与核验: {out}")


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()

