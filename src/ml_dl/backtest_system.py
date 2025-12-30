#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测系统
1. 使用历史信号和价格数据回测
2. 计算回测指标（收益率、胜率、最大回撤等）
3. 支持迭代优化
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager
import duckdb


class BacktestSystem:
    """回测系统"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.base_dir = Path(__file__).parent.parent.parent
        
        # 初始化价格数据连接
        self._init_price_data()
        
        # 回测结果
        self.results = {
            'total_signals': 0,
            'completed': 0,
            'stopped': 0,
            'missed': 0,
            'total_profit_pct': 0.0,
            'total_profit_usdt': 0.0,
            'win_rate': 0.0,
            'avg_profit_pct': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'signals': []
        }
    
    def _init_price_data(self):
        """初始化价格数据连接"""
        try:
            ts_file = Path(__file__).parent.parent / "data" / "btc_price_timeseries.duckdb"
            if ts_file.exists():
                self.price_conn = duckdb.connect(str(ts_file))
            else:
                self.price_conn = None
        except:
            self.price_conn = None
    
    def backtest_signal(self, signal: Dict) -> Dict:
        """回测单个信号"""
        if not self.price_conn:
            return None
        
        try:
            # 获取信号时间
            signal_time = signal.get('signal_time')
            if not signal_time:
                return None
            
            # 转换时间
            dt = datetime.strptime(signal_time, '%Y-%m-%d %H:%M:%S')
            signal_ts = int(dt.timestamp())
            
            # 获取信号参数
            entry_price = signal.get('entry_price')
            stop_loss = signal.get('stop_loss')
            take_profit_1 = signal.get('take_profit_1')
            take_profit_2 = signal.get('take_profit_2')
            signal_type = signal.get('signal_type', 'long')
            
            if not all([entry_price, stop_loss, take_profit_1]):
                return None
            
            # 获取信号后的价格数据（最多48小时）
            start_ts = signal_ts - 300  # 提前5分钟
            end_ts = signal_ts + 48 * 3600  # 48小时后
            
            query = '''
                SELECT timestamp, close
                FROM btc_price_5m
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
            '''
            
            price_data = self.price_conn.execute(query, [start_ts, end_ts]).fetchall()
            
            if not price_data:
                return {
                    'signal_id': signal.get('id'),
                    'result': 'missed',
                    'reason': '无价格数据',
                    'profit_pct': 0.0,
                    'profit_usdt': 0.0,
                    'exit_price': entry_price,
                    'exit_time': None
                }
            
            # 回测逻辑
            result = {
                'signal_id': signal.get('id'),
                'result': 'missed',
                'reason': '未触发',
                'profit_pct': 0.0,
                'profit_usdt': 0.0,
                'exit_price': entry_price,
                'exit_time': None,
                'stop_loss_hit': False,
                'take_profit_1_hit': False,
                'take_profit_2_hit': False
            }
            
            for ts, close_price in price_data:
                # 只评估信号时间之后的价格
                if ts < signal_ts:
                    continue
                
                if signal_type == 'long':
                    # 检查止损
                    if close_price <= stop_loss:
                        result['result'] = 'stopped'
                        result['reason'] = '触发止损'
                        result['exit_price'] = stop_loss
                        result['exit_time'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        result['profit_pct'] = ((stop_loss - entry_price) / entry_price) * 100
                        result['stop_loss_hit'] = True
                        break
                    
                    # 检查止盈
                    if close_price >= take_profit_2:
                        result['result'] = 'completed'
                        result['reason'] = '触发第二止盈'
                        result['exit_price'] = take_profit_2
                        result['exit_time'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        result['profit_pct'] = ((take_profit_2 - entry_price) / entry_price) * 100
                        result['take_profit_2_hit'] = True
                        break
                    elif close_price >= take_profit_1:
                        result['result'] = 'completed'
                        result['reason'] = '触发第一止盈'
                        result['exit_price'] = take_profit_1
                        result['exit_time'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        result['profit_pct'] = ((take_profit_1 - entry_price) / entry_price) * 100
                        result['take_profit_1_hit'] = True
                        # 继续检查是否达到第二止盈
                
                else:  # short
                    # 检查止损
                    if close_price >= stop_loss:
                        result['result'] = 'stopped'
                        result['reason'] = '触发止损'
                        result['exit_price'] = stop_loss
                        result['exit_time'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        result['profit_pct'] = ((entry_price - stop_loss) / entry_price) * 100
                        result['stop_loss_hit'] = True
                        break
                    
                    # 检查止盈
                    if close_price <= take_profit_2:
                        result['result'] = 'completed'
                        result['reason'] = '触发第二止盈'
                        result['exit_price'] = take_profit_2
                        result['exit_time'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        result['profit_pct'] = ((entry_price - take_profit_2) / entry_price) * 100
                        result['take_profit_2_hit'] = True
                        break
                    elif close_price <= take_profit_1:
                        result['result'] = 'completed'
                        result['reason'] = '触发第一止盈'
                        result['exit_price'] = take_profit_1
                        result['exit_time'] = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
                        result['profit_pct'] = ((entry_price - take_profit_1) / entry_price) * 100
                        result['take_profit_1_hit'] = True
            
            # 计算盈利金额（假设1%仓位，10000 USDT本金）
            base_capital = 10000
            position_size = base_capital * 0.01
            result['profit_usdt'] = position_size * (result['profit_pct'] / 100)
            
            return result
            
        except Exception as e:
            print(f"  回测信号失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None
    
    def run_backtest(self, limit: int = None) -> Dict:
        """运行回测"""
        print("=" * 80)
        print("回测系统")
        print("=" * 80)
        print()
        
        # 获取所有信号
        signals = self.db.get_trading_signals(status='pending', limit=limit)
        
        if not signals:
            print("没有待回测的信号")
            return self.results
        
        print(f"找到 {len(signals)} 个信号进行回测")
        print()
        
        # 重置结果
        self.results = {
            'total_signals': len(signals),
            'completed': 0,
            'stopped': 0,
            'missed': 0,
            'total_profit_pct': 0.0,
            'total_profit_usdt': 0.0,
            'win_rate': 0.0,
            'avg_profit_pct': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'signals': []
        }
        
        profits = []
        
        # 回测每个信号
        for i, signal in enumerate(signals):
            print(f"回测信号 {i+1}/{len(signals)}: {signal.get('signal_time')} {signal.get('signal_type')} @ {signal.get('entry_price')}")
            
            result = self.backtest_signal(signal)
            
            if result:
                self.results['signals'].append(result)
                
                # 统计
                if result['result'] == 'completed':
                    self.results['completed'] += 1
                    profits.append(result['profit_pct'])
                elif result['result'] == 'stopped':
                    self.results['stopped'] += 1
                    profits.append(result['profit_pct'])
                else:
                    self.results['missed'] += 1
                
                self.results['total_profit_pct'] += result['profit_pct']
                self.results['total_profit_usdt'] += result['profit_usdt']
        
        # 计算指标
        if profits:
            self.results['avg_profit_pct'] = sum(profits) / len(profits)
            self.results['win_rate'] = len([p for p in profits if p > 0]) / len(profits) * 100
            
            # 计算最大回撤
            cumulative = 0
            max_cumulative = 0
            max_drawdown = 0
            
            for p in profits:
                cumulative += p
                max_cumulative = max(max_cumulative, cumulative)
                drawdown = max_cumulative - cumulative
                max_drawdown = max(max_drawdown, drawdown)
            
            self.results['max_drawdown'] = max_drawdown
            
            # 计算Sharpe比率（简化版）
            if len(profits) > 1:
                import statistics
                mean_profit = statistics.mean(profits)
                std_profit = statistics.stdev(profits)
                self.results['sharpe_ratio'] = mean_profit / std_profit if std_profit > 0 else 0
        
        # 打印结果
        self._print_results()
        
        return self.results
    
    def _print_results(self):
        """打印回测结果"""
        print()
        print("=" * 80)
        print("回测结果")
        print("=" * 80)
        print()
        print(f"总信号数: {self.results['total_signals']}")
        print(f"  完成: {self.results['completed']} ({self.results['completed']/self.results['total_signals']*100:.1f}%)")
        print(f"  止损: {self.results['stopped']} ({self.results['stopped']/self.results['total_signals']*100:.1f}%)")
        print(f"  错过: {self.results['missed']} ({self.results['missed']/self.results['total_signals']*100:.1f}%)")
        print()
        print(f"总收益率: {self.results['total_profit_pct']:.2f}%")
        print(f"总盈利: {self.results['total_profit_usdt']:.2f} USDT")
        print(f"平均收益率: {self.results['avg_profit_pct']:.2f}%")
        print(f"胜率: {self.results['win_rate']:.2f}%")
        print(f"最大回撤: {self.results['max_drawdown']:.2f}%")
        print(f"Sharpe比率: {self.results['sharpe_ratio']:.2f}")
        print()
    
    def save_results(self, output_path: Path):
        """保存回测结果"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'backtest_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': self.results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 回测结果已保存到: {output_path}")
    
    def close(self):
        """关闭连接"""
        if hasattr(self, 'price_conn') and self.price_conn:
            self.price_conn.close()
        self.db.close()


def main():
    """主函数"""
    backtest = BacktestSystem(trader_id='de')
    
    try:
        # 运行回测
        results = backtest.run_backtest(limit=100)
        
        # 保存结果
        output_path = Path(__file__).parent.parent.parent / "trading_signals" / ".ml_models" / "backtest_results.json"
        backtest.save_results(output_path)
        
    except Exception as e:
        print(f"回测失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        backtest.close()

if __name__ == '__main__':
    main()

