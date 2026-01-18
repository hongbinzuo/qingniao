#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
性能分析器

提供深度的回测结果分析，包括：
- 信号质量分析
- 市场环境分析
- 模式表现分析
- 风险评估
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import statistics


@dataclass
class SignalPerformance:
    """单个信号的表现"""
    symbol: str
    timeframe: str
    pattern_name: str
    pattern_type: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    result: str  # 'win', 'loss', 'breakeven', 'unknown'
    pnl: float
    return_pct: float
    risk_reward_ratio: float
    hold_time: Optional[int] = None  # 持仓时间（秒）


@dataclass
class PatternPerformance:
    """模式表现统计"""
    pattern_name: str
    pattern_type: str
    total_signals: int
    win_count: int
    loss_count: int
    win_rate: float
    avg_return_pct: float
    total_pnl: float
    avg_risk_reward: float
    best_signal: Optional[SignalPerformance] = None
    worst_signal: Optional[SignalPerformance] = None


@dataclass
class MarketCondition:
    """市场环境"""
    volatility: str  # 'high', 'medium', 'low'
    trend: str  # 'bullish', 'bearish', 'sideways'
    volume: str  # 'high', 'medium', 'low'


class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.signals: List[SignalPerformance] = []
        self.pattern_stats: Dict[str, PatternPerformance] = {}
    
    def add_signal_result(self, signal: Dict, backtest_result: Dict):
        """
        添加信号回测结果
        
        Args:
            signal: 原始信号
            backtest_result: 回测结果
        """
        if not backtest_result.get('success'):
            return
        
        status = backtest_result.get('status', 'unknown')
        pnl = backtest_result.get('net_pnl', 0.0)
        return_pct = backtest_result.get('return_pct', 0.0)
        
        # 计算风险回报比
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        direction = signal.get('direction', 'long').lower()
        
        if direction == 'long' and entry_price > stop_loss:
            risk = entry_price - stop_loss
            reward = take_profit_1 - entry_price
        elif direction == 'short' and stop_loss > entry_price:
            risk = stop_loss - entry_price
            reward = entry_price - take_profit_1
        else:
            risk = 0
            reward = 0
        
        risk_reward = reward / risk if risk > 0 else 0
        
        # 计算持仓时间
        hold_time = None
        if 'entry_time' in backtest_result and 'exit_time' in backtest_result:
            entry_time = backtest_result['entry_time']
            exit_time = backtest_result['exit_time']
            if entry_time and exit_time:
                hold_time = exit_time - entry_time
        
        signal_perf = SignalPerformance(
            symbol=signal.get('symbol', 'Unknown'),
            timeframe=signal.get('timeframe', '5m'),
            pattern_name=signal.get('pattern_name', 'Unknown'),
            pattern_type=signal.get('pattern_type', 'Unknown'),
            direction=signal.get('direction', 'long'),
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            result='win' if pnl > 0 else ('loss' if pnl < 0 else 'breakeven'),
            pnl=pnl,
            return_pct=return_pct,
            risk_reward_ratio=risk_reward,
            hold_time=hold_time
        )
        
        self.signals.append(signal_perf)
    
    def analyze_pattern_performance(self) -> Dict[str, PatternPerformance]:
        """
        分析模式表现
        
        Returns:
            模式表现统计
        """
        pattern_groups = defaultdict(lambda: {'signals': [], 'wins': 0, 'losses': 0})
        
        for signal in self.signals:
            pattern_key = f"{signal.pattern_name}_{signal.pattern_type}"
            pattern_groups[pattern_key]['signals'].append(signal)
            if signal.result == 'win':
                pattern_groups[pattern_key]['wins'] += 1
            elif signal.result == 'loss':
                pattern_groups[pattern_key]['losses'] += 1
        
        for pattern_key, group in pattern_groups.items():
            signals = group['signals']
            total = len(signals)
            wins = group['wins']
            losses = group['losses']
            
            win_rate = wins / total if total > 0 else 0
            avg_return = statistics.mean([s.return_pct for s in signals]) if signals else 0
            total_pnl = sum([s.pnl for s in signals])
            avg_rr = statistics.mean([s.risk_reward_ratio for s in signals if s.risk_reward_ratio > 0]) if signals else 0
            
            # 找到最佳和最差信号
            best_signal = max(signals, key=lambda s: s.pnl) if signals else None
            worst_signal = min(signals, key=lambda s: s.pnl) if signals else None
            
            pattern_perf = PatternPerformance(
                pattern_name=signals[0].pattern_name if signals else 'Unknown',
                pattern_type=signals[0].pattern_type if signals else 'Unknown',
                total_signals=total,
                win_count=wins,
                loss_count=losses,
                win_rate=win_rate,
                avg_return_pct=avg_return,
                total_pnl=total_pnl,
                avg_risk_reward=avg_rr,
                best_signal=best_signal,
                worst_signal=worst_signal
            )
            
            self.pattern_stats[pattern_key] = pattern_perf
        
        return self.pattern_stats
    
    def analyze_by_timeframe(self) -> Dict[str, Dict]:
        """
        按时间框架分析
        
        Returns:
            按时间框架的统计
        """
        timeframe_stats = defaultdict(lambda: {'signals': [], 'wins': 0, 'losses': 0, 'total_pnl': 0})
        
        for signal in self.signals:
            tf = signal.timeframe
            timeframe_stats[tf]['signals'].append(signal)
            if signal.result == 'win':
                timeframe_stats[tf]['wins'] += 1
            elif signal.result == 'loss':
                timeframe_stats[tf]['losses'] += 1
            timeframe_stats[tf]['total_pnl'] += signal.pnl
        
        result = {}
        for tf, stats in timeframe_stats.items():
            signals = stats['signals']
            total = len(signals)
            result[tf] = {
                'total_signals': total,
                'win_count': stats['wins'],
                'loss_count': stats['losses'],
                'win_rate': stats['wins'] / total if total > 0 else 0,
                'total_pnl': stats['total_pnl'],
                'avg_pnl': stats['total_pnl'] / total if total > 0 else 0,
                'avg_return_pct': statistics.mean([s.return_pct for s in signals]) if signals else 0
            }
        
        return result
    
    def analyze_by_symbol(self) -> Dict[str, Dict]:
        """
        按币种分析
        
        Returns:
            按币种的统计
        """
        symbol_stats = defaultdict(lambda: {'signals': [], 'wins': 0, 'losses': 0, 'total_pnl': 0})
        
        for signal in self.signals:
            symbol = signal.symbol
            symbol_stats[symbol]['signals'].append(signal)
            if signal.result == 'win':
                symbol_stats[symbol]['wins'] += 1
            elif signal.result == 'loss':
                symbol_stats[symbol]['losses'] += 1
            symbol_stats[symbol]['total_pnl'] += signal.pnl
        
        result = {}
        for symbol, stats in symbol_stats.items():
            signals = stats['signals']
            total = len(signals)
            result[symbol] = {
                'total_signals': total,
                'win_count': stats['wins'],
                'loss_count': stats['losses'],
                'win_rate': stats['wins'] / total if total > 0 else 0,
                'total_pnl': stats['total_pnl'],
                'avg_pnl': stats['total_pnl'] / total if total > 0 else 0,
                'avg_return_pct': statistics.mean([s.return_pct for s in signals]) if signals else 0
            }
        
        return result
    
    def identify_best_patterns(self, min_signals: int = 3) -> List[Tuple[str, PatternPerformance]]:
        """
        识别表现最好的模式
        
        Args:
            min_signals: 最少信号数
        
        Returns:
            按表现排序的模式列表
        """
        if not self.pattern_stats:
            self.analyze_pattern_performance()
        
        # 过滤最少信号数
        filtered = {
            k: v for k, v in self.pattern_stats.items()
            if v.total_signals >= min_signals
        }
        
        # 按综合得分排序（胜率 + 平均收益率）
        scored = [
            (k, v, v.win_rate * 0.5 + min(v.avg_return_pct * 10, 0.5))
            for k, v in filtered.items()
        ]
        
        scored.sort(key=lambda x: x[2], reverse=True)
        
        return [(k, v) for k, v, _ in scored]
    
    def identify_worst_patterns(self, min_signals: int = 3) -> List[Tuple[str, PatternPerformance]]:
        """
        识别表现最差的模式
        
        Args:
            min_signals: 最少信号数
        
        Returns:
            按表现排序的模式列表（从差到好）
        """
        if not self.pattern_stats:
            self.analyze_pattern_performance()
        
        # 过滤最少信号数
        filtered = {
            k: v for k, v in self.pattern_stats.items()
            if v.total_signals >= min_signals
        }
        
        # 按综合得分排序（胜率 + 平均收益率）
        scored = [
            (k, v, v.win_rate * 0.5 + min(v.avg_return_pct * 10, 0.5))
            for k, v in filtered.items()
        ]
        
        scored.sort(key=lambda x: x[2])  # 升序
        
        return [(k, v) for k, v, _ in scored]
    
    def generate_analysis_report(self) -> str:
        """
        生成分析报告
        
        Returns:
            Markdown格式的报告
        """
        lines = []
        lines.append("# 性能分析报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 总体统计
        total_signals = len(self.signals)
        wins = sum(1 for s in self.signals if s.result == 'win')
        losses = sum(1 for s in self.signals if s.result == 'loss')
        win_rate = wins / total_signals if total_signals > 0 else 0
        total_pnl = sum(s.pnl for s in self.signals)
        avg_return = statistics.mean([s.return_pct for s in self.signals]) if self.signals else 0
        
        lines.append("## 总体统计")
        lines.append("")
        lines.append(f"- **总信号数**: {total_signals}")
        lines.append(f"- **盈利信号**: {wins}")
        lines.append(f"- **亏损信号**: {losses}")
        lines.append(f"- **胜率**: {win_rate:.2%}")
        lines.append(f"- **总盈亏**: ${total_pnl:,.2f}")
        lines.append(f"- **平均收益率**: {avg_return:.2%}")
        lines.append("")
        
        # 按时间框架分析
        tf_stats = self.analyze_by_timeframe()
        if tf_stats:
            lines.append("## 按时间框架分析")
            lines.append("")
            for tf, stats in tf_stats.items():
                lines.append(f"### {tf}")
                lines.append("")
                lines.append(f"- **信号数**: {stats['total_signals']}")
                lines.append(f"- **胜率**: {stats['win_rate']:.2%}")
                lines.append(f"- **总盈亏**: ${stats['total_pnl']:,.2f}")
                lines.append(f"- **平均收益率**: {stats['avg_return_pct']:.2%}")
                lines.append("")
        
        # 按币种分析
        symbol_stats = self.analyze_by_symbol()
        if symbol_stats:
            lines.append("## 按币种分析")
            lines.append("")
            for symbol, stats in sorted(symbol_stats.items(), key=lambda x: x[1]['total_pnl'], reverse=True):
                lines.append(f"### {symbol}")
                lines.append("")
                lines.append(f"- **信号数**: {stats['total_signals']}")
                lines.append(f"- **胜率**: {stats['win_rate']:.2%}")
                lines.append(f"- **总盈亏**: ${stats['total_pnl']:,.2f}")
                lines.append(f"- **平均收益率**: {stats['avg_return_pct']:.2%}")
                lines.append("")
        
        # 最佳模式
        best_patterns = self.identify_best_patterns()
        if best_patterns:
            lines.append("## 表现最佳的模式（Top 5）")
            lines.append("")
            for i, (key, perf) in enumerate(best_patterns[:5], 1):
                lines.append(f"### {i}. {perf.pattern_name} ({perf.pattern_type})")
                lines.append("")
                lines.append(f"- **信号数**: {perf.total_signals}")
                lines.append(f"- **胜率**: {perf.win_rate:.2%}")
                lines.append(f"- **平均收益率**: {perf.avg_return_pct:.2%}")
                lines.append(f"- **总盈亏**: ${perf.total_pnl:,.2f}")
                lines.append("")
        
        # 最差模式
        worst_patterns = self.identify_worst_patterns()
        if worst_patterns:
            lines.append("## 表现最差的模式（Bottom 5）")
            lines.append("")
            for i, (key, perf) in enumerate(worst_patterns[:5], 1):
                lines.append(f"### {i}. {perf.pattern_name} ({perf.pattern_type})")
                lines.append("")
                lines.append(f"- **信号数**: {perf.total_signals}")
                lines.append(f"- **胜率**: {perf.win_rate:.2%}")
                lines.append(f"- **平均收益率**: {perf.avg_return_pct:.2%}")
                lines.append(f"- **总盈亏**: ${perf.total_pnl:,.2f}")
                lines.append("")
        
        return '\n'.join(lines)
