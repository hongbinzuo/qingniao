#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De.策略提取模块
从对话中提取策略信息、交易信号、执行操作等
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class DeStrategyExtractor:
    """De.策略提取器"""
    
    def __init__(self):
        # 策略关键词映射
        self.strategy_keywords = {
            'vegas': ['vegas', 'Vegas', 'EMA144', 'EMA169'],
            'fvg': ['FVG', 'fvg', 'fair value gap', '价格缺口'],
            '区间': ['区间', '震荡', '箱体', '区间突破'],
            '保本': ['保本', '盈亏平衡', 'breakeven'],
            '止盈': ['止盈', 'take profit', '落袋', '平仓'],
            '止损': ['止损', 'stop loss', 'stop'],
            '挂单': ['挂', '挂单', 'limit order'],
            '加仓': ['加仓', '加', 'add position'],
            '减仓': ['减仓', '减', 'reduce position'],
            'SMC': ['SMC', 'smc', 'smart money concept'],
            '币本位': ['币本位', '币安现货'],
            'U本位': ['U本位', 'USDT'],
            'OTE': ['OTE', '618', '786', '斐波那契'],
            'M顶W底': ['M顶', 'W底', '双顶', '双底', '顶', '底'],
        }
        
        # 交易动作关键词
        self.action_keywords = {
            '挂单': ['挂', '挂单'],
            '平仓': ['平', '平仓', '出了', '跑了', '落袋'],
            '加仓': ['加', '加仓', '再加'],
            '减仓': ['减', '减仓', '减一点'],
            '止损': ['止损', 'stop'],
            '止盈': ['止盈', 'tp', '第一止盈', '第二止盈', '止盈到了', '止盈到'],
            '保本': ['保本', '挂保本'],
        }
        
        # 市场观点关键词
        self.sentiment_keywords = {
            '看涨': ['涨', '多', '做多', 'long', '看多', '看涨'],
            '看跌': ['跌', '空', '做空', 'short', '看空', '看跌'],
            '观望': ['观望', '等待', '等', '看看', '观察'],
        }
    
    def extract_strategy_info(self, text: str) -> Dict:
        """
        从文本中提取策略信息
        
        Returns:
            包含策略信息的字典
        """
        result = {
            'prices': [],
            'actions': [],
            'strategy': [],
            'market_state': [],
            'concepts': [],
            'theories': [],
            'philosophy': [],
            'trading_signal': {},
            'trading_execution': {},
            'trading_philosophy': {},
            'category': None,
            'tags': [],
            'direction': None,
            'entry_price': None,
            'stop_loss': None,
            'take_profit_1': None,
            'take_profit_2': None,
            '_original_text': text,  # 保存原始文本用于分类
        }
        
        # 提取价格
        result['prices'] = self._extract_prices(text)
        
        # 提取交易方向
        result['direction'] = self._extract_direction(text)
        
        # 提取交易动作
        result['actions'] = self._extract_actions(text)
        
        # 提取策略概念
        result['concepts'] = self._extract_concepts(text)
        
        # 提取策略类型
        result['strategy'] = self._extract_strategy_types(text)
        
        # 提取市场观点
        result['market_state'] = self._extract_market_sentiment(text)
        
        # 提取交易理论
        result['theories'] = self._extract_theories(text)
        
        # 提取交易信号
        result['trading_signal'] = self._extract_trading_signal(text, result['prices'])
        
        # 提取交易执行
        result['trading_execution'] = self._extract_trading_execution(text, result['prices'])
        
        # 分类对话类型（需要在提取执行后）
        result['category'] = self._classify_category(result)
        
        # 生成标签
        result['tags'] = self._generate_tags(result)
        
        # 清理临时字段
        if '_original_text' in result:
            del result['_original_text']
        
        return result
    
    def _extract_prices(self, text: str) -> List[float]:
        """提取价格"""
        prices = []
        
        # 提取5-6位数字（完整价格，如87000）
        prices_5_6 = re.findall(r'(\d{5,6})', text)
        for p in prices_5_6:
            price_val = int(p)
            if 40000 <= price_val <= 150000:  # BTC合理价格范围
                prices.append(float(price_val))
        
        # 提取3-4位数字（简化价格，如870、876）
        prices_3_4 = re.findall(r'(\d{3,4})', text)
        for p in prices_3_4:
            price_val = int(p)
            if 400 <= price_val <= 1000:  # 简化价格范围（需要乘以100）
                # 尝试推断完整价格（假设在8-9万区间）
                if 800 <= price_val <= 900:
                    full_price = price_val * 100
                    if full_price not in prices:
                        prices.append(float(full_price))
        
        return sorted(list(set(prices)))
    
    def _extract_direction(self, text: str) -> Optional[str]:
        """提取交易方向"""
        if any(kw in text for kw in ['做多', '多单', 'long', 'Long', '多']):
            return 'long'
        elif any(kw in text for kw in ['做空', '空单', 'short', 'Short', '空']):
            return 'short'
        return None
    
    def _extract_actions(self, text: str) -> List[str]:
        """提取交易动作"""
        actions = []
        for action, keywords in self.action_keywords.items():
            if any(kw in text for kw in keywords):
                actions.append(action)
        
        # 特殊处理：止盈到了、落袋
        if '止盈到了' in text or '止盈到' in text:
            if '止盈' not in actions:
                actions.append('止盈')
        if '落袋' in text:
            if '平仓' not in actions:
                actions.append('平仓')
        
        return actions
    
    def _extract_concepts(self, text: str) -> List[str]:
        """提取策略概念"""
        concepts = []
        for concept, keywords in self.strategy_keywords.items():
            if any(kw in text for kw in keywords):
                concepts.append(concept)
        return concepts
    
    def _extract_strategy_types(self, text: str) -> List[str]:
        """提取策略类型"""
        strategies = []
        
        # Vegas策略
        if any(kw in text for kw in ['vegas', 'Vegas', 'EMA144', 'EMA169']):
            if '反弹' in text or '回踩' in text:
                strategies.append('Vegas反弹策略')
            elif '突破' in text:
                strategies.append('Vegas突破策略')
            else:
                strategies.append('Vegas通道策略')
        
        # FVG策略
        if 'FVG' in text or 'fvg' in text or '价格缺口' in text:
            strategies.append('FVG策略')
        
        # 区间策略
        if '区间' in text:
            if '突破' in text:
                strategies.append('区间突破策略')
            else:
                strategies.append('区间震荡策略')
        
        # 保本策略
        if '保本' in text:
            strategies.append('保本止损策略')
        
        # 分批止盈
        if '第一止盈' in text or '第二止盈' in text or ('止盈' in text and ('50%' in text or '一半' in text)):
            strategies.append('分批止盈策略')
        
        # M顶W底
        if any(kw in text for kw in ['M顶', 'W底', '双顶', '双底']):
            strategies.append('形态识别策略')
        
        return strategies
    
    def _extract_market_sentiment(self, text: str) -> List[str]:
        """提取市场观点"""
        sentiments = []
        for sentiment, keywords in self.sentiment_keywords.items():
            if any(kw in text for kw in keywords):
                sentiments.append(sentiment)
        return sentiments
    
    def _extract_theories(self, text: str) -> List[str]:
        """提取交易理论"""
        theories = []
        
        if 'SMC' in text or 'smc' in text:
            theories.append('SMC理论')
        
        if '币本位' in text:
            theories.append('币本位理论')
        
        if 'U本位' in text:
            theories.append('U本位理论')
        
        if 'OTE' in text or '618' in text or '786' in text:
            theories.append('OTE理论')
        
        return theories
    
    def _extract_trading_signal(self, text: str, prices: List[float]) -> Dict:
        """提取交易信号"""
        signal = {}
        
        # 提取入场价
        if '挂' in text and prices:
            signal['entry'] = prices[0] if prices else None
            signal['entry_type'] = 'limit_order'
        
        # 提取止损
        if '止损' in text:
            # 尝试从价格中提取止损价
            if prices:
                signal['stop_loss'] = prices[-1] if len(prices) > 1 else None
        
        # 提取止盈
        if '止盈' in text:
            if '第一止盈' in text or '止盈1' in text:
                if prices:
                    signal['take_profit_1'] = prices[0] if prices else None
            if '第二止盈' in text or '止盈2' in text:
                if len(prices) > 1:
                    signal['take_profit_2'] = prices[1]
        
        return signal
    
    def _extract_trading_execution(self, text: str, prices: List[float]) -> Dict:
        """提取交易执行信息"""
        execution = {}
        
        # 保本止损
        if '保本' in text or '挂保本' in text:
            execution['action'] = 'breakeven_stop_loss'
            if prices:
                execution['price'] = prices[0]
        
        # 止盈执行
        if '止盈到了' in text or '落袋' in text or ('止盈' in text and ('到了' in text or '到' in text)):
            execution['action'] = 'take_profit'
            if '第一止盈' in text:
                execution['tp_level'] = 1
            elif '第二止盈' in text:
                execution['tp_level'] = 2
            elif '止盈1' in text:
                execution['tp_level'] = 1
            elif '止盈2' in text:
                execution['tp_level'] = 2
        
        # 加仓
        if '加仓' in text or ('加' in text and '仓' in text):
            execution['action'] = 'add_position'
        
        # 减仓
        if '减仓' in text or ('减' in text and '仓' in text):
            execution['action'] = 'reduce_position'
        
        # 平仓
        if '平仓' in text or '平' in text or '出了' in text or '跑了' in text:
            execution['action'] = 'close_position'
        
        return execution
    
    def _classify_category(self, strategy_info: Dict) -> str:
        """分类对话类型"""
        # 优先级：交易执行 > 交易信号 > 观点 > 对话
        
        # 检查原始文本（优先检查，因为动作提取可能不完整）
        original_text = strategy_info.get('_original_text', '')
        if original_text:
            execution_keywords = ['止盈到了', '止盈到', '落袋', '保本', '止损', '平仓', '加仓', '减仓']
            if any(kw in original_text for kw in execution_keywords):
                return 'trading_execution'
        
        # 检查交易执行
        execution = strategy_info.get('trading_execution', {})
        if execution and execution.get('action'):
            return 'trading_execution'
        
        # 检查动作关键词
        actions = strategy_info.get('actions', [])
        execution_keywords = ['止盈', '止损', '保本', '平仓', '加仓', '减仓', '落袋']
        if actions:
            actions_str = ' '.join(actions)
            if any(kw in actions_str for kw in execution_keywords):
                return 'trading_execution'
        
        # 检查交易信号
        signal = strategy_info.get('trading_signal', {})
        if signal and (signal.get('entry') or signal.get('stop_loss') or signal.get('take_profit_1')):
            return 'trading_signal'
        
        # 检查观点
        if strategy_info.get('concepts') or strategy_info.get('theories'):
            return 'viewpoint'
        
        if strategy_info.get('strategy'):
            return 'viewpoint'
        
        return 'conversation'
    
    def _generate_tags(self, strategy_info: Dict) -> List[str]:
        """生成标签"""
        tags = []
        
        # 方向标签
        if strategy_info.get('direction'):
            if strategy_info['direction'] == 'long':
                tags.append('做多')
            else:
                tags.append('做空')
        
        # 动作标签
        tags.extend(strategy_info.get('actions', []))
        
        # 策略标签
        tags.extend(strategy_info.get('strategy', []))
        
        # 概念标签
        tags.extend(strategy_info.get('concepts', []))
        
        # 去重
        return list(set(tags))

