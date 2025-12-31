#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为最近N笔 De. 交易自动打“技术标签”（OTE/883/Vegas/VWAP/SR/Pinbar），
并写入观点表与学习报告，便于统计和胜率分析。
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_manager_trader import TraderDBManager
from generate_btc_de_signals import get_btc_kline_gateio, analyze_timeframe

def near(x, y, pct=0.2):
    try:
        return abs(x-y)/y*100 < pct
    except Exception:
        return False

def label_one(entry, direction, current_price, kl_15, kl_1h):
    labels = []
    # 分析 15m / 1h
    a15 = analyze_timeframe(kl_15, '15分钟', current_price)
    a1h = analyze_timeframe(kl_1h, '1小时', current_price)
    # OTE
    for a in (a15,a1h):
        if a and a.get('ote_analysis'):
            oa=a['ote_analysis']; f618=oa.get('fib_618'); f786=oa.get('fib_786')
            if f618 and f786:
                if entry>=min(f618,f786) and entry<=max(f618,f786):
                    labels.append('OTE')
                    break
                if near(entry,f618) or near(entry,f786):
                    labels.append('OTE邻近'); break
    # 883规则
    if direction=='short' and entry<88300: labels.append('883下空')
    if direction=='long' and entry>88300: labels.append('883上多')
    # Vegas
    for a in (a15,a1h):
        if a and a.get('ema_144') and a.get('ema_169'):
            lo=min(a['ema_144'],a['ema_169']); hi=max(a['ema_144'],a['ema_169'])
            if near(entry,lo) or near(entry,hi): labels.append('Vegas邻近'); break
    # VWAP
    for a in (a15,a1h):
        if a and a.get('vwap') and near(entry,a['vwap']):
            labels.append('VWAP邻近'); break
    # SR
    for a in (a15,a1h):
        if a and a.get('support_resistance'):
            sr=a['support_resistance']
            arr=(sr.get('resistance') or []) if direction=='short' else (sr.get('support') or [])
            if arr and min(abs(entry-x)/entry*100 for x in arr)<0.2: labels.append('SR邻近'); break
    return labels

def main():
    db=TraderDBManager('de')
    con=db._get_connection()
    rows=con.execute("SELECT id,timestamp,direction,entry_price FROM trade_records ORDER BY id DESC LIMIT 10").fetchall()
    if not rows:
        print('无交易记录'); return
    # 获取K线
    kl_15=get_btc_kline_gateio('15m',200)
    kl_1h=get_btc_kline_gateio('1h',200)
    current=kl_15[-1]['close'] if kl_15 else (kl_1h[-1]['close'] if kl_1h else None)
    for tid,ts,dirc,entry in rows:
        labels=label_one(entry, 'short' if dirc=='short' else 'long', current, kl_15, kl_1h)
        if labels:
            content=f"De.交易技术归因 | trade#{tid} | {dirc.upper()} | entry ${entry:,.0f} | 技术: {', '.join(labels)}"
            db.add_viewpoint(content=content,timestamp=ts,source='tech-label',category='label',tags=['tech','label'],related_trade_id=tid)
            print('✓',tid,labels)
        else:
            print('-',tid,'no-label')
    db.close()

if __name__=='__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()

