#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查评分计算逻辑
"""
import sys

# 测试评分计算
similarity = 0.6184  # 61.84%

# 信号1: probability = 70 (可能是70%？)
probability1 = 70  # 如果是百分比
score1_a = (similarity * 0.7 + (probability1 / 100) * 0.3) * 100
score1_b = (similarity * 0.7 + probability1 * 0.3) * 100  # 如果是0-1之间的值
score1_c = (similarity * 0.7 + 0.7 * 0.3) * 100  # 如果是0.7

# 信号2: probability 默认值
probability2 = 0.6184  # 默认使用similarity
score2 = (similarity * 0.7 + probability2 * 0.3) * 100

print("=" * 80)
print("评分计算测试")
print("=" * 80)
print(f"\n相似度: {similarity} ({similarity*100:.2f}%)")
print(f"\n信号1 (实际评分: 2143.29):")
print(f"  如果probability=70 (百分比): score = {score1_a:.2f}")
print(f"  如果probability=70 (0-1值): score = {score1_b:.2f}")
print(f"  如果probability=0.7 (正确): score = {score1_c:.2f}")
print(f"\n信号2 (实际评分: 61.84):")
print(f"  如果probability=similarity (0.6184): score = {score2:.2f}")

# 反推信号1的probability
target_score1 = 2143.29
# score = (similarity * 0.7 + probability * 0.3) * 100
# score / 100 = similarity * 0.7 + probability * 0.3
# score / 100 - similarity * 0.7 = probability * 0.3
# probability = (score / 100 - similarity * 0.7) / 0.3
prob1_inferred = (target_score1 / 100 - similarity * 0.7) / 0.3
print(f"\n反推信号1的probability值:")
print(f"  从评分2143.29反推: probability = {prob1_inferred:.2f}")
print(f"  如果这是百分比，应该是: {prob1_inferred * 100:.0f}%")
print(f"  如果这是0-1值，应该是: {prob1_inferred:.2f}")

# 检查generate_signal_from_match中的probability提取
print(f"\n可能的问题:")
print(f"  1. probability可能是百分比值（如70）而不是0-1之间的值（如0.7）")
print(f"  2. 如果probability=70，计算时应该除以100")



