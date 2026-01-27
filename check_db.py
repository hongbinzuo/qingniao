#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv('.env.postgres')

try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='qingniao_abu',
        user='abu_user',
        password='Abu2026!Secure'
    )
    cursor = conn.cursor()
    
    # 查看表结构
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'pattern_library'
        ORDER BY ordinal_position;
    """)
    print('=== pattern_library 表结构 ===')
    for row in cursor.fetchall():
        print(f'{row[0]}: {row[1]}')
    
    # 查看记录数
    cursor.execute('SELECT COUNT(*) FROM pattern_library')
    count = cursor.fetchone()[0]
    print(f'\n=== 总记录数: {count} ===')
    
    # 查看前3条样本
    cursor.execute('SELECT id, pattern_name, source_page, image_path, gemini_annotation_json FROM pattern_library LIMIT 3')
    print('\n=== 前3条样本 ===')
    for row in cursor.fetchall():
        print(f'ID: {row[0]}')
        print(f'Pattern: {row[1]}')
        print(f'Page: {row[2]}')
        print(f'Image: {row[3]}')
        json_preview = row[4][:200] if row[4] else 'None'
        print(f'JSON Preview: {json_preview}...')
        print('---')
    
    conn.close()
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
