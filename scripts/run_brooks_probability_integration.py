#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行Brooks PA概率分类集成

完整流程：
1. 从PDF提取概率分类知识
2. 保存到JSON
3. 集成到模式库
4. 测试概率信息是否正确加载
"""

import sys
from pathlib import Path

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


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("Brooks PA概率分类集成")
    print("=" * 80)
    print()
    
    # 1. 提取概率分类知识
    print("1. 从PDF提取概率分类知识...")
    extractor = BrooksProbabilityExtractor()
    
    # 检查PDF文件
    if not extractor.pdf_path.exists():
        print(f"   [WARN] PDF文件不存在: {extractor.pdf_path}")
        print("   请确保PDF文件在Downloads文件夹中")
        print("   文件名: 'Brooks Price Action概率.pdf'")
        return 1
    
    print(f"   PDF文件: {extractor.pdf_path}")
    
    rules = extractor.extract_from_pdf()
    extractor.probability_rules = rules
    
    if not rules:
        print("   [WARN] 未提取到概率分类规则")
        print("   可能原因:")
        print("     - PDF格式不支持")
        print("     - 未安装PDF处理库: pip install pdfplumber")
        print("     - PDF内容不包含概率信息")
        return 1
    
    print(f"   [OK] 提取了 {len(rules)} 条概率分类规则")
    print()
    
    # 2. 保存到JSON
    output_path = ROOT / 'data' / 'brooks_probability_rules.json'
    print(f"2. 保存到: {output_path}")
    extractor.save_to_json(output_path)
    print("   [OK] 保存完成")
    print()
    
    # 3. 测试模式库集成
    print("3. 测试模式库集成...")
    pattern_library = UnifiedPatternLibrary()
    
    # 检查概率规则是否加载
    if pattern_library.probability_rules:
        print(f"   [OK] 概率规则已加载: {len(pattern_library.probability_rules)} 条")
        print("   示例规则:")
        for i, (pattern_name, rule) in enumerate(list(pattern_library.probability_rules.items())[:3], 1):
            print(f"     {i}. {pattern_name}: {rule.get('probability')}%")
    else:
        print("   [WARN] 概率规则未加载，可能需要重新运行")
    print()
    
    # 4. 显示提取的规则统计
    if rules:
        print("4. 提取规则统计:")
        
        # 统计概率分布
        prob_dist = {}
        pattern_count = {}
        
        for rule in rules:
            prob = rule.get('probability')
            pattern = rule.get('pattern_name', 'Unknown')
            
            if prob:
                prob_range = f"{(prob//10)*10}-{(prob//10)*10+9}%"
                prob_dist[prob_range] = prob_dist.get(prob_range, 0) + 1
            
            if pattern:
                pattern_count[pattern] = pattern_count.get(pattern, 0) + 1
        
        print("   概率分布:")
        for prob_range in sorted(prob_dist.keys()):
            print(f"     {prob_range}: {prob_dist[prob_range]} 条")
        
        print("   模式统计:")
        for pattern, count in sorted(pattern_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"     {pattern}: {count} 条")
        print()
    
    print("=" * 80)
    print("集成完成")
    print("=" * 80)
    print()
    print("下一步:")
    print("  - 概率分类规则已保存到: data/brooks_probability_rules.json")
    print("  - 模式库已加载概率规则")
    print("  - 可以在交易信号生成时使用概率信息")
    print("  - 运行交易计划生成脚本测试概率集成效果")
    print()


if __name__ == '__main__':
    main()
