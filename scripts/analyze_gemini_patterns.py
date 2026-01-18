#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Gemini标注的数据结构
"""
import sys
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def analyze_patterns():
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 获取所有有Gemini标注的记录
    results = conn.execute('''
        SELECT id, gemini_annotation_json, pattern_name, pattern_type
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL AND gemini_annotation_json != ''
        LIMIT 50
    ''').fetchall()
    
    print(f"分析 {len(results)} 个模式样本\n")
    print("=" * 80)
    
    # 统计信息
    kline_features_counter = Counter()
    pattern_types_counter = Counter()
    trend_counter = Counter()
    volatility_counter = Counter()
    signal_direction_counter = Counter()
    structure_counter = Counter()
    
    # 详细样本
    sample_patterns = []
    
    for pattern_id, gemini_json, pattern_name, pattern_type in results:
        try:
            ann = json.loads(gemini_json)
            parsed = ann.get('parsed', ann) if isinstance(ann, dict) else ann
            
            # 统计K线特征
            kline_features = parsed.get('price_action_behavior', {}).get('kline_features', [])
            if isinstance(kline_features, list):
                for feat in kline_features:
                    if isinstance(feat, dict):
                        feat_name = feat.get('feature', '') or str(feat)
                    else:
                        feat_name = str(feat)
                    if feat_name:
                        kline_features_counter[feat_name] += 1
            
            # 统计趋势
            trend = parsed.get('price_action_behavior', {}).get('trend', '')
            if trend:
                trend_counter[trend] += 1
            
            # 统计波动率
            volatility = parsed.get('market_conditions', {}).get('volatility', '')
            if volatility:
                volatility_counter[volatility] += 1
            
            # 统计结构
            structure = parsed.get('price_action_behavior', {}).get('structure', '')
            if structure:
                structure_counter[structure] += 1
            
            # 统计模式类型
            patterns = parsed.get('patterns', [])
            for p in patterns:
                if isinstance(p, dict):
                    ptype = p.get('type', '')
                    if ptype:
                        pattern_types_counter[ptype] += 1
            
            # 统计交易信号方向
            signals = parsed.get('trading_signals', [])
            for sig in signals:
                if isinstance(sig, dict):
                    direction = sig.get('direction', '')
                    if direction:
                        signal_direction_counter[direction] += 1
            
            # 保存样本
            if len(sample_patterns) < 5:
                sample_patterns.append({
                    'id': pattern_id,
                    'name': pattern_name,
                    'type': pattern_type,
                    'annotation': parsed
                })
        
        except Exception as e:
            print(f"⚠️  解析模式 {pattern_id} 失败: {e}", file=sys.stderr)
    
    db.close()
    
    # 打印统计结果
    print("\n📊 K线特征统计（Top 20）:")
    print("-" * 80)
    for feat, count in kline_features_counter.most_common(20):
        print(f"  {feat:40s} : {count:4d}")
    
    print("\n📊 模式类型统计:")
    print("-" * 80)
    for ptype, count in pattern_types_counter.most_common(10):
        print(f"  {ptype:40s} : {count:4d}")
    
    print("\n📊 趋势统计:")
    print("-" * 80)
    for trend, count in trend_counter.most_common(10):
        print(f"  {trend:40s} : {count:4d}")
    
    print("\n📊 波动率统计:")
    print("-" * 80)
    for vol, count in volatility_counter.most_common(10):
        print(f"  {vol:40s} : {count:4d}")
    
    print("\n📊 结构统计:")
    print("-" * 80)
    for struct, count in structure_counter.most_common(10):
        print(f"  {struct:40s} : {count:4d}")
    
    print("\n📊 交易信号方向统计:")
    print("-" * 80)
    for direction, count in signal_direction_counter.most_common(10):
        print(f"  {direction:40s} : {count:4d}")
    
    # 打印详细样本
    print("\n\n📋 详细样本（前5个）:")
    print("=" * 80)
    for i, sample in enumerate(sample_patterns, 1):
        print(f"\n样本 {i}: Pattern ID {sample['id']}")
        print(f"  名称: {sample['name']}")
        print(f"  类型: {sample['type']}")
        print(f"  标注结构:")
        print(json.dumps(sample['annotation'], indent=4, ensure_ascii=False)[:1000])
        print("  ...")

if __name__ == '__main__':
    analyze_patterns()



