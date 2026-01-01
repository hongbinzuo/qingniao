#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浮云滚仓策略模块
基于盈利逐步加仓的金字塔式滚仓策略
在盈利达到一定水平时，使用浮盈增加仓位，实现滚仓操作
"""

import sys
from typing import Dict, List, Optional, Tuple

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class RollingPositionManager:
    """滚仓策略管理器"""
    
    def __init__(self, 
                 initial_risk_pct: float = 1.0,
                 pyramid_levels: List[float] = [0.5, 1.0, 1.5, 2.0],
                 pyramid_size_pct: float = 0.3,
                 max_position_size: float = 3.0):
        """
        初始化滚仓管理器
        
        Args:
            initial_risk_pct: 初始风险百分比（默认1%）
            pyramid_levels: 金字塔加仓的盈利水平（相对于初始止损的倍数）
            pyramid_size_pct: 每次加仓的仓位百分比（默认30%，即新增30%的初始仓位）
            max_position_size: 最大仓位倍数（相对于初始仓位，默认3倍）
        """
        self.initial_risk_pct = initial_risk_pct
        self.pyramid_levels = pyramid_levels  # [0.5R, 1.0R, 1.5R, 2.0R]
        self.pyramid_size_pct = pyramid_size_pct
        self.max_position_size = max_position_size
    
    def generate_rolling_suggestion(self, signal: Dict, current_price: float) -> Optional[Dict]:
        """
        为交易信号生成滚仓建议
        
        Args:
            signal: 交易信号字典，包含 entry, stop_loss, take_profit_1, take_profit_2 等
            current_price: 当前价格
        
        Returns:
            滚仓建议字典，如果信号不适合滚仓则返回None
        """
        if not signal or not signal.get('entry') or not signal.get('stop_loss'):
            return None
        
        entry = signal['entry']
        stop_loss = signal['stop_loss']
        signal_type = signal.get('type', 'long')
        
        # 计算初始风险（R）
        if signal_type == 'long':
            if current_price <= entry:
                return None  # 尚未入场，无法滚仓
            initial_risk = abs(entry - stop_loss)
            if initial_risk <= 0:
                return None
            # 计算当前浮盈（以R为单位）
            current_profit_r = (current_price - entry) / initial_risk
        else:  # short
            if current_price >= entry:
                return None  # 尚未入场，无法滚仓
            initial_risk = abs(entry - stop_loss)
            if initial_risk <= 0:
                return None
            # 计算当前浮盈（以R为单位）
            current_profit_r = (entry - current_price) / initial_risk
        
        # 判断是否适合滚仓（需要有一定的浮盈）
        min_profit_r = 0.5  # 至少0.5R的浮盈才考虑滚仓
        if current_profit_r < min_profit_r:
            return None
        
        # 判断当前处于哪个金字塔层级
        current_level = None
        next_level = None
        for i, level in enumerate(self.pyramid_levels):
            if current_profit_r >= level:
                current_level = level
                if i + 1 < len(self.pyramid_levels):
                    next_level = self.pyramid_levels[i + 1]
        
        # 如果没有达到任何层级，返回None
        if current_level is None:
            return None
        
        # 计算滚仓建议
        # 使用浮盈来增加仓位（不增加额外风险）
        suggestion = {
            'signal_id': signal.get('entry_model', 'unknown'),
            'signal_type': signal_type,
            'entry_price': entry,
            'current_price': current_price,
            'stop_loss': stop_loss,
            'initial_risk': initial_risk,
            'current_profit_r': current_profit_r,
            'current_level': current_level,
            'next_level': next_level,
            'rolling_suggestions': []
        }
        
        # 生成具体的滚仓操作建议
        rolling_ops = []
        
        # 如果已经达到某个层级，建议在下一层级加仓
        if next_level:
            target_price = entry + (next_level * initial_risk) if signal_type == 'long' else entry - (next_level * initial_risk)
            rolling_ops.append({
                'action': 'add_position',
                'target_price': target_price,
                'target_profit_r': next_level,
                'position_size_pct': self.pyramid_size_pct,
                'description': f"当价格达到{next_level:.1f}R盈利时，使用浮盈加仓{self.pyramid_size_pct*100:.0f}%",
                'risk': '使用浮盈，不增加额外风险'
            })
        
        # 移动止损到盈亏平衡点
        rolling_ops.append({
            'action': 'move_stop_loss',
            'target_price': entry,  # 移动到入场价（盈亏平衡）
            'description': f"将止损移至入场价${entry:,.0f}（盈亏平衡点）",
            'risk': '锁定利润，无额外风险'
        })
        
        # 分批止盈建议
        take_profit_1 = signal.get('take_profit_1')
        take_profit_2 = signal.get('take_profit_2')
        
        if take_profit_1:
            if signal_type == 'long' and current_price >= take_profit_1 * 0.98:
                rolling_ops.append({
                    'action': 'partial_take_profit',
                    'target_price': take_profit_1,
                    'profit_percentage': 30,
                    'description': f"在第一止盈位${take_profit_1:,.0f}止盈30%仓位",
                    'risk': '锁定部分利润'
                })
        
        if take_profit_2:
            if signal_type == 'long' and current_price >= take_profit_2 * 0.98:
                rolling_ops.append({
                    'action': 'partial_take_profit',
                    'target_price': take_profit_2,
                    'profit_percentage': 30,
                    'description': f"在第二止盈位${take_profit_2:,.0f}止盈30%仓位",
                    'risk': '锁定部分利润，保留40%仓位继续持有'
                })
        
        suggestion['rolling_suggestions'] = rolling_ops
        suggestion['suitable_for_rolling'] = True
        
        return suggestion
    
    def analyze_signal_for_rolling(self, signal: Dict, current_price: float) -> Dict:
        """
        分析信号是否适合滚仓策略
        
        Args:
            signal: 交易信号
            current_price: 当前价格
        
        Returns:
            分析结果字典
        """
        analysis = {
            'suitable': False,
            'reason': '',
            'suggestion': None,
            'current_profit_r': 0.0,
            'risk_reward_ratio': 0.0
        }
        
        if not signal or not signal.get('entry') or not signal.get('stop_loss'):
            analysis['reason'] = '信号信息不完整'
            return analysis
        
        entry = signal['entry']
        stop_loss = signal['stop_loss']
        signal_type = signal.get('type', 'long')
        
        # 计算风险回报比
        initial_risk = abs(entry - stop_loss)
        if initial_risk <= 0:
            analysis['reason'] = '无法计算风险'
            return analysis
        
        take_profit_1 = signal.get('take_profit_1')
        if take_profit_1:
            if signal_type == 'long':
                reward = abs(take_profit_1 - entry)
            else:
                reward = abs(entry - take_profit_1)
            analysis['risk_reward_ratio'] = reward / initial_risk if initial_risk > 0 else 0
        
        # 计算当前浮盈
        if signal_type == 'long':
            if current_price > entry:
                analysis['current_profit_r'] = (current_price - entry) / initial_risk
            else:
                analysis['current_profit_r'] = (current_price - entry) / initial_risk  # 可能为负
        else:
            if current_price < entry:
                analysis['current_profit_r'] = (entry - current_price) / initial_risk
            else:
                analysis['current_profit_r'] = (entry - current_price) / initial_risk  # 可能为负
        
        # 判断是否适合滚仓
        # 条件1：风险回报比至少2:1
        if analysis['risk_reward_ratio'] < 2.0:
            analysis['reason'] = f'风险回报比{analysis["risk_reward_ratio"]:.1f}:1不足，建议至少2:1'
            return analysis
        
        # 条件2：信号强度至少中等
        strength = signal.get('strength', 'weak')
        if strength == 'weak':
            analysis['reason'] = '信号强度不足'
            return analysis
        
        # 条件3：有明确的止盈位
        if not take_profit_1:
            analysis['reason'] = '缺少明确的止盈位'
            return analysis
        
        # 如果已经入场且有浮盈，生成滚仓建议
        if (signal_type == 'long' and current_price > entry) or (signal_type == 'short' and current_price < entry):
            suggestion = self.generate_rolling_suggestion(signal, current_price)
            if suggestion:
                analysis['suitable'] = True
                analysis['reason'] = '适合滚仓策略'
                analysis['suggestion'] = suggestion
                return analysis
        
        analysis['suitable'] = True
        analysis['reason'] = '信号适合滚仓策略（待入场后评估）'
        
        return analysis
    
    def format_rolling_suggestion(self, suggestion: Dict) -> List[str]:
        """
        格式化滚仓建议为可读的文本列表
        
        Args:
            suggestion: 滚仓建议字典
        
        Returns:
            格式化后的文本列表
        """
        lines = []
        
        if not suggestion:
            return lines
        
        lines.append(f"**信号**: {suggestion.get('signal_id', '未知')}")
        lines.append(f"**当前价格**: ${suggestion.get('current_price', 0):,.2f}")
        lines.append(f"**入场价**: ${suggestion.get('entry_price', 0):,.2f}")
        lines.append(f"**当前浮盈**: {suggestion.get('current_profit_r', 0):.2f}R")
        lines.append(f"**当前层级**: {suggestion.get('current_level', 0):.1f}R")
        lines.append("")
        
        rolling_ops = suggestion.get('rolling_suggestions', [])
        if rolling_ops:
            lines.append("**滚仓操作建议**:")
            lines.append("")
            for i, op in enumerate(rolling_ops, 1):
                action = op.get('action', '')
                description = op.get('description', '')
                target_price = op.get('target_price')
                
                if action == 'add_position':
                    lines.append(f"{i}. **加仓操作** - {description}")
                    if target_price:
                        lines.append(f"   - 目标价格: ${target_price:,.2f}")
                    lines.append(f"   - 加仓比例: {op.get('position_size_pct', 0)*100:.0f}%")
                    lines.append(f"   - 风险: {op.get('risk', '未知')}")
                elif action == 'move_stop_loss':
                    lines.append(f"{i}. **移动止损** - {description}")
                    if target_price:
                        lines.append(f"   - 新止损价: ${target_price:,.2f}")
                    lines.append(f"   - 风险: {op.get('risk', '未知')}")
                elif action == 'partial_take_profit':
                    lines.append(f"{i}. **分批止盈** - {description}")
                    if target_price:
                        lines.append(f"   - 止盈价格: ${target_price:,.2f}")
                    lines.append(f"   - 止盈比例: {op.get('profit_percentage', 0)}%")
                    lines.append(f"   - 风险: {op.get('risk', '未知')}")
                lines.append("")
        else:
            lines.append("暂无具体滚仓操作建议")
            lines.append("")
        
        return lines




