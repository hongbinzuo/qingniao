#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段0完整执行：Gemini Vision分析全部1000张图片

注意：
- 这将需要较长时间（预计2-3小时，取决于API响应速度）
- 支持断点续传，可以随时中断（Ctrl+C）
- 成本约 $0.125 USD
"""

import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.gemini_vision_analyzer import GeminiVisionAnalyzer
import json

def main():
    print("=" * 80)
    print("阶段0完整执行：Gemini Vision分析全部1000张图片")
    print("=" * 80)
    print()
    print("注意事项:")
    print("  - 预计耗时：2-3小时（取决于API响应速度）")
    print("  - 预计成本：约 $0.125 USD")
    print("  - 支持断点续传：可以随时中断（Ctrl+C），下次运行自动继续")
    print("  - 输出文件：outputs/abu_gemini_annotations_enhanced.jsonl")
    print("  - 状态文件：outputs/abu_gemini_analysis_state.json")
    print()
    
    # 检查是否已有处理结果
    output_file = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'
    if output_file.exists():
        # 统计已处理数量
        try:
            with output_file.open('r', encoding='utf-8') as f:
                processed = sum(1 for line in f if line.strip())
            print(f"⚠️  发现已有处理结果：{processed} 条记录")
            print("   将自动跳过已处理的图片（断点续传）")
            print()
        except Exception:
            pass
    
    # 创建分析器
    try:
        analyzer = GeminiVisionAnalyzer(
            model='google/gemini-2.5-flash-image',
            sleep_ms=200  # 200ms间隔（优化：从1000ms减少到200ms，可节省约13分钟）
        )
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return 1
    
    # 执行完整分析（全部1000张）
    print("开始分析全部1000张图片...")
    print("（可以随时按 Ctrl+C 中断，状态已保存）")
    print()
    
    try:
        result = analyzer.analyze_all(
            resume=True,  # 支持断点续传
            force_reanalyze=False  # 不强制重新分析已处理的
        )
        
        print()
        print("=" * 80)
        print("阶段0完成：分析结果统计")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 检查结果
        if 'error' in result:
            print(f"❌ 分析失败: {result['error']}")
            return 1
        
        completed = result.get('completed', 0)
        failed = result.get('failed', 0)
        skipped = result.get('skipped', 0)
        total = result.get('total_images', 0)
        total_cost = result.get('total_cost_usd', 0)
        
        print(f"✅ 分析完成:")
        print(f"   - 总图片数: {total}")
        print(f"   - 已完成: {completed}")
        print(f"   - 跳过: {skipped}")
        print(f"   - 失败: {failed}")
        print(f"   - 总成本: ${total_cost:.6f}")
        print()
        
        if failed == 0 and completed + skipped >= total * 0.95:  # 95%以上完成
            print("✅ 阶段0完成！输出文件:")
            print(f"   {result.get('output_file')}")
            print()
            print("下一步:")
            print("  1. 检查输出质量: python scripts/abu_check_stage0_output.py")
            print("  2. 解析并更新模式库: python scripts/abu_parse_gemini_output.py")
            return 0
        else:
            print(f"⚠️  完成度: {(completed + skipped) / total * 100:.1f}%")
            if failed > 0:
                print(f"   - 失败数量: {failed}，请检查日志")
            print()
            print("可以继续运行以完成剩余图片:")
            print("  python -m src.abu.gemini_vision_analyzer --model google/gemini-2.5-flash-image --resume")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  分析被用户中断，状态已保存")
        print("可以继续运行:")
        print("  python -m src.abu.gemini_vision_analyzer --model google/gemini-2.5-flash-image --resume")
        return 130
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

