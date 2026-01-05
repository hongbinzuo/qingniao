#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De.策略问答系统
基于数据库中的对话和交易记录回答策略相关问题
"""

import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager
from de_strategy_extractor import DeStrategyExtractor

class DeStrategyQA:
    """De.策略问答系统"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.extractor = DeStrategyExtractor()
        
        # 问题模式匹配
        self.question_patterns = {
            'strategy_recent': [
                r'最近.*策略',
                r'用了什么策略',
                r'策略.*什么',
                r'什么策略',
            ],
            'strategy_type': [
                r'.*策略.*(Vegas|FVG|区间|保本|止盈|止损)',
                r'(Vegas|FVG|区间|保本|止盈|止损).*策略',
            ],
            'price_range': [
                r'价格.*区间',
                r'什么价格.*(做多|做空)',
                r'(做多|做空).*价格',
                r'价格.*多少',
            ],
            'stop_loss': [
                r'止损.*策略',
                r'止损.*怎么',
                r'止损.*设置',
            ],
            'take_profit': [
                r'止盈.*策略',
                r'止盈.*怎么',
                r'止盈.*设置',
            ],
            'market_condition': [
                r'什么.*市场.*策略',
                r'市场.*环境.*策略',
                r'(震荡|趋势).*策略',
            ],
            'direction': [
                r'(做多|做空).*策略',
                r'策略.*(做多|做空)',
            ],
        }
    
    def answer_question(self, question: str, days: int = 30) -> str:
        """
        回答问题
        
        Args:
            question: 问题文本
            days: 查询最近N天的数据
        
        Returns:
            答案文本
        """
        # 识别问题类型
        question_type = self._classify_question(question)
        
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        start_timestamp = start_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # 根据问题类型查询和回答
        if question_type == 'strategy_recent':
            return self._answer_recent_strategies(start_timestamp)
        elif question_type == 'strategy_type':
            return self._answer_strategy_type(question, start_timestamp)
        elif question_type == 'price_range':
            return self._answer_price_range(question, start_timestamp)
        elif question_type == 'stop_loss':
            return self._answer_stop_loss(start_timestamp)
        elif question_type == 'take_profit':
            return self._answer_take_profit(start_timestamp)
        elif question_type == 'market_condition':
            return self._answer_market_condition(question, start_timestamp)
        elif question_type == 'direction':
            return self._answer_direction(question, start_timestamp)
        else:
            return self._answer_general(question, start_timestamp)
    
    def _classify_question(self, question: str) -> str:
        """分类问题类型"""
        question_lower = question.lower()
        
        for qtype, patterns in self.question_patterns.items():
            for pattern in patterns:
                if re.search(pattern, question_lower):
                    return qtype
        
        return 'general'
    
    def _answer_recent_strategies(self, start_timestamp: str) -> str:
        """回答最近使用的策略"""
        conn = self.db._get_connection()
        
        # 获取最近的对话和观点
        conversations = conn.execute('''
            SELECT trader_message, timestamp FROM conversations
            WHERE timestamp >= ? AND trader_message IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 50
        ''', [start_timestamp]).fetchall()
        
        viewpoints = conn.execute('''
            SELECT content, timestamp FROM trader_viewpoints
            WHERE timestamp >= ? AND category IN ('trading_signal', 'trading_execution')
            ORDER BY timestamp DESC
            LIMIT 50
        ''', [start_timestamp]).fetchall()
        
        conn.close()
        
        # 提取策略
        strategies = []
        for conv in conversations:
            msg = conv[0]
            if msg:
                strategy_info = self.extractor.extract_strategy_info(msg)
                if strategy_info.get('strategy'):
                    strategies.extend(strategy_info['strategy'])
        
        for vp in viewpoints:
            content = vp[0]
            if content:
                strategy_info = self.extractor.extract_strategy_info(content)
                if strategy_info.get('strategy'):
                    strategies.extend(strategy_info['strategy'])
        
        # 统计频率
        from collections import Counter
        strategy_counts = Counter(strategies)
        
        if not strategy_counts:
            return "最近没有找到明确的策略信息。"
        
        answer = ["De.最近使用的策略：\n"]
        for strategy, count in strategy_counts.most_common(10):
            answer.append(f"- {strategy}: {count}次")
        
        return '\n'.join(answer)
    
    def _answer_strategy_type(self, question: str, start_timestamp: str) -> str:
        """回答特定策略类型的问题"""
        # 提取策略关键词
        strategy_keywords = ['Vegas', 'FVG', '区间', '保本', '止盈', '止损']
        found_keyword = None
        for kw in strategy_keywords:
            if kw in question:
                found_keyword = kw
                break
        
        if not found_keyword:
            return self._answer_recent_strategies(start_timestamp)
        
        conn = self.db._get_connection()
        conversations = conn.execute('''
            SELECT trader_message, timestamp FROM conversations
            WHERE timestamp >= ? AND trader_message LIKE ?
            ORDER BY timestamp DESC
            LIMIT 20
        ''', [start_timestamp, f'%{found_keyword}%']).fetchall()
        conn.close()
        
        if not conversations:
            return f"最近没有找到关于{found_keyword}策略的信息。"
        
        answer = [f"关于{found_keyword}策略的信息：\n"]
        for conv in conversations[:5]:  # 最近5条
            msg = conv[0]
            timestamp = conv[1]
            answer.append(f"- [{timestamp}] {msg[:100]}...")
        
        return '\n'.join(answer)
    
    def _answer_price_range(self, question: str, start_timestamp: str) -> str:
        """回答价格区间问题"""
        # 提取方向
        direction = None
        if '做多' in question or '多' in question:
            direction = 'long'
        elif '做空' in question or '空' in question:
            direction = 'short'
        
        conn = self.db._get_connection()
        
        # 获取相关对话
        if direction:
            conversations = conn.execute('''
                SELECT trader_message, timestamp FROM conversations
                WHERE timestamp >= ? AND trader_message LIKE ?
                ORDER BY timestamp DESC
                LIMIT 50
            ''', [start_timestamp, f'%{direction}%']).fetchall()
        else:
            conversations = conn.execute('''
                SELECT trader_message, timestamp FROM conversations
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 50
            ''', [start_timestamp]).fetchall()
        
        conn.close()
        
        # 提取价格
        prices = []
        for conv in conversations:
            msg = conv[0]
            if msg:
                strategy_info = self.extractor.extract_strategy_info(msg)
                prices.extend(strategy_info.get('prices', []))
        
        if not prices:
            return "最近没有找到价格信息。"
        
        prices = sorted(prices)
        answer = []
        if direction:
            answer.append(f"De.最近做{direction}的价格区间：\n")
        else:
            answer.append("De.最近提到的价格区间：\n")
        answer.append(f"- 最低价格: ${min(prices):,.0f}")
        answer.append(f"- 最高价格: ${max(prices):,.0f}")
        answer.append(f"- 平均价格: ${sum(prices)/len(prices):,.0f}")
        answer.append(f"- 价格范围: ${min(prices):,.0f} - ${max(prices):,.0f}")
        
        return '\n'.join(answer)
    
    def _answer_stop_loss(self, start_timestamp: str) -> str:
        """回答止损策略问题"""
        conn = self.db._get_connection()
        conversations = conn.execute('''
            SELECT trader_message, timestamp FROM conversations
            WHERE timestamp >= ? AND (trader_message LIKE '%止损%' OR trader_message LIKE '%保本%')
            ORDER BY timestamp DESC
            LIMIT 20
        ''', [start_timestamp]).fetchall()
        conn.close()
        
        if not conversations:
            return "最近没有找到关于止损策略的信息。"
        
        answer = ["De.的止损策略：\n"]
        for conv in conversations[:5]:
            msg = conv[0]
            timestamp = conv[1]
            strategy_info = self.extractor.extract_strategy_info(msg)
            
            if '保本' in msg:
                answer.append(f"- [{timestamp}] 保本止损策略")
            elif strategy_info.get('prices'):
                answer.append(f"- [{timestamp}] 止损价格: ${strategy_info['prices'][0]:,.0f}")
            else:
                answer.append(f"- [{timestamp}] {msg[:80]}...")
        
        return '\n'.join(answer)
    
    def _answer_take_profit(self, start_timestamp: str) -> str:
        """回答止盈策略问题"""
        conn = self.db._get_connection()
        conversations = conn.execute('''
            SELECT trader_message, timestamp FROM conversations
            WHERE timestamp >= ? AND trader_message LIKE '%止盈%'
            ORDER BY timestamp DESC
            LIMIT 20
        ''', [start_timestamp]).fetchall()
        conn.close()
        
        if not conversations:
            return "最近没有找到关于止盈策略的信息。"
        
        answer = ["De.的止盈策略：\n"]
        for conv in conversations[:5]:
            msg = conv[0]
            timestamp = conv[1]
            strategy_info = self.extractor.extract_strategy_info(msg)
            
            if '第一止盈' in msg or '第二止盈' in msg:
                answer.append(f"- [{timestamp}] 分批止盈策略")
            elif strategy_info.get('prices'):
                answer.append(f"- [{timestamp}] 止盈价格: ${strategy_info['prices'][0]:,.0f}")
            else:
                answer.append(f"- [{timestamp}] {msg[:80]}...")
        
        return '\n'.join(answer)
    
    def _answer_market_condition(self, question: str, start_timestamp: str) -> str:
        """回答市场环境策略问题"""
        # 提取市场环境关键词
        market_keywords = ['震荡', '趋势', '垃圾时间']
        found_keyword = None
        for kw in market_keywords:
            if kw in question:
                found_keyword = kw
                break
        
        conn = self.db._get_connection()
        if found_keyword:
            conversations = conn.execute('''
                SELECT trader_message, timestamp FROM conversations
                WHERE timestamp >= ? AND trader_message LIKE ?
                ORDER BY timestamp DESC
                LIMIT 20
            ''', [start_timestamp, f'%{found_keyword}%']).fetchall()
        else:
            conversations = conn.execute('''
                SELECT trader_message, timestamp FROM conversations
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT 50
            ''', [start_timestamp]).fetchall()
        
        conn.close()
        
        if not conversations:
            return "最近没有找到相关市场环境策略信息。"
        
        answer = ["市场环境策略：\n"]
        for conv in conversations[:5]:
            msg = conv[0]
            timestamp = conv[1]
            strategy_info = self.extractor.extract_strategy_info(msg)
            if strategy_info.get('strategy'):
                answer.append(f"- [{timestamp}] {', '.join(strategy_info['strategy'])}")
        
        return '\n'.join(answer)
    
    def _answer_direction(self, question: str, start_timestamp: str) -> str:
        """回答方向策略问题"""
        direction = None
        if '做多' in question or '多' in question:
            direction = 'long'
        elif '做空' in question or '空' in question:
            direction = 'short'
        
        if not direction:
            return "请明确是问做多还是做空的策略。"
        
        conn = self.db._get_connection()
        conversations = conn.execute('''
            SELECT trader_message, timestamp FROM conversations
            WHERE timestamp >= ? AND trader_message LIKE ?
            ORDER BY timestamp DESC
            LIMIT 30
        ''', [start_timestamp, f'%{direction}%']).fetchall()
        conn.close()
        
        if not conversations:
            return f"最近没有找到做{direction}的策略信息。"
        
        # 提取策略
        strategies = []
        for conv in conversations:
            msg = conv[0]
            if msg:
                strategy_info = self.extractor.extract_strategy_info(msg)
                strategies.extend(strategy_info.get('strategy', []))
        
        from collections import Counter
        strategy_counts = Counter(strategies)
        
        answer = [f"De.做{direction}的策略：\n"]
        for strategy, count in strategy_counts.most_common(5):
            answer.append(f"- {strategy}: {count}次")
        
        return '\n'.join(answer)
    
    def _answer_general(self, question: str, start_timestamp: str) -> str:
        """回答一般性问题"""
        # 关键词搜索
        keywords = re.findall(r'[\u4e00-\u9fa5]+', question)
        
        if not keywords:
            return "请提供更具体的问题。"
        
        conn = self.db._get_connection()
        
        # 构建搜索条件
        conditions = []
        params = [start_timestamp]
        for kw in keywords[:3]:  # 最多3个关键词
            conditions.append('trader_message LIKE ?')
            params.append(f'%{kw}%')
        
        query = f'''
            SELECT trader_message, timestamp FROM conversations
            WHERE timestamp >= ? AND ({' OR '.join(conditions)})
            ORDER BY timestamp DESC
            LIMIT 10
        '''
        
        conversations = conn.execute(query, params).fetchall()
        conn.close()
        
        if not conversations:
            return f"没有找到关于'{question}'的相关信息。"
        
        answer = [f"关于'{question}'的相关信息：\n"]
        for conv in conversations[:5]:
            msg = conv[0]
            timestamp = conv[1]
            answer.append(f"- [{timestamp}] {msg[:100]}...")
        
        return '\n'.join(answer)

def interactive_qa():
    """交互式问答"""
    qa = DeStrategyQA()
    
    print("=" * 80)
    print("De.策略问答系统")
    print("=" * 80)
    print()
    print("输入问题，输入 'exit' 或 '退出' 结束")
    print("示例问题：")
    print("  - De.最近用了什么策略？")
    print("  - De.在什么价格区间做多？")
    print("  - De.的止损策略是什么？")
    print()
    
    while True:
        try:
            question = input("问题: ").strip()
            if not question or question.lower() in ['exit', '退出', 'quit']:
                break
            
            answer = qa.answer_question(question)
            print()
            print("答案:")
            print(answer)
            print()
        except KeyboardInterrupt:
            print("\n\n已退出")
            break
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='De.策略问答系统')
    parser.add_argument('question', nargs='?', help='问题文本')
    parser.add_argument('--days', type=int, default=30, help='查询最近N天的数据（默认30天）')
    parser.add_argument('--interactive', action='store_true', help='交互式模式')
    
    args = parser.parse_args()
    
    if args.interactive or not args.question:
        interactive_qa()
    else:
        qa = DeStrategyQA()
        answer = qa.answer_question(args.question, days=args.days)
        print(answer)

if __name__ == '__main__':
    main()



