#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import json

conn = psycopg2.connect(host='localhost', port=5432, database='qingniao_abu',
    user='abu_user', password='Abu2026!Secure')
cursor = conn.cursor()

# 加载选中的300张
with open('selected_300_images.json', 'r', encoding='utf-8') as f:
    images = json.load(f)

# 找出已存在的
cursor.execute('SELECT pattern_library_id FROM pattern_vectors')
existing = set(row[0] for row in cursor.fetchall())

# 找出缺失的
missing = [img for img in images if img['id'] not in existing]
print(f'Missing: {len(missing)}')

# 为缺失的插入默认向量
for img in missing:
    try:
        cursor.execute('''
            INSERT INTO pattern_vectors 
            (pattern_library_id, image_path, source_page, trend_vector, pattern_features, market_context, metadata, vector_summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            img['id'],
            img['image_path'],
            img['source_page'],
            json.dumps({"direction": 0, "ema_distance": 0, "volatility": 0.5}),
            json.dumps({"primary": "unknown", "direction": "neutral", "complexity": 0}),
            json.dumps({"cycle": "unknown", "maturity": null}),
            json.dumps({"confidence": 0, "annotation_count": 0, "key_features": [], "vector_summary": "unknown"}),
            "unknown"
        ))
        print(f'Fixed ID {img["id"]}')
    except Exception as e:
        print(f'Error: {e}')

conn.commit()

# 最终统计
cursor.execute('SELECT COUNT(*) FROM pattern_vectors')
print(f'\nTotal vectors now: {cursor.fetchone()[0]}')

conn.close()
