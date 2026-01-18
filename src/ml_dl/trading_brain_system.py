#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易员大脑系统
模拟De.交易决策的端到端AI系统
结合规则引擎、市场感知、强化学习
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from db_manager_trader import TraderDBManager
from behavior_pattern_analyzer import BehaviorPatternAnalyzer
from sentiment_analyzer import SentimentAnalyzer


class MarketEnvironmentPerceiver:
    """市场环境感知器"""
    
    def __init__(self):
        self.db = None  # 价格数据连接
    
    def perceive_environment(self, price_data: Dict, indicators: Dict = None) -> Dict:
        """
        感知市场环境
        
        Args:
            price_data: 价格数据 {'5m': df, '15m': df, '1h': df, ...}
            indicators: 技术指标
        
        Returns:
            市场环境特征
        """
        environment = {
            'market_state': 'unknown',  # trend/consolidation/reversal
            'volatility_level': 'medium',  # low/medium/high
            'liquidity_level': 'medium',  # low/medium/high
            'trend_strength': 0.0,  # -1 to 1
            'opportunity_score': 0.0,  # 0 to 1
            'risk_level': 'medium'  # low/medium/high
        }
        
        if not price_data:
            return environment
        
        # 使用15分钟数据作为主要分析框架
        main_df = price_data.get('15m')
        if main_df is None or len(main_df) < 20:
            return environment
        
        # 1. 判断市场状态（趋势/震荡）
        environment['market_state'] = self._classify_market_state(main_df)
        
        # 2. 计算波动率
        environment['volatility_level'] = self._calculate_volatility(main_df)
        
        # 3. 计算趋势强度
        environment['trend_strength'] = self._calculate_trend_strength(main_df)
        
        # 4. 计算机会分数
        environment['opportunity_score'] = self._calculate_opportunity_score(
            main_df, environment
        )
        
        # 5. 评估风险
        environment['risk_level'] = self._assess_risk(main_df, environment)
        
        return environment
    
    def _classify_market_state(self, df: pd.DataFrame) -> str:
        """分类市场状态"""
        if len(df) < 20:
            return 'unknown'
        
        # 计算价格变化
        price_changes = df['close'].pct_change().dropna()
        
        # 计算移动平均
        ma_short = df['close'].rolling(window=10).mean()
        ma_long = df['close'].rolling(window=20).mean()
        
        if len(ma_short) < 20 or len(ma_long) < 20:
            return 'unknown'
        
        # 趋势判断
        current_ma_short = ma_short.iloc[-1]
        current_ma_long = ma_long.iloc[-1]
        
        # 计算价格在均线附近的波动
        price_std = df['close'].rolling(window=20).std().iloc[-1]
        price_mean = df['close'].mean()
        volatility_ratio = price_std / price_mean if price_mean > 0 else 0
        
        # 如果波动率低且价格围绕均线震荡，判断为震荡
        if volatility_ratio < 0.01 and abs(current_ma_short - current_ma_long) / current_ma_long < 0.005:
            return 'consolidation'
        
        # 如果短期均线明显高于长期均线，判断为上涨趋势
        if current_ma_short > current_ma_long * 1.01:
            return 'trend_up'
        
        # 如果短期均线明显低于长期均线，判断为下跌趋势
        if current_ma_short < current_ma_long * 0.99:
            return 'trend_down'
        
        return 'consolidation'
    
    def _calculate_volatility(self, df: pd.DataFrame) -> str:
        """计算波动率水平"""
        if len(df) < 20:
            return 'medium'
        
        returns = df['close'].pct_change().dropna()
        volatility = returns.std()
        
        # 根据历史波动率分位数判断
        if volatility < 0.005:
            return 'low'
        elif volatility > 0.02:
            return 'high'
        else:
            return 'medium'
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """计算趋势强度 (-1到1)"""
        if len(df) < 20:
            return 0.0
        
        # 使用线性回归计算趋势
        x = np.arange(len(df))
        y = df['close'].values
        
        # 简单线性回归
        slope = np.polyfit(x, y, 1)[0]
        
        # 归一化到-1到1
        price_range = df['close'].max() - df['close'].min()
        if price_range > 0:
            trend_strength = (slope * len(df)) / price_range
            trend_strength = np.clip(trend_strength, -1, 1)
        else:
            trend_strength = 0.0
        
        return float(trend_strength)
    
    def _calculate_opportunity_score(self, df: pd.DataFrame, env: Dict) -> float:
        """计算交易机会分数"""
        score = 0.5  # 基础分数
        
        # 市场状态加分
        if env['market_state'] == 'consolidation':
            score += 0.2  # 震荡市场适合区间交易
        
        # 波动率适中加分
        if env['volatility_level'] == 'medium':
            score += 0.1
        
        # 趋势明确加分
        if abs(env['trend_strength']) > 0.3:
            score += 0.2
        
        return min(score, 1.0)
    
    def _assess_risk(self, df: pd.DataFrame, env: Dict) -> str:
        """评估风险水平"""
        if env['volatility_level'] == 'high':
            return 'high'
        elif env['volatility_level'] == 'low':
            return 'low'
        else:
            return 'medium'


class RuleKnowledgeBase:
    """规则知识库"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.rules = self._load_rules()
    
    def _load_rules(self) -> Dict:
        """从数据库加载规则"""
        rules = {
            'entry_rules': [],
            'exit_rules': [],
            'risk_rules': [],
            'market_condition_rules': []
        }
        
        # 从观点中提取规则
        viewpoints = self.db.get_viewpoints(limit=1000)
        
        for vp in viewpoints:
            content = vp.get('content', '')
            category = vp.get('category', '')
            
            if category == 'trading_signal':
                # 提取入场规则
                if any(kw in content for kw in ['挂', '可以', '建议', '突破', '回踩']):
                    rules['entry_rules'].append({
                        'content': content,
                        'timestamp': vp.get('timestamp'),
                        'btc_price': vp.get('btc_price'),
                        'priority': self._extract_priority(content)
                    })
            
            if category == 'trading_execution':
                # 提取出场规则
                if any(kw in content for kw in ['止盈', '止损', '保本']):
                    rules['exit_rules'].append({
                        'content': content,
                        'timestamp': vp.get('timestamp'),
                        'btc_price': vp.get('btc_price')
                    })
        
        return rules
    
    def _extract_priority(self, content: str) -> int:
        """从内容中提取优先级"""
        if 'FVG' in content or 'fvg' in content.lower():
            return 100
        elif 'M顶' in content or 'W底' in content:
            return 90
        elif '突破' in content:
            return 85
        elif 'Vegas' in content or 'vegas' in content.lower():
            return 70
        else:
            return 50
    
    def match_rules(self, market_environment: Dict, current_price: float) -> List[Dict]:
        """匹配适用的规则"""
        matched_rules = []
        
        # 根据市场环境匹配规则
        market_state = market_environment.get('market_state', 'unknown')
        
        for rule in self.rules['entry_rules']:
            content = rule.get('content', '')
            
            # 简单匹配逻辑（可以增强）
            if market_state == 'consolidation' and '区间' in content:
                matched_rules.append(rule)
            elif market_state in ['trend_up', 'trend_down'] and '突破' in content:
                matched_rules.append(rule)
        
        # 按优先级排序
        matched_rules.sort(key=lambda x: x.get('priority', 0), reverse=True)
        
        return matched_rules


class TradingBrainSystem:
    """交易员大脑系统（主系统）"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.market_perceiver = MarketEnvironmentPerceiver()
        self.rule_knowledge = RuleKnowledgeBase(trader_id)
        self.behavior_analyzer = BehaviorPatternAnalyzer(trader_id)
        self.sentiment_analyzer = SentimentAnalyzer(trader_id)
        
        # 加载价格数据连接
        self._init_price_data()
    
    def _init_price_data(self):
        """初始化价格数据连接"""
        try:
            import duckdb
            ts_file = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
            if ts_file.exists():
                self.price_conn = duckdb.connect(str(ts_file))
            else:
                self.price_conn = None
        except:
            self.price_conn = None
    
    def load_market_data(self, timeframes: List[str] = ['5m', '15m', '1h']) -> Dict:
        """加载多时间框架市场数据"""
        if not self.price_conn:
            return {}
        
        market_data = {}
        
        for tf in timeframes:
            table_name = f'btc_price_{tf}'
            try:
                # 检查表是否存在
                tables = self.price_conn.execute("SHOW TABLES").fetchall()
                table_names = [t[0] for t in tables]
                
                if table_name in table_names:
                    # 加载最近500条数据
                    query = f'''
                        SELECT timestamp, datetime, open, high, low, close, volume
                        FROM {table_name}
                        ORDER BY timestamp DESC
                        LIMIT 500
                    '''
                    df = pd.read_sql(query, self.price_conn)
                    df = df.sort_values('timestamp')  # 按时间正序
                    market_data[tf] = df
            except Exception as e:
                print(f"  加载{tf}数据失败: {e}", file=sys.stderr)
        
        return market_data
    
    def generate_trading_signal(self, market_data: Dict = None) -> Dict:
        """
        生成交易信号（核心决策函数）
        
        Args:
            market_data: 市场数据（如果为None则自动加载）
        
        Returns:
            交易信号字典
        """
        # 1. 加载市场数据
        if market_data is None:
            market_data = self.load_market_data()
        
        if not market_data:
            return {
                'signal': None,
                'reason': '无市场数据',
                'confidence': 0.0
            }
        
        # 2. 感知市场环境
        environment = self.market_perceiver.perceive_environment(market_data)
        
        # 3. 匹配交易规则
        current_price = market_data.get('15m', pd.DataFrame()).get('close', pd.Series()).iloc[-1] if '15m' in market_data and len(market_data['15m']) > 0 else None
        
        if current_price is None:
            return {
                'signal': None,
                'reason': '无法获取当前价格',
                'confidence': 0.0
            }
        
        matched_rules = self.rule_knowledge.match_rules(environment, current_price)
        
        # 4. 分析交易员情绪
        sentiment_results = self.sentiment_analyzer.analyze_viewpoints(limit=50)
        recent_sentiment = self._aggregate_sentiment(sentiment_results[-10:]) if len(sentiment_results) >= 10 else None
        
        # 5. 综合决策
        signal = self._make_decision(
            environment=environment,
            matched_rules=matched_rules,
            current_price=current_price,
            sentiment=recent_sentiment,
            market_data=market_data
        )
        
        return signal
    
    def _aggregate_sentiment(self, sentiment_results: List[Dict]) -> Dict:
        """聚合情绪结果"""
        if not sentiment_results:
            return {'sentiment': 'neutral', 'score': 0.0}
        
        avg_score = sum(r.get('sentiment_score', 0) for r in sentiment_results) / len(sentiment_results)
        
        if avg_score > 0.3:
            sentiment = 'bullish'
        elif avg_score < -0.3:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'score': avg_score,
            'confidence': sum(r.get('confidence', 0) for r in sentiment_results) / len(sentiment_results)
        }
    
    def _make_decision(self, environment: Dict, matched_rules: List[Dict],
                      current_price: float, sentiment: Optional[Dict],
                      market_data: Dict) -> Dict:
        """做出交易决策"""
        # 如果没有匹配的规则，不生成信号
        if not matched_rules:
            return {
                'signal': None,
                'reason': '无匹配的交易规则',
                'confidence': 0.0,
                'environment': environment
            }
        
        # 选择最高优先级的规则
        top_rule = matched_rules[0]
        
        # 根据规则和环境生成信号
        signal = self._generate_signal_from_rule(
            rule=top_rule,
            environment=environment,
            current_price=current_price,
            sentiment=sentiment,
            market_data=market_data
        )
        
        return signal
    
    def _generate_signal_from_rule(self, rule: Dict, environment: Dict,
                                   current_price: float, sentiment: Optional[Dict],
                                   market_data: Dict) -> Dict:
        """从规则生成交易信号"""
        content = rule.get('content', '')
        
        # 提取方向
        direction = 'long'
        if '空' in content or '做空' in content or 'short' in content.lower():
            direction = 'short'
        elif '多' in content or '做多' in content or 'long' in content.lower():
            direction = 'long'
        
        # 提取价格
        import re
        prices = re.findall(r'(\d{4,5})', content)
        entry_price = current_price
        stop_loss = None
        take_profit_1 = None
        take_profit_2 = None
        
        if prices:
            # 尝试解析价格
            price_values = [int(p) for p in prices if 40000 <= int(p) <= 150000]
            if price_values:
                # 根据方向选择价格
                if direction == 'long':
                    entry_price = min(price_values) if price_values else current_price
                else:
                    entry_price = max(price_values) if price_values else current_price
        
        # 计算止损止盈（基于规则和风险）
        risk_pct = 0.015  # 默认1.5%风险
        if direction == 'long':
            stop_loss = entry_price * (1 - risk_pct)
            take_profit_1 = entry_price * (1 + risk_pct * 2.5)
            take_profit_2 = entry_price * (1 + risk_pct * 3.5)
        else:
            stop_loss = entry_price * (1 + risk_pct)
            take_profit_1 = entry_price * (1 - risk_pct * 2.5)
            take_profit_2 = entry_price * (1 - risk_pct * 3.5)
        
        # 计算置信度
        confidence = self._calculate_confidence(
            rule=rule,
            environment=environment,
            sentiment=sentiment
        )
        
        # 如果置信度太低，不生成信号
        if confidence < 0.5:
            return {
                'signal': None,
                'reason': f'置信度太低 ({confidence:.2f})',
                'confidence': confidence
            }
        
        return {
            'signal': {
                'direction': direction,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'timeframe': '15m',
                'rule_name': rule.get('content', '')[:50],
                'priority': rule.get('priority', 50)
            },
            'reason': f"规则匹配: {rule.get('content', '')[:100]}",
            'confidence': confidence,
            'environment': environment,
            'sentiment': sentiment
        }
    
    def _calculate_confidence(self, rule: Dict, environment: Dict,
                             sentiment: Optional[Dict]) -> float:
        """计算信号置信度"""
        confidence = 0.5  # 基础置信度
        
        # 规则优先级影响
        priority = rule.get('priority', 50)
        confidence += (priority / 100) * 0.3
        
        # 市场环境匹配
        if environment.get('opportunity_score', 0) > 0.6:
            confidence += 0.1
        
        # 情绪一致性
        if sentiment:
            sentiment_score = sentiment.get('score', 0)
            # 如果情绪与方向一致，加分
            # 这里简化处理
            if abs(sentiment_score) > 0.3:
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def close(self):
        """关闭连接"""
        if hasattr(self, 'price_conn') and self.price_conn:
            self.price_conn.close()
        self.rule_knowledge.db.close()
        self.behavior_analyzer.db.close()
        self.sentiment_analyzer.db.close()


def main():
    """主函数"""
    print("=" * 80)
    print("交易员大脑系统 - 生成交易信号")
    print("=" * 80)
    print()
    
    brain = TradingBrainSystem(trader_id='de')
    
    # 生成交易信号
    print("分析市场环境并生成交易信号...")
    signal_result = brain.generate_trading_signal()
    
    print()
    print("=" * 80)
    print("信号生成结果")
    print("=" * 80)
    
    if signal_result.get('signal'):
        signal = signal_result['signal']
        print(f"✓ 生成交易信号")
        print()
        print(f"方向: {signal['direction']}")
        print(f"入场价格: ${signal['entry_price']:,.2f}")
        print(f"止损: ${signal['stop_loss']:,.2f}")
        print(f"第一止盈: ${signal['take_profit_1']:,.2f}")
        print(f"第二止盈: ${signal['take_profit_2']:,.2f}")
        print(f"置信度: {signal_result['confidence']:.2%}")
        print()
        print(f"原因: {signal_result['reason']}")
        print()
        
        if signal_result.get('environment'):
            env = signal_result['environment']
            print("市场环境:")
            print(f"  市场状态: {env.get('market_state')}")
            print(f"  波动率: {env.get('volatility_level')}")
            print(f"  趋势强度: {env.get('trend_strength'):.2f}")
            print(f"  机会分数: {env.get('opportunity_score'):.2f}")
    else:
        print("✗ 未生成交易信号")
        print(f"原因: {signal_result.get('reason', '未知')}")
    
    print()
    print("=" * 80)
    
    brain.close()

if __name__ == '__main__':
    main()










