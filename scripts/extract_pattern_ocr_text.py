#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量OCR提取模式库图片中的文字说明
提取图片中的交易策略文字（如 "20-Gap bar buy in small PB bull trend so 75% chance of test of high of day"）
"""

import sys
import json
from pathlib import Path
from typing import Dict, Optional

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
from detailed_logger import get_detailed_logger

def convert_to_json_serializable(obj):
    """递归转换numpy类型为Python原生类型，支持JSON序列化"""
    import numpy as np
    
    if isinstance(obj, (np.integer, np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float_, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    else:
        return obj

def analyze_image_ocr(image_path: str) -> Optional[Dict]:
    """使用图表识别器进行OCR"""
    try:
        # 动态导入，避免依赖问题
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "abu_chart_recognizer", 
            ROOT / "scripts" / "abu" / "abu_chart_recognizer.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module.analyze(image_path)
    except Exception as e:
        print(f"⚠️ OCR分析失败: {e}", file=sys.stderr)
        return None
    return None

def main():
    import argparse
    
    ap = argparse.ArgumentParser(description='批量OCR提取模式库图片文字说明')
    ap.add_argument('--limit', type=int, help='限制处理的记录数（测试用）')
    ap.add_argument('--pattern-type', type=str, help='只处理特定模式类型')
    ap.add_argument('--dry-run', action='store_true', help='仅显示，不更新数据库')
    ap.add_argument('--force', action='store_true', help='强制重新提取已有OCR文字的记录')
    args = ap.parse_args()
    
    logger = get_detailed_logger('extract_pattern_ocr_text')
    logger.log_startup({'limit': args.limit, 'pattern_type': args.pattern_type, 'dry_run': args.dry_run})
    
    print("\n" + "="*80)
    print("批量OCR提取模式库图片文字说明")
    print("="*80 + "\n")
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 查询需要处理的记录
    query = '''
        SELECT id, pattern_name, pattern_type, image_path, chart_features_json
        FROM pattern_library 
        WHERE image_path IS NOT NULL AND image_path != ''
    '''
    params = []
    
    if args.pattern_type:
        query += ' AND pattern_type = ?'
        params.append(args.pattern_type)
    
    if not args.force:
        # 只处理还没有OCR文字的记录
        query += " AND (chart_features_json IS NULL OR chart_features_json = '' OR chart_features_json NOT LIKE '%ocr_text%')"
    
    if args.limit:
        query += ' LIMIT ?'
        params.append(args.limit)
    
    records = conn.execute(query, params).fetchall()
    
    total = len(records)
    print(f"找到 {total} 条需要处理的记录\n")
    
    if total == 0:
        print("没有需要处理的记录")
        db.close()
        return 0
    
    logger.info(f"开始处理 {total} 条记录")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    ocr_extracted_count = 0
    
    for i, (pid, name, ptype, img_path, existing_json) in enumerate(records, 1):
        logger.progress('ocr_extraction', i, total, f"处理 {i}/{total}: ID={pid}")
        
        # 检查图片文件是否存在
        # 处理路径格式（可能是相对路径或Windows路径）
        img_file = Path(img_path)
        if not img_file.is_absolute():
            # 尝试相对项目根目录
            img_file = ROOT / img_path
        # 标准化路径
        img_file = img_file.resolve()
        
        # 如果文件不存在，尝试查找匹配的文件（文件名可能不完全匹配）
        if not img_file.exists():
            # 提取页面号，尝试查找匹配的clip文件
            img_dir = img_file.parent
            img_name = img_file.name
            
            # 尝试从文件名提取页面号
            page_match = None
            if '_img_' in img_name:
                parts = img_name.split('_img_')
                if len(parts) >= 1:
                    page_part = parts[0]  # page_0851
                    if page_part.startswith('page_'):
                        page_num = page_part.replace('page_', '')
                        # 查找匹配的clip文件
                        possible_files = list(img_dir.glob(f'{page_part}_*_clip.png'))
                        if possible_files:
                            img_file = possible_files[0]
                            logger.info(f"找到匹配的图片文件: {img_path} -> {img_file}", {'id': pid, 'original': img_path, 'found': str(img_file)})
            
            # 如果还是找不到，跳过
            if not img_file.exists():
                logger.warning(f"图片文件不存在: {img_path}", {'id': pid, 'path': img_path})
                skipped_count += 1
                continue
        
        try:
            # 执行OCR
            result = analyze_image_ocr(str(img_file))
            
            if not result:
                logger.warning(f"OCR分析返回空结果", {'id': pid, 'image': img_path})
                failed_count += 1
                continue
            
            ocr_text = result.get('ocr_text', '').strip()
            
            # 检查是否有新的OCR文字
            existing_chart = None
            if existing_json:
                try:
                    existing_chart = json.loads(existing_json) if isinstance(existing_json, str) else existing_json
                    existing_ocr = existing_chart.get('ocr_text', '').strip()
                    if existing_ocr == ocr_text and not args.force:
                        # OCR文字相同，跳过
                        skipped_count += 1
                        continue
                except:
                    pass
            
            # 更新图表特征JSON
            if existing_chart and isinstance(existing_chart, dict):
                chart_features = existing_chart.copy()
            else:
                chart_features = {}
            
            # 更新OCR文字和其他特征
            chart_features['ocr_text'] = ocr_text
            chart_features['dominant_bar_width'] = result.get('dominant_bar_width', 0)
            chart_features['body_ratio'] = result.get('body_ratio', 0.0)
            chart_features['candlestick_like_score'] = result.get('candlestick_like_score', 0.0)
            chart_features['line_segments'] = result.get('line_segments', 0)
            chart_features['trendline_like'] = result.get('trendline_like', 0)
            chart_features['roi'] = result.get('roi', {})
            
            # 递归转换所有numpy类型为Python原生类型
            chart_features = convert_to_json_serializable(chart_features)
            
            # 如果有OCR文字，记录
            if ocr_text:
                ocr_extracted_count += 1
                logger.info(f"提取到OCR文字 (ID={pid}): {ocr_text[:100]}...", {
                    'id': pid,
                    'pattern_type': ptype,
                    'ocr_length': len(ocr_text)
                })
            
            # 更新数据库
            if not args.dry_run:
                chart_json = json.dumps(chart_features, ensure_ascii=False)
                conn.execute('''
                    UPDATE pattern_library 
                    SET chart_features_json = ?
                    WHERE id = ?
                ''', (chart_json, pid))
                conn.commit()
                success_count += 1
            else:
                print(f"  [DRY RUN] 将更新 ID={pid}:")
                if ocr_text:
                    print(f"    OCR文字: {ocr_text[:200]}...")
                success_count += 1
                
        except Exception as e:
            logger.error(f"处理失败 (ID={pid}): {e}", {'id': pid, 'error': str(e)})
            failed_count += 1
            continue
    
    # 统计结果
    print(f"\n{'='*80}")
    print("处理完成")
    print(f"{'='*80}\n")
    print(f"总计: {total} 条")
    print(f"成功: {success_count} 条")
    print(f"失败: {failed_count} 条")
    print(f"跳过: {skipped_count} 条")
    print(f"提取到OCR文字: {ocr_extracted_count} 条")
    
    if args.dry_run:
        print("\n[DRY RUN模式] 未实际更新数据库")
    else:
        print("\n✓ 数据库已更新")
    
    logger.info("OCR提取完成", {
        'total': total,
        'success': success_count,
        'failed': failed_count,
        'skipped': skipped_count,
        'ocr_extracted': ocr_extracted_count
    })
    
    db.close()
    logger.log_shutdown(exit_code=0)
    return 0

if __name__ == '__main__':
    sys.exit(main())
