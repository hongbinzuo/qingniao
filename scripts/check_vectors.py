#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import json

conn = psycopg2.connect(host='localhost', port=5432, database='qingniao_abu',
    user='abu_user', password='Abu2026!Secure')
cursor = conn.cursor()

# 统计
cursor.execute('SELECT COUNT(*) FROM pattern_vectors')
count = cursor.fetchone()[0]
print(f'Total vectors: {count}')

# 查看样本
cursor.execute('''
    SELECT v.pattern_library_id, v.image_path, v.vector_summary, 
           v.trend_vector, v.pattern_features, p.pattern_name
    FROM pattern_vectors v
    JOIN pattern_library p ON v.pattern_library_id = p.id
    LIMIT 5
''')

print('\n=== Sample vectors ===')
for row in cursor.fetchall():
    print(f'\nID: {row[0]}')
    print(f'Image: {row[1]}')
    print(f'Original pattern: {row[5]}')
    print(f'Vector summary: {row[2]}')
    print(f'Trend: {row[3]}')
    print(f'Pattern: {row[4]}')

# 统计向量摘要分布
print('\n=== Top 10 vector summaries ===')
cursor.execute('''
    SELECT vector_summary, COUNT(*) as cnt 
    FROM pattern_vectors 
    GROUP BY vector_summary 
    ORDER BY cnt DESC 
    LIMIT 10
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]}')

conn.close()
