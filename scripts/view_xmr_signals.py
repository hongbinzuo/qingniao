#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看XMR信号的详细信息
"""
import sys
import json
from pathlib import Path

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

def view_signals():
    """查看XMR信号的详细信息"""
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 查找模式269和181
    results = conn.execute('''
        SELECT id, pattern_name, pattern_type, gemini_annotation_json
        FROM pattern_library
        WHERE id IN (269, 181)
        ORDER BY id
    ''').fetchall()
    
    print("=" * 80)
    print("XMR信号的详细信息")
    print("=" * 80)
    
    for pattern_id, pattern_name, pattern_type, gemini_json in results:
        print(f"\n模式ID: {pattern_id}")
        print(f"模式名称: {pattern_name}")
        print(f"模式类型: {pattern_type}")
        
        try:
            annotation = json.loads(gemini_json)
            
            # 趋势信息
            pab = annotation.get('price_action_behavior', {})
            if isinstance(pab, dict):
                trend = pab.get('trend', 'N/A')
                structure = pab.get('structure', 'N/A')
                print(f"趋势: {trend}")
                print(f"结构: {structure}")
            
            # K线特征
            kline_features = pab.get('kline_features', [])
            if kline_features:
                print(f"K线特征数量: {len(kline_features)}")
                if isinstance(kline_features, list) and len(kline_features) > 0:
                    print(f"前3个特征:")
                    for i, feat in enumerate(kline_features[:3], 1):
                        if isinstance(feat, dict):
                            print(f"  {i}. {feat.get('feature', '')}")
                        else:
                            print(f"  {i}. {feat}")
            
            # 交易信号
            signals = annotation.get('trading_signals', [])
            if signals and isinstance(signals, list) and len(signals) > 0:
                first_signal = signals[0] if isinstance(signals[0], dict) else {}
                direction = first_signal.get('direction', 'N/A')
                probability = first_signal.get('probability', 'N/A')
                print(f"方向: {direction}")
                print(f"概率: {probability}")
            
            # 市场条件
            market_conditions = annotation.get('market_conditions', {})
            if market_conditions:
                volatility = market_conditions.get('volatility', 'N/A')
                print(f"波动率: {volatility}")
            
        except Exception as e:
            print(f"解析错误: {e}")
        
        print()
    
    db.close()
    
    # 显示信号摘要
    print("\n" + "=" * 80)
    print("信号摘要")
    print("=" * 80)
    print("""
信号1: XMR LONG
  入场: $118.70
  止损: $110.40 (7.0%)
  止盈1: $131.15 (10.5%)
  止盈2: $143.60 (21.0%)
  相似度: 61.84%
  评分: 2143.29
  模式: Pattern from page 269
  
信号2: XMR SHORT  
  入场: $118.70
  止损: $119.60 (0.8%)
  止盈1: $117.35 (1.1%)
  止盈2: $116.00 (2.3%)
  相似度: 61.84%
  评分: 61.84
  模式: Pattern from page 181
    """)


if __name__ == '__main__':
    view_signals()



