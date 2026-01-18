#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
速度优化版本：减少延迟，加速处理
"""

import sys
from pathlib import Path

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
    print("阶段0完整执行：Gemini Vision分析（速度优化版）")
    print("=" * 80)
    print()
    print("速度优化:")
    print("  - sleep_ms: 200ms（优化：从1000ms减少到200ms）")
    print("  - 预计节省时间: 约13分钟（1000张×0.8秒）")
    print()
    print("预计性能:")
    print("  - API响应时间: 约21秒/张（正常范围：4-47秒）")
    print("  - 总处理时间: 约5.5小时（优化后）")
    print("  - 预计成本: 约 $0.125 USD")
    print()
    
    analyzer = GeminiVisionAnalyzer(
        model='google/gemini-2.5-flash-image',
        sleep_ms=200  # 优化：减少到200ms
    )
    
    print("开始处理全部1000张图片（速度优化版）...")
    print("（可以随时按 Ctrl+C 中断，状态已保存）")
    print()
    
    try:
        result = analyzer.analyze_all(
            resume=True,
            force_reanalyze=False
        )
        
        print()
        print("=" * 80)
        print("处理完成")
        print("=" * 80)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return 0
    except KeyboardInterrupt:
        print("\n\n⚠️  分析被用户中断，状态已保存")
        return 130
    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())

