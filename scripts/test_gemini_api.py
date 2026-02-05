#!/usr/bin/env python3
"""测试 Gemini Pro 3 API 配置"""

import base64
import os
from pathlib import Path

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

GEMINI_BASE_URL = os.getenv("GOOGLE_GEMINI_BASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-pro")

if not GEMINI_BASE_URL or not GEMINI_API_KEY:
    print("❌ 错误: 请先配置环境变量")
    print("GOOGLE_GEMINI_BASE_URL=https://code.newcli.com/gemini")
    print("GEMINI_API_KEY=sk-ant-oat01-...")
    exit(1)

print(f"✓ Base URL: {GEMINI_BASE_URL}")
print(f"✓ API Key: {GEMINI_API_KEY[:20]}...")
print(f"✓ Model: {GEMINI_MODEL}")

# Test 1: Text API
print("\n测试 1: 文本 API...")
headers = {
    "Authorization": f"Bearer {GEMINI_API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "model": GEMINI_MODEL,
    "messages": [{"role": "user", "content": "Say 'Gemini API works!'"}],
    "max_tokens": 50,
}

response = requests.post(
    f"{GEMINI_BASE_URL}/v1/chat/completions", headers=headers, json=payload, timeout=30
)

if response.status_code == 200:
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    print(f"✅ 文本 API 正常: {content}")
else:
    print(f"❌ 文本 API 失败: {response.status_code}")
    print(response.text[:500])
    exit(1)

# Test 2: Vision API
print("\n测试 2: Vision API...")
image_path = "data/abu/images/page_0601_img_01_clip.png"

if not Path(image_path).exists():
    print(f"⚠️ 测试图片不存在: {image_path}")
    print("请确保图片路径正确")
    exit(1)

with open(image_path, "rb") as f:
    base64_image = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": GEMINI_MODEL,
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Describe this trading chart in one sentence.",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                },
            ],
        }
    ],
    "max_tokens": 200,
}

response = requests.post(
    f"{GEMINI_BASE_URL}/v1/chat/completions", headers=headers, json=payload, timeout=60
)

if response.status_code == 200:
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    print(f"✅ Vision API 正常: {content}")
    print("\n🎉 Gemini Pro 3 配置成功！可以开始批量处理")
    print("运行: python scripts/batch_process_gemini_601_1000.py")
else:
    print(f"❌ Vision API 失败: {response.status_code}")
    print(response.text[:500])
