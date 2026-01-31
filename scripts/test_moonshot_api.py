#!/usr/bin/env python3
"""测试 Moonshot API Key 是否有效"""

import os
import base64
import requests
from pathlib import Path

# Load .env file if exists
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

API_KEY = os.getenv("MOONSHOT_API_KEY", "")

if not API_KEY:
    print("❌ 错误: 未设置 MOONSHOT_API_KEY")
    print("请设置环境变量: export MOONSHOT_API_KEY=sk-...")
    exit(1)

print(f"✓ API Key: {API_KEY[:20]}...")

# Test with text first (cheaper)
headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

payload = {
    "model": "kimi-k2.5",
    "messages": [{"role": "user", "content": 'Say "Moonshot API works!"'}],
    "max_tokens": 50,
}

print("\n测试文本 API...")
response = requests.post(
    "https://api.moonshot.cn/v1/chat/completions",
    headers=headers,
    json=payload,
    timeout=30,
)

if response.status_code == 200:
    result = response.json()
    content = result["choices"][0]["message"]["content"]
    print(f"✅ 文本 API 正常: {content}")

    # Test Vision
    print("\n测试 Vision API...")
    image_path = "data/abu/images/page_0601_img_01_clip.png"
    if Path(image_path).exists():
        with open(image_path, "rb") as f:
            base64_image = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": "kimi-k2.5",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this chart in one word."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            "max_tokens": 100,
        }

        response = requests.post(
            "https://api.moonshot.cn/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            content = result['choices'][0]['message']['content']
            print(f"✅ Vision API 正常: {content}")
            print("\n🎉 可以开始批量处理！运行: python scripts/batch_process_601_1000.py")
        else:
            print(f"❌ Vision API 失败: {response.status_code}")
            print(response.text[:500])
    else:
        print(f"⚠️ 图片不存在: {image_path}")
else:
    print(f"❌ API 错误: {response.status_code}")
    print(response.text[:500])
