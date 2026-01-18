#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试脚本：检查模式库数据格式和匹配逻辑
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
from generate_comprehensive_trading_plans import get_kline_binance

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def check_pattern_library_format():
    """检查模式库数据格式"""
    print("=" * 80)
    print("1. 检查模式库数据格式")
    print("=" * 80)
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 获取3个样本
    results = conn.execute('''
        SELECT id, gemini_annotation_json, pattern_name, pattern_type
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL 
          AND gemini_annotation_json != ''
        LIMIT 3
    ''').fetchall()
    
    print(f"\n找到 {len(results)} 个样本\n")
    
    for i, (pattern_id, gemini_json, pattern_name, pattern_type) in enumerate(results, 1):
        print(f"样本 {i}:")
        print(f"  ID: {pattern_id}")
        print(f"  名称: {pattern_name}")
        print(f"  类型: {pattern_type}")
        
        try:
            annotation = json.loads(gemini_json)
            print(f"  标注结构: {list(annotation.keys())}")
            
            # 检查是否有parsed字段
            if 'parsed' in annotation:
                parsed = annotation['parsed']
                print(f"  有parsed字段: {list(parsed.keys())}")
                
                # 检查price_action_behavior
                if 'price_action_behavior' in parsed:
                    pab = parsed['price_action_behavior']
                    print(f"    price_action_behavior: {list(pab.keys())}")
                    if 'kline_features' in pab:
                        kf = pab['kline_features']
                        print(f"      kline_features类型: {type(kf)}")
                        print(f"      kline_features数量: {len(kf) if isinstance(kf, list) else 'N/A'}")
                        if isinstance(kf, list) and len(kf) > 0:
                            print(f"      第一个元素: {kf[0]} (类型: {type(kf[0])})")
            else:
                # 没有parsed，检查直接结构
                if 'price_action_behavior' in annotation:
                    pab = annotation['price_action_behavior']
                    print(f"    price_action_behavior (直接): {list(pab.keys())}")
                    if 'kline_features' in pab:
                        kf = pab['kline_features']
                        print(f"      kline_features类型: {type(kf)}")
                        print(f"      kline_features数量: {len(kf) if isinstance(kf, list) else 'N/A'}")
            
        except Exception as e:
            print(f"  解析错误: {e}")
        
        print()
    
    db.close()


def check_feature_extraction():
    """检查特征提取"""
    print("=" * 80)
    print("2. 检查特征提取")
    print("=" * 80)
    
    # 获取BTC的K线数据
    print("\n获取BTC 15m K线数据...")
    klines_15m = get_kline_binance('BTC', '15m', 200)
    klines_1h = get_kline_binance('BTC', '1h', 100)
    klines_5m = get_kline_binance('BTC', '5m', 200)
    klines_4h = get_kline_binance('BTC', '4h', 100)
    
    if not klines_15m:
        print("  无法获取K线数据")
        return
    
    print(f"  15m: {len(klines_15m)} 根")
    print(f"  1h: {len(klines_1h)} 根")
    print(f"  5m: {len(klines_5m)} 根")
    print(f"  4h: {len(klines_4h)} 根")
    
    # 提取特征
    print("\n提取特征...")
    matcher = EnhancedGeminiPatternMatcher(use_dl=False)
    
    klines_dict = {
        '5m': klines_5m,
        '15m': klines_15m,
        '1h': klines_1h,
        '4h': klines_4h
    }
    
    features = matcher.extract_realtime_features(klines_dict)
    
    if not features:
        print("  特征提取失败（返回空字典）")
        return
    
    print(f"  特征结构: {list(features.keys())}")
    
    if 'price_action_behavior' in features:
        pab = features['price_action_behavior']
        print(f"    price_action_behavior: {list(pab.keys())}")
        if 'kline_features' in pab:
            kf = pab['kline_features']
            print(f"      kline_features: {kf}")
            print(f"      kline_features数量: {len(kf)}")
    
    return features


def check_matching_logic(features):
    """检查匹配逻辑"""
    print("\n" + "=" * 80)
    print("3. 检查匹配逻辑")
    print("=" * 80)
    
    if not features:
        print("  没有特征数据，跳过匹配检查")
        return
    
    matcher = EnhancedGeminiPatternMatcher(use_dl=False)
    
    print(f"\n模式库数量: {len(matcher.pattern_library)}")
    
    if len(matcher.pattern_library) == 0:
        print("  模式库为空")
        return
    
    # 测试前3个模式的匹配
    print("\n测试前3个模式的匹配:")
    
    realtime_kline_features = set(features.get('price_action_behavior', {}).get('kline_features', []))
    print(f"实时K线特征: {realtime_kline_features}")
    
    for i, pattern in enumerate(matcher.pattern_library[:3], 1):
        print(f"\n模式 {i}: {pattern['pattern_name']}")
        
        annotation = pattern['gemini_annotation']
        pattern_parsed = annotation.get('parsed', annotation) if isinstance(annotation, dict) else {}
        
        pattern_kline_features = set()
        pattern_kline_raw = pattern_parsed.get('price_action_behavior', {}).get('kline_features', [])
        
        print(f"  原始kline_features类型: {type(pattern_kline_raw)}")
        print(f"  原始kline_features值: {pattern_kline_raw}")
        
        for feat in pattern_kline_raw:
            if isinstance(feat, dict):
                pattern_kline_features.add(feat.get('feature', ''))
            elif isinstance(feat, str):
                pattern_kline_features.add(feat)
        
        print(f"  提取的K线特征: {pattern_kline_features}")
        
        if pattern_kline_features:
            intersection = realtime_kline_features & pattern_kline_features
            union = pattern_kline_features | realtime_kline_features
            kline_match = len(intersection) / len(union) if union else 0.0
            print(f"  交集: {intersection}")
            print(f"  并集: {union}")
            print(f"  匹配度: {kline_match:.4f}")
        else:
            print(f"  模式库中没有K线特征")
        
        # 计算完整相似度
        similarity = matcher.calculate_similarity(features, annotation)
        print(f"  总相似度: {similarity:.4f}")


def main():
    check_pattern_library_format()
    features = check_feature_extraction()
    check_matching_logic(features)


if __name__ == '__main__':
    main()



