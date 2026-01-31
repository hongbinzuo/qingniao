#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import psycopg2
import json
import random

conn = psycopg2.connect(host='localhost', port=5432, database='qingniao_abu', user='abu_user', password='Abu2026!Secure')
cursor = conn.cursor()

cursor.execute("""SELECT id, pattern_name, source_page, image_path, gemini_annotation_json FROM pattern_library WHERE gemini_annotation_json LIKE '%chart%' AND gemini_annotation_json IS NOT NULL""")

all_charts = cursor.fetchall()
print('Total chart records:', len(all_charts))

wedge, trend, reversal, triangle, gap, other = [], [], [], [], [], []
for row in all_charts:
    pn = (row[1] or '').lower()
    if 'wedge' in pn: wedge.append(row)
    elif pn in ['bull trend', 'small pullback bull trend']: trend.append(row)
    elif 'double' in pn: reversal.append(row)
    elif 'triangle' in pn: triangle.append(row)
    elif any(x in pn for x in ['gap', 'breakout']): gap.append(row)
    else: other.append(row)

print(f'Wedge: {len(wedge)}, Trend: {len(trend)}, Reversal: {len(reversal)}, Triangle: {len(triangle)}, Gap: {len(gap)}, Other: {len(other)}')

random.seed(42)
selected = []
selected.extend(random.sample(wedge, min(60, len(wedge))))
selected.extend(random.sample(trend, min(60, len(trend))))
selected.extend(random.sample(reversal, min(50, len(reversal))))
selected.extend(random.sample(triangle, min(40, len(triangle))))
selected.extend(random.sample(gap, min(30, len(gap))))
selected.extend(random.sample(other, min(60, len(other))))

if len(selected) < 300:
    all_ids = set(r[0] for r in selected)
    remaining = [r for r in all_charts if r[0] not in all_ids]
    selected.extend(random.sample(remaining, 300 - len(selected)))

output = [{'id': r[0], 'pattern_name': r[1], 'source_page': r[2], 'image_path': r[3], 'gemini_json': r[4]} for r in selected[:300]]

with open('selected_300_images.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print('Selected', len(output), 'images saved to selected_300_images.json')
conn.close()
