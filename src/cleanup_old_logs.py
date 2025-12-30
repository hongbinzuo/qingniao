#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理旧日志脚本
保留最近3个月的对话日志
"""

import sys
from db_config import get_db_manager

def main():
    """主函数"""
    print("=" * 80)
    print("清理旧日志（保留最近3个月）")
    print("=" * 80)
    print()
    
    db = get_db_manager()
    
    # 获取清理前的统计
    stats_before = db.get_stats()
    print(f"清理前:")
    print(f"  总日志数: {stats_before.get('total_logs', 0)}")
    print()
    
    # 清理90天前的日志
    deleted_count = db.cleanup_old_logs(days=90)
    
    # 获取清理后的统计
    stats_after = db.get_stats()
    print(f"清理后:")
    print(f"  删除日志数: {deleted_count}")
    print(f"  剩余日志数: {stats_after.get('total_logs', 0)}")
    print()
    
    print("=" * 80)
    print("✅ 清理完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()

