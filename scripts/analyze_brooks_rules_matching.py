#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Brooks规则匹配情况

检查为什么Brooks规则（6777个）没有匹配到结果。
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from abu.unified_pattern_library import UnifiedPatternLibrary
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def analyze_brooks_rules():
    """分析Brooks规则"""
    print("=" * 80)
    print("Brooks规则匹配分析")
    print("=" * 80)
    print()
    
    # 加载模式库
    print("1. 加载模式库...")
    library = UnifiedPatternLibrary('abu')
    library.load_all_patterns()
    
    print(f"   总计: {len(library.patterns)} 个模式")
    print(f"   Gemini Flash: {library.stats['gemini_flash']} 个")
    print(f"   Cursor AI: {library.stats['cursor_ai']} 个")
    print(f"   Brooks规则: {library.stats['brooks_rule']} 个")
    print()
    
    # 分析Brooks规则
    print("2. 分析Brooks规则...")
    brooks_patterns = library.get_patterns_by_source('brooks_rule')
    print(f"   找到 {len(brooks_patterns)} 个Brooks规则")
    print()
    
    if len(brooks_patterns) == 0:
        print("   [ERROR] 没有找到Brooks规则！")
        return 1
    
    # 分析Brooks规则的特征
    print("3. 分析Brooks规则特征...")
    
    # 统计置信度分布
    confidence_dist = {}
    pattern_types = {}
    has_features = 0
    no_features = 0
    
    for pattern in brooks_patterns[:100]:  # 只分析前100个
        # 置信度
        conf = pattern.confidence
        conf_range = f"{int(conf * 10) * 10}%"
        confidence_dist[conf_range] = confidence_dist.get(conf_range, 0) + 1
        
        # 模式类型
        ptype = pattern.pattern_type
        pattern_types[ptype] = pattern_types.get(ptype, 0) + 1
        
        # 特征
        if pattern.structured_features:
            has_features += 1
        else:
            no_features += 1
    
    print(f"   置信度分布（前100个样本）:")
    for conf_range in sorted(confidence_dist.keys()):
        print(f"     {conf_range}: {confidence_dist[conf_range]}个")
    print()
    
    print(f"   模式类型（前100个样本）:")
    for ptype, count in sorted(pattern_types.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"     {ptype}: {count}个")
    print()
    
    print(f"   特征完整性:")
    print(f"     有特征: {has_features}个")
    print(f"     无特征: {no_features}个")
    print()
    
    # 检查特征结构
    print("4. 检查特征结构...")
    sample_patterns = brooks_patterns[:5]
    for i, pattern in enumerate(sample_patterns, 1):
        print(f"   样本 {i}: {pattern.pattern_name}")
        print(f"     模式类型: {pattern.pattern_type}")
        print(f"     置信度: {pattern.confidence:.2%}")
        print(f"     特征: {type(pattern.structured_features).__name__}")
        if pattern.structured_features:
            if isinstance(pattern.structured_features, dict):
                print(f"     特征键: {list(pattern.structured_features.keys())[:5]}")
            else:
                print(f"     特征内容: {str(pattern.structured_features)[:100]}...")
        else:
            print(f"     特征: 无")
        print()
    
    # 测试匹配
    print("5. 测试匹配...")
    test_features = {
        'pattern_type': 'unknown',
        'direction': 'long',
        'trend': 'bullish',
        'trend_strength': 0.02,
        'kline_features': [],
        'volatility': 0.01,
        'market_conditions': {
            'trend_strength': 'weak',
            'volatility': 'low',
            'trend_direction': 'bullish'
        }
    }
    
    matches = []
    for pattern in brooks_patterns[:100]:
        similarity = library._calculate_similarity(test_features, pattern.structured_features)
        if similarity > 0:
            matches.append({
                'pattern': pattern,
                'similarity': similarity
            })
    
    matches.sort(key=lambda x: x['similarity'], reverse=True)
    
    print(f"   测试匹配结果（前100个Brooks规则）:")
    print(f"     找到 {len(matches)} 个匹配")
    if matches:
        print(f"     Top 5 匹配:")
        for i, match in enumerate(matches[:5], 1):
            print(f"       {i}. {match['pattern'].pattern_name}")
            print(f"          相似度: {match['similarity']:.2%}")
            print(f"          置信度: {match['pattern'].confidence:.2%}")
    else:
        print(f"     [WARN] 没有找到匹配！")
        print(f"     可能原因:")
        print(f"       - 特征结构不匹配")
        print(f"       - 相似度计算逻辑需要优化")
        print(f"       - Brooks规则的特征格式与查询特征格式不一致")
    print()
    
    # 建议
    print("6. 改进建议...")
    print("-" * 80)
    
    if len(matches) == 0:
        print("  ⚠️  Brooks规则匹配失败，建议:")
        print("     1. 检查Brooks规则的特征标准化逻辑")
        print("     2. 优化相似度计算算法，使其能匹配Brooks规则的特征格式")
        print("     3. 检查Brooks规则的特征提取是否正确")
        print("     4. 考虑为Brooks规则创建专门的特征匹配逻辑")
    
    if no_features > has_features:
        print("  ⚠️  大量Brooks规则缺少特征，建议:")
        print("     1. 检查Brooks规则的加载逻辑")
        print("     2. 确保特征提取正确执行")
        print("     3. 检查数据库中的Brooks规则数据完整性")
    
    print()
    
    print("=" * 80)
    print("分析完成！")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = analyze_brooks_rules()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
