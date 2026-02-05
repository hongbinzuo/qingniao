#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process images 681-720 for ABU analysis
Agent-based processing with Claude API
"""

import json
import os
import sys
from pathlib import Path

# Configuration
START_PAGE = 681
END_PAGE = 720
IMAGE_DIR = r"C:\Users\zuoho\code\qingniao\data\abu\images"
TEMP_DIR = r"C:\Users\zuoho\code\qingniao\temp_results"

def get_image_path(page_num):
    """Get image path for given page number"""
    return os.path.join(IMAGE_DIR, f"page_{page_num:04d}_img_01_clip.png")

def check_image_exists(page_num):
    """Check if image exists"""
    path = get_image_path(page_num)
    return os.path.exists(path)

def convert_to_vector_format(gemini_json):
    """Convert Gemini JSON to vector format using convert_batch.py logic"""
    chart = gemini_json.get("chart", {})
    patterns = gemini_json.get("patterns", []) or []
    ema = chart.get("ema_20", {})

    # Extract EMA information
    ema_relation = ema.get("relation", "crossing")
    ema_slope = ema.get("slope", "flat")

    # Calculate EMA distance
    if ema_relation == "above":
        ema_dist = 0.6 if ema_slope == "up" else 0.3
    elif ema_relation == "below":
        ema_dist = -0.6 if ema_slope == "down" else -0.3
    else:
        ema_dist = 0.0

    # Extract trend direction
    direction_bias = chart.get("direction_bias", "neutral")
    trend_direction = {"long": 0.8, "short": -0.8, "neutral": 0.0}.get(direction_bias, 0.0)

    # Extract market cycle
    market_cycle = chart.get("market_cycle", "trading_range")
    trend_maturity = chart.get("trend_maturity", "middle")

    # Extract pattern information
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

    # Calculate confidence
    confidence = 0.6
    if gemini_json.get("quality", {}).get("ocr_quality") == "good":
        confidence = 0.85
    if patterns:
        confidence = sum(p.get("confidence", 0.5) for p in patterns) / len(patterns)

    # Count annotations
    annotations = gemini_json.get("annotations_text", [])
    annotation_count = len(annotations)

    # Extract key features
    key_features = []
    kline_features = gemini_json.get("kline_features", [])
    for kf in kline_features[:3]:
        feat = kf.get("feature")
        if feat:
            key_features.append(feat)

    if primary_pattern != "none":
        key_features.insert(0, primary_pattern)

    key_features = key_features[:5]

    # Generate vector summary
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

def main():
    """Main processing function"""
    # Create temp directory
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Check which images exist
    existing_images = []
    missing_images = []

    for page_num in range(START_PAGE, END_PAGE + 1):
        if check_image_exists(page_num):
            existing_images.append(page_num)
        else:
            missing_images.append(page_num)

    print(f"Total images to process: {len(existing_images)}")
    print(f"Missing images: {len(missing_images)}")
    if missing_images:
        print(f"Missing pages: {missing_images[:10]}{'...' if len(missing_images) > 10 else ''}")

    return existing_images

if __name__ == "__main__":
    images = main()
    print(f"\nReady to process {len(images)} images")
    print(f"Range: {START_PAGE} to {END_PAGE}")
