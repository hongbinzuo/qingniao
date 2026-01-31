#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""创建电子书知识库表"""
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
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
    
    print("=" * 80)
    print("创建电子书知识库表")
    print("=" * 80)
    print()
    
    # 删除旧表（如果存在）并重建
    print("创建 ebook_knowledge_base 表...")
    try:
        conn.execute('DROP TABLE IF EXISTS ebook_knowledge_base')
        print("  删除旧表（如果存在）")
    except:
        pass
    
    conn.execute('''
        CREATE TABLE ebook_knowledge_base (
            id INTEGER PRIMARY KEY,
            book_title TEXT NOT NULL,
            chapter_number INTEGER,
            chapter_title TEXT,
            section_title TEXT,
            content_type TEXT,  -- 'pattern_description', 'trading_rule', 'concept', 'example'
            content_text TEXT NOT NULL,
            extracted_patterns TEXT,  -- JSON数组: ["Wedge", "Triangle"]
            trading_rules_json TEXT,  -- JSON: {entry: "...", stop_loss: "...", take_profit: "..."}
            key_concepts TEXT,  -- JSON数组: ["support", "resistance", "breakout"]
            related_image_path TEXT,
            page_number INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    # 创建索引
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ebook_patterns ON ebook_knowledge_base(extracted_patterns)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ebook_content_type ON ebook_knowledge_base(content_type)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ebook_book_title ON ebook_knowledge_base(book_title)')
    
    print("✅ ebook_knowledge_base 表创建成功")
    print()
    
    # 扩展pattern_library表
    print("扩展 pattern_library 表...")
    try:
        conn.execute('ALTER TABLE pattern_library ADD COLUMN ebook_references TEXT')
        print("✅ 添加 ebook_references 字段成功")
    except Exception as e:
        if 'duplicate column' in str(e).lower():
            print("ℹ️  ebook_references 字段已存在")
        else:
            print(f"⚠️  添加 ebook_references 字段失败: {e}")
    
    try:
        conn.execute('ALTER TABLE pattern_library ADD COLUMN text_description TEXT')
        print("✅ 添加 text_description 字段成功")
    except Exception as e:
        if 'duplicate column' in str(e).lower():
            print("ℹ️  text_description 字段已存在")
        else:
            print(f"⚠️  添加 text_description 字段失败: {e}")
    
    conn.commit()
    db.close()
    
    print()
    print("=" * 80)
    print("✅ 电子书知识库表创建完成")
    print("=" * 80)

if __name__ == '__main__':
    main()

