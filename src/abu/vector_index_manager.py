#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
向量索引管理器 - ABU系统v3.0

使用Annoy建立向量索引，加速模式相似度搜索。
"""

from __future__ import annotations
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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
    print("[WARN] NumPy不可用", file=sys.stderr)

try:
    from annoy import AnnoyIndex
    ANNOY_AVAILABLE = True
except ImportError:
    ANNOY_AVAILABLE = False
    print("[WARN] Annoy不可用，请安装: pip install annoy", file=sys.stderr)

from abu.feature_vectorizer import FeatureVectorizer


class VectorIndexManager:
    """
    向量索引管理器
    
    功能：
    1. 建立向量索引
    2. 保存和加载索引
    3. 快速相似度搜索
    """
    
    def __init__(
        self,
        dimension: Optional[int] = None,
        metric: str = 'angular',  # 'angular' (余弦相似度) 或 'euclidean'
        n_trees: int = 10
    ):
        """
        初始化向量索引管理器
        
        Args:
            dimension: 特征向量维度
            metric: 距离度量 ('angular' 或 'euclidean')
            n_trees: Annoy索引树的数量（越多越精确但越慢）
        """
        if not NUMPY_AVAILABLE:
            raise RuntimeError("需要安装NumPy: pip install numpy")
        
        if not ANNOY_AVAILABLE:
            raise RuntimeError("需要安装Annoy: pip install annoy")
        
        self.dimension = dimension
        self.metric = metric
        self.n_trees = n_trees
        
        self.index: Optional[AnnoyIndex] = None
        self.vectorizer: Optional[FeatureVectorizer] = None
        self.pattern_id_map: Dict[int, str] = {}  # {index_id: pattern_id}
        self.pattern_id_reverse_map: Dict[str, int] = {}  # {pattern_id: index_id}
        self.built = False
    
    def set_vectorizer(self, vectorizer: FeatureVectorizer):
        """设置特征向量化器"""
        self.vectorizer = vectorizer
        if self.dimension is None:
            self.dimension = vectorizer.get_feature_dimension()
            self.index = AnnoyIndex(self.dimension, self.metric)
    
    def build_index(
        self,
        patterns: List[Dict],
        vectorizer: Optional[FeatureVectorizer] = None
    ) -> int:
        """
        建立向量索引
        
        Args:
            patterns: 模式列表，每个包含pattern_id和structured_features
            vectorizer: 特征向量化器，如果为None则自动创建
        
        Returns:
            索引的模式数量
        """
        if vectorizer is None:
            if self.vectorizer is None:
                self.vectorizer = FeatureVectorizer()
                self.vectorizer.build_vocabulary(patterns)
            vectorizer = self.vectorizer
        else:
            self.vectorizer = vectorizer
        
        if not vectorizer.vocab_built:
            vectorizer.build_vocabulary(patterns)
        
        # 初始化索引
        if self.dimension is None:
            self.dimension = vectorizer.get_feature_dimension()
        
        if self.index is None:
            self.index = AnnoyIndex(self.dimension, self.metric)
        
        # 清空现有索引
        self.index.unload()
        self.index = AnnoyIndex(self.dimension, self.metric)
        self.pattern_id_map = {}
        self.pattern_id_reverse_map = {}
        
        print(f"建立向量索引（维度: {self.dimension}, 模式数: {len(patterns)}）...")
        
        # 向量化并添加到索引
        for idx, pattern in enumerate(patterns):
            pattern_id = pattern.get('pattern_id', f'pattern_{idx}')
            features = pattern.get('structured_features', {})
            
            # 向量化
            vector = vectorizer.vectorize_and_normalize(features, normalize=True)
            
            # 添加到索引
            self.index.add_item(idx, vector)
            
            # 保存映射
            self.pattern_id_map[idx] = pattern_id
            self.pattern_id_reverse_map[pattern_id] = idx
        
        # 构建索引
        print(f"构建索引（{self.n_trees}棵树）...")
        self.index.build(self.n_trees)
        
        self.built = True
        print(f"索引构建完成，共 {len(patterns)} 个模式")
        
        return len(patterns)
    
    def search(
        self,
        query_features: Dict,
        top_k: int = 10,
        search_k: int = -1
    ) -> List[Tuple[str, float]]:
        """
        搜索相似模式
        
        Args:
            query_features: 查询特征（结构化特征字典）
            top_k: 返回Top K结果
            search_k: 搜索的候选数（-1表示自动，通常为top_k * n_trees）
        
        Returns:
            结果列表，每个元素为 (pattern_id, distance)
        """
        if not self.built or self.index is None:
            raise RuntimeError("索引未构建，请先调用build_index()")
        
        if self.vectorizer is None:
            raise RuntimeError("向量化器未设置")
        
        # 向量化查询
        query_vector = self.vectorizer.vectorize_and_normalize(query_features, normalize=True)
        
        # 搜索
        if search_k == -1:
            search_k = top_k * self.n_trees
        
        nearest_indices, distances = self.index.get_nns_by_vector(
            query_vector,
            top_k,
            include_distances=True,
            search_k=search_k
        )
        
        # 转换为pattern_id
        results = []
        for idx, distance in zip(nearest_indices, distances):
            pattern_id = self.pattern_id_map.get(idx, f'unknown_{idx}')
            # 将距离转换为相似度
            if self.metric == 'angular':
                # angular距离范围是0-2，0表示完全相同
                # 相似度 = 1 - (distance / 2)，范围0-1
                similarity = max(0.0, 1.0 - (distance / 2.0))
            else:
                # 对于欧氏距离，使用倒数归一化
                similarity = 1.0 / (1.0 + distance)
            results.append((pattern_id, similarity))
        
        return results
    
    def save_index(self, index_dir: Path):
        """
        保存索引到文件
        
        Args:
            index_dir: 索引目录
        """
        if not self.built or self.index is None:
            raise RuntimeError("索引未构建")
        
        index_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存Annoy索引
        index_file = index_dir / 'pattern_index.ann'
        self.index.save(str(index_file))
        
        # 保存映射
        mapping_file = index_dir / 'pattern_mapping.json'
        with mapping_file.open('w', encoding='utf-8') as f:
            json.dump(self.pattern_id_map, f, indent=2, ensure_ascii=False)
        
        # 保存配置
        config_file = index_dir / 'index_config.json'
        config = {
            'dimension': self.dimension,
            'metric': self.metric,
            'n_trees': self.n_trees,
            'pattern_count': len(self.pattern_id_map)
        }
        with config_file.open('w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        # 保存向量化器词汇表
        if self.vectorizer:
            vocab_file = index_dir / 'vocabulary.json'
            self.vectorizer.save_vocabulary(vocab_file)
        
        print(f"索引已保存到: {index_dir}")
    
    def load_index(
        self,
        index_dir: Path,
        vectorizer: Optional[FeatureVectorizer] = None
    ):
        """
        从文件加载索引
        
        Args:
            index_dir: 索引目录
            vectorizer: 特征向量化器，如果为None则自动创建
        """
        # 加载配置
        config_file = index_dir / 'index_config.json'
        if not config_file.exists():
            raise FileNotFoundError(f"索引配置文件不存在: {config_file}")
        
        with config_file.open('r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.dimension = config['dimension']
        self.metric = config['metric']
        self.n_trees = config['n_trees']
        
        # 加载向量化器
        if vectorizer is None:
            self.vectorizer = FeatureVectorizer()
            vocab_file = index_dir / 'vocabulary.json'
            if vocab_file.exists():
                self.vectorizer.load_vocabulary(vocab_file)
        else:
            self.vectorizer = vectorizer
        
        # 加载映射
        mapping_file = index_dir / 'pattern_mapping.json'
        with mapping_file.open('r', encoding='utf-8') as f:
            mapping_data = json.load(f)
            # 确保键是整数
            self.pattern_id_map = {int(k): v for k, v in mapping_data.items()}
        
        # 构建反向映射
        self.pattern_id_reverse_map = {v: int(k) for k, v in self.pattern_id_map.items()}
        
        # 加载Annoy索引
        index_file = index_dir / 'pattern_index.ann'
        if not index_file.exists():
            raise FileNotFoundError(f"索引文件不存在: {index_file}")
        
        self.index = AnnoyIndex(self.dimension, self.metric)
        self.index.load(str(index_file))
        
        self.built = True
        print(f"索引已加载，共 {len(self.pattern_id_map)} 个模式")
    
    def get_statistics(self) -> Dict:
        """获取索引统计信息"""
        return {
            'dimension': self.dimension,
            'metric': self.metric,
            'n_trees': self.n_trees,
            'pattern_count': len(self.pattern_id_map),
            'built': self.built
        }


def main():
    """测试函数"""
    print("=" * 80)
    print("向量索引管理器测试")
    print("=" * 80)
    print()
    
    # 模拟模式数据
    patterns = [
        {
            'pattern_id': 'pattern_1',
            'structured_features': {
                'pattern_type': 'triangle',
                'direction': 'long',
                'trend': 'bullish',
                'kline_features': ['ascending_triangle'],
                'confidence': 0.85
            }
        },
        {
            'pattern_id': 'pattern_2',
            'structured_features': {
                'pattern_type': 'wedge',
                'direction': 'short',
                'trend': 'bearish',
                'kline_features': ['descending_wedge'],
                'confidence': 0.75
            }
        },
        {
            'pattern_id': 'pattern_3',
            'structured_features': {
                'pattern_type': 'triangle',
                'direction': 'long',
                'trend': 'bullish',
                'kline_features': ['ascending_triangle', 'breakout'],
                'confidence': 0.90
            }
        }
    ]
    
    # 创建索引管理器
    manager = VectorIndexManager(n_trees=10)
    
    # 建立索引
    count = manager.build_index(patterns)
    print(f"索引了 {count} 个模式\n")
    
    # 测试搜索
    query_features = {
        'pattern_type': 'triangle',
        'direction': 'long',
        'trend': 'bullish',
        'kline_features': ['ascending_triangle'],
        'confidence': 0.8
    }
    
    print("搜索相似模式...")
    results = manager.search(query_features, top_k=3)
    
    print(f"\n找到 {len(results)} 个相似模式:")
    for i, (pattern_id, similarity) in enumerate(results, 1):
        print(f"  {i}. {pattern_id}: 相似度={similarity:.3f}")
    
    # 测试保存和加载
    index_dir = Path('/tmp') / 'test_vector_index'
    if sys.platform == 'win32':
        import os
        index_dir = Path(os.getenv('TEMP', '/tmp')) / 'test_vector_index'
    
    print(f"\n保存索引到: {index_dir}")
    manager.save_index(index_dir)
    
    # 重新加载
    print("\n重新加载索引...")
    new_manager = VectorIndexManager()
    new_manager.load_index(index_dir)
    
    # 再次搜索
    results2 = new_manager.search(query_features, top_k=3)
    print(f"\n重新加载后搜索，找到 {len(results2)} 个相似模式:")
    for i, (pattern_id, similarity) in enumerate(results2, 1):
        print(f"  {i}. {pattern_id}: 相似度={similarity:.3f}")


if __name__ == '__main__':
    main()
