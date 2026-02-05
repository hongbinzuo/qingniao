#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版混合匹配器 - ABU系统v3.0

集成：
1. 统一模式库（UnifiedPatternLibrary）
2. 多源融合算法（MultiSourceFusion）
3. 异步匹配（AsyncMatcher）
4. 混合视觉匹配（HybridVisionPatternMatcher）

提供完整的端到端匹配流程。
"""

from __future__ import annotations
import sys
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from abu.unified_pattern_library import UnifiedPatternLibrary
    from abu.async_matcher import AsyncPatternMatcher
    from abu.multi_source_fusion import (
        calculate_combined_confidence,
        fuse_grouped_matches,
        group_matches_by_pattern
    )
    from abu.hybrid_vision_pattern_matcher import HybridVisionPatternMatcher, HybridMatchResult
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[WARN] 导入失败: {e}", file=sys.stderr)


@dataclass
class EnhancedMatchResult:
    """增强版匹配结果"""
    pattern_id: str
    pattern_name: str
    pattern_type: str
    source: str
    algorithm_score: float
    combined_confidence: float  # 多源融合置信度
    final_score: float
    vision_score: Optional[float] = None
    all_sources: Optional[List[str]] = None  # 匹配到的所有数据源
    vision_result: Any = None


class EnhancedHybridMatcher:
    """
    增强版混合匹配器（v3.0完整版）
    
    工作流程：
    1. 使用统一模式库进行多源异步匹配
    2. 应用多源融合算法
    3. （可选）使用AI视觉验证Top N结果
    4. 综合评分，返回最终结果
    """
    
    def __init__(
        self,
        # 统一模式库配置
        pattern_library: Optional[UnifiedPatternLibrary] = None,
        load_patterns: bool = True,
        
        # 匹配策略
        strategy: str = 'comprehensive',  # 'fast' | 'balanced' | 'comprehensive'
        use_async: bool = True,
        use_vision: bool = False,  # 默认关闭，需要时启用
        
        # 匹配参数
        min_similarity: float = 0.5,
        top_k: int = 10,
        min_confidence: float = 0.0,
        
        # 视觉匹配配置（如果启用）
        vision_config: Optional[Dict] = None
    ):
        """
        初始化增强版混合匹配器
        
        Args:
            pattern_library: 统一模式库实例
            load_patterns: 是否自动加载模式库
            strategy: 匹配策略
            use_async: 是否使用异步匹配
            use_vision: 是否使用AI视觉验证
            min_similarity: 最小相似度阈值
            top_k: 返回Top K结果
            min_confidence: 最小置信度阈值
            vision_config: 视觉匹配配置
        """
        if not IMPORTS_AVAILABLE:
            raise ImportError("需要安装相关依赖")
        
        # 初始化统一模式库
        if pattern_library is None:
            self.pattern_library = UnifiedPatternLibrary('abu')
            if load_patterns:
                self.pattern_library.load_all_patterns()
        else:
            self.pattern_library = pattern_library
        
        # 初始化异步匹配器
        if use_async:
            self.async_matcher = AsyncPatternMatcher(
                pattern_library=self.pattern_library,
                max_workers=3
            )
        else:
            self.async_matcher = None
        
        # 初始化视觉匹配器（可选）
        self.vision_matcher = None
        if use_vision:
            try:
                vision_config = vision_config or {}
                self.vision_matcher = HybridVisionPatternMatcher(
                    min_similarity=min_similarity,
                    max_candidates=top_k,
                    use_vision=True,
                    use_all_candidates=False,  # 只对Top N使用视觉匹配
                    vision_top_n=min(5, top_k),  # 最多5个使用视觉匹配
                    **vision_config
                )
            except Exception as e:
                print(f"[WARN] 视觉匹配器初始化失败: {e}，将不使用视觉验证")
                self.vision_matcher = None
                use_vision = False
        
        # 配置参数
        self.strategy = strategy
        self.use_async = use_async
        self.use_vision = use_vision and self.vision_matcher is not None
        self.min_similarity = min_similarity
        self.top_k = top_k
        self.min_confidence = min_confidence
        
        # 传递给异步匹配器
        if self.async_matcher:
            self.async_matcher.min_similarity = min_similarity
            self.async_matcher.min_confidence = min_confidence
        
        # 加载策略配置
        self.strategy_config = self._load_strategy_config()
    
    def _load_strategy_config(self) -> Dict:
        """加载匹配策略配置"""
        try:
            import yaml
            config_file = ROOT / 'config' / 'pattern_weights.yaml'
            if config_file.exists():
                with config_file.open('r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    strategies = config.get('matching_strategies', {})
                    return strategies.get(self.strategy, {})
        except Exception:
            pass
        
        # 默认配置
        default_configs = {
            'fast': {
                'algorithm_only': True,
                'top_k': 5,
                'sources': ['gemini_flash']
            },
            'balanced': {
                'algorithm_filter': True,
                'ai_vision_top_n': 10,
                'sources': ['gemini_flash', 'cursor_ai']
            },
            'comprehensive': {
                'algorithm_filter': True,
                'ai_vision_all': True,
                'rule_validation': True,
                'sources': ['gemini_flash', 'cursor_ai', 'brooks_rule']
            }
        }
        return default_configs.get(self.strategy, default_configs['comprehensive'])
    
    async def async_match(
        self,
        query_features: Dict,
        klines_dict: Optional[Dict[str, List[Dict]]] = None,
        symbol: str = "BTC_USDT"
    ) -> List[EnhancedMatchResult]:
        """
        异步匹配模式
        
        Args:
            query_features: 查询特征（标准化格式）
            klines_dict: K线数据字典（用于视觉匹配）
            symbol: 交易对符号
        
        Returns:
            增强版匹配结果列表
        """
        if not self.use_async or self.async_matcher is None:
            # 降级到同步匹配
            return self.sync_match(query_features, klines_dict, symbol)
        
        # 1. 异步多源匹配
        sources = self.strategy_config.get('sources', ['gemini_flash', 'cursor_ai', 'brooks_rule'])
        top_k = self.strategy_config.get('top_k', self.top_k)
        
        matches = await self.async_matcher.async_match(
            query_features=query_features,
            sources=sources,
            top_k=top_k * 2,  # 获取更多候选，用于后续筛选
            min_confidence=self.min_confidence
        )
        
        # 2. （可选）AI视觉验证
        if self.use_vision and klines_dict and matches:
            vision_results = await self._apply_vision_verification(
                matches[:self.vision_matcher.vision_top_n],
                klines_dict,
                symbol
            )
            # 更新视觉分数
            for i, vision_result in enumerate(vision_results):
                if i < len(matches):
                    if vision_result is None:
                        matches[i]['vision_score'] = None
                        continue
                    if isinstance(vision_result, dict):
                        raw_score = vision_result.get('similarity_score')
                        matches[i]['vision_score'] = raw_score / 100.0 if isinstance(raw_score, (int, float)) else None
                    elif hasattr(vision_result, 'similarity_score'):
                        matches[i]['vision_score'] = vision_result.similarity_score / 100.0
                    elif hasattr(vision_result, 'vision_score'):
                        matches[i]['vision_score'] = vision_result.vision_score
                    else:
                        matches[i]['vision_score'] = None
        
        # 3. 转换为增强版结果
        enhanced_results = self._convert_to_enhanced_results(matches)
        
        # 4. 按最终分数排序
        enhanced_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return enhanced_results[:self.top_k]
    
    def sync_match(
        self,
        query_features: Dict,
        klines_dict: Optional[Dict[str, List[Dict]]] = None,
        symbol: str = "BTC_USDT"
    ) -> List[EnhancedMatchResult]:
        """
        同步匹配模式（用于对比测试）
        
        Args:
            query_features: 查询特征
            klines_dict: K线数据字典
            symbol: 交易对符号
        
        Returns:
            增强版匹配结果列表
        """
        if self.async_matcher is None:
            # 直接使用统一模式库搜索
            sources = self.strategy_config.get('sources', ['gemini_flash', 'cursor_ai', 'brooks_rule'])
            matches = self.pattern_library.search_patterns(
                query_features=query_features,
                sources=sources,
                top_k=self.top_k * 2,
                min_confidence=self.min_confidence
            )
        else:
            matches = self.async_matcher.sync_match(
                query_features=query_features,
                sources=self.strategy_config.get('sources'),
                top_k=self.top_k * 2,
                min_confidence=self.min_confidence
            )
        
        # 转换为增强版结果
        enhanced_results = self._convert_to_enhanced_results(matches)
        
        # 按最终分数排序
        enhanced_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return enhanced_results[:self.top_k]
    
    async def _apply_vision_verification(
        self,
        matches: List[Dict],
        klines_dict: Dict[str, List[Dict]],
        symbol: str
    ) -> List[Optional[HybridMatchResult]]:
        """
        应用AI视觉验证（异步）
        
        Args:
            matches: 匹配结果列表
            klines_dict: K线数据字典
            symbol: 交易对符号
        
        Returns:
            视觉验证结果列表
        """
        if not self.vision_matcher:
            return [None] * len(matches)
        
        # 使用视觉匹配器对指定候选打分，保证与候选顺序一致
        loop = asyncio.get_event_loop()
        timeframe = '15m'
        if isinstance(klines_dict, dict) and klines_dict:
            if '15m' in klines_dict:
                timeframe = '15m'
            else:
                timeframe = next(iter(klines_dict.keys()))
        vision_results = await loop.run_in_executor(
            None,
            self.vision_matcher.match_candidates,
            matches,
            klines_dict,
            symbol,
            timeframe
        )

        return vision_results[:len(matches)]
    
    def _convert_to_enhanced_results(self, matches: List[Dict]) -> List[EnhancedMatchResult]:
        """
        转换匹配结果为增强版结果
        
        Args:
            matches: 匹配结果列表
        
        Returns:
            增强版匹配结果列表
        """
        enhanced_results = []
        
        for match in matches:
            pattern = match.get('pattern', {})
            
            # 提取信息
            pattern_id = match.get('pattern_id', '')
            pattern_name = pattern.get('pattern_name', 'Unknown')
            pattern_type = pattern.get('pattern_type', 'unknown')
            source = match.get('source', 'unknown')
            similarity = match.get('similarity', 0.0)
            confidence = match.get('confidence', 0.0)
            combined_confidence = match.get('combined_confidence', 0.0)
            vision_score = match.get('vision_score')
            all_sources = match.get('all_sources', [source])
            
            # 计算最终分数
            if combined_confidence > 0:
                # 使用融合置信度
                base_score = combined_confidence
            else:
                # 使用相似度或置信度
                base_score = max(similarity, confidence)
            
            # 获取概率信息（如果可用）
            probability_score = None
            pattern = self.pattern_library.patterns.get(pattern_id)
            if pattern and hasattr(pattern, 'probability_score') and pattern.probability_score:
                probability_score = pattern.probability_score
            elif pattern_name in self.pattern_library.probability_rules:
                probability_score = self.pattern_library.probability_rules[pattern_name].get('probability')
            
            # 如果有概率信息，调整基础分数
            if probability_score is not None:
                # 概率权重30%，算法匹配权重70%
                probability_normalized = probability_score / 100.0
                base_score = (
                    base_score * 0.7 + 
                    probability_normalized * 0.3
                )
            
            # 如果有视觉分数，综合计算
            if vision_score is not None:
                final_score = (base_score * 0.4) + (vision_score * 0.6)
            else:
                final_score = base_score
            
            enhanced_result = EnhancedMatchResult(
                pattern_id=pattern_id,
                pattern_name=pattern_name,
                pattern_type=pattern_type,
                source=source,
                algorithm_score=similarity,
                combined_confidence=combined_confidence if combined_confidence > 0 else base_score,
                final_score=final_score,
                vision_score=vision_score,
                all_sources=all_sources
            )
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def close(self):
        """关闭资源"""
        if hasattr(self, 'async_matcher') and self.async_matcher:
            self.async_matcher.close()
        if hasattr(self, 'pattern_library') and self.pattern_library:
            self.pattern_library.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


async def enhanced_match(
    query_features: Dict,
    klines_dict: Optional[Dict[str, List[Dict]]] = None,
    symbol: str = "BTC_USDT",
    strategy: str = 'comprehensive',
    use_vision: bool = False,
    top_k: int = 10
) -> List[EnhancedMatchResult]:
    """
    便捷函数：增强版匹配
    
    Args:
        query_features: 查询特征
        klines_dict: K线数据字典
        symbol: 交易对符号
        strategy: 匹配策略
        use_vision: 是否使用视觉验证
        top_k: 返回Top K结果
    
    Returns:
        增强版匹配结果列表
    """
    matcher = EnhancedHybridMatcher(
        strategy=strategy,
        use_async=True,
        use_vision=use_vision,
        top_k=top_k
    )
    
    try:
        results = await matcher.async_match(
            query_features=query_features,
            klines_dict=klines_dict,
            symbol=symbol
        )
        return results
    finally:
        matcher.close()


def main():
    """测试函数"""
    import asyncio
    
    print("=" * 80)
    print("增强版混合匹配器测试")
    print("=" * 80)
    print()
    
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
    
    async def test_async():
        # 创建匹配器
        matcher = EnhancedHybridMatcher(
            strategy='comprehensive',
            use_async=True,
            use_vision=False,  # 测试时不使用视觉验证
            top_k=5
        )
        
        try:
            print("执行异步匹配...")
            results = await matcher.async_match(query_features, symbol="BTC_USDT")
            
            print(f"\n找到 {len(results)} 个匹配:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.pattern_name}")
                print(f"   来源: {result.source}")
                print(f"   算法分数: {result.algorithm_score:.3f}")
                print(f"   融合置信度: {result.combined_confidence:.3f}")
                print(f"   最终分数: {result.final_score:.3f}")
                if result.all_sources and len(result.all_sources) > 1:
                    print(f"   多源匹配: {', '.join(result.all_sources)}")
                print()
        finally:
            matcher.close()
    
    asyncio.run(test_async())


if __name__ == '__main__':
    main()
