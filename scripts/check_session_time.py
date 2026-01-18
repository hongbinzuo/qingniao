#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查当前运行周期时间"""

import sys
from datetime import datetime

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def main():
    # 从进度显示中获取启动时间
    start_time_str = '2026-01-11 00:25:54'  # 从show_progress.py输出中获取
    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    elapsed = (now - start_time).total_seconds() / 3600.0
    
    print("=" * 80)
    print("运行周期时间检查")
    print("=" * 80)
    print()
    print(f"启动时间: {start_time_str}")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"已运行: {elapsed:.2f} 小时")
    print()
    
    if elapsed < 3.0:
        remaining = 3.0 - elapsed
        print(f"距离3小时限制还有: {remaining:.2f} 小时 ({remaining*60:.0f} 分钟)")
        print()
        print("建议:")
        print("  当前进程是旧代码启动的，不包含运行/休息机制")
        print("  如果需要立即应用新机制，可以重启进程（状态已保存，会从断点继续）")
    else:
        print("已运行超过3小时")
        print()
        print("建议:")
        print("  当前进程已运行较长时间，建议重启以应用新机制")
    
    print()
    print("=" * 80)
    return 0

if __name__ == '__main__':
    sys.exit(main())



