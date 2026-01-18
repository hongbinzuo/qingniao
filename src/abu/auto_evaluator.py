#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动评估器

基于价格行为交易原则，自动评估交易信号的质量。
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import statistics


class SignalQuality(Enum):
    """信号质量等级"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"  # 良好
    FAIR = "fair"  # 一般
    POOR = "poor"  # 较差
    INVALID = "invalid"  # 无效


@dataclass
class SignalEvaluation:
    """信号评估结果"""
    signal_id: str
    symbol: str
    timeframe: str
    quality: SignalQuality
    score: float  # 0-100分
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    is_tradable: bool = True
    adjusted_params: Optional[Dict] = None  # 调整后的参数


class AutoEvaluator:
    """自动评估器"""
    
    # 阈值配置
    MIN_STOP_LOSS_5M = 0.02  # 5分钟最低止损2%
    MIN_STOP_LOSS_15M = 0.025  # 15分钟最低止损2.5%
    IDEAL_STOP_LOSS_5M = 0.025  # 5分钟理想止损2.5%
    IDEAL_STOP_LOSS_15M = 0.03  # 15分钟理想止损3%
    
    MIN_RISK_REWARD = 2.0  # 最低盈亏比2:1
    IDEAL_RISK_REWARD = 3.0  # 理想盈亏比3:1
    
    HIGH_VOLATILITY_COINS = {'DOGE', 'SHIB', 'SOL', 'XRP', 'ADA', 'TRX'}
    
    def __init__(self):
        """初始化评估器"""
        self.evaluation_history: List[SignalEvaluation] = []
    
    def evaluate_signal(self, signal: Dict, current_price: Optional[float] = None) -> SignalEvaluation:
        """
        评估单个信号
        
        Args:
            signal: 交易信号字典
            current_price: 当前市场价格（可选，用于检查信号是否过期）
        
        Returns:
            评估结果
        """
        symbol = signal.get('symbol', 'Unknown').upper()
        timeframe = signal.get('timeframe', '5m')
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        take_profit_2 = signal.get('take_profit_2', 0)
        direction = signal.get('direction', 'long').lower()
        pattern_name = signal.get('pattern_name', '')
        pattern_type = signal.get('pattern_type', '')
        
        # 初始化评估
        evaluation = SignalEvaluation(
            signal_id=f"{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol=symbol,
            timeframe=timeframe,
            quality=SignalQuality.FAIR,
            score=100.0
        )
        
        # 1. 检查基本有效性
        if not self._check_basic_validity(signal, evaluation):
            evaluation.quality = SignalQuality.INVALID
            evaluation.is_tradable = False
            evaluation.score = 0.0
            return evaluation
        
        # 2. 检查止损位置
        self._evaluate_stop_loss(signal, evaluation, current_price)
        
        # 3. 检查盈亏比
        self._evaluate_risk_reward(signal, evaluation)
        
        # 4. 检查入场时机
        self._evaluate_entry_timing(signal, evaluation, current_price)
        
        # 5. 检查模式识别
        self._evaluate_pattern_recognition(signal, evaluation)
        
        # 6. 检查市场环境
        self._evaluate_market_conditions(signal, evaluation)
        
        # 7. 生成调整建议
        self._generate_adjustments(signal, evaluation)
        
        # 8. 确定质量等级
        self._determine_quality(evaluation)
        
        # 保存到历史
        self.evaluation_history.append(evaluation)
        
        return evaluation
    
    def _check_basic_validity(self, signal: Dict, evaluation: SignalEvaluation) -> bool:
        """检查基本有效性"""
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        direction = signal.get('direction', 'long').lower()
        
        # 检查价格是否有效
        if entry_price <= 0 or stop_loss <= 0 or take_profit_1 <= 0:
            evaluation.issues.append("价格参数无效（<=0）")
            return False
        
        # 检查止损是否等于入场价
        if abs(stop_loss - entry_price) < entry_price * 0.0001:
            evaluation.issues.append("🚨 严重问题: 止损等于入场价，没有风险缓冲空间，不可交易")
            return False
        
        # 检查止损方向
        if direction == 'long' and stop_loss >= entry_price:
            evaluation.issues.append("🚨 严重问题: 做多止损应在入场价下方")
            return False
        
        if direction == 'short' and stop_loss <= entry_price:
            evaluation.issues.append("🚨 严重问题: 做空止损应在入场价上方")
            return False
        
        return True
    
    def _evaluate_stop_loss(self, signal: Dict, evaluation: SignalEvaluation, current_price: Optional[float]):
        """评估止损位置"""
        symbol = signal.get('symbol', '').upper()
        timeframe = signal.get('timeframe', '5m')
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        direction = signal.get('direction', 'long').lower()
        
        # 计算止损距离
        if direction == 'long':
            stop_distance_pct = (entry_price - stop_loss) / entry_price
        else:
            stop_distance_pct = (stop_loss - entry_price) / entry_price
        
        # 根据时间框架检查
        is_high_volatility = symbol in self.HIGH_VOLATILITY_COINS
        
        if '5m' in timeframe:
            min_distance = self.MIN_STOP_LOSS_5M
            ideal_distance = self.IDEAL_STOP_LOSS_5M
            if is_high_volatility:
                min_distance = 0.03  # 高波动币种至少3%
                ideal_distance = 0.04  # 理想4%
        elif '15m' in timeframe:
            min_distance = self.MIN_STOP_LOSS_15M
            ideal_distance = self.IDEAL_STOP_LOSS_15M
            if is_high_volatility:
                min_distance = 0.035  # 高波动币种至少3.5%
                ideal_distance = 0.045  # 理想4.5%
        else:
            min_distance = 0.02
            ideal_distance = 0.025
        
        # 评估
        if stop_distance_pct < min_distance:
            evaluation.issues.append(
                f"止损距离过小（{stop_distance_pct:.1%}），{timeframe}时间框架建议至少{min_distance:.1%}，"
                f"{'高波动币种' if is_high_volatility else ''}容易被市场噪音触发"
            )
            evaluation.score -= 20.0
            
            # 生成调整建议
            if direction == 'long':
                adjusted_stop = entry_price * (1 - min_distance)
            else:
                adjusted_stop = entry_price * (1 + min_distance)
            
            evaluation.adjusted_params = evaluation.adjusted_params or {}
            evaluation.adjusted_params['stop_loss'] = adjusted_stop
            evaluation.recommendations.append(
                f"建议止损调整到${adjusted_stop:,.2f}（{min_distance:.1%}）"
            )
        elif stop_distance_pct < ideal_distance:
            evaluation.warnings.append(
                f"止损距离{stop_distance_pct:.1%}，建议达到{ideal_distance:.1%}以获得更好缓冲"
            )
            evaluation.score -= 5.0
        else:
            evaluation.strengths.append(f"止损距离合理（{stop_distance_pct:.1%}）")
    
    def _evaluate_risk_reward(self, signal: Dict, evaluation: SignalEvaluation):
        """评估盈亏比"""
        direction = signal.get('direction', 'long').lower()
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        
        # 计算风险
        if direction == 'long':
            risk = entry_price - stop_loss
            reward = take_profit_1 - entry_price
        else:
            risk = stop_loss - entry_price
            reward = entry_price - take_profit_1
        
        if risk <= 0:
            evaluation.issues.append("风险为0或负数，盈亏比无法计算")
            evaluation.score -= 30.0
            return
        
        rr_ratio = reward / risk
        
        # 评估
        if rr_ratio < 1.0:
            evaluation.issues.append(f"盈亏比不足1:1（当前{rr_ratio:.2f}:1），即使方向正确也无法盈利")
            evaluation.score -= 30.0
        elif rr_ratio < self.MIN_RISK_REWARD:
            evaluation.issues.append(f"盈亏比不足{self.MIN_RISK_REWARD}:1（当前{rr_ratio:.2f}:1），建议至少{self.MIN_RISK_REWARD}:1")
            evaluation.score -= 15.0
        elif rr_ratio < self.IDEAL_RISK_REWARD:
            evaluation.warnings.append(f"盈亏比{rr_ratio:.2f}:1，建议达到{self.IDEAL_RISK_REWARD}:1以获得更好收益")
            evaluation.score -= 5.0
        else:
            evaluation.strengths.append(f"盈亏比优秀（{rr_ratio:.2f}:1）")
    
    def _evaluate_entry_timing(self, signal: Dict, evaluation: SignalEvaluation, current_price: Optional[float]):
        """评估入场时机"""
        if current_price is None:
            return
        
        entry_price = signal.get('entry_price', 0)
        direction = signal.get('direction', 'long').lower()
        
        if entry_price <= 0:
            return
        
        # 检查信号是否过期
        price_diff_pct = abs(current_price - entry_price) / entry_price
        
        if direction == 'long':
            if current_price > entry_price * 1.02:  # 价格已上涨超过2%
                evaluation.warnings.append(
                    f"入场价${entry_price:,.2f}低于当前价${current_price:,.2f}（{price_diff_pct:.1%}），"
                    f"信号可能已过期，建议等待回调或寻找新的入场点"
                )
                evaluation.score -= 10.0
            elif current_price < entry_price * 0.98:  # 价格已下跌超过2%
                evaluation.warnings.append(
                    f"入场价${entry_price:,.2f}高于当前价${current_price:,.2f}（{price_diff_pct:.1%}），"
                    f"价格已回调，可以考虑入场"
                )
        else:  # short
            if current_price < entry_price * 0.98:  # 价格已下跌超过2%
                evaluation.warnings.append(
                    f"入场价${entry_price:,.2f}高于当前价${current_price:,.2f}（{price_diff_pct:.1%}），"
                    f"信号可能已过期，建议等待反弹或寻找新的入场点"
                )
                evaluation.score -= 10.0
            elif current_price > entry_price * 1.02:  # 价格已上涨超过2%
                evaluation.warnings.append(
                    f"入场价${entry_price:,.2f}低于当前价${current_price:,.2f}（{price_diff_pct:.1%}），"
                    f"价格已反弹，可以考虑入场"
                )
    
    def _evaluate_pattern_recognition(self, signal: Dict, evaluation: SignalEvaluation):
        """评估模式识别"""
        pattern_name = signal.get('pattern_name', '').lower()
        pattern_type = signal.get('pattern_type', '').lower()
        
        # 检查模式信息是否充足
        if pattern_name in ['informational', 'unknown', ''] or pattern_type in ['informational', 'unknown', '']:
            evaluation.warnings.append("模式识别信息不足（'informational'），无法判断具体的价格行为模式")
            evaluation.score -= 10.0
        
        # 检查模式-方向一致性
        direction = signal.get('direction', 'long').lower()
        is_bull_pattern = any(kw in pattern_name or kw in pattern_type 
                            for kw in ['bull', 'ascending', '上升', '多头', 'small pullback bull'])
        is_bear_pattern = any(kw in pattern_name or kw in pattern_type 
                            for kw in ['bear', 'descending', '下降', '空头'])
        
        if is_bull_pattern and direction == 'short':
            evaluation.issues.append("识别为上升趋势模式，但交易方向是做空，这是逆势交易")
            evaluation.score -= 25.0
        elif is_bear_pattern and direction == 'long':
            evaluation.issues.append("识别为下降趋势模式，但交易方向是做多，这是逆势交易")
            evaluation.score -= 25.0
        elif is_bull_pattern and direction == 'long':
            evaluation.strengths.append("模式-方向一致性良好（上升趋势做多）")
        elif is_bear_pattern and direction == 'short':
            evaluation.strengths.append("模式-方向一致性良好（下降趋势做空）")
    
    def _evaluate_market_conditions(self, signal: Dict, evaluation: SignalEvaluation):
        """评估市场环境"""
        symbol = signal.get('symbol', '').upper()
        
        # 检查稳定币
        if symbol in {'USDC', 'USDT', 'BUSD', 'DAI', 'TUSD', 'PAXG'}:
            take_profit_1 = signal.get('take_profit_1', 0)
            entry_price = signal.get('entry_price', 0)
            if entry_price > 0:
                move_pct = abs(take_profit_1 - entry_price) / entry_price
                if move_pct > 0.001:  # 0.1%
                    evaluation.issues.append(
                        f"稳定币{symbol}的止盈目标不现实（波动{move_pct:.1%}，稳定币通常波动<0.1%）"
                    )
                    evaluation.score -= 30.0
                    evaluation.is_tradable = False
    
    def _generate_adjustments(self, signal: Dict, evaluation: SignalEvaluation):
        """生成调整建议"""
        if not evaluation.adjusted_params:
            evaluation.adjusted_params = {}
        
        # 如果止损需要调整，已经在_evaluate_stop_loss中处理
        # 这里可以添加其他调整建议
        
        # 如果盈亏比不足，建议调整止盈
        direction = signal.get('direction', 'long').lower()
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        
        if entry_price > 0 and stop_loss > 0:
            if direction == 'long':
                risk = entry_price - stop_loss
            else:
                risk = stop_loss - entry_price
            
            if risk > 0:
                current_reward = abs(take_profit_1 - entry_price)
                current_rr = current_reward / risk
                
                if current_rr < self.IDEAL_RISK_REWARD:
                    ideal_reward = risk * self.IDEAL_RISK_REWARD
                    if direction == 'long':
                        ideal_tp1 = entry_price + ideal_reward
                    else:
                        ideal_tp1 = entry_price - ideal_reward
                    
                    if 'take_profit_1' not in evaluation.adjusted_params:
                        evaluation.adjusted_params['take_profit_1'] = ideal_tp1
                        evaluation.recommendations.append(
                            f"建议止盈1调整到${ideal_tp1:,.2f}以获得{self.IDEAL_RISK_REWARD}:1盈亏比"
                        )
    
    def _determine_quality(self, evaluation: SignalEvaluation):
        """确定质量等级"""
        score = max(0.0, min(100.0, evaluation.score))
        evaluation.score = score
        
        if score >= 85:
            evaluation.quality = SignalQuality.EXCELLENT
        elif score >= 70:
            evaluation.quality = SignalQuality.GOOD
        elif score >= 50:
            evaluation.quality = SignalQuality.FAIR
        elif score >= 30:
            evaluation.quality = SignalQuality.POOR
        else:
            evaluation.quality = SignalQuality.INVALID
            evaluation.is_tradable = False
    
    def evaluate_batch(self, signals: List[Dict], current_prices: Optional[Dict[str, float]] = None) -> List[SignalEvaluation]:
        """
        批量评估信号
        
        Args:
            signals: 信号列表
            current_prices: 当前价格字典 {symbol: price}
        
        Returns:
            评估结果列表
        """
        evaluations = []
        for signal in signals:
            symbol = signal.get('symbol', 'Unknown').upper()
            current_price = current_prices.get(symbol) if current_prices else None
            evaluation = self.evaluate_signal(signal, current_price)
            evaluations.append(evaluation)
        
        return evaluations
    
    def get_statistics(self) -> Dict:
        """获取评估统计"""
        if not self.evaluation_history:
            return {
                'total_evaluated': 0,
                'average_score': 0.0,
                'quality_distribution': {}
            }
        
        total = len(self.evaluation_history)
        quality_counts = {}
        for q in SignalQuality:
            quality_counts[q.value] = sum(1 for e in self.evaluation_history if e.quality == q)
        
        avg_score = statistics.mean([e.score for e in self.evaluation_history])
        tradable_count = sum(1 for e in self.evaluation_history if e.is_tradable)
        
        return {
            'total_evaluated': total,  # 添加total_evaluated字段以兼容
            'total_signals': total,
            'tradable_signals': tradable_count,
            'quality_distribution': quality_counts,
            'average_score': avg_score,
            'excellent_count': quality_counts.get(SignalQuality.EXCELLENT.value, 0),
            'good_count': quality_counts.get(SignalQuality.GOOD.value, 0),
            'fair_count': quality_counts.get(SignalQuality.FAIR.value, 0),
            'poor_count': quality_counts.get(SignalQuality.POOR.value, 0),
            'invalid_count': quality_counts.get(SignalQuality.INVALID.value, 0)
        }
