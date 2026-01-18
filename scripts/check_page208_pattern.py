#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查Page 208模式是否被Gemini识别"""
import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

db = TraderDBManager('abu')
conn = db._get_connection()

# 查询Page 208
print("=" * 80)
print("检查Page 208模式")
print("=" * 80)

results = conn.execute("""
    SELECT id, source_page, pattern_name, pattern_type, gemini_annotation_json 
    FROM pattern_library 
    WHERE source_page = 208
""").fetchall()

print(f"\n找到 {len(results)} 个Page 208的模式\n")

for r in results:
    print(f"ID: {r[0]}")
    print(f"Page: {r[1]}")
    print(f"Name: {r[2]}")
    print(f"Type: {r[3]}")
    
    if r[4]:
        try:
            annotation = json.loads(r[4])
            print(f"\nGemini标注内容:")
            print(json.dumps(annotation, indent=2, ensure_ascii=False))
        except:
            print(f"标注JSON解析失败: {r[4][:200]}")
    else:
        print("无Gemini标注")
    print("-" * 80)

# 搜索包含"18"或"first"的模式
print("\n\n搜索包含'18'或'first'或'breakout'的模式:")
print("=" * 80)

results2 = conn.execute("""
    SELECT id, source_page, pattern_name, pattern_type 
    FROM pattern_library 
    WHERE pattern_name LIKE '%18%' 
       OR pattern_name LIKE '%first%' 
       OR gemini_annotation_json LIKE '%18%'
       OR gemini_annotation_json LIKE '%first%'
       OR gemini_annotation_json LIKE '%breakout%'
    LIMIT 20
""").fetchall()

print(f"\n找到 {len(results2)} 个相关模式\n")

for r in results2:
    print(f"ID: {r[0]}, Page: {r[1]}, Name: {r[2]}, Type: {r[3]}")

db.close()

