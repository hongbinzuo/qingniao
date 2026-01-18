#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看 llava 识别的所有结果，包括文字信息
"""

import sys
import json
from pathlib import Path
from collections import Counter

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加 src 到路径
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def main():
    print(f"\n{'='*80}")
    print(f"llava 图片模式识别 - 全部结果查看")
    print(f"{'='*80}\n")
    
    try:
        db = TraderDBManager('abu')
        conn = db._get_connection()
        
        # 1. 获取所有已分类的记录（非 other）
        classified = conn.execute('''
            SELECT id, pattern_name, pattern_type, source_page,
                   timeframe_hint, direction, key_features, confidence,
                   context_text, gemini_annotation_json, chart_features_json,
                   image_path, created_at
            FROM pattern_library 
            WHERE pattern_type IS NOT NULL 
              AND pattern_type != 'other'
              AND pattern_type != ''
            ORDER BY pattern_type, id
        ''').fetchall()
        
        print(f"已分类记录总数: {len(classified)}\n")
        
        # 按类型分组显示
        by_type = {}
        for record in classified:
            ptype = record[2]  # pattern_type
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(record)
        
        # 2. 详细显示每个类型的所有记录
        for ptype in sorted(by_type.keys()):
            records = by_type[ptype]
            print(f"\n{'='*80}")
            print(f"【{ptype}】- {len(records)} 条记录")
            print(f"{'='*80}\n")
            
            for i, (pid, name, ptype, page, tf, direction, features, conf, 
                    context, gemini_json, chart_json, img_path, created) in enumerate(records, 1):
                conf_str = f"{conf:.2f}" if conf is not None else "0.00"
                print(f"{i}. ID={pid}, 页面={page}, 置信度={conf_str}")
                print(f"   图片: {Path(img_path).name if img_path else 'N/A'}")
                print(f"   名称: {name[:60] if name else 'N/A'}")
                
                # 时间周期
                if tf:
                    print(f"   时间周期: {tf}")
                
                # 方向
                if direction:
                    print(f"   方向: {direction}")
                
                # 关键特征
                if features:
                    try:
                        if isinstance(features, str):
                            feat_data = json.loads(features)
                        else:
                            feat_data = features
                        
                        if isinstance(feat_data, dict):
                            concepts = feat_data.get('concepts', [])
                            indicators = feat_data.get('indicators', [])
                            method = feat_data.get('method', '')
                            
                            if concepts:
                                print(f"   特征概念: {', '.join(concepts)}")
                            if indicators:
                                print(f"   指标: {', '.join(indicators)}")
                            if method:
                                print(f"   方法: {method}")
                        else:
                            print(f"   特征: {str(feat_data)[:200]}")
                    except Exception as e:
                        print(f"   特征(原始): {str(features)[:200]}")
                
                # 上下文文字
                if context:
                    context_clean = context.strip()
                    if context_clean and len(context_clean) > 20:
                        print(f"   上下文文字: {context_clean[:150]}...")
                    elif context_clean:
                        print(f"   上下文文字: {context_clean}")
                
                # Gemini 标注（如果有）
                if gemini_json:
                    try:
                        gemini = json.loads(gemini_json) if isinstance(gemini_json, str) else gemini_json
                        if isinstance(gemini, dict):
                            pattern = gemini.get('pattern', '')
                            direction_g = gemini.get('direction', '')
                            key_feat = gemini.get('key_features', [])
                            
                            if pattern:
                                print(f"   Gemini模式: {pattern}")
                            if direction_g:
                                print(f"   Gemini方向: {direction_g}")
                            if key_feat:
                                print(f"   Gemini特征: {', '.join(key_feat[:5])}")
                    except:
                        pass
                
                # Chart features（如果有）
                if chart_json:
                    try:
                        chart = json.loads(chart_json) if isinstance(chart_json, str) else chart_json
                        if isinstance(chart, dict):
                            ocr_text = chart.get('ocr_text', '')
                            if ocr_text:
                                print(f"   OCR文字: {ocr_text[:150]}...")
                    except:
                        pass
                
                print()  # 空行分隔
        
        # 3. 统计文字信息
        print(f"\n{'='*80}")
        print(f"文字信息统计")
        print(f"{'='*80}\n")
        
        has_context = conn.execute('''
            SELECT COUNT(*) FROM pattern_library 
            WHERE context_text IS NOT NULL AND context_text != ''
        ''').fetchone()[0]
        
        has_gemini = conn.execute('''
            SELECT COUNT(*) FROM pattern_library 
            WHERE gemini_annotation_json IS NOT NULL AND gemini_annotation_json != ''
        ''').fetchone()[0]
        
        has_chart_features = conn.execute('''
            SELECT COUNT(*) FROM pattern_library 
            WHERE chart_features_json IS NOT NULL AND chart_features_json != ''
        ''').fetchone()[0]
        
        has_ocr = 0
        ocr_samples = []
        for record in classified[:100]:  # 检查前100条
            chart_json = record[10]  # chart_features_json
            if chart_json:
                try:
                    chart = json.loads(chart_json) if isinstance(chart_json, str) else chart_json
                    if isinstance(chart, dict) and chart.get('ocr_text'):
                        has_ocr += 1
                        if len(ocr_samples) < 5:
                            ocr_samples.append(chart.get('ocr_text', '')[:100])
                except:
                    pass
        
        print(f"有上下文文字: {has_context}/{len(classified)} ({has_context/len(classified)*100:.1f}%)")
        print(f"有Gemini标注: {has_gemini}/{len(classified)} ({has_gemini/len(classified)*100:.1f}%)")
        print(f"有图表特征: {has_chart_features}/{len(classified)} ({has_chart_features/len(classified)*100:.1f}%)")
        print(f"有OCR文字: {has_ocr} (在前100条中检查)")
        
        if ocr_samples:
            print(f"\nOCR文字示例:")
            for i, ocr in enumerate(ocr_samples, 1):
                print(f"  {i}. {ocr}...")
        
        # 4. 导出到文件
        output_file = Path('outputs') / 'llava_all_results.txt'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"llava 图片模式识别 - 全部结果\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"总记录数: {len(classified)}\n\n")
            
            for ptype in sorted(by_type.keys()):
                records = by_type[ptype]
                f.write(f"\n{'='*80}\n")
                f.write(f"【{ptype}】- {len(records)} 条\n")
                f.write(f"{'='*80}\n\n")
                
                for pid, name, ptype, page, tf, direction, features, conf, \
                        context, gemini_json, chart_json, img_path, created in records:
                    conf_str = f"{conf:.2f}" if conf is not None else "0.00"
                    f.write(f"ID={pid}, 页面={page}, 置信度={conf_str}\n")
                    f.write(f"图片: {Path(img_path).name if img_path else 'N/A'}\n")
                    if tf:
                        f.write(f"时间周期: {tf}\n")
                    if direction:
                        f.write(f"方向: {direction}\n")
                    if context:
                        f.write(f"上下文: {context[:200]}\n")
                    if chart_json:
                        try:
                            chart = json.loads(chart_json) if isinstance(chart_json, str) else chart_json
                            if isinstance(chart, dict) and chart.get('ocr_text'):
                                f.write(f"OCR: {chart.get('ocr_text')}\n")
                        except:
                            pass
                    f.write("\n")
        
        print(f"\n{'='*80}")
        print(f"结果已导出到: {output_file}")
        print(f"{'='*80}\n")
        
        db.close()
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

