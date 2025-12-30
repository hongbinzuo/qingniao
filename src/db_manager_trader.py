#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易员数据库管理模块
支持多交易员分库
"""

import duckdb
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

DB_DIR = Path(__file__).parent / "data"

class TraderDBManager:
    """交易员数据库管理器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db_file = DB_DIR / f"qingniao_{trader_id}.duckdb"
        self.conn = None
    
    def _get_connection(self):
        """获取数据库连接（支持连接复用）"""
        if self.conn is None:
            if not self.db_file.exists():
                raise FileNotFoundError(f"数据库文件不存在: {self.db_file}")
            try:
                self.conn = duckdb.connect(str(self.db_file))
            except Exception as e:
                # 如果连接失败，尝试等待后重试
                import time
                time.sleep(0.1)
                try:
                    self.conn = duckdb.connect(str(self.db_file))
                except:
                    raise e
        return self.conn
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    # ========== 对话记录操作 ==========
    
    def add_conversation(self, timestamp: str, user_message: str = None, 
                        trader_message: str = None, source: str = 'discord',
                        btc_price: float = None, extracted_content: str = None,
                        user_evaluation: str = None, evaluation_keywords: str = None) -> int:
        """添加对话记录"""
        conn = self._get_connection()
        
        max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM conversations').fetchone()
        next_id = (max_id_result[0] if max_id_result else 0) + 1
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        has_trading_info = 1 if extracted_content else 0
        
        # 检查字段是否存在
        try:
            columns = conn.execute("PRAGMA table_info(conversations)").fetchall()
            column_names = [col[1] for col in columns]
            
            # 如果字段不存在，尝试添加（静默失败，不影响主流程）
            if 'user_evaluation' not in column_names:
                try:
                    conn.execute('ALTER TABLE conversations ADD COLUMN user_evaluation TEXT')
                except:
                    pass
            
            if 'evaluation_keywords' not in column_names:
                try:
                    conn.execute('ALTER TABLE conversations ADD COLUMN evaluation_keywords TEXT')
                except:
                    pass
            
            # 重新获取列名
            columns = conn.execute("PRAGMA table_info(conversations)").fetchall()
            column_names = [col[1] for col in columns]
            
            # 构建INSERT语句
            if 'user_evaluation' in column_names and 'evaluation_keywords' in column_names:
                conn.execute('''
                    INSERT INTO conversations 
                    (id, timestamp, user_message, trader_message, source, has_trading_info, 
                     extracted_content, btc_price, user_evaluation, evaluation_keywords, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (next_id, timestamp, user_message, trader_message, source, 
                      has_trading_info, extracted_content, btc_price, 
                      user_evaluation, evaluation_keywords, created_at))
            elif 'user_evaluation' in column_names:
                conn.execute('''
                    INSERT INTO conversations 
                    (id, timestamp, user_message, trader_message, source, has_trading_info, 
                     extracted_content, btc_price, user_evaluation, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (next_id, timestamp, user_message, trader_message, source, 
                      has_trading_info, extracted_content, btc_price, 
                      user_evaluation, created_at))
            else:
                # 使用原有字段
                conn.execute('''
                    INSERT INTO conversations 
                    (id, timestamp, user_message, trader_message, source, has_trading_info, 
                     extracted_content, btc_price, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (next_id, timestamp, user_message, trader_message, source, 
                      has_trading_info, extracted_content, btc_price, created_at))
        except Exception as e:
            # 如果出错，使用原有字段
            conn.execute('''
                INSERT INTO conversations 
                (id, timestamp, user_message, trader_message, source, has_trading_info, 
                 extracted_content, btc_price, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (next_id, timestamp, user_message, trader_message, source, 
                  has_trading_info, extracted_content, btc_price, created_at))
        
        conn.commit()
        return next_id
    
    # ========== 交易记录操作 ==========
    
    def add_trade_record(self, timestamp: str, symbol: str = 'BTC/USDT',
                        direction: str = None, leverage: int = None,
                        entry_price: float = None, exit_price: float = None,
                        profit_pct: float = None, profit_usdt: float = None,
                        strategy: str = None, screenshot_path: str = None,
                        text_content: str = None, source: str = 'manual') -> int:
        """添加交易记录"""
        conn = self._get_connection()
        
        max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM trade_records').fetchone()
        next_id = (max_id_result[0] if max_id_result else 0) + 1
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn.execute('''
            INSERT INTO trade_records 
            (id, timestamp, symbol, direction, leverage, entry_price, exit_price,
             profit_pct, profit_usdt, strategy, screenshot_path, text_content, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (next_id, timestamp, symbol, direction, leverage, entry_price, exit_price,
              profit_pct, profit_usdt, strategy, screenshot_path, text_content, source, created_at))
        
        conn.commit()
        return next_id
    
    # ========== 交易观点操作 ==========
    
    def add_viewpoint(self, content: str, timestamp: str = None,
                     source: str = 'conversation', category: str = None,
                     tags: List[str] = None, btc_price: float = None,
                     related_trade_id: int = None, related_conversation_id: int = None) -> int:
        """添加交易观点"""
        if not timestamp:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn = self._get_connection()
        
        max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM trader_viewpoints').fetchone()
        next_id = (max_id_result[0] if max_id_result else 0) + 1
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tags_str = json.dumps(tags) if tags else None
        
        conn.execute('''
            INSERT INTO trader_viewpoints 
            (id, content, timestamp, source, category, tags, btc_price,
             related_trade_id, related_conversation_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (next_id, content, timestamp, source, category, tags_str, btc_price,
              related_trade_id, related_conversation_id, created_at))
        
        conn.commit()
        return next_id
    
    # ========== 交易信号操作 ==========
    
    def add_trading_signal(self, signal_time: str, timeframe: str = None,
                          signal_type: str = None, entry_price: float = None,
                          stop_loss: float = None, take_profit_1: float = None,
                          take_profit_2: float = None, entry_model: str = None,
                          strength: str = None, risk_reward_ratio: float = None,
                          volatility_level: str = None, system_name: str = None) -> int:
        """添加交易信号"""
        conn = self._get_connection()
        
        max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM trading_signals').fetchone()
        next_id = (max_id_result[0] if max_id_result else 0) + 1
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn.execute('''
            INSERT INTO trading_signals 
            (id, signal_time, timeframe, signal_type, entry_price, stop_loss,
             take_profit_1, take_profit_2, entry_model, strength, risk_reward_ratio,
             volatility_level, system_name, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (next_id, signal_time, timeframe, signal_type, entry_price, stop_loss,
              take_profit_1, take_profit_2, entry_model, strength, risk_reward_ratio,
              volatility_level, system_name, 'pending', created_at))
        
        conn.commit()
        return next_id
    
    # ========== 信号评估操作 ==========
    
    def add_signal_evaluation(self, signal_id: int, evaluation_time: str,
                             result: str = None, actual_entry_price: float = None,
                             actual_exit_price: float = None, actual_profit_pct: float = None,
                             actual_profit_usdt: float = None, stop_loss_hit: int = 0,
                             take_profit_1_hit: int = 0, take_profit_2_hit: int = 0,
                             missed: int = 0, notes: str = None) -> int:
        """添加信号评估"""
        conn = self._get_connection()
        
        max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM signal_evaluations').fetchone()
        next_id = (max_id_result[0] if max_id_result else 0) + 1
        
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn.execute('''
            INSERT INTO signal_evaluations 
            (id, signal_id, evaluation_time, result, actual_entry_price, actual_exit_price,
             actual_profit_pct, actual_profit_usdt, stop_loss_hit, take_profit_1_hit,
             take_profit_2_hit, missed, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (next_id, signal_id, evaluation_time, result, actual_entry_price, actual_exit_price,
              actual_profit_pct, actual_profit_usdt, stop_loss_hit, take_profit_1_hit,
              take_profit_2_hit, missed, notes, created_at))
        
        # 更新信号状态
        conn.execute('''
            UPDATE trading_signals 
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (result, created_at, signal_id))
        
        conn.commit()
        return next_id
    
    # ========== 查询方法 ==========
    
    def get_viewpoints(self, limit: int = None, start_date: str = None,
                      end_date: str = None, category: str = None) -> List[Dict]:
        """获取交易观点"""
        conn = self._get_connection()
        
        query = 'SELECT * FROM trader_viewpoints WHERE 1=1'
        params = []
        
        if start_date:
            query += ' AND timestamp >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND timestamp <= ?'
            params.append(end_date)
        if category:
            query += ' AND category = ?'
            params.append(category)
        
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
                'btc_price': row[6],
                'related_trade_id': row[7],
                'related_conversation_id': row[8],
                'created_at': row[9]
            }
            viewpoints.append(vp)
        
        return viewpoints
    
    def get_trading_signals(self, limit: int = None, status: str = None,
                           start_date: str = None, end_date: str = None) -> List[Dict]:
        """获取交易信号"""
        conn = self._get_connection()
        
        query = 'SELECT * FROM trading_signals WHERE 1=1'
        params = []
        
        if status:
            if isinstance(status, list):
                placeholders = ','.join(['?'] * len(status))
                query += f' AND status IN ({placeholders})'
                params.extend(status)
            else:
                query += ' AND status = ?'
                params.append(status)
        if start_date:
            query += ' AND signal_time >= ?'
            params.append(start_date)
        if end_date:
            query += ' AND signal_time <= ?'
            params.append(end_date)
        
        query += ' ORDER BY signal_time DESC'
        if limit:
            query += ' LIMIT ?'
            params.append(limit)
        
        result = conn.execute(query, params).fetchall()
        
        signals = []
        for row in result:
            signal = {
                'id': row[0],
                'signal_time': row[1],
                'timeframe': row[2],
                'signal_type': row[3],
                'entry_price': row[4],
                'stop_loss': row[5],
                'take_profit_1': row[6],
                'take_profit_2': row[7],
                'entry_model': row[8],
                'strength': row[9],
                'risk_reward_ratio': row[10],
                'volatility_level': row[11],
                'system_name': row[12],
                'status': row[13],
                'created_at': row[14]
            }
            signals.append(signal)
        
        return signals
    
    def get_trading_signals_count(self, status: str = None) -> int:
        """获取交易信号数量"""
        conn = self._get_connection()
        if status:
            result = conn.execute('SELECT COUNT(*) FROM trading_signals WHERE status = ?', [status]).fetchone()
        else:
            result = conn.execute('SELECT COUNT(*) FROM trading_signals').fetchone()
        return result[0] if result else 0
    
    def get_signal_evaluations_count(self) -> int:
        """获取信号评估数量"""
        conn = self._get_connection()
        result = conn.execute('SELECT COUNT(*) FROM signal_evaluations').fetchone()
        return result[0] if result else 0
    
    def get_signal_evaluation(self, signal_id: int) -> Optional[Dict]:
        """获取信号评估"""
        conn = self._get_connection()
        result = conn.execute('''
            SELECT * FROM signal_evaluations WHERE signal_id = ?
        ''', [signal_id]).fetchone()
        
        if not result:
            return None
        
        return {
            'id': result[0],
            'signal_id': result[1],
            'evaluation_time': result[2],
            'result': result[3],
            'actual_entry_price': result[4],
            'actual_exit_price': result[5],
            'actual_profit_pct': result[6],
            'actual_profit_usdt': result[7],
            'stop_loss_hit': result[8],
            'take_profit_1_hit': result[9],
            'take_profit_2_hit': result[10],
            'missed': result[11],
            'notes': result[12],
            'created_at': result[13]
        }
    
    def update_signal_status(self, signal_id: int, status: str):
        """更新信号状态"""
        conn = self._get_connection()
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute('''
            UPDATE trading_signals 
            SET status = ?, updated_at = ?
            WHERE id = ?
        ''', (status, updated_at, signal_id))
        conn.commit()

    