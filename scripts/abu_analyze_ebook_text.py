#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析Al Brooks电子书文本，提取模式、交易规则、关键概念
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

EXTRACTED_DIR = ROOT / 'data' / 'abu' / 'ebooks' / 'extracted'

# 预定义的模式名称列表（从现有pattern_library提取）
KNOWN_PATTERNS = {
    'wedge', 'triangle', 'head and shoulders', 'double top', 'double bottom',
    'inside bar', 'engulfing', 'pin bar', 'flag', 'pennant', 'channel',
    'trading range', 'breakout', 'pullback', 'trend', 'reversal',
    'measured move', 'climax', 'exhaustion', 'bear trap', 'bull trap'
}

# 交易规则关键词
ENTRY_KEYWORDS = ['enter', 'buy', 'sell', 'go long', 'go short', 'take', 'trade']
STOP_LOSS_KEYWORDS = ['stop loss', 'stop', 'risk', 'protect', 'below', 'above']
TAKE_PROFIT_KEYWORDS = ['take profit', 'target', 'exit', 'profit', 'reward']

def extract_patterns_from_text(text: str) -> List[str]:
    """从文本中提取模式名称"""
    patterns_found = []
    text_lower = text.lower()
    
    for pattern in KNOWN_PATTERNS:
        # 查找模式名称（单词边界）
        pattern_regex = r'\b' + re.escape(pattern) + r'\b'
        if re.search(pattern_regex, text_lower, re.IGNORECASE):
            patterns_found.append(pattern.title())
    
    return list(set(patterns_found))  # 去重

def extract_trading_rules(text: str) -> Dict:
    """从文本中提取交易规则"""
    rules = {
        'entry': [],
        'stop_loss': [],
        'take_profit': []
    }
    
    # 提取入场规则
    entry_pattern = r'(?:enter|buy|sell|go long|go short|take)[^\n\.]{5,100}'
    entry_matches = re.findall(entry_pattern, text, re.IGNORECASE)
    for match in entry_matches[:3]:  # 最多取3条
        if len(match.strip()) > 10:
            rules['entry'].append(match.strip())
    
    # 提取止损规则
    stop_pattern = r'(?:stop loss|stop|risk|protect)[^\n\.]{5,100}'
    stop_matches = re.findall(stop_pattern, text, re.IGNORECASE)
    for match in stop_matches[:3]:
        if len(match.strip()) > 10:
            rules['stop_loss'].append(match.strip())
    
    # 提取止盈规则
    profit_pattern = r'(?:take profit|target|exit|profit)[^\n\.]{5,100}'
    profit_matches = re.findall(profit_pattern, text, re.IGNORECASE)
    for match in profit_matches[:3]:
        if len(match.strip()) > 10:
            rules['take_profit'].append(match.strip())
    
    return rules

def extract_key_concepts(text: str) -> List[str]:
    """提取关键概念"""
    concepts = []
    
    # 常见的价格行为概念
    concept_keywords = [
        'support', 'resistance', 'trend line', 'breakout', 'pullback',
        'swing', 'high', 'low', 'bar', 'candle', 'momentum', 'volatility',
        'strength', 'weakness', 'climax', 'exhaustion', 'continuation'
    ]
    
    text_lower = text.lower()
    for keyword in concept_keywords:
        if keyword in text_lower:
            concepts.append(keyword.title())
    
    return list(set(concepts))[:10]  # 去重，最多10个

def determine_content_type(text: str, patterns: List[str]) -> str:
    """判断内容类型"""
    text_lower = text.lower()
    
    if patterns:
        return 'pattern_description'
    
    if any(kw in text_lower for kw in ENTRY_KEYWORDS + STOP_LOSS_KEYWORDS + TAKE_PROFIT_KEYWORDS):
        return 'trading_rule'
    
    if any(kw in text_lower for kw in ['example', 'case study', 'illustration']):
        return 'example'
    
    return 'concept'

def analyze_book(book_data: Dict, book_title: str) -> List[Dict]:
    """分析整本书，提取知识"""
    knowledge_items = []
    
    chapters = book_data.get('chapters', [])
    for chapter in chapters:
        chapter_num = chapter.get('chapter_number', 0)
        chapter_title = chapter.get('chapter_title', '')
        
        # 分析章节段落
        paragraphs = chapter.get('paragraphs', [])
        sections = chapter.get('sections', [])
        
        # 如果没有节，直接分析段落
        if not sections:
            for para in paragraphs:
                if len(para) > 50:  # 跳过太短的段落
                    patterns = extract_patterns_from_text(para)
                    rules = extract_trading_rules(para)
                    concepts = extract_key_concepts(para)
                    content_type = determine_content_type(para, patterns)
                    
                    if patterns or concepts or any(rules.values()):
                        knowledge_items.append({
                            'book_title': book_title,
                            'chapter_number': chapter_num,
                            'chapter_title': chapter_title,
                            'section_title': None,
                            'content_type': content_type,
                            'content_text': para[:2000],  # 限制长度
                            'extracted_patterns': json.dumps(patterns) if patterns else None,
                            'trading_rules_json': json.dumps(rules) if any(rules.values()) else None,
                            'key_concepts': json.dumps(concepts) if concepts else None,
                            'page_number': None
                        })
        else:
            # 分析每个节
            for section in sections:
                section_title = section.get('section_title', '')
                paragraphs = section.get('paragraphs', [])
                
                for para in paragraphs:
                    if len(para) > 50:
                        patterns = extract_patterns_from_text(para)
                        rules = extract_trading_rules(para)
                        concepts = extract_key_concepts(para)
                        content_type = determine_content_type(para, patterns)
                        
                        if patterns or concepts or any(rules.values()):
                            knowledge_items.append({
                                'book_title': book_title,
                                'chapter_number': chapter_num,
                                'chapter_title': chapter_title,
                                'section_title': section_title,
                                'content_type': content_type,
                                'content_text': para[:2000],
                                'extracted_patterns': json.dumps(patterns) if patterns else None,
                                'trading_rules_json': json.dumps(rules) if any(rules.values()) else None,
                                'key_concepts': json.dumps(concepts) if concepts else None,
                                'page_number': section.get('page_number')
                            })
    
    return knowledge_items

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    # 查找提取的JSON文件
    json_files = list(EXTRACTED_DIR.glob('*_extracted.json'))
    
    if not json_files:
        print(f"❌ 未找到提取的JSON文件")
        print(f"   请先运行: python scripts/abu_extract_ebook_text.py")
        return
    
    print("=" * 80)
    print("分析Al Brooks电子书文本")
    print("=" * 80)
    print(f"找到 {len(json_files)} 个提取文件\n")
    
    # 连接数据库
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 清空旧数据（如果存在同名书籍，先删除）
    # 可以手动控制，这里默认不清空，只追加
    # conn.execute('DELETE FROM ebook_knowledge_base')
    print("ℹ️  将追加新数据到知识库（不会删除旧数据）\n")
    
    total_items = 0
    
    for json_file in json_files:
        print(f"分析: {json_file.name}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
        
        book_title = book_data.get('book_title', json_file.stem.replace('_extracted', ''))
        
        # 分析书籍
        knowledge_items = analyze_book(book_data, book_title)
        
        # 入库（不指定id，让数据库自动生成）
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for item in knowledge_items:
            # 获取当前最大ID
            max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM ebook_knowledge_base').fetchone()
            next_id = (max_id_result[0] or 0) + 1
            
            conn.execute('''
                INSERT INTO ebook_knowledge_base 
                (id, book_title, chapter_number, chapter_title, section_title, 
                 content_type, content_text, extracted_patterns, trading_rules_json, 
                 key_concepts, related_image_path, page_number, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                next_id,
                item['book_title'],
                item['chapter_number'],
                item['chapter_title'],
                item['section_title'],
                item['content_type'],
                item['content_text'],
                item['extracted_patterns'],
                item['trading_rules_json'],
                item['key_concepts'],
                None,  # related_image_path
                item['page_number'],
                created_at
            ))
        
        conn.commit()
        total_items += len(knowledge_items)
        
        print(f"✅ 已提取 {len(knowledge_items)} 条知识")
        print(f"   章节数: {len(book_data.get('chapters', []))}")
        print()
    
    db.close()
    
    print("=" * 80)
    print(f"✅ 分析完成，共提取 {total_items} 条知识")
    print("=" * 80)
    
    # 统计信息
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    stats = conn.execute('''
        SELECT content_type, COUNT(*) as cnt 
        FROM ebook_knowledge_base 
        GROUP BY content_type
    ''').fetchall()
    
    print("\n📊 知识类型统计:")
    for content_type, cnt in stats:
        print(f"   {content_type}: {cnt}条")
    
    db.close()

if __name__ == '__main__':
    main()

