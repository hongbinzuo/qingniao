#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAISS向量索引构建器
从Postgres加载向量，构建高效检索索引
"""
import psycopg2
import numpy as np
import faiss
import pickle
import json
from pathlib import Path
from typing import List, Tuple, Dict

class FaissIndexBuilder:
    def __init__(self, pg_config: Dict, index_dir: str = "data/faiss_index"):
        self.pg_config = pg_config
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
    def load_vectors_from_postgres(self) -> Tuple[np.ndarray, List[Dict]]:
        """从Postgres加载所有向量"""
        print("Loading vectors from PostgreSQL...")
        
        conn = psycopg2.connect(**self.pg_config)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT v.pattern_library_id, v.image_path, v.source_page,
                   v.trend_vector, v.pattern_features, v.vector_summary,
                   p.pattern_name
            FROM pattern_vectors v
            JOIN pattern_library p ON v.pattern_library_id = p.id
            ORDER BY v.pattern_library_id
        ''')
        
        vectors = []
        metadata = []
        
        for row in cursor.fetchall():
            pid, img_path, page, trend, pattern, summary, name = row
            
            # 构建特征向量 [direction, ema_dist, volatility, slope, primary_id, direction_id, complexity]
            trend_vec = trend if isinstance(trend, dict) else json.loads(trend)
            pattern_vec = pattern if isinstance(pattern, dict) else json.loads(pattern)
            
            # 数值特征（归一化到-1~1）
            features = [
                trend_vec.get('direction', 0),
                trend_vec.get('ema_distance', 0),
                trend_vec.get('volatility', 0.5),
                trend_vec.get('slope_strength', 0),
                pattern_vec.get('complexity', 0.5),
            ]
            
            # One-hot编码pattern类型（简化版，用哈希）
            primary = pattern_vec.get('primary', 'unknown')
            direction = pattern_vec.get('direction', 'neutral')
            
            # 将类别映射为数值（简单哈希）
            primary_id = hash(primary) % 10 / 10.0  # 0-1之间
            direction_id = {'long': 1.0, 'short': -1.0, 'neutral': 0.0}.get(direction, 0.0)
            
            features.extend([primary_id, direction_id])
            
            vectors.append(features)
            metadata.append({
                'id': pid,
                'image_path': img_path,
                'source_page': page,
                'pattern_name': name,
                'vector_summary': summary,
                'primary': primary,
                'direction': direction
            })
        
        conn.close()
        
        vectors_array = np.array(vectors, dtype=np.float32)
        print(f"Loaded {len(vectors)} vectors, dim={vectors_array.shape[1]}")
        
        return vectors_array, metadata
    
    def build_index(self, vectors: np.ndarray, metadata: List[Dict]):
        """构建FAISS索引"""
        d = vectors.shape[1]  # 向量维度
        n = vectors.shape[0]  # 向量数量
        
        print(f"Building FAISS index (d={d}, n={n})...")
        
        # 选择索引类型
        if n < 1000:
            # 小数据集：暴力搜索（最精确）
            print("Using IndexFlatIP (exact search)")
            index = faiss.IndexFlatIP(d)  # 内积相似度
        else:
            # 大数据集：使用IVF加速
            print("Using IndexIVFFlat (approximate search)")
            nlist = min(100, int(np.sqrt(n)))  # 聚类中心数
            quantizer = faiss.IndexFlatIP(d)
            index = faiss.IndexIVFFlat(quantizer, d, nlist, faiss.METRIC_INNER_PRODUCT)
            
            # 训练索引
            print("Training index...")
            index.train(vectors)
        
        # 添加向量
        print("Adding vectors to index...")
        index.add(vectors)
        
        # 保存索引
        index_path = self.index_dir / "chart_vectors.index"
        faiss.write_index(index, str(index_path))
        print(f"Index saved to: {index_path}")
        
        # 保存元数据
        meta_path = self.index_dir / "metadata.pkl"
        with open(meta_path, 'wb') as f:
            pickle.dump(metadata, f)
        print(f"Metadata saved to: {meta_path}")
        
        # 保存配置
        config = {
            'vector_dim': d,
            'num_vectors': n,
            'index_type': 'IndexFlatIP' if n < 1000 else 'IndexIVFFlat',
            'feature_names': ['direction', 'ema_distance', 'volatility', 'slope_strength', 
                            'complexity', 'primary_id', 'direction_id']
        }
        config_path = self.index_dir / "config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        return index, metadata
    
    def test_search(self, index: faiss.Index, metadata: List[Dict], k: int = 5):
        """测试检索功能"""
        print(f"\nTesting search (k={k})...")
        
        # 随机选5个查询
        import random
        random.seed(42)
        test_indices = random.sample(range(len(metadata)), min(5, len(metadata)))
        
        for idx in test_indices:
            query_vec = index.reconstruct(idx)  # 从索引中取出原始向量
            distances, indices = index.search(query_vec.reshape(1, -1), k)
            
            print(f"\nQuery: {metadata[idx]['pattern_name']} (page {metadata[idx]['source_page']})")
            print(f"  Top-{k} matches:")
            for i, (dist, found_idx) in enumerate(zip(distances[0], indices[0]), 1):
                if found_idx < len(metadata):
                    meta = metadata[found_idx]
                    print(f"    {i}. {meta['pattern_name']} (page {meta['source_page']}) - sim: {dist:.3f}")
    
    def run(self):
        """完整流程"""
        print("=" * 60)
        print("FAISS Index Builder")
        print("=" * 60)
        
        # 1. 加载数据
        vectors, metadata = self.load_vectors_from_postgres()
        
        # 2. 构建索引
        index, metadata = self.build_index(vectors, metadata)
        
        # 3. 测试检索
        self.test_search(index, metadata, k=5)
        
        print("\n" + "=" * 60)
        print("Build completed!")
        print(f"Index location: {self.index_dir}")
        print("=" * 60)


if __name__ == "__main__":
    pg_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'qingniao_abu',
        'user': 'abu_user',
        'password': 'Abu2026!Secure'
    }
    
    builder = FaissIndexBuilder(pg_config)
    builder.run()
