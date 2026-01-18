#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brooks交易规则验证器

基于Al Brooks交易原则，验证交易计划的合理性：
1. 止损位置验证
2. 盈亏比验证
3. 顺势交易验证
4. 模式-方向一致性验证
5. 稳定币过滤
6. 风险控制验证
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(Enum):
    """验证级别"""
    PASS = "pass"  # 通过
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重错误


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    level: ValidationLevel
    issues: List[str]
    warnings: List[str]
    score: float  # 0-100分


class BrooksTradingValidator:
    """Brooks交易规则验证器"""
    
    # 稳定币列表
    STABLECOINS = {'USDC', 'USDT', 'BUSD', 'DAI', 'TUSD', 'PAXG'}
    
    # 阈值配置
    MIN_RISK_REWARD_RATIO = 2.0  # 最低盈亏比2:1
    IDEAL_RISK_REWARD_RATIO = 3.0  # 理想盈亏比3:1
    
    MIN_STOP_LOSS_DISTANCE_PCT = 0.01  # 最低止损距离1%
    MIN_STOP_LOSS_DISTANCE_5M = 0.015  # 5分钟最低止损距离1.5%
    MIN_STOP_LOSS_DISTANCE_15M = 0.02  # 15分钟最低止损距离2%
    
    MAX_STOP_LOSS_PCT = 0.05  # 最大止损5%
    MAX_TAKE_PROFIT_PCT = 0.20  # 最大止盈20%（防止不现实的目标）
    
    STABLECOIN_MAX_MOVE_PCT = 0.001  # 稳定币最大波动0.1%
    
    def __init__(self):
        """初始化验证器"""
        pass
    
    def validate_signal(self, signal: Dict) -> ValidationResult:
        """
        验证交易信号
        
        Args:
            signal: 交易信号字典
        
        Returns:
            验证结果
        """
        issues = []
        warnings = []
        score = 100.0
        
        symbol = signal.get('symbol', '').upper()
        direction = signal.get('direction', 'long').lower()
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        take_profit_2 = signal.get('take_profit_2', 0)
        pattern_name = signal.get('pattern_name', '')
        pattern_type = signal.get('pattern_type', '')
        timeframe = signal.get('timeframe', '5m')
        
        if not all([entry_price, stop_loss, take_profit_1]):
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.CRITICAL,
                issues=["信号参数不完整"],
                warnings=[],
                score=0.0
            )
        
        # 1. 稳定币检查
        if symbol in self.STABLECOINS:
            issue = self._validate_stablecoin(signal)
            if issue:
                issues.append(issue)
                score -= 50.0
        
        # 2. 止损位置验证
        stop_loss_issues = self._validate_stop_loss(signal)
        issues.extend(stop_loss_issues)
        if stop_loss_issues:
            score -= len(stop_loss_issues) * 20.0
        
        # 3. 盈亏比验证
        rr_issues, rr_warnings = self._validate_risk_reward(signal)
        issues.extend(rr_issues)
        warnings.extend(rr_warnings)
        if rr_issues:
            score -= len(rr_issues) * 15.0
        if rr_warnings:
            score -= len(rr_warnings) * 5.0
        
        # 4. 顺势交易验证
        trend_issues = self._validate_trend_consistency(signal)
        issues.extend(trend_issues)
        if trend_issues:
            score -= len(trend_issues) * 25.0
        
        # 5. 模式-方向一致性验证
        pattern_issues = self._validate_pattern_direction_consistency(signal)
        issues.extend(pattern_issues)
        if pattern_issues:
            score -= len(pattern_issues) * 20.0
        
        # 6. 止损距离验证
        distance_warnings = self._validate_stop_loss_distance(signal, timeframe)
        warnings.extend(distance_warnings)
        if distance_warnings:
            score -= len(distance_warnings) * 5.0
        
        # 7. 止盈目标合理性验证
        target_warnings = self._validate_take_profit_targets(signal)
        warnings.extend(target_warnings)
        if target_warnings:
            score -= len(target_warnings) * 3.0
        
        # 确定验证级别
        if issues:
            if any('严重' in issue or '不可交易' in issue for issue in issues):
                level = ValidationLevel.CRITICAL
            else:
                level = ValidationLevel.ERROR
        elif warnings:
            level = ValidationLevel.WARNING
        else:
            level = ValidationLevel.PASS
        
        # 确保分数在0-100范围内
        score = max(0.0, min(100.0, score))
        
        return ValidationResult(
            is_valid=len(issues) == 0,
            level=level,
            issues=issues,
            warnings=warnings,
            score=score
        )
    
    def _validate_stablecoin(self, signal: Dict) -> Optional[str]:
        """验证稳定币信号"""
        symbol = signal.get('symbol', '').upper()
        if symbol not in self.STABLECOINS:
            return None
        
        entry_price = signal.get('entry_price', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        
        if entry_price > 0:
            move_pct = abs(take_profit_1 - entry_price) / entry_price
            if move_pct > self.STABLECOIN_MAX_MOVE_PCT:
                return f"稳定币{symbol}的止盈目标不现实（波动{move_pct:.1%}，稳定币通常波动<0.1%）"
        
        return None
    
    def _validate_stop_loss(self, signal: Dict) -> List[str]:
        """验证止损位置"""
        issues = []
        direction = signal.get('direction', 'long').lower()
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        
        if entry_price <= 0 or stop_loss <= 0:
            return ["入场价或止损价无效"]
        
        # 检查止损是否等于入场价
        if abs(stop_loss - entry_price) < entry_price * 0.0001:  # 允许微小误差
            issues.append("🚨 严重问题: 止损等于入场价，没有风险缓冲空间，几乎100%会被立即止损")
            return issues
        
        # 检查止损方向
        if direction == 'long':
            if stop_loss >= entry_price:
                issues.append(f"🚨 严重问题: 做多止损应在入场价下方，当前止损${stop_loss:,.2f} >= 入场价${entry_price:,.2f}")
        else:  # short
            if stop_loss <= entry_price:
                issues.append(f"🚨 严重问题: 做空止损应在入场价上方，当前止损${stop_loss:,.2f} <= 入场价${entry_price:,.2f}")
        
        return issues
    
    def _validate_risk_reward(self, signal: Dict) -> Tuple[List[str], List[str]]:
        """验证盈亏比"""
        issues = []
        warnings = []
        
        direction = signal.get('direction', 'long').lower()
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        
        if entry_price <= 0 or stop_loss <= 0 or take_profit_1 <= 0:
            return ["参数无效"], []
        
        # 计算风险
        if direction == 'long':
            risk = entry_price - stop_loss
            reward = take_profit_1 - entry_price
        else:  # short
            risk = stop_loss - entry_price
            reward = entry_price - take_profit_1
        
        # 检查风险是否为0
        if risk <= 0:
            issues.append("🚨 严重问题: 风险为0或负数，盈亏比无法计算，信号不可交易")
            return issues, warnings
        
        # 计算盈亏比
        if risk > 0:
            rr_ratio = reward / risk
        else:
            rr_ratio = 0
        
        # 验证盈亏比
        if rr_ratio < 1.0:
            issues.append(f"🚨 严重问题: 盈亏比不足1:1（当前{rr_ratio:.2f}:1），即使方向正确也无法盈利")
        elif rr_ratio < self.MIN_RISK_REWARD_RATIO:
            issues.append(f"⚠️ 盈亏比不足{self.MIN_RISK_REWARD_RATIO}:1（当前{rr_ratio:.2f}:1），建议至少{self.MIN_RISK_REWARD_RATIO}:1")
        elif rr_ratio < self.IDEAL_RISK_REWARD_RATIO:
            warnings.append(f"盈亏比{rr_ratio:.2f}:1，建议达到{self.IDEAL_RISK_REWARD_RATIO}:1以获得更好收益")
        
        return issues, warnings
    
    def _validate_trend_consistency(self, signal: Dict) -> List[str]:
        """验证顺势交易"""
        issues = []
        
        pattern_name = signal.get('pattern_name', '').lower()
        pattern_type = signal.get('pattern_type', '').lower()
        direction = signal.get('direction', 'long').lower()
        
        # 检查Bull模式是否做多
        if any(keyword in pattern_name or keyword in pattern_type for keyword in ['bull', 'ascending', '上升', '多头']):
            if direction == 'short':
                issues.append(f"🚨 严重问题: 识别为上升趋势模式（{pattern_name}），但交易方向是做空，这是逆势交易，风险极高")
        
        # 检查Bear模式是否做空
        if any(keyword in pattern_name or keyword in pattern_type for keyword in ['bear', 'descending', '下降', '空头']):
            if direction == 'long':
                issues.append(f"🚨 严重问题: 识别为下降趋势模式（{pattern_name}），但交易方向是做多，这是逆势交易，风险极高")
        
        return issues
    
    def _validate_pattern_direction_consistency(self, signal: Dict) -> List[str]:
        """验证模式-方向一致性"""
        issues = []
        
        pattern_name = signal.get('pattern_name', '').lower()
        pattern_type = signal.get('pattern_type', '').lower()
        direction = signal.get('direction', 'long').lower()
        
        # 上升通道应该做多
        if 'bull channel' in pattern_name or 'ascending channel' in pattern_name:
            if direction == 'short':
                issues.append("🚨 严重问题: 上升通道（Bull Channel）应该做多，而不是做空")
        
        # 下降通道应该做空
        if 'bear channel' in pattern_name or 'descending channel' in pattern_name:
            if direction == 'long':
                issues.append("🚨 严重问题: 下降通道（Bear Channel）应该做空，而不是做多")
        
        # 牛旗应该做多
        if 'bull flag' in pattern_name:
            if direction == 'short':
                issues.append("🚨 严重问题: 牛旗（Bull Flag）应该做多，而不是做空")
        
        # 熊旗应该做空
        if 'bear flag' in pattern_name:
            if direction == 'long':
                issues.append("🚨 严重问题: 熊旗（Bear Flag）应该做空，而不是做多")
        
        return issues
    
    def _validate_stop_loss_distance(self, signal: Dict, timeframe: str) -> List[str]:
        """验证止损距离"""
        warnings = []
        
        direction = signal.get('direction', 'long').lower()
        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        
        if entry_price <= 0 or stop_loss <= 0:
            return warnings
        
        # 计算止损距离
        if direction == 'long':
            distance_pct = (entry_price - stop_loss) / entry_price
        else:  # short
            distance_pct = (stop_loss - entry_price) / entry_price
        
        # 根据时间框架检查
        if '5m' in timeframe:
            min_distance = self.MIN_STOP_LOSS_DISTANCE_5M
            if distance_pct < min_distance:
                warnings.append(f"5分钟时间框架止损距离过小（{distance_pct:.1%}），建议至少{min_distance:.1%}，容易被市场噪音触发")
        elif '15m' in timeframe:
            min_distance = self.MIN_STOP_LOSS_DISTANCE_15M
            if distance_pct < min_distance:
                warnings.append(f"15分钟时间框架止损距离过小（{distance_pct:.1%}），建议至少{min_distance:.1%}，容易被市场噪音触发")
        else:
            min_distance = self.MIN_STOP_LOSS_DISTANCE_PCT
            if distance_pct < min_distance:
                warnings.append(f"止损距离过小（{distance_pct:.1%}），建议至少{min_distance:.1%}")
        
        # 检查止损是否过大
        if distance_pct > self.MAX_STOP_LOSS_PCT:
            warnings.append(f"止损距离过大（{distance_pct:.1%}），建议不超过{self.MAX_STOP_LOSS_PCT:.1%}")
        
        return warnings
    
    def _validate_take_profit_targets(self, signal: Dict) -> List[str]:
        """验证止盈目标合理性"""
        warnings = []
        
        entry_price = signal.get('entry_price', 0)
        take_profit_1 = signal.get('take_profit_1', 0)
        take_profit_2 = signal.get('take_profit_2', 0)
        
        if entry_price <= 0:
            return warnings
        
        # 检查止盈1
        if take_profit_1 > 0:
            tp1_pct = abs(take_profit_1 - entry_price) / entry_price
            if tp1_pct > self.MAX_TAKE_PROFIT_PCT:
                warnings.append(f"止盈1目标过大（{tp1_pct:.1%}），可能不现实，建议不超过{self.MAX_TAKE_PROFIT_PCT:.1%}")
        
        # 检查止盈2
        if take_profit_2 > 0:
            tp2_pct = abs(take_profit_2 - entry_price) / entry_price
            if tp2_pct > self.MAX_TAKE_PROFIT_PCT * 1.5:
                warnings.append(f"止盈2目标过大（{tp2_pct:.1%}），可能不现实")
        
        return warnings
    
    def validate_batch(self, signals: List[Dict]) -> Dict:
        """
        批量验证信号
        
        Args:
            signals: 信号列表
        
        Returns:
            验证统计
        """
        results = []
        stats = {
            'total': len(signals),
            'valid': 0,
            'invalid': 0,
            'critical': 0,
            'error': 0,
            'warning': 0,
            'pass': 0,
            'avg_score': 0.0
        }
        
        for signal in signals:
            result = self.validate_signal(signal)
            results.append(result)
            
            if result.is_valid:
                stats['valid'] += 1
            else:
                stats['invalid'] += 1
            
            if result.level == ValidationLevel.CRITICAL:
                stats['critical'] += 1
            elif result.level == ValidationLevel.ERROR:
                stats['error'] += 1
            elif result.level == ValidationLevel.WARNING:
                stats['warning'] += 1
            else:
                stats['pass'] += 1
            
            stats['avg_score'] += result.score
        
        if stats['total'] > 0:
            stats['avg_score'] /= stats['total']
        
        return {
            'results': results,
            'stats': stats
        }
