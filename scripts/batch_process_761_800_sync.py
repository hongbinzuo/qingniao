#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理图片 761-800 - 使用 Gemini Pro 3 (同步版本)
"""

import base64
import json
import os
import sys
import time
import requests
from pathlib import Path

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ==========================================
# Gemini Pro 3 配置
# ==========================================
GEMINI_BASE_URL = os.getenv("GOOGLE_GEMINI_BASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-pro")

if not GEMINI_BASE_URL or not GEMINI_API_KEY:
    print("[ERROR] Please configure GOOGLE_GEMINI_BASE_URL and GEMINI_API_KEY")
    sys.exit(1)

print(f"[OK] Gemini Base URL: {GEMINI_BASE_URL}")
print(f"[OK] API Key: {GEMINI_API_KEY[:20]}...")
print(f"[OK] Model: {GEMINI_MODEL}")

# ==========================================
# 读取提示词
# ==========================================
with open('config/abu_analyzer_prompt.md', 'r', encoding='utf-8') as f:
    PROMPT = f.read()

print(f"[OK] Prompt loaded ({len(PROMPT)} chars)")

# ==========================================
# API 调用函数
# ==========================================
def call_gemini_api(image_path: str, max_retries: int = 3):
    """调用 Gemini API"""
    with open(image_path, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": GEMINI_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 4000,
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{GEMINI_BASE_URL}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=90
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                # 解析 JSON
                content = content.strip()
                if content.startswith("```json"):
                    content = content.split("```json")[1].split("```")[0].strip()
                elif content.startswith("```"):
                    content = content.split("```")[1].split("```")[0].strip()

                data = json.loads(content)
                return data
            else:
                print(f"  API Error {response.status_code}: {response.text[:200]}")

        except requests.Timeout:
            print(f"  Timeout (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            print(f"  Error (attempt {attempt + 1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            time.sleep(2**attempt)

    return None

# ==========================================
# 向量转换函数 (Part 1)
# ==========================================
def convert_to_vector(gemini_json: dict) -> dict:
    """将Gemini JSON转换为向量格式"""
    chart = gemini_json.get("chart", {})
    patterns = gemini_json.get("patterns", []) or []
    ema = chart.get("ema_20", {})

    ema_relation = ema.get("relation", "crossing")
    ema_slope = ema.get("slope", "flat")

    if ema_relation == "above":
        ema_dist = 0.6 if ema_slope == "up" else 0.3
    elif ema_relation == "below":
        ema_dist = -0.6 if ema_slope == "down" else -0.3
    else:
        ema_dist = 0.0

    direction_bias = chart.get("direction_bias", "neutral")
    trend_direction = {"long": 0.8, "short": -0.8, "neutral": 0.0}.get(direction_bias, 0.0)

    market_cycle = chart.get("market_cycle", "trading_range")
    trend_maturity = chart.get("trend_maturity", "middle")

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

    confidence = 0.6
    if gemini_json.get("quality", {}).get("ocr_quality") == "good":
        confidence = 0.85
    if patterns:
        confidence = sum(p.get("confidence", 0.5) for p in patterns) / len(patterns)

    annotations = gemini_json.get("annotations_text", [])
    annotation_count = len(annotations)

    key_features = []
    kline_features = gemini_json.get("kline_features", [])
    for kf in kline_features[:3]:
        feat = kf.get("feature")
        if feat:
            key_features.append(feat)

    if primary_pattern != "none":
        key_features.insert(0, primary_pattern)
    key_features = key_features[:5]

    summary_parts = [primary_pattern]
    if trend_maturity:
        summary_parts.append(trend_maturity)
    if ema_relation:
        summary_parts.append(ema_relation + "_ema")
    vector_summary = "_".join(filter(None, summary_parts))

    return {
        "trend_vector": {
            "direction": round(trend_direction, 2),
            "ema_distance": round(ema_dist, 2),
            "volatility": 0.5,
            "slope_strength": round(abs(trend_direction), 2)
        },
        "pattern_features": {
            "primary": primary_pattern,
            "secondary": secondary_pattern,
            "direction": pattern_direction,
            "complexity": round(complexity, 2)
        },
        "market_context": {
            "cycle": market_cycle,
            "maturity": trend_maturity,
            "timeframe": gemini_json.get("timeframe_hint", "5m")
        },
        "metadata": {
            "confidence": round(confidence, 2),
            "annotation_count": annotation_count,
            "key_features": key_features,
            "vector_summary": vector_summary
        }
    }

# ==========================================
# 数据库操作
# ==========================================
import psycopg2

class DatabaseManager:
    def __init__(self):
        self.pg_config = {
            "host": "localhost",
            "port": 5432,
            "database": "qingniao_abu",
            "user": "abu_user",
            "password": "Abu2026!Secure",
        }
        self.conn = psycopg2.connect(**self.pg_config)

    def save_result(self, page_num: int, image_path: str, gemini_data: dict, vector_data: dict):
        """保存识别结果和向量到数据库"""
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT id FROM pattern_library WHERE source_page = %s", (page_num,))
            existing = cursor.fetchone()

            pattern_name = None
            if gemini_data.get("patterns"):
                pattern_name = gemini_data["patterns"][0].get("pattern_name")

            if existing:
                pattern_id = existing[0]
                cursor.execute(
                    """UPDATE pattern_library
                       SET gemini_annotation_json = %s, pattern_name = %s,
                           pattern_type = %s, updated_at = NOW()
                       WHERE id = %s""",
                    (json.dumps(gemini_data), pattern_name, gemini_data.get("slide_type"), pattern_id),
                )
            else:
                cursor.execute(
                    """INSERT INTO pattern_library
                       (source_page, image_path, pattern_name, pattern_type,
                        gemini_annotation_json, created_at)
                       VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id""",
                    (page_num, image_path, pattern_name, gemini_data.get("slide_type"), json.dumps(gemini_data)),
                )
                pattern_id = cursor.fetchone()[0]

            # 保存向量
            cursor.execute("DELETE FROM pattern_vectors WHERE pattern_library_id = %s", (pattern_id,))
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

            self.conn.commit()
            return pattern_id
        except Exception as e:
            self.conn.rollback()
            print(f"  DB Error: {e}")
            return None

    def close(self):
        self.conn.close()

# ==========================================
# 主处理函数
# ==========================================
def process_single_image(db: DatabaseManager, page_num: int) -> bool:
    """处理单张图片"""
    image_path = f"data/abu/images/page_{page_num:04d}_img_01_clip.png"

    if not os.path.exists(image_path):
        print(f"[{page_num}] 图片不存在，跳过")
        return False

    print(f"[{page_num}] 开始处理...")

    # 调用API分析
    gemini_data = call_gemini_api(image_path)
    if not gemini_data:
        print(f"[{page_num}] API调用失败")
        return False

    # 转换为向量
    try:
        vector_data = convert_to_vector(gemini_data)
    except Exception as e:
        print(f"[{page_num}] 向量转换失败: {e}")
        return False

    # 保存到数据库
    pattern_id = db.save_result(page_num, image_path, gemini_data, vector_data)
    if pattern_id:
        print(f"[{page_num}] ✓ 成功保存 (id={pattern_id})")
        return True
    else:
        print(f"[{page_num}] ✗ 保存失败")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("开始处理图片 761-800 (共40张)")
    print("=" * 60)

    db = DatabaseManager()
    success_count = 0
    fail_count = 0
    skip_count = 0

    for i, page_num in enumerate(range(761, 801), 1):
        try:
            result = process_single_image(db, page_num)

            if result:
                success_count += 1
            elif os.path.exists(f"data/abu/images/page_{page_num:04d}_img_01_clip.png"):
                fail_count += 1
            else:
                skip_count += 1

            # 每10张报告一次进度
            if i % 10 == 0:
                print(f"\n进度报告 [{i}/40]:")
                print(f"  成功: {success_count}")
                print(f"  失败: {fail_count}")
                print(f"  跳过: {skip_count}")
                print()

            # 避免API限流
            time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n用户中断")
            break
        except Exception as e:
            print(f"[{page_num}] 未预期错误: {e}")
            fail_count += 1

    db.close()

    print("\n" + "=" * 60)
    print("处理完成!")
    print(f"总计: 40张")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"跳过: {skip_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
