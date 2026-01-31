#!/usr/bin/env python3
"""诊断 Gemini API 端点配置"""

import os

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

GEMINI_BASE_URL = os.getenv("GOOGLE_GEMINI_BASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-pro")

print(f"Base URL: {GEMINI_BASE_URL}")
print(f"API Key: {GEMINI_API_KEY[:20]}...")
print(f"Model: {GEMINI_MODEL}\n")

# Test different endpoint combinations
endpoints_to_test = [
    f"{GEMINI_BASE_URL}/v1/chat/completions",
    f"{GEMINI_BASE_URL}/chat/completions",
    f"{GEMINI_BASE_URL}/v1/messages",
    GEMINI_BASE_URL,  # Direct base URL
]

headers = {
    "Authorization": f"Bearer {GEMINI_API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": GEMINI_MODEL,
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10,
}

print("Testing different endpoints...\n")

for i, endpoint in enumerate(endpoints_to_test, 1):
    print(f"{i}. Testing: {endpoint}")
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ SUCCESS! Use this endpoint.")
            break
        else:
            print(f"   Error: {response.text[:150]}")
    except Exception as e:
        print(f"   Exception: {e}")
    print()
