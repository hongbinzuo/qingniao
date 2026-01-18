#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间周期风险计算器

根据时间框架（5分钟、15分钟等）计算合理的：
1. 止损距离
2. 止盈目标
3. 波动范围估算
4. 入场时机判断
5. 仓位大小
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TimeframeRiskParams:
    """时间周期风险参数"""
    # 止损参数
    min_stop_distance_pct: float  # 最小止损距离（百分比）
    max_stop_distance_pct: float  # 最大止损距离（百分比）
    typical_stop_distance_pct: float  # 典型止损距离（百分比）
    
    # 止盈参数
    min_reward_risk_ratio: float  # 最小盈亏比
    typical_reward_risk_ratio: float  # 典型盈亏比
    
    # 波动参数
    typical_daily_range_pct: float  # 典型日内波动范围（百分比）
    max_acceptable_delay_hours: float  # 最大可接受延迟（小时）
    
    # 仓位参数
    max_position_size_pct: float  # 最大仓位百分比
    typical_position_size_pct: float  # 典型仓位百分比


class TimeframeRiskCalculator:
    """时间周期风险计算器"""
    
    # 不同时间框架的风险参数（基于专业交易员经验）
    TIMEFRAME_PARAMS = {
        '5m': TimeframeRiskParams(
            min_stop_distance_pct=0.005,  # 0.5%（5分钟信号止损要紧）
            max_stop_distance_pct=0.015,  # 1.5%（最大不超过1.5%）
            typical_stop_distance_pct=0.008,  # 0.8%（典型0.8%）
            min_reward_risk_ratio=2.0,  # 至少2:1
            typical_reward_risk_ratio=2.5,  # 理想2.5:1
            typical_daily_range_pct=0.03,  # 3%（加密货币日内波动）
            max_acceptable_delay_hours=0.5,  # 5分钟信号最多等30分钟
            max_position_size_pct=0.15,  # 最大15%仓位（5分钟信号风险较高）
            typical_position_size_pct=0.10  # 典型10%仓位
        ),
        '15m': TimeframeRiskParams(
            min_stop_distance_pct=0.01,  # 1%（15分钟信号可以稍宽）
            max_stop_distance_pct=0.025,  # 2.5%
            typical_stop_distance_pct=0.015,  # 1.5%
            min_reward_risk_ratio=2.0,
            typical_reward_risk_ratio=3.0,  # 15分钟信号可以追求更高盈亏比
            typical_daily_range_pct=0.05,  # 5%
            max_acceptable_delay_hours=2.0,  # 15分钟信号可以等2小时
            max_position_size_pct=0.20,  # 最大20%仓位
            typical_position_size_pct=0.15  # 典型15%仓位
        ),
        '1h': TimeframeRiskParams(
            min_stop_distance_pct=0.015,  # 1.5%
            max_stop_distance_pct=0.04,  # 4%
            typical_stop_distance_pct=0.025,  # 2.5%
            min_reward_risk_ratio=2.0,
            typical_reward_risk_ratio=3.0,
            typical_daily_range_pct=0.08,  # 8%
            max_acceptable_delay_hours=6.0,  # 1小时信号可以等6小时
            max_position_size_pct=0.25,  # 最大25%仓位
            typical_position_size_pct=0.20  # 典型20%仓位
        )
    }
    
    def __init__(self):
        """初始化计算器"""
        pass
    
    def get_params(self, timeframe: str) -> TimeframeRiskParams:
        """
        获取时间框架的风险参数
        
        Args:
            timeframe: 时间框架（'5m', '15m', '1h'等）
        
        Returns:
            风险参数
        """
        # 标准化时间框架名称
        timeframe = timeframe.lower().replace('min', 'm').replace('分钟', 'm')
        if timeframe.endswith('m'):
            timeframe = timeframe
        
        return self.TIMEFRAME_PARAMS.get(timeframe, self.TIMEFRAME_PARAMS['15m'])
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        direction: str,
        timeframe: str,
        recent_lows: Optional[List[float]] = None,
        recent_highs: Optional[List[float]] = None,
        is_small_price: bool = False
    ) -> Tuple[float, float]:
        """
        计算止损价格和止损距离
        
        Args:
            entry_price: 入场价
            direction: 方向（'long'或'short'）
            timeframe: 时间框架
            recent_lows: 最近低点列表
            recent_highs: 最近高点列表
            is_small_price: 是否为小价格币种
        
        Returns:
            (stop_loss_price, stop_loss_distance_pct)
        """
        params = self.get_params(timeframe)
        
        if direction == 'long':
            # 做多：止损在入场价下方
            # 使用最近低点，但不超过最大止损距离
            if recent_lows:
                candidate_stop = min(recent_lows)
            else:
                candidate_stop = entry_price * (1 - params.typical_stop_distance_pct)
            
            # 确保止损在合理范围内
            min_stop = entry_price * (1 - params.max_stop_distance_pct)
            max_stop = entry_price * (1 - params.min_stop_distance_pct)
            
            # 对于小价格币种，使用更严格的止损
            if is_small_price:
                # 小价格币种的最小止损距离要更小（绝对值）
                if entry_price < 0.01:
                    min_absolute_diff = 0.0001
                elif entry_price < 0.1:
                    min_absolute_diff = 0.0005
                else:
                    min_absolute_diff = 0.001
                
                min_stop = max(min_stop, entry_price - min_absolute_diff)
            
            stop_loss = max(min_stop, min(candidate_stop, max_stop))
            
            # 确保止损明显低于入场价
            stop_loss = min(stop_loss, entry_price * 0.998)  # 至少0.2%距离
            
        else:  # short
            # 做空：止损在入场价上方
            if recent_highs:
                candidate_stop = max(recent_highs)
            else:
                candidate_stop = entry_price * (1 + params.typical_stop_distance_pct)
            
            # 确保止损在合理范围内
            min_stop = entry_price * (1 + params.min_stop_distance_pct)
            max_stop = entry_price * (1 + params.max_stop_distance_pct)
            
            # 对于小价格币种，使用更严格的止损
            if is_small_price:
                if entry_price < 0.01:
                    min_absolute_diff = 0.0001
                elif entry_price < 0.1:
                    min_absolute_diff = 0.0005
                else:
                    min_absolute_diff = 0.001
                
                max_stop = min(max_stop, entry_price + min_absolute_diff)
            
            stop_loss = min(max_stop, max(candidate_stop, min_stop))
            
            # 确保止损明显高于入场价
            stop_loss = max(stop_loss, entry_price * 1.002)  # 至少0.2%距离
        
        # 计算止损距离
        if direction == 'long':
            stop_loss_distance_pct = (entry_price - stop_loss) / entry_price
        else:
            stop_loss_distance_pct = (stop_loss - entry_price) / entry_price
        
        return stop_loss, stop_loss_distance_pct
    
    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss: float,
        direction: str,
        timeframe: str
    ) -> Tuple[float, float]:
        """
        计算止盈价格
        
        Args:
            entry_price: 入场价
            stop_loss: 止损价
            direction: 方向
            timeframe: 时间框架
        
        Returns:
            (take_profit_1, take_profit_2)
        """
        params = self.get_params(timeframe)
        
        # 计算风险
        if direction == 'long':
            risk = entry_price - stop_loss
        else:
            risk = stop_loss - entry_price
        
        if risk <= 0:
            # 如果风险计算失败，使用默认参数
            risk = entry_price * params.typical_stop_distance_pct
        
        # 计算止盈（至少2:1，理想达到典型盈亏比）
        take_profit_1_distance = risk * params.min_reward_risk_ratio
        take_profit_2_distance = risk * params.typical_reward_risk_ratio
        
        if direction == 'long':
            take_profit_1 = entry_price + take_profit_1_distance
            take_profit_2 = entry_price + take_profit_2_distance
        else:
            take_profit_1 = entry_price - take_profit_1_distance
            take_profit_2 = entry_price - take_profit_2_distance
        
        return take_profit_1, take_profit_2
    
    def calculate_position_size(
        self,
        account_equity: float,
        entry_price: float,
        stop_loss: float,
        risk_per_trade_pct: float = 1.0,  # 单笔交易风险（账户的1%）
        timeframe: str = '15m'
    ) -> Dict:
        """
        计算仓位大小（基于风险百分比）
        
        Args:
            account_equity: 账户权益
            entry_price: 入场价
            stop_loss: 止损价
            risk_per_trade_pct: 单笔交易风险百分比（默认1%）
            timeframe: 时间框架
        
        Returns:
            仓位信息字典
        """
        params = self.get_params(timeframe)
        
        # 计算风险金额
        risk_amount = account_equity * (risk_per_trade_pct / 100.0)
        
        # 计算每单位风险
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit <= 0:
            # 如果风险计算失败，使用默认仓位
            position_size_pct = params.typical_position_size_pct
            quantity = account_equity * position_size_pct / entry_price
        else:
            # 计算数量（基于风险）
            quantity = risk_amount / risk_per_unit
            
            # 计算仓位百分比
            position_value = quantity * entry_price
            position_size_pct = position_value / account_equity
            
            # 限制最大仓位
            max_position_value = account_equity * params.max_position_size_pct
            if position_value > max_position_value:
                quantity = max_position_value / entry_price
                position_size_pct = params.max_position_size_pct
        
        return {
            'quantity': quantity,
            'position_size_pct': position_size_pct,
            'position_value': quantity * entry_price,
            'risk_amount': risk_amount,
            'risk_per_unit': risk_per_unit
        }
    
    def estimate_entry_probability(
        self,
        current_price: float,
        target_entry_price: float,
        timeframe: str,
        recent_volatility: Optional[float] = None
    ) -> Dict:
        """
        估算入场概率（价格到达目标入场价的概率）
        
        Args:
            current_price: 当前价格
            target_entry_price: 目标入场价
            timeframe: 时间框架
            recent_volatility: 近期波动率（可选）
        
        Returns:
            入场概率信息
        """
        params = self.get_params(timeframe)
        
        # 计算价格差异
        price_diff = abs(current_price - target_entry_price)
        price_diff_pct = price_diff / current_price
        
        # 估算波动范围（基于时间框架）
        if recent_volatility:
            typical_range = recent_volatility
        else:
            typical_range = params.typical_daily_range_pct
        
        # 如果价格差异超过典型波动范围，概率较低
        if price_diff_pct > typical_range * 0.5:  # 超过一半波动范围
            probability = max(0.1, 1.0 - (price_diff_pct / typical_range))
        else:
            # 在合理范围内，概率较高
            probability = max(0.5, 1.0 - (price_diff_pct / (typical_range * 0.3)))
        
        # 判断是否在可接受延迟内
        # 简化：如果价格差异小于典型波动范围的30%，认为可以快速到达
        is_acceptable = price_diff_pct < typical_range * 0.3
        
        return {
            'probability': probability,
            'is_acceptable': is_acceptable,
            'price_diff_pct': price_diff_pct,
            'estimated_hours': price_diff_pct / (typical_range / 24.0)  # 估算小时数
        }


def main():
    """测试函数"""
    calculator = TimeframeRiskCalculator()
    
    # 测试5分钟信号
    print("=== 5分钟信号参数 ===")
    params_5m = calculator.get_params('5m')
    print(f"最小止损: {params_5m.min_stop_distance_pct*100:.2f}%")
    print(f"典型止损: {params_5m.typical_stop_distance_pct*100:.2f}%")
    print(f"最大止损: {params_5m.max_stop_distance_pct*100:.2f}%")
    print(f"最大延迟: {params_5m.max_acceptable_delay_hours*60:.0f}分钟")
    print()
    
    # 测试止损计算
    entry = 100.0
    stop_loss, distance = calculator.calculate_stop_loss(
        entry_price=entry,
        direction='long',
        timeframe='5m',
        recent_lows=[99.0, 98.5, 99.2]
    )
    print(f"入场价: ${entry:.2f}")
    print(f"止损价: ${stop_loss:.2f}")
    print(f"止损距离: {distance*100:.2f}%")
    print()
    
    # 测试止盈计算
    tp1, tp2 = calculator.calculate_take_profit(entry, stop_loss, 'long', '5m')
    print(f"止盈1: ${tp1:.2f}")
    print(f"止盈2: ${tp2:.2f}")
    print()
    
    # 测试仓位计算
    position = calculator.calculate_position_size(
        account_equity=10000.0,
        entry_price=entry,
        stop_loss=stop_loss,
        risk_per_trade_pct=1.0,
        timeframe='5m'
    )
    print(f"仓位数量: {position['quantity']:.4f}")
    print(f"仓位百分比: {position['position_size_pct']*100:.2f}%")
    print(f"风险金额: ${position['risk_amount']:.2f}")


if __name__ == '__main__':
    main()
