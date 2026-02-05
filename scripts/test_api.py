#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试 API 配置 - 支持 OpenRouter、Kimi 和 Kimi Code"""
import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

# 获取 API Keys
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
KIMI_API_KEY = os.getenv('KIMI_API_KEY')

# 测试图片
image_path = "data/abu/images/page_0601_img_01_clip.png"

def get_professional_prompt():
    """获取专业图表分析提示词"""
    return """你是专业的交易图表分析专家。请详细分析这张价格行为图表图片，并按照以下格式输出识别结果：

## 输出要求

### 1. 文本描述（保持原有格式）
- 图表概览
- 关键概念
- 完整价格路径
- 模式识别
- 交易信号
- 价格行为分析
- 市场条件
- 完整叙述

### 2. 结构化JSON特征（必须输出）

```json
{
  "pattern_type": "模式类型，如bull_breakout",
  "pattern_subtype": "子类型",
  "direction": "long/short/neutral",
  "confidence": 0.85,
  "kline_features": {
    "consecutive_bull_bars": 2,
    "bull_bars_closing_near_high": {"count": 2, "min_ratio": 0.90},
    "bars_above_ema": 2,
    "ema_relationship": "above_price"
  },
  "price_levels": {
    "breakout_level": 87500.0,
    "trading_range": {"high": 87400.0, "low": 87200.0},
    "support_levels": [87200.0],
    "resistance_levels": [87500.0]
  },
  "trading_signals": {
    "entry": {"type": "buy_the_close", "bar_index": 20},
    "stop_loss": {"type": "below_trading_range_low", "price": 87200.0},
    "take_profit": {"type": "measured_move", "target_price": 87750.0}
  },
  "market_conditions": {
    "trend": "bullish",
    "volatility": "medium",
    "context": "trading_range_breakout"
  }
}
```

现在请分析这张图表，输出完整的识别结果，包括文本描述和结构化JSON特征。"""

def test_openrouter():
    """测试 OpenRouter API (Gemini)"""
    if not OPENROUTER_API_KEY:
        print("[SKIP] OpenRouter API Key not configured")
        return False
    
    print("\n[TEST] OpenRouter API (Gemini)...")
    print(f"Key: {OPENROUTER_API_KEY[:30]}...")
    
    # 加载专业提示词
    prompt = get_professional_prompt()
    
    with open(image_path, 'rb') as f:
        base64_image = base64.b64encode(f.read()).decode('utf-8')
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://qingniao.trading",
        "X-Title": "Qingniao Trading System"
    }
    
    payload = {
        "model": "google/gemini-2.0-flash-001",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]
            }
        ],
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"[OK] Response: {content[:200]}")
            return True
        else:
            print(f"[FAIL] {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_kimi():
    """测试 Moonshot Kimi API"""
    if not KIMI_API_KEY:
        print("[SKIP] Kimi API Key not configured")
        return False
    
    print("\n[TEST] Moonshot Kimi API...")
    print(f"Key: {KIMI_API_KEY[:20]}...")
    
    # 加载专业提示词
    prompt = get_professional_prompt()
    
    with open(image_path, 'rb') as f:
        base64_image = base64.b64encode(f.read()).decode('utf-8')
    
    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "kimi-k2.5",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]
            }
        ],
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"[OK] Response: {content[:200]}")
            return True
        else:
            print(f"[FAIL] {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

def test_kimi_code():
    """测试 Kimi Code API"""
    if not KIMI_API_KEY:
        print("[SKIP] Kimi API Key not configured")
        return False
    
    print("\n[TEST] Kimi Code API (api.kimi.com)...")
    print(f"Key: {KIMI_API_KEY[:20]}...")
    print("Note: Kimi Code API is only available for Coding Agents (Kimi CLI, etc.)")
    
    with open(image_path, 'rb') as f:
        base64_image = base64.b64encode(f.read()).decode('utf-8')
    
    headers = {
        "Authorization": f"Bearer {KIMI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "kimi-for-coding",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this chart pattern."},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]
            }
        ],
        "max_tokens": 500
    }
    
    try:
        response = requests.post(
            "https://api.kimi.com/coding/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"[OK] Response: {content[:200]}")
            return True
        elif response.status_code == 403:
            print("[INFO] Kimi Code API requires a Coding Agent context")
            print("       This key can only be used with Kimi CLI, not direct API calls")
            return False
        else:
            print(f"[FAIL] {response.text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("API Key Test Tool")
    print("=" * 50)
    print(f"\nImage: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"[ERROR] Image not found: {image_path}")
        exit(1)
    
    # 测试 OpenRouter
    openrouter_ok = test_openrouter()
    
    # 测试 Moonshot Kimi
    kimi_ok = test_kimi()
    
    # 测试 Kimi Code
    kimi_code_ok = test_kimi_code()
    
    # 总结
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"OpenRouter API (Gemini): {'OK' if openrouter_ok else 'FAIL'}")
    print(f"Moonshot Kimi API: {'OK' if kimi_ok else 'FAIL'}")
    print(f"Kimi Code API: {'OK' if kimi_code_ok else 'N/A (Agent-only)'}")
    
    print("\n" + "-" * 50)
    if openrouter_ok:
        print("[OK] OpenRouter API is available - recommended for vision tasks")
    if kimi_ok:
        print("[OK] Moonshot Kimi API is available")
    if not openrouter_ok and not kimi_ok:
        print("[ERROR] No API available for direct calls")
        print("\nTo use Kimi Code key:")
        print("  1. Use Kimi CLI tool directly")
        print("  2. Or get Moonshot API key from https://platform.moonshot.cn/")
