#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库结构设计
考虑分库分表策略
"""

import duckdb
from pathlib import Path
from datetime import datetime
import json

DB_DIR = Path(__file__).parent / "data"
MAIN_DB = DB_DIR / "qingniao_main.duckdb"
ARCHIVE_DB = DB_DIR / "qingniao_archive.duckdb"

class DatabaseDesign:
    """数据库结构设计"""
    
    def __init__(self):
        DB_DIR.mkdir(exist_ok=True)
    
    def create_main_database(self):
        """创建主数据库（当前数据）"""
        conn = duckdb.connect(str(MAIN_DB))
        
        # De.观点表（当前数据，最近3个月）
        # DuckDB会自动生成ROWID，但我们使用自定义ID以便跨库迁移
        conn.execute('''
            CREATE TABLE IF NOT EXISTS de_viewpoints (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                category TEXT,
                tags TEXT,
                btc_price REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                is_archived INTEGER DEFAULT 0
            )
        ''')
        
        # 对话日志表（当前数据，最近3个月）
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                user_message TEXT,
                assistant_message TEXT,
                timestamp TEXT NOT NULL,
                has_de_marker INTEGER DEFAULT 0,
                de_content TEXT,
                created_at TEXT NOT NULL,
                is_archived INTEGER DEFAULT 0
            )
        ''')
        
        # 交易记录表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS trade_records (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT DEFAULT 'BTC/USDT',
                direction TEXT,
                leverage INTEGER,
                entry_price REAL,
                exit_price REAL,
                profit_pct REAL,
                profit_usdt REAL,
                strategy TEXT,
                created_at TEXT NOT NULL,
                is_archived INTEGER DEFAULT 0
            )
        ''')
        
        # 创建索引
        conn.execute('CREATE INDEX IF NOT EXISTS idx_de_viewpoints_timestamp ON de_viewpoints(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_de_viewpoints_source ON de_viewpoints(source)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_de_viewpoints_category ON de_viewpoints(category)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_conversation_logs_timestamp ON conversation_logs(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_conversation_logs_de_marker ON conversation_logs(has_de_marker)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_trade_records_timestamp ON trade_records(timestamp)')
        
        conn.commit()
        conn.close()
        print(f"[OK] 主数据库创建完成: {MAIN_DB}")
    
    def create_archive_database(self):
        """创建归档数据库（历史数据，3个月以上）"""
        conn = duckdb.connect(str(ARCHIVE_DB))
        
        # 归档表结构与主数据库相同
        conn.execute('''
            CREATE TABLE IF NOT EXISTS de_viewpoints_archive (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                category TEXT,
                tags TEXT,
                btc_price REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                archived_at TEXT NOT NULL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversation_logs_archive (
                id INTEGER PRIMARY KEY,
                session_id TEXT,
                user_message TEXT,
                assistant_message TEXT,
                timestamp TEXT NOT NULL,
                has_de_marker INTEGER DEFAULT 0,
                de_content TEXT,
                created_at TEXT NOT NULL,
                archived_at TEXT NOT NULL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS trade_records_archive (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT DEFAULT 'BTC/USDT',
                direction TEXT,
                leverage INTEGER,
                entry_price REAL,
                exit_price REAL,
                profit_pct REAL,
                profit_usdt REAL,
                strategy TEXT,
                created_at TEXT NOT NULL,
                archived_at TEXT NOT NULL
            )
        ''')
        
        # 创建索引
        conn.execute('CREATE INDEX IF NOT EXISTS idx_de_viewpoints_archive_timestamp ON de_viewpoints_archive(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_conversation_logs_archive_timestamp ON conversation_logs_archive(timestamp)')
        
        conn.commit()
        conn.close()
        print(f"[OK] 归档数据库创建完成: {ARCHIVE_DB}")
    
    def init_all_databases(self):
        """初始化所有数据库"""
        print("=" * 80)
        print("初始化数据库结构")
        print("=" * 80)
        print()
        
        self.create_main_database()
        self.create_archive_database()
        
        print()
        print("=" * 80)
        print("数据库初始化完成！")
        print("=" * 80)

if __name__ == '__main__':
    design = DatabaseDesign()
    design.init_all_databases()

