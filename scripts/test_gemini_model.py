#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Gemini模型可用性（OpenRouter）
"""

import sys
import json
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from openrouter_config import get_openrouter_api_key, get_openrouter_api_url, is_openrouter_configured
import requests
import base64

def test_model(model_name: str):
    """测试模型是否可用"""
    if not is_openrouter_configured():
        print("❌ OpenRouter API Key 未配置")
        return False
    
    api_key = get_openrouter_api_key()
    api_url = f"{get_openrouter_api_url()}/chat/completions"
    
    # 创建一个简单的测试请求（文本）
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/qingniao",
        "X-Title": "QingNiao Model Test"
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {
                "role": "user",
                "content": "Hello, respond with 'OK' if you can see this message."
            }
        ],
        "max_tokens": 10
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"[OK] {model_name}: 可用")
                print(f"    响应: {content[:50]}")
                return True
            else:
                print(f"[WARN] {model_name}: 响应格式异常")
                return False
        else:
            error_text = response.text
            print(f"[FAIL] {model_name}: 请求失败 (状态码 {response.status_code})")
            print(f"    错误: {error_text[:200]}")
            return False
    except Exception as e:
        print(f"[FAIL] {model_name}: 异常 - {str(e)}")
        return False

def main():
    models_to_test = [
        "google/gemini-3.0-flash-image-exp",  # 3.0预览版（优先）
        "google/gemini-2.5-flash-image",      # 2.5正式版（默认）
        "google/gemini-2.5-flash",            # 2.5（无-image后缀）
    ]
    
    print("测试Gemini模型可用性（OpenRouter）\n")
    print("=" * 60)
    
    if not is_openrouter_configured():
        print("[FAIL] OpenRouter API Key 未配置")
        return 1
    
    available_models = []
    for model in models_to_test:
        if test_model(model):
            available_models.append(model)
        print()
    
    print("=" * 60)
    print(f"\n可用模型: {len(available_models)}/{len(models_to_test)}")
    
    if available_models:
        recommended = available_models[0]  # 第一个可用的（优先3.0）
        print(f"\n推荐使用: {recommended}")
        print(f"\n使用命令:")
        print(f"  python -m src.abu.gemini_vision_analyzer --model {recommended}")
        return 0
    else:
        print("\n[FAIL] 没有可用模型，请检查OpenRouter配置")
        return 1

if __name__ == '__main__':
    sys.exit(main())

