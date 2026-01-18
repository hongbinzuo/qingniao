#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反馈循环系统

收集回测结果，分析问题，生成改进建议，并自动调整系统参数。
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import json
import statistics
from collections import defaultdict


@dataclass
class BacktestFeedback:
    """回测反馈"""
    signal_id: str
    symbol: str
    timeframe: str
    pattern_name: str
    pattern_type: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    
    # 回测结果
    backtest_success: bool
    result: str  # 'win', 'loss', 'timeout', 'invalid'
    pnl: float
    return_pct: float
    duration_hours: float
    
    # 评估结果
    evaluation_score: float
    evaluation_quality: str
    evaluation_issues: List[str]
    
    # 问题分析
    failure_reason: Optional[str] = None
    improvement_suggestions: List[str] = field(default_factory=list)


@dataclass
class SystemImprovement:
    """系统改进建议"""
    category: str  # 'stop_loss', 'risk_reward', 'entry_timing', 'pattern_recognition'
    issue: str
    current_value: Optional[float] = None
    suggested_value: Optional[float] = None
    confidence: float = 0.0  # 0-1
    evidence_count: int = 0
    priority: str = 'medium'  # 'high', 'medium', 'low'


class FeedbackLoop:
    """反馈循环系统"""
    
    def __init__(self, feedback_dir: Optional[Path] = None):
        """
        初始化反馈循环系统
        
        Args:
            feedback_dir: 反馈数据存储目录
        """
        self.feedback_dir = feedback_dir or Path('outputs/feedback_loop')
        self.feedback_dir.mkdir(parents=True, exist_ok=True)
        
        self.feedback_history: List[BacktestFeedback] = []
        self.improvements: List[SystemImprovement] = []
        
        # 加载历史反馈
        self._load_feedback_history()
    
    def add_backtest_result(
        self,
        signal: Dict,
        backtest_result: Dict,
        evaluation: Optional[Dict] = None
    ):
        """
        添加回测结果
        
        Args:
            signal: 原始信号
            backtest_result: 回测结果
            evaluation: 评估结果（可选）
        """
        feedback = BacktestFeedback(
            signal_id=signal.get('pattern_id', f"{signal.get('symbol')}_{signal.get('timeframe')}"),
            symbol=signal.get('symbol', 'Unknown').upper(),
            timeframe=signal.get('timeframe', '5m'),
            pattern_name=signal.get('pattern_name', ''),
            pattern_type=signal.get('pattern_type', ''),
            direction=signal.get('direction', 'long'),
            entry_price=signal.get('entry_price', 0),
            stop_loss=signal.get('stop_loss', 0),
            take_profit_1=signal.get('take_profit_1', 0),
            take_profit_2=signal.get('take_profit_2', 0),
            backtest_success=backtest_result.get('success', False),
            result=self._determine_result(backtest_result),
            pnl=backtest_result.get('net_pnl', 0),
            return_pct=backtest_result.get('return_pct', 0),
            duration_hours=backtest_result.get('duration_hours', 0),
            evaluation_score=evaluation.get('score', 0) if evaluation else 0,
            evaluation_quality=evaluation.get('quality', 'unknown') if evaluation else 'unknown',
            evaluation_issues=evaluation.get('issues', []) if evaluation else []
        )
        
        # 分析失败原因
        if not feedback.backtest_success or feedback.result == 'loss':
            feedback.failure_reason = self._analyze_failure(signal, backtest_result, evaluation)
        
        # 生成改进建议
        feedback.improvement_suggestions = self._generate_improvement_suggestions(feedback)
        
        self.feedback_history.append(feedback)
        
        # 保存反馈
        self._save_feedback(feedback)
    
    def _determine_result(self, backtest_result: Dict) -> str:
        """确定回测结果"""
        if not backtest_result.get('success', False):
            return 'invalid'
        
        status = backtest_result.get('status', '')
        pnl = backtest_result.get('net_pnl', 0)
        
        if 'stop_loss' in status.lower() or 'stopped' in status.lower():
            return 'loss'
        elif 'take_profit' in status.lower() or 'completed' in status.lower():
            return 'win' if pnl > 0 else 'loss'
        elif 'timeout' in status.lower():
            return 'timeout'
        else:
            return 'win' if pnl > 0 else 'loss'
    
    def _analyze_failure(
        self,
        signal: Dict,
        backtest_result: Dict,
        evaluation: Optional[Dict]
    ) -> str:
        """分析失败原因"""
        reasons = []
        
        # 检查评估问题
        if evaluation and evaluation.get('issues'):
            reasons.extend(evaluation['issues'][:2])
        
        # 检查回测原因
        backtest_reason = backtest_result.get('reason', '')
        if backtest_reason:
            reasons.append(backtest_reason)
        
        # 检查止损触发
        if 'stop_loss' in backtest_result.get('exit_reason', '').lower():
            reasons.append("触发止损")
        
        # 检查盈亏比
        direction = signal.get('direction', 'long').lower()
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        
        if entry_price > 0 and stop_loss > 0 and take_profit_1 > 0:
            if direction == 'long':
                risk = entry_price - stop_loss
                reward = take_profit_1 - entry_price
            else:
                risk = stop_loss - entry_price
                reward = entry_price - take_profit_1
            
            if risk > 0:
                rr_ratio = reward / risk
                if rr_ratio < 2.0:
                    reasons.append(f"盈亏比不足（{rr_ratio:.2f}:1）")
        
        return '; '.join(reasons) if reasons else '未知原因'
    
    def _generate_improvement_suggestions(self, feedback: BacktestFeedback) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 基于失败原因生成建议
        if feedback.failure_reason:
            if '止损' in feedback.failure_reason:
                suggestions.append("考虑放宽止损距离，减少被市场噪音触发")
            if '盈亏比' in feedback.failure_reason:
                suggestions.append("提高止盈目标，确保至少2:1盈亏比")
            if '过期' in feedback.failure_reason or '入场' in feedback.failure_reason:
                suggestions.append("改进入场时机判断，避免信号过期")
        
        # 基于评估问题生成建议
        for issue in feedback.evaluation_issues:
            if '止损距离' in issue:
                suggestions.append("调整止损计算逻辑，考虑币种波动性")
            if '逆势' in issue:
                suggestions.append("改进模式-方向一致性检查")
            if '模式识别' in issue:
                suggestions.append("改进模式识别，提供更具体的模式信息")
        
        return suggestions
    
    def analyze_feedback(self) -> List[SystemImprovement]:
        """
        分析反馈历史，生成系统改进建议
        
        Returns:
            改进建议列表
        """
        if not self.feedback_history:
            return []
        
        improvements = []
        
        # 1. 分析止损问题
        stop_loss_issues = self._analyze_stop_loss_issues()
        improvements.extend(stop_loss_issues)
        
        # 2. 分析盈亏比问题
        risk_reward_issues = self._analyze_risk_reward_issues()
        improvements.extend(risk_reward_issues)
        
        # 3. 分析入场时机问题
        entry_timing_issues = self._analyze_entry_timing_issues()
        improvements.extend(entry_timing_issues)
        
        # 4. 分析模式识别问题
        pattern_recognition_issues = self._analyze_pattern_recognition_issues()
        improvements.extend(pattern_recognition_issues)
        
        # 按优先级排序
        improvements.sort(key=lambda x: (
            {'high': 0, 'medium': 1, 'low': 2}.get(x.priority, 1),
            -x.confidence,
            -x.evidence_count
        ))
        
        self.improvements = improvements
        return improvements
    
    def _analyze_stop_loss_issues(self) -> List[SystemImprovement]:
        """分析止损问题"""
        improvements = []
        
        # 统计止损触发情况
        stop_loss_failures = [
            f for f in self.feedback_history
            if '止损' in f.failure_reason or 'stop_loss' in f.failure_reason.lower()
        ]
        
        if len(stop_loss_failures) > len(self.feedback_history) * 0.3:  # 超过30%因止损失败
            # 分析止损距离
            stop_distances = []
            for f in stop_loss_failures:
                if f.entry_price > 0 and f.stop_loss > 0:
                    if f.direction == 'long':
                        dist = (f.entry_price - f.stop_loss) / f.entry_price
                    else:
                        dist = (f.stop_loss - f.entry_price) / f.entry_price
                    stop_distances.append(dist)
            
            if stop_distances:
                avg_distance = statistics.mean(stop_distances)
                improvements.append(SystemImprovement(
                    category='stop_loss',
                    issue='止损距离过小，导致频繁触发',
                    current_value=avg_distance,
                    suggested_value=avg_distance * 1.5,  # 建议增加50%
                    confidence=min(1.0, len(stop_loss_failures) / len(self.feedback_history)),
                    evidence_count=len(stop_loss_failures),
                    priority='high' if len(stop_loss_failures) > len(self.feedback_history) * 0.4 else 'medium'
                ))
        
        return improvements
    
    def _analyze_risk_reward_issues(self) -> List[SystemImprovement]:
        """分析盈亏比问题"""
        improvements = []
        
        # 统计盈亏比不足的情况
        low_rr_failures = []
        for f in self.feedback_history:
            if f.entry_price > 0 and f.stop_loss > 0 and f.take_profit_1 > 0:
                if f.direction == 'long':
                    risk = f.entry_price - f.stop_loss
                    reward = f.take_profit_1 - f.entry_price
                else:
                    risk = f.stop_loss - f.entry_price
                    reward = f.entry_price - f.take_profit_1
                
                if risk > 0:
                    rr_ratio = reward / risk
                    if rr_ratio < 2.0 and f.result == 'loss':
                        low_rr_failures.append((f, rr_ratio))
        
        if len(low_rr_failures) > len(self.feedback_history) * 0.2:  # 超过20%
            avg_rr = statistics.mean([rr for _, rr in low_rr_failures])
            improvements.append(SystemImprovement(
                category='risk_reward',
                issue='盈亏比不足，导致即使方向正确也无法盈利',
                current_value=avg_rr,
                suggested_value=2.5,  # 建议至少2.5:1
                confidence=min(1.0, len(low_rr_failures) / len(self.feedback_history)),
                evidence_count=len(low_rr_failures),
                priority='high' if len(low_rr_failures) > len(self.feedback_history) * 0.3 else 'medium'
            ))
        
        return improvements
    
    def _analyze_entry_timing_issues(self) -> List[SystemImprovement]:
        """分析入场时机问题"""
        improvements = []
        
        # 统计信号过期情况
        expired_signals = [
            f for f in self.feedback_history
            if '过期' in f.failure_reason or 'expired' in f.failure_reason.lower()
        ]
        
        if len(expired_signals) > len(self.feedback_history) * 0.15:  # 超过15%
            improvements.append(SystemImprovement(
                category='entry_timing',
                issue='信号生成后价格已变化，入场时机判断不准确',
                confidence=min(1.0, len(expired_signals) / len(self.feedback_history)),
                evidence_count=len(expired_signals),
                priority='medium'
            ))
        
        return improvements
    
    def _analyze_pattern_recognition_issues(self) -> List[SystemImprovement]:
        """分析模式识别问题"""
        improvements = []
        
        # 统计模式识别信息不足的情况
        poor_pattern_signals = [
            f for f in self.feedback_history
            if f.pattern_name.lower() in ['informational', 'unknown', ''] or
            '模式识别' in ' '.join(f.evaluation_issues)
        ]
        
        if len(poor_pattern_signals) > len(self.feedback_history) * 0.2:  # 超过20%
            improvements.append(SystemImprovement(
                category='pattern_recognition',
                issue='模式识别信息不足，无法准确判断价格行为',
                confidence=min(1.0, len(poor_pattern_signals) / len(self.feedback_history)),
                evidence_count=len(poor_pattern_signals),
                priority='medium'
            ))
        
        return improvements
    
    def generate_improvement_report(self) -> str:
        """生成改进报告"""
        improvements = self.analyze_feedback()
        stats = self._get_statistics()
        
        lines = []
        lines.append("# 系统改进建议报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 统计信息
        lines.append("## 反馈统计")
        lines.append("")
        lines.append(f"- **总反馈数**: {stats['total_feedbacks']}")
        lines.append(f"- **成功交易**: {stats['win_count']}")
        lines.append(f"- **失败交易**: {stats['loss_count']}")
        lines.append(f"- **胜率**: {stats['win_rate']:.1%}")
        lines.append(f"- **平均收益率**: {stats['avg_return_pct']:.2%}")
        lines.append("")
        
        # 改进建议
        if improvements:
            lines.append("## 系统改进建议")
            lines.append("")
            
            high_priority = [i for i in improvements if i.priority == 'high']
            medium_priority = [i for i in improvements if i.priority == 'medium']
            low_priority = [i for i in improvements if i.priority == 'low']
            
            if high_priority:
                lines.append("### 🚨 高优先级")
                lines.append("")
                for i, imp in enumerate(high_priority, 1):
                    lines.append(f"{i}. **{imp.category}** - {imp.issue}")
                    if imp.current_value is not None:
                        lines.append(f"   - 当前值: {imp.current_value:.2%}" if imp.category in ['stop_loss', 'risk_reward'] else f"   - 当前值: {imp.current_value}")
                    if imp.suggested_value is not None:
                        lines.append(f"   - 建议值: {imp.suggested_value:.2%}" if imp.category in ['stop_loss', 'risk_reward'] else f"   - 建议值: {imp.suggested_value}")
                    lines.append(f"   - 置信度: {imp.confidence:.1%}")
                    lines.append(f"   - 证据数: {imp.evidence_count}")
                    lines.append("")
            
            if medium_priority:
                lines.append("### ⚠️ 中优先级")
                lines.append("")
                for i, imp in enumerate(medium_priority, 1):
                    lines.append(f"{i}. **{imp.category}** - {imp.issue}")
                    lines.append(f"   - 置信度: {imp.confidence:.1%}")
                    lines.append(f"   - 证据数: {imp.evidence_count}")
                    lines.append("")
            
            if low_priority:
                lines.append("### 💡 低优先级")
                lines.append("")
                for i, imp in enumerate(low_priority, 1):
                    lines.append(f"{i}. **{imp.category}** - {imp.issue}")
                    lines.append("")
        else:
            lines.append("## 系统改进建议")
            lines.append("")
            lines.append("暂无改进建议，系统运行良好。")
            lines.append("")
        
        return '\n'.join(lines)
    
    def _get_statistics(self) -> Dict:
        """获取统计信息"""
        if not self.feedback_history:
            return {
                'total_feedbacks': 0,
                'win_count': 0,
                'loss_count': 0,
                'win_rate': 0.0,
                'avg_return_pct': 0.0
            }
        
        wins = [f for f in self.feedback_history if f.result == 'win']
        losses = [f for f in self.feedback_history if f.result == 'loss']
        
        return_pcts = [f.return_pct for f in self.feedback_history if f.result == 'win']
        
        return {
            'total_feedbacks': len(self.feedback_history),
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_rate': len(wins) / len(self.feedback_history) if self.feedback_history else 0,
            'avg_return_pct': statistics.mean(return_pcts) if return_pcts else 0.0
        }
    
    def _save_feedback(self, feedback: BacktestFeedback):
        """保存反馈"""
        feedback_file = self.feedback_dir / f"feedback_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        feedback_dict = {
            'signal_id': feedback.signal_id,
            'symbol': feedback.symbol,
            'timeframe': feedback.timeframe,
            'backtest_success': feedback.backtest_success,
            'result': feedback.result,
            'pnl': feedback.pnl,
            'return_pct': feedback.return_pct,
            'evaluation_score': feedback.evaluation_score,
            'evaluation_quality': feedback.evaluation_quality,
            'failure_reason': feedback.failure_reason,
            'improvement_suggestions': feedback.improvement_suggestions,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(feedback_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(feedback_dict, ensure_ascii=False) + '\n')
    
    def _load_feedback_history(self):
        """加载历史反馈"""
        # 加载最近30天的反馈
        for i in range(30):
            date_str = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            feedback_file = self.feedback_dir / f"feedback_{date_str}.jsonl"
            if feedback_file.exists():
                try:
                    with open(feedback_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            data = json.loads(line)
                            # 可以在这里重建BacktestFeedback对象
                except Exception:
                    pass
