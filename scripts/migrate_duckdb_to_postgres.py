#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 DuckDB 数据迁移到 PostgreSQL
"""

import duckdb
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

def _is_wsl() -> bool:
    if os.getenv('WSL_DISTRO_NAME') or os.getenv('WSL_INTEROP'):
        return True
    try:
        return 'microsoft' in Path('/proc/version').read_text(encoding='utf-8', errors='ignore').lower()
    except Exception:
        return False

def _load_env():
    root = Path(__file__).resolve().parent.parent
    wsl_env = root / '.env.wsl'
    if _is_wsl() and wsl_env.exists():
        load_dotenv(wsl_env, override=True)
    load_dotenv(override=False)

_load_env()

DB_DIR = Path(__file__).parent.parent / "src" / "data"
DUCKDB_FILE = DB_DIR / "qingniao_abu.duckdb"

def migrate_table(duck_conn, pg_conn, table_name, columns, select_columns=None, on_conflict=None):
    """迁移单个表"""
    print(f"\n迁移表: {table_name}")
    
    # 读取 DuckDB 数据
    try:
        columns_to_select = select_columns or columns
        select_cols_sql = ", ".join(columns_to_select)
        rows = duck_conn.execute(f"SELECT {select_cols_sql} FROM {table_name}").fetchall()
        print(f"  从 DuckDB 读取 {len(rows)} 条记录")
    except Exception as e:
        print(f"  ⚠️ 表不存在或读取失败: {e}")
        return
    
    if not rows:
        print("  ℹ️ 表为空，跳过")
        return
    
    # 写入 PostgreSQL
    pg_cursor = pg_conn.cursor()
    placeholders = ', '.join(['%s'] * len(columns))
    insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    if on_conflict:
        insert_query += f" ON CONFLICT ({on_conflict}) DO NOTHING"
    
    success_count = 0
    error_count = 0
    
    for row in rows:
        try:
            # DuckDB 返回的是 tuple，需要转换
            values = list(row)
            pg_cursor.execute(insert_query, values)
            success_count += 1
        except Exception as e:
            error_count += 1
            try:
                pg_conn.rollback()
            except Exception:
                pass
            if error_count <= 3:  # 只显示前3个错误
                print(f"  ❌ 插入失败: {e}")
            continue
    
    pg_conn.commit()
    print(f"  ✅ 成功迁移 {success_count} 条记录", end="")
    if error_count > 0:
        print(f"，失败 {error_count} 条")
    else:
        print()

def reset_sequence(pg_conn, table_name, column_name):
    """重置 SERIAL 序列，避免后续插入冲突"""
    try:
        with pg_conn.cursor() as cursor:
            cursor.execute(
                f"SELECT setval(pg_get_serial_sequence(%s, %s), "
                f"(SELECT COALESCE(MAX({column_name}), 1) FROM {table_name}))",
                (table_name, column_name),
            )
        pg_conn.commit()
        print(f"  ✅ 已重置 {table_name}.{column_name} 的序列")
    except Exception as e:
        pg_conn.rollback()
        print(f"  ⚠️ 序列重置失败: {e}")

def main():
    """主迁移流程"""
    
    print("=" * 60)
    print("DuckDB → PostgreSQL 数据迁移工具")
    print("=" * 60)
    
    if not DUCKDB_FILE.exists():
        print(f"\n❌ DuckDB 文件不存在: {DUCKDB_FILE}")
        print("   如果这是新安装，可以跳过迁移步骤。")
        return
    
    # 连接 DuckDB
    print("\n[1] 连接 DuckDB...")
    try:
        duck_conn = duckdb.connect(str(DUCKDB_FILE), read_only=True)
        print("  ✅ DuckDB 连接成功")
    except Exception as e:
        print(f"  ❌ DuckDB 连接失败: {e}")
        return
    
    # 连接 PostgreSQL
    print("\n[2] 连接 PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(
            host=os.getenv('PG_HOST', 'localhost'),
            port=int(os.getenv('PG_PORT', 5432)),
            database=os.getenv('PG_DATABASE', 'qingniao_abu'),
            user=os.getenv('PG_USER', 'abu_user'),
            password=os.getenv('PG_PASSWORD', '')
        )
        print("  ✅ PostgreSQL 连接成功")
    except Exception as e:
        print(f"  ❌ PostgreSQL 连接失败: {e}")
        print("     请确保:")
        print("     1. PostgreSQL 服务正在运行")
        print("     2. 数据库 qingniao_abu 已创建")
        print("     3. .env 文件配置正确")
        duck_conn.close()
        return
    
    # 迁移 trading_signals 表
    print("\n[3] 迁移数据...")
    migrate_table(
        duck_conn, pg_conn, 'trading_signals',
        [
            'id', 'signal_time', 'timeframe', 'symbol', 'signal_type', 'entry_price',
            'stop_loss', 'take_profit_1', 'take_profit_2', 'entry_model',
            'strength', 'risk_reward_ratio', 'volatility_level', 'system_name',
            'status', 'created_at', 'updated_at', 'score', 'notes'
        ],
        on_conflict='id'
    )
    reset_sequence(pg_conn, 'trading_signals', 'id')
    
    # 迁移 signal_evaluations 表
    migrate_table(
        duck_conn, pg_conn, 'signal_evaluations',
        [
            'signal_id', 'evaluation_time', 'result', 'actual_entry_price',
            'actual_exit_price', 'actual_profit_pct', 'actual_profit_usdt',
            'stop_loss_hit', 'take_profit_1_hit', 'take_profit_2_hit',
            'missed', 'notes', 'created_at'
        ]
    )
    
    # 迁移 pattern_library 表（如果存在）
    migrate_table(
        duck_conn, pg_conn, 'pattern_library',
        [
            'id', 'pattern_name', 'pattern_type', 'source_page', 'source_pdf',
            'image_path', 'context_text', 'gemini_annotation_json',
            'chart_features_json', 'timeframe_hint', 'direction',
            'key_features', 'confidence', 'created_at', 'updated_at',
            'ebook_references', 'text_description'
        ],
        on_conflict='id'
    )
    reset_sequence(pg_conn, 'pattern_library', 'id')
    
    duck_conn.close()
    pg_conn.close()
    
    print("\n" + "=" * 60)
    print("✅ 迁移完成！")
    print("=" * 60)
    print("\n下一步:")
    print("  1. 运行测试验证: python src/db_manager_postgres.py")
    print("  2. 备份 DuckDB 文件: move src\\data\\qingniao_abu.duckdb src\\data\\qingniao_abu.duckdb.bak")
    print("  3. 重启 Abu 系统: scripts/abu/Abu全部启动.bat")

if __name__ == '__main__':
    main()
