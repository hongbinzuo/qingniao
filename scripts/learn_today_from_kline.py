#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习今日K线与观点（De.）

做的事：
- 读取 data/btc_price_timeseries.duckdb 的 5m/15m/1h K线（近200根，覆盖当天）
- 复用系统的 analyze_timeframe（Vegas/OTE/VWAP/SR/FVG/OB）提取结构与特征
- 汇总今日 De. 对话中的关键价位（粗解析 3~5 位数字），与 SR/OTE 做对齐与偏差分析
- 生成学习报告到 trading_signals/.learning_reports/learn_today_YYYYMMDD.md，并写入 viewpoint 摘要

注意：
- 仅读取本地 DuckDB，不依赖外网；
- 数字简化规则：
  * 5位数 -> 原值（例 88888 -> 88888）
  * 4位数 -> *10（例 9044 -> 90440）
  * 3位数 -> *100（例 905 -> 90500, 896 -> 89600）
"""
from __future__ import annotations
import os, re, json
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Tuple
import duckdb
import sys

# src 路径
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_manager_trader import TraderDBManager  # type: ignore
from generate_btc_de_signals import analyze_timeframe  # type: ignore

TS_DB = str(Path('data') / 'btc_price_timeseries.duckdb')
OUTDIR = Path('trading_signals') / '.learning_reports'
OUTDIR.mkdir(parents=True, exist_ok=True)


def load_klines(tf: str, n: int = 200) -> List[Dict]:
    table = {
        '5m': 'btc_price_5m',
        '15m': 'btc_price_15m',
        '1h': 'btc_price_1h',
    }[tf]
    con = duckdb.connect(TS_DB, read_only=True)
    rows = con.execute(
        f"SELECT timestamp, open, high, low, close, volume FROM {table} ORDER BY timestamp DESC LIMIT ?",
        [n],
    ).fetchall()
    con.close()
    rows.reverse()
    kl = []
    for ts, o, h, l, c, v in rows:
        kl.append({'timestamp': int(ts), 'open': float(o), 'high': float(h), 'low': float(l), 'close': float(c), 'volume': float(v or 0.0)})
    return kl


def parse_levels_from_conversations(the_day: str) -> Tuple[List[int], List[Tuple[str, int]]]:
    """粗提取当天对话中的3~5位数字并归一化为价格级别。返回（levels, raw_items）。"""
    db = TraderDBManager('de')
    con = db._get_connection()
    rows = con.execute(
        "SELECT timestamp, trader_message FROM conversations WHERE date(timestamp)=? ORDER BY timestamp",
        [the_day],
    ).fetchall()
    db.close()

    found: List[int] = []
    tagged: List[Tuple[str, int]] = []
    for ts, msg in rows:
        if not msg:
            continue
        for m in re.finditer(r"(?<!\d)(\d{3,5})(?!\d)", str(msg)):
            num = int(m.group(1))
            if 10000 <= num <= 99999:
                val = num
            elif 1000 <= num <= 9999:
                val = num * 10
            elif 100 <= num <= 999:
                val = num * 100
            else:
                continue
            if 60000 <= val <= 120000:  # 大致过滤
                found.append(val)
                tagged.append((ts, val))
    # 去重保序
    uniq: List[int] = []
    seen = set()
    for v in found:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq, tagged


def describe_alignment(levels: List[int], sr: Dict, ote: Dict, current: float) -> List[str]:
    lines = []
    sup = (sr or {}).get('support') or []
    res = (sr or {}).get('resistance') or []
    fib_618 = (ote or {}).get('fib_618'); fib_786 = (ote or {}).get('fib_786')
    for lv in levels:
        nearest = None; dmin = 1e9; kind = ''
        for s in sup:
            d = abs(lv - s)/lv*100
            if d < dmin:
                dmin=d; nearest=s; kind='support'
        for r in res:
            d = abs(lv - r)/lv*100
            if d < dmin:
                dmin=d; nearest=r; kind='resistance'
        ote_hit = ''
        if fib_618 and fib_786:
            lo=min(fib_618,fib_786); hi=max(fib_618,fib_786)
            if lo<=lv<=hi: ote_hit='(OTE区间内)'
        pos = '上方' if current>lv else '下方'
        if nearest is not None:
            lines.append(f"- 观点位 {lv:,.0f} → 最近{kind} {nearest:,.0f} | 偏差 {dmin:.2f}% | 当前价在其{pos} {ote_hit}")
        else:
            lines.append(f"- 观点位 {lv:,.0f} → 无SR匹配 | 当前价在其{pos} {ote_hit}")
    return lines[:12]


def main():
    today = date.today().strftime('%Y-%m-%d')
    # 取近200根做特征，current_price 用15m收盘
    k5 = load_klines('5m', 200)
    k15 = load_klines('15m', 200)
    k1h = load_klines('1h', 200)
    if not k15:
        print('❌ 无15m数据，终止')
        return
    current = k15[-1]['close']

    a5 = analyze_timeframe(k5, '5分钟', current) if k5 else None
    a15 = analyze_timeframe(k15, '15分钟', current)
    a1h = analyze_timeframe(k1h, '1小时', current) if k1h else None

    # 解析当天观点数字
    levels, tagged = parse_levels_from_conversations(today)

    # 组装报告
    lines: List[str] = []
    lines.append('# 今日K线学习（De.）')
    lines.append('')
    lines.append(f'**日期**: {today}  |  **当前价(15m收盘)**: ${current:,.2f}')
    lines.append('')
    # 结构概览
    def tf_snapshot(a: Dict, name: str) -> List[str]:
        if not a:
            return [f'- {name}: 无数据']
        out = [f'## {name} 结构快照']
        e144=a.get('ema_144'); e169=a.get('ema_169'); vwap=a.get('vwap'); rsi=a.get('rsi')
        if e144 and e169:
            lo=min(e144,e169); hi=max(e144,e169)
            pos='上方' if current>hi else ('下方' if current<lo else '通道内')
            out.append(f"- Vegas: EMA144=${e144:,.0f}, EMA169=${e169:,.0f}（{pos}）")
        if vwap:
            out.append(f"- VWAP: ${vwap:,.0f}（价格在其{'上方' if current>vwap else '下方'}）")
        if rsi is not None:
            out.append(f"- RSI: {rsi:.1f}")
        sr=(a.get('support_resistance') or {})
        sup=sr.get('support') or []; res=sr.get('resistance') or []
        if sup: out.append("- 支撑: "+', '.join(f"${x:,.0f}" for x in sup[:3]))
        if res: out.append("- 阻力: "+', '.join(f"${x:,.0f}" for x in res[:3]))
        oa=a.get('ote_analysis') or {}
        f618=oa.get('fib_618'); f786=oa.get('fib_786')
        if f618 and f786:
            z = '内' if (oa.get('in_ote_zone')) else ('上方' if oa.get('above_786') else ('下方' if oa.get('below_618') else '附近'))
            out.append(f"- OTE 618=${f618:,.0f} / 786=${f786:,.0f}（价格在其{z}）")
        return out

    lines += tf_snapshot(a1h, '1小时')
    lines.append('')
    lines += tf_snapshot(a15, '15分钟')
    lines.append('')

    # 观点数字对齐
    if levels:
        lines.append('## 观点价位与结构对齐')
        lines += describe_alignment(levels, (a15 or {}).get('support_resistance'), (a15 or {}).get('ote_analysis'), current)
        lines.append('')

    # 简要学习结论（基于15m/1h趋势+观点）
    concl: List[str] = []
    def bias(a: Dict) -> str:
        if not a or not a.get('ema_144') or not a.get('ema_169'):
            return 'unknown'
        lo=min(a['ema_144'], a['ema_169']); hi=max(a['ema_144'], a['ema_169'])
        return '多' if current>hi else ('空' if current<lo else '震荡')
    b15=bias(a15); b1h=bias(a1h)
    concl.append(f"- 趋势偏向：15m={b15} / 1h={b1h}；若分歧，以1h为主、5m作确认。")
    if a15 and a15.get('ote_analysis'):
        concl.append("- 纪律：优先 OTE 0.618–0.786 回踩/反抽 + 5m确认（针/吞没+放量）再入场。")
    if levels:
        # 若观点位与SR偏差 <0.2% 视为显著支撑/阻力
        sr15=(a15 or {}).get('support_resistance') or {}
        signif=[]
        for lv in levels:
            arr=(sr15.get('support') or [])+(sr15.get('resistance') or [])
            for x in arr:
                if abs(lv-x)/lv*100<0.2:
                    signif.append(lv); break
        if signif:
            uniq=list(dict.fromkeys(signif))
            concl.append("- 关键价位："+", ".join(f"${x:,.0f}" for x in uniq[:6])+"（与SR高度一致）")
    lines.append('## 学习结论')
    lines += concl
    lines.append('')

    # 输出
    fname = OUTDIR / f"learn_today_{today.replace('-','')}.md"
    fname.write_text("\n".join(lines), encoding='utf-8')

    # 记录 viewpoint 摘要
    try:
        db = TraderDBManager('de')
        summary = f"今日学习 {today} | 15m/1h 趋势 {b15}/{b1h} | 关键位: "+ \
                  ", ".join(f"${x:,.0f}" for x in (levels[:5] if levels else []))
        db.add_viewpoint(content=summary, timestamp=f"{today} 23:59:00", source='learn', category='learning', tags=['learn','kline','de'])
        db.close()
    except Exception:
        pass

    print(f"✓ 学习报告已写入: {fname}")


if __name__ == '__main__':
    main()

