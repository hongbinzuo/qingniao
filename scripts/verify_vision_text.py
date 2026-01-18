#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证 Vision 文字提取结果"""

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

db = TraderDBManager('abu')
conn = db._get_connection()

rows = conn.execute('''
    SELECT id, pattern_name, chart_features_json 
    FROM pattern_library 
    WHERE chart_features_json LIKE '%vision_text%'
    LIMIT 5
''').fetchall()

print(f"找到 {len(rows)} 条包含 Vision 文字说明的记录:\n")

for pid, name, chart_json in rows:
    try:
        chart = json.loads(chart_json) if isinstance(chart_json, str) else chart_json
        vision_text = chart.get('vision_text', '')
        model = chart.get('vision_model', 'unknown')
        extracted_at = chart.get('vision_extracted_at', 'unknown')
        print(f"ID={pid} ({name}):")
        print(f"  模型: {model}")
        print(f"  提取时间: {extracted_at}")
        print(f"  文字: {vision_text[:150]}...")
        print()
    except Exception as e:
        print(f"ID={pid}: 解析失败 - {e}")

db.close()

