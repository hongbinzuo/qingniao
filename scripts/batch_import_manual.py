#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量导入手工识别的JSON数据
"""

import json
import sys
import psycopg2
from pathlib import Path

def convert_to_vector(gemini_json):
    """将Gemini JSON转换为向量格式"""
    chart = gemini_json.get("chart") or {}
    patterns = gemini_json.get("patterns", []) or []
    ema = chart.get("ema_20", {})

    # EMA关系
    ema_relation = ema.get("relation", "crossing")
    ema_slope = ema.get("slope", "flat")

    if ema_relation == "above":
        ema_dist = 0.6 if ema_slope == "up" else 0.3
    elif ema_relation == "below":
        ema_dist = -0.6 if ema_slope == "down" else -0.3
    else:
        ema_dist = 0.0

    # 趋势方向
    direction_bias = chart.get("direction_bias", "neutral")
    trend_direction = {"long": 0.8, "short": -0.8, "neutral": 0.0}.get(
        direction_bias, 0.0
    )

    # 模式信息
    primary_pattern = "none"
    secondary_pattern = "none"
    pattern_direction = direction_bias
    complexity = 0.5

    if patterns:
        primary = patterns[0]
        primary_pattern = primary.get("pattern_family", "none")
        pattern_direction = primary.get("direction_bias", direction_bias)
        complexity = min(1.0, 0.3 + len(patterns) * 0.2)
        if len(patterns) > 1:
            secondary_pattern = patterns[1].get("pattern_family", "none")

    # 置信度
    confidence = 0.6
    if patterns:
        confidence = sum(p.get("confidence", 0.5) for p in patterns) / len(patterns)

    # 标注数量
    annotation_count = len(gemini_json.get("annotations_text", []))

    # 关键特征
    key_features = []
    for kf in gemini_json.get("kline_features", [])[:3]:
        feat = kf.get("feature")
        if feat:
            key_features.append(feat)
    if primary_pattern != "none":
        key_features.insert(0, primary_pattern)
    key_features = key_features[:5]

    # 向量摘要
    summary_parts = [primary_pattern]
    if chart.get("trend_maturity"):
        summary_parts.append(chart["trend_maturity"])
    if ema_relation:
        summary_parts.append(ema_relation + "_ema")
    vector_summary = "_".join(filter(None, summary_parts))

    return {
        "trend_vector": {
            "direction": round(trend_direction, 2),
            "ema_distance": round(ema_dist, 2),
            "volatility": 0.5,
            "slope_strength": round(abs(trend_direction), 2),
        },
        "pattern_features": {
            "primary": primary_pattern,
            "secondary": secondary_pattern,
            "direction": pattern_direction,
            "complexity": round(complexity, 2),
        },
        "market_context": {
            "cycle": chart.get("market_cycle", "trading_range"),
            "maturity": chart.get("trend_maturity", "middle"),
            "timeframe": gemini_json.get("timeframe_hint", "5m"),
        },
        "metadata": {
            "confidence": round(confidence, 2),
            "annotation_count": annotation_count,
            "key_features": key_features,
            "vector_summary": vector_summary,
        },
    }

def save_to_database(record, conn):
    """保存单条记录到数据库"""
    cursor = conn.cursor()

    page_num = record.get("page")
    image_id = record.get("image_id", "")
    image_path = f"data/abu/images/{image_id}"

    # 处理null字符串问题
    if record.get("market") == "null":
        record["market"] = None

    try:
        # 1. 检查是否已存在
        cursor.execute(
            "SELECT id FROM pattern_library WHERE source_page = %s",
            (page_num,)
        )
        existing = cursor.fetchone()

        # 提取pattern_name
        pattern_name = None
        if record.get("patterns"):
            pattern_name = record["patterns"][0].get("pattern_name")

        # 2. 保存到pattern_library
        if existing:
            pattern_id = existing[0]
            cursor.execute(
                """UPDATE pattern_library
                   SET gemini_annotation_json = %s,
                       pattern_name = %s,
                       pattern_type = %s,
                       updated_at = NOW()
                   WHERE id = %s""",
                (json.dumps(record), pattern_name,
                 record.get("slide_type"), pattern_id)
            )
            print(f"  [Page {page_num}] Updated pattern_library")
        else:
            cursor.execute(
                """INSERT INTO pattern_library
                   (source_page, image_path, pattern_name, pattern_type,
                    gemini_annotation_json, created_at)
                   VALUES (%s, %s, %s, %s, %s, NOW())
                   RETURNING id""",
                (page_num, image_path, pattern_name,
                 record.get("slide_type"), json.dumps(record))
            )
            pattern_id = cursor.fetchone()[0]
            print(f"  [Page {page_num}] Inserted into pattern_library")

        # 3. 转换为向量
        vector_data = convert_to_vector(record)

        # 4. 保存到pattern_vectors
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
             json.dumps(vector_data["trend_vector"]),
             json.dumps(vector_data["pattern_features"]),
             json.dumps(vector_data["market_context"]),
             json.dumps(vector_data["metadata"]),
             vector_data["metadata"]["vector_summary"])
        )
        print(f"  [Page {page_num}] Saved to pattern_vectors")

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        print(f"  [Page {page_num}] ERROR: {e}")
        return False

def main():
    """主函数：批量导入JSON数据"""

    # 连接数据库
    conn = psycopg2.connect(
        host='localhost', port=5432, database='qingniao_abu',
        user='abu_user', password='Abu2026!Secure'
    )

    # 从命令行参数或文件读取JSON数据
    if len(sys.argv) > 1:
        # 从文件读取
        json_file = sys.argv[1]
        print(f"Reading from file: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # 从stdin读取
        print("Reading from stdin (paste JSON and press Ctrl+D)...")
        data = json.load(sys.stdin)

    # 确保data是列表
    if not isinstance(data, list):
        data = [data]

    print(f"\n{'='*60}")
    print(f"Batch Import: {len(data)} records")
    print(f"{'='*60}\n")

    success_count = 0
    fail_count = 0

    for record in data:
        page_num = record.get("page", "unknown")
        print(f"Processing page {page_num}...")

        if save_to_database(record, conn):
            success_count += 1
        else:
            fail_count += 1

    conn.close()

    print(f"\n{'='*60}")
    print(f"Import Complete!")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()

