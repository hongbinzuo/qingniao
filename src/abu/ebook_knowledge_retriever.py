#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电子书知识检索接口
提供电子书知识库的查询和检索功能
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent.parent

# 确保可以导入数据库管理器
if str(ROOT / 'src') not in sys.path:
    sys.path.insert(0, str(ROOT / 'src'))

try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  数据库模块不可用", file=sys.stderr)


class EbookKnowledgeRetriever:
    """电子书知识检索器"""
    
    def __init__(self, trader_id: str = 'abu'):
        if not DB_AVAILABLE:
            raise RuntimeError("数据库模块不可用")
        
        self.db = TraderDBManager(trader_id)
        # 使用只读连接，允许多进程同时读取
        self.conn = self.db._get_connection(read_only=True)
    
    def get_pattern_info(self, pattern_name: str) -> List[Dict]:
        """
        获取模式的电子书信息
        
        Args:
            pattern_name: 模式名称（如 'Wedge', 'Triangle'等）
        
        Returns:
            电子书信息列表
        """
        # 从pattern_library查找匹配的模式
        patterns = self.conn.execute('''
            SELECT id, pattern_name, pattern_type, text_description, ebook_references
            FROM pattern_library
            WHERE pattern_type LIKE ? OR pattern_name LIKE ?
            LIMIT 10
        ''', (f'%{pattern_name}%', f'%{pattern_name}%')).fetchall()
        
        results = []
        for pattern_id, pname, ptype, text_desc, ebook_refs in patterns:
            # 解析电子书引用
            refs = []
            if ebook_refs:
                try:
                    refs = json.loads(ebook_refs)
                except:
                    pass
            
            # 获取详细的电子书内容
            ebook_details = []
            for ref in refs:
                ebook_item_id = ref.get('ebook_item_id')
                if ebook_item_id:
                    ebook_item = self.conn.execute('''
                        SELECT book_title, chapter_number, chapter_title, section_title,
                               content_type, content_text, trading_rules_json, key_concepts
                        FROM ebook_knowledge_base
                        WHERE id = ?
                    ''', (ebook_item_id,)).fetchone()
                    
                    if ebook_item:
                        book_title, ch_num, ch_title, sec_title, content_type, \
                        content_text, rules_json, concepts_json = ebook_item
                        
                        # 解析交易规则
                        rules = {}
                        if rules_json:
                            try:
                                rules = json.loads(rules_json)
                            except:
                                pass
                        
                        # 解析关键概念
                        concepts = []
                        if concepts_json:
                            try:
                                concepts = json.loads(concepts_json)
                            except:
                                pass
                        
                        ebook_details.append({
                            'book': book_title,
                            'chapter': ch_num,
                            'chapter_title': ch_title,
                            'section': sec_title,
                            'content_type': content_type,
                            'content': content_text,
                            'trading_rules': rules,
                            'key_concepts': concepts,
                            'similarity': ref.get('similarity', 0.0)
                        })
            
            results.append({
                'pattern_id': pattern_id,
                'pattern_name': pname,
                'pattern_type': ptype,
                'text_description': text_desc,
                'ebook_references': refs,
                'ebook_details': ebook_details
            })
        
        return results
    
    def get_trading_rules(self, pattern_name: str) -> List[Dict]:
        """
        获取模式的交易规则
        
        Args:
            pattern_name: 模式名称
        
        Returns:
            交易规则列表
        """
        # 从电子书知识库查找
        items = self.conn.execute('''
            SELECT trading_rules_json, content_text, book_title, chapter_title, section_title
            FROM ebook_knowledge_base
            WHERE extracted_patterns LIKE ? 
              AND trading_rules_json IS NOT NULL
              AND trading_rules_json != ''
            ORDER BY id
            LIMIT 20
        ''', (f'%{pattern_name}%',)).fetchall()
        
        rules = []
        for rules_json, content, book, chapter, section in items:
            try:
                rule_data = json.loads(rules_json)
                if rule_data and any(rule_data.values()):
                    rules.append({
                        'book': book,
                        'chapter': chapter,
                        'section': section,
                        'rules': rule_data,
                        'context': content[:500] if content else ''
                    })
            except:
                continue
        
        return rules
    
    def get_pattern_description(self, pattern_name: str) -> Optional[Dict]:
        """
        获取模式的完整描述（文本描述 + 电子书内容）
        
        Args:
            pattern_name: 模式名称
        
        Returns:
            模式描述字典
        """
        pattern_info = self.get_pattern_info(pattern_name)
        if not pattern_info:
            return None
        
        # 使用第一个匹配的模式
        info = pattern_info[0]
        
        # 汇总所有电子书描述
        descriptions = []
        for detail in info['ebook_details']:
            if detail['content']:
                descriptions.append({
                    'source': f"{detail['book']} - {detail['chapter_title']}",
                    'content': detail['content'],
                    'concepts': detail.get('key_concepts', [])
                })
        
        return {
            'pattern_name': info['pattern_name'],
            'pattern_type': info['pattern_type'],
            'text_description': info['text_description'],
            'ebook_descriptions': descriptions,
            'trading_rules': self.get_trading_rules(pattern_name)
        }
    
    def search_concepts(self, keyword: str, limit: int = 10) -> List[Dict]:
        """
        搜索关键概念
        
        Args:
            keyword: 关键词
            limit: 返回数量限制
        
        Returns:
            匹配的知识项列表
        """
        items = self.conn.execute('''
            SELECT id, book_title, chapter_title, section_title, content_text,
                   extracted_patterns, key_concepts, trading_rules_json
            FROM ebook_knowledge_base
            WHERE content_text LIKE ? 
               OR key_concepts LIKE ?
               OR extracted_patterns LIKE ?
            LIMIT ?
        ''', (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', limit)).fetchall()
        
        results = []
        for item_id, book, chapter, section, content, patterns, concepts, rules in items:
            results.append({
                'id': item_id,
                'book': book,
                'chapter': chapter,
                'section': section,
                'content': content[:500] if content else '',
                'patterns': json.loads(patterns) if patterns else [],
                'concepts': json.loads(concepts) if concepts else [],
                'has_rules': bool(rules)
            })
        
        return results
    
    def validate_pattern_with_ebook(self, pattern_match: Dict, pattern_name: str) -> Dict:
        """
        使用电子书知识验证模式匹配
        
        Args:
            pattern_match: 模式匹配结果
            pattern_name: 模式名称
        
        Returns:
            验证结果字典
        """
        pattern_info = self.get_pattern_info(pattern_name)
        
        if not pattern_info:
            return {
                'validated': False,
                'reason': 'No ebook knowledge found',
                'confidence_adjustment': 0.0
            }
        
        # 简单验证：如果有电子书关联，增加置信度
        info = pattern_info[0]
        ebook_count = len(info['ebook_details'])
        
        confidence_adjustment = min(0.1 * ebook_count, 0.3)  # 最多增加0.3
        
        return {
            'validated': True,
            'ebook_references_count': ebook_count,
            'confidence_adjustment': confidence_adjustment,
            'ebook_details': info['ebook_details'][:3]  # 返回前3个
        }
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()



