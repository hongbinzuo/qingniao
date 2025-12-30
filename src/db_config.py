#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置模块
选择使用的数据库类型
"""

import os
from pathlib import Path

# 数据库类型: 'duckdb', 'mysql', 'sqlite', 'tinydb'
DB_TYPE = os.getenv('QINGNIAO_DB_TYPE', 'duckdb')  # 默认使用DuckDB

# MySQL配置（如果使用MySQL）
MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', 'localhost'),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'qingniao'),
    'charset': 'utf8mb4'
}

def get_db_manager():
    """根据配置返回数据库管理器"""
    if DB_TYPE == 'duckdb':
        try:
            from db_manager_duckdb import DuckDBManager
            return DuckDBManager()
        except ImportError:
            print("WARNING: DuckDB not installed, please run: pip install duckdb")
            # 回退到SQLite
            from db_manager import DatabaseManager
            return DatabaseManager()
    
    elif DB_TYPE == 'mysql':
        try:
            from db_manager_mysql import MySQLManager
            return MySQLManager(**MYSQL_CONFIG)
        except ImportError:
            print("⚠️ MySQL连接器未安装，请运行: pip install mysql-connector-python")
            raise
    
    elif DB_TYPE == 'sqlite':
        from db_manager import DatabaseManager
        return DatabaseManager()
    
    elif DB_TYPE == 'tinydb':
        try:
            from db_manager_tinydb import TinyDBManager
            return TinyDBManager()
        except ImportError:
            print("⚠️ TinyDB未安装，请运行: pip install tinydb")
            raise
    
    else:
        raise ValueError(f"不支持的数据库类型: {DB_TYPE}")

if __name__ == '__main__':
    print(f"当前数据库类型: {DB_TYPE}")
    print("要更改数据库类型，请设置环境变量 QINGNIAO_DB_TYPE")
    print("可选值: duckdb, mysql, sqlite, tinydb")

