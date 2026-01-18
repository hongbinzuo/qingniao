#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brooks规则参数提取器

从Brooks规则的文本中提取交易参数：
- 止损规则
- 止盈规则
- 仓位配置
- 盈亏比
"""

import re
import json
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field


@dataclass
class TradingParameters:
    """交易参数"""
    stop_loss_pct: Optional[float] = None  # 止损百分比
    take_profit_pct: Optional[float] = None  # 止盈百分比
    risk_reward_ratio: Optional[float] = None  # 盈亏比
    position_size_pct: Optional[float] = None  # 仓位百分比
    max_loss_pct: Optional[float] = None  # 最大亏损百分比
    notes: List[str] = field(default_factory=list)  # 备注


class BrooksParameterExtractor:
    """Brooks规则参数提取器"""
    
    def __init__(self):
        # 止损模式
        self.stop_loss_patterns = [
            r'止损[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'stop\s*loss[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'止损.*?(\d+(?:\.\d+)?)\s*%',
            r'亏损.*?(\d+(?:\.\d+)?)\s*%',
            r'loss.*?(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%?\s*止损',
        ]
        
        # 止盈模式
        self.take_profit_patterns = [
            r'止盈[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'take\s*profit[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'止盈.*?(\d+(?:\.\d+)?)\s*%',
            r'目标[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'target[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'盈利.*?(\d+(?:\.\d+)?)\s*%',
            r'profit.*?(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%?\s*止盈',
        ]
        
        # 盈亏比模式
        self.rr_patterns = [
            r'盈亏比[：:]\s*(\d+(?:\.\d+)?)\s*[:：]\s*(\d+(?:\.\d+)?)',
            r'risk[-\s]*reward[：:]\s*(\d+(?:\.\d+)?)\s*[:：]\s*(\d+(?:\.\d+)?)',
            r'RR[：:]\s*(\d+(?:\.\d+)?)\s*[:：]\s*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*[:：]\s*(\d+(?:\.\d+)?)\s*盈亏比',
        ]
        
        # 仓位模式
        self.position_patterns = [
            r'仓位[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'position[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'仓位.*?(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%?\s*仓位',
            r'资金.*?(\d+(?:\.\d+)?)\s*%',
        ]
        
        # 最大亏损模式
        self.max_loss_patterns = [
            r'最大亏损[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'max.*?loss[：:]\s*(\d+(?:\.\d+)?)\s*%?',
            r'最大.*?(\d+(?:\.\d+)?)\s*%',
        ]
    
    def extract_parameters(self, trading_rules: Dict, content_text: Optional[str] = None, 
                          key_concepts: Optional[List] = None) -> TradingParameters:
        """
        从Brooks规则中提取交易参数
        
        Args:
            trading_rules: 交易规则字典
            content_text: 内容文本
            key_concepts: 关键概念列表
        
        Returns:
            TradingParameters对象
        """
        # 合并所有文本
        all_text = ""
        if trading_rules:
            all_text += json.dumps(trading_rules, ensure_ascii=False)
        if content_text:
            all_text += " " + content_text
        if key_concepts:
            all_text += " " + " ".join(str(kc) for kc in key_concepts)
        
        all_text = all_text.lower()
        
        params = TradingParameters(notes=[])
        
        # 提取止损
        stop_loss = self._extract_stop_loss(all_text)
        if stop_loss:
            params.stop_loss_pct = stop_loss
            params.notes.append(f"止损: {stop_loss}%")
        
        # 提取止盈
        take_profit = self._extract_take_profit(all_text)
        if take_profit:
            params.take_profit_pct = take_profit
            params.notes.append(f"止盈: {take_profit}%")
        
        # 提取盈亏比
        rr_ratio = self._extract_rr_ratio(all_text)
        if rr_ratio:
            params.risk_reward_ratio = rr_ratio
            params.notes.append(f"盈亏比: {rr_ratio}:1")
        
        # 如果只有止损和止盈，计算盈亏比
        if not params.risk_reward_ratio and params.stop_loss_pct and params.take_profit_pct:
            params.risk_reward_ratio = params.take_profit_pct / params.stop_loss_pct
            params.notes.append(f"计算盈亏比: {params.risk_reward_ratio:.2f}:1")
        
        # 提取仓位
        position_size = self._extract_position_size(all_text)
        if position_size:
            params.position_size_pct = position_size
            params.notes.append(f"仓位: {position_size}%")
        
        # 提取最大亏损
        max_loss = self._extract_max_loss(all_text)
        if max_loss:
            params.max_loss_pct = max_loss
            params.notes.append(f"最大亏损: {max_loss}%")
        
        return params
    
    def _extract_stop_loss(self, text: str) -> Optional[float]:
        """提取止损百分比"""
        for pattern in self.stop_loss_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # 如果值大于1，可能是百分比，需要除以100
                if value > 1:
                    value = value / 100
                return min(value, 0.1)  # 限制最大止损为10%
        return None
    
    def _extract_take_profit(self, text: str) -> Optional[float]:
        """提取止盈百分比"""
        for pattern in self.take_profit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # 如果值大于1，可能是百分比，需要除以100
                if value > 1:
                    value = value / 100
                return min(value, 0.5)  # 限制最大止盈为50%
        return None
    
    def _extract_rr_ratio(self, text: str) -> Optional[float]:
        """提取盈亏比"""
        for pattern in self.rr_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                risk = float(match.group(1))
                reward = float(match.group(2))
                if risk > 0:
                    return reward / risk
        return None
    
    def _extract_position_size(self, text: str) -> Optional[float]:
        """提取仓位百分比"""
        for pattern in self.position_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # 如果值大于1，可能是百分比，需要除以100
                if value > 1:
                    value = value / 100
                return min(value, 0.3)  # 限制最大仓位为30%
        return None
    
    def _extract_max_loss(self, text: str) -> Optional[float]:
        """提取最大亏损百分比"""
        for pattern in self.max_loss_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                # 如果值大于1，可能是百分比，需要除以100
                if value > 1:
                    value = value / 100
                return min(value, 0.2)  # 限制最大亏损为20%
        return None


# 默认参数（基于Brooks交易系统常见值）
DEFAULT_PARAMETERS = TradingParameters(
    stop_loss_pct=0.02,  # 2%止损
    take_profit_pct=0.04,  # 4%止盈
    risk_reward_ratio=2.0,  # 2:1盈亏比
    position_size_pct=0.1,  # 10%仓位
    max_loss_pct=0.05,  # 5%最大亏损
    notes=["使用Brooks默认参数"]
)
