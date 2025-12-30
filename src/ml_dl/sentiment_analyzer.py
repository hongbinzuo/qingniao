#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易员情绪分析器
从对话和观点中提取市场情绪
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import re

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager

# 尝试导入NLP库
try:
    import jieba
    import jieba.analyse
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    print("警告: jieba未安装，某些功能可能受限", file=sys.stderr)

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


class SentimentAnalyzer:
    """交易员情绪分析器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        
        # 情绪关键词
        self.bullish_keywords = [
            '看涨', '上涨', '突破', '做多', '多单', '买入', '涨', '拉升',
            '强势', '机会', '可以', '应该', '建议', '很好', '不错',
            '目标', '止盈', '盈利', '赚', '拿下', '吃了'
        ]
        
        self.bearish_keywords = [
            '看跌', '下跌', '做空', '空单', '卖出', '跌', '回调', '下探',
            '弱势', '风险', '不要', '避免', '止损', '亏损', '亏',
            '稳住', '等待', '观望', '谨慎'
        ]
        
        self.neutral_keywords = [
            '震荡', '横盘', '整理', '区间', '支撑', '阻力', '观察',
            '可能', '大概', '也许', '或者'
        ]
        
        # 尝试加载预训练模型
        self.model = None
        self.tokenizer = None
        if TRANSFORMERS_AVAILABLE:
            try:
                # 使用中文情感分析模型
                model_name = "uer/roberta-base-finetuned-chinanews-chinese"
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.model.eval()
                print("✓ 已加载预训练情感分析模型")
            except:
                print("⚠️  无法加载预训练模型，将使用规则方法")
    
    def analyze_sentiment_rule_based(self, text: str) -> Dict:
        """基于规则的情绪分析"""
        text_lower = text.lower()
        
        bullish_score = sum(1 for kw in self.bullish_keywords if kw in text)
        bearish_score = sum(1 for kw in self.bearish_keywords if kw in text)
        neutral_score = sum(1 for kw in self.neutral_keywords if kw in text)
        
        # 特殊模式
        if re.search(r'(\d+)\s*点', text):
            bullish_score += 1
        
        if '止损' in text and '保本' in text:
            neutral_score += 1
        
        total_score = bullish_score + bearish_score + neutral_score
        
        if total_score == 0:
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'bullish_score': 0,
                'bearish_score': 0,
                'neutral_score': 0
            }
        
        # 计算情绪分数（-1到1，-1为看跌，1为看涨）
        sentiment_score = (bullish_score - bearish_score) / total_score
        
        if sentiment_score > 0.3:
            sentiment = 'bullish'
        elif sentiment_score < -0.3:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'
        
        confidence = abs(sentiment_score)
        
        return {
            'sentiment': sentiment,
            'score': sentiment_score,
            'confidence': confidence,
            'bullish_score': bullish_score,
            'bearish_score': bearish_score,
            'neutral_score': neutral_score
        }
    
    def analyze_sentiment_ml(self, text: str) -> Dict:
        """使用机器学习模型分析情绪"""
        if self.model is None or self.tokenizer is None:
            return self.analyze_sentiment_rule_based(text)
        
        try:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            
            # 假设模型输出：0=负面，1=中性，2=正面
            probs = predictions[0].tolist()
            
            if len(probs) >= 3:
                negative_prob = probs[0]
                neutral_prob = probs[1]
                positive_prob = probs[2]
                
                sentiment_score = positive_prob - negative_prob
                
                if positive_prob > negative_prob and positive_prob > neutral_prob:
                    sentiment = 'bullish'
                elif negative_prob > positive_prob and negative_prob > neutral_prob:
                    sentiment = 'bearish'
                else:
                    sentiment = 'neutral'
                
                confidence = max(probs)
                
                return {
                    'sentiment': sentiment,
                    'score': sentiment_score,
                    'confidence': confidence,
                    'positive_prob': positive_prob,
                    'negative_prob': negative_prob,
                    'neutral_prob': neutral_prob
                }
        except Exception as e:
            print(f"  ML分析失败: {e}", file=sys.stderr)
            return self.analyze_sentiment_rule_based(text)
    
    def analyze_viewpoints(self, limit: int = None) -> List[Dict]:
        """分析所有观点的情绪"""
        viewpoints = self.db.get_viewpoints(limit=limit)
        
        results = []
        for vp in viewpoints:
            content = vp.get('content', '')
            if not content:
                continue
            
            # 移除价格标签等
            content_clean = re.sub(r'\[BTC价格.*?\]', '', content)
            content_clean = re.sub(r'\[.*?\]', '', content_clean).strip()
            
            if not content_clean:
                continue
            
            sentiment_result = self.analyze_sentiment_ml(content_clean)
            
            results.append({
                'viewpoint_id': vp['id'],
                'timestamp': vp['timestamp'],
                'content': content_clean[:100],  # 只保留前100字符
                'btc_price': vp.get('btc_price'),
                'category': vp.get('category'),
                'sentiment': sentiment_result['sentiment'],
                'sentiment_score': sentiment_result['score'],
                'confidence': sentiment_result['confidence']
            })
        
        return results
    
    def get_sentiment_timeline(self, start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> List[Dict]:
        """获取情绪时间线"""
        results = self.analyze_viewpoints()
        
        # 按时间排序
        results.sort(key=lambda x: x['timestamp'])
        
        # 过滤时间范围
        if start_date:
            results = [r for r in results if r['timestamp'] >= start_date]
        if end_date:
            results = [r for r in results if r['timestamp'] <= end_date]
        
        return results
    
    def analyze_sentiment_vs_price(self) -> Dict:
        """分析情绪与价格的关系"""
        results = self.analyze_viewpoints()
        
        # 只保留有价格的数据
        valid_results = [r for r in results if r.get('btc_price')]
        
        if len(valid_results) < 10:
            return {
                'message': '数据不足，需要至少10条带价格的记录',
                'total': len(valid_results)
            }
        
        # 计算情绪与价格变化的关系
        bullish_prices = [r['btc_price'] for r in valid_results if r['sentiment'] == 'bullish']
        bearish_prices = [r['btc_price'] for r in valid_results if r['sentiment'] == 'bearish']
        neutral_prices = [r['btc_price'] for r in valid_results if r['sentiment'] == 'neutral']
        
        # 计算后续价格变化（如果有足够数据）
        price_changes = []
        for i in range(len(valid_results) - 1):
            current = valid_results[i]
            next_price = valid_results[i + 1].get('btc_price')
            if next_price and current.get('btc_price'):
                change_pct = (next_price - current['btc_price']) / current['btc_price'] * 100
                price_changes.append({
                    'sentiment': current['sentiment'],
                    'sentiment_score': current['sentiment_score'],
                    'price_change_pct': change_pct
                })
        
        return {
            'total_records': len(valid_results),
            'bullish_count': len(bullish_prices),
            'bearish_count': len(bearish_prices),
            'neutral_count': len(neutral_prices),
            'avg_bullish_price': sum(bullish_prices) / len(bullish_prices) if bullish_prices else None,
            'avg_bearish_price': sum(bearish_prices) / len(bearish_prices) if bearish_prices else None,
            'avg_neutral_price': sum(neutral_prices) / len(neutral_prices) if neutral_prices else None,
            'price_changes': price_changes[:20]  # 只返回前20条
        }


def main():
    """主函数"""
    print("=" * 80)
    print("交易员情绪分析")
    print("=" * 80)
    print()
    
    analyzer = SentimentAnalyzer(trader_id='de')
    
    # 分析所有观点
    print("分析观点情绪...")
    results = analyzer.analyze_viewpoints(limit=100)
    
    print(f"✓ 分析了 {len(results)} 条观点")
    print()
    
    # 统计情绪分布
    sentiment_counts = {}
    for r in results:
        sentiment = r['sentiment']
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
    
    print("情绪分布:")
    for sentiment, count in sentiment_counts.items():
        pct = count / len(results) * 100
        print(f"  {sentiment}: {count} 条 ({pct:.1f}%)")
    
    print()
    
    # 分析情绪与价格的关系
    print("分析情绪与价格的关系...")
    price_analysis = analyzer.analyze_sentiment_vs_price()
    
    if 'message' in price_analysis:
        print(f"  {price_analysis['message']}")
    else:
        print(f"  总记录数: {price_analysis['total_records']}")
        print(f"  看涨记录: {price_analysis['bullish_count']}")
        print(f"  看跌记录: {price_analysis['bearish_count']}")
        print(f"  中性记录: {price_analysis['neutral_count']}")
        
        if price_analysis['avg_bullish_price']:
            print(f"  平均看涨时价格: ${price_analysis['avg_bullish_price']:,.2f}")
        if price_analysis['avg_bearish_price']:
            print(f"  平均看跌时价格: ${price_analysis['avg_bearish_price']:,.2f}")
    
    print()
    print("=" * 80)
    
    analyzer.db.close()

if __name__ == '__main__':
    main()




