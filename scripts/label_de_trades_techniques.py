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

def _ensure_trade_labels_column(conn):
    """确保 trade_records 存在 tech_labels 列（TEXT, JSON字符串）。"""
    try:
        cols = conn.execute("PRAGMA table_info(trade_records)").fetchall()
        names = [c[1] for c in cols]
        if 'tech_labels' not in names:
            conn.execute("ALTER TABLE trade_records ADD COLUMN tech_labels TEXT")
            conn.commit()
    except Exception:
        # 忽略错误（DuckDB旧版可能不支持，或者表不存在）
        pass


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

def get_combo_stats(n: int = 20):
    """聚合最近 n 笔交易的“技术组合”胜率/均值/尾部风险。
    返回: [ { 'combo': 'OTE+SR邻近+Vegas邻近', 'count': 7, 'winrate': 0.71,
             'avg_profit_pct': 1.23, 'tail_risk_pct': -2.8 }, ... ]
    """
    db = TraderDBManager('de')
    con = db._get_connection()
    _ensure_trade_labels_column(con)
    rows = con.execute(
        "SELECT id,direction,profit_pct,tech_labels FROM trade_records ORDER BY id DESC LIMIT ?",
        [int(n)]
    ).fetchall()
    stats = {}
    for tid, direction, profit, labels_json in rows:
        try:
            if not labels_json:
                continue
            labels = []
            # 允许 labels_json 既可能是 JSON 字符串也可能是逗号分隔文本
            import json as _json
            try:
                obj = _json.loads(labels_json)
                if isinstance(obj, list):
                    labels = [str(x) for x in obj]
                elif isinstance(obj, dict) and 'labels' in obj:
                    labels = [str(x) for x in obj.get('labels') or []]
            except Exception:
                labels = [x.strip() for x in str(labels_json).split(',') if x.strip()]
            if not labels:
                continue
            combo = '+'.join(sorted(set(labels)))
            s = stats.setdefault(combo, {'combo': combo, 'count': 0, 'wins': 0, 'profits': []})
            s['count'] += 1
            try:
                p = float(profit) if profit is not None else 0.0
            except Exception:
                p = 0.0
            s['profits'].append(p)
            if p > 0:
                s['wins'] += 1
        except Exception:
            continue
    # 汇总
    out = []
    for combo, s in stats.items():
        if s['count'] <= 0:
            continue
        profits = s['profits']
        avg = sum(profits) / len(profits) if profits else 0.0
        # 粗略尾部风险：亏损分布的10分位数
        tail = 0.0
        if profits:
            negs = sorted([x for x in profits if x < 0])
            if negs:
                import math
                k = max(0, int(math.floor(0.1 * (len(negs) - 1))))
                tail = negs[k]
        out.append({
            'combo': combo,
            'count': s['count'],
            'winrate': s['wins'] / s['count'],
            'avg_profit_pct': avg,
            'tail_risk_pct': tail,
        })
    # 排序：优先最近命中多且胜率高
    out.sort(key=lambda x: (x['count'], x['winrate'], x['avg_profit_pct']), reverse=True)
    db.close()
    return out


def format_combo_snapshot(ns=(20, 50)):
    """格式化“最近N笔技术组合胜率快照”的 Markdown 行。"""
    lines = []
    try:
        for n in ns:
            stats = get_combo_stats(n)
            if not stats:
                continue
            lines.append(f"- 最近{n}笔 Top 5 组合：")
            for row in stats[:5]:
                lines.append(
                    f"  - {row['combo']} | 次数 {row['count']} | 胜率 {row['winrate']*100:.0f}% | 平均收益 {row['avg_profit_pct']:.2f}% | 尾部风险 {row['tail_risk_pct']:.2f}%"
                )
    except Exception:
        return []
    return lines


def main():
    db=TraderDBManager('de')
    con=db._get_connection()
    _ensure_trade_labels_column(con)
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
            # 将标签持久化写回 trade_records.tech_labels
            try:
                import json as _json
                con.execute("UPDATE trade_records SET tech_labels=? WHERE id=?", [_json.dumps(labels, ensure_ascii=False), tid])
                con.commit()
            except Exception:
                pass
            print('✓',tid,labels)
        else:
            print('-',tid,'no-label')
    db.close()

if __name__=='__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()
