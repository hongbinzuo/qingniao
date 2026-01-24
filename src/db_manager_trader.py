#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 数据库管理器
用于 Abu 系统，支持多进程并发
"""

import os
import sys
import psycopg2
import re
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import cursor as PGCursor
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

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

_PLACEHOLDER_RE = re.compile(r'\?')


def _to_psycopg2_placeholders(sql: str) -> str:
    """将DuckDB/SQLite风格的?占位符转换为psycopg2的%s"""
    if '?' not in sql:
        return sql
    return _PLACEHOLDER_RE.sub('%s', sql)


class _CompatCursor:
    """DuckDB风格的cursor包装器，支持execute().fetch*链式调用"""

    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, query: str, params: Optional[object] = None):
        sql = _to_psycopg2_placeholders(query)
        if params is None:
            self._cursor.execute(sql)
        else:
            self._cursor.execute(sql, params)
        return self

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    @property
    def description(self):
        return self._cursor.description

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()

    def __iter__(self):
        return iter(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _CompatConnection:
    """DuckDB风格连接包装器，提供execute/commit/rollback并自动归还连接池"""

    def __init__(self, conn, manager):
        self._conn = conn
        self._manager = manager
        self._closed = False

    def execute(self, query: str, params: Optional[object] = None):
        cur = self._conn.cursor(cursor_factory=PGCursor)
        return _CompatCursor(cur).execute(query, params)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def cursor(self, *args, **kwargs):
        return self._conn.cursor(*args, **kwargs)

    def close(self):
        if not self._closed:
            self._manager.return_connection(self._conn)
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self._conn, name)

class PostgresDBManager:
    """PostgreSQL 数据库管理器"""
    
    # 连接池（类级别共享）
    _connection_pool = None
    
    def __init__(self, trader_id='abu'):
        self.trader_id = trader_id
        self._init_connection_pool()
    
    @classmethod
    def _init_connection_pool(cls):
        """初始化连接池（只初始化一次）"""
        if cls._connection_pool is None:
            try:
                cls._connection_pool = psycopg2.pool.ThreadedConnectionPool(
                    minconn=int(os.getenv('PG_POOL_MIN_SIZE', 2)),
                    maxconn=int(os.getenv('PG_POOL_MAX_SIZE', 10)),
                    host=os.getenv('PG_HOST', 'localhost'),
                    port=int(os.getenv('PG_PORT', 5432)),
                    database=os.getenv('PG_DATABASE', 'qingniao_abu'),
                    user=os.getenv('PG_USER', 'abu_user'),
                    password=os.getenv('PG_PASSWORD', ''),
                    cursor_factory=RealDictCursor
                )
                print(f"[INFO] PostgreSQL 连接池已初始化", file=sys.stderr)
            except Exception as e:
                print(f"[ERROR] 无法初始化 PostgreSQL 连接池: {e}", file=sys.stderr)
                raise
    
    def get_connection(self):
        """从连接池获取连接"""
        if self._connection_pool is None:
            raise RuntimeError("连接池未初始化")
        return self._connection_pool.getconn()
    
    def _get_connection(self, read_only=False, **kwargs):
        """兼容旧代码的方法（DuckDB 风格）
        
        注意：返回的是连接对象，使用完后需要调用 return_connection() 归还
        PostgreSQL 的连接不能直接 execute()，需要通过 cursor
        """
        # PostgreSQL 连接池不区分只读/读写，都从池中获取
        return _CompatConnection(self.get_connection(), self)
    
    def return_connection(self, conn):
        """归还连接到连接池"""
        if self._connection_pool:
            self._connection_pool.putconn(conn)
    
    def close_all_connections(self):
        """关闭所有连接"""
        if self._connection_pool:
            self._connection_pool.closeall()
            PostgresDBManager._connection_pool = None

    def close(self):
        """兼容旧代码的关闭方法"""
        self.close_all_connections()
    
    # ========== 交易信号操作 ==========
    
    def add_trading_signal(self, signal_data: Dict) -> int:
        """添加交易信号"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 准备数据，设置默认值
            data = {
                'signal_time': signal_data.get('signal_time'),
                'timeframe': signal_data.get('timeframe'),
                'symbol': signal_data.get('symbol'),
                'signal_type': signal_data.get('signal_type'),
                'entry_price': signal_data.get('entry_price'),
                'stop_loss': signal_data.get('stop_loss'),
                'take_profit_1': signal_data.get('take_profit_1'),
                'take_profit_2': signal_data.get('take_profit_2'),
                'entry_model': signal_data.get('entry_model'),
                'strength': signal_data.get('strength'),
                'risk_reward_ratio': signal_data.get('risk_reward_ratio'),
                'volatility_level': signal_data.get('volatility_level'),
                'system_name': signal_data.get('system_name', 'abu'),
                'score': signal_data.get('score'),
                'notes': signal_data.get('notes'),
                'status': signal_data.get('status', 'pending'),
                'created_at': signal_data.get('created_at', datetime.now())
            }
            
            cursor.execute('''
                INSERT INTO trading_signals (
                    signal_time, timeframe, symbol, signal_type, entry_price,
                    stop_loss, take_profit_1, take_profit_2, entry_model,
                    strength, risk_reward_ratio, volatility_level, system_name,
                    score, notes, status, created_at
                ) VALUES (
                    %(signal_time)s, %(timeframe)s, %(symbol)s, %(signal_type)s, %(entry_price)s,
                    %(stop_loss)s, %(take_profit_1)s, %(take_profit_2)s, %(entry_model)s,
                    %(strength)s, %(risk_reward_ratio)s, %(volatility_level)s, %(system_name)s,
                    %(score)s, %(notes)s, %(status)s, %(created_at)s
                ) RETURNING id
            ''', data)
            
            signal_id = cursor.fetchone()['id']
            conn.commit()
            return signal_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[ERROR] 添加交易信号失败: {e}", file=sys.stderr)
            raise
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def update_signal_status(self, signal_id: int, status: str, **kwargs):
        """更新信号状态"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 构建更新语句
            update_fields = ['status = %s', 'updated_at = %s']
            values = [status, datetime.now()]
            
            # 动态添加其他字段
            field_mapping = {
                'entry_time': 'entry_time',
                'exit_time': 'exit_time',
                'exit_price': 'exit_price',
                'exit_reason': 'exit_reason',
                'pnl_pct': 'pnl_pct',
                'breakeven_stop_set': 'breakeven_stop_set',
                'quick_tp_reached': 'quick_tp_reached',
                'last_check_time': 'last_check_time',
                'check_count': 'check_count',
                'entry_price_actual': 'entry_price_actual'
            }
            
            for key, db_field in field_mapping.items():
                if key in kwargs and kwargs[key] is not None:
                    update_fields.append(f'{db_field} = %s')
                    values.append(kwargs[key])
            
            values.append(signal_id)
            
            query = f'''
                UPDATE trading_signals 
                SET {', '.join(update_fields)}
                WHERE id = %s
            '''
            
            cursor.execute(query, values)
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[ERROR] 更新信号状态失败: {e}", file=sys.stderr)
            raise
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def get_active_signals(self, hours: int = 24) -> List[Dict]:
        """获取活跃信号"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            cursor.execute('''
                SELECT *
                FROM trading_signals
                WHERE status IN ('pending', 'active', 'partial_tp')
                AND created_at >= %s
                ORDER BY created_at DESC
            ''', (cutoff_time,))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"[ERROR] 获取活跃信号失败: {e}", file=sys.stderr)
            return []
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def get_trading_signals(self, 
                           timeframe: Optional[str] = None,
                           symbol: Optional[str] = None,
                           status: Optional[str] = None,
                           system_name: Optional[str] = None,
                           limit: int = 100,
                           days: int = 7) -> List[Dict]:
        """查询交易信号"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            conditions = []
            values = []
            
            cutoff_time = datetime.now() - timedelta(days=days)
            conditions.append('created_at >= %s')
            values.append(cutoff_time)
            
            if timeframe:
                conditions.append('timeframe = %s')
                values.append(timeframe)
            
            if symbol:
                conditions.append('symbol = %s')
                values.append(symbol)
            
            if status:
                conditions.append('status = %s')
                values.append(status)
            
            if system_name:
                conditions.append('system_name = %s')
                values.append(system_name)
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            values.append(limit)
            
            query = f'''
                SELECT *
                FROM trading_signals
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            '''
            
            cursor.execute(query, values)
            results = cursor.fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            print(f"[ERROR] 查询交易信号失败: {e}", file=sys.stderr)
            return []
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)
    
    def add_signal_evaluation(self, evaluation_data: Dict) -> int:
        """添加信号评估"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            data = {
                'signal_id': evaluation_data.get('signal_id'),
                'evaluation_time': evaluation_data.get('evaluation_time', datetime.now()),
                'result': evaluation_data.get('result'),
                'actual_entry_price': evaluation_data.get('actual_entry_price'),
                'actual_exit_price': evaluation_data.get('actual_exit_price'),
                'actual_profit_pct': evaluation_data.get('actual_profit_pct'),
                'actual_profit_usdt': evaluation_data.get('actual_profit_usdt'),
                'stop_loss_hit': evaluation_data.get('stop_loss_hit', False),
                'take_profit_1_hit': evaluation_data.get('take_profit_1_hit', False),
                'take_profit_2_hit': evaluation_data.get('take_profit_2_hit', False),
                'missed': evaluation_data.get('missed', False),
                'notes': evaluation_data.get('notes'),
                'created_at': evaluation_data.get('created_at', datetime.now())
            }
            
            cursor.execute('''
                INSERT INTO signal_evaluations (
                    signal_id, evaluation_time, result, actual_entry_price,
                    actual_exit_price, actual_profit_pct, actual_profit_usdt,
                    stop_loss_hit, take_profit_1_hit, take_profit_2_hit,
                    missed, notes, created_at
                ) VALUES (
                    %(signal_id)s, %(evaluation_time)s, %(result)s, %(actual_entry_price)s,
                    %(actual_exit_price)s, %(actual_profit_pct)s, %(actual_profit_usdt)s,
                    %(stop_loss_hit)s, %(take_profit_1_hit)s, %(take_profit_2_hit)s,
                    %(missed)s, %(notes)s, %(created_at)s
                ) RETURNING id
            ''', data)
            
            eval_id = cursor.fetchone()['id']
            conn.commit()
            return eval_id
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[ERROR] 添加信号评估失败: {e}", file=sys.stderr)
            raise
        finally:
            if conn:
                cursor.close()
                self.return_connection(conn)

# 向后兼容：创建别名
TraderDBManager = PostgresDBManager

if __name__ == '__main__':
    # 测试连接
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("测试 PostgreSQL 连接...")
    try:
        db = PostgresDBManager('abu')
        print("[OK] 连接成功！")
        db.close_all_connections()
    except Exception as e:
        print(f"[ERROR] 连接失败: {e}")
