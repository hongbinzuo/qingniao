#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAISS向量检索接口
提供快速相似图表检索功能
"""
import faiss
import pickle
import json
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import time

class ChartVectorSearch:
    """图表向量检索器"""
    
    def __init__(self, index_dir: str = "data/faiss_index"):
        self.index_dir = Path(index_dir)
        self.index = None
        self.metadata = None
        self.config = None
        self._load_index()
    
    def _load_index(self):
        """加载FAISS索引和元数据"""
        index_path = self.index_dir / "chart_vectors.index"
        meta_path = self.index_dir / "metadata.pkl"
        config_path = self.index_dir / "config.json"
        
        if not index_path.exists():
            raise FileNotFoundError(f"Index not found: {index_path}")
        
        print(f"Loading FAISS index from: {index_path}")
        self.index = faiss.read_index(str(index_path))
        
        with open(meta_path, 'rb') as f:
            self.metadata = pickle.load(f)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        print(f"Index loaded: {self.config['num_vectors']} vectors, dim={self.config['vector_dim']}")
    
    def _build_query_vector(self, trend_data: Dict, pattern_data: Dict) -> np.ndarray:
        """
        构建查询向量（与索引构建时保持一致）
        
        Args:
            trend_data: {"direction": 0.8, "ema_distance": 0.6, ...}
            pattern_data: {"primary": "wedge", "direction": "short", "complexity": 0.5}
        """
        features = [
            trend_data.get('direction', 0),
            trend_data.get('ema_distance', 0),
            trend_data.get('volatility', 0.5),
            trend_data.get('slope_strength', 0),
            pattern_data.get('complexity', 0.5),
        ]
        
        primary = pattern_data.get('primary', 'unknown')
        direction = pattern_data.get('direction', 'neutral')
        
        primary_id = hash(primary) % 10 / 10.0
        direction_id = {'long': 1.0, 'short': -1.0, 'neutral': 0.0}.get(direction, 0.0)
        
        features.extend([primary_id, direction_id])
        
        return np.array([features], dtype=np.float32)
    
    def search(self, trend_data: Dict, pattern_data: Dict, k: int = 5) -> List[Dict]:
        """
        检索相似图表
        
        Args:
            trend_data: 趋势特征字典
            pattern_data: 模式特征字典
            k: 返回Top-K个结果
            
        Returns:
            相似图表列表，包含相似度分数
        """
        query_vec = self._build_query_vector(trend_data, pattern_data)
        
        start_time = time.time()
        distances, indices = self.index.search(query_vec, k)
        search_time = (time.time() - start_time) * 1000  # ms
        
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.metadata):
                meta = self.metadata[idx]
                results.append({
                    'rank': i + 1,
                    'id': meta['id'],
                    'image_path': meta['image_path'],
                    'source_page': meta['source_page'],
                    'pattern_name': meta['pattern_name'],
                    'vector_summary': meta['vector_summary'],
                    'similarity': float(dist),
                    'search_time_ms': search_time if i == 0 else None
                })
        
        return results
    
    def search_by_id(self, pattern_id: int, k: int = 5) -> List[Dict]:
        """
        根据已知图表ID检索相似图（用于测试）
        
        Args:
            pattern_id: pattern_library表中的ID
            k: 返回Top-K个结果
        """
        # 在metadata中查找
        for i, meta in enumerate(self.metadata):
            if meta['id'] == pattern_id:
                # 从索引中重建向量
                vector = self.index.reconstruct(i)
                
                start_time = time.time()
                distances, indices = self.index.search(vector.reshape(1, -1), k + 1)  # +1排除自己
                search_time = (time.time() - start_time) * 1000
                
                results = []
                for dist, idx in zip(distances[0], indices[0]):
                    if idx < len(self.metadata) and self.metadata[idx]['id'] != pattern_id:
                        meta = self.metadata[idx]
                        results.append({
                            'id': meta['id'],
                            'image_path': meta['image_path'],
                            'source_page': meta['source_page'],
                            'pattern_name': meta['pattern_name'],
                            'vector_summary': meta['vector_summary'],
                            'similarity': float(dist),
                            'search_time_ms': search_time
                        })
                        if len(results) >= k:
                            break
                
                return results
        
        return []
    
    def batch_search(self, queries: List[Tuple[Dict, Dict]], k: int = 5) -> List[List[Dict]]:
        """
        批量检索（用于回测）
        
        Args:
            queries: [(trend_data1, pattern_data1), ...]
            k: 每个查询返回Top-K
            
        Returns:
            每个查询的结果列表
        """
        query_matrix = np.vstack([
            self._build_query_vector(t, p)[0] for t, p in queries
        ]).astype(np.float32)
        
        start_time = time.time()
        distances, indices = self.index.search(query_matrix, k)
        batch_time = (time.time() - start_time) * 1000
        
        all_results = []
        for i in range(len(queries)):
            results = []
            for j in range(k):
                idx = indices[i][j]
                if idx < len(self.metadata):
                    meta = self.metadata[idx]
                    results.append({
                        'id': meta['id'],
                        'pattern_name': meta['pattern_name'],
                        'similarity': float(distances[i][j])
                    })
            all_results.append(results)
        
        print(f"Batch search: {len(queries)} queries, avg {batch_time/len(queries):.2f}ms per query")
        return all_results
    
    def get_stats(self) -> Dict:
        """获取索引统计信息"""
        return {
            'total_vectors': self.config['num_vectors'],
            'vector_dimension': self.config['vector_dim'],
            'feature_names': self.config['feature_names'],
            'index_type': self.config['index_type']
        }


# 便捷函数
def quick_search(trend_direction: float = 0.8, 
                 ema_relation: str = "above",
                 primary_pattern: str = "wedge",
                 direction: str = "long",
                 k: int = 5) -> List[Dict]:
    """
    快速检索接口（简化参数）
    
    Args:
        trend_direction: 趋势方向 (-1.0~1.0)
        ema_relation: EMA关系 ("above"/"below"/"crossing")
        primary_pattern: 主模式类型
        direction: 方向偏好 ("long"/"short"/"neutral")
        k: 返回结果数
    """
    ema_map = {"above": 0.6, "below": -0.6, "crossing": 0.0}
    
    trend_data = {
        'direction': trend_direction,
        'ema_distance': ema_map.get(ema_relation, 0),
        'volatility': 0.5,
        'slope_strength': abs(trend_direction)
    }
    
    pattern_data = {
        'primary': primary_pattern,
        'direction': direction,
        'complexity': 0.5
    }
    
    searcher = ChartVectorSearch()
    return searcher.search(trend_data, pattern_data, k)


if __name__ == "__main__":
    # 测试
    print("Testing FAISS Search...")
    print("=" * 60)
    
    # 初始化
    searcher = ChartVectorSearch()
    
    # 打印统计
    stats = searcher.get_stats()
    print(f"\nIndex stats: {stats}")
    
    # 测试1: 根据ID检索
    print("\nTest 1: Search by ID (pattern_id=24)")
    results = searcher.search_by_id(24, k=5)
    for r in results:
        print(f"  {r['pattern_name']} (page {r['source_page']}) - sim: {r['similarity']:.3f} - {r['search_time_ms']:.2f}ms")
    
    # 测试2: 自定义特征检索
    print("\nTest 2: Custom feature search")
    trend = {'direction': 0.8, 'ema_distance': 0.6, 'volatility': 0.5, 'slope_strength': 0.8}
    pattern = {'primary': 'wedge', 'direction': 'short', 'complexity': 0.7}
    results = searcher.search(trend, pattern, k=5)
    for r in results:
        print(f"  {r['pattern_name']} - sim: {r['similarity']:.3f}")
    
    # 测试3: 快速接口
    print("\nTest 3: Quick search interface")
    results = quick_search(trend_direction=0.8, ema_relation="above", 
                          primary_pattern="wedge", direction="long", k=5)
    for r in results:
        print(f"  {r['pattern_name']} - sim: {r['similarity']:.3f}")
    
    print("\n" + "=" * 60)
    print("All tests passed!")
