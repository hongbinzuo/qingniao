#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试向量索引与统一模式库的集成
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from abu.unified_pattern_library import UnifiedPatternLibrary
from abu.vector_index_manager import VectorIndexManager
from abu.feature_vectorizer import FeatureVectorizer


def test_vector_index_integration():
    """测试向量索引集成"""
    print("=" * 80)
    print("向量索引集成测试")
    print("=" * 80)
    print()
    
    # 1. 加载统一模式库
    print("1. 加载统一模式库...")
    library = UnifiedPatternLibrary('abu')
    stats = library.load_all_patterns()
    print(f"   加载了 {stats['total']} 个模式")
    print()
    
    # 2. 建立向量索引
    print("2. 建立向量索引...")
    vectorizer = FeatureVectorizer()
    
    # 准备模式数据
    pattern_data = []
    for pattern_id, pattern in library.patterns.items():
        pattern_data.append({
            'pattern_id': pattern_id,
            'structured_features': pattern.structured_features
        })
    
    # 构建词汇表
    vectorizer.build_vocabulary(pattern_data)
    print(f"   特征维度: {vectorizer.get_feature_dimension()}")
    
    # 建立索引
    start_time = time.time()
    manager = VectorIndexManager(n_trees=10)
    manager.set_vectorizer(vectorizer)
    count = manager.build_index(pattern_data)
    build_time = time.time() - start_time
    print(f"   索引建立完成，耗时: {build_time:.3f}秒")
    print()
    
    # 3. 测试搜索性能
    print("3. 测试搜索性能...")
    query_features = {
        'pattern_type': 'triangle',
        'direction': 'long',
        'trend': 'bullish',
        'kline_features': ['ascending_triangle'],
        'confidence': 0.8
    }
    
    # 向量索引搜索
    start_time = time.time()
    vector_results = manager.search(query_features, top_k=10)
    vector_time = time.time() - start_time
    print(f"   向量索引搜索: {vector_time:.4f}秒，找到 {len(vector_results)} 个结果")
    
    # 线性搜索（对比）
    start_time = time.time()
    linear_results = library.search_patterns(query_features, top_k=10, use_vector_index=False)
    linear_time = time.time() - start_time
    print(f"   线性搜索: {linear_time:.4f}秒，找到 {len(linear_results)} 个结果")
    
    if linear_time > 0:
        speedup = linear_time / vector_time if vector_time > 0 else 0
        print(f"   性能提升: {speedup:.2f}x")
    print()
    
    # 4. 显示Top 3结果
    print("4. Top 3匹配结果（向量索引）:")
    for i, (pattern_id, similarity) in enumerate(vector_results[:3], 1):
        pattern = library.get_pattern(pattern_id)
        if pattern:
            print(f"   {i}. {pattern.pattern_name} (来源: {pattern.source}, 相似度: {similarity:.3f})")
    print()
    
    # 5. 保存索引
    index_dir = ROOT / 'data' / 'vector_index'
    print(f"5. 保存索引到: {index_dir}")
    manager.save_index(index_dir)
    print("   索引已保存")
    print()
    
    library.close()
    
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == '__main__':
    test_vector_index_integration()
