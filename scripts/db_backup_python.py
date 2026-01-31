#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库备份工具 - Python版本 (不依赖pg_dump)
Database Backup Utility - Python version (no pg_dump dependency)

用法 / Usage:
    python scripts/db_backup_python.py --backup
    python scripts/db_backup_python.py --list
"""

import argparse
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

# Backup directory
BACKUP_BASE_DIR = ROOT / "backups" / "database"
BACKUP_BASE_DIR.mkdir(parents=True, exist_ok=True)

def get_backup_dir():
    """获取今天的备份目录"""
    today = datetime.now().strftime('%Y%m%d')
    backup_dir = BACKUP_BASE_DIR / today
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def backup_database():
    """备份数据库 - 导出为JSON格式"""
    db = TraderDBManager()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_{timestamp}.json.gz"
    
    backup_dir = get_backup_dir()
    backup_path = backup_dir / filename
    
    print(f"备份数据库到: {backup_path}")
    print(f"Backing up database to: {backup_path}")
    
    try:
        # Get all tables
        tables = ['trading_signals', 'abu_patterns', 'signal_evaluations']
        backup_data = {}
        
        for table in tables:
            try:
                query = f"SELECT * FROM {table}"
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(query)
                rows = cursor.fetchall()
                backup_data[table] = rows
                print(f"  ✓ 备份表: {table} ({len(rows)} 行)")
            except Exception as e:
                print(f"  ⚠ 跳过表 {table}: {e}")
        
        # Save to compressed JSON
        with gzip.open(backup_path, 'wt', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        size = backup_path.stat().st_size / 1024 / 1024
        print(f"✓ 备份成功: {filename} ({size:.2f} MB)")
        print(f"✓ Backup successful: {filename} ({size:.2f} MB)")
        return str(backup_path)
        
    except Exception as e:
        print(f"✗ 备份失败: {e}")
        return None


def list_backups():
    """列出所有备份"""
    all_backups = []
    for date_dir in sorted(BACKUP_BASE_DIR.iterdir(), reverse=True):
        if date_dir.is_dir():
            backups = list(date_dir.glob("*.json.gz"))
            for backup in backups:
                all_backups.append((date_dir.name, backup))
    
    if not all_backups:
        print("没有找到备份文件")
        return
    
    print(f"\n可用备份:")
    print("=" * 60)
    for date, backup in all_backups:
        size = backup.stat().st_size / 1024 / 1024
        print(f"[{date}] {backup.name} ({size:.2f} MB)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="数据库备份工具")
    parser.add_argument('--backup', action='store_true', help='备份数据库')
    parser.add_argument('--list', action='store_true', help='列出所有备份')
    args = parser.parse_args()
    
    if args.backup:
        backup_database()
    elif args.list:
        list_backups()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
