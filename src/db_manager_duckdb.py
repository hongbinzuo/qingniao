#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB数据库管理模块
高性能、无需服务器的数据库方案
"""

import duckdb
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_DIR = Path(__file__).parent / "data"
DB_FILE = DB_DIR / "qingniao_main.duckdb"  # 使用主数据库

class DuckDBManager:
    """DuckDB数据库管理器"""
    
    def __init__(self, db_file=None):
        self.db_file = db_file or DB_FILE
        self._ensure_db_exists()
        self.conn = None
    
    def _ensure_db_exists(self):
        """确保数据库文件存在"""
        DB_DIR.mkdir(exist_ok=True)
        if not self.db_file.exists():
            self._init_database()
    
    def _get_connection(self):
        """获取数据库连接"""
        if self.conn is None:
            self.conn = duckdb.connect(str(self.db_file))
        return self.conn
    
    def _init_database(self):
        """初始化数据库"""
        conn = self._get_connection()
        
        # 创建De.观点表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS de_viewpoints (
                id INTEGER PRIMARY KEY,
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
        conn.execute('''
            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY,
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
        conn.execute('CREATE INDEX IF NOT EXISTS idx_de_viewpoints_timestamp ON de_viewpoints(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_de_viewpoints_source ON de_viewpoints(source)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_conversation_logs_timestamp ON conversation_logs(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_conversation_logs_de_marker ON conversation_logs(has_de_marker)')
        
        conn.commit()
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    # ========== De.观点操作 ==========
    
    def add_de_viewpoint(self, content: str, timestamp: str = None, 
                        source: str = 'manual', category: str = None, 
                        tags: List[str] = None, btc_price: float = None) -> int:
        """添加De.观点"""
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tags_str = json.dumps(tags) if tags else None
        
        conn = self._get_connection()
        
        # 获取下一个ID
        max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM de_viewpoints').fetchone()
        next_id = (max_id_result[0] if max_id_result else 0) + 1
        
        conn.execute('''
            INSERT INTO de_viewpoints 
            (id, content, timestamp, source, category, tags, btc_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (next_id, content, timestamp, source, category, tags_str, btc_price, created_at))
        
        conn.commit()
        return next_id
    
    def get_de_viewpoints(self, limit: int = None, start_date: str = None, 
                          end_date: str = None, source: str = None) -> List[Dict]:
        """获取De.观点列表"""
        conn = self._get_connection()
        
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
        
        result = conn.execute(query, params).fetchall()
        
        viewpoints = []
        for row in result:
            vp = {
                'id': row[0],
                'content': row[1],
                'timestamp': row[2],
                'source': row[3],
                'category': row[4],
                'tags': json.loads(row[5]) if row[5] else [],
                'created_at': row[6],
                'updated_at': row[7]
            }
            viewpoints.append(vp)
        
        return viewpoints
    
    def search_de_viewpoints(self, keyword: str, limit: int = 50) -> List[Dict]:
        """搜索De.观点"""
        conn = self._get_connection()
        
        result = conn.execute('''
            SELECT * FROM de_viewpoints 
            WHERE content LIKE ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (f'%{keyword}%', limit)).fetchall()
        
        viewpoints = []
        for row in result:
            vp = {
                'id': row[0],
                'content': row[1],
                'timestamp': row[2],
                'source': row[3],
                'category': row[4],
                'tags': json.loads(row[5]) if row[5] else [],
                'created_at': row[6],
                'updated_at': row[7]
            }
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
        
        # 获取下一个ID
        max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM conversation_logs').fetchone()
        next_id = (max_id_result[0] if max_id_result else 0) + 1
        
        conn.execute('''
            INSERT INTO conversation_logs 
            (id, session_id, user_message, assistant_message, timestamp, 
             has_de_marker, de_content, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (next_id, session_id, user_message, assistant_message, timestamp,
              has_de_marker, de_content, created_at))
        
        conn.commit()
        return next_id
    
    def get_conversation_logs(self, limit: int = None, 
                              start_date: str = None, 
                              end_date: str = None,
                              has_de_marker: bool = None) -> List[Dict]:
        """获取对话日志"""
        conn = self._get_connection()
        
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
        
        result = conn.execute(query, params).fetchall()
        
        logs = []
        for row in result:
            log = {
                'id': row[0],
                'session_id': row[1],
                'user_message': row[2],
                'assistant_message': row[3],
                'timestamp': row[4],
                'has_de_marker': bool(row[5]),
                'de_content': row[6],
                'created_at': row[7]
            }
            logs.append(log)
        
        return logs
    
    def cleanup_old_logs(self, days: int = 90):
        """清理旧日志（保留指定天数）"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        conn = self._get_connection()
        result = conn.execute('''
            DELETE FROM conversation_logs 
            WHERE timestamp < ?
        ''', (cutoff_date,))
        
        deleted_count = result.rowcount if hasattr(result, 'rowcount') else 0
        conn.commit()
        
        return deleted_count
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        conn = self._get_connection()
        
        stats = {}
        
        # De.观点统计
        result = conn.execute('SELECT COUNT(*) as count FROM de_viewpoints').fetchone()
        stats['total_viewpoints'] = result[0] if result else 0
        
        result = conn.execute('SELECT COUNT(*) as count FROM de_viewpoints WHERE source = ?', ('manual',)).fetchone()
        stats['manual_viewpoints'] = result[0] if result else 0
        
        # 对话日志统计
        result = conn.execute('SELECT COUNT(*) as count FROM conversation_logs').fetchone()
        stats['total_logs'] = result[0] if result else 0
        
        result = conn.execute('SELECT COUNT(*) as count FROM conversation_logs WHERE has_de_marker = 1').fetchone()
        stats['logs_with_de'] = result[0] if result else 0
        
        # 最近30天的统计
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        result = conn.execute('SELECT COUNT(*) as count FROM conversation_logs WHERE timestamp >= ?', (thirty_days_ago,)).fetchone()
        stats['logs_last_30_days'] = result[0] if result else 0
        
        return stats

