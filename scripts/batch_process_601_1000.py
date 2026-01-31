#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理图片 601-1000
使用 Kimi Code API 识别 + 入库 + 向量化 + 更新 FAISS
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import psycopg2

ROOT = Path(__file__).resolve().parent.parent

# Load .env file if exists
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# ==========================================
# 配置区域 - 请修改以下配置
# ==========================================
# Get Moonshot API Key from: https://platform.moonshot.cn
# New users get ¥15 free credits

# 方式1: 环境变量（推荐）
API_KEY = os.getenv("MOONSHOT_API_KEY", "")

# 方式2: 直接填写（临时使用，不推荐）
# API_KEY = "sk-your-moonshot-api-key-here"

if not API_KEY or "your" in API_KEY.lower():
    print("错误: 请先配置 MOONSHOT_API_KEY")
    print("1. 访问 https://platform.moonshot.cn 注册/登录")
    print("2. 创建 API Key（新用户送¥15）")
    print("3. 设置环境变量: export MOONSHOT_API_KEY=sk-...")
    print("   或修改本脚本第22行")
    sys.exit(1)
# ==========================================

# API 配置
API_URL = "https://api.moonshot.cn/v1/chat/completions"
MODEL = "kimi-k2.5"  # 或 kimi-latest

# 提示词（VECTOR特征向量提取 - 用于向量数据库检索）
PROMPT = """你是专业价格行为分析师。请从图表截图中提取结构化特征向量，用于向量数据库检索匹配。

要求（必须遵守）：
1) 只输出 JSON，不要附加说明文字。
2) 未知字段一律用 JSON 的 null；禁止输出字符串 "null"/"unknown"/"n/a"/""。
3) 只允许使用给定词表；不在词表中的值必须置 null，并把原始值写入 raw（raw 仅收 OOV）。
4) patterns/status 必须从词表选择，无法确定置 null。
5) slide_type=separator 时，只保留 image_id/page/slide_type/summary/annotations_text/raw；其他字段设为 null。
6) raw 只允许写入"不在词表中的原始值"，已在词表中的值禁止写入 raw。
7) vector_embedding 字段为特征向量表示，用于相似度检索。

允许词表：
- slide_type: chart|separator|text|unknown
- timeframe_hint: 1m|5m|15m|30m|1h|4h|1D|1W|1M|null
- market_cycle: trend|trading_range|spike_channel|tight_channel|climactic|null
- trend_maturity: early|middle|late|climactic|null
- direction_bias: long|short|neutral|null
- ema_20.relation: above|below|crossing|null
- ema_20.slope: up|down|flat|null
- bar_by_bar.body_gap: yes|no|null
- bar_by_bar.overlap_level: low|medium|high|null
- bar_by_bar.follow_through: strong|weak|mixed|null
- bar_by_bar.setup_signal_entry: setup|signal|entry|null
- pattern.status: confirmed|suspected|failed|invalidated|null
- pattern_family: triangle|wedge|gap|breakout|reversal|trend|range|double_top_bottom|null
- pattern_type: triangle|wedge|gap|breakout|trend|range|reversal|null
- pattern_name: Nested Expanding Triangle|Expanding Triangle|Wedge Top|Truncated Wedge Bottom|Bull Measuring Gap|Exhaustion Gap|Small Pullback Bull Trend|Bull Trend|Double Bottom|Double Top|null
- kline_features.feature: double_bottom|double_top|engulfing|inside_bar|outside_bar|gap|doji|null
- quality.ocr_quality: good|fair|poor|null
- quality.chart_visibility: full|partial|poor|null

输出 JSON schema（严格遵守字段名）：
{
  "image_id": "string",
  "page": "string|number|null",
  "slide_type": "chart|separator|text|unknown",
  "timeframe_hint": "1m|5m|15m|30m|1h|4h|1D|1W|1M|null",
  "market": "ES|NQ|YM|BTC|ETH|FX|unknown|null",
  "vector_embedding": {
    "feature_vector": [0.0, 0.0, 0.0],
    "dimension": 768,
    "model": "kimi-vision-extracted"
  },
  "chart": {
    "market_cycle": "trend|trading_range|spike_channel|tight_channel|climactic|null",
    "trend_maturity": "early|middle|late|climactic|null",
    "direction_bias": "long|short|neutral|null",
    "ema_20": {
      "exists": true|false|null,
      "relation": "above|below|crossing|null",
      "slope": "up|down|flat|null",
      "confidence": 0.0
    }
  },
  "patterns": [
    {
      "pattern_family": "triangle|wedge|gap|breakout|reversal|trend|range|double_top_bottom|null",
      "pattern_type": "triangle|wedge|gap|breakout|trend|range|reversal|null",
      "pattern_name": "Nested Expanding Triangle|Expanding Triangle|Wedge Top|Truncated Wedge Bottom|Bull Measuring Gap|Exhaustion Gap|Small Pullback Bull Trend|Bull Trend|Double Bottom|Double Top|null",
      "direction_bias": "long|short|neutral|null",
      "status": "confirmed|suspected|failed|invalidated|null",
      "confidence": 0.0,
      "evidence": ["string"],
      "raw": {"pattern_name": "string", "pattern_type": "string", "pattern_family": "string", "direction_bias": "string", "status": "string"}
    }
  ],
  "bar_by_bar": {
    "body_gap": "yes|no|null",
    "overlap_level": "low|medium|high|null",
    "follow_through": "strong|weak|mixed|null",
    "setup_signal_entry": "setup|signal|entry|null",
    "confidence": 0.0
  },
  "counting": {
    "leg_count": "number|null",
    "hl_count": "number|null",
    "bar_number": "number|null",
    "confidence": 0.0
  },
  "kline_features": [
    {"feature": "double_bottom|double_top|engulfing|inside_bar|outside_bar|gap|doji|null", "confidence": 0.0}
  ],
  "key_levels": {
    "support": ["number"],
    "resistance": ["number"],
    "confidence": 0.0
  },
  "targets_probabilities": [
    {"target": "string", "probability": 0.0}
  ],
  "confirmations": ["string"],
  "invalidations": ["string"],
  "annotations_text": ["string"],
  "summary": "string|null",
  "quality": {
    "ocr_quality": "good|fair|poor|null",
    "chart_visibility": "full|partial|poor|null",
    "notes": "string|null"
  },
  "raw": {
    "slide_type": "string",
    "timeframe_hint": "string",
    "market": "string",
    "chart": {
      "market_cycle": "string",
      "trend_maturity": "string",
      "direction_bias": "string"
    },
    "ema_20": {"relation": "string", "slope": "string"},
    "bar_by_bar": {
      "body_gap": "string",
      "overlap_level": "string",
      "follow_through": "string",
      "setup_signal_entry": "string"
    },
    "kline_features": ["string"],
    "quality": {"ocr_quality": "string", "chart_visibility": "string"}
  }
}

输出规范：
- patterns 最多 2 个，主模式在前。
- annotations_text 去重，短语化，不要整段长文本。
- 无法纠正到词表时，置 null，raw 记录原始值（raw 只写 OOV）。"""


class BatchProcessor:
    def __init__(self):
        self.pg_config = {
            "host": "localhost",
            "port": 5432,
            "database": "qingniao_abu",
            "user": "abu_user",
            "password": "Abu2026!Secure",
        }
        self.conn = psycopg2.connect(**self.pg_config)
        self.image_dir = Path("data/abu/images")
        self.processed = 0
        self.failed = 0

    def encode_image(self, image_path: str) -> str:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def call_kimi_api(self, image_path: str) -> Optional[Dict]:
        """调用 Kimi Code API 识别图片"""
        try:
            import requests

            base64_image = self.encode_image(image_path)

            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            }

            payload = {
                "model": MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                },
                            },
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 2000,
            }

            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # 解析 JSON
            try:
                # 尝试直接解析
                data = json.loads(content)
            except json.JSONDecodeError:
                # 尝试提取 JSON 代码块
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                else:
                    json_str = content.strip()
                data = json.loads(json_str)

            return data

        except Exception as e:
            print(f"  API Error: {e}")
            return None

    def save_to_postgres(self, page_num: int, image_path: str, data: Dict):
        """保存识别结果到 Postgres"""
        cursor = self.conn.cursor()

        try:
            # 检查是否已存在
            cursor.execute(
                "SELECT id FROM pattern_library WHERE source_page = %s", (page_num,)
            )
            existing = cursor.fetchone()

            if existing:
                pattern_id = existing[0]
                # 更新
                cursor.execute(
                    """
                    UPDATE pattern_library
                    SET gemini_annotation_json = %s,
                        pattern_name = %s,
                        pattern_type = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """,
                    (
                        json.dumps(data),
                        data.get("patterns", [{}])[0].get("pattern_name")
                        if data.get("patterns")
                        else None,
                        data.get("slide_type"),
                        pattern_id,
                    ),
                )
            else:
                # 插入新记录
                cursor.execute(
                    """
                    INSERT INTO pattern_library
                    (source_page, image_path, pattern_name, pattern_type,
                     gemini_annotation_json, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """,
                    (
                        page_num,
                        image_path,
                        data.get("patterns", [{}])[0].get("pattern_name")
                        if data.get("patterns")
                        else None,
                        data.get("slide_type"),
                        json.dumps(data),
                    ),
                )
                pattern_id = cursor.fetchone()[0]

            self.conn.commit()
            return pattern_id

        except Exception as e:
            self.conn.rollback()
            print(f"  DB Error: {e}")
            return None

    def convert_to_vector(self, data: Dict) -> Dict:
        """将 Gemini JSON 转换为向量特征"""
        chart = data.get("chart", {})
        patterns = data.get("patterns", []) or []
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
        annotation_count = len(data.get("annotations_text", []))

        # 关键特征
        key_features = []
        for kf in data.get("kline_features", [])[:3]:
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
                "timeframe": data.get("timeframe_hint", "5m"),
            },
            "metadata": {
                "confidence": round(confidence, 2),
                "annotation_count": annotation_count,
                "key_features": key_features,
                "vector_summary": vector_summary,
            },
        }

    def save_vector(
        self, pattern_id: int, image_path: str, page_num: int, vector_data: Dict
    ):
        """保存向量到数据库"""
        cursor = self.conn.cursor()

        try:
            # 删除旧向量
            cursor.execute(
                "DELETE FROM pattern_vectors WHERE pattern_library_id = %s",
                (pattern_id,),
            )

            # 插入新向量
            cursor.execute(
                """
                INSERT INTO pattern_vectors
                (pattern_library_id, image_path, source_page, trend_vector,
                 pattern_features, market_context, metadata, vector_summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    pattern_id,
                    image_path,
                    page_num,
                    json.dumps(vector_data["trend_vector"]),
                    json.dumps(vector_data["pattern_features"]),
                    json.dumps(vector_data["market_context"]),
                    json.dumps(vector_data["metadata"]),
                    vector_data["metadata"]["vector_summary"],
                ),
            )

            self.conn.commit()
            return True

        except Exception as e:
            self.conn.rollback()
            print(f"  Vector Error: {e}")
            return False

    def process_range(self, start_page: int = 601, end_page: int = 1000):
        """处理指定范围的图片"""
        print(f"=" * 60)
        print(f"Batch Processing: Page {start_page} - {end_page}")
        print(f"=" * 60)
        print(f"API Key: {API_KEY[:15]}...")
        print(f"Model: {MODEL}")
        print(f"=" * 60)

        for page_num in range(start_page, end_page + 1):
            image_path = self.image_dir / f"page_{page_num:04d}_img_01_clip.png"

            if not image_path.exists():
                print(f"[{page_num}] Image not found: {image_path}")
                self.failed += 1
                continue

            print(f"[{page_num}] Processing {image_path.name}...", end=" ")

            # 1. 调用 API 识别
            data = self.call_kimi_api(str(image_path))
            if not data:
                print("FAILED (API)")
                self.failed += 1
                continue

            # 2. 保存到 Postgres
            pattern_id = self.save_to_postgres(page_num, str(image_path), data)
            if not pattern_id:
                print("FAILED (DB)")
                self.failed += 1
                continue

            # 3. 转换为向量
            vector_data = self.convert_to_vector(data)

            # 4. 保存向量
            if self.save_vector(pattern_id, str(image_path), page_num, vector_data):
                print("OK")
                self.processed += 1
            else:
                print("FAILED (Vector)")
                self.failed += 1

            # 延迟避免频控
            time.sleep(1)

            # 每10张显示进度
            if (page_num - start_page + 1) % 10 == 0:
                print(f"  Progress: {self.processed} OK, {self.failed} Failed")

        print(f"=" * 60)
        print(f"Completed: {self.processed} OK, {self.failed} Failed")
        print(f"=" * 60)

    def rebuild_faiss(self):
        """重建 FAISS 索引"""
        print("\nRebuilding FAISS index...")
        sys.path.insert(0, str(ROOT / "src"))
        from faiss_index_builder import FaissIndexBuilder

        builder = FaissIndexBuilder(self.pg_config, "data/faiss_index")
        vectors, metadata = builder.load_vectors_from_postgres()
        index, metadata = builder.build_index(vectors, metadata)
        print(f"FAISS index rebuilt with {len(vectors)} vectors")

    def close(self):
        self.conn.close()


def main():
    processor = BatchProcessor()

    try:
        # 处理 601-1000
        processor.process_range(601, 1000)

        # 重建 FAISS
        processor.rebuild_faiss()

    finally:
        processor.close()


if __name__ == "__main__":
    main()
