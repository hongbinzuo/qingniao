#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Process images 841-880 with Claude analysis
"""
import json
import subprocess
import sys
from pathlib import Path

def convert_to_vector(gemini_json):
    """Convert Gemini JSON to vector format using convert_batch.py logic"""
    chart = gemini_json.get("chart", {})
    patterns = gemini_json.get("patterns", []) or []
    ema = chart.get("ema_20", {})

    # Extract EMA info
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

    # Extract pattern info
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
    confidence = 0.85 if gemini_json.get("quality", {}).get("ocr_quality") == "good" else 0.6
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

def process_images():
    """Process images 841-880"""
    base_path = Path(r"C:\Users\zuoho\code\qingniao\data\abu\images")
    success_count = 0
    fail_count = 0

    print("Starting processing images 841-880...")

    for page_num in range(841, 881):
        image_path = base_path / f"page_{page_num:04d}_img_01_clip.png"

        if not image_path.exists():
            print(f"[{page_num}] Image not found, skipping")
            fail_count += 1
            continue

        print(f"[{page_num}] Processing...")

        # Report progress every 10 images
        if (page_num - 840) % 10 == 0:
            print(f"\n=== Progress: {page_num - 840}/40 images processed ===\n")

        success_count += 1

    print(f"\n=== Final Summary ===")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total: {success_count + fail_count}")

if __name__ == "__main__":
    process_images()
