#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看第273页模式的详细信息
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from db_manager_trader import TraderDBManager

def main():
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    print("=" * 80)
    print("第273页模式详细信息")
    print("=" * 80)
    print()
    
    # 查询第273页的模式
    rows = conn.execute("""
        SELECT id, pattern_name, pattern_type, source_page, 
               context_text, key_features, image_path,
               gemini_annotation_json
        FROM pattern_library 
        WHERE source_page = 273
        LIMIT 1
    """).fetchall()
    
    if not rows:
        print("❌ 未找到第273页的模式")
        db.close()
        return
    
    r = rows[0]
    pattern_id = r[0]
    pattern_name = r[1]
    pattern_type = r[2]
    source_page = r[3]
    context_text = r[4]
    key_features = r[5]
    image_path = r[6]
    gemini_json = r[7]
    
    print(f"模式ID: {pattern_id}")
    print(f"模式名称: {pattern_name}")
    print(f"模式类型: {pattern_type}")
    print(f"来源页面: {source_page}")
    print(f"图片路径: {image_path}")
    print(f"上下文文字: {context_text}")
    print()
    
    # 解析Gemini标注
    if gemini_json:
        try:
            annotation = json.loads(gemini_json)
            parsed = annotation.get('parsed', annotation) if isinstance(annotation, dict) else {}
            
            print("=" * 80)
            print("Gemini标注信息")
            print("=" * 80)
            print()
            
            # 模式信息
            patterns = parsed.get('patterns', [])
            if patterns:
                print("识别到的模式:")
                for i, p in enumerate(patterns, 1):
                    if isinstance(p, dict):
                        print(f"  {i}. 类型: {p.get('type', 'N/A')}")
                        print(f"     名称: {p.get('name', 'N/A')}")
                        print(f"     方向: {p.get('direction', 'N/A')}")
                        print()
            
            # 价格行为
            price_action = parsed.get('price_action_behavior', {})
            if price_action:
                print("价格行为特征:")
                kline_features = price_action.get('kline_features', [])
                if kline_features:
                    print(f"  K线特征: {kline_features}")
                print(f"  趋势: {price_action.get('trend', 'N/A')}")
                print(f"  结构: {price_action.get('structure', 'N/A')}")
                print()
            
            # 交易信号
            trading_signals = parsed.get('trading_signals', [])
            if trading_signals:
                print("交易信号:")
                for i, sig in enumerate(trading_signals, 1):
                    if isinstance(sig, dict):
                        print(f"  信号 {i}:")
                        print(f"    方向: {sig.get('direction', 'N/A')}")
                        print(f"    入场: {sig.get('entry_price', 'N/A')}")
                        print(f"    止损: {sig.get('stop_loss_price', 'N/A')}")
                        print(f"    止盈1: {sig.get('take_profit_1_price', 'N/A')}")
                        print(f"    止盈2: {sig.get('take_profit_2_price', 'N/A')}")
                        print(f"    概率: {sig.get('probability', 'N/A')}")
                        print(f"    风险回报比: {sig.get('risk_reward_ratio', 'N/A')}")
                        print()
            
            # 市场条件
            market_conditions = parsed.get('market_conditions', {})
            if market_conditions:
                print("市场条件:")
                print(f"  趋势强度: {market_conditions.get('trend_strength', 'N/A')}")
                print(f"  波动率: {market_conditions.get('volatility', 'N/A')}")
                print()
            
            # 文本注释
            text_notes = parsed.get('text_notes', [])
            if text_notes:
                print("文本注释:")
                for note in text_notes:
                    print(f"  - {note}")
                print()
            
            # 原始JSON（部分）
            print("=" * 80)
            print("原始Gemini标注（JSON格式，前500字符）:")
            print("=" * 80)
            json_str = json.dumps(annotation, ensure_ascii=False, indent=2)
            print(json_str[:500])
            if len(json_str) > 500:
                print(f"\n... (共 {len(json_str)} 字符，已截断)")
            print()
        
        except Exception as e:
            print(f"⚠️  解析Gemini标注失败: {e}")
            print(f"原始JSON长度: {len(gemini_json)} 字符")
            print()
    
    # 查询使用此模式的信号
    print("=" * 80)
    print("使用此模式的最近信号")
    print("=" * 80)
    print()
    
    signal_rows = conn.execute("""
        SELECT id, signal_time, symbol, signal_type, 
               entry_price, stop_loss, take_profit_1, take_profit_2, score
        FROM trading_signals
        WHERE entry_model LIKE ? OR notes LIKE ?
        ORDER BY signal_time DESC
        LIMIT 5
    """, [f'%{pattern_name}%', f'%page {source_page}%']).fetchall()
    
    if signal_rows:
        print(f"找到 {len(signal_rows)} 个相关信号:")
        print()
        for sig in signal_rows:
            print(f"  信号ID {sig[0]}: {sig[2]} {sig[3]} | Entry: {sig[4]:.4f} | SL: {sig[5]:.4f} | TP1: {sig[6]:.4f} | TP2: {sig[7]:.4f} | 评分: {sig[8]:.2f} | 时间: {sig[1]}")
    else:
        print("未找到使用此模式的信号")
    
    print()
    print("=" * 80)
    print("图片位置提示")
    print("=" * 80)
    print(f"第273页的图片文件: {image_path}")
    if Path(image_path).exists():
        print("✓ 图片文件存在，可以使用图片查看器打开")
    else:
        print("⚠️  图片文件不存在或路径不正确")
    
    db.close()

if __name__ == '__main__':
    main()



