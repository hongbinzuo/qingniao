#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
带优化的回测系统
1. 回测原始信号
2. 分析结果
3. 应用优化（调整止损止盈参数）
4. 用优化后的参数重新回测
5. 循环迭代
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from backtest_system import BacktestSystem
from db_manager_trader import TraderDBManager


class OptimizedBacktest:
    """带优化的回测系统"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.backtest = BacktestSystem(trader_id)
        self.db = TraderDBManager(trader_id)
        
        # 优化参数
        self.optimizations = {
            'stop_loss_multiplier': 1.0,  # 止损倍数
            'take_profit_multiplier': 1.0,  # 止盈倍数
            'risk_reward_ratio': 2.5  # 目标盈亏比
        }
    
    def backtest_with_optimized_params(self, signal: Dict) -> Dict:
        """使用优化后的参数回测信号"""
        # 复制信号
        optimized_signal = signal.copy()
        
        # 应用优化
        entry_price = signal.get('entry_price')
        original_stop_loss = signal.get('stop_loss')
        original_tp1 = signal.get('take_profit_1')
        original_tp2 = signal.get('take_profit_2')
        signal_type = signal.get('signal_type', 'long')
        
        if not all([entry_price, original_stop_loss, original_tp1]):
            return None
        
        # 调整止损
        if signal_type == 'long':
            stop_loss_distance = entry_price - original_stop_loss
            optimized_stop_loss = entry_price - (stop_loss_distance * self.optimizations['stop_loss_multiplier'])
            
            # 调整止盈（保持盈亏比）
            risk = entry_price - optimized_stop_loss
            optimized_tp1 = entry_price + (risk * self.optimizations['risk_reward_ratio'])
            optimized_tp2 = optimized_tp1 + (risk * 1.0)  # 第二止盈再增加1R
        else:  # short
            stop_loss_distance = original_stop_loss - entry_price
            optimized_stop_loss = entry_price + (stop_loss_distance * self.optimizations['stop_loss_multiplier'])
            
            # 调整止盈
            risk = optimized_stop_loss - entry_price
            optimized_tp1 = entry_price - (risk * self.optimizations['risk_reward_ratio'])
            optimized_tp2 = optimized_tp1 - (risk * 1.0)
        
        # 应用止盈倍数
        if signal_type == 'long':
            optimized_tp1 = entry_price + (optimized_tp1 - entry_price) * self.optimizations['take_profit_multiplier']
            optimized_tp2 = entry_price + (optimized_tp2 - entry_price) * self.optimizations['take_profit_multiplier']
        else:
            optimized_tp1 = entry_price - (entry_price - optimized_tp1) * self.optimizations['take_profit_multiplier']
            optimized_tp2 = entry_price - (entry_price - optimized_tp2) * self.optimizations['take_profit_multiplier']
        
        # 更新信号参数
        optimized_signal['stop_loss'] = optimized_stop_loss
        optimized_signal['take_profit_1'] = optimized_tp1
        optimized_signal['take_profit_2'] = optimized_tp2
        
        # 重新计算盈亏比
        if signal_type == 'long':
            risk = entry_price - optimized_stop_loss
            reward = optimized_tp1 - entry_price
        else:
            risk = optimized_stop_loss - entry_price
            reward = entry_price - optimized_tp1
        
        optimized_signal['risk_reward_ratio'] = reward / risk if risk > 0 else 0
        
        # 回测优化后的信号
        return self.backtest.backtest_signal(optimized_signal)
    
    def run_optimized_backtest(self, limit: int = None) -> Dict:
        """运行优化后的回测"""
        print("=" * 80)
        print("优化回测系统")
        print("=" * 80)
        print()
        print(f"当前优化参数:")
        print(f"  止损倍数: {self.optimizations['stop_loss_multiplier']:.2f}")
        print(f"  止盈倍数: {self.optimizations['take_profit_multiplier']:.2f}")
        print(f"  目标盈亏比: {self.optimizations['risk_reward_ratio']:.2f}")
        print()
        
        # 获取所有信号
        signals = self.db.get_trading_signals(status='pending', limit=limit)
        
        if not signals:
            print("没有待回测的信号")
            return {}
        
        print(f"找到 {len(signals)} 个信号进行优化回测")
        print()
        
        # 回测结果
        results = {
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
        
        # 回测每个信号（使用优化参数）
        for i, signal in enumerate(signals):
            print(f"回测信号 {i+1}/{len(signals)}: {signal.get('signal_time')} {signal.get('signal_type')} @ {signal.get('entry_price')}")
            
            result = self.backtest_with_optimized_params(signal)
            
            if result:
                results['signals'].append(result)
                
                # 统计
                if result['result'] == 'completed':
                    results['completed'] += 1
                    profits.append(result['profit_pct'])
                elif result['result'] == 'stopped':
                    results['stopped'] += 1
                    profits.append(result['profit_pct'])
                else:
                    results['missed'] += 1
                
                results['total_profit_pct'] += result['profit_pct']
                results['total_profit_usdt'] += result['profit_usdt']
        
        # 计算指标
        if profits:
            results['avg_profit_pct'] = sum(profits) / len(profits)
            results['win_rate'] = len([p for p in profits if p > 0]) / len(profits) * 100
            
            # 计算最大回撤
            cumulative = 0
            max_cumulative = 0
            max_drawdown = 0
            
            for p in profits:
                cumulative += p
                max_cumulative = max(max_cumulative, cumulative)
                drawdown = max_cumulative - cumulative
                max_drawdown = max(max_drawdown, drawdown)
            
            results['max_drawdown'] = max_drawdown
            
            # 计算Sharpe比率
            if len(profits) > 1:
                import statistics
                mean_profit = statistics.mean(profits)
                std_profit = statistics.stdev(profits)
                results['sharpe_ratio'] = mean_profit / std_profit if std_profit > 0 else 0
        
        # 打印结果
        print()
        print("=" * 80)
        print("优化回测结果")
        print("=" * 80)
        print()
        print(f"总信号数: {results['total_signals']}")
        print(f"  完成: {results['completed']} ({results['completed']/results['total_signals']*100:.1f}%)")
        print(f"  止损: {results['stopped']} ({results['stopped']/results['total_signals']*100:.1f}%)")
        print(f"  错过: {results['missed']} ({results['missed']/results['total_signals']*100:.1f}%)")
        print()
        print(f"总收益率: {results['total_profit_pct']:.2f}%")
        print(f"总盈利: {results['total_profit_usdt']:.2f} USDT")
        print(f"平均收益率: {results['avg_profit_pct']:.2f}%")
        print(f"胜率: {results['win_rate']:.2f}%")
        print(f"最大回撤: {results['max_drawdown']:.2f}%")
        print(f"Sharpe比率: {results['sharpe_ratio']:.2f}")
        print()
        
        return results
    
    def update_optimizations(self, analysis: Dict):
        """根据分析结果更新优化参数"""
        high_priority = [s for i, s in enumerate(analysis['suggestions']) 
                        if analysis['priority'][i] == 'high']
        
        for suggestion in high_priority:
            if '止损' in suggestion and '放宽' in suggestion:
                # 放宽止损距离
                self.optimizations['stop_loss_multiplier'] *= 1.1
            elif '止盈' in suggestion and '优化止盈目标' in suggestion:
                # 提高止盈目标
                self.optimizations['take_profit_multiplier'] *= 1.1
            elif '风险收益比' in suggestion:
                # 提高盈亏比
                self.optimizations['risk_reward_ratio'] *= 1.05
        
        # 限制参数范围
        self.optimizations['stop_loss_multiplier'] = min(self.optimizations['stop_loss_multiplier'], 2.0)
        self.optimizations['take_profit_multiplier'] = min(self.optimizations['take_profit_multiplier'], 2.0)
        self.optimizations['risk_reward_ratio'] = min(self.optimizations['risk_reward_ratio'], 5.0)
    
    def close(self):
        """关闭连接"""
        self.backtest.close()
        self.db.close()


def main():
    """主函数 - 迭代优化回测"""
    from iterative_optimization import IterativeOptimizer
    
    optimizer = IterativeOptimizer(trader_id='de', max_iterations=5)
    optimized_backtest = OptimizedBacktest(trader_id='de')
    
    try:
        print("=" * 80)
        print("迭代优化回测系统")
        print("=" * 80)
        print()
        
        for i in range(1, optimizer.max_iterations + 1):
            print("=" * 80)
            print(f"迭代 {i}/{optimizer.max_iterations}")
            print("=" * 80)
            print()
            
            # 1. 运行优化回测
            print("【1/3】运行优化回测...")
            results = optimized_backtest.run_optimized_backtest(limit=100)
            print()
            
            if not results:
                break
            
            # 2. 分析结果
            print("【2/3】分析回测结果...")
            analysis = optimizer.analyze_backtest_results(results)
            
            print("发现的问题:")
            for issue in analysis['issues']:
                print(f"  - {issue}")
            print()
            
            print("优化建议:")
            for suggestion in analysis['suggestions']:
                print(f"  - {suggestion}")
            print()
            
            # 3. 更新优化参数
            print("【3/3】更新优化参数...")
            old_params = optimized_backtest.optimizations.copy()
            optimized_backtest.update_optimizations(analysis)
            
            print("参数变化:")
            for key in old_params:
                if old_params[key] != optimized_backtest.optimizations[key]:
                    print(f"  {key}: {old_params[key]:.2f} → {optimized_backtest.optimizations[key]:.2f}")
            print()
            
            # 检查是否达到目标
            if results.get('win_rate', 0) >= 50 and results.get('avg_profit_pct', 0) >= 1:
                print("=" * 80)
                print("达到目标性能，停止优化")
                print("=" * 80)
                break
            
            print()
        
        # 打印最终结果
        print("=" * 80)
        print("最终优化结果")
        print("=" * 80)
        print()
        print(f"最终优化参数:")
        for key, value in optimized_backtest.optimizations.items():
            print(f"  {key}: {value:.2f}")
        print()
        
    except Exception as e:
        print(f"优化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        optimized_backtest.close()
        optimizer.close()

if __name__ == '__main__':
    main()










