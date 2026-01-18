#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取 Bitget 支持的币种列表并保存到配置文件
用于 Dream 系统的币种白名单验证
"""
from __future__ import annotations
import sys
import json
import requests
from pathlib import Path
from typing import List, Set

def fetch_bitget_symbols() -> Set[str]:
    """从 Bitget API 获取所有 USDT 交易对的基础币种"""
    print("🔍 正在获取 Bitget 币种列表...")
    max_retries = 3
    symbols: Set[str] = set()
    
    for attempt in range(max_retries):
        try:
            # Bitget 现货交易对 API
            url = "https://api.bitget.com/api/spot/v1/public/products"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '00000' and 'data' in data:
                    products = data['data']
                    for product in products:
                        symbol = product.get('symbolName', '')
                        # 筛选 USDT 交易对
                        if symbol.endswith('USDT'):
                            base_symbol = symbol.replace('USDT', '').upper()
                            symbols.add(base_symbol)
                    print(f"✓ 获取到 {len(symbols)} 个币种")
                    return symbols
                else:
                    print(f"✗ API响应错误: {data.get('msg', 'Unknown error')} (尝试 {attempt+1}/{max_retries})")
            else:
                print(f"✗ HTTP错误: {response.status_code} (尝试 {attempt+1}/{max_retries})")
        except Exception as e:
            print(f"✗ 获取失败 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(2)
    
    # 如果 API 失败，返回常见币种列表作为后备
    print("⚠️  API 获取失败，使用常见币种列表作为后备")
    common_symbols = {
        'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'TRX', 'DOT', 'MATIC',
        'AVAX', 'LINK', 'UNI', 'ATOM', 'ETC', 'LTC', 'NEAR', 'APT', 'ARB', 'OP',
        'SUI', 'SEI', 'TIA', 'INJ', 'FIL', 'ICP', 'ALGO', 'VET', 'THETA', 'EOS',
        'AAVE', 'MKR', 'COMP', 'SNX', 'CRV', 'SUSHI', '1INCH', 'YFI', 'SAND', 'MANA',
        'AXS', 'ENJ', 'GALA', 'CHZ', 'FLOW', 'IMX', 'RENDER', 'FET', 'AGIX', 'OCEAN'
    }
    return common_symbols


def main():
    config_path = Path('config/dream_bitget_bases.json')
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    symbols = fetch_bitget_symbols()
    symbols_list = sorted(list(symbols))
    
    # 保存为 JSON 数组
    with config_path.open('w', encoding='utf-8') as f:
        json.dump(symbols_list, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已保存 {len(symbols_list)} 个币种到: {config_path}")
    print(f"   示例币种: {', '.join(symbols_list[:10])}...")


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()



