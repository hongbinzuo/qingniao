#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共同模式提取器

提取三个数据源（Gemini Flash, Cursor AI, Brooks规则）重叠的部分，
创建共同模式库，优先匹配。
"""

from typing import Dict, List, Set, Optional
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class CommonPattern:
    """共同模式"""
    pattern_name: str
    pattern_type: str
    sources: List[str]  # 匹配到的数据源列表
    confidence: float  # 综合置信度
    match_count: int  # 匹配次数


class CommonPatternExtractor:
    """共同模式提取器"""
    
    def __init__(self, pattern_library):
        """
        初始化
        
        Args:
            pattern_library: UnifiedPatternLibrary实例
        """
        self.pattern_library = pattern_library
        self.common_patterns: Dict[str, CommonPattern] = {}
    
    def extract_common_patterns(self, min_sources: int = 2) -> Dict[str, CommonPattern]:
        """
        提取共同模式
        
        Args:
            min_sources: 最少需要匹配的数据源数量（默认2个）
        
        Returns:
            共同模式字典
        """
        # 按模式名称和类型分组
        pattern_groups: Dict[tuple, List] = defaultdict(list)
        
        for pattern_id, pattern in self.pattern_library.patterns.items():
            # 使用模式名称和类型作为键
            key = (pattern.pattern_name.lower(), pattern.pattern_type.lower())
            pattern_groups[key].append({
                'pattern_id': pattern_id,
                'source': pattern.source,
                'pattern': pattern,
                'confidence': pattern.confidence
            })
        
        # 找出匹配多个数据源的模式
        common_patterns = {}
        for key, patterns in pattern_groups.items():
            # 统计数据源
            sources = set(p['source'] for p in patterns)
            
            if len(sources) >= min_sources:
                pattern_name, pattern_type = key
                
                # 计算综合置信度（加权平均）
                total_confidence = sum(p['confidence'] for p in patterns)
                avg_confidence = total_confidence / len(patterns)
                
                # 创建共同模式
                common_pattern = CommonPattern(
                    pattern_name=pattern_name,
                    pattern_type=pattern_type,
                    sources=sorted(list(sources)),
                    confidence=avg_confidence,
                    match_count=len(patterns)
                )
                
                # 使用模式名称作为键（如果有多个，使用第一个）
                common_key = f"{pattern_name}_{pattern_type}"
                if common_key not in common_patterns:
                    common_patterns[common_key] = common_pattern
                else:
                    # 如果已存在，选择置信度更高的
                    if avg_confidence > common_patterns[common_key].confidence:
                        common_patterns[common_key] = common_pattern
        
        self.common_patterns = common_patterns
        return common_patterns
    
    def get_common_pattern_ids(self) -> List[str]:
        """
        获取共同模式的所有pattern_id列表
        
        Returns:
            pattern_id列表
        """
        pattern_ids = []
        
        for pattern_id, pattern in self.pattern_library.patterns.items():
            key = (pattern.pattern_name.lower(), pattern.pattern_type.lower())
            if key in [(cp.pattern_name.lower(), cp.pattern_type.lower()) 
                      for cp in self.common_patterns.values()]:
                pattern_ids.append(pattern_id)
        
        return pattern_ids
    
    def prioritize_common_patterns(self, matches: List[Dict]) -> List[Dict]:
        """
        优先排序共同模式
        
        Args:
            matches: 匹配结果列表
        
        Returns:
            重新排序的匹配结果（共同模式在前）
        """
        common_ids = set(self.get_common_pattern_ids())
        
        common_matches = []
        other_matches = []
        
        for match in matches:
            pattern_id = match.get('pattern_id') or match.get('pattern', {}).get('pattern_id')
            if pattern_id in common_ids:
                common_matches.append(match)
            else:
                other_matches.append(match)
        
        # 共同模式在前，按置信度排序
        common_matches.sort(key=lambda x: x.get('confidence', 0) or x.get('combined_confidence', 0), reverse=True)
        other_matches.sort(key=lambda x: x.get('confidence', 0) or x.get('combined_confidence', 0), reverse=True)
        
        return common_matches + other_matches
