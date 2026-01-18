#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查模式库中的趋势分布
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

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def check_trend_distribution():
    """检查模式库中的趋势分布"""
    print("=" * 80)
    print("检查模式库中的趋势分布")
    print("=" * 80)
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 获取所有有Gemini标注的模式
    results = conn.execute('''
        SELECT id, gemini_annotation_json, pattern_type, pattern_name
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL 
          AND gemini_annotation_json != ''
    ''').fetchall()
    
    print(f"\n总共 {len(results)} 个模式\n")
    
    # 统计趋势分布
    trend_counter = Counter()
    direction_counter = Counter()
    pattern_type_counter = Counter()
    
    # 检查有趋势信息的模式数量
    has_trend_count = 0
    has_direction_count = 0
    
    for pattern_id, gemini_json, pattern_type, pattern_name in results:
        try:
            annotation = json.loads(gemini_json)
            
            # 统计模式类型
            pattern_type_counter[pattern_type] += 1
            
            # 检查price_action_behavior中的trend
            pab = annotation.get('price_action_behavior', {})
            if isinstance(pab, dict):
                trend = pab.get('trend', '')
                if trend:
                    trend_counter[trend.lower()] += 1
                    has_trend_count += 1
            
            # 检查direction字段（可能在根级别或trading_signals中）
            direction = annotation.get('direction', '')
            if not direction:
                # 检查trading_signals
                signals = annotation.get('trading_signals', [])
                if isinstance(signals, list) and len(signals) > 0:
                    first_signal = signals[0] if isinstance(signals[0], dict) else {}
                    direction = first_signal.get('direction', '')
            
            if direction:
                direction_counter[direction.lower()] += 1
                has_direction_count += 1
            
            # 从模式名称推断方向
            if not direction:
                name_lower = pattern_name.lower() if pattern_name else ''
                if any(kw in name_lower for kw in ['bull', 'long', 'buy', 'up', '上涨', '多头']):
                    direction_counter['long'] += 1
                elif any(kw in name_lower for kw in ['bear', 'short', 'sell', 'down', '下跌', '空头']):
                    direction_counter['short'] += 1
            
        except Exception as e:
            pass
    
    db.close()
    
    # 输出结果
    print("1. 趋势分布（price_action_behavior.trend）:")
    print(f"   有趋势信息的模式: {has_trend_count}/{len(results)} ({has_trend_count/len(results)*100:.1f}%)")
    for trend, count in trend_counter.most_common():
        print(f"   {trend:15s}: {count:4d} ({count/len(results)*100:5.1f}%)")
    
    print("\n2. 方向分布（direction / trading_signals.direction / 模式名称推断）:")
    print(f"   有方向信息的模式: {has_direction_count}/{len(results)} ({has_direction_count/len(results)*100:.1f}%)")
    for direction, count in direction_counter.most_common():
        print(f"   {direction:15s}: {count:4d} ({count/len(results)*100:5.1f}%)")
    
    print("\n3. 模式类型分布:")
    for ptype, count in pattern_type_counter.most_common():
        print(f"   {ptype:30s}: {count:4d} ({count/len(results)*100:5.1f}%)")
    
    # 计算多头vs空头比例
    long_count = direction_counter.get('long', 0) + direction_counter.get('buy', 0)
    short_count = direction_counter.get('short', 0) + direction_counter.get('sell', 0)
    total_directional = long_count + short_count
    
    if total_directional > 0:
        print(f"\n4. 方向比例:")
        print(f"   多头: {long_count} ({long_count/total_directional*100:.1f}%)")
        print(f"   空头: {short_count} ({short_count/total_directional*100:.1f}%)")
        print(f"   比例: {long_count/short_count:.2f}:1" if short_count > 0 else "比例: 全部为多头")
    
    print()


if __name__ == '__main__':
    check_trend_distribution()



