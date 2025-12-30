#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL数据库管理模块
需要MySQL服务器支持
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import mysql.connector
from mysql.connector import Error

class MySQLManager:
    """MySQL数据库管理器"""
    
    def __init__(self, host='localhost', port=3306, user='root', 
                 password='', database='qingniao', charset='utf8mb4'):
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'charset': charset
        }
        self._ensure_database_exists()
        self._init_tables()
    
    def _ensure_database_exists(self):
        """确保数据库存在"""
        try:
            # 先连接到MySQL服务器（不指定数据库）
            temp_config = self.config.copy()
            temp_config.pop('database', None)
            conn = mysql.connector.connect(**temp_config)
            cursor = conn.cursor()
            
            # 创建数据库（如果不存在）
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.commit()
            cursor.close()
            conn.close()
        except Error as e:
            print(f"数据库连接失败: {e}")
            raise
    
    def _get_connection(self):
        """获取数据库连接"""
        try:
            return mysql.connector.connect(**self.config)
        except Error as e:
            print(f"数据库连接失败: {e}")
            raise
    
    def _init_tables(self):
        """初始化数据表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 创建De.观点表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS de_viewpoints (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    content TEXT NOT NULL,
                    timestamp VARCHAR(50) NOT NULL,
                    source VARCHAR(50) DEFAULT 'manual',
                    category VARCHAR(50),
                    tags TEXT,
                    created_at VARCHAR(50) NOT NULL,
                    updated_at VARCHAR(50),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_source (source)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            # 创建对话日志表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(100),
                    user_message TEXT,
                    assistant_message TEXT,
                    timestamp VARCHAR(50) NOT NULL,
                    has_de_marker TINYINT(1) DEFAULT 0,
                    de_content TEXT,
                    created_at VARCHAR(50) NOT NULL,
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_de_marker (has_de_marker)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            ''')
            
            conn.commit()
        except Error as e:
            print(f"创建表失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    # ========== De.观点操作 ==========
    
    def add_de_viewpoint(self, content: str, timestamp: str = None, 
                        source: str = 'manual', category: str = None, 
                        tags: List[str] = None) -> int:
        """添加De.观点"""
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tags_str = json.dumps(tags, ensure_ascii=False) if tags else None
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO de_viewpoints 
                (content, timestamp, source, category, tags, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (content, timestamp, source, category, tags_str, created_at))
            
            viewpoint_id = cursor.lastrowid
            conn.commit()
            return viewpoint_id
        except Error as e:
            conn.rollback()
            print(f"添加观点失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_de_viewpoints(self, limit: int = None, start_date: str = None, 
                          end_date: str = None, source: str = None) -> List[Dict]:
        """获取De.观点列表"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = 'SELECT * FROM de_viewpoints WHERE 1=1'
            params = []
            
            if start_date:
                query += ' AND timestamp >= %s'
                params.append(start_date)
            
            if end_date:
                query += ' AND timestamp <= %s'
                params.append(end_date)
            
            if source:
                query += ' AND source = %s'
                params.append(source)
            
            query += ' ORDER BY timestamp DESC'
            
            if limit:
                query += ' LIMIT %s'
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
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
        finally:
            cursor.close()
            conn.close()
    
    def search_de_viewpoints(self, keyword: str, limit: int = 50) -> List[Dict]:
        """搜索De.观点"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute('''
                SELECT * FROM de_viewpoints 
                WHERE content LIKE %s
                ORDER BY timestamp DESC
                LIMIT %s
            ''', (f'%{keyword}%', limit))
            
            rows = cursor.fetchall()
            
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
        finally:
            cursor.close()
            conn.close()
    
    # ========== 对话日志操作 ==========
    
    def add_conversation_log(self, user_message: str, assistant_message: str,
                            session_id: str = None, de_content: str = None) -> int:
        """添加对话日志"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        created_at = timestamp
        has_de_marker = 1 if de_content else 0
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO conversation_logs 
                (session_id, user_message, assistant_message, timestamp, 
                 has_de_marker, de_content, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (session_id, user_message, assistant_message, timestamp,
                  has_de_marker, de_content, created_at))
            
            log_id = cursor.lastrowid
            conn.commit()
            return log_id
        except Error as e:
            conn.rollback()
            print(f"添加日志失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_conversation_logs(self, limit: int = None, 
                              start_date: str = None, 
                              end_date: str = None,
                              has_de_marker: bool = None) -> List[Dict]:
        """获取对话日志"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            query = 'SELECT * FROM conversation_logs WHERE 1=1'
            params = []
            
            if start_date:
                query += ' AND timestamp >= %s'
                params.append(start_date)
            
            if end_date:
                query += ' AND timestamp <= %s'
                params.append(end_date)
            
            if has_de_marker is not None:
                query += ' AND has_de_marker = %s'
                params.append(1 if has_de_marker else 0)
            
            query += ' ORDER BY timestamp DESC'
            
            if limit:
                query += ' LIMIT %s'
                params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
    
    def cleanup_old_logs(self, days: int = 90):
        """清理旧日志（保留指定天数）"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM conversation_logs 
                WHERE timestamp < %s
            ''', (cutoff_date,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
        except Error as e:
            conn.rollback()
            print(f"清理日志失败: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            stats = {}
            
            cursor.execute('SELECT COUNT(*) as count FROM de_viewpoints')
            stats['total_viewpoints'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM de_viewpoints WHERE source = %s', ('manual',))
            stats['manual_viewpoints'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM conversation_logs')
            stats['total_logs'] = cursor.fetchone()['count']
            
            cursor.execute('SELECT COUNT(*) as count FROM conversation_logs WHERE has_de_marker = 1')
            stats['logs_with_de'] = cursor.fetchone()['count']
            
            thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('SELECT COUNT(*) as count FROM conversation_logs WHERE timestamp >= %s', (thirty_days_ago,))
            stats['logs_last_30_days'] = cursor.fetchone()['count']
            
            return stats
        finally:
            cursor.close()
            conn.close()

