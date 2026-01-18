#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将电子书知识库与pattern_library关联
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def normalize_pattern_name(name: str) -> str:
    """标准化模式名称"""
    if not name:
        return ""
    
    name_lower = name.lower().strip()
    
    # 替换常见变体
    replacements = {
        'inside bar': 'insidebar',
        'head and shoulders': 'headandshoulders',
        'double top': 'doubletop',
        'double bottom': 'doublebottom',
        'trading range': 'tradingrange',
        'stop loss': 'stoploss',
        'take profit': 'takeprofit'
    }
    
    for old, new in replacements.items():
        name_lower = name_lower.replace(old, new)
    
    return name_lower

def extract_patterns_from_ebook_json(patterns_json: str) -> List[str]:
    """从JSON字符串提取模式列表"""
    if not patterns_json:
        return []
    
    try:
        patterns = json.loads(patterns_json)
        return [normalize_pattern_name(p) for p in patterns] if isinstance(patterns, list) else []
    except:
        return []

def find_pattern_matches(ebook_patterns: List[str], db_pattern_type: str) -> float:
    """计算模式匹配度"""
    if not db_pattern_type:
        return 0.0
    
    db_pattern = normalize_pattern_name(db_pattern_type)
    
    # 完全匹配
    if db_pattern in ebook_patterns:
        return 1.0
    
    # 部分匹配（包含关键词）
    for ebook_pattern in ebook_patterns:
        if ebook_pattern in db_pattern or db_pattern in ebook_pattern:
            return 0.7
    
    return 0.0

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    print("=" * 80)
    print("关联电子书知识库与模式库")
    print("=" * 80)
    print()
    
    # 获取所有电子书知识
    ebook_items = conn.execute('''
        SELECT id, book_title, chapter_number, chapter_title, section_title,
               content_type, content_text, extracted_patterns, trading_rules_json
        FROM ebook_knowledge_base
        WHERE extracted_patterns IS NOT NULL AND extracted_patterns != ''
    ''').fetchall()
    
    print(f"找到 {len(ebook_items)} 条有模式信息的电子书知识\n")
    
    # 获取所有模式库记录
    pattern_records = conn.execute('''
        SELECT id, pattern_name, pattern_type, image_path
        FROM pattern_library
    ''').fetchall()
    
    print(f"找到 {len(pattern_records)} 条模式库记录\n")
    
    # 建立关联
    linked_count = 0
    updated_count = 0
    
    for ebook_item in ebook_items:
        ebook_id, book_title, chapter_num, chapter_title, section_title, \
        content_type, content_text, patterns_json, rules_json = ebook_item
        
        ebook_patterns = extract_patterns_from_ebook_json(patterns_json)
        if not ebook_patterns:
            continue
        
        # 查找匹配的模式库记录
        matches = []
        for pattern_id, pattern_name, pattern_type, image_path in pattern_records:
            similarity = find_pattern_matches(ebook_patterns, pattern_type)
            if similarity > 0.5:  # 匹配度阈值
                matches.append({
                    'id': pattern_id,
                    'pattern_name': pattern_name,
                    'pattern_type': pattern_type,
                    'similarity': similarity
                })
        
        if matches:
            # 按相似度排序
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 更新模式库记录
            for match in matches[:3]:  # 最多关联3个
                pattern_id = match['id']
                
                # 获取现有的ebook_references
                existing_refs = conn.execute('''
                    SELECT ebook_references FROM pattern_library WHERE id = ?
                ''', (pattern_id,)).fetchone()
                
                existing_refs_json = existing_refs[0] if existing_refs and existing_refs[0] else '[]'
                try:
                    refs = json.loads(existing_refs_json)
                except:
                    refs = []
                
                # 添加新引用
                new_ref = {
                    'book': book_title,
                    'chapter': chapter_num,
                    'chapter_title': chapter_title,
                    'section': section_title,
                    'ebook_item_id': ebook_id,
                    'similarity': match['similarity']
                }
                
                # 检查是否已存在
                if not any(r.get('ebook_item_id') == ebook_id for r in refs):
                    refs.append(new_ref)
                    
                    # 更新text_description（使用第一个匹配的电子书内容）
                    existing_desc = conn.execute('''
                        SELECT text_description FROM pattern_library WHERE id = ?
                    ''', (pattern_id,)).fetchone()
                    
                    text_desc = existing_desc[0] if existing_desc and existing_desc[0] else None
                    if not text_desc and len(content_text) > 50:
                        text_desc = content_text[:1000]  # 限制长度
                    
                    # 更新记录
                    updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    conn.execute('''
                        UPDATE pattern_library 
                        SET ebook_references = ?, text_description = ?, updated_at = ?
                        WHERE id = ?
                    ''', (json.dumps(refs, ensure_ascii=False), text_desc, updated_at, pattern_id))
                    
                    updated_count += 1
                    linked_count += 1
    
    conn.commit()
    db.close()
    
    print("=" * 80)
    print(f"✅ 关联完成")
    print(f"   电子书知识条数: {len(ebook_items)}")
    print(f"   成功关联的模式: {updated_count} 个")
    print(f"   总关联数: {linked_count}")
    print("=" * 80)
    
    # 统计信息
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    stats = conn.execute('''
        SELECT COUNT(*) FROM pattern_library 
        WHERE ebook_references IS NOT NULL AND ebook_references != '' AND ebook_references != '[]'
    ''').fetchone()
    
    print(f"\n📊 有电子书关联的模式数: {stats[0]}")
    db.close()

if __name__ == '__main__':
    main()

