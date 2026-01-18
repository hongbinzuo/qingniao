#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Page 269模式与SEI的匹配详情
"""
import sys
import json
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).parent.parent
SRC = ROOT / 'src'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

sys.stdout.reconfigure(encoding='utf-8')

from db_manager_trader import TraderDBManager
from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
from generate_comprehensive_trading_plans import get_kline_binance

def load_page269_pattern():
    """从数据库加载Page 269的模式数据"""
    db = TraderDBManager('abu')
    conn = db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, pattern_name, pattern_type, source_page, gemini_annotation_json
        FROM pattern_library
        WHERE source_page = 269
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    db.close()
    
    if not row:
        return None
    
    pattern_id, pattern_name, pattern_type, source_page, gemini_json = row
    
    data = {
        'pattern_id': pattern_id,
        'pattern_name': pattern_name,
        'pattern_type': pattern_type,
        'source_page': source_page,
        'gemini_annotation': {}
    }
    
    if gemini_json:
        try:
            data['gemini_annotation'] = json.loads(gemini_json)
        except Exception:
            pass
    
    return data

def get_sei_signals():
    """获取SEI的Page 269信号"""
    db = TraderDBManager('abu')
    conn = db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, symbol, signal_type, entry_price, stop_loss, take_profit_1, 
               take_profit_2, notes, score, created_at
        FROM trading_signals
        WHERE symbol = 'SEI' 
          AND (notes LIKE '%page 269%' OR notes LIKE '%269%' OR entry_model LIKE '%269%')
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    columns = [desc[0] for desc in cursor.description]
    signals = []
    for row in cursor.fetchall():
        signal = dict(zip(columns, row))
        signals.append(signal)
    
    db.close()
    return signals

def print_pattern_info(pattern_data):
    """打印模式信息"""
    print("=" * 80)
    print("Page 269 模式信息")
    print("=" * 80)
    print(f"模式ID: {pattern_data.get('pattern_id', 'N/A')}")
    print(f"模式名称: {pattern_data.get('pattern_name', 'N/A')}")
    print(f"来源页面: {pattern_data.get('source_page', 'N/A')}")
    print(f"模式类型: {pattern_data.get('pattern_type', 'N/A')}")
    print()
    
    # 打印Gemini annotation
    gemini_annotation = pattern_data.get('gemini_annotation', {})
    parsed = gemini_annotation.get('parsed', gemini_annotation)
    
    print("模式特征:")
    price_action = parsed.get('price_action_behavior', {})
    if price_action:
        kline_features = price_action.get('kline_features', [])
        if kline_features:
            print(f"  K线特征 ({len(kline_features)}个):")
            for feat in kline_features[:15]:
                if isinstance(feat, dict):
                    print(f"    - {feat.get('feature', feat)}")
                else:
                    print(f"    - {feat}")
        
        patterns = price_action.get('patterns', [])
        if patterns:
            print(f"\n  价格行为模式 ({len(patterns)}个):")
            for pat in patterns[:10]:
                if isinstance(pat, dict):
                    print(f"    - {pat.get('type', pat)}")
                else:
                    print(f"    - {pat}")
        
        trend = price_action.get('trend', '')
        if trend:
            print(f"\n  趋势: {trend}")
        
        structure = price_action.get('structure', '')
        if structure:
            print(f"\n  结构: {structure}")
    
    trading_signals = parsed.get('trading_signals', [])
    if trading_signals:
        print(f"\n交易信号 ({len(trading_signals)}个):")
        for i, sig in enumerate(trading_signals[:3], 1):
            direction = sig.get('direction', 'N/A')
            entry = sig.get('entry_price', 'N/A')
            sl = sig.get('stop_loss', 'N/A')
            tp = sig.get('take_profit_1', 'N/A')
            print(f"  信号{i}: {direction} | Entry: {entry} | SL: {sl} | TP: {tp}")
    
    print()

def analyze_match(matcher, sei_klines, timeframe='15m'):
    """分析匹配详情"""
    klines_dict = {timeframe: sei_klines}
    
    matches = matcher.match_patterns(
        klines_dict,
        min_similarity=0.4,
        max_matches=20
    )
    
    # 查找page 269的匹配
    page269_match = None
    for match in matches:
        pattern_name = match.get('pattern_name', '')
        pattern_id = match.get('pattern_id', '')
        if '269' in pattern_name or pattern_id == 269:
            page269_match = match
            break
    
    return {
        'match': page269_match,
        'all_matches': matches[:5],
        'total_matches': len(matches)
    }

def print_match_details(match, sei_price):
    """打印匹配详情"""
    if not match:
        print("未找到Page 269的匹配")
        return
    
    print("=" * 80)
    print("SEI与Page 269的匹配详情")
    print("=" * 80)
    print(f"相似度: {match.get('similarity', 0):.2%}")
    print(f"模式名称: {match.get('pattern_name', 'N/A')}")
    print(f"模式类型: {match.get('pattern_type', 'N/A')}")
    print(f"SEI当前价格: {sei_price:.4f}")
    print()

def main():
    print("正在加载Page 269模式...")
    pattern_data = load_page269_pattern()
    if not pattern_data:
        print("未找到Page 269的模式数据")
        return
    
    print_pattern_info(pattern_data)
    
    print("正在获取SEI的信号...")
    sei_signals = get_sei_signals()
    if not sei_signals:
        print("未找到SEI的Page 269信号")
        return
    
    print(f"找到{len(sei_signals)}个SEI的Page 269信号")
    latest_signal = sei_signals[0]
    print(f"最新信号:")
    print(f"  方向: {latest_signal['signal_type']}")
    print(f"  入场: {latest_signal['entry_price']:.4f}")
    print(f"  止损: {latest_signal['stop_loss']:.4f}")
    print(f"  止盈1: {latest_signal['take_profit_1']:.4f}")
    print(f"  评分: {latest_signal['score']:.2f}")
    print(f"  时间: {latest_signal['created_at']}")
    print(f"  说明: {latest_signal['notes']}")
    print()
    
    print("正在获取SEI的K线数据...")
    sei_klines = get_kline_binance('SEI', '15m', 200)
    if not sei_klines:
        print("无法获取SEI的K线数据")
        return
    
    current_price = sei_klines[-1]['close']
    print(f"SEI当前价格: {current_price:.4f}")
    print(f"K线数量: {len(sei_klines)}")
    print()
    
    print("正在初始化匹配器...")
    matcher = EnhancedGeminiPatternMatcher(use_dl=False)
    
    print("正在分析匹配...")
    analysis = analyze_match(matcher, sei_klines, '15m')
    
    if analysis['match']:
        print_match_details(analysis['match'], current_price)
    else:
        print("未找到Page 269的匹配（可能需要降低相似度阈值）")
    
    print(f"\n总共找到{analysis['total_matches']}个匹配（相似度>=0.4）")
    if analysis['all_matches']:
        print("\n前5个匹配:")
        for i, match in enumerate(analysis['all_matches'], 1):
            pattern_name = match.get('pattern_name', 'N/A')
            similarity = match.get('similarity', 0)
            pattern_id = match.get('pattern_id', 'N/A')
            print(f"  {i}. Page {match.get('source_page', '?')} | ID: {pattern_id} | 相似度: {similarity:.2%} | {pattern_name[:60]}")

if __name__ == '__main__':
    main()

