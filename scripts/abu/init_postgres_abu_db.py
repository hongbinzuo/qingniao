#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化 PostgreSQL Abu 数据库
"""

import psycopg2
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

def _is_wsl() -> bool:
    if os.getenv('WSL_DISTRO_NAME') or os.getenv('WSL_INTEROP'):
        return True
    try:
        return 'microsoft' in Path('/proc/version').read_text(encoding='utf-8', errors='ignore').lower()
    except Exception:
        return False

def _load_env():
    root = Path(__file__).resolve().parents[2]
    wsl_env = root / '.env.wsl'
    if _is_wsl() and wsl_env.exists():
        load_dotenv(wsl_env, override=True)
    load_dotenv(override=False)

_load_env()

def init_database():
    """创建 Abu 系统所需的表结构"""
    
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("PostgreSQL Abu 数据库初始化")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('PG_HOST', 'localhost'),
            port=int(os.getenv('PG_PORT', 5432)),
            database=os.getenv('PG_DATABASE', 'qingniao_abu'),
            user=os.getenv('PG_USER', 'abu_user'),
            password=os.getenv('PG_PASSWORD', '')
        )
        
        cursor = conn.cursor()
        
        print("\n[1/5] 创建 trading_signals 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trading_signals (
                id SERIAL PRIMARY KEY,
                signal_time TIMESTAMP NOT NULL,
                timeframe VARCHAR(10),
                symbol VARCHAR(20),
                signal_type VARCHAR(10),
                entry_price NUMERIC(20, 8),
                stop_loss NUMERIC(20, 8),
                take_profit_1 NUMERIC(20, 8),
                take_profit_2 NUMERIC(20, 8),
                entry_model TEXT,
                strength VARCHAR(20),
                risk_reward_ratio NUMERIC(10, 2),
                volatility_level VARCHAR(20),
                system_name VARCHAR(50),
                score NUMERIC(10, 2),
                notes TEXT,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                
                -- 信号反馈相关字段
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                exit_price NUMERIC(20, 8),
                exit_reason TEXT,
                pnl_pct NUMERIC(10, 4),
                breakeven_stop_set BOOLEAN DEFAULT FALSE,
                quick_tp_reached BOOLEAN DEFAULT FALSE,
                last_check_time TIMESTAMP,
                check_count INTEGER DEFAULT 0,
                entry_price_actual NUMERIC(20, 8)
            )
        ''')
        
        # 创建索引
        print("   创建索引...")
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_symbol ON trading_signals(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_status ON trading_signals(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_created_at ON trading_signals(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timeframe ON trading_signals(timeframe)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_system ON trading_signals(system_name)')
        print("   [OK] trading_signals 表创建成功")
        
        print("\n[2/5] 创建 signal_evaluations 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signal_evaluations (
                id SERIAL PRIMARY KEY,
                signal_id INTEGER NOT NULL,
                evaluation_time TIMESTAMP NOT NULL,
                result VARCHAR(20),
                actual_entry_price NUMERIC(20, 8),
                actual_exit_price NUMERIC(20, 8),
                actual_profit_pct NUMERIC(10, 4),
                actual_profit_usdt NUMERIC(20, 8),
                stop_loss_hit BOOLEAN DEFAULT FALSE,
                take_profit_1_hit BOOLEAN DEFAULT FALSE,
                take_profit_2_hit BOOLEAN DEFAULT FALSE,
                missed BOOLEAN DEFAULT FALSE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (signal_id) REFERENCES trading_signals(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_evaluations_signal_id ON signal_evaluations(signal_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_evaluations_time ON signal_evaluations(evaluation_time)')
        print("   [OK] signal_evaluations 表创建成功")
        
        print("\n[3/5] 创建 pattern_library 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_library (
                id SERIAL PRIMARY KEY,
                pattern_name TEXT,
                pattern_type TEXT,
                source_page INTEGER,
                source_pdf TEXT,
                image_path TEXT,
                context_text TEXT,
                gemini_annotation_json TEXT,
                chart_features_json TEXT,
                timeframe_hint TEXT,
                direction TEXT,
                key_features TEXT,
                confidence DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                ebook_references TEXT,
                text_description TEXT
            )
        ''')

        # 兼容旧表结构：补齐缺失字段
        missing_columns = [
            ("pattern_name", "TEXT"),
            ("pattern_type", "TEXT"),
            ("source_page", "INTEGER"),
            ("source_pdf", "TEXT"),
            ("image_path", "TEXT"),
            ("context_text", "TEXT"),
            ("gemini_annotation_json", "TEXT"),
            ("chart_features_json", "TEXT"),
            ("timeframe_hint", "TEXT"),
            ("direction", "TEXT"),
            ("key_features", "TEXT"),
            ("confidence", "DOUBLE PRECISION"),
            ("created_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TIMESTAMP"),
            ("ebook_references", "TEXT"),
            ("text_description", "TEXT"),
        ]
        for col_name, col_type in missing_columns:
            cursor.execute(
                f"ALTER TABLE pattern_library ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
            )

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_type ON pattern_library(pattern_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_name ON pattern_library(pattern_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_pattern_source_page ON pattern_library(source_page)')
        print("   [OK] pattern_library 表创建成功")
        
        print("\n[4/6] 创建 ml_optimization_results 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ml_optimization_results (
                id SERIAL PRIMARY KEY,
                model_type VARCHAR(50),
                parameters_json TEXT,
                metrics_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ml_model_type ON ml_optimization_results(model_type)')
        print("   [OK] ml_optimization_results 表创建成功")
        
        print("\n[5/6] 创建 system_configs 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_configs (
                id SERIAL PRIMARY KEY,
                config_key VARCHAR(100) UNIQUE NOT NULL,
                config_value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_config_key ON system_configs(config_key)')
        print("   [OK] system_configs 表创建成功")

        print("\n[6/6] 创建 vision_match_records 表...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vision_match_records (
                id SERIAL PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT,
                batch_id TEXT,
                symbol TEXT,
                timeframe TEXT,
                pattern_id TEXT,
                pattern_name TEXT,
                pattern_type TEXT,
                algorithm_score DOUBLE PRECISION,
                vision_score DOUBLE PRECISION,
                final_score DOUBLE PRECISION,
                accepted BOOLEAN,
                model TEXT,
                pattern_image TEXT,
                chart_image TEXT,
                vision_result JSONB,
                extra JSONB
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vision_symbol ON vision_match_records(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vision_timeframe ON vision_match_records(timeframe)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vision_created_at ON vision_match_records(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vision_batch ON vision_match_records(batch_id)')
        print("   [OK] vision_match_records 表创建成功")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] PostgreSQL 数据库初始化完成！")
        print("=" * 60)
        print("\n数据库信息:")
        print(f"  主机: {os.getenv('PG_HOST', 'localhost')}")
        print(f"  端口: {os.getenv('PG_PORT', 5432)}")
        print(f"  数据库: {os.getenv('PG_DATABASE', 'qingniao_abu')}")
        print(f"  用户: {os.getenv('PG_USER', 'abu_user')}")
        print("\n已创建表:")
        print("  1. trading_signals (交易信号)")
        print("  2. signal_evaluations (信号评估)")
        print("  3. pattern_library (模式库)")
        print("  4. ml_optimization_results (ML优化结果)")
        print("  5. system_configs (系统配置)")
        print("  6. vision_match_records (视觉匹配记录)")
        
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    init_database()
