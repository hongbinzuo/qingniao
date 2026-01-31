#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Gemini分析结果更新pattern_library表（独立模块的一部分）

功能：
- 读取Gemini分析结果（已解析的JSONL文件）
- 匹配pattern_library记录（通过image_path）
- 更新gemini_annotation_json字段
- 提取并更新pattern_type, key_features等字段

输入：
- outputs/abu_gemini_parsed.jsonl（解析后的Gemini结果）

输出：
- 更新 pattern_library 表的 gemini_annotation_json 字段
- 生成更新报告

使用：
    python scripts/abu/abu_update_pattern_library_from_gemini.py \
        --input outputs/abu_gemini_parsed.jsonl \
        --dry-run  # 预览，不实际更新
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

ROOT = Path(__file__).resolve().parents[2]
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


def match_pattern_by_image_path(db_conn, image_path: str) -> Optional[int]:
    """通过图片路径匹配pattern_library记录"""
    # 方法1: 精确匹配
    pattern_name = Path(image_path).name
    result = db_conn.execute('''
        SELECT id FROM pattern_library
        WHERE image_path LIKE ?
        LIMIT 1
    ''', (f'%{pattern_name}%',)).fetchone()
    
    if result:
        return result[0]
    
    # 方法2: 通过页面号匹配
    import re
    page_match = re.search(r'page_(\d+)_', pattern_name)
    if page_match:
        page_num = int(page_match.group(1))
        result = db_conn.execute('''
            SELECT id FROM pattern_library
            WHERE source_page = ?
            LIMIT 1
        ''', (page_num,)).fetchone()
        if result:
            return result[0]
    
    return None


def extract_pattern_type_from_parsed(parsed: Dict) -> Optional[str]:
    """从解析结果提取pattern_type"""
    patterns = parsed.get('patterns', [])
    if patterns:
        # 使用第一个模式的名称
        return patterns[0].get('name')
    
    # 从pattern_combination提取
    combo = parsed.get('pattern_combination', '')
    if combo:
        # 取第一个模式
        first_pattern = combo.split('+')[0].strip() if '+' in combo else combo.strip()
        return first_pattern
    
    return None


def extract_direction_from_parsed(parsed: Dict) -> Optional[str]:
    """从解析结果提取交易方向"""
    signals = parsed.get('trading_signals', [])
    if signals:
        direction = signals[0].get('direction')
        if direction and direction != 'neutral':
            return direction
    
    # 从patterns推断
    patterns = parsed.get('patterns', [])
    for p in patterns:
        location = p.get('location', '').lower()
        if location == 'bottom':
            return 'long'
        elif location == 'top':
            return 'short'
    
    return None


def extract_key_features_from_parsed(parsed: Dict) -> Dict:
    """从解析结果提取关键特征"""
    behavior = parsed.get('price_action_behavior', {})
    return {
        'kline_features': behavior.get('kline_features', []),
        'trend': behavior.get('trend', 'neutral'),
        'structure': behavior.get('structure', 'unknown'),
        'volume_behavior': behavior.get('volume_behavior', 'unknown')
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='从Gemini分析结果更新pattern_library表')
    parser.add_argument('--input', type=str, required=True, help='输入JSONL文件（解析后的Gemini结果）')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不实际更新数据库')
    parser.add_argument('--skip-existing', action='store_true', default=True, help='跳过已有gemini_annotation_json的记录')
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}", file=sys.stderr)
        return 1
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    total = 0
    matched = 0
    updated = 0
    skipped = 0
    errors = 0
    
    print(f"开始更新pattern_library表")
    print(f"输入文件: {input_file}")
    print(f"预览模式: {args.dry_run}")
    print()
    
    with input_file.open('r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line)
                total += 1
                
                image_path = record.get('image')
                if not image_path:
                    continue
                
                # 匹配pattern_library记录
                pattern_id = match_pattern_by_image_path(conn, image_path)
                if not pattern_id:
                    print(f"  行 {line_num}: 未找到匹配的模式记录 - {Path(image_path).name}")
                    continue
                
                matched += 1
                
                # 检查是否已存在（如果启用skip-existing）
                if args.skip_existing:
                    existing = conn.execute('''
                        SELECT gemini_annotation_json FROM pattern_library
                        WHERE id = ? AND gemini_annotation_json IS NOT NULL 
                          AND gemini_annotation_json != ''
                    ''', (pattern_id,)).fetchone()
                    
                    if existing:
                        skipped += 1
                        if line_num % 100 == 0:
                            print(f"  进度: {line_num} (匹配: {matched}, 更新: {updated}, 跳过: {skipped})")
                        continue
                
                # 提取更新的字段
                parsed = record.get('parsed', {})
                
                pattern_type = extract_pattern_type_from_parsed(parsed)
                direction = extract_direction_from_parsed(parsed)
                key_features = extract_key_features_from_parsed(parsed)
                confidence = parsed.get('confidence', 0.0)
                
                # 准备更新数据
                gemini_annotation_json = json.dumps(parsed, ensure_ascii=False)
                key_features_json = json.dumps(key_features, ensure_ascii=False)
                updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                if args.dry_run:
                    print(f"  [预览] 将更新 pattern_id={pattern_id}:")
                    print(f"    pattern_type: {pattern_type}")
                    print(f"    direction: {direction}")
                    print(f"    confidence: {confidence:.2f}")
                    print(f"    key_features: {len(key_features.get('kline_features', []))} 个特征")
                    updated += 1
                else:
                    # 实际更新
                    conn.execute('''
                        UPDATE pattern_library
                        SET gemini_annotation_json = ?,
                            pattern_type = COALESCE(?, pattern_type),
                            direction = COALESCE(?, direction),
                            key_features = COALESCE(?, key_features),
                            confidence = COALESCE(?, confidence),
                            updated_at = ?
                        WHERE id = ?
                    ''', (
                        gemini_annotation_json,
                        pattern_type,
                        direction,
                        key_features_json,
                        confidence,
                        updated_at,
                        pattern_id
                    ))
                    updated += 1
                
                if line_num % 100 == 0:
                    print(f"  进度: {line_num} (匹配: {matched}, 更新: {updated}, 跳过: {skipped})")
            
            except Exception as e:
                print(f"  行 {line_num}: 处理失败 - {e}", file=sys.stderr)
                errors += 1
                continue
    
    if not args.dry_run:
        conn.commit()
    
    print()
    print("=" * 80)
    print("更新完成")
    print("=" * 80)
    print(f"  总记录数: {total}")
    print(f"  匹配记录: {matched}")
    print(f"  更新记录: {updated}")
    print(f"  跳过记录: {skipped}")
    print(f"  错误记录: {errors}")
    
    if args.dry_run:
        print()
        print("这是预览模式，未实际更新数据库。")
        print("要实际更新，请去掉 --dry-run 参数。")
    
    db.close()
    
    return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

