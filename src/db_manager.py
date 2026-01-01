#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理模块
提供De.观点和对话日志的数据库操作
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_DIR = Path(__file__).parent / "data"
DB_FILE = DB_DIR / "qingniao.db"

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_file=None):
        self.db_file = db_file or DB_FILE
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """确保数据库文件存在"""
        if not self.db_file.exists():
            from database_setup import init_database
            init_database()
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_file))
        conn.row_factory = sqlite3.Row
        return conn
    
    # ========== De.观点操作 ==========
    
    def add_de_viewpoint(self, content: str, timestamp: str = None, 
                        source: str = 'manual', category: str = None, 
                        tags: List[str] = None) -> int:
        """添加De.观点"""
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tags_str = json.dumps(tags) if tags else None
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO de_viewpoints 
            (content, timestamp, source, category, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (content, timestamp, source, category, tags_str, created_at))
        
        viewpoint_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return viewpoint_id
    
    def get_de_viewpoints(self, limit: int = None, start_date: str = None, 
                          end_date: str = None, source: str = None) -> List[Dict]:
        """获取De.观点列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM de_viewpoints WHERE 1=1'
        params = []
        
        if start_date:
            query += ' AND timestamp >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND timestamp <= ?'
            params.append(end_date)
        
        if source:
            query += ' AND source = ?'
            params.append(source)
        
        query += ' ORDER BY timestamp DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        viewpoints = []
        for row in rows:
            vp = dict(row)
            if vp.get('tags'):
                try:
                    vp['tags'] = json.loads(vp['tags'])
                except:
                    vp['tags'] = []
            viewpoints.append(vp)
        
        return viewpoints
    
    def search_de_viewpoints(self, keyword: str, limit: int = 50) -> List[Dict]:
        """搜索De.观点"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM de_viewpoints 
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (f'%{keyword}%', limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        viewpoints = []
        for row in rows:
            vp = dict(row)
            if vp.get('tags'):
                try:
                    vp['tags'] = json.loads(vp['tags'])
                except:
                    vp['tags'] = []
            viewpoints.append(vp)
        
        return viewpoints
    
    # ========== 对话日志操作 ==========
    
    def add_conversation_log(self, user_message: str, assistant_message: str,
                            session_id: str = None, de_content: str = None) -> int:
        """添加对话日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        created_at = timestamp
        has_de_marker = 1 if de_content else 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversation_logs 
            (session_id, user_message, assistant_message, timestamp, 
             has_de_marker, de_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, user_message, assistant_message, timestamp,
              has_de_marker, de_content, created_at))
        
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return log_id
    
    def get_conversation_logs(self, limit: int = None, 
                              start_date: str = None, 
                              end_date: str = None,
                              has_de_marker: bool = None) -> List[Dict]:
        """获取对话日志"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM conversation_logs WHERE 1=1'
        params = []
        
        if start_date:
            query += ' AND timestamp >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND timestamp <= ?'
            params.append(end_date)
        
        if has_de_marker is not None:
            query += ' AND has_de_marker = ?'
            params.append(1 if has_de_marker else 0)
        
        query += ' ORDER BY timestamp DESC'
        
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def cleanup_old_logs(self, days: int = 90):
        """清理旧日志（保留指定天数）"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM conversation_logs 
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        # De.观点统计
        cursor.execute('SELECT COUNT(*) as count FROM de_viewpoints')
        stats['total_viewpoints'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM de_viewpoints WHERE source = ?', ('manual',))
        stats['manual_viewpoints'] = cursor.fetchone()['count']
        
        # 对话日志统计
        cursor.execute('SELECT COUNT(*) as count FROM conversation_logs')
        stats['total_logs'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM conversation_logs WHERE has_de_marker = 1')
        stats['logs_with_de'] = cursor.fetchone()['count']
        
        # 最近30天的统计
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('SELECT COUNT(*) as count FROM conversation_logs WHERE timestamp >= ?', (thirty_days_ago,))
        stats['logs_last_30_days'] = cursor.fetchone()['count']
        
        conn.close()
        
        return stats

