#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查新进程运行周期时间"""

import sys
from datetime import datetime, timedelta

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def main():
    # 新进程启动时间（从日志中获取）
    session_start = datetime(2026, 1, 11, 2, 29, 17)
    now = datetime.now()
    elapsed = (now - session_start).total_seconds() / 3600.0
    remaining = 3.0 - elapsed
    
    print("=" * 80)
    print("新进程运行周期检查（包含运行/休息机制）")
    print("=" * 80)
    print()
    print(f"新进程启动时间: {session_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"已运行: {elapsed:.2f} 小时")
    print()
    
    if remaining > 0:
        next_rest_time = session_start + timedelta(hours=3)
        print(f"距离3小时限制: {remaining:.2f} 小时 ({remaining*60:.0f} 分钟)")
        print(f"预计第一次休息时间: {next_rest_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        print("机制说明:")
        print(f"  - 运行满3小时后，会自动保存状态并休息1小时")
        print(f"  - 休息期间会输出倒计时（每5分钟一次）")
        print(f"  - 休息结束后自动恢复处理")
    else:
        print("已运行超过3小时，应该已触发休息机制")
        print("请检查日志确认休息状态")
    
    print()
    print("=" * 80)
    return 0

if __name__ == '__main__':
    sys.exit(main())



