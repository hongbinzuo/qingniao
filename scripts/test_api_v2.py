#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 API 配置 V2 - 使用向量方案提示词"""
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

# 优先级: OpenRouter > Moonshot Kimi
OPENROUTER_KEY = os.getenv('OPENROUTER_API_KEY')
KIMI_KEY = os.getenv('KIMI_API_KEY')

image_path = "data/abu/images/page_0601_img_01_clip.png"

# 向量方案提示词 - 要求输出结构化特征用于向量检索
VECTOR_PROMPT = """你是专业价格行为分析师。请从图表截图中提取结构化特征向量，用于向量数据库检索匹配。

要求（必须遵守）：
1) 只输出 JSON，不要附加说明文字。
2) 未知字段一律用 JSON 的 null；禁止输出字符串 "null"/"unknown"/"n/a"/""。
3) 只允许使用给定词表；不在词表中的值必须置 null，并把原始值写入 raw（raw 仅收 OOV）。
4) patterns/status 必须从词表选择，无法确定置 null。
5) slide_type=separator 时，只保留 image_id/page/slide_type/summary/annotations_text/raw；其他字段设为 null。
6) raw 只允许写入"不在词表中的原始值"，已在词表中的值禁止写入 raw。

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

pattern_family: triangle|wedge|gap|breakout|reversal|trend|range|double_top_bottom|null
pattern_type: triangle|wedge|gap|breakout|trend|range|reversal|null
pattern_name: Nested Expanding Triangle|Expanding Triangle|Wedge Top|Truncated Wedge Bottom|Bull Measuring Gap|Exhaustion Gap|Small Pullback Bull Trend|Bull Trend|Double Bottom|Double Top|null
kline_features.feature: double_bottom|double_top|engulfing|inside_bar|outside_bar|gap|doji|null
quality.ocr_quality: good|fair|poor|null
quality.chart_visibility: full|partial|poor|null

输出 JSON schema（严格遵守字段名）：
{
  "image_id": "string",
  "page": "string|number|null",
  "slide_type": "chart|separator|text|unknown",
  "timeframe_hint": "1m|5m|15m|30m|1h|4h|1D|1W|1M|null",
  "market": "ES|NQ|YM|BTC|ETH|FX|unknown|null",
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
      "raw": {
        "pattern_name": "string",
        "pattern_type": "string",
        "pattern_family": "string",
        "direction_bias": "string",
        "status": "string"
      }
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
    { "feature": "double_bottom|double_top|engulfing|inside_bar|outside_bar|gap|doji|null", "confidence": 0.0 }
  ],
  "key_levels": {
    "support": ["number"],
    "resistance": ["number"],
    "confidence": 0.0
  },
  "targets_probabilities": [
    { "target": "string", "probability": 0.0 }
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
    "ema_20": { "relation": "string", "slope": "string" },
    "bar_by_bar": {
      "body_gap": "string",
      "overlap_level": "string",
      "follow_through": "string",
      "setup_signal_entry": "string"
    },
    "kline_features": ["string"],
    "quality": { "ocr_quality": "string", "chart_visibility": "string" }
  }
}

输出规范：
- patterns 最多 2 个，主模式在前。
- annotations_text 去重，短语化，不要整段长文本。
- 无法纠正到词表时，置 null，raw 记录原始值（raw 只写 OOV）。
- 所有 confidence 字段为 0.0-1.0 浮点数。

请分析这张图表，只输出符合上述 schema 的 JSON。"""

# 确定使用哪个 API
if OPENROUTER_KEY:
    API_KEY = OPENROUTER_KEY
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL = "google/gemini-2.0-flash-001"
    API_NAME = "OpenRouter (Gemini)"
    HEADERS_EXTRA = {
        "HTTP-Referer": "https://qingniao.trading",
        "X-Title": "Qingniao Trading System"
    }
elif KIMI_KEY:
    if KIMI_KEY.startswith('sk-kimi-'):
        print("[WARNING] Detected Kimi Code key")
        print("  Kimi Code API is only available for Coding Agents (Kimi CLI)")
        print("  Please use OpenRouter API instead, or get Moonshot API key")
        print("  from https://platform.moonshot.cn/")
        exit(1)
    
    API_KEY = KIMI_KEY
    API_URL = "https://api.moonshot.cn/v1/chat/completions"
    MODEL = "kimi-k2.5"
    API_NAME = "Moonshot Kimi"
    HEADERS_EXTRA = {}
else:
    print("[ERROR] No API key configured")
    print("Please set OPENROUTER_API_KEY or KIMI_API_KEY in .env file")
    exit(1)

print("=" * 60)
print("API Test (V2) - Vector Schema Analysis")
print("=" * 60)
print(f"Provider: {API_NAME}")
print(f"Model: {MODEL}")
print(f"Key: {API_KEY[:25]}...")

if not os.path.exists(image_path):
    print(f"[ERROR] Image not found: {image_path}")
    exit(1)

# 编码图片
with open(image_path, 'rb') as f:
    base64_image = base64.b64encode(f.read()).decode('utf-8')

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
headers.update(HEADERS_EXTRA)

payload = {
    "model": MODEL,
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": VECTOR_PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
        ]
    }],
    "max_tokens": 2000,
    "temperature": 0.1  # 低温度确保输出稳定
}

print("\n[SENDING] Requesting vector schema analysis...")
print("-" * 60)
try:
    response = requests.post(API_URL, headers=headers, json=payload, timeout=90)
    print(f"[STATUS] {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"\n[VECTOR ANALYSIS RESULT]")
        print("=" * 60)
        print(content)
        print("=" * 60)
        
        # 尝试验证 JSON 格式
        try:
            import json
            json_content = content.strip()
            # 如果输出有 markdown 代码块，提取其中的 JSON
            if "```json" in json_content:
                json_content = json_content.split("```json")[1].split("```")[0].strip()
            elif "```" in json_content:
                json_content = json_content.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(json_content)
            print(f"\n[JSON VALID] Successfully parsed, top keys: {list(parsed.keys())}")
        except Exception as e:
            print(f"\n[JSON WARNING] Could not parse as JSON: {e}")
            
    elif response.status_code == 401:
        print("[ERROR] Invalid API key")
    elif response.status_code == 403:
        print("[ERROR] API access denied")
    else:
        print(f"[ERROR] {response.text[:300]}")
except Exception as e:
    print(f"[ERROR] {e}")
