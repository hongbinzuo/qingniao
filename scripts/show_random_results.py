#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""随机展示几张图片的识别结果"""
import sys
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    if not OUTPUT_FILE.exists():
        print(f"❌ 输出文件不存在: {OUTPUT_FILE}")
        return
    
    # 读取所有记录
    records = []
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception as e:
                    continue
    
    if not records:
        print("❌ 没有找到任何记录")
        return
    
    print("=" * 80)
    print(f"随机抽取识别结果（共 {len(records)} 条记录）")
    print("=" * 80)
    print()
    
    # 先筛选出有成功解析结果的记录
    successful_records = []
    for record in records:
        result = record.get('result', {})
        if result:
            raw = result.get('raw', '')
            parse_error = result.get('parse_error', '')
            # 尝试解析，如果能解析就认为是成功的
            if raw and not parse_error:
                try:
                    # 简单检查是否包含关键字段
                    if 'chart_overview' in raw or 'patterns' in raw or 'trading_signals' in raw:
                        successful_records.append(record)
                except:
                    pass
    
    # 如果没有成功记录，使用所有记录
    if not successful_records:
        successful_records = records
    
    # 随机抽取5条
    sample_size = min(5, len(successful_records))
    samples = random.sample(successful_records, sample_size)
    
    for idx, record in enumerate(samples, 1):
        print("=" * 80)
        print(f"样本 #{idx}")
        print("=" * 80)
        
        # 基本信息
        image_path = record.get('image', record.get('image_path', 'N/A'))
        print(f"📷 图片: {Path(image_path).name if image_path != 'N/A' else 'N/A'}")
        print(f"📄 页码: {record.get('page', 'N/A')}")
        print(f"⏱️  耗时: {record.get('elapsed_seconds', 0):.2f}秒")
        print(f"💰 成本: ${record.get('estimated_cost_usd', 0):.6f}")
        print(f"💾 缓存: {'是' if record.get('cached', False) else '否'}")
        
        # 获取result
        result = record.get('result', {})
        if not result:
            print("❌ 没有分析结果")
            print()
            continue
        
        # 状态判断
        parse_error = result.get('parse_error', '')
        raw = result.get('raw', '')
        if parse_error:
            print(f"⚠️  状态: 部分成功（JSON解析失败，但有原始数据）")
            print(f"   错误: {parse_error}")
        elif raw:
            print(f"✅ 状态: 成功")
        else:
            print(f"❌ 状态: 失败")
        
        print()
        
        # 尝试解析raw JSON
        analysis = {}
        if raw:
            try:
                # raw可能是完整的JSON字符串，也可能被截断
                # 尝试直接解析
                if raw.startswith('```json'):
                    # 提取markdown代码块中的JSON
                    import re
                    json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw, re.DOTALL)
                    if json_match:
                        raw = json_match.group(1)
                elif raw.startswith('```'):
                    json_match = re.search(r'```\s*(\{.*?\})\s*```', raw, re.DOTALL)
                    if json_match:
                        raw = json_match.group(1)
                
                # 尝试找到第一个{到最后一个}
                if not raw.strip().startswith('{'):
                    first_brace = raw.find('{')
                    last_brace = raw.rfind('}')
                    if first_brace >= 0 and last_brace > first_brace:
                        raw = raw[first_brace:last_brace+1]
                
                analysis = json.loads(raw)
            except Exception as e:
                # 如果解析失败，尝试从raw中提取部分信息
                print(f"⚠️  JSON解析失败: {str(e)[:100]}")
                print(f"📝 原始数据（前500字符）:")
                print(f"   {raw[:500]}...")
                print()
                continue
        
        # Gemini分析结果
        if not analysis:
            print("❌ 无法解析分析结果")
            print()
            continue
        if analysis:
            print("📊 Gemini分析结果:")
            print("-" * 80)
            
            # Chart Overview
            chart_overview = analysis.get('chart_overview', {})
            if chart_overview:
                print("\n【图表概览】")
                if isinstance(chart_overview, dict):
                    print(f"  时间框架: {chart_overview.get('timeframe', 'N/A')}")
                    print(f"  价格范围: {chart_overview.get('price_range', 'N/A')}")
                    layout = chart_overview.get('layout_description', '')
                    if layout:
                        print(f"  布局描述: {layout[:200]}..." if len(layout) > 200 else f"  布局描述: {layout}")
                else:
                    print(f"  {str(chart_overview)[:200]}...")
            
            # Complete Price Path
            price_path = analysis.get('complete_price_path', {})
            if price_path:
                print("\n【完整价格路径】")
                if isinstance(price_path, dict):
                    journey = price_path.get('price_journey', '')
                    if journey:
                        print(f"  价格历程: {journey[:200]}..." if len(journey) > 200 else f"  价格历程: {journey}")
                    swings = price_path.get('major_swings', [])
                    if swings:
                        print(f"  主要摆动: {len(swings)}个")
                else:
                    print(f"  {str(price_path)[:200]}...")
            
            # Complete Narrative
            narrative = analysis.get('complete_narrative', '')
            if narrative:
                print("\n【完整叙述】")
                print(f"  {narrative[:300]}..." if len(narrative) > 300 else f"  {narrative}")
            
            # Patterns
            patterns = analysis.get('patterns', [])
            if patterns:
                print(f"\n【识别到的模式】({len(patterns)}个)")
                for i, pattern in enumerate(patterns[:5], 1):  # 最多显示5个
                    if isinstance(pattern, dict):
                        ptype = pattern.get('type', 'N/A')
                        pname = pattern.get('name', '')
                        confidence = pattern.get('confidence', 0)
                        print(f"  {i}. {ptype}" + (f" ({pname})" if pname else "") + f" - 置信度: {confidence}")
                    else:
                        print(f"  {i}. {pattern}")
            
            # Trading Signals
            signals = analysis.get('trading_signals', [])
            if signals:
                print(f"\n【交易信号】({len(signals)}个)")
                for i, signal in enumerate(signals[:3], 1):  # 最多显示3个
                    if isinstance(signal, dict):
                        direction = signal.get('direction', 'N/A')
                        entry = signal.get('entry', 'N/A')
                        stop_loss = signal.get('stop_loss', 'N/A')
                        take_profit = signal.get('take_profit', 'N/A')
                        probability = signal.get('probability', 'N/A')
                        print(f"  {i}. {direction.upper()}")
                        print(f"     入场: {entry}, 止损: {stop_loss}, 止盈: {take_profit}")
                        print(f"     概率: {probability}")
                    else:
                        print(f"  {i}. {signal}")
            
            # Key Features
            key_features = analysis.get('key_features', [])
            if key_features:
                print(f"\n【关键特征】({len(key_features)}个)")
                for i, feature in enumerate(key_features[:5], 1):  # 最多显示5个
                    print(f"  {i}. {feature}")
            
            # K-line Behaviors
            kline_behaviors = analysis.get('kline_behaviors', [])
            if kline_behaviors:
                print(f"\n【K线行为】({len(kline_behaviors)}个)")
                for i, behavior in enumerate(kline_behaviors[:5], 1):  # 最多显示5个
                    if isinstance(behavior, dict):
                        btype = behavior.get('type', 'N/A')
                        desc = behavior.get('description', '')
                        print(f"  {i}. {btype}: {desc[:100]}..." if len(desc) > 100 else f"  {i}. {btype}: {desc}")
                    else:
                        print(f"  {i}. {behavior}")
        
        # 如果有错误信息
        error = record.get('error', '')
        if error:
            print(f"\n⚠️  错误信息: {error[:200]}...")
        
        # 如果有原始文本（解析失败时）
        raw_text = record.get('raw_text', '')
        if raw_text and status != 'success':
            print(f"\n📝 原始文本（前200字符）: {raw_text[:200]}...")
        
        print()
        print()
    
    print("=" * 80)
    print(f"✅ 已展示 {sample_size} 条随机样本")
    print("=" * 80)

if __name__ == '__main__':
    main()

