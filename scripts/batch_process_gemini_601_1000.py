#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理图片 601-1000 - 使用 Gemini Pro 3
优化版本：异步处理 + 重试机制 + 质量验证
"""

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor

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
    print("❌ 错误: 请先配置 GOOGLE_GEMINI_BASE_URL 和 GEMINI_API_KEY")
    print("在 .env 文件中添加:")
    print("GOOGLE_GEMINI_BASE_URL=https://code.newcli.com/gemini")
    print("GEMINI_API_KEY=sk-ant-oat01-...")
    sys.exit(1)

print(f"✓ Gemini Base URL: {GEMINI_BASE_URL}")
print(f"✓ API Key: {GEMINI_API_KEY[:20]}...")
print(f"✓ Model: {GEMINI_MODEL}")

# ==========================================
# 提示词 - 简化版，专注于核心特征
# ==========================================
PROMPT = """你是专业价格行为分析师。分析这张交易图表，提取结构化特征。

要求：
1. 只输出JSON，不要其他文字
2. 未知字段用 null（JSON null，不是字符串）
3. 只使用词表中的值，否则置 null
4. 所有confidence为0.0-1.0浮点数

词表：
- slide_type: chart|separator|text|unknown
- timeframe_hint: 1m|5m|15m|30m|1h|4h|1D|1W|1M
- market_cycle: trend|trading_range|spike_channel|tight_channel|climactic
- trend_maturity: early|middle|late|climactic
- direction_bias: long|short|neutral
- ema_relation: above|below|crossing
- ema_slope: up|down|flat
- pattern_family: triangle|wedge|gap|breakout|reversal|trend|range|double_top_bottom
- pattern_name: Nested Expanding Triangle|Expanding Triangle|Wedge Top|Wedge Bottom|Bull Measuring Gap|Exhaustion Gap|Small Pullback Bull Trend|Bull Trend|Double Bottom|Double Top
- pattern_status: confirmed|suspected|failed|invalidated

输出JSON：
{
  "slide_type": "chart",
  "timeframe_hint": "5m",
  "market": "ES",
  "chart": {
    "market_cycle": "trend",
    "trend_maturity": "middle",
    "direction_bias": "long",
    "ema_20": {
      "exists": true,
      "relation": "above",
      "slope": "up",
      "confidence": 0.9
    }
  },
  "patterns": [
    {
      "pattern_family": "trend",
      "pattern_name": "Small Pullback Bull Trend",
      "direction_bias": "long",
      "status": "confirmed",
      "confidence": 0.85,
      "evidence": ["higher highs", "higher lows", "small pullbacks"]
    }
  ],
  "key_levels": {
    "support": [4930, 4955],
    "resistance": [4985, 5000],
    "confidence": 0.8
  },
  "annotations_text": ["20-Gap bar", "Minor Bar 38"],
  "summary": "Small pullback bull trend with strong follow-through",
  "quality": {
    "ocr_quality": "good",
    "chart_visibility": "full"
  }
}

只输出JSON，不要markdown代码块包裹。"""


# ==========================================
# 异步 API 调用
# ==========================================
async def call_gemini_api(
    session: aiohttp.ClientSession, image_path: str, max_retries: int = 3
) -> Optional[Dict]:
    """异步调用 Gemini API"""
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
        "max_tokens": 2000,
    }

    for attempt in range(max_retries):
        try:
            async with session.post(
                f"{GEMINI_BASE_URL}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status == 200:
                    result = await response.json()
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
                    error_text = await response.text()
                    print(f"  API Error {response.status}: {error_text[:200]}")

        except asyncio.TimeoutError:
            print(f"  Timeout (attempt {attempt + 1}/{max_retries})")
        except Exception as e:
            print(f"  Error (attempt {attempt + 1}/{max_retries}): {e}")

        if attempt < max_retries - 1:
            await asyncio.sleep(2**attempt)

    return None


# ==========================================
# 数据库操作
# ==========================================
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

    def save_result(self, page_num: int, image_path: str, data: Dict) -> Optional[int]:
        """保存识别结果到数据库"""
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                "SELECT id FROM pattern_library WHERE source_page = %s", (page_num,)
            )
            existing = cursor.fetchone()

            if existing:
                pattern_id = existing[0]
                cursor.execute(
                    """UPDATE pattern_library
                       SET gemini_annotation_json = %s, pattern_name = %s,
                           pattern_type = %s, updated_at = NOW()
                       WHERE id = %s""",
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
                cursor.execute(
                    """INSERT INTO pattern_library
                       (source_page, image_path, pattern_name, pattern_type,
                        gemini_annotation_json, created_at)
                       VALUES (%s, %s, %s, %s, %s, NOW()) RETURNING id""",
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

    def close(self):
        self.conn.close()


# ==========================================
# 批处理器
# ==========================================
class BatchProcessor:
    def __init__(self):
        self.db = DatabaseManager()
        self.image_dir = Path("data/abu/images")
        self.processed = 0
        self.failed = 0
        self.semaphore = asyncio.Semaphore(5)  # 并发限制

    async def process_single_image(self, session: aiohttp.ClientSession, page_num: int):
        """处理单张图片"""
        image_path = self.image_dir / f"page_{page_num:04d}_img_01_clip.png"

        if not image_path.exists():
            print(f"[{page_num}] Image not found")
            self.failed += 1
            return

        async with self.semaphore:
            print(f"[{page_num}] Processing...", end=" ", flush=True)

            # 调用 API
            data = await call_gemini_api(session, str(image_path))
            if not data:
                print("FAILED")
                self.failed += 1
                return

            # 保存到数据库
            pattern_id = self.db.save_result(page_num, str(image_path), data)
            if pattern_id:
                print(f"OK (id={pattern_id})")
                self.processed += 1
            else:
                print("FAILED (DB)")
                self.failed += 1

    async def process_batch(self, start_page: int, end_page: int):
        """批量处理图片"""
        print(f"{'=' * 60}")
        print(f"Gemini Pro 3 Batch Processing: {start_page}-{end_page}")
        print(f"{'=' * 60}")

        async with aiohttp.ClientSession() as session:
            tasks = [
                self.process_single_image(session, page_num)
                for page_num in range(start_page, end_page + 1)
            ]
            await asyncio.gather(*tasks)

        print(f"\n{'=' * 60}")
        print(f"Completed: {self.processed} OK, {self.failed} Failed")
        print(f"{'=' * 60}")

    def close(self):
        self.db.close()


# ==========================================
# 主函数
# ==========================================
async def main():
    processor = BatchProcessor()
    try:
        await processor.process_batch(601, 1000)
    finally:
        processor.close()


if __name__ == "__main__":
    asyncio.run(main())
