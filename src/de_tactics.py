#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De. 战术模板

1) 整位阻力带挂单（Bracket Short）
   - 识别最近整千位（例如 90,000）构成的阻力带 [L, L+200]
   - 止损：L+588（De. 风格固定偏移）
   - 止盈：就近的重复数字位（例如 88,888），或按 1R

2) 确认多（Confirm Long）
   - 15m OTE 0.618–0.786 回撤区间
   - 5m 确认（针/吞没 + 放量）后入场
   - 止损：默认点距（persona），或最近摆动低点；RR≥1.2
"""
from __future__ import annotations
from typing import Dict, Optional, List
from statistics import mean


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


def _calc_fib_ote(last_swing_low: float, last_swing_high: float) -> Dict[str, float]:
    lo = min(last_swing_low, last_swing_high)
    hi = max(last_swing_low, last_swing_high)
    length = hi - lo
    return {
        'fib_618': hi - 0.618 * length,
        'fib_786': hi - 0.786 * length,
    }


def build_confirm_long(current_price: float,
                       k15: List[Dict], k5: List[Dict],
                       default_stop_pts: float = 400.0) -> Optional[Dict]:
    """构建一条“确认多”信号（简化版启用规则）：
    - 15m 近段 swing 推导 OTE 区间
    - 当前价格邻近/回踩 OTE；5m 出现小实体针/吞没 + 放量
    - 入场价格=当前价，止损=当前价-default_stop_pts；TP1/TP2=1R/2R
    - RR 以 1R/2R 计算，若 <1.2 则放弃
    """
    if not k15 or not k5:
        return None
    # 近若干根估算 swing
    last = k15[-50:]
    hi = max(c['high'] for c in last)
    lo = min(c['low'] for c in last)
    fib = _calc_fib_ote(lo, hi)
    f618, f786 = fib['fib_618'], fib['fib_786']
    # 邻近判断（0.2%）
    loz, hiz = min(f618, f786), max(f618, f786)
    in_zone = (loz * 0.998) <= current_price <= (hiz * 1.002)
    # 5m 确认（极简检测：最近3根内有下影较长或吞没，且成交量位于最近20根均量之上）
    vol = [c.get('volume', 0) or 0 for c in k5[-20:]] or [0]
    avgv = mean(vol) if vol else 0
    recent = k5[-3:]
    confirm = False
    for c in recent:
        body = abs(c['close'] - c['open'])
        lower_wick = c['open'] - c['low'] if c['open'] >= c['close'] else c['close'] - c['low']
        engulf = False
        if len(k5) >= 2:
            p = k5[-2]
            engulf = (c['close'] > p['open'] and c['open'] < p['close'])
        if (lower_wick > body * 1.5 or engulf) and c.get('volume', 0) >= (avgv * 1.05):
            confirm = True
            break
    if not (in_zone and confirm):
        return None
    entry = float(current_price)
    stop_loss = float(entry - default_stop_pts)
    take_profit_1 = float(entry + default_stop_pts)
    take_profit_2 = float(entry + 2 * default_stop_pts)
    rr = (take_profit_1 - entry) / (entry - stop_loss) if (entry - stop_loss) > 0 else 0
    if rr < 1.2:
        return None
    return {
        'type': 'long',
        'strength': 'medium',
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'entry_model': 'DeConfirmLong',
        'reason': '15m OTE 回撤 + 5m 反转确认（针/吞没+放量）',
        'stop_rule': 'fixed_pts_persona',
        'tp_rule': '1R/2R',
        'stop_distance_points': float(entry - stop_loss),
    }

