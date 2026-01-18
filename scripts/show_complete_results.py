#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""展示有完整交易参数的识别结果"""
import sys
import json
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
    
    # 查询有完整交易信号的记录
    all_records = conn.execute('''
        SELECT id, pattern_name, image_path, gemini_annotation_json, 
               pattern_type, direction, confidence
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL 
          AND gemini_annotation_json != ''
    ''').fetchall()
    
    # 筛选有完整交易参数的记录
    complete_records = []
    for record in all_records:
        id_val, pattern_name, image_path, gemini_json, pattern_type, direction, confidence = record
        try:
            analysis = json.loads(gemini_json)
            signals = analysis.get('trading_signals', [])
            for signal in signals:
                if isinstance(signal, dict):
                    entry = signal.get('entry') or signal.get('entry_price')
                    stop_loss = signal.get('stop_loss')
                    take_profit = signal.get('take_profit') or signal.get('take_profit_1')
                    if entry and stop_loss and take_profit:
                        complete_records.append((record, signal))
                        break
        except:
            continue
    
    if not complete_records:
        print("❌ 没有找到有完整交易参数的记录")
        print(f"   总记录数: {len(all_records)}")
        return
    
    print("=" * 80)
    print(f"有完整交易参数的识别结果（共 {len(complete_records)} 条）")
    print("=" * 80)
    print()
    
    # 展示前5条
    for idx, (record, signal) in enumerate(complete_records[:5], 1):
        id_val, pattern_name, image_path, gemini_json, pattern_type, direction, confidence = record
        
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
        
        # 交易信号详情
        print("【交易信号详情】")
        sig_direction = signal.get('direction', 'N/A')
        entry = signal.get('entry') or signal.get('entry_price', 'N/A')
        stop_loss = signal.get('stop_loss', 'N/A')
        take_profit = signal.get('take_profit') or signal.get('take_profit_1', 'N/A')
        take_profit_2 = signal.get('take_profit_2', 'N/A')
        probability = signal.get('probability') or signal.get('confidence', 'N/A')
        
        print(f"  方向: {sig_direction.upper()}")
        print(f"  入场价: {entry}")
        print(f"  止损价: {stop_loss}")
        print(f"  止盈价1: {take_profit}")
        if take_profit_2 and take_profit_2 != 'N/A':
            print(f"  止盈价2: {take_profit_2}")
        print(f"  概率/置信度: {probability}")
        
        # 计算风险回报比
        if isinstance(entry, (int, float)) and isinstance(stop_loss, (int, float)) and isinstance(take_profit, (int, float)):
            if sig_direction.upper() == 'LONG':
                risk = abs(entry - stop_loss)
                reward = abs(take_profit - entry)
            else:  # SHORT
                risk = abs(stop_loss - entry)
                reward = abs(entry - take_profit)
            
            if risk > 0:
                rr_ratio = reward / risk
                print(f"  风险回报比: 1:{rr_ratio:.2f}")
        print()
        
        # 解析完整分析
        try:
            analysis = json.loads(gemini_json)
            
            # Complete Narrative
            narrative = analysis.get('complete_narrative', '')
            if narrative:
                print("【完整叙述】")
                print(f"  {narrative[:300]}..." if len(narrative) > 300 else f"  {narrative}")
                print()
            
            # Patterns
            patterns = analysis.get('patterns', [])
            if patterns:
                print(f"【识别到的模式】({len(patterns)}个)")
                for i, pattern in enumerate(patterns[:3], 1):
                    if isinstance(pattern, dict):
                        ptype = pattern.get('type', 'N/A')
                        pname = pattern.get('name', '')
                        pconf = pattern.get('confidence', 0)
                        print(f"  {i}. {ptype}" + (f" ({pname})" if pname else "") + f" - 置信度: {pconf}")
                print()
        except:
            pass
        
        print()
    
    print("=" * 80)
    print(f"✅ 已展示 {min(5, len(complete_records))} 条有完整交易参数的样本")
    print(f"   总共有 {len(complete_records)} 条记录包含完整交易参数")
    print("=" * 80)
    
    conn.close()

if __name__ == '__main__':
    main()



