#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试probability提取逻辑
"""
import json
from pathlib import Path

# 模拟模式269和181的trading_signals
pattern269 = {
    "trading_signals": [{
        "direction": "long",
        "probability": 70  # 这是百分比值
    }]
}

pattern181 = {
    "trading_signals": [{
        "direction": "short"
        # 没有probability字段
    }]
}

# 测试probability提取逻辑（从generate_signal_from_match）
def extract_probability(signal_dict, match_similarity):
    """模拟probability提取"""
    probability = signal_dict.get('probability', match_similarity)
    return probability

# 测试
similarity = 0.6184

signal1 = pattern269["trading_signals"][0]
prob1 = extract_probability(signal1, similarity)
print(f"信号1 probability: {prob1} (类型: {type(prob1).__name__})")

signal2 = pattern181["trading_signals"][0]
prob2 = extract_probability(signal2, similarity)
print(f"信号2 probability: {prob2} (类型: {type(prob2).__name__})")

# 计算评分
score1 = (similarity * 0.7 + prob1 * 0.3) * 100
score2 = (similarity * 0.7 + prob2 * 0.3) * 100

print(f"\n如果probability直接使用（不转换）:")
print(f"  信号1评分: {score1:.2f}")
print(f"  信号2评分: {score2:.2f}")

# 正确的转换（如果是百分比，应该除以100）
prob1_corrected = prob1 / 100 if prob1 > 1 else prob1
score1_corrected = (similarity * 0.7 + prob1_corrected * 0.3) * 100

print(f"\n如果probability>1则除以100:")
print(f"  信号1 probability: {prob1} -> {prob1_corrected}")
print(f"  信号1评分: {score1_corrected:.2f}")



