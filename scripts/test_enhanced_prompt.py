#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强Prompt效果（对比新旧Prompt）
"""

import sys
from pathlib import Path
import json

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.gemini_vision_analyzer import GeminiVisionAnalyzer

def analyze_sample_images(limit=5):
    """分析几张样本图片，检查增强Prompt效果"""
    
    print("=" * 80)
    print("测试增强Prompt效果")
    print("=" * 80)
    print()
    
    analyzer = GeminiVisionAnalyzer(
        model='google/gemini-2.5-flash-image',
        sleep_ms=200
    )
    
    # 获取几张还未处理的图片（或使用失败的图片重新测试）
    image_paths = sorted(list(analyzer.images_dir.glob('*.png')))[:limit]
    
    print(f"测试图片: {len(image_paths)} 张")
    print()
    
    results = []
    for i, img_path in enumerate(image_paths, 1):
        print(f"[{i}/{len(image_paths)}] 分析: {img_path.name}")
        try:
            result = analyzer.analyze_single_image(img_path, force_reanalyze=True)
            results.append(result)
            
            # 检查结果完整性
            res = result.get('result', {})
            
            print(f"  ✅ 完成")
            print(f"     - chart_overview: {'✅' if 'chart_overview' in res else '❌'}")
            print(f"     - complete_price_path: {'✅' if 'complete_price_path' in res else '❌'}")
            print(f"     - complete_narrative: {'✅' if 'complete_narrative' in res else '❌'}")
            print(f"     - patterns: {len(res.get('patterns', []))}")
            print(f"     - trading_signals: {len(res.get('trading_signals', []))}")
            print()
            
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            print()
            continue
    
    # 分析结果
    print("=" * 80)
    print("结果分析")
    print("=" * 80)
    print()
    
    total = len(results)
    with_chart_overview = sum(1 for r in results if 'chart_overview' in r.get('result', {}))
    with_price_path = sum(1 for r in results if 'complete_price_path' in r.get('result', {}))
    with_narrative = sum(1 for r in results if 'complete_narrative' in r.get('result', {}))
    
    avg_patterns = sum(len(r.get('result', {}).get('patterns', [])) for r in results) / total if total > 0 else 0
    avg_signals = sum(len(r.get('result', {}).get('trading_signals', [])) for r in results) / total if total > 0 else 0
    
    print(f"总测试数: {total}")
    print(f"  - 有chart_overview: {with_chart_overview}/{total} ({with_chart_overview/total*100:.1f}%)")
    print(f"  - 有complete_price_path: {with_price_path}/{total} ({with_price_path/total*100:.1f}%)")
    print(f"  - 有complete_narrative: {with_narrative}/{total} ({with_narrative/total*100:.1f}%)")
    print(f"  - 平均patterns: {avg_patterns:.1f}/张")
    print(f"  - 平均signals: {avg_signals:.1f}/张")
    print()
    
    # 评估
    print("=" * 80)
    print("评估")
    print("=" * 80)
    print()
    
    if with_chart_overview == total and with_price_path == total and with_narrative == total:
        print("✅ 增强Prompt效果显著！")
        print("   - 所有新字段都被提取")
        print("   - 建议：重新运行全部1000张图片以获取完整数据")
        return True
    elif with_chart_overview >= total * 0.8 and with_narrative >= total * 0.8:
        print("⚠️  增强Prompt效果较好")
        print("   - 大部分新字段被提取")
        print("   - 建议：可以重新运行，但可能需要进一步优化Prompt")
        return True
    else:
        print("❌ 增强Prompt效果不足")
        print("   - 部分新字段缺失")
        print("   - 建议：进一步优化Prompt后再运行")
        return False

def main():
    try:
        should_rerun = analyze_sample_images(limit=5)
        
        print()
        print("=" * 80)
        if should_rerun:
            print("建议: 重新运行全部1000张图片")
            print()
            print("步骤:")
            print("  1. 清空现有输出: python scripts/abu_reset_stage0.py")
            print("  2. 使用增强Prompt重新处理: python scripts/abu_optimize_speed.py")
        else:
            print("建议: 进一步优化Prompt后再运行")
        
        return 0
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
