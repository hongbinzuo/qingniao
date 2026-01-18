#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从数据库随机展示几张图片的识别结果"""
import sys
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 查询有Gemini标注的记录，优先选择有完整叙述的
    records = conn.execute('''
        SELECT id, pattern_name, image_path, gemini_annotation_json, 
               pattern_type, key_features, direction, confidence
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL 
          AND gemini_annotation_json != ''
          AND gemini_annotation_json LIKE '%complete_narrative%'
        ORDER BY RANDOM()
        LIMIT 5
    ''').fetchall()
    
    # 如果不够5条，补充其他记录
    if len(records) < 5:
        more_records = conn.execute('''
            SELECT id, pattern_name, image_path, gemini_annotation_json, 
                   pattern_type, key_features, direction, confidence
            FROM pattern_library
            WHERE gemini_annotation_json IS NOT NULL 
              AND gemini_annotation_json != ''
              AND id NOT IN (SELECT id FROM pattern_library WHERE gemini_annotation_json LIKE '%complete_narrative%' LIMIT 5)
            ORDER BY RANDOM()
            LIMIT ?
        ''', [5 - len(records)]).fetchall()
        records = list(records) + list(more_records)
    
    if not records:
        print("❌ 数据库中没有找到Gemini标注的记录")
        return
    
    print("=" * 80)
    print(f"随机抽取识别结果（从数据库，共 {len(records)} 条）")
    print("=" * 80)
    print()
    
    for idx, record in enumerate(records, 1):
        id_val, pattern_name, image_path, gemini_json, pattern_type, key_features, direction, confidence = record
        
        print("=" * 80)
        print(f"样本 #{idx}")
        print("=" * 80)
        
        # 基本信息
        print(f"📷 图片: {Path(image_path).name if image_path else 'N/A'}")
        print(f"📝 模式名称: {pattern_name}")
        print(f"🏷️  模式类型: {pattern_type or 'N/A'}")
        print(f"➡️  方向: {direction or 'N/A'}")
        print(f"📊 置信度: {confidence or 'N/A'}")
        print()
        
        # 解析Gemini JSON
        try:
            analysis = json.loads(gemini_json)
        except Exception as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"📝 原始JSON（前500字符）: {gemini_json[:500]}...")
            print()
            continue
        
        # Chart Overview
        chart_overview = analysis.get('chart_overview', {})
        if chart_overview:
            print("【图表概览】")
            if isinstance(chart_overview, dict):
                print(f"  时间框架: {chart_overview.get('timeframe', 'N/A')}")
                price_range = chart_overview.get('price_range', {})
                if isinstance(price_range, dict):
                    high = price_range.get('high', 'N/A')
                    low = price_range.get('low', 'N/A')
                    print(f"  价格范围: {low} - {high}")
                layout = chart_overview.get('layout_description', '')
                if layout:
                    print(f"  布局描述: {layout[:200]}..." if len(layout) > 200 else f"  布局描述: {layout}")
            print()
        
        # Complete Price Path
        price_path = analysis.get('complete_price_path', {})
        if price_path:
            print("【完整价格路径】")
            if isinstance(price_path, dict):
                journey = price_path.get('price_journey', '')
                if journey:
                    print(f"  价格历程: {journey[:300]}..." if len(journey) > 300 else f"  价格历程: {journey}")
                swings = price_path.get('major_swings', [])
                if swings:
                    print(f"  主要摆动: {len(swings)}个")
                    for i, swing in enumerate(swings[:3], 1):
                        if isinstance(swing, dict):
                            stype = swing.get('type', 'N/A')
                            sfrom = swing.get('from', 'N/A')
                            sto = swing.get('to', 'N/A')
                            print(f"    {i}. {stype}: {sfrom} → {sto}")
            print()
        
        # Complete Narrative
        narrative = analysis.get('complete_narrative', '')
        if narrative:
            print("【完整叙述】")
            print(f"  {narrative[:500]}..." if len(narrative) > 500 else f"  {narrative}")
            print()
        
        # Chart Overview (详细)
        chart_overview = analysis.get('chart_overview', {})
        if chart_overview and isinstance(chart_overview, dict):
            print("【图表概览详情】")
            print(f"  时间框架: {chart_overview.get('timeframe', 'N/A')}")
            print(f"  时间周期: {chart_overview.get('time_period', 'N/A')}")
            price_range = chart_overview.get('price_range', {})
            if isinstance(price_range, dict):
                high = price_range.get('high', 'N/A')
                low = price_range.get('low', 'N/A')
                print(f"  价格范围: {low} - {high}")
            chart_structure = chart_overview.get('chart_structure', '')
            if chart_structure:
                print(f"  图表结构: {chart_structure[:200]}..." if len(chart_structure) > 200 else f"  图表结构: {chart_structure}")
            print()
        
        # Patterns
        patterns = analysis.get('patterns', [])
        if patterns:
            print(f"【识别到的模式】({len(patterns)}个)")
            for i, pattern in enumerate(patterns[:5], 1):
                if isinstance(pattern, dict):
                    ptype = pattern.get('type', 'N/A')
                    pname = pattern.get('name', '')
                    pconf = pattern.get('confidence', 0)
                    location = pattern.get('location', '')
                    print(f"  {i}. {ptype}" + (f" ({pname})" if pname else ""))
                    print(f"     置信度: {pconf}, 位置: {location[:100]}")
                else:
                    print(f"  {i}. {pattern}")
            print()
        
        # Trading Signals
        signals = analysis.get('trading_signals', [])
        if signals:
            print(f"【交易信号】({len(signals)}个)")
            for i, signal in enumerate(signals[:3], 1):
                if isinstance(signal, dict):
                    direction = signal.get('direction', 'N/A')
                    entry = signal.get('entry', signal.get('entry_price', 'N/A'))
                    stop_loss = signal.get('stop_loss', 'N/A')
                    take_profit = signal.get('take_profit', signal.get('take_profit_1', 'N/A'))
                    probability = signal.get('probability', signal.get('confidence', 'N/A'))
                    print(f"  {i}. {direction.upper()}")
                    print(f"     入场: {entry}, 止损: {stop_loss}, 止盈: {take_profit}")
                    print(f"     概率: {probability}")
                else:
                    print(f"  {i}. {signal}")
            print()
        
        # Key Features
        key_features = analysis.get('key_features', [])
        if key_features:
            print(f"【关键特征】({len(key_features)}个)")
            for i, feature in enumerate(key_features[:5], 1):
                print(f"  {i}. {feature}")
            print()
        
        # K-line Behaviors
        kline_behaviors = analysis.get('kline_behaviors', [])
        if kline_behaviors:
            print(f"【K线行为】({len(kline_behaviors)}个)")
            for i, behavior in enumerate(kline_behaviors[:5], 1):
                if isinstance(behavior, dict):
                    btype = behavior.get('type', 'N/A')
                    desc = behavior.get('description', '')
                    print(f"  {i}. {btype}: {desc[:150]}..." if len(desc) > 150 else f"  {i}. {btype}: {desc}")
                else:
                    print(f"  {i}. {behavior}")
            print()
        
        print()
    
    print("=" * 80)
    print(f"✅ 已展示 {len(records)} 条随机样本")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    main()

