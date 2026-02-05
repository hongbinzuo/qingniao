#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Kimi CLI 批量分析图片
需要已登录的 Kimi CLI: kimi login
"""
import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def analyze_image_with_kimi(image_path: str, prompt: str = None) -> str:
    """
    使用 Kimi CLI 分析单张图片
    
    Args:
        image_path: 图片路径
        prompt: 自定义提示词
    
    Returns:
        Kimi 的分析结果
    """
    default_prompt = "Analyze this trading chart and identify the price action pattern. Reply with pattern name and brief description."
    user_prompt = prompt or default_prompt
    
    full_prompt = f"{user_prompt} Image: {image_path}"
    
    try:
        result = subprocess.run(
            ["kimi", "--print", "--prompt", full_prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            return f"Error: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: Timeout"
    except Exception as e:
        return f"Error: {e}"

def batch_analyze(images_dir: str, output_file: str = None):
    """
    批量分析目录中的图片
    
    Args:
        images_dir: 图片目录
        output_file: 输出文件路径
    """
    images_path = Path(images_dir)
    image_files = list(images_path.glob("*.png")) + list(images_path.glob("*.jpg"))
    
    results = []
    
    print(f"Found {len(image_files)} images to analyze")
    
    for i, img_path in enumerate(image_files[:10], 1):  # 限制前10张
        print(f"\n[{i}/{min(len(image_files), 10)}] Analyzing: {img_path.name}")
        
        result = analyze_image_with_kimi(str(img_path))
        results.append({
            "image": img_path.name,
            "analysis": result
        })
    
    # 保存结果
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\nResults saved to: {output_path}")
    
    return results

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze images using Kimi CLI")
    parser.add_argument("--image", "-i", help="Single image path")
    parser.add_argument("--dir", "-d", default="data/abu/images", 
                       help="Directory containing images")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--prompt", "-p", help="Custom analysis prompt")
    
    args = parser.parse_args()
    
    if args.image:
        # 单张图片分析
        print(f"Analyzing: {args.image}")
        result = analyze_image_with_kimi(args.image, args.prompt)
        print("\n" + "="*50)
        print(result)
    else:
        # 批量分析
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = args.output or f"outputs/kimi_analysis_{timestamp}.json"
        batch_analyze(args.dir, output)
