#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""估算OCR提取运行时间"""

import sys
sys.path.insert(0, 'src')
from db_manager_trader import TraderDBManager

db = TraderDBManager('abu')
conn = db._get_connection()

# 统计
total = conn.execute('''
    SELECT COUNT(*) FROM pattern_library 
    WHERE image_path IS NOT NULL AND image_path != ''
''').fetchone()[0]

processed = conn.execute('''
    SELECT COUNT(*) FROM pattern_library 
    WHERE chart_features_json IS NOT NULL 
      AND chart_features_json != '' 
      AND chart_features_json LIKE '%ocr_text%'
''').fetchone()[0]

pending = total - processed

print(f"\n统计信息:")
print(f"总记录数: {total}")
print(f"已处理: {processed}")
print(f"待处理: {pending}")

# 估算时间（基于测试：每张图片约3-4秒）
time_per_image = 3.5  # 秒
total_seconds = pending * time_per_image
total_minutes = total_seconds / 60
total_hours = total_minutes / 60

print(f"\n时间估算（基于 {time_per_image}秒/图片）:")
print(f"预计总时间: {total_seconds:.0f}秒 = {total_minutes:.1f}分钟 = {total_hours:.2f}小时")

# 建议
print(f"\n建议:")
print(f"- 如果要睡觉，可以:")
print(f"  1. 后台运行（Windows: start /b python scripts/extract_pattern_ocr_text.py）")
print(f"  2. 或者先运行部分（--limit 100），明天继续")
print(f"  3. 脚本支持断点续传（已处理的会跳过）")

db.close()



