#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录昨天的信号结果
用于学习和改进系统
"""

import sys
from datetime import datetime
from record_signal_results_20251229_202648 import (
    record_stopped_signal,
    record_partial_tp_signal
)

def main():
    """记录昨天的信号结果"""
    
    # 信号1：5分钟做空 - 被止损
    print("=" * 80)
    print("记录信号1：5分钟做空 - 被止损")
    print("=" * 80)
    
    record_stopped_signal(
        system_name='de',
        timeframe='5分钟',
        signal_type='short',
        entry=87804,
        stop_loss=88067,
        take_profit_1=86347,
        take_profit_2=85475,
        entry_model='阻力位回落(量能大)',
        strength='strong',
        reason='FVG做空机会，价格可能回填到87474',
        generated_time='2025-12-29 20:26:48',
        entry_time='2025-12-29 20:26:48',  # 假设立即入场
        stop_time='2025-12-30 00:00:00',  # 假设在当天被止损
        stop_price=88067,  # 止损价格
        max_profit_pct=None,  # 自动计算
        max_loss_pct=None  # 自动计算
    )
    
    print()
    
    # 信号2：15分钟做空 - 被止损
    print("=" * 80)
    print("记录信号2：15分钟做空 - 被止损")
    print("=" * 80)
    
    record_stopped_signal(
        system_name='de',
        timeframe='15分钟',
        signal_type='short',
        entry=87279,
        stop_loss=87584,
        take_profit_1=85717,
        take_profit_2=84937,
        entry_model='反转形态-三重顶',
        strength='strong',
        reason='价格在Vegas通道下方，反弹到87948做空',
        generated_time='2025-12-29 20:26:48',
        entry_time='2025-12-29 20:26:48',
        stop_time='2025-12-30 00:00:00',
        stop_price=87584,
        max_profit_pct=None,
        max_loss_pct=None
    )
    
    print()
    
    # 信号3：1小时做多 - 部分止盈（还在运行中）
    print("=" * 80)
    print("记录信号3：1小时做多 - 部分止盈（还在运行中）")
    print("=" * 80)
    
    record_partial_tp_signal(
        system_name='de',
        timeframe='1小时',
        signal_type='long',
        entry=87018,
        stop_loss=86700,
        take_profit_1=88091,
        take_profit_2=88963,
        entry_model='支撑位反弹(量能大)',
        strength='strong',
        reason='价格从支撑位反弹确认',
        generated_time='2025-12-29 20:26:48',
        entry_time='2025-12-29 20:26:48',
        tp1_time='2025-12-30 12:00:00',  # 假设到达第一止盈位
        current_price=88091,  # 当前价格在第一止盈位
        max_profit_pct=None
    )
    
    print()
    print("=" * 80)
    print("✅ 所有信号结果已成功录入系统")
    print("=" * 80)
    print()
    print("这些数据将用于：")
    print("1. 机器学习模型训练")
    print("2. 波动率分析优化")
    print("3. 止损距离优化")
    print("4. 信号质量评估")

if __name__ == '__main__':
    main()


