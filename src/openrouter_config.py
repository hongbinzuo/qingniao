#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenRouter API 配置模块
从环境变量读取 OpenRouter API key
"""

import os
from pathlib import Path
from typing import Optional

# 尝试从 .env 文件加载环境变量
try:
    from dotenv import load_dotenv
    # 加载项目根目录的 .env 文件
    env_path = Path(__file__).resolve().parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv 未安装时，只使用系统环境变量
    pass


def get_openrouter_api_key() -> Optional[str]:
    """
    获取 OpenRouter API Key
    
    Returns:
        str: OpenRouter API Key，如果未设置则返回 None
        
    Example:
        >>> api_key = get_openrouter_api_key()
        >>> if api_key:
        ...     print("API key loaded successfully")
    """
    api_key = os.getenv('OPENROUTER_API_KEY')
    if api_key and api_key.strip():
        return api_key.strip()
    return None


def get_openrouter_api_url() -> str:
    """
    获取 OpenRouter API URL
    
    Returns:
        str: OpenRouter API 基础 URL
    """
    return os.getenv('OPENROUTER_API_URL', 'https://openrouter.ai/api/v1')


def is_openrouter_configured() -> bool:
    """
    检查 OpenRouter 是否已配置
    
    Returns:
        bool: 如果 API key 已配置则返回 True，否则返回 False
    """
    return get_openrouter_api_key() is not None


if __name__ == '__main__':
    # 测试配置
    print("OpenRouter 配置检查:")
    configured = is_openrouter_configured()
    print(f"  API Key: {'已配置' if configured else '未配置'}")
    if configured:
        key = get_openrouter_api_key()
        if key:
            print(f"  Key 长度: {len(key)} 字符")
            print(f"  Key 前缀: {key[:10]}...")
    api_url = get_openrouter_api_url()
    print(f"  API URL: {api_url}")

