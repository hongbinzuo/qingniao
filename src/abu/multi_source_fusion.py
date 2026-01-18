#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多源置信度融合模块 - ABU系统v3.0

实现多源匹配结果的融合算法：
1. 加权平均
2. 一致性奖励（多个源匹配到相似模式时，置信度提升）
"""

from __future__ import annotations
import sys
from pathlib import Path
from typing import List, Dict, Optional
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT / 'config'

# 默认权重配置（如果配置文件不存在）
DEFAULT_SOURCE_WEIGHTS = {
    'cursor_ai': 0.5,
    'brooks_rule': 0.3,
    'gemini_flash': 0.2
}

DEFAULT_CONSISTENCY_CONFIG = {
    'enabled': True,
    'bonus_per_source': 0.1,
    'max_bonus': 0.2
}


def load_weights_config() -> Dict:
    """加载权重配置文件"""
    config_file = CONFIG_DIR / 'pattern_weights.yaml'
    
    if config_file.exists():
        try:
            with config_file.open('r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            print(f"⚠️  加载权重配置失败: {e}，使用默认配置", file=sys.stderr)
    
    return {
        'source_weights': DEFAULT_SOURCE_WEIGHTS,
        'consistency': DEFAULT_CONSISTENCY_CONFIG
    }


def calculate_combined_confidence(matches: List[Dict], 
                                  source_weights: Optional[Dict[str, float]] = None,
                                  consistency_config: Optional[Dict] = None) -> float:
    """
    计算多源匹配结果的融合置信度
    
    Args:
        matches: 匹配结果列表，每个包含：
            - 'source': 数据源名称
            - 'confidence': 置信度分数（0.0-1.0）
            - 'similarity': 相似度分数（0.0-1.0）
        source_weights: 数据源权重配置，None则使用默认配置
        consistency_config: 一致性奖励配置，None则使用默认配置
    
    Returns:
        融合后的置信度分数（0.0-1.0）
    
    Example:
        >>> matches = [
        ...     {'source': 'cursor_ai', 'confidence': 0.92, 'similarity': 0.85},
        ...     {'source': 'gemini_flash', 'confidence': 0.85, 'similarity': 0.78},
        ...     {'source': 'brooks_rule', 'confidence': 0.78, 'similarity': 0.70}
        ... ]
        >>> combined = calculate_combined_confidence(matches)
        >>> print(f"融合置信度: {combined:.2%}")
    """
    if not matches:
        return 0.0
    
    # 加载配置
    if source_weights is None or consistency_config is None:
        config = load_weights_config()
        if source_weights is None:
            source_weights = config.get('source_weights', DEFAULT_SOURCE_WEIGHTS)
        if consistency_config is None:
            consistency_config = config.get('consistency', DEFAULT_CONSISTENCY_CONFIG)
    
    # 1. 加权平均
    weighted_sum = 0.0
    total_weight = 0.0
    
    for match in matches:
        source = match.get('source', 'unknown')
        # 使用confidence或similarity作为基础分数
        confidence = match.get('confidence', match.get('similarity', 0.0))
        weight = source_weights.get(source, 0.1)  # 默认权重0.1
        
        weighted_sum += confidence * weight
        total_weight += weight
    
    # 计算加权平均
    if total_weight > 0:
        weighted_avg = weighted_sum / total_weight
    else:
        weighted_avg = 0.0
    
    # 2. 一致性奖励
    consistency_bonus = 0.0
    if consistency_config.get('enabled', True):
        consistency_bonus = calculate_consistency_bonus(
            matches, 
            consistency_config
        )
    
    # 3. 应用一致性奖励
    final_confidence = weighted_avg * (1 + consistency_bonus)
    
    # 确保在0.0-1.0范围内
    return min(1.0, max(0.0, final_confidence))


def calculate_consistency_bonus(matches: List[Dict], 
                                consistency_config: Optional[Dict] = None) -> float:
    """
    计算一致性奖励
    
    当多个数据源匹配到相似模式时，给予置信度奖励。
    例如：如果3个源都匹配到相似模式，置信度提升20%
    
    Args:
        matches: 匹配结果列表
        consistency_config: 一致性配置
    
    Returns:
        一致性奖励倍数（0.0-0.2，表示0%-20%的提升）
    """
    if not matches or len(matches) < 2:
        return 0.0
    
    if consistency_config is None:
        config = load_weights_config()
        consistency_config = config.get('consistency', DEFAULT_CONSISTENCY_CONFIG)
    
    # 统计不同数据源的数量
    sources = set(match.get('source', 'unknown') for match in matches)
    source_count = len(sources)
    
    # 如果只有1个源，没有一致性奖励
    if source_count < 2:
        return 0.0
    
    # 计算奖励：每个额外源增加bonus_per_source
    bonus_per_source = consistency_config.get('bonus_per_source', 0.1)
    max_bonus = consistency_config.get('max_bonus', 0.2)
    
    # 奖励 = (源数量 - 1) * bonus_per_source，但不超过max_bonus
    bonus = min((source_count - 1) * bonus_per_source, max_bonus)
    
    return bonus


def merge_match_results(matches_by_source: Dict[str, List[Dict]], 
                       top_k: int = 10) -> List[Dict]:
    """
    合并多个数据源的匹配结果
    
    Args:
        matches_by_source: 按数据源分组的匹配结果
            {
                'gemini_flash': [...],
                'cursor_ai': [...],
                'brooks_rule': [...]
            }
        top_k: 返回Top K结果
    
    Returns:
        合并后的匹配结果列表，按融合置信度排序
    """
    # 1. 收集所有匹配结果
    all_matches = []
    
    for source, matches in matches_by_source.items():
        for match in matches:
            # 确保包含source信息
            if 'source' not in match:
                match['source'] = source
            
            all_matches.append(match)
    
    # 2. 按模式分组（如果可能）
    # 这里简化处理，直接对每个匹配计算融合置信度
    # 实际应用中，可能需要先按模式类型分组，然后融合
    
    # 3. 计算每个匹配的融合置信度
    # 注意：这里假设每个匹配是独立的，实际可能需要按模式分组
    for match in all_matches:
        # 如果只有一个匹配，直接使用其置信度
        if len(all_matches) == 1:
            match['combined_confidence'] = match.get('confidence', match.get('similarity', 0.0))
        else:
            # 对于单个匹配，计算其加权置信度
            source = match.get('source', 'unknown')
            config = load_weights_config()
            source_weights = config.get('source_weights', DEFAULT_SOURCE_WEIGHTS)
            weight = source_weights.get(source, 0.1)
            confidence = match.get('confidence', match.get('similarity', 0.0))
            match['combined_confidence'] = confidence * weight
    
    # 4. 按融合置信度排序
    all_matches.sort(key=lambda x: x.get('combined_confidence', 0.0), reverse=True)
    
    # 5. 返回Top K
    return all_matches[:top_k]


def group_matches_by_pattern(matches: List[Dict]) -> Dict[str, List[Dict]]:
    """
    按模式类型分组匹配结果
    
    Args:
        matches: 匹配结果列表
    
    Returns:
        按模式类型分组的匹配结果
    """
    grouped = {}
    
    for match in matches:
        # 尝试从不同字段获取模式类型
        pattern_type = (
            match.get('pattern', {}).get('pattern_type') or
            match.get('pattern_type') or
            match.get('pattern_name') or
            'unknown'
        )
        
        if pattern_type not in grouped:
            grouped[pattern_type] = []
        
        grouped[pattern_type].append(match)
    
    return grouped


def fuse_grouped_matches(grouped_matches: Dict[str, List[Dict]]) -> List[Dict]:
    """
    融合分组后的匹配结果
    
    对于每个模式类型，如果有多个数据源匹配，则融合它们的置信度
    
    Args:
        grouped_matches: 按模式类型分组的匹配结果
    
    Returns:
        融合后的匹配结果列表
    """
    fused_results = []
    
    for pattern_type, matches in grouped_matches.items():
        if len(matches) == 1:
            # 只有一个匹配，直接使用
            match = matches[0].copy()
            match['combined_confidence'] = match.get('confidence', match.get('similarity', 0.0))
            fused_results.append(match)
        else:
            # 多个匹配，融合置信度
            combined_confidence = calculate_combined_confidence(matches)
            
            # 选择置信度最高的匹配作为代表
            best_match = max(matches, key=lambda x: x.get('confidence', x.get('similarity', 0.0)))
            
            # 创建融合结果
            fused_match = best_match.copy()
            fused_match['combined_confidence'] = combined_confidence
            fused_match['source_count'] = len(set(m.get('source', 'unknown') for m in matches))
            fused_match['all_sources'] = [m.get('source', 'unknown') for m in matches]
            
            fused_results.append(fused_match)
    
    # 按融合置信度排序
    fused_results.sort(key=lambda x: x.get('combined_confidence', 0.0), reverse=True)
    
    return fused_results


def main():
    """测试函数"""
    # 模拟匹配结果
    matches = [
        {
            'source': 'cursor_ai',
            'confidence': 0.92,
            'similarity': 0.85,
            'pattern_type': 'triangle',
            'pattern_name': 'Ascending Triangle'
        },
        {
            'source': 'gemini_flash',
            'confidence': 0.85,
            'similarity': 0.78,
            'pattern_type': 'triangle',
            'pattern_name': 'Triangle Pattern'
        },
        {
            'source': 'brooks_rule',
            'confidence': 0.78,
            'similarity': 0.70,
            'pattern_type': 'triangle',
            'pattern_name': 'Triangle Rule'
        }
    ]
    
    print("=" * 80)
    print("多源置信度融合测试")
    print("=" * 80)
    print()
    
    print("输入匹配结果:")
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match['source']}: 置信度={match['confidence']:.2%}, "
              f"相似度={match['similarity']:.2%}")
    print()
    
    # 计算融合置信度
    combined = calculate_combined_confidence(matches)
    print(f"融合置信度: {combined:.2%}")
    print()
    
    # 测试一致性奖励
    consistency_bonus = calculate_consistency_bonus(matches)
    print(f"一致性奖励: {consistency_bonus:.2%}")
    print()
    
    # 测试分组融合
    grouped = group_matches_by_pattern(matches)
    print(f"按模式分组: {len(grouped)} 个模式类型")
    for pattern_type, group_matches in grouped.items():
        print(f"  - {pattern_type}: {len(group_matches)} 个匹配")
    print()
    
    fused = fuse_grouped_matches(grouped)
    print("融合后的结果:")
    for i, result in enumerate(fused, 1):
        print(f"{i}. {result['pattern_name']}: "
              f"融合置信度={result['combined_confidence']:.2%}, "
              f"来源数={result.get('source_count', 1)}")


if __name__ == '__main__':
    main()
