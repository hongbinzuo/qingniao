#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De. 战术模板：整位阻力带挂单（Bracket Short）

- 识别最近整千位（例如 90,000）构成的阻力带 [L, L+200]
- 止损：L+588（De. 风格固定偏移）
- 止盈：就近的重复数字位（例如 88,888），或按 1R
"""
from __future__ import annotations
from typing import Dict, Optional


def _nearest_thousand(price: float) -> int:
    return int(price // 1000) * 1000


def _repeated_digit_below(thousand: int) -> Optional[int]:
    """返回低于给定整千的“重复数字位”作为战术止盈。例如 90k -> 88,888。"""
    if thousand < 20000:
        return None
    lead = int(str(thousand // 1000)[0])  # 9 for 90k
    rep = lead - 1
    if rep <= 0:
        return None
    return int(str(rep) * 5) * 1  # 88888 之类


def build_bracket_short(current_price: float) -> Dict:
    """构建一条“整位阻力带挂空”战术信号（使用中点用于RR与入库）。"""
    L = _nearest_thousand(current_price)
    entry_lower = float(L)
    entry_upper = float(L + 200)
    entry_mid = float(L + 100)
    stop_loss = float(L + 588)
    tp_rep = _repeated_digit_below(L)

    # 若无法构造重复数字，退化为 1R 止盈
    risk = stop_loss - entry_mid
    take_profit_1 = float(entry_mid - risk) if tp_rep is None else float(tp_rep)
    take_profit_2 = float(entry_mid - risk * 2)

    return {
        'type': 'short',
        'strength': 'strong',
        'entry': entry_mid,
        'entry_lower': entry_lower,
        'entry_upper': entry_upper,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'entry_model': 'DeBracketShort',
        'reason': f'整位阻力带挂单 [{int(entry_lower):,}-{int(entry_upper):,}] / 止损 {int(stop_loss):,}',
        'stop_rule': 'fixed_offset_+588',
        'tp_rule': 'repeated_digit_below' if tp_rep is not None else '1R/2R',
        'stop_distance_points': float(risk),
        'bracket_note': '挂单区间，入库用中点作为entry（报告保留区间）',
    }

