#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版De.策略问答系统
整合规则引擎、ML/DL系统、策略知识库
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from de_strategy_qa import DeStrategyQA
from de_strategy_knowledge_base import DeStrategyKnowledgeBase, StrategyRuleMapping

class EnhancedDeStrategyQA(DeStrategyQA):
    """增强版策略问答系统"""
    
    def __init__(self, trader_id='de'):
        super().__init__(trader_id)
        self.knowledge_base = DeStrategyKnowledgeBase(trader_id)
        self.mapping = StrategyRuleMapping()
    
    def answer_question(self, question: str, days: int = 30) -> str:
        """
        增强版回答问题（整合规则引擎和ML/DL）
        """
        # 先使用基础问答
        base_answer = super().answer_question(question, days)
        
        # 识别问题类型并增强
        question_lower = question.lower()
        
        # 策略-规则关系问题
        if any(kw in question_lower for kw in ['规则', 'rule', '策略规则', '规则引擎']):
            return self._answer_strategy_rules_question(question, base_answer)
        
        # ML/DL预测问题
        if any(kw in question_lower for kw in ['预测', 'ML', '深度学习', '机器学习', '模型']):
            return self._answer_ml_prediction_question(question, base_answer)
        
        # 策略关系问题
        if any(kw in question_lower for kw in ['关系', '关联', '相关', '联系']):
            return self._answer_strategy_relationship_question(question, base_answer)
        
        # 策略效果问题
        if any(kw in question_lower for kw in ['效果', '成功率', '表现', '统计']):
            return self._answer_strategy_performance_question(question, base_answer)
        
        return base_answer
    
    def _answer_strategy_rules_question(self, question: str, base_answer: str) -> str:
        """回答策略-规则关系问题"""
        # 提取策略名称
        strategy_keywords = list(self.mapping.strategy_to_rules.keys())
        found_strategy = None
        
        for strategy in strategy_keywords:
            # 检查策略名称或关键词
            strategy_keywords_list = self.mapping.get_strategy_rules(strategy)['concepts']
            if any(kw in question for kw in [strategy] + strategy_keywords_list):
                found_strategy = strategy
                break
        
        if not found_strategy:
            # 尝试从基础答案中提取
            for strategy in strategy_keywords:
                if strategy in base_answer:
                    found_strategy = strategy
                    break
        
        if found_strategy:
            strategy_info = self.knowledge_base.get_strategy_rules_info(found_strategy)
            if strategy_info:
                answer = [f"【{found_strategy}】的规则信息：\n"]
                answer.append(f"规则引擎规则: {', '.join(strategy_info['rules'])}")
                answer.append(f"核心概念: {', '.join(strategy_info['concepts'])}")
                answer.append(f"适用市场: {', '.join(strategy_info['market_conditions'])}")
                answer.append(f"时间框架: {', '.join(strategy_info['timeframes'])}")
                answer.append(f"优先级: {strategy_info['priority']}")
                answer.append(f"描述: {strategy_info['description']}")
                
                if strategy_info.get('rule_details'):
                    answer.append("\n相关示例：")
                    for detail in strategy_info['rule_details'][:3]:
                        answer.append(f"- {detail['concept']}: {detail['examples'][0][:60]}...")
                
                return '\n'.join(answer)
        
        return base_answer + "\n\n提示: 可以询问具体策略的规则信息，如'FVG策略的规则是什么？'"
    
    def _answer_ml_prediction_question(self, question: str, base_answer: str) -> str:
        """回答ML/DL预测问题"""
        # 提取策略名称
        strategy_keywords = list(self.mapping.strategy_to_rules.keys())
        found_strategy = None
        
        for strategy in strategy_keywords:
            if strategy in question:
                found_strategy = strategy
                break
        
        if found_strategy:
            ml_result = self.knowledge_base.get_ml_prediction_for_strategy(found_strategy)
            if 'error' not in ml_result:
                answer = [f"【{found_strategy}】的ML/DL预测：\n"]
                if ml_result.get('ml_signal'):
                    signal = ml_result['ml_signal']
                    answer.append(f"信号方向: {signal.get('direction', 'N/A')}")
                    answer.append(f"入场价格: ${signal.get('entry_price', 0):,.2f}")
                    answer.append(f"置信度: {ml_result.get('confidence', 0):.2%}")
                    answer.append(f"理由: {ml_result.get('reason', 'N/A')}")
                else:
                    answer.append("当前无ML预测信号")
                
                return '\n'.join(answer)
        
        return base_answer + "\n\n提示: ML/DL预测功能需要交易员大脑系统支持"
    
    def _answer_strategy_relationship_question(self, question: str, base_answer: str) -> str:
        """回答策略关系问题"""
        # 提取策略名称
        strategy_keywords = list(self.mapping.strategy_to_rules.keys())
        found_strategy = None
        
        for strategy in strategy_keywords:
            if strategy in question or any(kw in question for kw in self.mapping.get_strategy_rules(strategy)['concepts']):
                found_strategy = strategy
                break
        
        if found_strategy:
            relationships = self.knowledge_base.get_strategy_relationships(found_strategy)
            if relationships:
                answer = [f"【{found_strategy}】的关系网络：\n"]
                answer.append(f"相关规则: {', '.join(relationships['rules'])}")
                answer.append(f"核心概念: {', '.join(relationships['concepts'])}")
                
                if relationships.get('related_strategies'):
                    answer.append(f"\n相关策略: {', '.join(relationships['related_strategies'])}")
                
                if relationships.get('related_concepts'):
                    answer.append(f"相关概念: {', '.join(list(relationships['related_concepts'])[:5])}")
                
                return '\n'.join(answer)
        
        return base_answer
    
    def _answer_strategy_performance_question(self, question: str, base_answer: str) -> str:
        """回答策略效果问题"""
        # 提取规则名称
        rule_keywords = list(self.mapping.rule_to_strategies.keys())
        found_rule = None
        
        for rule in rule_keywords:
            if rule.lower() in question.lower():
                found_rule = rule
                break
        
        if found_rule:
            stats = self.knowledge_base.get_rule_usage_stats(found_rule)
            if stats:
                answer = [f"【{found_rule}】规则使用统计：\n"]
                answer.append(f"相关策略: {', '.join(stats['related_strategies'])}")
                answer.append(f"使用次数（最近30天）: {stats['usage_count']} 次")
                
                if stats.get('recent_examples'):
                    answer.append("\n最近使用示例：")
                    for example in stats['recent_examples'][:3]:
                        answer.append(f"- [{example['timestamp']}] {example['content']}...")
                
                return '\n'.join(answer)
        
        return base_answer
    
    def get_comprehensive_answer(self, question: str, days: int = 30) -> Dict:
        """获取综合答案（包含规则引擎、ML/DL、知识库）"""
        result = {
            'question': question,
            'base_answer': super().answer_question(question, days),
            'strategy_rules': None,
            'ml_prediction': None,
            'relationships': None,
            'rule_stats': None
        }
        
        # 尝试提取策略名称
        strategy_keywords = list(self.mapping.strategy_to_rules.keys())
        found_strategy = None
        
        for strategy in strategy_keywords:
            if strategy in question or any(kw in question for kw in self.mapping.get_strategy_rules(strategy)['concepts']):
                found_strategy = strategy
                break
        
        if found_strategy:
            # 策略规则信息
            result['strategy_rules'] = self.knowledge_base.get_strategy_rules_info(found_strategy)
            
            # ML预测
            result['ml_prediction'] = self.knowledge_base.get_ml_prediction_for_strategy(found_strategy)
            
            # 关系网络
            result['relationships'] = self.knowledge_base.get_strategy_relationships(found_strategy)
        
        # 规则统计
        rule_keywords = list(self.mapping.rule_to_strategies.keys())
        for rule in rule_keywords:
            if rule.lower() in question.lower():
                result['rule_stats'] = self.knowledge_base.get_rule_usage_stats(rule)
                break
        
        return result

def interactive_qa():
    """交互式问答（增强版）"""
    qa = EnhancedDeStrategyQA()
    
    print("=" * 80)
    print("De.策略问答系统（增强版 - 整合规则引擎和ML/DL）")
    print("=" * 80)
    print()
    print("输入问题，输入 'exit' 或 '退出' 结束")
    print("示例问题：")
    print("  - De.最近用了什么策略？")
    print("  - FVG策略的规则是什么？")
    print("  - Vegas策略和FVG策略有什么关系？")
    print("  - ML模型对当前市场的预测是什么？")
    print()
    
    while True:
        try:
            question = input("问题: ").strip()
            if not question or question.lower() in ['exit', '退出', 'quit']:
                break
            
            # 获取综合答案
            comprehensive = qa.get_comprehensive_answer(question)
            
            print()
            print("=" * 80)
            print("答案:")
            print("=" * 80)
            print(comprehensive['base_answer'])
            
            # 如果有额外信息，显示
            if comprehensive.get('strategy_rules'):
                print()
                print("-" * 80)
                print("策略规则信息:")
                rules_info = comprehensive['strategy_rules']
                print(f"规则: {', '.join(rules_info.get('rules', []))}")
                print(f"概念: {', '.join(rules_info.get('concepts', []))}")
                print(f"描述: {rules_info.get('description', '')}")
            
            if comprehensive.get('ml_prediction') and 'error' not in comprehensive['ml_prediction']:
                print()
                print("-" * 80)
                print("ML/DL预测:")
                ml_info = comprehensive['ml_prediction']
                if ml_info.get('ml_signal'):
                    print(f"信号: {ml_info['ml_signal'].get('direction', 'N/A')}")
                    print(f"置信度: {ml_info.get('confidence', 0):.2%}")
            
            if comprehensive.get('relationships'):
                print()
                print("-" * 80)
                print("策略关系:")
                rel_info = comprehensive['relationships']
                if rel_info.get('related_strategies'):
                    print(f"相关策略: {', '.join(rel_info['related_strategies'])}")
            
            print()
            print("=" * 80)
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
    
    parser = argparse.ArgumentParser(description='增强版De.策略问答系统')
    parser.add_argument('question', nargs='?', help='问题文本')
    parser.add_argument('--days', type=int, default=30, help='查询最近N天的数据（默认30天）')
    parser.add_argument('--interactive', action='store_true', help='交互式模式')
    parser.add_argument('--comprehensive', action='store_true', help='显示综合答案（包含规则引擎和ML/DL）')
    
    args = parser.parse_args()
    
    if args.interactive or not args.question:
        interactive_qa()
    else:
        qa = EnhancedDeStrategyQA()
        if args.comprehensive:
            result = qa.get_comprehensive_answer(args.question, days=args.days)
            print("=" * 80)
            print("综合答案")
            print("=" * 80)
            print()
            print("基础答案:")
            print(result['base_answer'])
            
            if result.get('strategy_rules'):
                print()
                print("策略规则信息:")
                print(json.dumps(result['strategy_rules'], indent=2, ensure_ascii=False))
            
            if result.get('ml_prediction'):
                print()
                print("ML预测:")
                print(json.dumps(result['ml_prediction'], indent=2, ensure_ascii=False))
        else:
            answer = qa.answer_question(args.question, days=args.days)
            print(answer)

if __name__ == '__main__':
    main()

