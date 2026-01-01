#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析信号结果，生成科学评估报告
包含波动率分析、盈亏比评估和改进建议
"""

import sys
from datetime import datetime
from signal_tracker import SignalTracker
from volatility_analyzer import (
    calculate_risk_reward_ratio,
    calculate_atr_percent,
    assess_volatility_level
)

def analyze_signal_results():
    """分析最近的信号结果"""
    tracker = SignalTracker()
    signals_data = tracker.load_signals()
    
    if 'de' not in signals_data or not signals_data['de']:
        print("没有找到信号数据")
        return
    
    # 获取最近的信号（未分析的）
    recent_signals = [s for s in signals_data['de'] if not s.get('analyzed', False)]
    
    if not recent_signals:
        print("没有未分析的信号")
        return
    
    # 按生成时间排序
    recent_signals.sort(key=lambda x: x.get('generated_time', ''), reverse=True)
    
    # 生成分析报告
    report = []
    report.append("# BTC交易信号结果分析报告（科学评估）")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report.append(f"**分析信号数**: {len(recent_signals)}  ")
    report.append("")
    
    # 统计信息
    stopped_count = sum(1 for s in recent_signals if s.get('status') == 'stopped')
    partial_tp_count = sum(1 for s in recent_signals if s.get('status') == 'partial_tp')
    full_tp_count = sum(1 for s in recent_signals if s.get('status') == 'full_tp')
    
    report.append("## 📊 信号结果汇总")
    report.append("")
    report.append("| 信号 | 时间框架 | 方向 | 入场价 | 止损 | 止盈1 | 止盈2 | 盈亏比 | 结果 | 状态 |")
    report.append("|------|---------|------|--------|------|-------|-------|--------|------|------|")
    
    total_rr_ratios = []
    
    for i, signal in enumerate(recent_signals, 1):
        # 计算盈亏比
        try:
            rr_analysis = calculate_risk_reward_ratio(
                entry=signal['entry'],
                stop_loss=signal['stop_loss'],
                take_profit_1=signal['take_profit_1'],
                take_profit_2=signal['take_profit_2'],
                signal_type=signal['type']
            )
            avg_rr = rr_analysis['avg_rr_ratio']
            total_rr_ratios.append(avg_rr)
        except:
            avg_rr = 0
        
        # 状态标记
        status_emoji = {
            'stopped': '❌',
            'partial_tp': '⚠️',
            'full_tp': '✅'
        }
        status_text = {
            'stopped': '被止损',
            'partial_tp': '部分止盈',
            'full_tp': '全部止盈'
        }
        
        emoji = status_emoji.get(signal.get('status'), '')
        status = status_text.get(signal.get('status'), '未知')
        
        direction = "做多" if signal['type'] == 'long' else "做空"
        
        report.append(f"| 信号{i} | {signal['timeframe']} | {direction} | ${signal['entry']:,.0f} | ${signal['stop_loss']:,.0f} | ${signal['take_profit_1']:,.0f} | ${signal['take_profit_2']:,.0f} | {avg_rr:.2f}:1 | {emoji} {status} | {signal.get('status', '未知')} |")
    
    report.append("")
    
    if stopped_count + partial_tp_count + full_tp_count > 0:
        completed_count = stopped_count + full_tp_count
        success_rate = (full_tp_count / completed_count * 100) if completed_count > 0 else 0
        report.append(f"**成功率**: {full_tp_count}/{completed_count} = {success_rate:.1f}%（已完成信号）  ")
        report.append(f"**部分成功率**: {(partial_tp_count + full_tp_count)}/{len(recent_signals)} = {((partial_tp_count + full_tp_count) / len(recent_signals) * 100):.1f}%（包含运行中信号）")
    
    if total_rr_ratios:
        avg_rr = sum(total_rr_ratios) / len(total_rr_ratios)
        report.append(f"**平均盈亏比**: {avg_rr:.2f}:1")
    
    report.append("")
    report.append("---")
    report.append("")
    
    # 详细分析
    report.append("## 📝 详细信号分析（科学评估）")
    report.append("")
    
    for i, signal in enumerate(recent_signals, 1):
        report.append(f"### 信号{i}：{signal['timeframe']}{'做多' if signal['type'] == 'long' else '做空'} - {signal.get('entry_model', '未知')}")
        
        # 状态标记
        if signal.get('status') == 'stopped':
            report.append("❌")
        elif signal.get('status') == 'partial_tp':
            report.append("⚠️")
        elif signal.get('status') == 'full_tp':
            report.append("✅")
        
        report.append("")
        report.append("**信号信息**:")
        report.append(f"- **入场模型**: {signal.get('entry_model', '未知')}")
        report.append(f"- **入场价**: ${signal['entry']:,.0f}")
        report.append(f"- **止损**: ${signal['stop_loss']:,.0f} ({abs(signal['entry'] - signal['stop_loss']) / signal['entry'] * 100:.2f}%)")
        report.append(f"- **止盈**: ${signal['take_profit_1']:,.0f} (50%) / ${signal['take_profit_2']:,.0f} (50%)")
        report.append(f"- **生成时价格**: ${signal.get('current_price', signal['entry']):,.2f}")
        report.append("")
        
        # 盈亏比分析
        try:
            rr_analysis = calculate_risk_reward_ratio(
                entry=signal['entry'],
                stop_loss=signal['stop_loss'],
                take_profit_1=signal['take_profit_1'],
                take_profit_2=signal['take_profit_2'],
                signal_type=signal['type']
            )
            
            quality_map = {
                'excellent': '优秀',
                'good': '良好',
                'acceptable': '可接受',
                'poor': '较低',
                'very_poor': '过低'
            }
            
            report.append("**盈亏比分析**:")
            report.append(f"- **风险**: ${rr_analysis['risk']:,.0f} ({abs(signal['entry'] - signal['stop_loss']) / signal['entry'] * 100:.2f}%)")
            report.append(f"- **止盈1回报**: ${rr_analysis['reward_1']:,.0f} ({abs(signal['take_profit_1'] - signal['entry']) / signal['entry'] * 100:.2f}%) → **盈亏比: {rr_analysis['rr_ratio_1']:.2f}:1**")
            report.append(f"- **止盈2回报**: ${rr_analysis['reward_2']:,.0f} ({abs(signal['take_profit_2'] - signal['entry']) / signal['entry'] * 100:.2f}%) → **盈亏比: {rr_analysis['rr_ratio_2']:.2f}:1**")
            report.append(f"- **平均盈亏比**: **{rr_analysis['avg_rr_ratio']:.2f}:1** {'✅' if rr_analysis['quality'] in ['excellent', 'good'] else '⚠️'} {quality_map.get(rr_analysis['quality'], '未知')}")
            report.append("")
        except Exception as e:
            report.append(f"**盈亏比分析**: 计算失败 ({e})")
            report.append("")
        
        # 结果分析
        if signal.get('status') == 'stopped':
            report.append("**结果**: ❌ **被止损 - 失败**")
            report.append("")
            report.append("**分析**:")
            if rr_analysis and rr_analysis['avg_rr_ratio'] >= 3.0:
                if rr_analysis and rr_analysis['avg_rr_ratio'] >= 3.0:
                report.append(f"- ✅ **盈亏比优秀**: 平均盈亏比{rr_analysis['avg_rr_ratio']:.2f}:1，理论上是非常好的信号")
            report.append(f"- ❌ **被止损**: 价格触发止损${signal['stop_loss']:,.0f}")
            stop_distance = abs(signal['entry'] - signal['stop_loss']) / signal['entry'] * 100
            if stop_distance < 0.5:
                report.append(f"- ⚠️ **止损距离过窄**: {stop_distance:.2f}%的止损距离可能无法承受市场波动")
            report.append("")
            report.append("**问题总结**:")
            report.append(f"1. 止损距离设置过窄（{stop_distance:.2f}%），无法承受市场波动")
            if rr_analysis and rr_analysis['avg_rr_ratio'] >= 3.0:
                report.append("2. 虽然盈亏比优秀，但止损被触发，信号失败")
            report.append("3. 需要根据市场波动率动态调整止损距离")
            report.append("")
            report.append("**改进建议**:")
            report.append("- 💡 **波动率调整**: 高波动时，止损距离应调整为0.45-0.60%（1.5-2倍ATR）")
            report.append("- 💡 **订单簿分析**: 确保止损放在流动性稀疏区，避免被扫止损")
        
        elif signal.get('status') == 'partial_tp':
            report.append("**结果**: ⚠️ **部分止盈 - 运行中**")
            report.append("")
            report.append("**分析**:")
            report.append(f"- ✅ **第一止盈位已到达**: ${signal['take_profit_1']:,.0f}")
            report.append(f"- ⏳ **等待第二止盈位**: ${signal['take_profit_2']:,.0f}")
            report.append("- 💡 **建议**: 可以考虑将止损移至盈亏平衡点，保护利润")
        
        elif signal.get('status') == 'full_tp':
            report.append("**结果**: ✅ **全部止盈 - 成功**")
            report.append("")
            report.append("**分析**:")
            report.append(f"- ✅ **第一止盈位已到达**: ${signal['take_profit_1']:,.0f}")
            report.append(f"- ✅ **第二止盈位已到达**: ${signal['take_profit_2']:,.0f}")
            report.append("- ✅ **信号执行成功**: 按预期完成")
        
        report.append("")
        report.append("---")
        report.append("")
    
    # 系统改进建议
    report.append("## 🔧 系统改进建议")
    report.append("")
    
    # 分析止损距离
    stop_distances = []
    for signal in recent_signals:
        if signal.get('status') == 'stopped':
            distance = abs(signal['entry'] - signal['stop_loss']) / signal['entry'] * 100
            stop_distances.append(distance)
    
    if stop_distances:
        avg_stop_distance = sum(stop_distances) / len(stop_distances)
        report.append("### 1. 止损距离优化")
        report.append("")
        report.append(f"**当前平均止损距离**: {avg_stop_distance:.2f}%")
        if avg_stop_distance < 0.5:
            report.append("")
            report.append("**问题**: 止损距离过窄，容易被市场波动扫掉")
            report.append("")
            report.append("**改进内容**:")
            report.append("- 添加ATR计算")
            report.append("- 根据波动率评估调整止损距离")
            report.append("- 高波动时自动放宽止损")
            report.append("")
            report.append("**实施方法**:")
            report.append("```python")
            report.append("# 计算ATR")
            report.append("atr_percent = calculate_atr_percent(klines, period=14)")
            report.append("")
            report.append("# 评估波动率")
            report.append("volatility_assessment = assess_volatility_level(atr_percent)")
            report.append("")
            report.append("# 调整止损距离")
            report.append("if volatility_assessment['level'] in ['high', 'very_high']:")
            report.append("    stop_loss_multiplier = volatility_assessment['stop_loss_multiplier']")
            report.append("    adjusted_stop_distance = original_stop_distance * stop_loss_multiplier")
            report.append("```")
            report.append("")
    
    report.append("### 2. 盈亏比显示 ✅（已实施）")
    report.append("")
    report.append("**改进内容**:")
    report.append("- 在信号报告中显示盈亏比")
    report.append("- 评估盈亏比质量（优秀/良好/可接受/较低/过低）")
    report.append("- 显示风险、回报和盈亏比详情")
    report.append("")
    
    report.append("### 3. 科学化评估 ✅（已实施）")
    report.append("")
    report.append("**改进内容**:")
    report.append("- 使用ATR评估市场波动率")
    report.append("- 使用盈亏比评估信号质量")
    report.append("- 综合波动率和盈亏比给出建议")
    report.append("")
    
    report.append("---")
    report.append("")
    
    # 数据录入状态
    report.append("## 🔄 数据已录入系统")
    report.append("")
    report.append("所有信号结果已成功录入系统，可用于：")
    report.append("- ✅ 机器学习模型训练")
    report.append("- ✅ 波动率分析优化")
    report.append("- ✅ 止损距离优化")
    report.append("")
    report.append("**录入状态**:")
    for signal in recent_signals:
        status_icon = "✅" if signal.get('analyzed', False) else "⏳"
        report.append(f"- 信号{recent_signals.index(signal)+1}: {status_icon} 已录入（{signal.get('status', '未知')}状态）")
    
    report.append("")
    report.append("---")
    report.append("")
    
    report.append(f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report.append("**数据来源**: 用户手动评估结果  ")
    report.append("**评估方法**: 科学化分析（波动率 + 盈亏比）")
    
    # 输出报告
    output = "\n".join(report)
    print(output)
    
    # 保存报告
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"信号结果分析报告_{timestamp}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n分析报告已保存到: {filename}", file=sys.stderr)
    
    # 标记信号为已分析
    for signal in recent_signals:
        signal['analyzed'] = True
    
    tracker.save_signals(signals_data)
    print("✅ 所有信号已标记为已分析", file=sys.stderr)

if __name__ == '__main__':
    analyze_signal_results()

