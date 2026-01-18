#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU ML增强模块

功能：
- 集成价格行为学习模型到信号检测和评分
- 使用ML模型预测价格行为，提高信号质量
"""
from __future__ import annotations
from typing import List, Dict, Optional
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 尝试导入价格行为学习模型
try:
    from ml_dl.abu_price_action_learner import PriceActionLearner
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    PriceActionLearner = None

# 尝试导入数据库管理器
try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    TraderDBManager = None


def extract_kline_features_for_ml(klines: List[Dict]) -> Dict:
    """
    从K线数据提取特征，用于ML模型预测
    
    这个函数从实时K线数据提取特征，模拟Gemini分析结果的结构
    """
    if not klines or len(klines) < 10:
        return {}
    
    # 提取最近K线的特征
    recent = klines[-10:]
    closes = [k['close'] for k in recent]
    highs = [k['high'] for k in recent]
    lows = [k['low'] for k in recent]
    opens = [k['open'] for k in recent]
    
    # 计算趋势特征
    price_trend = 'bullish' if closes[-1] > closes[0] else 'bearish'
    trend_strength = abs(closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
    
    # 计算波动率特征
    price_ranges = [(h - l) for h, l in zip(highs, lows)]
    avg_range = sum(price_ranges) / len(price_ranges) if price_ranges else 0
    volatility = avg_range / closes[-1] if closes[-1] > 0 else 0
    
    # K线行为特征（简单检测）
    kline_features = []
    if len(klines) >= 2:
        last = klines[-1]
        prev = klines[-2]
        
        # 检测吞没形态
        if last['close'] > last['open'] and prev['close'] < prev['open']:
            if last['open'] < prev['close'] and last['close'] > prev['open']:
                kline_features.append('bullish_engulfing')
        elif last['close'] < last['open'] and prev['close'] > prev['open']:
            if last['open'] > prev['close'] and last['close'] < prev['open']:
                kline_features.append('bearish_engulfing')
        
        # 检测Pin Bar
        body = abs(last['close'] - last['open'])
        total_range = last['high'] - last['low']
        if total_range > 0:
            body_ratio = body / total_range
            upper_wick = last['high'] - max(last['open'], last['close'])
            lower_wick = min(last['open'], last['close']) - last['low']
            
            if body_ratio < 0.3:
                if upper_wick > lower_wick * 2:
                    kline_features.append('bearish_pin_bar')
                elif lower_wick > upper_wick * 2:
                    kline_features.append('bullish_pin_bar')
        
        # 检测Inside Bar
        if last['high'] < prev['high'] and last['low'] > prev['low']:
            kline_features.append('inside_bar')
    
    # 构建类似Gemini分析结果的结构
    gemini_like_annotation = {
        'patterns': [],  # 简化：不匹配具体模式
        'pattern_combination': '',
        'price_action_behavior': {
            'kline_features': kline_features,
            'trend': price_trend,
            'structure': 'unknown'
        },
        'trading_signals': [],
        'market_conditions': {
            'trend_strength': 'strong' if trend_strength > 0.02 else 'weak',
            'volatility': 'high' if volatility > 0.01 else 'low',
            'trend_direction': price_trend
        }
    }
    
    return gemini_like_annotation


def enhance_candidate_with_ml(candidate: Dict, klines: List[Dict]) -> Dict:
    """
    使用ML模型增强候选信号
    
    Args:
        candidate: 候选信号字典
        klines: K线数据列表
    
    Returns:
        增强后的候选信号（添加ml_prediction字段）
    """
    if not ML_AVAILABLE:
        candidate['_ml_available'] = False
        return candidate
    
    try:
        learner = PriceActionLearner()
        
        # 从K线数据提取特征
        gemini_like_annotation = extract_kline_features_for_ml(klines)
        
        # 使用ML模型预测
        prediction = learner.predict(gemini_like_annotation)
        
        if prediction.get('success'):
            candidate['_ml_prediction'] = prediction
            candidate['_ml_available'] = True
            
            # 提取预测的价格行为类别和概率
            price_action = prediction.get('price_action', 'indecision')
            probabilities = prediction.get('probabilities', {})
            
            # 计算ML置信度（使用最高概率）
            ml_confidence = max(probabilities.values()) if probabilities else 0.0
            
            candidate['_ml_price_action'] = price_action
            candidate['_ml_confidence'] = ml_confidence
            candidate['_ml_probabilities'] = probabilities
            
            # 检查价格行为是否与信号方向一致
            signal_type = candidate.get('type', '')
            is_consistent = False
            
            if price_action == 'reversal':
                # 反转模式：如果信号是long，可能是反转下跌，需要谨慎
                # 这里简化处理，反转模式一般置信度较低
                is_consistent = ml_confidence > 0.6
            elif price_action == 'continuation':
                # 延续模式：与趋势一致，置信度较高
                is_consistent = ml_confidence > 0.5
            elif price_action == 'indecision':
                # 不确定：置信度较低
                is_consistent = False
            elif price_action == 'consolidation':
                # 整理：需要谨慎
                is_consistent = ml_confidence > 0.6
            
            candidate['_ml_consistent'] = is_consistent
        else:
            candidate['_ml_available'] = False
            candidate['_ml_error'] = prediction.get('error', 'Unknown error')
    
    except Exception as e:
        candidate['_ml_available'] = False
        candidate['_ml_error'] = str(e)
    
    return candidate


def calculate_ml_score_boost(candidate: Dict) -> float:
    """
    计算ML预测对评分的提升
    
    Returns:
        ML评分提升（0.0 - 1.0）
    """
    if not candidate.get('_ml_available'):
        return 0.0
    
    ml_confidence = candidate.get('_ml_confidence', 0.0)
    is_consistent = candidate.get('_ml_consistent', False)
    price_action = candidate.get('_ml_price_action', 'indecision')
    
    if not is_consistent:
        # 如果不一致，可能降低评分
        return -0.2 * ml_confidence
    
    # 根据价格行为类型和置信度计算提升
    base_boost = ml_confidence
    
    if price_action == 'continuation':
        # 延续模式：高置信度时给予较大提升
        boost = base_boost * 0.8
    elif price_action == 'reversal':
        # 反转模式：谨慎，中等提升
        boost = base_boost * 0.5
    elif price_action == 'consolidation':
        # 整理：中等提升
        boost = base_boost * 0.6
    else:  # indecision
        # 不确定：不提升
        boost = 0.0
    
    return min(1.0, max(-0.5, boost))



