#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库结构设计 V2
按交易员分库设计
"""

import duckdb
from pathlib import Path
from datetime import datetime

DB_DIR = Path(__file__).parent / "data"

# 交易员数据库
TRADERS = {
    'de': 'De.',
    'meng': '梦',
    # 未来可以添加更多交易员
}

class DatabaseDesignV2:
    """数据库结构设计 V2 - 按交易员分库"""
    
    def __init__(self):
        DB_DIR.mkdir(exist_ok=True)
    
    def create_trader_database(self, trader_id, trader_name):
        """为每个交易员创建独立的数据库"""
        db_file = DB_DIR / f"qingniao_{trader_id}.duckdb"
        conn = duckdb.connect(str(db_file))
        
        print(f"创建交易员数据库: {trader_name} ({trader_id})")
        
        # 1. 对话记录表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                user_message TEXT,
                trader_message TEXT,
                source TEXT DEFAULT 'discord',
                has_trading_info INTEGER DEFAULT 0,
                extracted_content TEXT,
                btc_price REAL,
                created_at TEXT NOT NULL,
                is_archived INTEGER DEFAULT 0
            )
        ''')
        
        # 2. 交易记录表
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
                screenshot_path TEXT,
                text_content TEXT,
                source TEXT DEFAULT 'manual',
                created_at TEXT NOT NULL,
                is_archived INTEGER DEFAULT 0
            )
        ''')
        
        # 3. 交易观点表（从对话和交易记录中提取）
        conn.execute('''
            CREATE TABLE IF NOT EXISTS trader_viewpoints (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                source TEXT DEFAULT 'conversation',
                category TEXT,
                tags TEXT,
                btc_price REAL,
                related_trade_id INTEGER,
                related_conversation_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                is_archived INTEGER DEFAULT 0
            )
        ''')
        
        # 4. 系统生成的信号表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY,
                signal_time TEXT NOT NULL,
                timeframe TEXT,
                signal_type TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,
                entry_model TEXT,
                strength TEXT,
                risk_reward_ratio REAL,
                volatility_level TEXT,
                system_name TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        
        # 5. 信号评估表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS signal_evaluations (
                id INTEGER PRIMARY KEY,
                signal_id INTEGER NOT NULL,
                evaluation_time TEXT NOT NULL,
                result TEXT,
                actual_entry_price REAL,
                actual_exit_price REAL,
                actual_profit_pct REAL,
                actual_profit_usdt REAL,
                stop_loss_hit INTEGER DEFAULT 0,
                take_profit_1_hit INTEGER DEFAULT 0,
                take_profit_2_hit INTEGER DEFAULT 0,
                missed INTEGER DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (signal_id) REFERENCES trading_signals(id)
            )
        ''')
        
        # 6. 策略规则表（可选，用于存储策略配置）
        conn.execute('''
            CREATE TABLE IF NOT EXISTS strategy_rules (
                id INTEGER PRIMARY KEY,
                rule_name TEXT NOT NULL,
                rule_type TEXT,
                rule_content TEXT,
                parameters TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        
        # 创建索引
        conn.execute('CREATE INDEX IF NOT EXISTS idx_conversations_timestamp ON conversations(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_trade_records_timestamp ON trade_records(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_trader_viewpoints_timestamp ON trader_viewpoints(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_trading_signals_signal_time ON trading_signals(signal_time)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_trading_signals_status ON trading_signals(status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_signal_evaluations_signal_id ON signal_evaluations(signal_id)')
        
        conn.commit()
        conn.close()
        
        print(f"  [OK] 数据库创建完成: {db_file}")
        return db_file
    
    def create_shared_database(self):
        """创建共享数据库（用于跨交易员查询）"""
        db_file = DB_DIR / "qingniao_shared.duckdb"
        conn = duckdb.connect(str(db_file))
        
        print("创建共享数据库...")
        
        # 交易员信息表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS traders (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT,
                database_file TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        ''')
        
        # 插入默认交易员
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for trader_id, trader_name in TRADERS.items():
            conn.execute('''
                INSERT OR REPLACE INTO traders 
                (id, name, display_name, database_file, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (trader_id, trader_name, trader_name, f'qingniao_{trader_id}.duckdb', 1, created_at))
        
        conn.commit()
        conn.close()
        
        print(f"  [OK] 共享数据库创建完成: {db_file}")
        return db_file
    
    def init_all_databases(self):
        """初始化所有数据库"""
        print("=" * 80)
        print("初始化数据库结构 V2 (按交易员分库)")
        print("=" * 80)
        print()
        
        # 创建共享数据库
        self.create_shared_database()
        print()
        
        # 为每个交易员创建数据库
        for trader_id, trader_name in TRADERS.items():
            self.create_trader_database(trader_id, trader_name)
        
        print()
        print("=" * 80)
        print("数据库初始化完成！")
        print("=" * 80)
        print()
        print("数据库文件位置:")
        print(f"  共享数据库: {DB_DIR}/qingniao_shared.duckdb")
        for trader_id in TRADERS.keys():
            print(f"  {TRADERS[trader_id]}数据库: {DB_DIR}/qingniao_{trader_id}.duckdb")

if __name__ == '__main__':
    design = DatabaseDesignV2()
    design.init_all_databases()

