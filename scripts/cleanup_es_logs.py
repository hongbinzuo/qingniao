#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定期清理Elasticsearch旧日志
保留最近3个月（90天）的数据
"""

import sys
from pathlib import Path

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from elasticsearch_logger import get_es_logger

if __name__ == '__main__':
    print("=" * 80)
    print("清理Elasticsearch旧日志")
    print("=" * 80)
    print()
    
    logger = get_es_logger()
    
    if not logger.available:
        print("❌ Elasticsearch不可用，跳过清理")
        sys.exit(1)
    
    # 清理90天前的数据
    print(f"清理 {logger.retention_days} 天前的数据...")
    logger.cleanup_old_indices()
    
    print()
    print("=" * 80)
    print("清理完成")
    print("=" * 80)


