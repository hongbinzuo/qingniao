#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""显示选中的50张图片列表"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def main():
    list_file = ROOT / 'data' / 'abu' / 'comparison_test' / 'selected_50_images.json'
    
    if not list_file.exists():
        print("❌ 未找到图片列表文件")
        print("   请先运行: python scripts/select_50_random_images.py")
        return
    
    with open(list_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("=" * 80)
    print(f"已选择的50张图片列表")
    print("=" * 80)
    print()
    
    for item in data:
        print(f"{item['index']:2d}. {item['image_name']}")
    
    print()
    print("=" * 80)
    print(f"共 {len(data)} 张图片")
    print("=" * 80)

if __name__ == '__main__':
    main()

