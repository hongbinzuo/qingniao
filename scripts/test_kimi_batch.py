#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Kimi CLI 批量处理机制
验证：
1. 每次调用是否独立 session
2. Token 使用情况
3. 并发/批处理能力
"""
import subprocess
import time
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

def analyze_single_image(image_path: str, prompt: str) -> dict:
    """
    单张图片分析 - 每次调用都是独立 session
    
    Returns:
        {
            "image": str,
            "success": bool,
            "duration": float,
            "token_usage": dict,
            "result": str,
            "error": str
        }
    """
    start_time = time.time()
    
    full_prompt = f"{prompt}\n\nAnalyze this image: {image_path}"
    
    try:
        result = subprocess.run(
            ["kimi", "--print", "--prompt", full_prompt],
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )
        
        duration = time.time() - start_time
        
        if result.returncode == 0:
            output = result.stdout
            
            # 提取 token 使用情况
            token_usage = extract_token_usage(output)
            
            return {
                "image": Path(image_path).name,
                "success": True,
                "duration": round(duration, 2),
                "token_usage": token_usage,
                "result": output[:500] + "..." if len(output) > 500 else output,
                "error": None
            }
        else:
            return {
                "image": Path(image_path).name,
                "success": False,
                "duration": round(duration, 2),
                "token_usage": {},
                "result": None,
                "error": result.stderr[:200]
            }
            
    except subprocess.TimeoutExpired:
        return {
            "image": Path(image_path).name,
            "success": False,
            "duration": round(time.time() - start_time, 2),
            "token_usage": {},
            "result": None,
            "error": "Timeout"
        }
    except Exception as e:
        return {
            "image": Path(image_path).name,
            "success": False,
            "duration": round(time.time() - start_time, 2),
            "token_usage": {},
            "result": None,
            "error": str(e)
        }

def extract_token_usage(output: str) -> dict:
    """从输出中提取 token 使用情况"""
    try:
        # 查找 TokenUsage 部分
        if "TokenUsage" in output:
            # 简单提取数值
            import re
            
            # 提取 input_cache_read
            cache_read = re.search(r'input_cache_read[=:]\s*(\d+)', output)
            # 提取 input_other
            input_other = re.search(r'input_other[=:]\s*(\d+)', output)
            # 提取 output
            output_tokens = re.search(r'"?output"?[=:]\s*(\d+)', output)
            
            return {
                "input_cache_read": int(cache_read.group(1)) if cache_read else 0,
                "input_other": int(input_other.group(1)) if input_other else 0,
                "output": int(output_tokens.group(1)) if output_tokens else 0,
                "total": sum([
                    int(cache_read.group(1)) if cache_read else 0,
                    int(input_other.group(1)) if input_other else 0,
                    int(output_tokens.group(1)) if output_tokens else 0
                ])
            }
    except:
        pass
    
    return {}

def test_serial_processing(image_paths: list, prompt: str):
    """串行处理测试"""
    print("\n" + "="*60)
    print("SERIAL PROCESSING TEST (Sequential)")
    print("="*60)
    print(f"Total images: {len(image_paths)}")
    
    results = []
    start_total = time.time()
    
    for i, img_path in enumerate(image_paths, 1):
        print(f"\n[{i}/{len(image_paths)}] Processing: {Path(img_path).name}")
        result = analyze_single_image(img_path, prompt)
        results.append(result)
        
        if result["success"]:
            print(f"  [OK] Success in {result['duration']}s")
            if result['token_usage']:
                print(f"  Tokens: {result['token_usage']}")
        else:
            print(f"  [FAIL] {result['error']}")
    
    total_time = time.time() - start_total
    
    # 统计
    success_count = sum(1 for r in results if r["success"])
    total_tokens = sum(r["token_usage"].get("total", 0) for r in results if r["token_usage"])
    
    print(f"\n--- Summary ---")
    print(f"Total time: {total_time:.2f}s")
    print(f"Success: {success_count}/{len(image_paths)}")
    print(f"Total tokens: {total_tokens}")
    print(f"Avg time per image: {total_time/len(image_paths):.2f}s")
    
    return results

def test_parallel_processing(image_paths: list, prompt: str, max_workers: int = 3):
    """并行处理测试"""
    print("\n" + "="*60)
    print(f"PARALLEL PROCESSING TEST (max_workers={max_workers})")
    print("="*60)
    print(f"Total images: {len(image_paths)}")
    print("Note: Each process is independent with its own session")
    
    results = []
    start_total = time.time()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_image = {
            executor.submit(analyze_single_image, img_path, prompt): img_path 
            for img_path in image_paths
        }
        
        # 收集结果
        for future in as_completed(future_to_image):
            img_path = future_to_image[future]
            try:
                result = future.result()
                results.append(result)
                
                if result["success"]:
                    print(f"  [OK] {result['image']}: {result['duration']}s")
                else:
                    print(f"  [FAIL] {result['image']}: {result['error']}")
                    
            except Exception as e:
                results.append({
                    "image": Path(img_path).name,
                    "success": False,
                    "error": str(e)
                })
                print(f"  [FAIL] {Path(img_path).name}: {e}")
    
    total_time = time.time() - start_total
    
    # 统计
    success_count = sum(1 for r in results if r["success"])
    total_tokens = sum(r["token_usage"].get("total", 0) for r in results if r["token_usage"])
    
    print(f"\n--- Summary ---")
    print(f"Total time: {total_time:.2f}s")
    print(f"Success: {success_count}/{len(image_paths)}")
    print(f"Total tokens: {total_tokens}")
    print(f"Speedup vs serial: ~{len(image_paths) * sum(r['duration'] for r in results if r['success'])/max(1, total_time):.1f}x")
    
    return results

def estimate_batch_capacity():
    """
    估算批处理能力
    基于 Gemini/Kimi 的 token 限制
    """
    print("\n" + "="*60)
    print("BATCH CAPACITY ESTIMATION")
    print("="*60)
    
    # 估算值（基于观察）
    single_image_base64_tokens = 6000  # 一张图片的 base64 大约 6000 tokens
    prompt_tokens = 1500  # 向量提示词约 1500 tokens
    output_tokens = 800  # JSON 输出约 800 tokens
    context_limit = 128000  # 假设上下文限制 128K
    
    print(f"Context limit: {context_limit:,} tokens")
    print(f"Prompt tokens: {prompt_tokens:,}")
    print(f"Single image (base64): ~{single_image_base64_tokens:,} tokens")
    print(f"Expected output: ~{output_tokens:,} tokens")
    
    # 计算每批最多图片数
    available_for_images = context_limit - prompt_tokens - output_tokens
    max_images_per_batch = available_for_images // single_image_base64_tokens
    
    print(f"\nTheoretical max images per batch: {max_images_per_batch}")
    print(f"Recommended batch size: 1-3 images")
    print(f"Reason: Images are large in base64, multiple images quickly exhaust context")
    
    return {
        "theoretical_max": max_images_per_batch,
        "recommended": 1,
        "single_image_tokens": single_image_base64_tokens + prompt_tokens + output_tokens
    }

if __name__ == "__main__":
    import sys
    
    # 向量提示词（简化版用于测试）
    VECTOR_PROMPT_SHORT = """You are a professional price action analyst. 
Extract structured features from the chart image and output strict JSON only.

Key fields to extract:
- slide_type: chart|separator|text
- market_cycle: trend|trading_range|spike_channel
- direction_bias: long|short|neutral
- patterns: array of {pattern_name, pattern_family, confidence}
- kline_features: array of detected features

Output valid JSON only, no additional text."""
    
    # 查找测试图片
    image_dir = Path("data/abu/images")
    if not image_dir.exists():
        print(f"Image directory not found: {image_dir}")
        sys.exit(1)
    
    # 获取前3张图片用于测试
    test_images = list(image_dir.glob("*.png"))[:3]
    if not test_images:
        print("No PNG images found for testing")
        sys.exit(1)
    
    print(f"Found {len(test_images)} test images")
    
    # 估算批处理能力
    capacity = estimate_batch_capacity()
    
    # 串行测试
    serial_results = test_serial_processing([str(p) for p in test_images], VECTOR_PROMPT_SHORT)
    
    # 并行测试（如果有多张图片）
    if len(test_images) > 1:
        time.sleep(2)  # 短暂暂停
        parallel_results = test_parallel_processing([str(p) for p in test_images], VECTOR_PROMPT_SHORT, max_workers=2)
    
    # 保存结果
    output_file = "outputs/kimi_batch_test_results.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "serial_results": serial_results,
            "capacity_estimate": capacity,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to: {output_file}")
