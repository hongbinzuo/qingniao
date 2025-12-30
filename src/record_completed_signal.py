#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动录入已完成的交易信号
用于将已成功完成的交易信号记录到系统中，供机器学习训练使用
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
    print("请确保在src目录下运行此脚本，或在项目根目录运行: python src/record_completed_signal.py", file=sys.stderr)
    sys.exit(1)


def record_completed_signal(
    system_name: str,
    timeframe: str,
    signal_type: str,  # 'long' or 'short'
    entry: float,
    stop_loss: float,
    take_profit_1: float,
    take_profit_2: float,
    entry_model: str,
    strength: str = 'strong',
    reason: str = '',
    generated_time: str = None,
    entry_time: str = None,
    completion_time: str = None,
    max_profit_pct: float = None
):
    """
    记录已完成的信号
    
    Args:
        system_name: 系统名称（如 'de', 'meng'）
        timeframe: 时间框架（如 '5分钟', '15分钟'）
        signal_type: 信号类型（'long' 或 'short'）
        entry: 入场价
        stop_loss: 止损价
        take_profit_1: 第一止盈价
        take_profit_2: 第二止盈价
        entry_model: 入场模型
        strength: 信号强度（'strong', 'medium', 'weak'）
        reason: 入场原因
        generated_time: 信号生成时间（格式：'YYYY-MM-DD HH:MM:SS'），默认使用当前时间
        entry_time: 实际入场时间，默认使用generated_time
        completion_time: 完成时间，默认使用当前时间
        max_profit_pct: 最大浮盈百分比，如果为None则自动计算
    """
    tracker = SignalTracker()
    signals_data = tracker.load_signals()
    
    # 设置默认时间
    if generated_time is None:
        generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if entry_time is None:
        entry_time = generated_time
    if completion_time is None:
        completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 计算最大浮盈（如果未提供）
    if max_profit_pct is None:
        if signal_type == 'long':
            # 做多：最大浮盈是第二止盈位相对于入场价的涨幅
            max_profit_pct = ((take_profit_2 - entry) / entry) * 100
        else:  # short
            # 做空：最大浮盈是入场价相对于第二止盈位的跌幅
            max_profit_pct = ((entry - take_profit_2) / entry) * 100
    
    # 创建信号ID
    signal_id = f"{system_name}_{timeframe}_{generated_time.replace(':', '-').replace(' ', '_')}"
    
    # 创建信号记录（标记为已完成）
    signal_record = {
        'id': signal_id,
        'system': system_name,
        'timeframe': timeframe,
        'generated_time': generated_time,
        'status': 'full_tp',  # 标记为全部止盈（成功）
        'type': signal_type,
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'entry_model': entry_model,
        'reason': reason,
        'strength': strength,
        # 追踪字段
        'last_check_time': completion_time,
        'entry_time': entry_time,
        'current_price': take_profit_2,  # 完成时的价格是第二止盈位
        'max_profit': max_profit_pct,
        'max_loss': 0,  # 成功的信号最大浮亏为0（或接近0）
        'tp1_hit': True,  # 已触及第一止盈位
        'tp2_hit': True,  # 已触及第二止盈位
        'stop_hit': False,  # 未触及止损位
        'analyzed': False,  # 标记为未分析，等待性能分析
    }
    
    # 初始化系统信号列表
    if system_name not in signals_data:
        signals_data[system_name] = []
    
    # 添加信号
    signals_data[system_name].append(signal_record)
    
    # 保存
    tracker.save_signals(signals_data)
    
    print(f"✅ 已成功记录已完成的信号")
    print(f"   ID: {signal_id}")
    print(f"   系统: {system_name}")
    print(f"   时间框架: {timeframe}")
    print(f"   类型: {'做多' if signal_type == 'long' else '做空'}")
    print(f"   入场: ${entry:,.0f}")
    print(f"   止损: ${stop_loss:,.0f}")
    print(f"   止盈1: ${take_profit_1:,.0f} ✅")
    print(f"   止盈2: ${take_profit_2:,.0f} ✅")
    print(f"   模型: {entry_model}")
    print(f"   最大浮盈: {max_profit_pct:.2f}%")
    print(f"   状态: 全部止盈（成功）")
    print()
    print(f"💡 提示: 可以运行以下命令训练/更新机器学习模型:")
    print(f"   python src/train_ml_model.py")
    
    return signal_id


def main():
    """主函数 - 从用户提供的信号信息录入"""
    # 根据用户提供的信息录入信号
    # 生成时间: 2025-12-28 09:45:27
    # 当前价格: $87,828.00（信号生成时的价格）
    # 入场: $87,740
    # 止损: $87,400
    # 止盈: $87,960 (50%) / $88,223 (50%)
    # 模型: Vegas通道突破
    # 理由: 价格突破Vegas通道后，Vegas成为支撑，回踩不破做多
    
    print("=" * 80)
    print("录入已完成的BTC交易信号")
    print("=" * 80)
    print()
    
    # 解析用户提供的信息
    signal_id = record_completed_signal(
        system_name='de',
        timeframe='5分钟',
        signal_type='long',
        entry=87740,
        stop_loss=87400,
        take_profit_1=87960,
        take_profit_2=88223,
        entry_model='Vegas通道突破',
        strength='strong',
        reason='价格突破Vegas通道后，Vegas成为支撑，回踩不破做多（大阳K线，不着急止盈）',
        generated_time='2025-12-28 09:45:27',
        entry_time='2025-12-28 09:45:27',  # 假设在信号生成时入场
        completion_time='2025-12-28 10:30:00',  # 假设在信号生成后45分钟完成（实际时间需要用户提供）
    )
    
    print("=" * 80)
    print("录入完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()



