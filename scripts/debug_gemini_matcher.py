#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""调试Gemini模式匹配器"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from generate_comprehensive_trading_plans import get_kline_binance
from abu.gemini_pattern_matcher import GeminiPatternMatcher

if __name__ == '__main__':
    # 测试BTC
    print("获取BTC K线数据...")
    kl15m = get_kline_binance('BTC', '15m', 200)
    kl1h = get_kline_binance('BTC', '1h', 100)
    
    print(f"15m K线: {len(kl15m)} 根")
    print(f"1h K线: {len(kl1h)} 根")
    
    print("\n初始化匹配器...")
    matcher = GeminiPatternMatcher()
    print(f"模式库: {len(matcher.pattern_library)} 个模式")
    
    print("\n提取实时特征...")
    features = matcher.extract_realtime_features(kl15m, kl1h)
    print(f"特征: {json.dumps(features, indent=2, ensure_ascii=False)[:500]}")
    
    print("\n测试匹配（前5个模式）...")
    for i, pattern in enumerate(matcher.pattern_library[:5], 1):
        similarity = matcher.calculate_similarity(features, pattern['gemini_annotation'])
        print(f"{i}. Pattern {pattern['id']} ({pattern['pattern_name']}): 相似度 = {similarity:.3f}")



