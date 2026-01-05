#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
规则性能追踪模块
追踪每个规则的历史表现，为权重优化做准备
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager


class RulePerformanceTracker:
    """规则性能追踪器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.stats_cache = None
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """确保表存在"""
        try:
            conn = self.db._get_connection()
            conn.execute('SELECT 1 FROM rule_performance LIMIT 1')
        except:
            self._create_table()
    
    def _create_table(self):
        """创建规则性能表"""
        try:
            conn = self.db._get_connection()
            conn.execute('''
                CREATE TABLE IF NOT EXISTS rule_performance (
                    id INTEGER PRIMARY KEY,
                    signal_id INTEGER,
                    rule_name TEXT,
                    result TEXT,
                    profit_pct REAL,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rule_performance_rule_name ON rule_performance(rule_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_rule_performance_signal_id ON rule_performance(signal_id)')
            conn.commit()
        except Exception as e:
            print(f"创建表失败: {e}", file=sys.stderr)
    
    def track_signal(self, signal_id: int, rule_name: str, evaluation_result: Dict):
        """追踪信号结果"""
        try:
            conn = self.db._get_connection()
            
            # 检查是否已存在记录
            existing = conn.execute(
                'SELECT id FROM rule_performance WHERE signal_id = ? AND rule_name = ?',
                [signal_id, rule_name]
            ).fetchone()
            
            if existing:
                # 更新记录
                conn.execute(
                    'UPDATE rule_performance SET result = ?, profit_pct = ?, updated_at = ? WHERE signal_id = ? AND rule_name = ?',
                    [
                        evaluation_result.get('result', 'unknown'),
                        evaluation_result.get('profit_pct', 0),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        signal_id,
                        rule_name
                    ]
                )
            else:
                # 插入新记录
                max_id_result = conn.execute('SELECT COALESCE(MAX(id), 0) FROM rule_performance').fetchone()
                next_id = (max_id_result[0] if max_id_result else 0) + 1
                
                conn.execute(
                    'INSERT INTO rule_performance (id, signal_id, rule_name, result, profit_pct, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    [
                        next_id,
                        signal_id,
                        rule_name,
                        evaluation_result.get('result', 'unknown'),
                        evaluation_result.get('profit_pct', 0),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ]
                )
            
            conn.commit()
            
        except Exception as e:
            print(f"追踪信号失败: {e}", file=sys.stderr)
    
    def get_rule_stats(self, rule_name: str = None, days: int = 30) -> Dict:
        """获取规则统计信息"""
        try:
            conn = self.db._get_connection()
            self._ensure_table_exists()
            
            from datetime import timedelta
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
            
            if rule_name:
                query = '''
                    SELECT 
                        rule_name,
                        COUNT(*) as total_signals,
                        SUM(CASE WHEN result = 'full_tp' THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN result = 'stopped' THEN 1 ELSE 0 END) as stopped_count,
                        AVG(profit_pct) as avg_profit_pct,
                        SUM(profit_pct) as total_profit_pct
                    FROM rule_performance
                    WHERE rule_name = ? AND created_at >= ?
                    GROUP BY rule_name
                '''
                rows = conn.execute(query, [rule_name, cutoff_date]).fetchall()
            else:
                query = '''
                    SELECT 
                        rule_name,
                        COUNT(*) as total_signals,
                        SUM(CASE WHEN result = 'full_tp' THEN 1 ELSE 0 END) as success_count,
                        SUM(CASE WHEN result = 'stopped' THEN 1 ELSE 0 END) as stopped_count,
                        AVG(profit_pct) as avg_profit_pct,
                        SUM(profit_pct) as total_profit_pct
                    FROM rule_performance
                    WHERE created_at >= ?
                    GROUP BY rule_name
                '''
                rows = conn.execute(query, [cutoff_date]).fetchall()
            
            stats = {}
            for row in rows:
                if isinstance(row, tuple):
                    rule_name = row[0]
                    total = row[1] if len(row) > 1 else 0
                    success = row[2] if len(row) > 2 else 0
                    stopped = row[3] if len(row) > 3 else 0
                    avg_profit = row[4] if len(row) > 4 else 0
                    total_profit = row[5] if len(row) > 5 else 0
                else:
                    rule_name = row.get('rule_name')
                    total = row.get('total_signals', 0)
                    success = row.get('success_count', 0)
                    stopped = row.get('stopped_count', 0)
                    avg_profit = row.get('avg_profit_pct', 0)
                    total_profit = row.get('total_profit_pct', 0)
                
                win_rate = (success / total * 100) if total > 0 else 0
                
                stats[rule_name] = {
                    'total_signals': total,
                    'success_count': success,
                    'stopped_count': stopped,
                    'win_rate': win_rate,
                    'avg_profit_pct': avg_profit,
                    'total_profit_pct': total_profit
                }
            
            return stats
            
        except Exception as e:
            print(f"获取规则统计失败: {e}", file=sys.stderr)
            return {}
    
    def close(self):
        """关闭连接"""
        self.db.close()



