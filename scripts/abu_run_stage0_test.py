#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段0测试：Gemini Vision分析（小批量测试）
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

# 导入分析器
from abu.gemini_vision_analyzer import GeminiVisionAnalyzer
import json

def main():
    print("=" * 80)
    print("阶段0测试：Gemini Vision分析（10张图片测试）")
    print("=" * 80)
    print()
    
    # 创建分析器
    try:
        analyzer = GeminiVisionAnalyzer(
            model='google/gemini-2.5-flash-image',
            sleep_ms=1000  # 1秒间隔，控制成本
        )
    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        return 1
    
    # 测试分析10张图片
    print("开始测试分析（10张图片）...")
    print()
    
    try:
        result = analyzer.analyze_all(
            resume=True,  # 支持断点续传
            limit=10,     # 只处理10张
            force_reanalyze=False
        )
        
        print()
        print("=" * 80)
        print("测试结果:")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print()
        
        # 检查结果
        if 'error' in result:
            print(f"❌ 测试失败: {result['error']}")
            return 1
        
        completed = result.get('completed', 0)
        failed = result.get('failed', 0)
        total_cost = result.get('total_cost_usd', 0)
        
        print(f"✅ 测试完成:")
        print(f"   - 已完成: {completed}")
        print(f"   - 失败: {failed}")
        print(f"   - 成本: ${total_cost:.6f}")
        print()
        
        if failed == 0 and completed > 0:
            print("✅ 测试通过！可以继续处理全部1000张图片")
            print()
            print("下一步:")
            print("  python -m src.abu.gemini_vision_analyzer --model google/gemini-2.5-flash-image")
            return 0
        else:
            print("⚠️ 测试有问题，请检查日志")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断，状态已保存")
        print("可以继续运行: python -m src.abu.gemini_vision_analyzer --model google/gemini-2.5-flash-image --resume")
        return 130
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

