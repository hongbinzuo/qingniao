#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU系统v3.0集成测试脚本

测试：
1. 统一模式库加载
2. 多源匹配
3. 多源融合
4. 异步匹配性能
5. 增强版混合匹配器
"""

import sys
import time
import asyncio
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from abu.unified_pattern_library import UnifiedPatternLibrary
from abu.async_matcher import AsyncPatternMatcher
from abu.multi_source_fusion import calculate_combined_confidence
from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher


def test_unified_library():
    """测试统一模式库"""
    print("=" * 80)
    print("测试1: 统一模式库加载")
    print("=" * 80)
    
    library = UnifiedPatternLibrary('abu')
    stats = library.load_all_patterns()
    
    print(f"\n统计信息:")
    print(f"  总计: {stats['total']} 个模式")
    print(f"  - Gemini Flash: {stats['gemini_flash']}")
    print(f"  - Cursor AI: {stats['cursor_ai']}")
    print(f"  - Brooks规则: {stats['brooks_rule']}")
    
    library.close()
    print("\n[PASS] 统一模式库测试通过\n")
    return library


def test_multi_source_fusion():
    """测试多源融合"""
    print("=" * 80)
    print("测试2: 多源融合算法")
    print("=" * 80)
    
    # 模拟匹配结果
    matches = [
        {'source': 'cursor_ai', 'confidence': 0.92, 'similarity': 0.85},
        {'source': 'gemini_flash', 'confidence': 0.85, 'similarity': 0.78},
        {'source': 'brooks_rule', 'confidence': 0.78, 'similarity': 0.70}
    ]
    
    combined = calculate_combined_confidence(matches)
    print(f"\n输入匹配结果:")
    for i, match in enumerate(matches, 1):
        print(f"  {i}. {match['source']}: 置信度={match['confidence']:.2%}")
    
    print(f"\n融合置信度: {combined:.2%}")
    print(f"\n[PASS] 多源融合测试通过\n")


def test_async_matcher():
    """测试异步匹配器"""
    print("=" * 80)
    print("测试3: 异步匹配器")
    print("=" * 80)
    
    library = UnifiedPatternLibrary('abu')
    library.load_all_patterns()
    
    matcher = AsyncPatternMatcher(pattern_library=library)
    
    query_features = {
        'pattern_type': 'triangle',
        'direction': 'long',
        'kline_features': ['ascending_triangle']
    }
    
    async def test():
        start_time = time.time()
        results = await matcher.async_match(query_features, top_k=5)
        elapsed = time.time() - start_time
        
        print(f"\n查询特征: {query_features['pattern_type']}")
        print(f"耗时: {elapsed:.3f}秒")
        print(f"找到 {len(results)} 个匹配")
        
        if results:
            print(f"\nTop 3结果:")
            for i, result in enumerate(results[:3], 1):
                pattern = result.get('pattern', {})
                print(f"  {i}. {pattern.get('pattern_name', 'Unknown')} "
                      f"(来源: {result.get('source')}, "
                      f"融合置信度: {result.get('combined_confidence', 0.0):.2%})")
        
        return elapsed
    
    elapsed = asyncio.run(test())
    matcher.close()
    library.close()
    
    print(f"\n[PASS] 异步匹配器测试通过 (耗时: {elapsed:.3f}秒)\n")


def test_enhanced_hybrid_matcher():
    """测试增强版混合匹配器"""
    print("=" * 80)
    print("测试4: 增强版混合匹配器")
    print("=" * 80)
    
    query_features = {
        'pattern_type': 'triangle',
        'direction': 'long',
        'kline_features': ['ascending_triangle']
    }
    
    async def test():
        matcher = EnhancedHybridMatcher(
            strategy='comprehensive',
            use_async=True,
            use_vision=False,  # 测试时不使用视觉验证
            top_k=5
        )
        
        try:
            start_time = time.time()
            results = await matcher.async_match(query_features, symbol="BTC_USDT")
            elapsed = time.time() - start_time
            
            print(f"\n查询特征: {query_features['pattern_type']}")
            print(f"策略: comprehensive")
            print(f"耗时: {elapsed:.3f}秒")
            print(f"找到 {len(results)} 个匹配")
            
            if results:
                print(f"\nTop 3结果:")
                for i, result in enumerate(results[:3], 1):
                    print(f"  {i}. {result.pattern_name}")
                    print(f"     来源: {result.source}")
                    print(f"     算法分数: {result.algorithm_score:.3f}")
                    print(f"     融合置信度: {result.combined_confidence:.3f}")
                    print(f"     最终分数: {result.final_score:.3f}")
                    if result.all_sources and len(result.all_sources) > 1:
                        print(f"     多源匹配: {', '.join(result.all_sources)}")
        finally:
            matcher.close()
        
        return elapsed
    
    elapsed = asyncio.run(test())
    print(f"\n[PASS] 增强版混合匹配器测试通过 (耗时: {elapsed:.3f}秒)\n")


def test_performance_comparison():
    """性能对比测试"""
    print("=" * 80)
    print("测试5: 性能对比 (同步 vs 异步)")
    print("=" * 80)
    
    library = UnifiedPatternLibrary('abu')
    library.load_all_patterns()
    
    matcher = AsyncPatternMatcher(pattern_library=library)
    
    query_features = {
        'pattern_type': 'triangle',
        'direction': 'long'
    }
    
    # 同步匹配
    print("\n同步匹配...")
    start_time = time.time()
    sync_results = matcher.sync_match(query_features, top_k=5)
    sync_time = time.time() - start_time
    print(f"  耗时: {sync_time:.3f}秒")
    print(f"  找到 {len(sync_results)} 个匹配")
    
    # 异步匹配
    async def async_test():
        start_time = time.time()
        async_results = await matcher.async_match(query_features, top_k=5)
        async_time = time.time() - start_time
        print(f"  耗时: {async_time:.3f}秒")
        print(f"  找到 {len(async_results)} 个匹配")
        return async_time
    
    async_time = asyncio.run(async_test())
    
    # 性能对比
    if sync_time > 0:
        speedup = sync_time / async_time if async_time > 0 else 0
        print(f"\n性能提升: {speedup:.2f}x")
        print(f"时间节省: {(sync_time - async_time):.3f}秒 ({(1 - async_time/sync_time)*100:.1f}%)")
    
    matcher.close()
    library.close()
    print(f"\n[PASS] 性能对比测试完成\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("ABU系统v3.0集成测试")
    print("=" * 80)
    print()
    
    try:
        # 测试1: 统一模式库
        test_unified_library()
        
        # 测试2: 多源融合
        test_multi_source_fusion()
        
        # 测试3: 异步匹配器
        test_async_matcher()
        
        # 测试4: 增强版混合匹配器
        test_enhanced_hybrid_matcher()
        
        # 测试5: 性能对比
        test_performance_comparison()
        
        print("=" * 80)
        print("所有测试通过！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
