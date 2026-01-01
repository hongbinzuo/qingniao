#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滚仓策略整合模块
将De.的滚仓策略整合到信号生成和交易计划中
"""

import sys
from typing import Dict, List, Optional
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

class ScalingStrategyIntegrator:
    """滚仓策略整合器"""
    
    def __init__(self):
        # 滚仓策略参数（基于De.的实际操作）
        self.scaling_params = {
            'initial_entry': {
                'description': '初始入场',
                'position_size': 1.0,  # 100%
            },
            'downward_scaling': {
                'description': '向下加仓（降低成本）',
                'trigger': 'price_drop_pct',  # 价格下跌触发
                'trigger_value': 0.05,  # 下跌5%左右
                'position_size': 1.0,  # 加仓100%（总仓位200%）
                'max_scaling_times': 2,  # 最多加仓2次
            },
            'profit_taking': {
                'description': '分批止盈（锁定利润）',
                'trigger': 'price_rise_pct',  # 价格上涨触发
                'trigger_value': 0.04,  # 上涨4%左右
                'reduce_size': 0.5,  # 减仓50%
            },
            'pullback_scaling': {
                'description': '回调加仓（重新入场）',
                'trigger': 'pullback_pct',  # 回调幅度
                'trigger_value': 0.006,  # 回调0.6%左右
                'position_size': 0.25,  # 加回25%
            },
            'manual_mode': {
                'description': '手动档操作',
                'flexible_stop_loss': True,  # 灵活止损
                'breakout_first': True,  # 先突破再看
            }
        }
    
    def generate_scaling_plan(self, entry_price: float, direction: str = 'long') -> Dict:
        """
        生成滚仓交易计划
        
        Args:
            entry_price: 入场价格
            direction: 方向（long/short）
        
        Returns:
            滚仓交易计划
        """
        plan = {
            'strategy_type': 'scaling_strategy',
            'direction': direction,
            'entry_price': entry_price,
            'initial_position': 1.0,
            'scaling_levels': [],
            'profit_taking_levels': [],
            'risk_management': {},
            'notes': []
        }
        
        if direction == 'long':
            # 向下加仓位（降低成本）
            downward_level = entry_price * (1 - self.scaling_params['downward_scaling']['trigger_value'])
            plan['scaling_levels'].append({
                'price': downward_level,
                'action': 'add_position',
                'size': self.scaling_params['downward_scaling']['position_size'],
                'description': f'价格跌到 ${downward_level:,.0f} 时加仓（降低成本）',
                'priority': 'high'
            })
            
            # 止盈位（锁定利润）
            profit_level = entry_price * (1 + self.scaling_params['profit_taking']['trigger_value'])
            plan['profit_taking_levels'].append({
                'price': profit_level,
                'action': 'reduce_position',
                'size': self.scaling_params['profit_taking']['reduce_size'],
                'description': f'价格涨到 ${profit_level:,.0f} 时减仓一半（锁定利润）',
                'priority': 'high'
            })
            
            # 回调加仓位
            pullback_level = profit_level * (1 - self.scaling_params['pullback_scaling']['trigger_value'])
            plan['scaling_levels'].append({
                'price': pullback_level,
                'action': 'add_position',
                'size': self.scaling_params['pullback_scaling']['position_size'],
                'description': f'价格回调到 ${pullback_level:,.0f} 时加回1/4（重新入场）',
                'priority': 'medium'
            })
            
            # 止损位（灵活）
            stop_loss = entry_price * 0.98  # 初始止损2%
            plan['risk_management'] = {
                'initial_stop_loss': stop_loss,
                'breakeven_stop_loss': entry_price,  # 保本止损
                'flexible': True,
                'note': '先突破再看，手动调整'
            }
        
        plan['notes'].append('需要密切监控市场，手动操作')
        plan['notes'].append('根据市场情况灵活调整止损')
        plan['notes'].append('先突破再看，不固定止损')
        
        return plan
    
    def enhance_trading_signal(self, signal: Dict) -> Dict:
        """
        增强交易信号，添加滚仓策略建议
        
        Args:
            signal: 原始交易信号
        
        Returns:
            增强后的信号（包含滚仓计划）
        """
        enhanced_signal = signal.copy()
        
        entry_price = signal.get('entry_price') or signal.get('entry')
        if not entry_price:
            return signal
        
        direction = signal.get('direction', 'long')
        if signal.get('signal_type'):
            direction = 'long' if signal.get('signal_type') == 'long' else 'short'
        
        # 生成滚仓计划
        scaling_plan = self.generate_scaling_plan(entry_price, direction)
        
        enhanced_signal['scaling_strategy'] = {
            'enabled': True,
            'plan': scaling_plan,
            'applicable': self._is_applicable(signal),
            'recommendation': self._get_recommendation(signal)
        }
        
        return enhanced_signal
    
    def _is_applicable(self, signal: Dict) -> bool:
        """判断滚仓策略是否适用于该信号"""
        # 滚仓策略适用于：
        # 1. 趋势明确的信号
        # 2. 有足够波动空间的信号
        # 3. 中长期持仓的信号
        
        strength = signal.get('strength', 'medium')
        timeframe = signal.get('timeframe', '15m')
        
        # 强信号且时间框架较大时适用
        if strength in ['strong', 'very_strong']:
            if timeframe in ['1h', '4h', '1d']:
                return True
        
        # 有明确趋势时适用
        if signal.get('trend') == 'up' or signal.get('trend') == 'down':
            return True
        
        return False
    
    def _get_recommendation(self, signal: Dict) -> str:
        """获取滚仓策略建议"""
        if self._is_applicable(signal):
            return "建议使用滚仓策略：可以向下加仓降低成本，上涨时分批止盈"
        else:
            return "当前信号可能不适合滚仓策略，建议使用标准止盈止损"
    
    def generate_trading_plan_reminder(self, signal: Dict) -> List[str]:
        """
        生成交易计划提醒
        
        Returns:
            提醒列表
        """
        reminders = []
        
        if not self._is_applicable(signal):
            return reminders
        
        entry_price = signal.get('entry_price') or signal.get('entry')
        if not entry_price:
            return reminders
        
        scaling_plan = self.generate_scaling_plan(entry_price, signal.get('direction', 'long'))
        
        reminders.append("【滚仓策略提醒】")
        reminders.append("")
        
        # 加仓提醒
        if scaling_plan.get('scaling_levels'):
            reminders.append("加仓计划：")
            for level in scaling_plan['scaling_levels']:
                reminders.append(f"  - {level['description']}")
            reminders.append("")
        
        # 止盈提醒
        if scaling_plan.get('profit_taking_levels'):
            reminders.append("止盈计划：")
            for level in scaling_plan['profit_taking_levels']:
                reminders.append(f"  - {level['description']}")
            reminders.append("")
        
        # 风险提醒
        if scaling_plan.get('risk_management'):
            rm = scaling_plan['risk_management']
            reminders.append("风险管理：")
            reminders.append(f"  - 初始止损: ${rm.get('initial_stop_loss', 0):,.0f}")
            reminders.append(f"  - 保本止损: ${rm.get('breakeven_stop_loss', 0):,.0f}")
            reminders.append(f"  - {rm.get('note', '')}")
            reminders.append("")
        
        reminders.append("⚠️ 注意：滚仓策略需要密切监控，手动操作")
        
        return reminders


