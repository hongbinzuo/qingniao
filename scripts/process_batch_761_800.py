#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理图片761-800的批处理脚本
使用Claude API进行图片分析
"""
import json
import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
import anthropic

# 配置
API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    print("错误: 请设置环境变量 ANTHROPIC_API_KEY")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)

# 读取提示词
with open(r'C:\Users\zuoho\code\qingniao\config\abu_analyzer_prompt.md', 'r', encoding='utf-8') as f:
    ANALYZER_PROMPT = f.read()

def convert_to_vector(gemini_json):
    """将Gemini JSON转换为向量格式（基于convert_batch.py的逻辑）"""
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
    annotation_count = len(annotations)

    # 提取关键特征
    key_features = []
    kline_features = gemini_json.get("kline_features", [])
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

def analyze_image(image_path, page_num):
    """使用Claude API分析图片"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()

        import base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": ANALYZER_PROMPT
                    }
                ]
            }]
        )

        response_text = message.content[0].text.strip()

        # 清理响应，移除可能的markdown包裹
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        # 解析JSON
        gemini_json = json.loads(response_text)

        # 确保必要字段存在
        if "image_id" not in gemini_json:
            gemini_json["image_id"] = f"page_{page_num:04d}"
        if "page" not in gemini_json:
            gemini_json["page"] = page_num

        return gemini_json

    except Exception as e:
        print(f"  错误: {e}")
        return None

def process_single_image(page_num):
    """处理单张图片"""
    image_path = f"C:\\Users\\zuoho\\code\\qingniao\\data\\abu\\images\\page_{page_num:04d}_img_01_clip.png"

    # 检查图片是否存在
    if not os.path.exists(image_path):
        print(f"[{page_num}] 图片不存在，跳过")
        return False

    print(f"[{page_num}] 开始处理...")

    # 分析图片
    gemini_json = analyze_image(image_path, page_num)
    if not gemini_json:
        print(f"[{page_num}] 分析失败")
        return False

    # 转换为向量格式
    try:
        vector_json = convert_to_vector(gemini_json)
    except Exception as e:
        print(f"[{page_num}] 向量转换失败: {e}")
        return False

    # 保存临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(gemini_json, f, ensure_ascii=False, indent=2)
        gemini_file = f.name

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(vector_json, f, ensure_ascii=False, indent=2)
        vector_file = f.name

    # 调用save_agent_result.py
    try:
        result = subprocess.run(
            ['python', 'save_agent_result.py', str(page_num), image_path, gemini_file, vector_file],
            cwd=r'C:\Users\zuoho\code\qingniao',
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print(f"[{page_num}] 成功保存")
            return True
        else:
            print(f"[{page_num}] 保存失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"[{page_num}] 保存异常: {e}")
        return False
    finally:
        # 清理临时文件
        try:
            os.unlink(gemini_file)
            os.unlink(vector_file)
        except:
            pass

def main():
    """主函数"""
    print("=" * 60)
    print("开始处理图片 761-800 (共40张)")
    print("=" * 60)

    success_count = 0
    fail_count = 0
    skip_count = 0

    for i, page_num in enumerate(range(761, 801), 1):
        try:
            result = process_single_image(page_num)

            if result:
                success_count += 1
            elif os.path.exists(f"C:\\Users\\zuoho\\code\\qingniao\\data\\abu\\images\\page_{page_num:04d}_img_01_clip.png"):
                fail_count += 1
            else:
                skip_count += 1

            # 每10张报告一次进度
            if i % 10 == 0:
                print(f"\n进度报告 [{i}/40]:")
                print(f"  成功: {success_count}")
                print(f"  失败: {fail_count}")
                print(f"  跳过: {skip_count}")
                print()

            # 避免API限流
            time.sleep(1)

        except KeyboardInterrupt:
            print("\n\n用户中断")
            break
        except Exception as e:
            print(f"[{page_num}] 未预期错误: {e}")
            fail_count += 1

    print("\n" + "=" * 60)
    print("处理完成!")
    print(f"总计: 40张")
    print(f"成功: {success_count}")
    print(f"失败: {fail_count}")
    print(f"跳过: {skip_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()
