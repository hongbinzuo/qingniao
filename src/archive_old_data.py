#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
归档旧数据到归档数据库
自动将3个月前的数据归档
"""

import duckdb
from pathlib import Path
from datetime import datetime, timedelta

DB_DIR = Path(__file__).parent / "data"
MAIN_DB = DB_DIR / "qingniao_main.duckdb"
ARCHIVE_DB = DB_DIR / "qingniao_archive.duckdb"

def archive_conversation_logs(days=90):
    """归档对话日志"""
    if not MAIN_DB.exists() or not ARCHIVE_DB.exists():
        print("数据库不存在，请先初始化数据库")
        return
    
    main_conn = duckdb.connect(str(MAIN_DB))
    archive_conn = duckdb.connect(str(ARCHIVE_DB))
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    archived_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"归档 {days} 天前的对话日志（截止日期: {cutoff_date}）...")
    
    # 查询需要归档的数据
    result = main_conn.execute('''
        SELECT * FROM conversation_logs 
        WHERE timestamp < ? AND is_archived = 0
    ''', (cutoff_date,)).fetchall()
    
    if not result:
        print("没有需要归档的数据")
        main_conn.close()
        archive_conn.close()
        return
    
    print(f"找到 {len(result)} 条需要归档的数据")
    
    # 插入到归档数据库
    archived_count = 0
    for row in result:
        try:
            archive_conn.execute('''
                INSERT INTO conversation_logs_archive 
                (id, session_id, user_message, assistant_message, timestamp, 
                 has_de_marker, de_content, created_at, archived_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row[0], row[1], row[2], row[3], row[4],
                row[5], row[6], row[7], archived_at
            ))
            archived_count += 1
        except Exception as e:
            print(f"归档失败 (ID: {row[0]}): {e}")
    
    archive_conn.commit()
    
    # 从主数据库删除（标记为已归档）
    main_conn.execute('''
        UPDATE conversation_logs 
        SET is_archived = 1 
        WHERE timestamp < ? AND is_archived = 0
    ''', (cutoff_date,))
    
    main_conn.commit()
    
    print(f"✅ 已归档 {archived_count} 条对话日志")
    
    main_conn.close()
    archive_conn.close()

def archive_old_viewpoints(days=365):
    """归档旧观点（可选，默认1年）"""
    if not MAIN_DB.exists() or not ARCHIVE_DB.exists():
        print("数据库不存在，请先初始化数据库")
        return
    
    main_conn = duckdb.connect(str(MAIN_DB))
    archive_conn = duckdb.connect(str(ARCHIVE_DB))
    
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    archived_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"归档 {days} 天前的De.观点（截止日期: {cutoff_date}）...")
    
    # 查询需要归档的数据
    result = main_conn.execute('''
        SELECT * FROM de_viewpoints 
        WHERE timestamp < ? AND is_archived = 0
    ''', (cutoff_date,)).fetchall()
    
    if not result:
        print("没有需要归档的数据")
        main_conn.close()
        archive_conn.close()
        return
    
    print(f"找到 {len(result)} 条需要归档的数据")
    
    # 插入到归档数据库
    archived_count = 0
    for row in result:
        try:
            archive_conn.execute('''
                INSERT INTO de_viewpoints_archive 
                (id, content, timestamp, source, category, tags, btc_price, 
                 created_at, updated_at, archived_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row[0], row[1], row[2], row[3], row[4], row[5], row[6],
                row[7], row[8], archived_at
            ))
            archived_count += 1
        except Exception as e:
            print(f"归档失败 (ID: {row[0]}): {e}")
    
    archive_conn.commit()
    
    # 从主数据库标记为已归档（不删除，因为观点需要用于学习）
    main_conn.execute('''
        UPDATE de_viewpoints 
        SET is_archived = 1 
        WHERE timestamp < ? AND is_archived = 0
    ''', (cutoff_date,))
    
    main_conn.commit()
    
    print(f"✅ 已归档 {archived_count} 条De.观点")
    
    main_conn.close()
    archive_conn.close()

def main():
    """主函数"""
    import sys
    
    print("=" * 80)
    print("归档旧数据")
    print("=" * 80)
    print()
    
    # 默认归档90天前的对话日志
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    
    # 归档对话日志
    archive_conversation_logs(days)
    
    print()
    
    # 可选：归档1年以上的观点（如果需要）
    if len(sys.argv) > 2 and sys.argv[2] == '--archive-viewpoints':
        archive_old_viewpoints(365)
    
    print()
    print("=" * 80)
    print("归档完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()

