# -*- coding: utf-8 -*-
"""
日志维护脚本
- 压缩1个月之前的日志文件
- 删除超过3个月的日志文件（包括压缩文件）
"""

import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.file_logger import get_file_logger

def main():
    print("=" * 60)
    print("日志维护脚本")
    print("=" * 60)
    print()
    print("策略：")
    print("  - 保留最近1个月的日志（未压缩）")
    print("  - 压缩1-3个月之间的日志")
    print("  - 删除超过3个月的日志")
    print()
    
    logger = get_file_logger()
    
    # 执行维护
    print("执行维护...")
    result = logger.maintain_logs()
    
    print()
    print("维护结果：")
    print(f"  ✓ 压缩文件数: {result['compressed']}")
    print(f"  ✓ 删除文件数: {result['deleted']}")
    
    # 显示统计信息
    print()
    print("当前日志统计：")
    stats = logger.get_stats()
    print(f"  总文件数: {stats['total_files']}")
    print(f"  总条目数: {stats['total_entries']}")
    print(f"  最早日期: {stats.get('oldest_date', 'N/A')}")
    print(f"  最新日期: {stats.get('newest_date', 'N/A')}")
    
    print()
    print("=" * 60)
    print("维护完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()


