#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理向量表：只保留Gemini识别过的
然后补充剩余的向量化
"""
import psycopg2
import json
import numpy as np
from pathlib import Path

conn = psycopg2.connect(host='localhost', port=5432, database='qingniao_abu',
    user='abu_user', password='Abu2026!Secure')
cursor = conn.cursor()

print("Step 1: Removing unprocessed vectors...")
cursor.execute('''
    DELETE FROM pattern_vectors 
    WHERE pattern_library_id IN (
        SELECT id FROM pattern_library WHERE pattern_name = 'unprocessed'
    )
''')
deleted = cursor.rowcount
print(f'  Deleted {deleted} unprocessed vectors')

conn.commit()

cursor.execute('''
    SELECT COUNT(*) FROM pattern_vectors v
    JOIN pattern_library p ON v.pattern_library_id = p.id
    WHERE p.gemini_annotation_json IS NOT NULL
''')
remaining = cursor.fetchone()[0]
print(f'  Remaining identified vectors: {remaining}')

print("\nStep 2: Processing remaining identified images...")
cursor.execute('''
    SELECT p.id, p.image_path, p.source_page, p.gemini_annotation_json
    FROM pattern_library p
    LEFT JOIN pattern_vectors v ON p.id = v.pattern_library_id
    WHERE p.gemini_annotation_json IS NOT NULL
    AND v.id IS NULL
''')

to_process = cursor.fetchall()
print(f'  Found {len(to_process)} identified images without vectors')

def convert_gemini_to_vector(gemini_json_str):
    """将Gemini JSON转换为向量特征"""
    data = json.loads(gemini_json_str)
    
    chart = data.get('chart', {})
    patterns = data.get('patterns', []) or []
    ema = chart.get('ema_20', {})
    
    # EMA关系
    ema_relation = ema.get('relation', 'crossing')
    ema_slope = ema.get('slope', 'flat')
    
    if ema_relation == 'above':
        ema_dist = 0.6 if ema_slope == 'up' else 0.3
    elif ema_relation == 'below':
        ema_dist = -0.6 if ema_slope == 'down' else -0.3
    else:
        ema_dist = 0.0
    
    # 趋势方向
    direction_bias = chart.get('direction_bias', 'neutral')
    trend_direction = {'long': 0.8, 'short': -0.8, 'neutral': 0.0}.get(direction_bias, 0.0)
    
    # 模式信息
    primary_pattern = 'none'
    secondary_pattern = 'none'
    pattern_direction = direction_bias
    complexity = 0.5
    
    if patterns:
        primary = patterns[0]
        primary_pattern = primary.get('pattern_family', 'none')
        pattern_direction = primary.get('direction_bias', direction_bias)
        complexity = min(1.0, 0.3 + len(patterns) * 0.2)
        if len(patterns) > 1:
            secondary_pattern = patterns[1].get('pattern_family', 'none')
    
    # 置信度
    confidence = 0.6
    if patterns:
        confidence = sum(p.get('confidence', 0.5) for p in patterns) / len(patterns)
    
    # 标注数量
    annotation_count = len(data.get('annotations_text', []))
    
    # 关键特征
    key_features = []
    for kf in data.get('kline_features', [])[:3]:
        feat = kf.get('feature')
        if feat:
            key_features.append(feat)
    if primary_pattern != 'none':
        key_features.insert(0, primary_pattern)
    key_features = key_features[:5]
    
    # 向量摘要
    summary_parts = [primary_pattern]
    if chart.get('trend_maturity'):
        summary_parts.append(chart['trend_maturity'])
    if ema_relation:
        summary_parts.append(ema_relation + '_ema')
    vector_summary = '_'.join(filter(None, summary_parts))
    
    return {
        'trend_vector': {
            'direction': round(trend_direction, 2),
            'ema_distance': round(ema_dist, 2),
            'volatility': 0.5,
            'slope_strength': round(abs(trend_direction), 2)
        },
        'pattern_features': {
            'primary': primary_pattern,
            'secondary': secondary_pattern,
            'direction': pattern_direction,
            'complexity': round(complexity, 2)
        },
        'market_context': {
            'cycle': chart.get('market_cycle', 'trading_range'),
            'maturity': chart.get('trend_maturity', 'middle'),
            'timeframe': data.get('timeframe_hint', '5m')
        },
        'metadata': {
            'confidence': round(confidence, 2),
            'annotation_count': annotation_count,
            'key_features': key_features,
            'vector_summary': vector_summary
        }
    }

# 处理剩余的
processed = 0
for row in to_process:
    try:
        pid, img_path, page, gemini_json = row
        vector_data = convert_gemini_to_vector(gemini_json)
        
        cursor.execute('''
            INSERT INTO pattern_vectors 
            (pattern_library_id, image_path, source_page, trend_vector, 
             pattern_features, market_context, metadata, vector_summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            pid, img_path, page,
            json.dumps(vector_data['trend_vector']),
            json.dumps(vector_data['pattern_features']),
            json.dumps(vector_data['market_context']),
            json.dumps(vector_data['metadata']),
            vector_data['metadata']['vector_summary']
        ))
        processed += 1
        
        if processed % 50 == 0:
            conn.commit()
            print(f'  Processed {processed}/{len(to_process)}...')
            
    except Exception as e:
        print(f'Error: {e}')
        continue

conn.commit()
print(f'\n  Completed: {processed} new vectors added')

# 最终统计
cursor.execute('''
    SELECT COUNT(*) FROM pattern_vectors v
    JOIN pattern_library p ON v.pattern_library_id = p.id
    WHERE p.gemini_annotation_json IS NOT NULL
''')
final_count = cursor.fetchone()[0]
print(f'\nFinal: {final_count} vectors (all from Gemini-identified images)')

conn.close()
