#!/usr/bin/env python3
"""测试正确的 base URL"""

import os

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("GEMINI_API_KEY", "")

# Test different base URLs
base_urls = [
    "https://code.newcli.com",
    "https://code.newcli.com/api",
    "https://api.newcli.com",
]

headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "gemini-3-pro",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 10,
}

print("Testing different base URLs...\n")

for base_url in base_urls:
    for path in ["/v1/chat/completions", "/chat/completions"]:
        endpoint = f"{base_url}{path}"
        print(f"Testing: {endpoint}")
        try:
            response = requests.post(
                endpoint, headers=headers, json=payload, timeout=10
            )
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  ✅ SUCCESS!")
                print(f"  Use: GOOGLE_GEMINI_BASE_URL={base_url}")
                exit(0)
        except Exception as e:
            print(f"  Error: {e}")
        print()
