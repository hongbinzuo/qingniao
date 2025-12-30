#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
录入错过的信号（方向正确但挂单价格不合理导致未接到）
用于机器学习训练，标记为特殊失败案例
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
    print("请确保在src目录下运行此脚本，或在项目根目录运行: python src/record_missed_signal.py", file=sys.stderr)
    sys.exit(1)


def record_missed_signal(
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
    current_price_at_generation: float = None,
    actual_price_movement: str = '',  # 描述实际价格走势
    why_missed: str = '挂单价格不合理，价格未到达入场价'
):
    """
    记录错过的信号（方向正确但未接到）
    
    Args:
        system_name: 系统名称（如 'de', 'meng'）
        timeframe: 时间框架（如 '5分钟', '15分钟'）
        signal_type: 信号类型（'long' 或 'short'）
        entry: 入场价（挂单价格）
        stop_loss: 止损价
        take_profit_1: 第一止盈价
        take_profit_2: 第二止盈价
        entry_model: 入场模型
        strength: 信号强度（'strong', 'medium', 'weak'）
        reason: 入场原因
        generated_time: 信号生成时间（格式：'YYYY-MM-DD HH:MM:SS'），默认使用当前时间
        current_price_at_generation: 信号生成时的当前价格
        actual_price_movement: 实际价格走势描述
        why_missed: 为什么错过（默认：挂单价格不合理）
    """
    tracker = SignalTracker()
    signals_data = tracker.load_signals()
    
    # 设置默认时间
    if generated_time is None:
        generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 创建信号ID
    signal_id = f"{system_name}_{timeframe}_{generated_time.replace(':', '-').replace(' ', '_')}"
    
    # 计算如果入场的话，可能的盈亏
    # 假设价格最终到达了止盈位（因为方向正确）
    if signal_type == 'long':
        # 做多：如果价格到达止盈位，计算潜在盈利
        potential_profit_pct = ((take_profit_2 - entry) / entry) * 100 if entry > 0 else 0
        # 计算入场价与生成时价格的差距（做多时，入场价应该低于或接近当前价格）
        if current_price_at_generation:
            # 入场价低于当前价格，差距为正（表示需要回调）
            entry_distance_pct = ((current_price_at_generation - entry) / current_price_at_generation) * 100
        else:
            entry_distance_pct = None
    else:  # short
        # 做空：如果价格到达止盈位，计算潜在盈利
        potential_profit_pct = ((entry - take_profit_2) / entry) * 100 if entry > 0 else 0
        # 计算入场价与生成时价格的差距（做空时，入场价应该高于或接近当前价格）
        if current_price_at_generation:
            # 入场价高于当前价格，差距为正（表示需要反弹）
            entry_distance_pct = ((entry - current_price_at_generation) / current_price_at_generation) * 100
        else:
            entry_distance_pct = None
    
    # 创建信号记录（标记为特殊失败：方向正确但未接到）
    signal_record = {
        'id': signal_id,
        'system': system_name,
        'timeframe': timeframe,
        'generated_time': generated_time,
        'status': 'missed',  # 新状态：错过（方向正确但未接到）
        'type': signal_type,
        'entry': entry,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'entry_model': entry_model,
        'reason': reason,
        'strength': strength,
        # 追踪字段
        'last_check_time': generated_time,
        'entry_time': None,  # 未入场
        'current_price': current_price_at_generation or entry,
        'max_profit': potential_profit_pct,  # 潜在最大盈利
        'max_loss': 0,  # 未入场，无损失
        'tp1_hit': False,  # 未入场，未触及
        'tp2_hit': False,  # 未入场，未触及
        'stop_hit': False,  # 未入场，未触及止损
        # 特殊字段
        'missed_reason': why_missed,
        'entry_distance_pct': entry_distance_pct,  # 入场价与生成时价格的差距
        'actual_price_movement': actual_price_movement,  # 实际价格走势
        'direction_correct': True,  # 标记方向正确
        'potential_profit_pct': potential_profit_pct,  # 潜在盈利百分比
        'analyzed': False,
    }
    
    # 初始化系统信号列表
    if system_name not in signals_data:
        signals_data[system_name] = []
    
    # 添加信号
    signals_data[system_name].append(signal_record)
    
    # 保存
    tracker.save_signals(signals_data)
    
    print("=" * 80)
    print("✅ 已成功记录错过的信号（方向正确但未接到）")
    print("=" * 80)
    print(f"   ID: {signal_id}")
    print(f"   系统: {system_name}")
    print(f"   时间框架: {timeframe}")
    print(f"   类型: {'做多' if signal_type == 'long' else '做空'} ({strength})")
    print(f"   生成时间: {generated_time}")
    if current_price_at_generation:
        print(f"   生成时价格: ${current_price_at_generation:,.2f}")
        if entry_distance_pct:
            print(f"   入场价差距: {abs(entry_distance_pct):.2f}% ({'高于' if entry_distance_pct < 0 else '低于'}当前价格)")
    print(f"   入场价: ${entry:,.0f}")
    print(f"   止损: ${stop_loss:,.0f}")
    print(f"   止盈1: ${take_profit_1:,.0f}")
    print(f"   止盈2: ${take_profit_2:,.0f}")
    print(f"   模型: {entry_model}")
    print(f"   潜在盈利: {potential_profit_pct:.2f}% (如果入场)")
    print(f"   错过原因: {why_missed}")
    if actual_price_movement:
        print(f"   实际走势: {actual_price_movement}")
    print(f"   状态: 错过（方向正确但未接到）")
    print()
    print("💡 提示:")
    print("   - 此信号将用于机器学习训练，标记为'方向正确但入场价设置不合理'的失败案例")
    print("   - 可以运行以下命令训练/更新机器学习模型:")
    print("     python src/train_ml_model.py")
    print("=" * 80)
    
    return signal_id


def main():
    """主函数 - 录入早上9点的15分钟做多信号"""
    print("=" * 80)
    print("录入错过的信号（方向正确但挂单价格不合理）")
    print("=" * 80)
    print()
    
    # 根据用户提供的信息录入信号
    # 15分钟信号
    # 做多 (强)
    # 入场: $87,702
    # 止损: $87,400 ✅ [基于实时订单簿] (0.34%)
    # 止盈: $89,480 (50%) / $90,368 (50%)
    # 模型: 反转形态-三重底
    # 生成时间: 早上9点附近（假设是2025-12-29 09:00:00）
    # 问题: 入场价$87,702，但价格根本没有到达这个位置
    
    signal_id = record_missed_signal(
        system_name='de',
        timeframe='15分钟',
        signal_type='long',
        entry=87702,
        stop_loss=87400,
        take_profit_1=89480,
        take_profit_2=90368,
        entry_model='反转形态-三重底',
        strength='strong',
        reason='识别到三重底形态',
        generated_time='2025-12-29 09:00:00',  # 早上9点
        current_price_at_generation=88200,  # 假设生成时价格约$88,200
        actual_price_movement='价格继续上涨，未回调到入场价$87,702，最终达到$89,000+',
        why_missed='入场价设置过低（基于颈线计算），当前价格已远高于颈线，价格未回调到入场价'
    )
    
    print()
    print("=" * 80)
    print("录入完成！")
    print("=" * 80)
    print()
    print("📊 信号分析:")
    print("   - 方向: ✅ 正确（价格最终上涨）")
    print("   - 入场价: ❌ 不合理（$87,702，距离生成时价格约5.7%）")
    print("   - 如果入场: 潜在盈利约3.0%")
    print("   - 问题: 入场价设置基于历史颈线，未考虑当前价格位置")
    print()
    print("🔧 已优化:")
    print("   - 三重底形态入场价计算已优化")
    print("   - 现在会根据当前价格位置动态调整入场价")
    print("=" * 80)


if __name__ == "__main__":
    main()

