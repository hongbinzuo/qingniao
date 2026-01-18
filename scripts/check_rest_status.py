#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查休息状态"""

import sys
import re
from pathlib import Path
from datetime import datetime

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
    
    log_content = LOG_FILE.read_text(encoding='utf-8')
    
    print("=" * 80)
    print("休息机制状态检查")
    print("=" * 80)
    print()
    
    # 查找休息触发记录
    rest_triggers = []
    for line in log_content.split('\n'):
        if '达到运行时间限制' in line or '开始休息' in line:
            rest_triggers.append(line)
    
    # 查找恢复记录
    resume_records = []
    for line in log_content.split('\n'):
        if '休息结束' in line or '恢复处理' in line or '新的运行周期开始时间' in line:
            resume_records.append(line)
    
    # 查找最近的休息倒计时
    rest_countdowns = []
    for line in log_content.split('\n'):
        if '休息中... 剩余' in line:
            rest_countdowns.append(line)
    
    # 显示最近的休息触发
    if rest_triggers:
        print("✅ 休息机制已触发:")
        for i, trigger in enumerate(rest_triggers[-3:], 1):
            # 提取时间
            time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', trigger)
            if time_match:
                print(f"  {i}. {time_match.group(1)}: 触发休息")
            else:
                print(f"  {i}. {trigger[:80]}...")
        print()
    
    # 显示恢复记录
    if resume_records:
        print("✅ 已恢复处理:")
        for i, resume in enumerate(resume_records[-3:], 1):
            time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', resume)
            if time_match:
                print(f"  {i}. {time_match.group(1)}: 恢复处理")
            else:
                print(f"  {i}. {resume[:80]}...")
        print()
    else:
        print("⚠️  未找到恢复记录，可能仍在休息中")
        print()
    
    # 显示最近的休息倒计时
    if rest_countdowns:
        print("最近的休息倒计时:")
        for countdown in rest_countdowns[-5:]:
            time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', countdown)
            remaining_match = re.search(r'剩余 (\d+) 分钟', countdown)
            if time_match and remaining_match:
                print(f"  {time_match.group(1)}: 剩余 {remaining_match.group(1)} 分钟")
        print()
    
    # 查找最后一次处理记录
    last_process_lines = []
    for line in reversed(log_content.split('\n')):
        if '开始分析:' in line or '分析完成:' in line:
            last_process_lines.append(line)
            if len(last_process_lines) >= 3:
                break
    
    if last_process_lines:
        print("最近的处理记录（倒序）:")
        for i, line in enumerate(last_process_lines, 1):
            time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
            if time_match:
                action = "开始分析" if "开始分析" in line else "分析完成"
                print(f"  {i}. {time_match.group(1)}: {action}")
        print()
    
    # 判断当前状态
    now = datetime.now()
    if resume_records:
        # 提取最后一次恢复时间
        last_resume_line = resume_records[-1]
        time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', last_resume_line)
        if time_match:
            last_resume_time = datetime.strptime(time_match.group(1), '%Y-%m-%d %H:%M:%S')
            elapsed = (now - last_resume_time).total_seconds() / 3600.0
            remaining = 3.0 - elapsed
            print(f"当前运行周期:")
            print(f"  开始时间: {last_resume_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  已运行: {elapsed:.2f} 小时")
            if remaining > 0:
                next_rest = last_resume_time + timedelta(hours=3)
                print(f"  距离下次休息: {remaining:.2f} 小时 ({remaining*60:.0f} 分钟)")
                print(f"  预计下次休息: {next_rest.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"  ⚠️  已运行超过3小时，应该已触发休息")
    
    print()
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    from datetime import timedelta
    sys.exit(main())



