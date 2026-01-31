#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import json

conn = psycopg2.connect(
    host='localhost', port=5432, database='qingniao_abu',
    user='abu_user', password='Abu2026!Secure'
)
cursor = conn.cursor()

# 查看完整JSON样本
cursor.execute('''
    SELECT id, pattern_name, source_page, image_path, gemini_annotation_json 
    FROM pattern_library 
    WHERE gemini_annotation_json IS NOT NULL
    LIMIT 1
''')

row = cursor.fetchone()
if row:
    print(f'ID: {row[0]}')
    print(f'Pattern: {row[1]}')
    print(f'Page: {row[2]}')
    print(f'Image: {row[3]}')
    print('\n=== 完整JSON结构 ===')
    try:
        data = json.loads(row[4])
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except:
        print(row[4][:1000])

# 统计模式类型分布
print('\n=== 模式分布统计 ===')
cursor.execute('''
    SELECT pattern_name, COUNT(*) as cnt 
    FROM pattern_library 
    WHERE pattern_name IS NOT NULL 
    GROUP BY pattern_name 
    ORDER BY cnt DESC 
    LIMIT 15
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

# 统计slide_type分布
print('\n=== Slide类型分布 ===')
cursor.execute('''
    SELECT 
        CASE 
            WHEN gemini_annotation_json LIKE '%"slide_type": "chart"%' THEN 'chart'
            WHEN gemini_annotation_json LIKE '%"slide_type": "separator"%' THEN 'separator'
            ELSE 'unknown'
        END as slide_type,
        COUNT(*) as cnt
    FROM pattern_library
    GROUP BY 1
    ORDER BY cnt DESC
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

conn.close()
