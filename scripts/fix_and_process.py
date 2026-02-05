#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理未识别图片 - 修复版
"""
import psycopg2
import json
import glob
import os
from pathlib import Path

conn = psycopg2.connect(host='localhost', port=5432, database='qingniao_abu',
    user='abu_user', password='Abu2026!Secure')
cursor = conn.cursor()

# 获取已识别的page列表
cursor.execute('SELECT source_page FROM pattern_library WHERE gemini_annotation_json IS NOT NULL')
identified_pages = set(row[0] for row in cursor.fetchall() if row[0])

print(f'Identified pages: {len(identified_pages)}')

# 获取所有clip图片
clip_files = sorted(glob.glob('data/abu/images/page_*_img_01_clip.png'))

# 筛选未识别的
to_process = []
for f in clip_files:
    basename = os.path.basename(f)
    parts = basename.split('_')
    if len(parts) >= 2:
        try:
            page_num = int(parts[1])
            if page_num not in identified_pages:
                to_process.append((page_num, f))
        except:
            pass

print(f'Unidentified images to process: {len(to_process)}')

# 获取当前最大ID
cursor.execute('SELECT MAX(id) FROM pattern_library')
max_id = cursor.fetchone()[0] or 0
print(f'Current max ID: {max_id}')

# 批量插入未识别图片
inserted = 0
for page_num, img_path in to_process:
    try:
        # 检查是否已存在（通过image_path）
        cursor.execute('SELECT id FROM pattern_library WHERE image_path = %s', (img_path,))
        existing = cursor.fetchone()
        
        if existing:
            pattern_id = existing[0]
        else:
            # 插入新记录
            max_id += 1
            cursor.execute('''
                INSERT INTO pattern_library 
                (id, source_page, image_path, pattern_name, pattern_type, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            ''', (max_id, page_num, img_path, 'unprocessed', 'chart'))
            pattern_id = max_id
            inserted += 1
        
        # 检查是否已有向量
        cursor.execute('SELECT 1 FROM pattern_vectors WHERE pattern_library_id = %s', (pattern_id,))
        if cursor.fetchone():
            continue
        
        # 插入基础向量
        vector_data = {
            'trend': {'direction': 0.0, 'ema_distance': 0.0, 'volatility': 0.5, 'slope_strength': 0.0},
            'pattern': {'primary': 'unprocessed', 'secondary': 'none', 'direction': 'neutral', 'complexity': 0.0},
            'market': {'cycle': 'unknown', 'maturity': None, 'timeframe': '5m'},
            'meta': {'confidence': 0.0, 'annotation_count': 0, 'key_features': [], 
                    'vector_summary': f'unprocessed_page_{page_num}'},
            'summary': f'unprocessed_page_{page_num}'
        }
        
        cursor.execute('''
            INSERT INTO pattern_vectors 
            (pattern_library_id, image_path, source_page, trend_vector, 
             pattern_features, market_context, metadata, vector_summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            pattern_id, img_path, page_num,
            json.dumps(vector_data['trend']),
            json.dumps(vector_data['pattern']),
            json.dumps(vector_data['market']),
            json.dumps(vector_data['meta']),
            vector_data['summary']
        ))
        
    except Exception as e:
        print(f'Error: {e}')
        continue

conn.commit()
print(f'Inserted {inserted} new records')

# 统计
cursor.execute('SELECT COUNT(*) FROM pattern_vectors')
print(f'Total vectors now: {cursor.fetchone()[0]}')

conn.close()
