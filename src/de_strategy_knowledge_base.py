#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
De.策略知识库
存储策略、规则、概念之间的关系
整合规则引擎、ML/DL系统的知识
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager

class StrategyRuleMapping:
    """策略-规则映射"""
    
    def __init__(self):
        # 策略到规则的映射
        self.strategy_to_rules = {
            'FVG策略': {
                'rules': ['FVG_Bullish_Long', 'FVG_Bearish_Short'],
                'concepts': ['FVG', 'Fair Value Gap', '价格缺口'],
                'market_conditions': ['trend', 'volatile'],
                'timeframes': ['5m', '15m'],
                'priority': 100,
                'description': 'FVG（Fair Value Gap）价格缺口策略，优先级最高'
            },
            'Vegas通道策略': {
                'rules': ['Vegas_Above_Long', 'Vegas_Below_Short', 'Vegas_Breakout'],
                'concepts': ['Vegas', 'EMA144', 'EMA169', '动态支撑阻力'],
                'market_conditions': ['trend', 'consolidation'],
                'timeframes': ['15m', '1h'],
                'priority': 70,
                'description': 'Vegas通道（EMA144/169）作为动态支撑阻力'
            },
            '区间震荡策略': {
                'rules': ['Range_Breakout', 'Range_Bounce'],
                'concepts': ['区间', '震荡', '箱体', '突破'],
                'market_conditions': ['consolidation'],
                'timeframes': ['5m', '15m'],
                'priority': 85,
                'description': '区间震荡市场，在区间上下沿挂单'
            },
            '保本止损策略': {
                'rules': ['Breakeven_Stop_Loss'],
                'concepts': ['保本', '盈亏平衡', '风险管理'],
                'market_conditions': ['all'],
                'timeframes': ['all'],
                'priority': 50,
                'description': '盈利后移动止损到保本位置'
            },
            '分批止盈策略': {
                'rules': ['Partial_Take_Profit'],
                'concepts': ['止盈', '分批', '风险管理'],
                'market_conditions': ['all'],
                'timeframes': ['all'],
                'priority': 50,
                'description': '分批止盈，第一止盈位止盈50%，第二止盈位止盈50%'
            },
            'M顶W底策略': {
                'rules': ['M_Top_Short', 'W_Bottom_Long'],
                'concepts': ['M顶', 'W底', '双顶', '双底', '反转形态'],
                'market_conditions': ['reversal', 'consolidation'],
                'timeframes': ['15m', '1h'],
                'priority': 90,
                'description': 'M顶/W底反转形态识别'
            },
        }
        
        # 规则到策略的反向映射
        self.rule_to_strategies = {}
        for strategy, info in self.strategy_to_rules.items():
            for rule in info['rules']:
                if rule not in self.rule_to_strategies:
                    self.rule_to_strategies[rule] = []
                self.rule_to_strategies[rule].append({
                    'strategy': strategy,
                    'priority': info['priority'],
                    'description': info['description']
                })
        
        # 概念到策略的映射
        self.concept_to_strategies = {}
        for strategy, info in self.strategy_to_rules.items():
            for concept in info['concepts']:
                if concept not in self.concept_to_strategies:
                    self.concept_to_strategies[concept] = []
                self.concept_to_strategies[concept].append(strategy)
    
    def get_strategy_rules(self, strategy_name: str) -> Optional[Dict]:
        """获取策略对应的规则"""
        return self.strategy_to_rules.get(strategy_name)
    
    def get_rule_strategies(self, rule_name: str) -> List[Dict]:
        """获取规则对应的策略"""
        return self.rule_to_strategies.get(rule_name, [])
    
    def get_concept_strategies(self, concept: str) -> List[str]:
        """获取概念对应的策略"""
        return self.concept_to_strategies.get(concept, [])
    
    def find_strategies_by_concept(self, concepts: List[str]) -> Dict[str, List[str]]:
        """根据概念列表查找策略"""
        result = {}
        for concept in concepts:
            strategies = self.get_concept_strategies(concept)
            if strategies:
                result[concept] = strategies
        return result


class DeStrategyKnowledgeBase:
    """De.策略知识库（整合规则引擎和ML/DL）"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.mapping = StrategyRuleMapping()
        
        # 尝试导入规则引擎
        try:
            import sys
            rules_engine_path = Path(__file__).parent.parent / "rules_engine"
            if str(rules_engine_path) not in sys.path:
                sys.path.insert(0, str(rules_engine_path))
            
            from trading_rules_engine import TradingRulesEngine, TradingSignal
            self.rules_engine_available = True
            self.TradingRulesEngine = TradingRulesEngine
            self.TradingSignal = TradingSignal
        except (ImportError, AttributeError, ModuleNotFoundError) as e:
            self.rules_engine_available = False
            # 静默失败，不影响其他功能
            if hasattr(sys, 'stderr'):
                print(f"提示: 规则引擎不可用（{type(e).__name__}），部分功能将受限", file=sys.stderr)
        
        # 尝试导入ML/DL系统
        try:
            from ml_dl.trading_brain_system import TradingBrainSystem
            self.trading_brain_available = True
            self.TradingBrainSystem = TradingBrainSystem
        except ImportError:
            self.trading_brain_available = False
            print("警告: 交易员大脑系统不可用，部分功能将受限", file=sys.stderr)
    
    def get_strategy_rules_info(self, strategy_name: str) -> Dict:
        """获取策略的规则信息"""
        mapping_info = self.mapping.get_strategy_rules(strategy_name)
        if not mapping_info:
            return {
                'strategy': strategy_name,
                'error': '策略不存在'
            }
        
        result = {
            'strategy': strategy_name,
            'rules': mapping_info.get('rules', []),
            'concepts': mapping_info.get('concepts', []),
            'market_conditions': mapping_info.get('market_conditions', []),
            'timeframes': mapping_info.get('timeframes', []),
            'priority': mapping_info.get('priority', 0),
            'description': mapping_info.get('description', ''),
            'rule_details': []
        }
        
        # 从数据库查找相关规则的使用情况
        try:
            conn = self.db._get_connection()
            
            # 查找包含这些概念的对话/观点
            for concept in mapping_info.get('concepts', [])[:3]:  # 只查前3个概念
                try:
                    viewpoints = conn.execute('''
                        SELECT content, timestamp, category, tags FROM trader_viewpoints
                        WHERE content LIKE ? AND category IN ('trading_signal', 'trading_execution')
                        ORDER BY timestamp DESC
                        LIMIT 10
                    ''', [f'%{concept}%']).fetchall()
                    
                    if viewpoints:
                        result['rule_details'].append({
                            'concept': concept,
                            'examples': [vp[0][:100] for vp in viewpoints[:3]]  # 最近3个例子
                        })
                except Exception as e:
                    # 忽略单个概念查询错误
                    continue
            
            conn.close()
        except Exception as e:
            # 数据库查询失败不影响返回基本信息
            pass
        
        return result
    
    def get_rule_usage_stats(self, rule_name: str, days: int = 30) -> Dict:
        """获取规则使用统计"""
        from datetime import timedelta
        start_date = datetime.now() - timedelta(days=days)
        start_timestamp = start_date.strftime('%Y-%m-%d %H:%M:%S')
        
        conn = self.db._get_connection()
        
        # 查找相关策略的使用情况
        strategies = self.mapping.get_rule_strategies(rule_name)
        strategy_names = [s['strategy'] for s in strategies]
        
        # 统计对话中提到的策略
        stats = {
            'rule_name': rule_name,
            'related_strategies': strategy_names,
            'usage_count': 0,
            'recent_examples': []
        }
        
        for strategy in strategy_names:
            # 查找包含策略关键词的对话
            keywords = self.mapping.get_strategy_rules(strategy)['concepts']
            for keyword in keywords[:2]:  # 前2个关键词
                results = conn.execute('''
                    SELECT trader_message, timestamp FROM conversations
                    WHERE timestamp >= ? AND trader_message LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT 5
                ''', [start_timestamp, f'%{keyword}%']).fetchall()
                
                stats['usage_count'] += len(results)
                for result in results:
                    stats['recent_examples'].append({
                        'content': result[0][:100],
                        'timestamp': result[1]
                    })
        
        conn.close()
        
        return stats
    
    def analyze_strategy_with_rules_engine(self, strategy_name: str, market_data: Dict = None) -> Dict:
        """使用规则引擎分析策略"""
        if not self.rules_engine_available:
            return {'error': '规则引擎不可用'}
        
        mapping_info = self.mapping.get_strategy_rules(strategy_name)
        if not mapping_info:
            return {'error': f'未找到策略: {strategy_name}'}
        
        # 这里可以调用规则引擎分析
        # 暂时返回策略信息
        return {
            'strategy': strategy_name,
            'rules': mapping_info['rules'],
            'description': mapping_info['description'],
            'market_conditions': mapping_info['market_conditions'],
            'note': '规则引擎分析功能待实现'
        }
    
    def get_ml_prediction_for_strategy(self, strategy_name: str) -> Dict:
        """获取ML/DL对策略的预测"""
        if not self.trading_brain_available:
            return {'error': '交易员大脑系统不可用'}
        
        try:
            brain = self.TradingBrainSystem(self.trader_id)
            signal = brain.generate_trading_signal()
            brain.close()
            
            return {
                'strategy': strategy_name,
                'ml_signal': signal.get('signal'),
                'confidence': signal.get('confidence', 0.0),
                'reason': signal.get('reason', '')
            }
        except Exception as e:
            return {'error': f'ML预测失败: {e}'}
    
    def get_strategy_relationships(self, strategy_name: str) -> Dict:
        """获取策略的关系网络"""
        mapping_info = self.mapping.get_strategy_rules(strategy_name)
        if not mapping_info:
            return {}
        
        relationships = {
            'strategy': strategy_name,
            'rules': mapping_info['rules'],
            'concepts': mapping_info['concepts'],
            'related_strategies': set(),
            'related_concepts': set()
        }
        
        # 查找相关策略（通过共享概念）
        for concept in mapping_info['concepts']:
            related_strategies = self.mapping.get_concept_strategies(concept)
            for rs in related_strategies:
                if rs != strategy_name:
                    relationships['related_strategies'].add(rs)
        
        # 查找相关概念（通过相关策略）
        for rs in relationships['related_strategies']:
            rs_info = self.mapping.get_strategy_rules(rs)
            if rs_info:
                relationships['related_concepts'].update(rs_info['concepts'])
        
        relationships['related_strategies'] = list(relationships['related_strategies'])
        relationships['related_concepts'] = list(relationships['related_concepts'])
        
        return relationships
    
    def save_knowledge_graph(self, output_file: str = None):
        """保存知识图谱到JSON文件"""
        if output_file is None:
            output_file = Path(__file__).parent.parent / "data" / "strategy_knowledge_graph.json"
        
        graph = {
            'strategies': {},
            'rules': {},
            'concepts': {},
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 构建策略节点
        for strategy, info in self.mapping.strategy_to_rules.items():
            graph['strategies'][strategy] = {
                'rules': info['rules'],
                'concepts': info['concepts'],
                'market_conditions': info['market_conditions'],
                'timeframes': info['timeframes'],
                'priority': info['priority'],
                'description': info['description']
            }
        
        # 构建规则节点
        for rule, strategies in self.mapping.rule_to_strategies.items():
            graph['rules'][rule] = {
                'strategies': [s['strategy'] for s in strategies],
                'priority': max([s['priority'] for s in strategies]) if strategies else 0
            }
        
        # 构建概念节点
        for concept, strategies in self.mapping.concept_to_strategies.items():
            graph['concepts'][concept] = {
                'strategies': strategies,
                'usage_count': len(strategies)
            }
        
        # 保存到文件
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        
        return output_path

