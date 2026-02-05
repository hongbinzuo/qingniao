#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一导入脚本 - Consolidated Import Script
用法：将JSON数据粘贴到下面的data变量中，然后运行此脚本
Usage: Paste your JSON data into the 'data' variable below, then run this script
"""

import sys
from pathlib import Path

# Add src to path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from batch_import_manual import save_to_database

# ============================================
# 在这里粘贴你的JSON数据
# PASTE YOUR JSON DATA HERE
# ============================================

data = [
    # 示例格式 / Example format:
    # {
    #     "image_id": "page_0601_img_01_clip.jpg",
    #     "page": 601,
    #     "slide_type": "chart",
    #     ...
    # }
]

# ============================================
# 不要修改下面的代码
# DO NOT MODIFY CODE BELOW
# ============================================

if __name__ == "__main__":
    if not data or (len(data) == 1 and not data[0]):
        print("错误：data 为空，请先粘贴JSON数据")
        print("Error: data is empty, please paste JSON data first")
        sys.exit(1)

    print(f"准备导入 {len(data)} 条记录...")
    print(f"Preparing to import {len(data)} records...")

    try:
        save_to_database(data)
        print(f"✓ 成功导入 {len(data)} 条记录")
        print(f"✓ Successfully imported {len(data)} records")
    except Exception as e:
        print(f"✗ 导入失败: {e}")
        print(f"✗ Import failed: {e}")
        sys.exit(1)
