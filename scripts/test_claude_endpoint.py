#!/usr/bin/env python3
"""测试是否为 Claude API"""

import os

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

GEMINI_BASE_URL = os.getenv("GOOGLE_GEMINI_BASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

print(f"Base URL: {GEMINI_BASE_URL}")
print(f"API Key prefix: {GEMINI_API_KEY[:15]}...")
print("\nAPI Key 格式分析:")
print(f"  - 以 'sk-ant-' 开头 = Anthropic Claude API")
print(f"  - 以 'sk-' 开头 = OpenAI/兼容格式")
print(f"  - 以 'AIza' 开头 = Google Gemini API")

# Test Claude API format
print("\n测试 Claude API 格式...")
headers = {
    "x-api-key": GEMINI_API_KEY,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
}

payload = {
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 50,
    "messages": [{"role": "user", "content": "Say 'Claude API works!'"}],
}

response = requests.post(
    f"{GEMINI_BASE_URL}/v1/messages", headers=headers, json=payload, timeout=30
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print(f"✅ 这是 Claude API!")
    print(response.json())
else:
    print(f"Response: {response.text[:300]}")
