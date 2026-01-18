#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分析处理时间趋势"""

import sys
import json
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
OUTPUT_FILE = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'
LOG_FILE = ROOT / 'outputs' / 'abu_gemini' / 'gemini_analysis.log'

def parse_log_time(log_line: str) -> tuple:
    """从日志行提取时间和耗时"""
    # 格式: 2026-01-11 01:48:48 [INFO] 分析完成: page_0087_img_01_clip.png (耗时: 40.85s, 成本: $0.000125)
    time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', log_line)
    elapsed_match = re.search(r'耗时: ([\d.]+)s', log_line)
    
    if time_match and elapsed_match:
        try:
            time_str = time_match.group(1)
            elapsed = float(elapsed_match.group(1))
            return time_str, elapsed
        except:
            pass
    return None, None

def main():
    print("=" * 80)
    print("处理时间趋势分析")
    print("=" * 80)
    print()
    
    # 从输出文件分析
    if OUTPUT_FILE.exists():
        lines = OUTPUT_FILE.read_text(encoding='utf-8').strip().split('\n')
        records = []
        for line in lines:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if 'elapsed_seconds' in record:
                    records.append({
                        'image': Path(record.get('image', '')).name,
                        'elapsed': record.get('elapsed_seconds', 0),
                        'page': record.get('page', 0)
                    })
            except:
                continue
        
        if records:
            # 按page排序
            records.sort(key=lambda x: x['page'])
            
            print(f"📊 从输出文件分析（共 {len(records)} 条记录）:")
            print()
            
            # 最近20条的时间
            recent = records[-20:] if len(records) >= 20 else records
            print(f"最近 {len(recent)} 张图片的处理时间:")
            for i, r in enumerate(recent, 1):
                print(f"  {i:2d}. {r['image']:30s} {r['elapsed']:6.2f}s")
            
            print()
            
            # 计算趋势
            if len(records) >= 20:
                first_10 = records[:10]
                last_10 = records[-10:]
                
                avg_first = sum(r['elapsed'] for r in first_10) / len(first_10)
                avg_last = sum(r['elapsed'] for r in last_10) / len(last_10)
                
                print(f"📈 时间趋势分析:")
                print(f"   前10张平均: {avg_first:.2f}s")
                print(f"   后10张平均: {avg_last:.2f}s")
                change = avg_last - avg_first
                change_pct = (change / avg_first * 100) if avg_first > 0 else 0
                print(f"   变化: {change:+.2f}s ({change_pct:+.1f}%)")
                
                if change < -5:
                    print(f"   ✅ 处理速度明显提升！")
                elif change < -2:
                    print(f"   ✅ 处理速度有所提升")
                elif change > 5:
                    print(f"   ⚠️  处理速度变慢")
                else:
                    print(f"   ➡️  处理速度基本稳定")
                print()
    
    # 从日志文件分析
    if LOG_FILE.exists():
        print(f"📋 从日志文件分析（最近20条）:")
        print()
        
        log_lines = LOG_FILE.read_text(encoding='utf-8').strip().split('\n')
        recent_logs = [l for l in log_lines if '分析完成' in l][-20:]
        
        times = []
        for line in recent_logs:
            time_str, elapsed = parse_log_time(line)
            if time_str and elapsed:
                times.append({
                    'time': time_str,
                    'elapsed': elapsed
                })
        
        if times:
            print("最近处理时间:")
            for i, t in enumerate(times[-10:], 1):
                print(f"  {i:2d}. {t['time']} - {t['elapsed']:6.2f}s")
            
            if len(times) >= 10:
                first_5_avg = sum(t['elapsed'] for t in times[:5]) / 5
                last_5_avg = sum(t['elapsed'] for t in times[-5:]) / 5
                print()
                print(f"   前5条平均: {first_5_avg:.2f}s")
                print(f"   后5条平均: {last_5_avg:.2f}s")
                change = last_5_avg - first_5_avg
                change_pct = (change / first_5_avg * 100) if first_5_avg > 0 else 0
                print(f"   变化: {change:+.2f}s ({change_pct:+.1f}%)")
    
    print()
    print("=" * 80)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())



