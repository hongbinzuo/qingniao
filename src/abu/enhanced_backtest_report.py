#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的回测报告生成器

提供更详细的回测报告，包括：
- 性能分析可视化
- 风险评估
- 策略建议
"""

from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class EnhancedBacktestReport:
    """增强的回测报告生成器"""
    
    def __init__(self):
        """初始化报告生成器"""
        pass
    
    def generate_comprehensive_report(
        self,
        backtest_result: Dict,
        output_file: Optional[Path] = None
    ) -> str:
        """
        生成综合回测报告
        
        Args:
            backtest_result: 回测结果字典
            output_file: 输出文件路径（可选）
        
        Returns:
            Markdown格式的报告
        """
        lines = []
        
        # 标题
        lines.append("# 综合回测报告")
        lines.append("")
        lines.append(f"**生成时间**: {backtest_result.get('backtest_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
        lines.append(f"**交易计划**: {Path(backtest_result.get('plan_file', '')).name}")
        lines.append("")
        
        # 执行摘要
        lines.append("## 📊 执行摘要")
        lines.append("")
        metrics = backtest_result.get('metrics', {})
        lines.append(f"- **总收益率**: {metrics.get('total_return_pct', 0):+.2f}%")
        lines.append(f"- **胜率**: {metrics.get('win_rate', 0):.2f}%")
        lines.append(f"- **Sharpe比率**: {metrics.get('sharpe_ratio', 0):.2f}")
        lines.append(f"- **最大回撤**: {metrics.get('max_drawdown_pct', 0):.2f}%")
        lines.append(f"- **盈亏比**: {metrics.get('profit_factor', 0):.2f}")
        lines.append("")
        
        # 评估等级
        grade = self._calculate_strategy_grade(metrics)
        lines.append(f"### 策略评分: {grade['score']}/100 ({grade['level']})")
        lines.append("")
        if grade['strengths']:
            lines.append("**优势**:")
            for strength in grade['strengths']:
                lines.append(f"- ✅ {strength}")
            lines.append("")
        if grade['weaknesses']:
            lines.append("**需要改进**:")
            for weakness in grade['weaknesses']:
                lines.append(f"- ⚠️ {weakness}")
            lines.append("")
        
        # 信号统计
        lines.append("## 📈 信号统计")
        lines.append("")
        lines.append(f"- **总信号数**: {backtest_result.get('total_signals', 0)}")
        lines.append(f"- **成功回测**: {backtest_result.get('successful_signals', 0)}")
        lines.append(f"- **失败信号**: {len(backtest_result.get('failed_signals', []))}")
        if backtest_result.get('brooks_rejected', 0) > 0:
            lines.append(f"- **Brooks规则拒绝**: {backtest_result['brooks_rejected']} 个信号")
        lines.append("")
        
        # Brooks验证统计
        if backtest_result.get('brooks_validation'):
            bv = backtest_result['brooks_validation']
            lines.append("### Brooks规则验证")
            lines.append("")
            lines.append(f"- **通过验证**: {bv.get('valid', 0)}")
            lines.append(f"- **验证失败**: {bv.get('invalid', 0)}")
            lines.append(f"- **严重错误**: {bv.get('critical', 0)}")
            lines.append(f"- **一般错误**: {bv.get('error', 0)}")
            lines.append(f"- **警告**: {bv.get('warning', 0)}")
            lines.append(f"- **平均分数**: {bv.get('avg_score', 0):.1f}/100")
            lines.append("")
        
        # 性能指标
        lines.append("## 📊 性能指标")
        lines.append("")
        lines.append("### 收益指标")
        lines.append("")
        lines.append(f"- **总收益率**: {metrics.get('total_return_pct', 0):+.2f}%")
        lines.append(f"- **最终权益**: ${metrics.get('final_equity', 0):,.2f}")
        lines.append("")
        
        lines.append("### 风险指标")
        lines.append("")
        lines.append(f"- **最大回撤**: {metrics.get('max_drawdown_pct', 0):.2f}%")
        lines.append(f"- **Sharpe比率**: {metrics.get('sharpe_ratio', 0):.2f}")
        lines.append("")
        
        lines.append("### 交易统计")
        lines.append("")
        lines.append(f"- **总交易数**: {metrics.get('total_trades', 0)}")
        lines.append(f"- **盈利交易**: {metrics.get('winning_trades', 0)}")
        lines.append(f"- **亏损交易**: {metrics.get('losing_trades', 0)}")
        lines.append(f"- **胜率**: {metrics.get('win_rate', 0):.2f}%")
        lines.append("")
        
        lines.append("### 盈亏分析")
        lines.append("")
        lines.append(f"- **平均盈利**: ${metrics.get('avg_win', 0):,.2f}")
        lines.append(f"- **平均亏损**: ${metrics.get('avg_loss', 0):,.2f}")
        if metrics.get('avg_win', 0) > 0 and metrics.get('avg_loss', 0) > 0:
            win_loss_ratio = metrics.get('avg_win', 0) / metrics.get('avg_loss', 0)
            lines.append(f"- **盈亏比**: {win_loss_ratio:.2f}:1")
        lines.append(f"- **盈亏比（Profit Factor）**: {metrics.get('profit_factor', 0):.2f}")
        lines.append("")
        
        # 性能分析
        if backtest_result.get('performance_analysis'):
            perf = backtest_result['performance_analysis']
            lines.append("## 🔍 深度分析")
            lines.append("")
            
            # 按时间框架
            if perf.get('timeframe_stats'):
                lines.append("### 按时间框架分析")
                lines.append("")
                for tf, stats in perf['timeframe_stats'].items():
                    lines.append(f"#### {tf}")
                    lines.append("")
                    lines.append(f"- **信号数**: {stats['total_signals']}")
                    lines.append(f"- **胜率**: {stats['win_rate']:.2%}")
                    lines.append(f"- **总盈亏**: ${stats['total_pnl']:,.2f}")
                    lines.append(f"- **平均收益率**: {stats['avg_return_pct']:.2%}")
                    lines.append("")
            
            # 按币种
            if perf.get('symbol_stats'):
                lines.append("### 按币种分析")
                lines.append("")
                sorted_symbols = sorted(perf['symbol_stats'].items(), 
                                      key=lambda x: x[1]['total_pnl'], reverse=True)
                for symbol, stats in sorted_symbols:
                    pnl_sign = "+" if stats['total_pnl'] >= 0 else ""
                    lines.append(f"#### {symbol} ({pnl_sign}${stats['total_pnl']:,.2f})")
                    lines.append("")
                    lines.append(f"- **信号数**: {stats['total_signals']}")
                    lines.append(f"- **胜率**: {stats['win_rate']:.2%}")
                    lines.append(f"- **平均收益率**: {stats['avg_return_pct']:.2%}")
                    lines.append("")
            
            # 最佳模式
            if perf.get('best_patterns'):
                lines.append("### 🏆 表现最佳的模式")
                lines.append("")
                for i, (key, pattern_info) in enumerate(perf['best_patterns'], 1):
                    lines.append(f"{i}. **{pattern_info['pattern_name']}** ({pattern_info['pattern_type']})")
                    lines.append(f"   - 胜率: {pattern_info['win_rate']:.2%}")
                    lines.append(f"   - 平均收益率: {pattern_info['avg_return_pct']:.2%}")
                    lines.append(f"   - 总盈亏: ${pattern_info['total_pnl']:,.2f}")
                    lines.append("")
            
            # 最差模式
            if perf.get('worst_patterns'):
                lines.append("### ⚠️ 表现最差的模式")
                lines.append("")
                for i, (key, pattern_info) in enumerate(perf['worst_patterns'], 1):
                    lines.append(f"{i}. **{pattern_info['pattern_name']}** ({pattern_info['pattern_type']})")
                    lines.append(f"   - 胜率: {pattern_info['win_rate']:.2%}")
                    lines.append(f"   - 平均收益率: {pattern_info['avg_return_pct']:.2%}")
                    lines.append(f"   - 总盈亏: ${pattern_info['total_pnl']:,.2f}")
                    lines.append("")
        
        # 警告和问题
        warnings = backtest_result.get('warnings', [])
        issues = backtest_result.get('issues', [])
        
        if warnings:
            lines.append("## ⚠️ 警告")
            lines.append("")
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")
        
        if issues:
            lines.append("## 🚨 严重问题")
            lines.append("")
            for issue in issues:
                lines.append(f"- {issue}")
            lines.append("")
        
        # 改进建议
        suggestions = self._generate_suggestions(metrics, backtest_result)
        if suggestions:
            lines.append("## 💡 改进建议")
            lines.append("")
            for suggestion in suggestions:
                lines.append(f"- {suggestion}")
            lines.append("")
        
        # 生成报告
        report = '\n'.join(lines)
        
        # 保存到文件
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
        
        return report
    
    def _calculate_strategy_grade(self, metrics: Dict) -> Dict:
        """
        计算策略评分
        
        Args:
            metrics: 性能指标
        
        Returns:
            评分结果
        """
        score = 0
        strengths = []
        weaknesses = []
        
        # 总收益率 (30分)
        total_return = metrics.get('total_return_pct', 0)
        if total_return > 10:
            score += 30
            strengths.append("总收益率优秀 (>10%)")
        elif total_return > 5:
            score += 20
            strengths.append("总收益率良好 (>5%)")
        elif total_return > 0:
            score += 10
        else:
            weaknesses.append("总收益率为负")
        
        # 胜率 (20分)
        win_rate = metrics.get('win_rate', 0)
        if win_rate >= 60:
            score += 20
            strengths.append("胜率优秀 (≥60%)")
        elif win_rate >= 50:
            score += 15
            strengths.append("胜率良好 (≥50%)")
        elif win_rate >= 40:
            score += 10
        else:
            weaknesses.append(f"胜率过低 ({win_rate:.1f}% < 40%)")
        
        # Sharpe比率 (20分)
        sharpe = metrics.get('sharpe_ratio', 0)
        if sharpe >= 1.0:
            score += 20
            strengths.append("Sharpe比率优秀 (≥1.0)")
        elif sharpe >= 0.5:
            score += 15
            strengths.append("Sharpe比率良好 (≥0.5)")
        elif sharpe > 0:
            score += 10
        else:
            weaknesses.append(f"Sharpe比率过低 ({sharpe:.2f} < 0.5)")
        
        # 最大回撤 (20分)
        drawdown = metrics.get('max_drawdown_pct', 0)
        if drawdown < 10:
            score += 20
            strengths.append("最大回撤控制良好 (<10%)")
        elif drawdown < 20:
            score += 15
            strengths.append("最大回撤可接受 (<20%)")
        elif drawdown < 30:
            score += 10
        else:
            weaknesses.append(f"最大回撤过大 ({drawdown:.1f}% ≥ 30%)")
        
        # 盈亏比 (10分)
        profit_factor = metrics.get('profit_factor', 0)
        if profit_factor >= 2.0:
            score += 10
            strengths.append("盈亏比优秀 (≥2.0)")
        elif profit_factor >= 1.2:
            score += 8
            strengths.append("盈亏比良好 (≥1.2)")
        elif profit_factor >= 1.0:
            score += 5
        else:
            weaknesses.append(f"盈亏比不足 ({profit_factor:.2f} < 1.2)")
        
        # 确定等级
        if score >= 80:
            level = "优秀"
        elif score >= 60:
            level = "良好"
        elif score >= 40:
            level = "一般"
        else:
            level = "需要改进"
        
        return {
            'score': score,
            'level': level,
            'strengths': strengths,
            'weaknesses': weaknesses
        }
    
    def _generate_suggestions(self, metrics: Dict, backtest_result: Dict) -> List[str]:
        """
        生成改进建议
        
        Args:
            metrics: 性能指标
            backtest_result: 回测结果
        
        Returns:
            建议列表
        """
        suggestions = []
        
        # 胜率建议
        win_rate = metrics.get('win_rate', 0)
        if win_rate < 40:
            suggestions.append("胜率过低，建议：1) 提高信号质量筛选标准；2) 优化入场时机；3) 避免逆势交易")
        
        # 盈亏比建议
        profit_factor = metrics.get('profit_factor', 0)
        if profit_factor < 1.2:
            suggestions.append("盈亏比不足，建议：1) 提高止盈目标（至少2:1）；2) 收紧止损距离；3) 优化退出策略")
        
        # 回撤建议
        drawdown = metrics.get('max_drawdown_pct', 0)
        if drawdown > 20:
            suggestions.append("最大回撤过大，建议：1) 降低仓位大小；2) 增加止损距离；3) 避免连续亏损")
        
        # Sharpe比率建议
        sharpe = metrics.get('sharpe_ratio', 0)
        if sharpe < 0.5:
            suggestions.append("Sharpe比率过低，建议：1) 提高收益稳定性；2) 降低风险；3) 优化仓位管理")
        
        # 性能分析建议
        if backtest_result.get('performance_analysis'):
            perf = backtest_result['performance_analysis']
            
            # 最差模式建议
            if perf.get('worst_patterns'):
                worst = perf['worst_patterns'][0][1]
                if worst['win_rate'] < 0.3:
                    suggestions.append(f"模式 '{worst['pattern_name']}' 表现很差（胜率{worst['win_rate']:.1%}），建议避免使用或优化该模式")
            
            # 时间框架建议
            if perf.get('timeframe_stats'):
                tf_stats = perf['timeframe_stats']
                if len(tf_stats) > 1:
                    best_tf = max(tf_stats.items(), key=lambda x: x[1]['win_rate'])
                    worst_tf = min(tf_stats.items(), key=lambda x: x[1]['win_rate'])
                    if best_tf[1]['win_rate'] - worst_tf[1]['win_rate'] > 0.2:
                        suggestions.append(f"时间框架表现差异大：{best_tf[0]}表现更好（胜率{best_tf[1]['win_rate']:.1%}），建议优先使用该时间框架")
        
        # Brooks验证建议
        if backtest_result.get('brooks_validation'):
            bv = backtest_result['brooks_validation']
            if bv.get('critical', 0) > 0:
                suggestions.append(f"发现{bv['critical']}个严重错误，建议立即修复止损计算和方向判断逻辑")
            if bv.get('invalid', 0) / max(bv.get('total', 1), 1) > 0.3:
                suggestions.append("Brooks验证失败率过高，建议检查信号生成逻辑，确保符合Brooks交易原则")
        
        return suggestions
