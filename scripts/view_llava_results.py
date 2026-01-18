#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看 llava 图片模式识别结果
"""

import sys
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

# 添加 src 到路径
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from detailed_logger import get_detailed_logger

def main():
    logger = get_detailed_logger('view_llava_results')
    logger.log_startup()
    
    # 1. 检查 patterns.json
    patterns_file = Path('data/abu/patterns.json')
    if patterns_file.exists():
        logger.info(f"读取 patterns.json: {patterns_file}")
        try:
            with open(patterns_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
            
            print(f"\n{'='*80}")
            print(f"📊 Patterns.json 统计信息")
            print(f"{'='*80}")
            print(f"总记录数: {len(patterns)}")
            
            # 统计 pattern_type
            pattern_types = Counter(p.get('pattern_type', 'unknown') for p in patterns)
            print(f"\n模式类型分布:")
            for ptype, count in pattern_types.most_common():
                print(f"  {ptype}: {count}")
            
            # 统计有 llava 分类的记录
            llava_classified = [p for p in patterns if p.get('pattern_type') and p.get('pattern_type') != 'other']
            print(f"\n已分类记录数: {len(llava_classified)} (非 'other' 类型)")
            
            # 显示最近分类的记录
            if llava_classified:
                print(f"\n最近分类的记录 (前10条):")
                for i, p in enumerate(llava_classified[:10], 1):
                    print(f"\n  {i}. ID: {p.get('id')}")
                    print(f"     模式名称: {p.get('pattern_name', 'N/A')}")
                    print(f"     模式类型: {p.get('pattern_type', 'N/A')}")
                    print(f"     来源页面: {p.get('source_page', 'N/A')}")
                    print(f"     图片路径: {Path(p.get('image_path', '')).name if p.get('image_path') else 'N/A'}")
                    if p.get('timeframe_hint'):
                        print(f"     时间周期: {p.get('timeframe_hint')}")
                    if p.get('direction'):
                        print(f"     方向: {p.get('direction')}")
                    if p.get('confidence'):
                        print(f"     置信度: {p.get('confidence')}")
            
        except Exception as e:
            logger.error(f"读取 patterns.json 失败", error=e)
            print(f"❌ 读取失败: {e}")
    
    # 2. 查找可能的输出文件
    logger.info("查找 llava 输出文件")
    output_dirs = [Path('outputs'), Path('data/abu'), Path('data')]
    found_files = []
    
    for output_dir in output_dirs:
        if output_dir.exists():
            for file_path in output_dir.rglob('*'):
                if file_path.is_file():
                    name_lower = file_path.name.lower()
                    if 'llava' in name_lower or ('classify' in name_lower and 'pattern' in name_lower):
                        found_files.append({
                            'path': str(file_path),
                            'size': file_path.stat().st_size,
                            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        })
    
    if found_files:
        print(f"\n{'='*80}")
        print(f"📁 找到的 llava 相关输出文件:")
        print(f"{'='*80}")
        for f in found_files:
            print(f"\n  路径: {f['path']}")
            print(f"  大小: {f['size']} bytes")
            print(f"  修改时间: {f['modified']}")
            
            # 尝试读取 JSONL 文件
            if f['path'].endswith('.jsonl'):
                try:
                    with open(f['path'], 'r', encoding='utf-8') as file:
                        lines = file.readlines()
                        print(f"  行数: {len(lines)}")
                        if lines:
                            sample = json.loads(lines[0])
                            print(f"  示例记录: {json.dumps(sample, ensure_ascii=False, indent=2)[:200]}...")
                except Exception as e:
                    print(f"  读取失败: {e}")
    else:
        print(f"\n⚠️ 未找到明确的 llava 输出文件")
        print(f"   可能结果已直接更新到 patterns.json 中")
    
    # 3. 检查日志文件
    logger.info("检查日志文件")
    log_file = Path('data/logs') / f"logs_{datetime.now().strftime('%Y%m%d')}.jsonl"
    if log_file.exists():
        print(f"\n{'='*80}")
        print(f"📝 今日日志文件: {log_file}")
        print(f"{'='*80}")
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                llava_logs = []
                for line in f:
                    if line.strip():
                        try:
                            entry = json.loads(line)
                            if 'llava' in json.dumps(entry, ensure_ascii=False).lower():
                                llava_logs.append(entry)
                        except:
                            pass
                
                if llava_logs:
                    print(f"找到 {len(llava_logs)} 条 llava 相关日志")
                    for log in llava_logs[-5:]:  # 显示最后5条
                        print(f"\n  [{log.get('timestamp', 'N/A')}] {log.get('operation_type', 'N/A')}")
                else:
                    print("未找到 llava 相关日志")
        except Exception as e:
            print(f"读取日志失败: {e}")
    
    logger.log_shutdown(exit_code=0)

if __name__ == '__main__':
    main()



