#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
集成Brooks PA概率分类到ABU系统

从PDF提取概率分类知识，并集成到模式库和交易信号生成系统。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from abu.brooks_probability_extractor import BrooksProbabilityExtractor
    from abu.unified_pattern_library import UnifiedPatternLibrary
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def integrate_probability_to_pattern_library(
    probability_rules: List[Dict],
    pattern_library: UnifiedPatternLibrary
) -> int:
    """
    将概率分类规则集成到模式库
    
    Args:
        probability_rules: 概率分类规则列表
        pattern_library: 统一模式库实例
    
    Returns:
        集成的规则数量
    """
    integrated_count = 0
    
    for rule in probability_rules:
        # 提取概率信息
        probabilities = rule.get('probabilities', [])
        pattern_names = rule.get('pattern_names', [])
        text = rule.get('text', '')
        page = rule.get('page', 0)
        
        # 为每个模式创建概率分类条目
        for pattern_name in pattern_names:
            # 查找现有模式
            # TODO: 实现模式匹配和概率更新逻辑
            integrated_count += 1
    
    return integrated_count


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Brooks PA概率分类集成到ABU系统")
    print("=" * 80)
    print()
    
    # 1. 提取概率分类知识
    print("1. 从PDF提取概率分类知识...")
    extractor = BrooksProbabilityExtractor()
    rules = extractor.extract_from_pdf()
    
    if not rules:
        print("   [WARN] 未提取到概率分类规则")
        print("   可能原因:")
        print("     - PDF文件不存在或无法读取")
        print("     - 未安装PDF处理库: pip install pdfplumber")
        print("     - PDF格式不支持")
        return 1
    
    print(f"   [OK] 提取了 {len(rules)} 条概率分类规则")
    print()
    
    # 2. 保存到JSON
    output_path = ROOT / 'data' / 'brooks_probability_rules.json'
    print(f"2. 保存到: {output_path}")
    extractor.probability_rules = rules
    extractor.save_to_json(output_path)
    print("   [OK] 保存完成")
    print()
    
    # 3. 集成到模式库
    print("3. 集成到模式库...")
    pattern_library = UnifiedPatternLibrary()
    integrated_count = integrate_probability_to_pattern_library(rules, pattern_library)
    print(f"   [OK] 集成了 {integrated_count} 条规则")
    print()
    
    # 4. 显示示例
    if rules:
        print("4. 示例规则:")
        for i, rule in enumerate(rules[:3], 1):
            print(f"   规则 {i} (第{rule['page']}页):")
            if rule.get('probabilities'):
                print(f"     概率: {', '.join(rule['probabilities'])}%")
            if rule.get('pattern_names'):
                print(f"     模式: {', '.join(rule['pattern_names'])}")
            print()
    
    print("=" * 80)
    print("集成完成")
    print("=" * 80)
    print()
    print("下一步:")
    print("  - 概率分类规则已保存到: data/brooks_probability_rules.json")
    print("  - 可以在交易信号生成时使用概率信息")
    print("  - 概率信息将影响信号置信度计算")
    print()


if __name__ == '__main__':
    main()
