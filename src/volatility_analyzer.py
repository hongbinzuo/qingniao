#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
波动率分析模块
计算ATR、历史波动率等指标，用于评估市场波动性和调整止损止盈
"""

import math
from typing import List, Dict, Optional


def calculate_atr(klines: List[Dict], period: int = 14) -> Optional[float]:
    """
    计算ATR（Average True Range，平均真实波幅）
    
    ATR是衡量市场波动性的重要指标，可以用于：
    1. 设置止损距离（通常为1-2倍ATR）
    2. 评估市场波动性（高ATR = 高波动）
    3. 调整止盈距离（高波动时止盈可以更宽）
    
    Args:
        klines: K线数据列表，每个元素包含 'high', 'low', 'close'
        period: 计算周期，默认14
    
    Returns:
        ATR值（价格单位），如果数据不足返回None
    """
    if len(klines) < period + 1:
        return None
    
    true_ranges = []
    for i in range(1, len(klines)):
        high = klines[i]['high']
        low = klines[i]['low']
        prev_close = klines[i-1]['close']
        
        # True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)
    
    # 计算ATR（简单移动平均）
    if len(true_ranges) < period:
        return None
    
    atr = sum(true_ranges[-period:]) / period
    return atr


def calculate_atr_percent(klines: List[Dict], period: int = 14) -> Optional[float]:
    """
    计算ATR百分比（相对于当前价格）
    
    Returns:
        ATR百分比，例如 0.5 表示0.5%
    """
    if len(klines) < period + 1:
        return None
    
    atr = calculate_atr(klines, period)
    if atr is None:
        return None
    
    current_price = klines[-1]['close']
    atr_percent = (atr / current_price) * 100
    return atr_percent


def calculate_historical_volatility(klines: List[Dict], period: int = 20) -> Optional[float]:
    """
    计算历史波动率（基于收益率标准差）
    
    Args:
        klines: K线数据列表
        period: 计算周期
    
    Returns:
        历史波动率（年化百分比），例如 30.0 表示30%
    """
    if len(klines) < period + 1:
        return None
    
    # 计算收益率
    returns = []
    for i in range(1, len(klines)):
        prev_close = klines[i-1]['close']
        curr_close = klines[i]['close']
        if prev_close > 0:
            ret = (curr_close - prev_close) / prev_close
            returns.append(ret)
    
    if len(returns) < period:
        return None
    
    # 计算标准差
    recent_returns = returns[-period:]
    mean_return = sum(recent_returns) / len(recent_returns)
    variance = sum((r - mean_return) ** 2 for r in recent_returns) / len(recent_returns)
    std_dev = math.sqrt(variance)
    
    # 年化波动率（假设252个交易日）
    # 对于5分钟K线：252 * 288 = 72576 个5分钟K线/年
    # 对于15分钟K线：252 * 96 = 24192 个15分钟K线/年
    # 对于1小时K线：252 * 24 = 6048 个1小时K线/年
    
    # 简化：使用周期数估算年化因子
    # 假设每天有288个5分钟K线，252个交易日
    timeframe_multiplier = {
        '5分钟': 288 * 252,
        '15分钟': 96 * 252,
        '1小时': 24 * 252,
    }
    
    # 默认使用5分钟
    annualization_factor = math.sqrt(288 * 252 / period)
    annualized_volatility = std_dev * annualization_factor * 100
    
    return annualized_volatility


def assess_volatility_level(atr_percent: Optional[float]) -> Dict[str, any]:
    """
    评估波动率水平
    
    Returns:
        包含波动率等级、建议等的字典
    """
    if atr_percent is None:
        return {
            'level': 'unknown',
            'description': '数据不足',
            'stop_loss_multiplier': 1.0,
            'take_profit_multiplier': 1.0,
            'recommendation': '无法评估'
        }
    
    # BTC的波动率参考值（基于历史数据）
    # 低波动：ATR < 0.3%
    # 中等波动：0.3% <= ATR < 0.6%
    # 高波动：0.6% <= ATR < 1.0%
    # 极高波动：ATR >= 1.0%
    
    if atr_percent < 0.3:
        level = 'low'
        description = '低波动'
        stop_loss_multiplier = 0.8  # 低波动时止损可以更紧
        take_profit_multiplier = 1.0
        recommendation = '市场波动较小，止损可以设置较紧，止盈按正常设置'
    elif atr_percent < 0.6:
        level = 'medium'
        description = '中等波动'
        stop_loss_multiplier = 1.0
        take_profit_multiplier = 1.0
        recommendation = '市场波动正常，按标准设置止损止盈'
    elif atr_percent < 1.0:
        level = 'high'
        description = '高波动'
        stop_loss_multiplier = 1.5  # 高波动时止损需要更宽
        take_profit_multiplier = 1.2  # 高波动时止盈可以更宽
        recommendation = '市场波动较大，建议放宽止损距离，止盈可以设置更宽以获取更大利润'
    else:
        level = 'very_high'
        description = '极高波动'
        stop_loss_multiplier = 2.0
        take_profit_multiplier = 1.5
        recommendation = '市场波动极大，建议大幅放宽止损距离，或考虑暂停交易'
    
    return {
        'level': level,
        'description': description,
        'atr_percent': atr_percent,
        'stop_loss_multiplier': stop_loss_multiplier,
        'take_profit_multiplier': take_profit_multiplier,
        'recommendation': recommendation
    }


def calculate_risk_reward_ratio(
    entry: float,
    stop_loss: float,
    take_profit_1: float,
    take_profit_2: float,
    signal_type: str
) -> Dict[str, float]:
    """
    计算盈亏比
    
    Args:
        entry: 入场价
        stop_loss: 止损价
        take_profit_1: 第一止盈价
        take_profit_2: 第二止盈价
        signal_type: 'long' 或 'short'
    
    Returns:
        包含各种盈亏比的字典
    """
    if signal_type == 'long':
        risk = entry - stop_loss
        reward_1 = take_profit_1 - entry
        reward_2 = take_profit_2 - entry
    else:  # short
        risk = stop_loss - entry
        reward_1 = entry - take_profit_1
        reward_2 = entry - take_profit_2
    
    if risk <= 0:
        return {
            'risk': 0,
            'reward_1': 0,
            'reward_2': 0,
            'rr_ratio_1': 0,
            'rr_ratio_2': 0,
            'avg_rr_ratio': 0,
            'quality': 'invalid'
        }
    
    rr_ratio_1 = reward_1 / risk if risk > 0 else 0
    rr_ratio_2 = reward_2 / risk if risk > 0 else 0
    avg_rr_ratio = (rr_ratio_1 + rr_ratio_2) / 2
    
    # 评估盈亏比质量
    if avg_rr_ratio >= 3.0:
        quality = 'excellent'
    elif avg_rr_ratio >= 2.0:
        quality = 'good'
    elif avg_rr_ratio >= 1.5:
        quality = 'acceptable'
    elif avg_rr_ratio >= 1.0:
        quality = 'poor'
    else:
        quality = 'very_poor'
    
    return {
        'risk': risk,
        'reward_1': reward_1,
        'reward_2': reward_2,
        'rr_ratio_1': rr_ratio_1,
        'rr_ratio_2': rr_ratio_2,
        'avg_rr_ratio': avg_rr_ratio,
        'quality': quality
    }


def analyze_signal_with_volatility(
    signal: Dict,
    klines: List[Dict],
    timeframe: str = '5分钟'
) -> Dict:
    """
    综合分析信号（包含波动率和盈亏比）
    
    Args:
        signal: 信号字典，包含 entry, stop_loss, take_profit_1, take_profit_2, type
        klines: K线数据
        timeframe: 时间框架
    
    Returns:
        包含波动率分析和盈亏比的综合评估
    """
    # 计算ATR
    atr = calculate_atr(klines, period=14)
    atr_percent = calculate_atr_percent(klines, period=14)
    
    # 评估波动率
    volatility_assessment = assess_volatility_level(atr_percent)
    
    # 计算盈亏比
    rr_analysis = calculate_risk_reward_ratio(
        entry=signal['entry'],
        stop_loss=signal['stop_loss'],
        take_profit_1=signal['take_profit_1'],
        take_profit_2=signal['take_profit_2'],
        signal_type=signal['type']
    )
    
    # 综合评估
    return {
        'signal': signal,
        'volatility': {
            'atr': atr,
            'atr_percent': atr_percent,
            'assessment': volatility_assessment
        },
        'risk_reward': rr_analysis,
        'recommendation': generate_signal_recommendation(volatility_assessment, rr_analysis)
    }


def generate_signal_recommendation(
    volatility_assessment: Dict,
    rr_analysis: Dict
) -> str:
    """生成信号建议"""
    recommendations = []
    
    # 波动率建议
    if volatility_assessment['level'] == 'high' or volatility_assessment['level'] == 'very_high':
        recommendations.append(f"⚠️ 市场波动{volatility_assessment['description']}，建议放宽止损距离")
    
    # 盈亏比建议
    if rr_analysis['quality'] == 'very_poor':
        recommendations.append("❌ 盈亏比过低（<1.0），不建议交易")
    elif rr_analysis['quality'] == 'poor':
        recommendations.append("⚠️ 盈亏比较低（1.0-1.5），风险较大")
    elif rr_analysis['quality'] == 'acceptable':
        recommendations.append("✅ 盈亏比可接受（1.5-2.0）")
    elif rr_analysis['quality'] == 'good':
        recommendations.append("✅ 盈亏比良好（2.0-3.0）")
    else:
        recommendations.append("✅✅ 盈亏比优秀（≥3.0）")
    
    return " | ".join(recommendations) if recommendations else "无特殊建议"


