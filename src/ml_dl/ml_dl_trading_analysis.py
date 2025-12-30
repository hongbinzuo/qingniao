#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机器学习/深度学习交易数据分析主入口
整合所有ML/DL功能
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from behavior_pattern_analyzer import BehaviorPatternAnalyzer
from sentiment_analyzer import SentimentAnalyzer


class MLDLTradingAnalyzer:
    """ML/DL交易数据分析器（主入口）"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.behavior_analyzer = BehaviorPatternAnalyzer(trader_id)
        self.sentiment_analyzer = SentimentAnalyzer(trader_id)
    
    def run_full_analysis(self) -> Dict:
        """运行完整分析"""
        print("=" * 80)
        print("机器学习/深度学习交易数据分析")
        print("=" * 80)
        print()
        
        results = {}
        
        # 1. 行为模式分析
        print("【1/3】行为模式分析...")
        print("-" * 80)
        behavior_report = self.behavior_analyzer.generate_behavior_report()
        results['behavior'] = behavior_report
        print()
        
        # 2. 情绪分析
        print("【2/3】情绪分析...")
        print("-" * 80)
        sentiment_results = self.sentiment_analyzer.analyze_viewpoints(limit=500)
        sentiment_counts = {}
        for r in sentiment_results:
            sentiment = r['sentiment']
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        print(f"分析了 {len(sentiment_results)} 条观点")
        print("情绪分布:")
        for sentiment, count in sentiment_counts.items():
            pct = count / len(sentiment_results) * 100 if sentiment_results else 0
            print(f"  {sentiment}: {count} 条 ({pct:.1f}%)")
        
        # 情绪与价格关系
        price_analysis = self.sentiment_analyzer.analyze_sentiment_vs_price()
        if 'message' not in price_analysis:
            print()
            print("情绪与价格关系:")
            print(f"  看涨记录: {price_analysis['bullish_count']} 条")
            print(f"  看跌记录: {price_analysis['bearish_count']} 条")
            if price_analysis['avg_bullish_price']:
                print(f"  平均看涨时价格: ${price_analysis['avg_bullish_price']:,.2f}")
            if price_analysis['avg_bearish_price']:
                print(f"  平均看跌时价格: ${price_analysis['avg_bearish_price']:,.2f}")
        
        results['sentiment'] = {
            'distribution': sentiment_counts,
            'price_analysis': price_analysis
        }
        print()
        
        # 3. 价格预测（如果模型可用）
        print("【3/3】价格预测...")
        print("-" * 80)
        try:
            from price_predictor_lstm import BTCPricePredictor
            
            predictor = BTCPricePredictor()
            if predictor.load_model():
                print("✓ 已加载LSTM价格预测模型")
                
                # 加载最新数据
                df = predictor.load_price_data()
                df = predictor.prepare_features(df)
                
                # 预测
                prediction = predictor.predict(df)
                current_price = df['close'].iloc[-1]
                
                print(f"当前价格: ${current_price:,.2f}")
                print(f"预测未来1小时平均价格: ${prediction:,.2f}")
                change_pct = ((prediction - current_price) / current_price * 100)
                print(f"预测变化: {change_pct:+.2f}%")
                
                results['price_prediction'] = {
                    'current_price': current_price,
                    'predicted_price': prediction,
                    'change_pct': change_pct
                }
            else:
                print("⚠️  LSTM模型未训练，跳过价格预测")
                print("  提示: 运行 python src/ml_dl/price_predictor_lstm.py 训练模型")
                results['price_prediction'] = {'status': 'model_not_trained'}
        except ImportError:
            print("⚠️  PyTorch未安装，跳过价格预测")
            print("  提示: pip install torch")
            results['price_prediction'] = {'status': 'pytorch_not_available'}
        except Exception as e:
            print(f"⚠️  价格预测失败: {e}")
            results['price_prediction'] = {'status': 'error', 'error': str(e)}
        
        print()
        print("=" * 80)
        print("分析完成！")
        print("=" * 80)
        
        return results
    
    def generate_insights(self, results: Dict) -> List[str]:
        """生成洞察建议"""
        insights = []
        
        # 行为模式洞察
        if 'behavior' in results:
            behavior = results['behavior']
            
            # 时间偏好
            if behavior.get('time_pattern', {}).get('most_active_hour') is not None:
                hour = behavior['time_pattern']['most_active_hour']
                insights.append(f"交易活跃时段: {hour}:00，建议在此时间段重点关注市场")
            
            # 策略偏好
            strategy_pattern = behavior.get('strategy_pattern', {})
            top_strategy = max(strategy_pattern.get('strategies', {}).items(), 
                             key=lambda x: x[1], default=(None, 0))
            if top_strategy[0]:
                insights.append(f"最常用策略: {top_strategy[0]} ({top_strategy[1]}次)，可重点优化此策略")
            
            # 方向偏好
            directions = strategy_pattern.get('directions', {})
            if directions.get('long', 0) > directions.get('short', 0):
                insights.append("交易方向偏好: 做多 > 做空，可能更擅长上涨趋势")
            elif directions.get('short', 0) > directions.get('long', 0):
                insights.append("交易方向偏好: 做空 > 做多，可能更擅长下跌趋势")
        
        # 情绪洞察
        if 'sentiment' in results:
            sentiment = results['sentiment']
            distribution = sentiment.get('distribution', {})
            
            bullish_count = distribution.get('bullish', 0)
            bearish_count = distribution.get('bearish', 0)
            
            if bullish_count > bearish_count * 1.5:
                insights.append("整体情绪: 偏向看涨，对市场较为乐观")
            elif bearish_count > bullish_count * 1.5:
                insights.append("整体情绪: 偏向看跌，对市场较为谨慎")
            else:
                insights.append("整体情绪: 相对平衡，根据市场情况灵活调整")
        
        # 价格预测洞察
        if 'price_prediction' in results:
            pred = results['price_prediction']
            if 'change_pct' in pred:
                change = pred['change_pct']
                if change > 0.5:
                    insights.append(f"价格预测: 短期看涨 ({change:+.2f}%)，可关注做多机会")
                elif change < -0.5:
                    insights.append(f"价格预测: 短期看跌 ({change:+.2f}%)，可关注做空机会")
                else:
                    insights.append(f"价格预测: 短期震荡 ({change:+.2f}%)，建议观望")
        
        return insights


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ML/DL交易数据分析')
    parser.add_argument('--trader', type=str, default='de', help='交易员ID')
    parser.add_argument('--train-price', action='store_true', help='训练价格预测模型')
    
    args = parser.parse_args()
    
    analyzer = MLDLTradingAnalyzer(trader_id=args.trader)
    
    if args.train_price:
        # 训练价格预测模型
        print("训练价格预测模型...")
        try:
            from price_predictor_lstm import BTCPricePredictor
            predictor = BTCPricePredictor()
            df = predictor.load_price_data()
            df = predictor.prepare_features(df)
            result = predictor.train(df, epochs=50)
            print(f"训练完成！最佳验证损失: {result['best_val_loss']:.6f}")
        except Exception as e:
            print(f"训练失败: {e}")
    else:
        # 运行完整分析
        results = analyzer.run_full_analysis()
        
        # 生成洞察
        print()
        print("=" * 80)
        print("💡 洞察建议")
        print("=" * 80)
        insights = analyzer.generate_insights(results)
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight}")
        
        if not insights:
            print("暂无洞察建议")
        
        print()
    
    # 关闭数据库连接
    analyzer.behavior_analyzer.db.close()
    analyzer.sentiment_analyzer.db.close()

if __name__ == '__main__':
    main()

