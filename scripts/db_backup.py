#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库备份和恢复工具
Database Backup and Restore Utility

功能 / Features:
- 备份数据库数据和结构 / Backup database data and schema
- 恢复数据库 / Restore database
- 支持无数据库时的结构备份 / Support schema backup when no DB exists

用法 / Usage:
    # 备份数据库 / Backup database
    python scripts/db_backup.py --backup

    # 仅备份结构 / Backup schema only
    python scripts/db_backup.py --backup-schema

    # 恢复数据库 / Restore database
    python scripts/db_backup.py --restore backup_20260131_123456.sql

    # 列出所有备份 / List all backups
    python scripts/db_backup.py --list
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Backup directory - organized by date
BACKUP_BASE_DIR = ROOT / "backups" / "database"
BACKUP_BASE_DIR.mkdir(parents=True, exist_ok=True)


def get_backup_dir():
    """获取今天的备份目录 / Get today's backup directory"""
    today = datetime.now().strftime("%Y%m%d")
    backup_dir = BACKUP_BASE_DIR / today
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def get_db_config():
    """获取数据库配置"""
    from dotenv import load_dotenv

    load_dotenv()

    return {
        "host": os.getenv("PG_HOST", "localhost"),
        "port": os.getenv("PG_PORT", "5432"),
        "database": os.getenv("PG_DATABASE", "qingniao"),
        "user": os.getenv("PG_USER", "postgres"),
        "password": os.getenv("PG_PASSWORD", ""),
    }


def backup_database(schema_only=False):
    """备份数据库"""
    config = get_db_config()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if schema_only:
        filename = f"schema_{timestamp}.sql"
    else:
        filename = f"backup_{timestamp}.sql"

    backup_dir = get_backup_dir()
    backup_path = backup_dir / filename

    print(f"备份数据库到: {backup_path}")
    print(f"Backing up database to: {backup_path}")

    # Build pg_dump command
    cmd = [
        "pg_dump",
        "-h",
        config["host"],
        "-p",
        config["port"],
        "-U",
        config["user"],
        "-d",
        config["database"],
        "-f",
        str(backup_path),
    ]

    if schema_only:
        cmd.append("--schema-only")

    # Set password environment variable
    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ 备份成功: {filename}")
            print(f"✓ Backup successful: {filename}")
            return str(backup_path)
        else:
            print(f"✗ 备份失败: {result.stderr}")
            print(f"✗ Backup failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"✗ 错误: {e}")
        print(f"✗ Error: {e}")
        return None


def restore_database(backup_file):
    """恢复数据库"""
    config = get_db_config()

    # Search for backup file in all subdirectories
    backup_path = None
    for date_dir in BACKUP_BASE_DIR.iterdir():
        if date_dir.is_dir():
            potential_path = date_dir / backup_file
            if potential_path.exists():
                backup_path = potential_path
                break

    if not backup_path:
        print(f"✗ 备份文件不存在: {backup_file}")
        print(f"✗ Backup file not found: {backup_file}")
        return False

    print(f"恢复数据库从: {backup_path}")
    print(f"Restoring database from: {backup_path}")

    # Build psql command
    cmd = [
        "psql",
        "-h",
        config["host"],
        "-p",
        config["port"],
        "-U",
        config["user"],
        "-d",
        config["database"],
        "-f",
        str(backup_path),
    ]

    # Set password environment variable
    env = os.environ.copy()
    env["PGPASSWORD"] = config["password"]

    try:
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ 恢复成功")
            print(f"✓ Restore successful")
            return True
        else:
            print(f"✗ 恢复失败: {result.stderr}")
            print(f"✗ Restore failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        print(f"✗ Error: {e}")
        return False


def list_backups():
    """列出所有备份"""
    # Collect all backups from all date subdirectories
    all_backups = []
    for date_dir in sorted(BACKUP_BASE_DIR.iterdir(), reverse=True):
        if date_dir.is_dir():
            backups = list(date_dir.glob("*.sql"))
            for backup in backups:
                all_backups.append((date_dir.name, backup))

    if not all_backups:
        print("没有找到备份文件")
        print("No backup files found")
        return

    print(f"\n可用备份 / Available backups:")
    print("=" * 60)
    for date, backup in all_backups:
        size = backup.stat().st_size / 1024 / 1024
        print(f"[{date}] {backup.name} ({size:.2f} MB)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="数据库备份和恢复工具")
    parser.add_argument("--backup", action="store_true", help="备份数据库")
    parser.add_argument("--backup-schema", action="store_true", help="仅备份结构")
    parser.add_argument("--restore", type=str, help="恢复数据库")
    parser.add_argument("--list", action="store_true", help="列出所有备份")

    args = parser.parse_args()

    if args.backup:
        backup_database(schema_only=False)
    elif args.backup_schema:
        backup_database(schema_only=True)
    elif args.restore:
        restore_database(args.restore)
    elif args.list:
        list_backups()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
