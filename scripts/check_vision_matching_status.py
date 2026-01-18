#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查视觉匹配状态
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


def main():
    print("=" * 80)
    print("视觉匹配状态检查")
    print("=" * 80)
    print()
    
    # 加载模式库
    print("1. 加载模式库...")
    lib = UnifiedPatternLibrary('abu')
    lib.load_all_patterns()
    
    print(f"   总计: {len(lib.patterns)} 个模式")
    print()
    
    # 检查有图片的模式
    print("2. 检查模式图片...")
    
    patterns_with_image = []
    patterns_without_image = []
    
    for pattern in lib.patterns.values():
        if hasattr(pattern, 'image_path') and pattern.image_path:
            image_path = Path(pattern.image_path)
            if image_path.exists() or (ROOT / pattern.image_path).exists():
                patterns_with_image.append(pattern)
            else:
                patterns_without_image.append(pattern)
        else:
            patterns_without_image.append(pattern)
    
    print(f"   有图片且文件存在: {len(patterns_with_image)} 个")
    print(f"   无图片或文件不存在: {len(patterns_without_image)} 个")
    print()
    
    # 按数据源统计
    print("3. 按数据源统计...")
    
    gemini_with_image = [p for p in patterns_with_image if p.source == 'gemini_flash']
    cursor_with_image = [p for p in patterns_with_image if p.source == 'cursor_ai']
    brooks_with_image = [p for p in patterns_with_image if p.source == 'brooks_rule']
    
    print(f"   Gemini Flash: {len(gemini_with_image)}/{lib.stats['gemini_flash']} 个有图片")
    print(f"   Cursor AI: {len(cursor_with_image)}/{lib.stats['cursor_ai']} 个有图片")
    print(f"   Brooks规则: {len(brooks_with_image)}/{lib.stats['brooks_rule']} 个有图片")
    print()
    
    # 检查图片路径
    print("4. 检查图片路径示例...")
    if patterns_with_image:
        for i, pattern in enumerate(patterns_with_image[:5], 1):
            image_path = Path(pattern.image_path) if pattern.image_path else None
            if not image_path or not image_path.exists():
                image_path = ROOT / pattern.image_path if pattern.image_path else None
            
            exists = image_path.exists() if image_path else False
            print(f"   {i}. {pattern.pattern_name} ({pattern.source})")
            print(f"      路径: {pattern.image_path}")
            print(f"      存在: {'✓' if exists else '✗'}")
    else:
        print("   [WARN] 没有找到有图片的模式")
    print()
    
    # 结论
    print("=" * 80)
    print("结论")
    print("=" * 80)
    
    if len(patterns_with_image) == 0:
        print("❌ 当前没有模式包含图片，视觉匹配功能无法使用")
        print()
        print("建议:")
        print("  1. 确保模式库中的模式有image_path字段")
        print("  2. 确保图片文件存在于指定路径")
        print("  3. 如果使用Gemini Flash模式，图片应该在data/abu/images/目录")
    elif len(patterns_with_image) < len(lib.patterns) * 0.1:
        print(f"⚠️  只有 {len(patterns_with_image)}/{len(lib.patterns)} 个模式有图片")
        print("  视觉匹配功能可用，但覆盖率较低")
    else:
        print(f"✅ 有 {len(patterns_with_image)}/{len(lib.patterns)} 个模式有图片")
        print("  视觉匹配功能可用")
    
    print()
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
