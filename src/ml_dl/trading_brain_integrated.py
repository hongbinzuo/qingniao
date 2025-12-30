#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合青鸟系统的交易员大脑系统
充分利用青鸟系统的现有功能，专注于智能决策增强
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 导入青鸟系统的功能
try:
    from generate_btc_de_signals import (
        get_btc_kline_gateio,
        get_btc_current_price,
        calculate_ema,
        calculate_vwap,
        calculate_rsi,
        identify_fvg,
        identify_support_resistance,
        analyze_timeframe
    )
    QINGNIAO_FUNCTIONS_AVAILABLE = True
except ImportError as e:
    QINGNIAO_FUNCTIONS_AVAILABLE = False
    print(f"警告: 无法导入青鸟系统功能: {e}", file=sys.stderr)

# 导入规则引擎
try:
    from rules_engine.trading_rules_engine import analyze_with_rules_engine
    RULES_ENGINE_AVAILABLE = True
except ImportError:
    RULES_ENGINE_AVAILABLE = False
    print("警告: 规则引擎不可用", file=sys.stderr)

# 导入统一系统
try:
    from unified_trading_system import UnifiedTradingSystem
    UNIFIED_SYSTEM_AVAILABLE = True
except ImportError:
    UNIFIED_SYSTEM_AVAILABLE = False

# 导入交易员大脑系统的智能组件
from ml_dl.trading_brain_system import (
    MarketEnvironmentPerceiver,
    RuleKnowledgeBase,
    TradingBrainSystem
)
from ml_dl.behavior_pattern_analyzer import BehaviorPatternAnalyzer
from ml_dl.sentiment_analyzer import SentimentAnalyzer

# 可选：TensorTrade RL（暂时禁用，避免导入错误）
TENSORTRADE_AVAILABLE = False


class IntegratedTradingBrain:
    """整合青鸟系统的交易员大脑系统"""
    
    def __init__(self, trader_id='de', use_rl: bool = False):
        self.trader_id = trader_id
        
        # 初始化青鸟系统
        if UNIFIED_SYSTEM_AVAILABLE:
            self.qingniao_system = UnifiedTradingSystem()
        else:
            self.qingniao_system = None
        
        # 初始化交易员大脑的智能组件
        self.market_perceiver = MarketEnvironmentPerceiver()
        self.rule_knowledge = RuleKnowledgeBase(trader_id)
        self.behavior_analyzer = BehaviorPatternAnalyzer(trader_id)
        self.sentiment_analyzer = SentimentAnalyzer(trader_id)
        
        # 可选：TensorTrade RL
        self.use_rl = use_rl and TENSORTRADE_AVAILABLE
        self.rl_agent = None
        if self.use_rl:
            try:
                from ml_dl.tensortrade_rl_agent import TensorTradeRLAgent
                self.rl_agent = TensorTradeRLAgent(trader_id=trader_id)
                if self.rl_agent.load_model(algorithm='PPO'):
                    print("✓ 已加载TensorTrade RL模型", file=sys.stderr)
            except Exception as e:
                print(f"⚠️  TensorTrade RL初始化失败: {e}", file=sys.stderr)
                self.use_rl = False
    
    def get_market_data_from_qingniao(self, timeframes: List[str] = ['5m', '15m', '1h']) -> Dict:
        """使用青鸟系统获取市场数据"""
        if not QINGNIAO_FUNCTIONS_AVAILABLE:
            return {}
        
        market_data = {}
        
        for tf in timeframes:
            try:
                # 使用青鸟系统的函数获取K线数据
                klines = get_btc_kline_gateio(tf, limit=200)
                
                if klines:
                    # 转换为DataFrame
                    df = pd.DataFrame(klines)
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df = df.set_index('datetime')
                    df = df[['open', 'high', 'low', 'close', 'volume']]
                    market_data[tf] = df
            except Exception as e:
                print(f"  获取{tf}数据失败: {e}", file=sys.stderr)
        
        return market_data
    
    def calculate_indicators_from_qingniao(self, klines: List[Dict]) -> Dict:
        """使用青鸟系统计算技术指标"""
        if not QINGNIAO_FUNCTIONS_AVAILABLE:
            return {}
        
        indicators = {}
        
        try:
            closes = [k['close'] for k in klines]
            
            # 计算EMA
            if len(closes) >= 144:
                indicators['ema_144'] = calculate_ema(closes, 144)
            if len(closes) >= 169:
                indicators['ema_169'] = calculate_ema(closes, 169)
            
            # 计算VWAP
            indicators['vwap'] = calculate_vwap(klines[-100:])
            
            # 计算RSI
            indicators['rsi'] = calculate_rsi(closes)
            
        except Exception as e:
            print(f"  计算技术指标失败: {e}", file=sys.stderr)
        
        return indicators
    
    def identify_patterns_from_qingniao(self, klines: List[Dict]) -> Dict:
        """使用青鸟系统识别技术形态"""
        if not QINGNIAO_FUNCTIONS_AVAILABLE:
            return {}
        
        patterns = {}
        
        try:
            # 识别FVG
            patterns['fvgs'] = identify_fvg(klines[-50:])
            
            # 识别支撑阻力
            current_price = get_btc_current_price() or klines[-1]['close']
            patterns['support_resistance'] = identify_support_resistance(klines, current_price)
            
            # M顶/W底和OTE分析暂时跳过（函数可能不存在）
            patterns['m_top'] = None
            patterns['w_bottom'] = None
            patterns['ote_analysis'] = None
            patterns['is_garbage_time'] = False
            
        except Exception as e:
            print(f"  识别技术形态失败: {e}", file=sys.stderr)
        
        return patterns
    
    def generate_signals_with_rules_engine(self, market_data: Dict, 
                                         patterns: Dict, 
                                         indicators: Dict) -> List[Dict]:
        """使用青鸟系统的规则引擎生成信号"""
        if not RULES_ENGINE_AVAILABLE:
            return []
        
        try:
            # 准备规则引擎输入
            current_price = get_btc_current_price()
            if not current_price:
                klines_15m = market_data.get('15m', [])
                if klines_15m:
                    current_price = klines_15m[-1]['close'] if isinstance(klines_15m, list) else klines_15m.iloc[-1]['close']
            
            # 构建market_data字典
            engine_market_data = {
                'current_price': current_price,
                'timeframe': '15m',
                'ema_144': indicators.get('ema_144'),
                'ema_169': indicators.get('ema_169'),
                'vwap': indicators.get('vwap'),
                'rsi': indicators.get('rsi')
            }
            
            # 转换为规则引擎格式
            engine_patterns = []
            if patterns.get('fvgs'):
                for fvg in patterns['fvgs']:
                    engine_patterns.append({
                        'type': 'fvg',
                        'data': fvg
                    })
            
            if patterns.get('m_top'):
                engine_patterns.append({
                    'type': 'm_top',
                    'data': patterns['m_top']
                })
            
            if patterns.get('w_bottom'):
                engine_patterns.append({
                    'type': 'w_bottom',
                    'data': patterns['w_bottom']
                })
            
            # 使用规则引擎分析
            signals = analyze_with_rules_engine(
                market_data=engine_market_data,
                patterns=engine_patterns,
                support_resistance=patterns.get('support_resistance', {}),
                ote_analysis=patterns.get('ote_analysis'),
                is_garbage_time=patterns.get('is_garbage_time', False)
            )
            
            # 转换为标准格式
            formatted_signals = []
            for signal in signals:
                formatted_signals.append({
                    'direction': signal.signal_type,
                    'entry_price': signal.entry,
                    'stop_loss': signal.stop_loss,
                    'take_profit_1': signal.take_profit_1,
                    'take_profit_2': signal.take_profit_2,
                    'strength': signal.strength,
                    'priority': signal.priority,
                    'reason': signal.reason,
                    'rule_name': signal.rule_name
                })
            
            return formatted_signals
            
        except Exception as e:
            print(f"  规则引擎生成信号失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return []
    
    def enhance_signals_with_brain(self, signals: List[Dict], 
                                  market_data: Dict,
                                  environment: Dict) -> List[Dict]:
        """使用交易员大脑系统增强信号"""
        enhanced_signals = []
        
        # 分析交易员情绪
        sentiment_results = self.sentiment_analyzer.analyze_viewpoints(limit=50)
        recent_sentiment = self._aggregate_sentiment(sentiment_results[-10:]) if len(sentiment_results) >= 10 else None
        
        for signal in signals:
            enhanced_signal = signal.copy()
            
            # 1. 市场环境匹配度
            market_state = environment.get('market_state', 'unknown')
            if market_state == 'consolidation' and '区间' in signal.get('reason', ''):
                enhanced_signal['environment_match'] = 0.9
            else:
                enhanced_signal['environment_match'] = 0.5
            
            # 2. 情绪一致性
            if recent_sentiment:
                sentiment = recent_sentiment.get('sentiment', 'neutral')
                signal_direction = signal.get('direction', '')
                
                if (sentiment == 'bullish' and signal_direction == 'long') or \
                   (sentiment == 'bearish' and signal_direction == 'short'):
                    enhanced_signal['sentiment_match'] = 0.8
                else:
                    enhanced_signal['sentiment_match'] = 0.5
            else:
                enhanced_signal['sentiment_match'] = 0.5
            
            # 3. 综合置信度
            base_confidence = signal.get('priority', 50) / 100.0
            enhanced_confidence = (
                base_confidence * 0.4 +
                enhanced_signal['environment_match'] * 0.3 +
                enhanced_signal['sentiment_match'] * 0.3
            )
            enhanced_signal['brain_confidence'] = enhanced_confidence
            
            # 4. RL优化（如果可用）
            if self.use_rl and self.rl_agent and self.rl_agent.model:
                # 这里可以添加RL优化逻辑
                enhanced_signal['rl_optimized'] = False  # 待实现
            
            enhanced_signals.append(enhanced_signal)
        
        # 按置信度排序
        enhanced_signals.sort(key=lambda x: x.get('brain_confidence', 0), reverse=True)
        
        return enhanced_signals
    
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
    
    def generate_enhanced_signals(self) -> Dict:
        """
        生成增强的交易信号（整合青鸟系统和交易员大脑）
        
        Returns:
            增强后的信号字典
        """
        print("=" * 80)
        print("整合青鸟系统 + 交易员大脑 - 生成增强信号")
        print("=" * 80)
        print()
        
        # 1. 使用青鸟系统获取市场数据
        print("【1/5】获取市场数据（使用青鸟系统）...")
        market_data = self.get_market_data_from_qingniao(['5m', '15m', '1h'])
        if not market_data:
            return {'signals': [], 'error': '无法获取市场数据'}
        print(f"✓ 获取了 {len(market_data)} 个时间框架的数据")
        print()
        
        # 2. 使用青鸟系统计算技术指标
        print("【2/5】计算技术指标（使用青鸟系统）...")
        klines_15m = market_data.get('15m', pd.DataFrame())
        if isinstance(klines_15m, pd.DataFrame):
            klines_list = klines_15m.reset_index().to_dict('records')
        else:
            klines_list = klines_15m
        
        indicators = self.calculate_indicators_from_qingniao(klines_list)
        print(f"✓ 计算了 {len(indicators)} 个技术指标")
        print()
        
        # 3. 使用青鸟系统识别技术形态
        print("【3/5】识别技术形态（使用青鸟系统）...")
        patterns = self.identify_patterns_from_qingniao(klines_list)
        print(f"✓ 识别了 {len(patterns)} 种技术形态")
        print()
        
        # 4. 使用青鸟系统规则引擎生成信号
        print("【4/5】生成交易信号（使用青鸟系统规则引擎）...")
        signals = self.generate_signals_with_rules_engine(market_data, patterns, indicators)
        print(f"✓ 生成了 {len(signals)} 个基础信号")
        print()
        
        # 5. 使用交易员大脑系统增强信号
        print("【5/5】智能增强信号（使用交易员大脑系统）...")
        environment = self.market_perceiver.perceive_environment(market_data)
        enhanced_signals = self.enhance_signals_with_brain(signals, market_data, environment)
        print(f"✓ 增强了 {len(enhanced_signals)} 个信号")
        print()
        
        return {
            'signals': enhanced_signals,
            'environment': environment,
            'indicators': indicators,
            'patterns': patterns,
            'total_signals': len(enhanced_signals)
        }
    
    def close(self):
        """关闭所有连接"""
        if hasattr(self, 'rule_knowledge'):
            self.rule_knowledge.db.close()
        if hasattr(self, 'behavior_analyzer'):
            self.behavior_analyzer.db.close()
        if hasattr(self, 'sentiment_analyzer'):
            self.sentiment_analyzer.db.close()
        if self.rl_agent:
            self.rl_agent.close()


def main():
    """主函数"""
    print("=" * 80)
    print("整合青鸟系统 + 交易员大脑系统")
    print("=" * 80)
    print()
    
    # 初始化整合系统
    brain = IntegratedTradingBrain(trader_id='de', use_rl=False)
    
    # 生成增强信号
    result = brain.generate_enhanced_signals()
    
    # 显示结果
    print("=" * 80)
    print("增强信号结果")
    print("=" * 80)
    
    if result.get('signals'):
        signals = result['signals']
        print(f"\n共生成 {len(signals)} 个增强信号\n")
        
        for i, signal in enumerate(signals[:5], 1):  # 只显示前5个
            print(f"信号 {i}:")
            print(f"  方向: {signal.get('direction')}")
            print(f"  入场: ${signal.get('entry_price', 0):,.2f}")
            print(f"  止损: ${signal.get('stop_loss', 0):,.2f}")
            print(f"  止盈1: ${signal.get('take_profit_1', 0):,.2f}")
            print(f"  止盈2: ${signal.get('take_profit_2', 0):,.2f}")
            print(f"  规则: {signal.get('rule_name', 'N/A')}")
            print(f"  大脑置信度: {signal.get('brain_confidence', 0):.2%}")
            print(f"  原因: {signal.get('reason', 'N/A')[:100]}")
            print()
    else:
        print("未生成信号")
        if result.get('error'):
            print(f"错误: {result['error']}")
    
    # 显示市场环境
    if result.get('environment'):
        env = result['environment']
        print("市场环境:")
        print(f"  市场状态: {env.get('market_state')}")
        print(f"  波动率: {env.get('volatility_level')}")
        print(f"  趋势强度: {env.get('trend_strength'):.2f}")
        print(f"  机会分数: {env.get('opportunity_score'):.2f}")
    
    print()
    print("=" * 80)
    
    brain.close()

if __name__ == '__main__':
    main()

