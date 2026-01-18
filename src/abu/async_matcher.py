#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异步匹配模块 - ABU系统v3.0

实现异步多源匹配，并行查询三个数据源以提高性能。
"""

from __future__ import annotations
import sys
import asyncio
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor
import time

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from abu.unified_pattern_library import UnifiedPatternLibrary
    from abu.multi_source_fusion import (
        calculate_combined_confidence,
        group_matches_by_pattern,
        fuse_grouped_matches
    )
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"⚠️  导入失败: {e}", file=sys.stderr)


class AsyncPatternMatcher:
    """异步模式匹配器"""
    
    def __init__(self, 
                 pattern_library: Optional[UnifiedPatternLibrary] = None,
                 max_workers: int = 3):
        """
        初始化异步匹配器
        
        Args:
            pattern_library: 统一模式库实例，None则自动创建
            max_workers: 最大并发工作线程数
        """
        if not IMPORTS_AVAILABLE:
            raise ImportError("需要安装相关依赖")
        
        self.pattern_library = pattern_library
        if self.pattern_library is None:
            self.pattern_library = UnifiedPatternLibrary('abu')
            # 自动加载模式库
            self.pattern_library.load_all_patterns()
        
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.min_similarity = 0.5  # 默认值
        self.min_confidence = 0.0  # 默认值
    
    async def async_match(self,
                         query_features: Dict,
                         sources: Optional[List[str]] = None,
                         top_k: int = 10,
                         min_confidence: float = 0.0,
                         min_similarity: float = 0.5,
                         use_fusion: bool = True) -> List[Dict]:
        """
        异步多源匹配
        
        Args:
            query_features: 查询特征（标准化格式）
            sources: 数据源列表，None表示所有源
            top_k: 返回Top K结果
            min_confidence: 最小置信度阈值
            use_fusion: 是否使用多源融合
        
        Returns:
            匹配结果列表，按融合置信度排序
        """
        if sources is None:
            sources = ['gemini_flash', 'cursor_ai', 'brooks_rule']
        
        # 创建异步任务
        loop = asyncio.get_event_loop()
        
        # 并行查询三个数据源
        tasks = []
        for source in sources:
            task = loop.run_in_executor(
                self.executor,
                self._search_source,
                source,
                query_features,
                top_k,
                min_confidence,
                min_similarity
            )
            tasks.append(task)
        
        # 等待所有任务完成
        start_time = time.time()
        results_by_source = await asyncio.gather(*tasks)
        elapsed_time = time.time() - start_time
        
        # 合并结果
        matches_by_source = {}
        for source, matches in zip(sources, results_by_source):
            matches_by_source[source] = matches
        
        # 融合结果
        if use_fusion:
            # 按模式分组
            all_matches = []
            for matches in matches_by_source.values():
                all_matches.extend(matches)
            
            grouped = group_matches_by_pattern(all_matches)
            fused_results = fuse_grouped_matches(grouped)
            
            # 返回Top K
            return fused_results[:top_k]
        else:
            # 简单合并，不融合
            all_matches = []
            for matches in matches_by_source.values():
                all_matches.extend(matches)
            
            # 按相似度排序
            all_matches.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
            return all_matches[:top_k]
    
    def _search_source(self,
                      source: str,
                      query_features: Dict,
                      top_k: int,
                      min_confidence: float,
                      min_similarity: float = 0.5) -> List[Dict]:
        """
        在指定数据源中搜索（同步函数，在线程池中执行）
        
        Args:
            source: 数据源名称
            query_features: 查询特征
            top_k: 返回Top K结果
            min_confidence: 最小置信度阈值
        
        Returns:
            匹配结果列表
        """
        # 获取该数据源的所有模式
        patterns = self.pattern_library.get_patterns_by_source(source)
        
        matches = []
        for pattern in patterns:
            # 跳过低置信度模式
            if pattern.confidence < min_confidence:
                continue
            
            # 计算相似度
            similarity = self.pattern_library._calculate_similarity(
                query_features,
                pattern.structured_features
            )
            
            # 使用min_similarity阈值
            if similarity >= min_similarity:
                matches.append({
                    'pattern_id': pattern.pattern_id,
                    'pattern': pattern.to_dict(),
                    'similarity': similarity,
                    'confidence': pattern.confidence,
                    'source': source,
                    'weight': 0.5 if source == 'cursor_ai' else 0.3 if source == 'brooks_rule' else 0.2
                })
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return matches[:top_k]
    
    def sync_match(self,
                   query_features: Dict,
                   sources: Optional[List[str]] = None,
                   top_k: int = 10,
                   min_confidence: float = 0.0,
                   min_similarity: float = 0.5,
                   use_fusion: bool = True) -> List[Dict]:
        """
        同步多源匹配（用于对比测试）
        
        Args:
            query_features: 查询特征
            sources: 数据源列表
            top_k: 返回Top K结果
            min_confidence: 最小置信度阈值
            use_fusion: 是否使用多源融合
        
        Returns:
            匹配结果列表
        """
        if sources is None:
            sources = ['gemini_flash', 'cursor_ai', 'brooks_rule']
        
        matches_by_source = {}
        
        # 顺序查询每个数据源
        for source in sources:
            matches = self._search_source(source, query_features, top_k, min_confidence)
            matches_by_source[source] = matches
        
        # 融合结果
        if use_fusion:
            all_matches = []
            for matches in matches_by_source.values():
                all_matches.extend(matches)
            
            grouped = group_matches_by_pattern(all_matches)
            fused_results = fuse_grouped_matches(grouped)
            
            return fused_results[:top_k]
        else:
            all_matches = []
            for matches in matches_by_source.values():
                all_matches.extend(matches)
            
            all_matches.sort(key=lambda x: x.get('similarity', 0.0), reverse=True)
            return all_matches[:top_k]
    
    def close(self):
        """关闭线程池"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


async def async_match_patterns(query_features: Dict,
                                pattern_library: Optional[UnifiedPatternLibrary] = None,
                                sources: Optional[List[str]] = None,
                                top_k: int = 10,
                                min_confidence: float = 0.0) -> List[Dict]:
    """
    便捷函数：异步匹配模式
    
    Args:
        query_features: 查询特征
        pattern_library: 统一模式库实例
        sources: 数据源列表
        top_k: 返回Top K结果
        min_confidence: 最小置信度阈值
    
    Returns:
        匹配结果列表
    """
    matcher = AsyncPatternMatcher(pattern_library=pattern_library)
    try:
        results = await matcher.async_match(
            query_features=query_features,
            sources=sources,
            top_k=top_k,
            min_confidence=min_confidence
        )
        return results
    finally:
        matcher.close()


def main():
    """测试函数"""
    import asyncio
    
    print("=" * 80)
    print("异步匹配测试")
    print("=" * 80)
    print()
    
    # 创建匹配器
    matcher = AsyncPatternMatcher()
    
    # 测试查询特征
    query_features = {
        'pattern_type': 'triangle',
        'direction': 'long',
        'kline_features': ['ascending_triangle']
    }
    
    print("查询特征:")
    print(f"  模式类型: {query_features['pattern_type']}")
    print(f"  方向: {query_features['direction']}")
    print()
    
    # 测试同步匹配
    print("1. 同步匹配测试...")
    start_time = time.time()
    sync_results = matcher.sync_match(query_features, top_k=5)
    sync_time = time.time() - start_time
    print(f"   耗时: {sync_time:.3f}秒")
    print(f"   找到 {len(sync_results)} 个匹配")
    print()
    
    # 测试异步匹配
    print("2. 异步匹配测试...")
    async def test_async():
        start_time = time.time()
        async_results = await matcher.async_match(query_features, top_k=5)
        async_time = time.time() - start_time
        print(f"   耗时: {async_time:.3f}秒")
        print(f"   找到 {len(async_results)} 个匹配")
        
        # 显示前3个结果
        print("\n   前3个匹配结果:")
        for i, result in enumerate(async_results[:3], 1):
            pattern = result.get('pattern', {})
            print(f"   {i}. {pattern.get('pattern_name', 'Unknown')} "
                  f"(来源: {result.get('source', 'unknown')}, "
                  f"融合置信度: {result.get('combined_confidence', 0.0):.2%})")
        
        return async_time
    
    async_time = asyncio.run(test_async())
    print()
    
    # 性能对比
    if sync_time > 0:
        speedup = sync_time / async_time if async_time > 0 else 0
        print(f"性能提升: {speedup:.2f}x")
        print(f"时间节省: {(sync_time - async_time):.3f}秒 ({(1 - async_time/sync_time)*100:.1f}%)")
    
    matcher.close()


if __name__ == '__main__':
    main()
