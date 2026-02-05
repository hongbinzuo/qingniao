#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从469张chart中分层抽样选出300张
"""
import psycopg2
import json
import random

# 连接数据库
conn = psycopg2.connect(
    host='localhost', port=5432, database='qingniao_abu',
    user='abu_user', password='Abu2026!Secure'
)
cursor = conn.cursor()

# 获取所有chart记录（469张）
cursor.execute("""
    SELECT id, pattern_name, source_page, image_path, gemini_annotation_json
    FROM pattern_library 
    WHERE gemini_annotation_json LIKE '%"slide_type": "chart"%'
    AND gemini_annotation_json IS NOT NULL
""")

all_charts = cursor.fetchall()
print(f"Total chart records: {len(all_charts)}")

# 按模式分类
wedge_records = []      # Wedge Top/Bottom
trend_records = []      # Bull Trend/Small Pullback Bull
reversal_records = []   # Double Top/Bottom
triangle_records = []   # Expanding Triangle/etc
gap_breakout_records = []  # Gap/Breakout
other_records = []      # 其他

for row in all_charts:
    pattern_name = row[1] or ""
    pattern_lower = pattern_name.lower()
    
    if 'wedge' in pattern_lower:
        wedge_records.append(row)
    elif pattern_lower in ['bull trend', 'small pullback bull trend']:
        trend_records.append(row)
    elif 'double' in pattern_lower:
        reversal_records.append(row)
    elif 'triangle' in pattern_lower:
        triangle_records.append(row)
    elif any(x in pattern_lower for x in ['gap', 'breakout']):
        gap_breakout_records.append(row)
    else:
        other_records.append(row)

print(f"Wedge: {len(wedge_records)}")
print(f"Trend: {len(trend_records)}")
print(f"Reversal: {len(reversal_records)}")
print(f"Triangle: {len(triangle_records)}")
print(f"Gap/Breakout: {len(gap_breakout_records)}")
print(f"Other: {len(other_records)}")

# 分层抽样
random.seed(42)  # 固定随机种子，可复现

selected = []

# 1. Wedge类：选60张
wedge_sample = random.sample(wedge_records, min(60, len(wedge_records)))
selected.extend(wedge_sample)

# 2. Trend类：选60张  
trend_sample = random.sample(trend_records, min(60, len(trend_records)))
selected.extend(trend_sample)

# 3. 反转形态：选50张
reversal_sample = random.sample(reversal_records, min(50, len(reversal_records)))
selected.extend(reversal_sample)

# 4. 三角形：选40张（如果不够从other补）
triangle_needed = 40
triangle_sample = random.sample(triangle_records, min(triangle_needed, len(triangle_records)))
selected.extend(triangle_sample)
remaining_triangle = triangle_needed - len(triangle_sample)

# 5. Gap/Breakout：选30张
gap_needed = 30
gap_sample = random.sample(gap_breakout_records, min(gap_needed, len(gap_breakout_records)))
selected.extend(gap_sample)
remaining_gap = gap_needed - len(gap_sample)

# 6. 特殊/复杂：从other中选30张 + 补足上面不够的
other_needed = 30 + remaining_triangle + remaining_gap
other_sample = random.sample(other_records, min(other_needed, len(other_records)))
selected.extend(other_sample)

# 7. 如果还不够300张，从所有剩余中随机补
if len(selected) < 300:
    all_ids = set(row[0] for row in selected)
    remaining = [row for row in all_charts if row[0] not in all_ids]
    need_more = 300 - len(selected)
    if remaining and need_more > 0:
        selected.extend(random.sample(remaining, min(need_more, len(remaining))))

# 保存结果
output = []
for row in selected[:300]:
    output.append({
        "id": row[0],
        "pattern_name": row[1],
        "source_page": row[2],
        "image_path": row[3],
        "gemini_json": row[4]
    })

with open('selected_300_images.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ Selected {len(output)} images saved to selected_300_images.json")

# 统计选中的分布
pattern_dist = {}
for item in output:
    pn = item['pattern_name'] or 'None'
    pattern_dist[pn] = pattern_dist.get(pn, 0) + 1

print("\n📊 Selected distribution:")
for pattern, count in sorted(pattern_dist.items(), key=lambda x: -x[1])[:10]:
    print(f"  {pattern}: {count}")

conn.close()
