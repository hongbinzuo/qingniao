#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证ABU信号的合理性
"""
import sys
import json
from pathlib import Path
from typing import List, Dict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from db_manager_trader import TraderDBManager
from datetime import datetime

def validate_signal(signal: Dict) -> tuple[bool, List[str]]:
    """
    验证单个信号的合理性
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    entry = signal.get('entry') or signal.get('entry_price')
    stop_loss = signal.get('stop') or signal.get('stop_loss')
    tp1 = signal.get('tp1') or signal.get('take_profit_1')
    tp2 = signal.get('tp2') or signal.get('take_profit_2')
    direction = signal.get('type') or signal.get('direction', '').lower()
    symbol = signal.get('symbol', '')
    
    if not entry or entry <= 0:
        errors.append("入场价无效或为0")
    
    if not stop_loss or stop_loss <= 0:
        errors.append("止损价无效或为0")
    
    if not tp1 or tp1 <= 0:
        errors.append("止盈1无效或为0")
    
    # 检查价格是否相同
    if entry == stop_loss:
        errors.append(f"⚠️ 入场价与止损价相同: {entry}")
    
    if entry == tp1:
        errors.append(f"⚠️ 入场价与止盈1相同: {entry}")
    
    if stop_loss == tp1:
        errors.append(f"⚠️ 止损价与止盈1相同: {stop_loss}")
    
    # 检查方向逻辑
    if direction == 'long':
        if stop_loss >= entry:
            errors.append(f"⚠️ LONG信号：止损({stop_loss})应该低于入场({entry})")
        if tp1 <= entry:
            errors.append(f"⚠️ LONG信号：止盈1({tp1})应该高于入场({entry})")
        if tp2 and tp2 <= tp1:
            errors.append(f"⚠️ LONG信号：止盈2({tp2})应该高于止盈1({tp1})")
    elif direction == 'short':
        if stop_loss <= entry:
            errors.append(f"⚠️ SHORT信号：止损({stop_loss})应该高于入场({entry})")
        if tp1 >= entry:
            errors.append(f"⚠️ SHORT信号：止盈1({tp1})应该低于入场({entry})")
        if tp2 and tp2 >= tp1:
            errors.append(f"⚠️ SHORT信号：止盈2({tp2})应该低于止盈1({tp1})")
    
    # 检查风险收益比
    if entry and stop_loss and tp1:
        if direction == 'long':
            risk = abs(entry - stop_loss)
            reward = abs(tp1 - entry)
        else:  # short
            risk = abs(stop_loss - entry)
            reward = abs(entry - tp1)
        
        if risk > 0:
            rr_ratio = reward / risk
            if rr_ratio < 0.5:
                errors.append(f"⚠️ 风险收益比过低: {rr_ratio:.2f}:1")
            if rr_ratio > 10:
                errors.append(f"⚠️ 风险收益比异常高: {rr_ratio:.2f}:1")
        else:
            errors.append("⚠️ 风险为0（入场价与止损价相同）")
    
    return len(errors) == 0, errors


def check_duplicate_signals(signals: List[Dict]) -> List[Dict]:
    """检查重复信号"""
    duplicates = []
    seen = {}
    
    for sig in signals:
        key = (
            sig.get('symbol', ''),
            sig.get('type') or sig.get('direction', '').lower(),
            sig.get('entry') or sig.get('entry_price'),
            sig.get('stop') or sig.get('stop_loss'),
            sig.get('tp1') or sig.get('take_profit_1')
        )
        if key in seen:
            duplicates.append({
                'signal1': seen[key],
                'signal2': sig
            })
        else:
            seen[key] = sig
    
    return duplicates


def main():
    """主函数"""
    print("=" * 80)
    print("ABU信号合理性验证")
    print("=" * 80)
    print()
    
    # 从数据库获取最新信号
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 获取最新的信号时间
    latest_time = conn.execute("SELECT MAX(signal_time) FROM trading_signals").fetchone()[0]
    if not latest_time:
        print("❌ 数据库中没有信号")
        db.close()
        return
    
    print(f"📅 最新信号时间: {latest_time}")
    print()
    
    # 获取所有最新信号（同一时间的）
    rows = conn.execute("""
        SELECT symbol, signal_type, entry_price, stop_loss, take_profit_1, take_profit_2,
               entry_model, strength, risk_reward_ratio, COALESCE(score,0), COALESCE(notes,''),
               timeframe
        FROM trading_signals
        WHERE signal_time=?
        ORDER BY COALESCE(score,0) DESC, id DESC
    """, [latest_time]).fetchall()
    
    db.close()
    
    signals = []
    for r in rows:
        signals.append({
            'symbol': r[0],
            'type': r[1],
            'entry': r[2],
            'stop': r[3],
            'tp1': r[4],
            'tp2': r[5],
            'model': r[6],
            'strength': r[7],
            'rr': r[8],
            'score': r[9],
            'reason': r[10],
            'timeframe': r[11]
        })
    
    print(f"📊 信号总数: {len(signals)}")
    print()
    
    # 验证每个信号
    print("=" * 80)
    print("信号验证结果")
    print("=" * 80)
    print()
    
    invalid_count = 0
    for i, sig in enumerate(signals, 1):
        is_valid, errors = validate_signal(sig)
        
        if not is_valid:
            invalid_count += 1
            print(f"❌ 信号 {i}: {sig['symbol']} {sig['type'].upper()}")
            print(f"   入场: {sig['entry']}, 止损: {sig['stop']}, 止盈1: {sig['tp1']}, 止盈2: {sig.get('tp2', 'N/A')}")
            print(f"   评分: {sig['score']}, 时间框架: {sig.get('timeframe', 'N/A')}")
            for error in errors:
                print(f"   {error}")
            print()
    
    # 检查重复信号
    print("=" * 80)
    print("重复信号检查")
    print("=" * 80)
    print()
    
    duplicates = check_duplicate_signals(signals)
    if duplicates:
        print(f"⚠️  发现 {len(duplicates)} 组重复信号:")
        for dup in duplicates:
            s1 = dup['signal1']
            s2 = dup['signal2']
            print(f"   {s1['symbol']} {s1['type'].upper()}: Entry={s1['entry']}, SL={s1['stop']}, TP1={s1['tp1']}")
            print(f"   {s2['symbol']} {s2['type'].upper()}: Entry={s2['entry']}, SL={s2['stop']}, TP1={s2['tp1']}")
            print()
    else:
        print("✓ 未发现完全重复的信号")
        print()
    
    # 检查同一币种的多空信号
    print("=" * 80)
    print("同一币种的多空信号检查")
    print("=" * 80)
    print()
    
    symbol_signals = {}
    for sig in signals:
        symbol = sig['symbol']
        if symbol not in symbol_signals:
            symbol_signals[symbol] = []
        symbol_signals[symbol].append(sig)
    
    conflicts = []
    for symbol, sigs in symbol_signals.items():
        if len(sigs) > 1:
            longs = [s for s in sigs if s['type'].lower() == 'long']
            shorts = [s for s in sigs if s['type'].lower() == 'short']
            if longs and shorts:
                conflicts.append({
                    'symbol': symbol,
                    'longs': longs,
                    'shorts': shorts
                })
    
    if conflicts:
        print(f"⚠️  发现 {len(conflicts)} 个币种同时有多空信号:")
        for conflict in conflicts:
            print(f"   {conflict['symbol']}:")
            for sig in conflict['longs']:
                print(f"     LONG: Entry={sig['entry']}, SL={sig['stop']}, TP1={sig['tp1']}, Score={sig['score']}")
            for sig in conflict['shorts']:
                print(f"     SHORT: Entry={sig['entry']}, SL={sig['stop']}, TP1={sig['tp1']}, Score={sig['score']}")
            print()
    else:
        print("✓ 未发现同一币种的多空冲突")
        print()
    
    # 总结
    print("=" * 80)
    print("验证总结")
    print("=" * 80)
    print()
    print(f"总信号数: {len(signals)}")
    print(f"无效信号: {invalid_count}")
    print(f"有效信号: {len(signals) - invalid_count}")
    print(f"重复信号组: {len(duplicates)}")
    print(f"多空冲突币种: {len(conflicts)}")
    print()
    
    if invalid_count > 0 or duplicates or conflicts:
        print("❌ 发现信号质量问题，建议检查信号生成逻辑")
    else:
        print("✓ 所有信号验证通过")


if __name__ == '__main__':
    main()



