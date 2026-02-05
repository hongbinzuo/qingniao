#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理图片921-960的批处理脚本
"""
import json
import sys
import os
import subprocess
from pathlib import Path

def convert_to_vector(gemini_json):
    """将Gemini JSON转换为向量格式"""
    chart = gemini_json.get("chart", {})
    patterns = gemini_json.get("patterns", []) or []
    ema = chart.get("ema_20", {})

    # 提取EMA信息
    ema_relation = ema.get("relation", "crossing")
    ema_slope = ema.get("slope", "flat")

    # 计算EMA距离
    if ema_relation == "above":
        ema_dist = 0.6 if ema_slope == "up" else 0.3
    elif ema_relation == "below":
        ema_dist = -0.6 if ema_slope == "down" else -0.3
    else:
        ema_dist = 0.0

    # 提取趋势方向
    direction_bias = chart.get("direction_bias", "neutral")
    trend_direction = {"long": 0.8, "short": -0.8, "neutral": 0.0}.get(direction_bias, 0.0)

    # 提取市场周期
    market_cycle = chart.get("market_cycle", "trading_range")
    trend_maturity = chart.get("trend_maturity", "middle")

    # 提取模式信息
    primary_pattern = "none"
    secondary_pattern = "none"
    pattern_direction = direction_bias
    complexity = 0.5

    if patterns:
        primary = patterns[0]
        primary_pattern = primary.get("pattern_family", "none")
        pattern_direction = primary.get("direction_bias", direction_bias)
        complexity = min(1.0, 0.3 + len(patterns) * 0.2)

        if len(patterns) > 1:
            secondary_pattern = patterns[1].get("pattern_family", "none")

    # 计算置信度
    confidence = 0.6
    if gemini_json.get("quality", {}).get("ocr_quality") == "good":
        confidence = 0.85
    if patterns:
        confidence = sum(p.get("confidence", 0.5) for p in patterns) / len(patterns)

    # 统计标注数量
    annotations = gemini_json.get("annotations_text", [])
    annotation_count = len(annotations) if annotations else 0

    # 提取关键特征
    key_features = []
    kline_features = gemini_json.get("kline_features", [])
    if kline_features:
        for kf in kline_features[:3]:
            feat = kf.get("feature")
            if feat:
                key_features.append(feat)

    if primary_pattern != "none":
        key_features.insert(0, primary_pattern)

    key_features = key_features[:5]

    # 生成向量摘要
    summary_parts = [primary_pattern]
    if trend_maturity:
        summary_parts.append(trend_maturity)
    if ema_relation:
        summary_parts.append(ema_relation + "_ema")
    vector_summary = "_".join(filter(None, summary_parts))

    return {
        "trend_vector": {
            "direction": round(trend_direction, 2),
            "ema_distance": round(ema_dist, 2),
            "volatility": 0.5,
            "slope_strength": round(abs(trend_direction), 2)
        },
        "pattern_features": {
            "primary": primary_pattern,
            "secondary": secondary_pattern,
            "direction": pattern_direction,
            "complexity": round(complexity, 2)
        },
        "market_context": {
            "cycle": market_cycle,
            "maturity": trend_maturity,
            "timeframe": gemini_json.get("timeframe_hint", "5m")
        },
        "metadata": {
            "confidence": round(confidence, 2),
            "annotation_count": annotation_count,
            "key_features": key_features,
            "vector_summary": vector_summary
        }
    }

def process_single_image(page_num):
    """处理单张图片"""
    image_path = f"C:\\Users\\zuoho\\code\\qingniao\\data\\abu\\images\\page_{page_num:04d}_img_01_clip.png"

    # 检查图片是否存在
    if not os.path.exists(image_path):
        print(f"✗ Page {page_num}: Image not found")
        return False

    # 这里需要调用Claude API分析图片
    # 由于我们在Claude Code环境中，图片分析会在主流程中完成
    # 这个脚本主要用于保存结果

    return True

if __name__ == "__main__":
    start_page = 921
    end_page = 960

    print(f"准备处理图片 {start_page}-{end_page} (共 {end_page - start_page + 1} 张)")

    # 检查图片存在性
    existing_images = []
    for page_num in range(start_page, end_page + 1):
        image_path = f"C:\\Users\\zuoho\\code\\qingniao\\data\\abu\\images\\page_{page_num:04d}_img_01_clip.png"
        if os.path.exists(image_path):
            existing_images.append(page_num)

    print(f"找到 {len(existing_images)} 张图片")
    print(f"图片范围: {existing_images[0] if existing_images else 'N/A'} - {existing_images[-1] if existing_images else 'N/A'}")
