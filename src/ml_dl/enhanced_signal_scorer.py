#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强信号评分系统
集成ML、DL和TensorTrade RL来增强信号评分
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 尝试导入ML/DL模块
try:
    from ml_dl.abu_price_action_learner import PriceActionLearner
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    PriceActionLearner = None

try:
    from abu.dl_features import DLFeatureExtractor
    DL_AVAILABLE = True
except ImportError:
    DL_AVAILABLE = False
    DLFeatureExtractor = None

try:
    from ml_dl.tensortrade_rl_agent import TensorTradeRLAgent
    TENSORTRADE_AVAILABLE = True
except ImportError:
    TENSORTRADE_AVAILABLE = False
    TensorTradeRLAgent = None

class EnhancedSignalScorer:
    """增强信号评分器"""
    
    def __init__(self, use_ml: bool = True, use_dl: bool = False, use_rl: bool = False):
        """
        初始化评分器
        
        Args:
            use_ml: 是否使用ML模型（XGBoost价格行为预测）
            use_dl: 是否使用DL特征（CNN/LSTM）
            use_rl: 是否使用TensorTrade RL（强化学习）
        """
        self.use_ml = use_ml and ML_AVAILABLE
        self.use_dl = use_dl and DL_AVAILABLE
        self.use_rl = use_rl and TENSORTRADE_AVAILABLE
        
        # 初始化组件
        self.ml_learner = PriceActionLearner() if self.use_ml else None
        self.dl_extractor = DLFeatureExtractor() if self.use_dl else None
        self.rl_agent = TensorTradeRLAgent() if self.use_rl else None
        
        # 权重配置
        self.weights = {
            'base_score': 0.4,      # 基础评分（相似度）
            'ml_score': 0.3 if self.use_ml else 0.0,  # ML预测
            'dl_score': 0.2 if self.use_dl else 0.0,  # DL特征
            'rl_score': 0.1 if self.use_rl else 0.0   # RL信号
        }
        
        # 归一化权重
        total = sum(self.weights.values())
        if total > 0:
            for k in self.weights:
                self.weights[k] /= total
    
    def score_signal(self, signal: Dict, klines: List[Dict], 
                    pattern_match: Dict) -> float:
        """
        综合评分信号
        
        Args:
            signal: 交易信号字典
            klines: K线数据
            pattern_match: 模式匹配结果
            
        Returns:
            综合评分（0-100）
        """
        scores = {}
        
        # 1. 基础评分（相似度）
        similarity = pattern_match.get('similarity', 0.0)
        scores['base_score'] = similarity * 100
        
        # 2. ML评分（价格行为预测）
        if self.use_ml and self.ml_learner:
            try:
                # 确保模型已加载
                if not self.ml_learner.model:
                    if not self.ml_learner.load_model():
                        # 模型未训练，跳过ML评分
                        scores['ml_score'] = 50.0
                    else:
                        # 模型加载成功，继续预测
                        pass
                
                # 提取特征（格式需要匹配PriceActionLearner的输入）
                # PriceActionLearner.predict需要gemini_annotation格式
                gemini_annotation = pattern_match.get('gemini_annotation', {})
                if gemini_annotation and self.ml_learner.model:
                    try:
                        # 预测价格行为
                        prediction = self.ml_learner.predict(gemini_annotation)
                        # 转换为评分
                        ml_score = self._ml_prediction_to_score(prediction)
                        scores['ml_score'] = ml_score
                    except Exception:
                        scores['ml_score'] = 50.0
                else:
                    scores['ml_score'] = 50.0
            except Exception as e:
                scores['ml_score'] = 50.0  # 默认中等评分
        
        # 3. DL评分（深度学习特征）
        if self.use_dl and self.dl_extractor:
            try:
                # DL特征提取需要K线数据字典格式
                klines_dict = {signal.get('timeframe', '15m'): klines}
                dl_features = self.dl_extractor.extract_features(klines_dict)
                # 使用DL特征计算评分
                dl_score = self._dl_features_to_score(dl_features)
                scores['dl_score'] = dl_score
            except Exception as e:
                scores['dl_score'] = 50.0
        
        # 4. RL评分（TensorTrade强化学习）
        if self.use_rl and self.rl_agent:
            try:
                rl_score = self._rl_signal_to_score(signal, klines)
                scores['rl_score'] = rl_score
            except Exception as e:
                scores['rl_score'] = 50.0
        
        # 综合评分
        final_score = sum(scores.get(k, 0) * self.weights.get(k, 0) 
                         for k in self.weights)
        
        return min(100.0, max(0.0, final_score))
    
    def _extract_ml_features(self, signal: Dict, klines: List[Dict], 
                           pattern_match: Dict) -> Dict:
        """提取ML特征（兼容PriceActionLearner的输入格式）"""
        if not klines:
            return {}
        
        # 构建实时特征字典（格式与extract_realtime_features一致）
        recent = klines[-20:] if len(klines) >= 20 else klines
        closes = [k['close'] for k in recent]
        highs = [k['high'] for k in recent]
        lows = [k['low'] for k in recent]
        volumes = [k['volume'] for k in recent]
        
        # 计算技术指标
        price_change = (closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0.0
        volatility = np.std(closes) if len(closes) > 1 else 0.0
        
        # 构建特征字典（格式与PriceActionLearner期望的一致）
        features = {
            'price_action_behavior': {
                'kline_features': [],  # 简化，实际可以从pattern_match提取
                'trend': 'bullish' if price_change > 0 else 'bearish',
                'structure': 'higher_highs' if price_change > 0 else 'lower_lows',
                'trend_strength': abs(price_change)
            },
            'market_conditions': {
                'volatility': 'high' if volatility > 0.02 else 'low',
                'volatility_value': volatility,
                'trend_direction': 'bullish' if price_change > 0 else 'bearish',
                'volume_ratio': np.mean(volumes[-5:]) / np.mean(volumes) if len(volumes) >= 5 and np.mean(volumes) > 0 else 1.0
            },
            'patterns': [],
            'trading_signals': []
        }
        
        return features
    
    def _ml_prediction_to_score(self, prediction: any) -> float:
        """将ML预测转换为评分"""
        # 处理不同格式的预测结果
        if isinstance(prediction, dict):
            price_action = prediction.get('price_action', '')
            confidence = prediction.get('confidence', 0.5)
            prediction_str = price_action
        elif isinstance(prediction, str):
            prediction_str = prediction
            confidence = 0.7  # 默认置信度
        else:
            return 50.0
        
        prediction_lower = prediction_str.lower() if prediction_str else 'indecision'
        
        # 基础评分
        base_score = 50.0
        if 'reversal' in prediction_lower:
            base_score = 80.0  # 反转模式，高分
        elif 'continuation' in prediction_lower:
            base_score = 75.0  # 延续模式，高分
        elif 'consolidation' in prediction_lower:
            base_score = 60.0  # 整理模式，中等
        
        # 根据置信度调整
        if isinstance(prediction, dict) and 'confidence' in prediction:
            confidence = prediction['confidence']
            # 置信度越高，评分越高
            adjusted_score = base_score + (confidence - 0.5) * 20
            return min(100.0, max(0.0, adjusted_score))
        
        return base_score
    
    def _dl_features_to_score(self, dl_features: any) -> float:
        """将DL特征转换为评分"""
        if not dl_features:
            return 50.0
        
        # 处理不同格式的DL特征
        if isinstance(dl_features, dict):
            # 如果是字典，提取特征值
            feature_values = [v for v in dl_features.values() if isinstance(v, (int, float))]
            if feature_values:
                feature_norm = np.linalg.norm(feature_values)
                score = min(100.0, feature_norm * 10)  # 归一化到0-100
                return score
        elif isinstance(dl_features, (list, np.ndarray)):
            # 如果是数组，直接计算范数
            feature_norm = np.linalg.norm(dl_features)
            score = min(100.0, feature_norm * 10)
            return score
        
        return 50.0  # 默认中等评分
    
    def _rl_signal_to_score(self, signal: Dict, klines: List[Dict]) -> float:
        """使用RL模型评分信号"""
        if not self.rl_agent or not self.rl_agent.model:
            return 50.0
        
        try:
            # 构建观察向量（简化版）
            if not klines:
                return 50.0
            
            # 提取价格特征
            recent = klines[-20:] if len(klines) >= 20 else klines
            prices = [k['close'] for k in recent]
            
            # 构建观察（需要匹配RL模型的输入格式）
            # 这里简化处理，实际需要根据RL模型的具体输入格式
            observation = np.array(prices[-20:]).reshape(1, -1)
            
            # 预测动作（0=持有, 1=买入, 2=卖出）
            action = self.rl_agent.predict_action(observation)
            
            # 根据信号方向和RL动作的一致性评分
            signal_direction = signal.get('direction', '').lower()
            if signal_direction == 'long' and action == 1:
                return 90.0  # RL也建议买入，高分
            elif signal_direction == 'short' and action == 2:
                return 90.0  # RL也建议卖出，高分
            elif action == 0:
                return 40.0  # RL建议持有，低分
            else:
                return 30.0  # RL建议相反，很低分
        
        except Exception as e:
            return 50.0  # 默认中等评分

