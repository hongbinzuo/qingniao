#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从最近对话中提取关键交易要点（"ML-lite" 规则 + 轻量特征），写入 trader_viewpoints，供学习与回放。

说明：
- 不依赖外部大模型与重型库，使用正则与关键短语集合做“弱监督抽取”。
- 提取：关键价位（整数/3~5位）、CME缺口/补缺、扫损/扫针、回踩/突破、情绪线索（OI/溢价）、方向倾向（多/空/陷阱）。
- 输出：一条聚合 viewpoint（source='auto-ml', category='learning'），内容含要点摘要与结构化标签。
"""
from __future__ import annotations
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager


KEY_PHRASES = {
    'gap': ['缺口', '补缺', 'CME'],
    'sweep': ['扫损', '扫针', '扫韭菜'],
    'retest': ['回踩', 'retest'],
    'breakout': ['突破', 'breakout'],
    'trap': ['陷阱'],
    'oi_up': ['oi升', 'OI升'],
    'cb_prem_neg': ['cb溢价还是负', 'CB溢价还是负', '负溢价'],
    'avg': ['均价'],
}


def extract_levels(text: str) -> list[int]:
    # 捕捉 3~5 位数字，过滤过小噪声；同时允许 4位+一位小数被近似为整数
    nums = re.findall(r"(?<!\d)(\d{3,5})(?!\d)", text)
    out = []
    for n in nums:
        try:
            v = int(n)
            if 500 <= v <= 99999:
                out.append(v)
        except Exception:
            continue
    # 去重排序
    out = sorted(list(dict.fromkeys(out)))
    return out


def hit_any(text: str, keys: list[str]) -> bool:
    return any(k in text for k in keys)


def main():
    db = TraderDBManager('de')
    con = db._get_connection()
    # 最近 120 条对话
    rows = con.execute("SELECT id, timestamp, COALESCE(trader_message,'') || ' ' || COALESCE(user_message,'') AS msg FROM conversations ORDER BY id DESC LIMIT 120").fetchall()
    if not rows:
        print('no conversations')
        return
    rows = rows[::-1]  # 按时间升序

    # 聚合文本
    text = '\n'.join(r[2] for r in rows if r[2])
    lv = extract_levels(text)

    flags = {k: hit_any(text, v) for k, v in KEY_PHRASES.items()}

    # 领域短语特化
    # 缺口区间提取（如 8815-8855）
    gaps = []
    for m in re.finditer(r"(\d{3,5})\s*[-~]\s*(\d{3,5})", text):
        try:
            a, b = int(m.group(1)), int(m.group(2))
            if 500 <= a <= 99999 and 500 <= b <= 99999:
                gaps.append((min(a, b), max(a, b)))
        except Exception:
            continue
    gaps = list(dict.fromkeys(gaps))

    # 简单方向倾向
    bias = []
    if flags['trap']:
        bias.append('多头陷阱/警惕上方阻力')
    if flags['retest']:
        bias.append('等待回踩确认')
    if flags['breakout']:
        bias.append('突破观察')
    if flags['oi_up'] and flags['cb_prem_neg']:
        bias.append('OI上升+负溢价（非现货抬价），谨慎追多')

    # 构造 viewpoint 文本
    lines = []
    lines.append('De. 对话要点（自动抽取）')
    lines.append('')
    # 关键价位
    if gaps:
        lines.append(f"- 缺口区间: {', '.join([f'{a}-{b}' for a,b in gaps])}")
    if lv:
        lines.append(f"- 关键价位: {', '.join(map(str, lv[-10:]))}")
    # 规则线索
    tags = []
    if flags['sweep']:
        tags.append('扫损/扫针')
    if flags['retest']:
        tags.append('回踩')
    if flags['breakout']:
        tags.append('突破')
    if flags['trap']:
        tags.append('陷阱')
    if flags['oi_up']:
        tags.append('OI↑')
    if flags['cb_prem_neg']:
        tags.append('CB负溢价')
    if tags:
        lines.append(f"- 线索: {', '.join(tags)}")
    if bias:
        lines.append(f"- 观点: {', '.join(bias)}")

    # 操作提示（根据出现频率生成）
    hint = []
    if gaps:
        hint.append('按缺口区间设置回补/回踩观察与风险位')
    if flags['sweep']:
        hint.append('注意“扫损位”位置（如 885 下方）避免被动触发')
    if flags['retest']:
        hint.append('回踩确认后再加仓/激活挂单')
    if flags['cb_prem_neg']:
        hint.append('负溢价+OI升，谨慎追多，优先等回踩')
    if hint:
        lines.append(f"- 提示: { '；'.join(hint) }")

    content = '\n'.join(lines)

    vid = db.add_viewpoint(
        content=content,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        source='auto-ml',
        category='learning',
        tags=['auto','ml','de','conversation','summary']
    )
    db.close()
    print('OK viewpoint_id=', vid)

if __name__=='__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()

