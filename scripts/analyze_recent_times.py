#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析最近处理时间"""

import sys
import re
from pathlib import Path

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / 'outputs' / 'abu_gemini' / 'gemini_analysis.log'

def main():
    if not LOG_FILE.exists():
        print("日志文件不存在")
        return 1
    
    log_lines = LOG_FILE.read_text(encoding='utf-8').strip().split('\n')
    
    # 提取所有"分析完成"的记录
    completed = []
    for line in log_lines:
        if '分析完成' in line and '耗时' in line:
            match = re.search(r'分析完成: (page_\d+_img_\d+_clip\.png).*耗时: ([\d.]+)s', line)
            if match:
                page_name = match.group(1)
                elapsed = float(match.group(2))
                completed.append((page_name, elapsed))
    
    if not completed:
        print("未找到处理记录")
        return 1
    
    print("=" * 80)
    print("最近处理时间分析")
    print("=" * 80)
    print()
    
    # 显示最近20条
    recent = completed[-20:]
    print(f"最近 {len(recent)} 张图片的处理时间:")
    print()
    for i, (name, elapsed) in enumerate(recent, 1):
        status = "⚡" if elapsed < 30 else "✅" if elapsed < 50 else "⚠️" if elapsed < 100 else "🐌"
        print(f"  {i:2d}. {status} {name:35s} {elapsed:6.2f}s")
    
    print()
    
    # 分析最近的变化
    if len(completed) >= 15:
        # 最近5张
        last_5 = completed[-5:]
        # 之前的5张
        prev_5 = completed[-10:-5] if len(completed) >= 10 else completed[-5:]
        
        avg_last_5 = sum(e for _, e in last_5) / len(last_5)
        avg_prev_5 = sum(e for _, e in prev_5) / len(prev_5)
        
        print(f"📊 时间对比:")
        print(f"   最近5张平均: {avg_last_5:.2f}s")
        print(f"   之前5张平均: {avg_prev_5:.2f}s")
        change = avg_last_5 - avg_prev_5
        change_pct = (change / avg_prev_5 * 100) if avg_prev_5 > 0 else 0
        print(f"   变化: {change:+.2f}s ({change_pct:+.1f}%)")
        print()
        
        if change < -5:
            print("   ✅ 处理速度明显提升！")
        elif change < -2:
            print("   ✅ 处理速度有所提升")
        elif change > 5:
            print("   ⚠️  处理速度变慢")
        else:
            print("   ➡️  处理速度基本稳定")
        print()
        
        # 显示最近5张的详细时间
        print(f"最近5张详细时间:")
        for name, elapsed in last_5:
            print(f"   {name:35s} {elapsed:6.2f}s")
    
    print()
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())



