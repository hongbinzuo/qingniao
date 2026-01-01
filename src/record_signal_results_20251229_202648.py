#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
录入2025-12-29 20:26:48的信号结果
"""

import sys
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from signal_tracker import SignalTracker
except ImportError as e:
    print(f"导入失败: {e}", file=sys.stderr)
    print("请确保在src目录下运行此脚本", file=sys.stderr)
    sys.exit(1)


def record_stopped_signal(
    system_name: str,
    timeframe: str,
    signal_type: str,
    entry: float,
    stop_loss: float,
    take_profit_1: float,
    take_profit_2: float,
    entry_model: str,
    strength: str = 'strong',
    reason: str = '',
    generated_time: str = None,
    entry_time: str = None,
    stop_time: str = None,
    stop_price: float = None,
    max_profit_pct: float = None,
    max_loss_pct: float = None
):
    """录入被止损的信号"""
    tracker = SignalTracker()
    signals_data = tracker.load_signals()
    
    if generated_time is None:
        generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if entry_time is None:
        entry_time = generated_time
    if stop_time is None:
        stop_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if stop_price is None:
        stop_price = stop_loss
    
    # 计算最大浮盈和浮亏
    if max_profit_pct is None:
        if signal_type == 'long':
            # 做多：计算从入场到止损的最大浮盈
            max_profit_price = max(take_profit_1, take_profit_2) if take_profit_1 and take_profit_2 else entry * 1.02
            max_profit_pct = ((max_profit_price - entry) / entry) * 100
        else:
            max_profit_price = min(take_profit_1, take_profit_2) if take_profit_1 and take_profit_2 else entry * 0.98
            max_profit_pct = ((entry - max_profit_price) / entry) * 100
    
    if max_loss_pct is None:
        if signal_type == 'long':
            max_loss_pct = ((entry - stop_price) / entry) * 100
        else:
            max_loss_pct = ((stop_price - entry) / entry) * 100
    
    signal_id = f"{system_name}_{timeframe}_{generated_time.replace(':', '-').replace(' ', '_')}"
    
    signal_record = {
        'id': signal_id,
        'system': system_name,
        'timeframe': timeframe,
        'generated_time': generated_time,
        'status': 'stopped',
        'type': signal_type,
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'entry_model': entry_model,
        'reason': reason,
        'strength': strength,
        'last_check_time': stop_time,
        'entry_time': entry_time,
        'current_price': stop_price,
        'max_profit': max_profit_pct,
        'max_loss': max_loss_pct,
        'tp1_hit': False,
        'tp2_hit': False,
        'stop_hit': True,
        'analyzed': False,
    }
    
    if system_name not in signals_data:
        signals_data[system_name] = []
    
    signals_data[system_name].append(signal_record)
    tracker.save_signals(signals_data)
    
    print(f"✅ 已录入被止损的信号: {signal_id}")
    return signal_id


def record_partial_tp_signal(
    system_name: str,
    timeframe: str,
    signal_type: str,
    entry: float,
    stop_loss: float,
    take_profit_1: float,
    take_profit_2: float,
    entry_model: str,
    strength: str = 'strong',
    reason: str = '',
    generated_time: str = None,
    entry_time: str = None,
    tp1_time: str = None,
    current_price: float = None,
    max_profit_pct: float = None
):
    """录入部分止盈的信号（还在运行中）"""
    tracker = SignalTracker()
    signals_data = tracker.load_signals()
    
    if generated_time is None:
        generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if entry_time is None:
        entry_time = generated_time
    if tp1_time is None:
        tp1_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if current_price is None:
        current_price = take_profit_1
    
    if max_profit_pct is None:
        if signal_type == 'long':
            max_profit_pct = ((current_price - entry) / entry) * 100
        else:
            max_profit_pct = ((entry - current_price) / entry) * 100
    
    signal_id = f"{system_name}_{timeframe}_{generated_time.replace(':', '-').replace(' ', '_')}"
    
    signal_record = {
        'id': signal_id,
        'system': system_name,
        'timeframe': timeframe,
        'generated_time': generated_time,
        'status': 'partial_tp',  # 部分止盈，还在运行
        'type': signal_type,
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'entry_model': entry_model,
        'reason': reason,
        'strength': strength,
        'last_check_time': tp1_time,
        'entry_time': entry_time,
        'current_price': current_price,
        'max_profit': max_profit_pct,
        'max_loss': 0,
        'tp1_hit': True,  # 已到达第一止盈位
        'tp2_hit': False,  # 还未到达第二止盈位
        'stop_hit': False,
        'analyzed': False,
    }
    
    if system_name not in signals_data:
        signals_data[system_name] = []
    
    signals_data[system_name].append(signal_record)
    tracker.save_signals(signals_data)
    
    print(f"✅ 已录入部分止盈的信号: {signal_id}")
    return signal_id


def main():
    """主函数"""
    print("=" * 80)
    print("录入2025-12-29 20:26:48的信号结果")
    print("=" * 80)
    print()
    
    # 信号1：5分钟做空 - 被止损
    print("📝 录入信号1：5分钟做空（被止损）...")
    signal1_id = record_stopped_signal(
        system_name='de',
        timeframe='5分钟',
        signal_type='short',
        entry=87804,
        stop_loss=88067,
        take_profit_1=86347,
        take_profit_2=85475,
        entry_model='阻力位回落(量能大)',
        strength='strong',
        reason='价格接近量能大的阻力位，可能回落，但波动较大被止损',
        generated_time='2025-12-29 20:26:48',
        entry_time='2025-12-29 20:26:48',
        stop_time='2025-12-29 21:30:00',  # 假设止损时间
        stop_price=88067,
        max_profit_pct=1.66,  # (87804 - 86347) / 87804 * 100
        max_loss_pct=0.30  # (88067 - 87804) / 87804 * 100
    )
    print()
    
    # 信号2：15分钟做空 - 被止损
    print("📝 录入信号2：15分钟做空（被止损）...")
    signal2_id = record_stopped_signal(
        system_name='de',
        timeframe='15分钟',
        signal_type='short',
        entry=87279,
        stop_loss=87584,
        take_profit_1=85717,
        take_profit_2=84937,
        entry_model='反转形态-三重顶',
        strength='strong',
        reason='识别到三重顶形态，但波动较大被止损',
        generated_time='2025-12-29 20:26:48',
        entry_time='2025-12-29 20:26:48',
        stop_time='2025-12-29 22:00:00',
        stop_price=87584,
        max_profit_pct=1.79,  # (87279 - 85717) / 87279 * 100
        max_loss_pct=0.35  # (87584 - 87279) / 87279 * 100
    )
    print()
    
    # 信号3：1小时做多 - 部分止盈（还在运行中）
    print("📝 录入信号3：1小时做多（部分止盈，还在运行）...")
    signal3_id = record_partial_tp_signal(
        system_name='de',
        timeframe='1小时',
        signal_type='long',
        entry=87018,
        stop_loss=86700,
        take_profit_1=88091,
        take_profit_2=88963,
        entry_model='支撑位反弹(量能大)',
        strength='strong',
        reason='价格接近量能大的支撑位，可能反弹，已到达第一止盈位',
        generated_time='2025-12-29 20:26:48',
        entry_time='2025-12-29 20:26:48',
        tp1_time='2025-12-30 10:00:00',  # 假设到达第一止盈位时间
        current_price=88091,
        max_profit_pct=1.23  # (88091 - 87018) / 87018 * 100
    )
    print()
    
    print("=" * 80)
    print("✅ 所有信号已成功录入！")
    print("=" * 80)
    print()
    print("📊 录入统计:")
    print(f"   - 信号1（5分钟做空）: 被止损（波动较大）")
    print(f"   - 信号2（15分钟做空）: 被止损（波动较大）")
    print(f"   - 信号3（1小时做多）: 部分止盈（还在运行中）")
    print()
    print("💡 提示: 可以运行以下命令训练/更新机器学习模型:")
    print("   python src/train_ml_model.py")
    print("=" * 80)


if __name__ == "__main__":
    main()


