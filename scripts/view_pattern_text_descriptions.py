#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看模式库中的文字说明和交易信号
包括OCR文字、上下文文字、Gemini标注等
"""

import sys
import json
from pathlib import Path
from typing import Dict, List

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加 src 到路径
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def main():
    import argparse
    
    ap = argparse.ArgumentParser(description='查看模式库中的文字说明和交易信号')
    ap.add_argument('--pattern-type', type=str, help='特定模式类型')
    ap.add_argument('--search', type=str, help='搜索关键词（如 Gap bar, buy, PB, trend）')
    ap.add_argument('--limit', type=int, default=50, help='显示数量限制')
    args = ap.parse_args()
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    print("\n" + "="*80)
    print("模式库文字说明和交易信号查看")
    print("="*80 + "\n")
    
    # 构建查询
    query = '''
        SELECT id, pattern_name, pattern_type, 
               context_text, chart_features_json, gemini_annotation_json,
               timeframe_hint, direction, key_features, image_path
        FROM pattern_library 
        WHERE 1=1
    '''
    params = []
    
    if args.pattern_type:
        query += ' AND pattern_type = ?'
        params.append(args.pattern_type)
    
    if args.search:
        query += ' AND (context_text LIKE ? OR chart_features_json LIKE ?)'
        search_term = f'%{args.search}%'
        params.extend([search_term, search_term])
    
    query += ' ORDER BY id LIMIT ?'
    params.append(args.limit)
    
    records = conn.execute(query, params).fetchall()
    
    print(f"找到 {len(records)} 条记录\n")
    
    for i, (pid, name, ptype, context, chart_json, gemini_json, 
            tf, direction, key_features, img_path) in enumerate(records, 1):
        print(f"\n{'='*80}")
        print(f"【记录 {i}】ID={pid}, 类型={ptype or 'N/A'}")
        print(f"{'='*80}")
        print(f"图片: {Path(img_path).name if img_path else 'N/A'}")
        print(f"名称: {name or 'N/A'}")
        
        # 时间周期和方向
        if tf:
            print(f"时间周期: {tf}")
        if direction:
            print(f"方向: {direction}")
        
        # 上下文文字（最重要！）
        if context:
            context_clean = context.strip()
            # 过滤掉页脚文字
            if '阿布价格行为全套课程' not in context_clean:
                print(f"\n📝 文字说明:")
                print(f"   {context_clean}")
            else:
                # 如果只有页脚，尝试提取其他部分
                lines = context_clean.split('\n')
                useful_lines = [l.strip() for l in lines if l.strip() and '阿布价格行为' not in l and len(l.strip()) > 10]
                if useful_lines:
                    print(f"\n📝 文字说明:")
                    for line in useful_lines[:5]:
                        print(f"   {line}")
        
        # 图表特征（OCR文字）
        if chart_json:
            try:
                chart = json.loads(chart_json) if isinstance(chart_json, str) else chart_json
                if isinstance(chart, dict):
                    ocr_text = chart.get('ocr_text', '')
                    if ocr_text and len(ocr_text.strip()) > 5:
                        print(f"\n🔍 OCR识别文字:")
                        print(f"   {ocr_text}")
            except:
                pass
        
        # Gemini标注
        if gemini_json:
            try:
                gemini = json.loads(gemini_json) if isinstance(gemini_json, str) else gemini_json
                if isinstance(gemini, dict):
                    pattern = gemini.get('pattern', '')
                    key_feat = gemini.get('key_features', [])
                    annotations = gemini.get('annotations', [])
                    
                    if pattern:
                        print(f"\n🤖 Gemini标注:")
                        print(f"   模式: {pattern}")
                    if key_feat:
                        print(f"   特征: {', '.join(key_feat[:5])}")
                    if annotations:
                        print(f"   标注: {json.dumps(annotations, ensure_ascii=False)[:200]}")
            except:
                pass
        
        # 关键特征
        if key_features:
            try:
                if isinstance(key_features, str):
                    kf = json.loads(key_features)
                else:
                    kf = key_features
                
                if isinstance(kf, dict):
                    concepts = kf.get('concepts', [])
                    indicators = kf.get('indicators', [])
                    if concepts or indicators:
                        print(f"\n🎯 关键特征:")
                        if concepts:
                            print(f"   概念: {', '.join(concepts[:5])}")
                        if indicators:
                            print(f"   指标: {', '.join(indicators[:5])}")
            except:
                pass
        
        print()
    
    db.close()
    
    # 统计信息
    print(f"\n{'='*80}")
    print("统计信息")
    print(f"{'='*80}\n")
    
    # 有上下文文字的记录数
    conn = db._get_connection()
    has_context = conn.execute('''
        SELECT COUNT(*) FROM pattern_library 
        WHERE context_text IS NOT NULL 
          AND context_text != ''
          AND context_text NOT LIKE '%阿布价格行为全套课程%'
          AND LENGTH(context_text) > 20
    ''').fetchone()[0]
    
    # 有OCR文字的记录数
    has_ocr = 0
    ocr_samples = []
    all_records = conn.execute('''
        SELECT id, chart_features_json FROM pattern_library 
        WHERE chart_features_json IS NOT NULL AND chart_features_json != ''
        LIMIT 200
    ''').fetchall()
    
    for pid, chart_json in all_records:
        try:
            chart = json.loads(chart_json) if isinstance(chart_json, str) else chart_json
            if isinstance(chart, dict):
                ocr_text = chart.get('ocr_text', '')
                if ocr_text and len(ocr_text.strip()) > 5:
                    has_ocr += 1
                    if len(ocr_samples) < 5:
                        ocr_samples.append(ocr_text[:150])
        except:
            pass
    
    print(f"有有效文字说明的记录: {has_context} 条")
    print(f"有OCR识别文字的记录: {has_ocr} 条（在检查的{len(all_records)}条中）")
    
    if ocr_samples:
        print(f"\nOCR文字示例:")
        for i, ocr in enumerate(ocr_samples, 1):
            print(f"  {i}. {ocr}...")
    
    db.close()
    return 0

if __name__ == '__main__':
    sys.exit(main())



