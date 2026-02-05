#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量转换Gemini JSON为向量格式 - 使用Kimi Code API
"""
import json
import psycopg2
import time
import sys
from pathlib import Path

# ==========================================
# 配置区域 - 请修改以下配置
# ==========================================
API_KEY = "sk-kimi-M74EL3Df"  # 请替换为你的完整API Key
BATCH_SIZE = 5  # 每批处理数量，建议5-10
DELAY_SECONDS = 2  # 每批间隔，避免频控
# ==========================================

VECTOR_PROMPT = """你是专业价格行为特征提取专家。请将Gemini的详细图表分析转换为紧凑的向量特征格式，用于相似度检索。

【输入】Gemini生成的详细JSON分析
【输出】紧凑向量特征JSON

【转换规则】
1. trend_direction: 趋势方向，-1.0到1.0 (1.0=极强上涨, -1.0=极强下跌, 0=震荡)
2. trend_slope: 趋势斜率强度，0.0到1.0
3. volatility: 波动率，0.0到1.0 (0=极低波动, 1=极高波动)
4. ema_distance: 价格与EMA20距离，-1.0到1.0 (1=远上方, -1=远下方, 0=交叉)
5. pattern_complexity: 形态复杂度，0.0到1.0 (标注越多越复杂)
6. primary_pattern: 主模式类型 (wedge/trend/reversal/triangle/gap/breakout/none)
7. secondary_pattern: 次模式类型
8. direction_bias: 方向偏好 (long/short/neutral)
9. market_cycle: 市场周期 (trend/trading_range/spike_channel/tight_channel/climactic)
10. confidence_score: 整体置信度，0.0到1.0
11. annotation_count: 图上文字标注数量
12. key_features: 关键特征列表 (最多5个)
13. vector_summary: 一句话向量签名，用于快速匹配

【示例输入】
{"chart": {"direction_bias": "long", "ema_20": {"relation": "above", "slope": "up"}}, "patterns": [{"pattern_family": "wedge", "pattern_name": "Wedge Top"}]}

【示例输出】
{
  "trend_vector": {
    "direction": 0.75,
    "slope": 0.68,
    "volatility": 0.45,
    "ema_distance": 0.62
  },
  "pattern_features": {
    "primary": "wedge",
    "secondary": "none",
    "direction": "short",
    "complexity": 0.7
  },
  "market_context": {
    "cycle": "trend",
    "maturity": "late",
    "timeframe": "5m"
  },
  "metadata": {
    "confidence": 0.85,
    "annotation_count": 8,
    "key_features": ["wedge_top", "3_pushes", "above_ema"],
    "vector_summary": "wedge_top_late_trend_above_ema"
  }
}

【要求】
- 只输出JSON，不要解释
- 数值基于Gemini分析合理推断
- vector_summary用下划线连接关键词
- 未知字段设为null

请转换以下Gemini分析："""

def convert_single(gemini_json: dict) -> dict:
    """将Gemini JSON转换为向量格式（规则-based，不调用API）"""
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
    confidence = gemini_json.get("quality", {}).get("ocr_quality") == "good" and 0.85 or 0.6
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
            "volatility": 0.5,  # 默认值
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

def process_batch():
    """处理300张图片的批量转换"""
    # 加载选中的300张
    with open('selected_300_images.json', 'r', encoding='utf-8') as f:
        images = json.load(f)
    
    print(f"准备处理 {len(images)} 张图片...")
    
    # 连接数据库
    conn = psycopg2.connect(
        host='localhost', port=5432, database='qingniao_abu',
        user='abu_user', password='Abu2026!Secure'
    )
    cursor = conn.cursor()
    
    # 创建向量表（如果不存在）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pattern_vectors (
            id SERIAL PRIMARY KEY,
            pattern_library_id INTEGER REFERENCES pattern_library(id),
            image_path TEXT,
            source_page INTEGER,
            trend_vector JSONB,
            pattern_features JSONB,
            market_context JSONB,
            metadata JSONB,
            vector_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 检查是否已有数据
    cursor.execute("SELECT pattern_library_id FROM pattern_vectors")
    existing_ids = set(row[0] for row in cursor.fetchall())
    
    # 过滤已处理的
    to_process = [img for img in images if img['id'] not in existing_ids]
    print(f"已存在 {len(existing_ids)} 条，待处理 {len(to_process)} 条")
    
    if not to_process:
        print("所有图片已处理完成！")
        conn.close()
        return
    
    # 批量处理
    processed = 0
    for i, img_data in enumerate(to_process, 1):
        try:
            # 解析Gemini JSON
            gemini_json = json.loads(img_data['gemini_json'])
            
            # 转换为向量格式（规则-based，快速）
            vector_data = convert_single(gemini_json)
            
            # 写入数据库
            cursor.execute('''
                INSERT INTO pattern_vectors 
                (pattern_library_id, image_path, source_page, trend_vector, pattern_features, market_context, metadata, vector_summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                img_data['id'],
                img_data['image_path'],
                img_data['source_page'],
                json.dumps(vector_data['trend_vector']),
                json.dumps(vector_data['pattern_features']),
                json.dumps(vector_data['market_context']),
                json.dumps(vector_data['metadata']),
                vector_data['metadata']['vector_summary']
            ))
            
            processed += 1
            
            if i % BATCH_SIZE == 0:
                conn.commit()
                print(f"[{i}/{len(to_process)}] 已处理 {processed} 张...")
                time.sleep(DELAY_SECONDS)
            
        except Exception as e:
            print(f"Error processing {img_data.get('image_path', 'unknown')}: {e}")
            continue
    
    conn.commit()
    conn.close()
    print(f"\n✅ 完成！共处理 {processed} 张图片，数据已写入 pattern_vectors 表")

if __name__ == "__main__":
    process_batch()
