#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估用户提供的交易信号
"""

import sys
from datetime import datetime, timedelta
from calculate_trade_results import (
    calculate_trade_result,
    format_trade_result_report,
    analyze_stop_loss_optimization,
    get_btc_current_price
)

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def main():
    print("="*80)
    print("青鸟系统 - 交易信号评估报告")
    print("="*80)
    print("")
    
    current_price = get_btc_current_price()
    if current_price:
        print(f"当前BTC价格: ${current_price:,.2f}")
        print("")
    
    # 15分钟做空信号
    print("="*80)
    print("信号1: 15分钟做空信号")
    print("="*80)
    print("")
    
    signal_15m = {
        'entry_price': 87824,
        'stop_loss': 88087,
        'take_profit_1': 86493,
        'take_profit_2': 85620,
        'signal_type': 'short',
        'timeframe': '15m',
        'atr_pct': 0.08,  # 低波动
        'signal_time': None  # 需要从历史数据推断
    }
    
    # 假设信号生成时间是当前时间往前推48小时（给足够的时间让信号执行）
    # 实际应该从信号生成时间开始，但这里我们使用最近的数据
    signal_time_15m = datetime.now() - timedelta(hours=48)
    
    print(f"评估时间范围: {signal_time_15m.strftime('%Y-%m-%d %H:%M:%S')} 至 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    result_15m = calculate_trade_result(
        entry_price=signal_15m['entry_price'],
        stop_loss=signal_15m['stop_loss'],
        take_profit_1=signal_15m['take_profit_1'],
        take_profit_2=signal_15m['take_profit_2'],
        signal_type=signal_15m['signal_type'],
        timeframe=signal_15m['timeframe'],
        signal_time=signal_time_15m
    )
    
    if 'error' in result_15m:
        print(f"❌ 错误: {result_15m['error']}")
    else:
        report_15m = format_trade_result_report(result_15m)
        print(report_15m)
        
        # 止损优化分析
        suggestions_15m = analyze_stop_loss_optimization(result_15m, signal_15m.get('atr_pct'))
        if suggestions_15m['suggestions']:
            print("**止损优化建议**:")
            for suggestion in suggestions_15m['suggestions']:
                print(f"- {suggestion}")
            print("")
        
        # 详细分析
        print("**详细分析**:")
        if result_15m['status'] == 'stopped':
            print(f"- ❌ 信号已止损，亏损 {result_15m['final_pnl_pct']:.2f}%")
            print(f"- 止损距离: {suggestions_15m['current_stop_distance_pct']:.2f}%")
            if suggestions_15m['is_stop_too_tight']:
                print(f"- ⚠️ 止损可能过紧，建议调整为 {suggestions_15m['recommended_stop_distance_pct']:.2f}%")
            if result_15m['max_profit_pct'] > 0:
                print(f"- 最大浮盈曾达到 {result_15m['max_profit_pct']:.2f}%，但最终止损")
        print("")
    
    print("")
    print("="*80)
    print("信号2: 1小时做多信号")
    print("="*80)
    print("")
    
    signal_1h = {
        'entry_price': 87018,
        'stop_loss': 86700,
        'take_profit_1': 88241,
        'take_profit_2': 89114,
        'signal_type': 'long',
        'timeframe': '1h',
        'atr_pct': 0.81,  # 高波动
        'signal_time': None
    }
    
    signal_time_1h = datetime.now() - timedelta(hours=48)
    
    print(f"评估时间范围: {signal_time_1h.strftime('%Y-%m-%d %H:%M:%S')} 至 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    result_1h = calculate_trade_result(
        entry_price=signal_1h['entry_price'],
        stop_loss=signal_1h['stop_loss'],
        take_profit_1=signal_1h['take_profit_1'],
        take_profit_2=signal_1h['take_profit_2'],
        signal_type=signal_1h['signal_type'],
        timeframe=signal_1h['timeframe'],
        signal_time=signal_time_1h
    )
    
    if 'error' in result_1h:
        print(f"❌ 错误: {result_1h['error']}")
    else:
        report_1h = format_trade_result_report(result_1h)
        print(report_1h)
        
        # 止损优化分析
        suggestions_1h = analyze_stop_loss_optimization(result_1h, signal_1h.get('atr_pct'))
        if suggestions_1h['suggestions']:
            print("**止损优化建议**:")
            for suggestion in suggestions_1h['suggestions']:
                print(f"- {suggestion}")
            print("")
        
        # 详细分析
        print("**详细分析**:")
        if result_1h['status'] == 'full_tp':
            print(f"- ✅ 信号完全止盈，盈利 {result_1h['final_pnl_pct']:.2f}%")
            print(f"- 实际盈亏比: {result_1h['actual_risk_reward_ratio']:.2f}:1")
        elif result_1h['status'] == 'partial_tp':
            print(f"- ⚠️ 信号部分止盈，盈利 {result_1h['final_pnl_pct']:.2f}%")
        elif result_1h['status'] == 'stopped':
            print(f"- ❌ 信号已止损，亏损 {result_1h['final_pnl_pct']:.2f}%")
        elif result_1h['status'] == 'open':
            print(f"- 🔄 信号持仓中，当前盈亏 {result_1h['final_pnl_pct']:.2f}%")
        print("")
    
    # 总结
    print("")
    print("="*80)
    print("总结")
    print("="*80)
    print("")
    
    if 'error' not in result_15m and 'error' not in result_1h:
        print("**15分钟做空信号**:")
        print(f"  - 结果: {result_15m['status']}")
        print(f"  - 盈亏: {result_15m['final_pnl_pct']:+.2f}%")
        if result_15m['status'] == 'stopped':
            print(f"  - ⚠️ 止损距离过小 ({suggestions_15m['current_stop_distance_pct']:.2f}%)，建议调整")
        print("")
        
        print("**1小时做多信号**:")
        print(f"  - 结果: {result_1h['status']}")
        print(f"  - 盈亏: {result_1h['final_pnl_pct']:+.2f}%")
        if result_1h['status'] == 'full_tp':
            print(f"  - ✅ 信号成功，实际盈亏比 {result_1h['actual_risk_reward_ratio']:.2f}:1")
        if suggestions_1h['is_stop_too_tight']:
            print(f"  - ⚠️ 高波动市场，止损距离建议调整为 {suggestions_1h['recommended_stop_distance_pct']:.2f}%")
        print("")


if __name__ == "__main__":
    main()










