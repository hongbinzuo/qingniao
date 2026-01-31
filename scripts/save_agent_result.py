#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
保存agent分析结果到数据库
用于多agent并行处理时保存结果
"""

import json
import sys
import psycopg2

def save_result(page_num, image_path, gemini_json, vector_json):
    """保存分析结果和向量到数据库"""

    conn = psycopg2.connect(
        host='localhost', port=5432, database='qingniao_abu',
        user='abu_user', password='Abu2026!Secure'
    )
    cursor = conn.cursor()

    try:
        # 1. 保存到pattern_library
        cursor.execute(
            "SELECT id FROM pattern_library WHERE source_page = %s",
            (page_num,)
        )
        existing = cursor.fetchone()

        pattern_name = None
        if gemini_json.get("patterns"):
            pattern_name = gemini_json["patterns"][0].get("pattern_name")

        if existing:
            pattern_id = existing[0]
            cursor.execute(
                """UPDATE pattern_library
                   SET gemini_annotation_json = %s, pattern_name = %s,
                       pattern_type = %s, updated_at = NOW()
                   WHERE id = %s""",
                (json.dumps(gemini_json), pattern_name,
                 gemini_json.get("slide_type"), pattern_id)
            )
        else:
            cursor.execute(
                """INSERT INTO pattern_library
                   (source_page, image_path, pattern_name, pattern_type,
                    gemini_annotation_json, created_at)
                   VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id""",
                (page_num, image_path, pattern_name,
                 gemini_json.get("slide_type"), json.dumps(gemini_json))
            )
            pattern_id = cursor.fetchone()[0]

        # 2. 保存向量
        cursor.execute(
            "DELETE FROM pattern_vectors WHERE pattern_library_id = %s",
            (pattern_id,)
        )
        cursor.execute(
            """INSERT INTO pattern_vectors
               (pattern_library_id, image_path, source_page,
                trend_vector, pattern_features, market_context,
                metadata, vector_summary)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (pattern_id, image_path, page_num,
             json.dumps(vector_json["trend_vector"]),
             json.dumps(vector_json["pattern_features"]),
             json.dumps(vector_json["market_context"]),
             json.dumps(vector_json["metadata"]),
             vector_json["metadata"]["vector_summary"])
        )

        conn.commit()
        print(f"[OK] Page {page_num} saved (id={pattern_id})")
        return pattern_id

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error: {e}", file=sys.stderr)
        return None
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python save_agent_result.py <page> <image_path> <gemini.json> <vector.json>")
        sys.exit(1)

    page = int(sys.argv[1])
    img_path = sys.argv[2]

    with open(sys.argv[3], 'r', encoding='utf-8') as f:
        gemini = json.load(f)
    with open(sys.argv[4], 'r', encoding='utf-8') as f:
        vector = json.load(f)

    result = save_result(page, img_path, gemini, vector)
    sys.exit(0 if result else 1)
