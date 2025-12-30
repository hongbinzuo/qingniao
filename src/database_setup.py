#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
使用SQLite数据库存储De.观点和对话日志
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

# 数据库文件路径
DB_DIR = Path(__file__).parent / "data"
DB_FILE = DB_DIR / "qingniao.db"

def init_database():
    """初始化数据库"""
    # 创建数据目录
    DB_DIR.mkdir(exist_ok=True)
    
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row  # 返回字典格式
    cursor = conn.cursor()
    
    # 创建De.观点表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS de_viewpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            category TEXT,
            tags TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    # 创建对话日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_message TEXT,
            assistant_message TEXT,
            timestamp TEXT NOT NULL,
            has_de_marker INTEGER DEFAULT 0,
            de_content TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_de_viewpoints_timestamp 
        ON de_viewpoints(timestamp)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_de_viewpoints_source 
        ON de_viewpoints(source)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_logs_timestamp 
        ON conversation_logs(timestamp)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_conversation_logs_de_marker 
        ON conversation_logs(has_de_marker)
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据库初始化完成: {DB_FILE}")
    return DB_FILE

if __name__ == '__main__':
    init_database()

