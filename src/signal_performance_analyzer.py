#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号性能分析器
分析已结束的信号，计算胜率、盈亏比等指标，并给出改进建议
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class SignalPerformanceAnalyzer:
    """信号性能分析器"""
    
    def __init__(self, signals_data: Dict):
        """
        初始化分析器
        
        Args:
            signals_data: 信号数据字典（从SignalTracker.load_signals()获取）
        """
        self.signals_data = signals_data
    
    def analyze_completed_signals(self) -> Dict:
        """
        分析已完成的信号（stopped和full_tp）
        
        Returns:
            {
                'total_completed': int,
                'win_count': int,  # 全部止盈数量
                'loss_count': int,  # 已止损数量
                'win_rate': float,  # 胜率（%）
                'avg_profit': float,  # 平均盈利（%）
                'avg_loss': float,  # 平均亏损（%）
                'profit_factor': float,  # 盈亏比
                'by_system': {...},  # 按系统分类
                'by_timeframe': {...},  # 按时间框架分类
                'by_entry_model': {...},  # 按入场模型分类
                'completed_signals': [...]  # 已完成的信号列表
            }
        """
        all_signals = []
        for system_name, signals in self.signals_data.items():
            for signal in signals:
                if signal.get('status') in ['stopped', 'full_tp']:
                    all_signals.append(signal)
        
        if not all_signals:
            return {
                'total_completed': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0.0,
                'avg_profit': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'by_system': {},
                'by_timeframe': {},
                'by_entry_model': {},
                'completed_signals': []
            }
        
        # 分类统计
        wins = [s for s in all_signals if s['status'] == 'full_tp']
        losses = [s for s in all_signals if s['status'] == 'stopped']
        
        # 计算平均值
        avg_profit = sum([s.get('max_profit', 0) for s in wins]) / len(wins) if wins else 0
        avg_loss = sum([s.get('max_loss', 0) for s in losses]) / len(losses) if losses else 0
        
        # 盈亏比 = 平均盈利 / 平均亏损（取绝对值）
        profit_factor = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
        
        # 按系统分类
        by_system = defaultdict(lambda: {'wins': 0, 'losses': 0, 'signals': []})
        for signal in all_signals:
            system = signal.get('system', 'unknown')
            by_system[system]['signals'].append(signal)
            if signal['status'] == 'full_tp':
                by_system[system]['wins'] += 1
            else:
                by_system[system]['losses'] += 1
        
        # 按时间框架分类
        by_timeframe = defaultdict(lambda: {'wins': 0, 'losses': 0, 'signals': []})
        for signal in all_signals:
            tf = signal.get('timeframe', 'unknown')
            by_timeframe[tf]['signals'].append(signal)
            if signal['status'] == 'full_tp':
                by_timeframe[tf]['wins'] += 1
            else:
                by_timeframe[tf]['losses'] += 1
        
        # 按入场模型分类
        by_entry_model = defaultdict(lambda: {'wins': 0, 'losses': 0, 'signals': []})
        for signal in all_signals:
            model = signal.get('entry_model', '未知模型')
            by_entry_model[model]['signals'].append(signal)
            if signal['status'] == 'full_tp':
                by_entry_model[model]['wins'] += 1
            else:
                by_entry_model[model]['losses'] += 1
        
        # 计算各分类的胜率
        for category_dict in [by_system, by_timeframe, by_entry_model]:
            for key, data in category_dict.items():
                total = data['wins'] + data['losses']
                data['win_rate'] = (data['wins'] / total * 100) if total > 0 else 0
        
        return {
            'total_completed': len(all_signals),
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_rate': (len(wins) / len(all_signals) * 100) if all_signals else 0,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'by_system': dict(by_system),
            'by_timeframe': dict(by_timeframe),
            'by_entry_model': dict(by_entry_model),
            'completed_signals': all_signals
        }
    
    def generate_improvement_suggestions(self, analysis: Dict) -> List[str]:
        """
        根据分析结果生成改进建议
        
        Args:
            analysis: analyze_completed_signals()的返回结果
        
        Returns:
            改进建议列表
        """
        suggestions = []
        
        if analysis['total_completed'] == 0:
            suggestions.append("📊 **数据不足**：目前还没有已完成的信号，建议等待更多数据后再进行分析")
            return suggestions
        
        # 总体胜率分析
        win_rate = analysis['win_rate']
        if win_rate < 40:
            suggestions.append(f"⚠️ **胜率偏低**：当前胜率{win_rate:.1f}%，建议：")
            suggestions.append("  - 检查入场条件是否过于宽松，考虑增加更多确认条件")
            suggestions.append("  - 提高止损设置精度，避免被小幅波动扫止损")
            suggestions.append("  - 优先使用高信号强度的入场模型")
        elif win_rate >= 60:
            suggestions.append(f"✅ **胜率良好**：当前胜率{win_rate:.1f}%，继续保持")
        else:
            suggestions.append(f"📈 **胜率正常**：当前胜率{win_rate:.1f}%，有提升空间")
        
        # 盈亏比分析
        profit_factor = analysis['profit_factor']
        if profit_factor < 1.5:
            suggestions.append(f"⚠️ **盈亏比偏低**：当前盈亏比{profit_factor:.2f}，建议：")
            suggestions.append("  - 提高止盈目标，设置更合理的分批止盈策略")
            suggestions.append("  - 降低止损距离，提高盈亏比")
            suggestions.append("  - 优化入场点选择，减少止损被触发的概率")
        elif profit_factor >= 2.0:
            suggestions.append(f"✅ **盈亏比良好**：当前盈亏比{profit_factor:.2f}，策略有效")
        else:
            suggestions.append(f"📊 **盈亏比正常**：当前盈亏比{profit_factor:.2f}，可以优化")
        
        # 按系统分析
        by_system = analysis['by_system']
        if len(by_system) > 1:
            suggestions.append("\n**按系统分类分析**：")
            for system, data in by_system.items():
                win_rate_sys = data['win_rate']
                if win_rate_sys < 40:
                    suggestions.append(f"  - ⚠️ {system}系统胜率{win_rate_sys:.1f}%，需要优化")
                elif win_rate_sys >= 60:
                    suggestions.append(f"  - ✅ {system}系统胜率{win_rate_sys:.1f}%，表现良好")
        
        # 按时间框架分析
        by_timeframe = analysis['by_timeframe']
        if len(by_timeframe) > 1:
            suggestions.append("\n**按时间框架分类分析**：")
            best_tf = max(by_timeframe.items(), key=lambda x: x[1]['win_rate'])
            worst_tf = min(by_timeframe.items(), key=lambda x: x[1]['win_rate'])
            suggestions.append(f"  - ✅ 最佳时间框架：{best_tf[0]}（胜率{best_tf[1]['win_rate']:.1f}%）")
            suggestions.append(f"  - ⚠️ 需优化时间框架：{worst_tf[0]}（胜率{worst_tf[1]['win_rate']:.1f}%）")
            suggestions.append(f"  - 💡 建议：优先使用{best_tf[0]}时间框架的信号")
        
        # 按入场模型分析
        by_entry_model = analysis['by_entry_model']
        if len(by_entry_model) > 1:
            suggestions.append("\n**按入场模型分类分析**：")
            
            # 找出表现最好和最差的模型
            model_stats = []
            for model, data in by_entry_model.items():
                if data['wins'] + data['losses'] >= 2:  # 至少2个信号才分析
                    model_stats.append((model, data))
            
            if model_stats:
                model_stats.sort(key=lambda x: x[1]['win_rate'], reverse=True)
                best_model = model_stats[0]
                worst_model = model_stats[-1]
                
                suggestions.append(f"  - ✅ 最佳入场模型：{best_model[0]}（胜率{best_model[1]['win_rate']:.1f}%，{best_model[1]['wins']+best_model[1]['losses']}个信号）")
                if worst_model[0] != best_model[0]:
                    suggestions.append(f"  - ⚠️ 需优化入场模型：{worst_model[0]}（胜率{worst_model[1]['win_rate']:.1f}%，{worst_model[1]['wins']+worst_model[1]['losses']}个信号）")
                    suggestions.append(f"  - 💡 建议：减少使用{worst_model[0]}，优先使用{best_model[0]}")
        
        # 平均盈亏分析
        avg_profit = analysis['avg_profit']
        avg_loss = analysis['avg_loss']
        suggestions.append(f"\n**盈亏分析**：")
        suggestions.append(f"  - 平均盈利：{avg_profit:.2f}%")
        suggestions.append(f"  - 平均亏损：{avg_loss:.2f}%")
        
        if abs(avg_loss) > abs(avg_profit) * 0.8:
            suggestions.append("  - ⚠️ 平均亏损接近平均盈利，建议收紧止损或提高止盈目标")
        
        # 风险提示
        suggestions.append(f"\n**风险提示**：")
        suggestions.append(f"  - 当前分析基于{analysis['total_completed']}个已完成的信号")
        suggestions.append(f"  - 建议至少积累50个以上信号后再做最终评估")
        suggestions.append(f"  - 市场环境变化时，策略表现可能会有较大波动")
        
        return suggestions
    
    def format_analysis_report(self, analysis: Dict, suggestions: List[str]) -> str:
        """
        格式化分析报告
        
        Args:
            analysis: analyze_completed_signals()的返回结果
            suggestions: generate_improvement_suggestions()的返回结果
        
        Returns:
            格式化的报告文本
        """
        report = []
        report.append("# 信号性能分析报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 总体统计
        report.append("## 一、总体统计")
        report.append("")
        report.append(f"- **已完成信号总数**: {analysis['total_completed']}")
        report.append(f"- **全部止盈**: {analysis['win_count']} ({analysis['win_rate']:.1f}%)")
        report.append(f"- **已止损**: {analysis['loss_count']} ({100-analysis['win_rate']:.1f}%)")
        report.append(f"- **平均盈利**: {analysis['avg_profit']:.2f}%")
        report.append(f"- **平均亏损**: {analysis['avg_loss']:.2f}%")
        report.append(f"- **盈亏比**: {analysis['profit_factor']:.2f}")
        report.append("")
        
        # 详细分类统计
        if analysis['by_system']:
            report.append("## 二、按系统分类")
            report.append("")
            for system, data in analysis['by_system'].items():
                total = data['wins'] + data['losses']
                report.append(f"### {system}")
                report.append(f"- 总信号数: {total}")
                report.append(f"- 全部止盈: {data['wins']} ({data['win_rate']:.1f}%)")
                report.append(f"- 已止损: {data['losses']} ({100-data['win_rate']:.1f}%)")
                report.append("")
        
        if analysis['by_timeframe']:
            report.append("## 三、按时间框架分类")
            report.append("")
            for tf, data in analysis['by_timeframe'].items():
                total = data['wins'] + data['losses']
                report.append(f"### {tf}")
                report.append(f"- 总信号数: {total}")
                report.append(f"- 全部止盈: {data['wins']} ({data['win_rate']:.1f}%)")
                report.append(f"- 已止损: {data['losses']} ({100-data['win_rate']:.1f}%)")
                report.append("")
        
        if analysis['by_entry_model']:
            report.append("## 四、按入场模型分类")
            report.append("")
            # 按胜率排序
            sorted_models = sorted(analysis['by_entry_model'].items(), 
                                  key=lambda x: x[1]['win_rate'], 
                                  reverse=True)
            for model, data in sorted_models:
                total = data['wins'] + data['losses']
                report.append(f"### {model}")
                report.append(f"- 总信号数: {total}")
                report.append(f"- 全部止盈: {data['wins']} ({data['win_rate']:.1f}%)")
                report.append(f"- 已止损: {data['losses']} ({100-data['win_rate']:.1f}%)")
                report.append("")
        
        # 改进建议
        report.append("## 五、系统改进建议")
        report.append("")
        for suggestion in suggestions:
            report.append(suggestion)
        report.append("")
        
        # 已完成信号列表（最近20个）
        if analysis['completed_signals']:
            report.append("## 六、最近完成的信号")
            report.append("")
            recent_signals = sorted(analysis['completed_signals'], 
                                   key=lambda x: x.get('last_check_time', ''), 
                                   reverse=True)[:20]
            for signal in recent_signals:
                status_emoji = "✅" if signal['status'] == 'full_tp' else "🔴"
                direction = "做多" if signal['type'] == 'long' else "做空"
                profit_pct = signal.get('max_profit', 0) if signal['status'] == 'full_tp' else signal.get('max_loss', 0)
                report.append(f"{status_emoji} **{signal['system']} {signal['timeframe']}** {direction} ({signal['entry_model']})")
                report.append(f"  - 入场: ${signal['entry']:,.0f} | 状态: {signal['status']} | 盈亏: {profit_pct:.2f}%")
                report.append(f"  - 生成时间: {signal.get('generated_time', 'N/A')}")
                report.append("")
        
        return "\n".join(report)




