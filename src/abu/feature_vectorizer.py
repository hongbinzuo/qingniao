#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特征向量化器 - ABU系统v3.0

将结构化特征转换为数值向量，用于：
1. 向量索引（FAISS/Annoy）
2. 相似度计算
3. ML/DL模型输入
"""

from __future__ import annotations
import sys
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("[WARN] NumPy不可用，向量化功能将受限", file=sys.stderr)


class FeatureVectorizer:
    """
    特征向量化器
    
    功能：
    1. 将结构化特征转换为数值向量
    2. 支持多种特征类型（数值、类别、文本）
    3. 特征归一化和标准化
    """
    
    def __init__(self):
        """初始化向量化器"""
        if not NUMPY_AVAILABLE:
            raise RuntimeError("需要安装NumPy: pip install numpy")
        
        # 特征词汇表（用于one-hot编码）
        self.vocabularies = {
            'pattern_types': set(),
            'directions': {'long', 'short', 'neutral'},
            'trends': {'bullish', 'bearish', 'neutral'},
            'kline_features': set(),
            'market_conditions': set()
        }
        
        # 特征维度（动态计算）
        self.feature_dim = None
        
        # 是否已构建词汇表
        self.vocab_built = False
    
    def build_vocabulary(self, patterns: List[Dict]):
        """
        从模式集合构建词汇表
        
        Args:
            patterns: 模式列表，每个包含structured_features
        """
        print("构建特征词汇表...")
        
        for pattern in patterns:
            features = pattern.get('structured_features', {})
            
            # 收集模式类型
            pattern_type = features.get('pattern_type', '')
            if pattern_type:
                self.vocabularies['pattern_types'].add(pattern_type)
            
            # 收集K线特征
            kline_features = features.get('kline_features', [])
            if isinstance(kline_features, list):
                for feat in kline_features:
                    if isinstance(feat, str):
                        self.vocabularies['kline_features'].add(feat)
                    elif isinstance(feat, dict):
                        feat_name = feat.get('feature', '') or feat.get('name', '')
                        if feat_name:
                            self.vocabularies['kline_features'].add(feat_name)
            
            # 收集市场条件
            market_conditions = features.get('market_conditions', {})
            if isinstance(market_conditions, dict):
                for key, value in market_conditions.items():
                    if isinstance(value, str):
                        self.vocabularies['market_conditions'].add(f"{key}_{value}")
        
        # 转换为有序列表（保证一致性）
        for key in self.vocabularies:
            self.vocabularies[key] = sorted(list(self.vocabularies[key]))
        
        # 计算特征维度
        self._calculate_feature_dimension()
        
        self.vocab_built = True
        print(f"词汇表构建完成，特征维度: {self.feature_dim}")
    
    def _calculate_feature_dimension(self):
        """计算特征向量维度"""
        dim = 0
        
        # 模式类型（one-hot）
        dim += len(self.vocabularies['pattern_types'])
        
        # 方向（one-hot）
        dim += len(self.vocabularies['directions'])
        
        # 趋势（one-hot）
        dim += len(self.vocabularies['trends'])
        
        # K线特征（multi-hot）
        dim += len(self.vocabularies['kline_features'])
        
        # 市场条件（multi-hot）
        dim += len(self.vocabularies['market_conditions'])
        
        # 数值特征（固定维度）
        dim += 10  # 置信度、相似度等数值特征
        
        self.feature_dim = dim
    
    def vectorize(self, features: Dict) -> np.ndarray:
        """
        将结构化特征转换为向量
        
        Args:
            features: 结构化特征字典
        
        Returns:
            特征向量（numpy数组）
        """
        if not self.vocab_built:
            raise RuntimeError("请先调用build_vocabulary()构建词汇表")
        
        vector = np.zeros(self.feature_dim, dtype=np.float32)
        offset = 0
        
        # 1. 模式类型（one-hot）
        pattern_type = features.get('pattern_type', '')
        if pattern_type in self.vocabularies['pattern_types']:
            idx = self.vocabularies['pattern_types'].index(pattern_type)
            vector[offset + idx] = 1.0
        offset += len(self.vocabularies['pattern_types'])
        
        # 2. 方向（one-hot）
        direction = features.get('direction', 'neutral').lower()
        if direction in self.vocabularies['directions']:
            idx = self.vocabularies['directions'].index(direction)
            vector[offset + idx] = 1.0
        offset += len(self.vocabularies['directions'])
        
        # 3. 趋势（one-hot）
        trend = features.get('trend', 'neutral').lower()
        if trend in self.vocabularies['trends']:
            idx = self.vocabularies['trends'].index(trend)
            vector[offset + idx] = 1.0
        offset += len(self.vocabularies['trends'])
        
        # 4. K线特征（multi-hot）
        kline_features = features.get('kline_features', [])
        if isinstance(kline_features, list):
            for feat in kline_features:
                feat_name = feat if isinstance(feat, str) else feat.get('feature', '') or feat.get('name', '')
                if feat_name in self.vocabularies['kline_features']:
                    idx = self.vocabularies['kline_features'].index(feat_name)
                    vector[offset + idx] = 1.0
        offset += len(self.vocabularies['kline_features'])
        
        # 5. 市场条件（multi-hot）
        market_conditions = features.get('market_conditions', {})
        if isinstance(market_conditions, dict):
            for key, value in market_conditions.items():
                if isinstance(value, str):
                    condition_key = f"{key}_{value}"
                    if condition_key in self.vocabularies['market_conditions']:
                        idx = self.vocabularies['market_conditions'].index(condition_key)
                        vector[offset + idx] = 1.0
        offset += len(self.vocabularies['market_conditions'])
        
        # 6. 数值特征
        # 置信度
        confidence = float(features.get('confidence', 0.0))
        vector[offset] = confidence
        offset += 1
        
        # 趋势强度（如果有）
        trend_strength = float(features.get('trend_strength', 0.0))
        vector[offset] = trend_strength
        offset += 1
        
        # 波动率（如果有）
        volatility = float(features.get('volatility', 0.0))
        vector[offset] = volatility
        offset += 1
        
        # 其他数值特征（预留7个位置）
        offset += 7
        
        return vector
    
    def normalize(self, vector: np.ndarray, method: str = 'l2') -> np.ndarray:
        """
        归一化向量
        
        Args:
            vector: 特征向量
            method: 归一化方法 ('l2', 'l1', 'minmax')
        
        Returns:
            归一化后的向量
        """
        if method == 'l2':
            # L2归一化（用于余弦相似度）
            norm = np.linalg.norm(vector)
            if norm > 0:
                return vector / norm
            return vector
        elif method == 'l1':
            # L1归一化
            norm = np.sum(np.abs(vector))
            if norm > 0:
                return vector / norm
            return vector
        elif method == 'minmax':
            # Min-Max归一化
            min_val = np.min(vector)
            max_val = np.max(vector)
            if max_val > min_val:
                return (vector - min_val) / (max_val - min_val)
            return vector
        else:
            return vector
    
    def vectorize_and_normalize(self, features: Dict, normalize: bool = True) -> np.ndarray:
        """
        向量化并归一化
        
        Args:
            features: 结构化特征
            normalize: 是否归一化
        
        Returns:
            归一化后的特征向量
        """
        vector = self.vectorize(features)
        if normalize:
            vector = self.normalize(vector, method='l2')
        return vector
    
    def get_feature_dimension(self) -> int:
        """获取特征维度"""
        if self.feature_dim is None:
            raise RuntimeError("请先调用build_vocabulary()构建词汇表")
        return self.feature_dim
    
    def save_vocabulary(self, filepath: Path):
        """保存词汇表到文件"""
        vocab_dict = {k: list(v) for k, v in self.vocabularies.items()}
        with filepath.open('w', encoding='utf-8') as f:
            json.dump(vocab_dict, f, indent=2, ensure_ascii=False)
    
    def load_vocabulary(self, filepath: Path):
        """从文件加载词汇表"""
        with filepath.open('r', encoding='utf-8') as f:
            vocab_dict = json.load(f)
        
        # 保持为列表（需要index方法）
        self.vocabularies = {k: list(v) if isinstance(v, list) else sorted(list(v)) for k, v in vocab_dict.items()}
        self._calculate_feature_dimension()
        self.vocab_built = True


def main():
    """测试函数"""
    print("=" * 80)
    print("特征向量化器测试")
    print("=" * 80)
    print()
    
    # 创建向量化器
    vectorizer = FeatureVectorizer()
    
    # 模拟模式数据
    patterns = [
        {
            'structured_features': {
                'pattern_type': 'triangle',
                'direction': 'long',
                'trend': 'bullish',
                'kline_features': ['ascending_triangle', 'breakout'],
                'market_conditions': {'volatility': 'high', 'trend_strength': 'strong'},
                'confidence': 0.85
            }
        },
        {
            'structured_features': {
                'pattern_type': 'wedge',
                'direction': 'short',
                'trend': 'bearish',
                'kline_features': ['descending_wedge'],
                'market_conditions': {'volatility': 'medium'},
                'confidence': 0.75
            }
        }
    ]
    
    # 构建词汇表
    vectorizer.build_vocabulary(patterns)
    print(f"特征维度: {vectorizer.get_feature_dimension()}")
    print()
    
    # 向量化
    for i, pattern in enumerate(patterns, 1):
        features = pattern['structured_features']
        vector = vectorizer.vectorize_and_normalize(features)
        print(f"模式 {i}:")
        print(f"  特征: {features['pattern_type']}, {features['direction']}")
        print(f"  向量维度: {len(vector)}")
        print(f"  向量非零元素: {np.count_nonzero(vector)}")
        print(f"  向量L2范数: {np.linalg.norm(vector):.4f}")
        print()


if __name__ == '__main__':
    main()
