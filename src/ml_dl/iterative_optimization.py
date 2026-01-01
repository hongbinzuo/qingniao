#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
迭代优化系统
1. 回测
2. 分析结果
3. 优化参数
4. 再次回测
循环进行
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


class IterativeOptimizer:
    """迭代优化器"""
    
    def __init__(self, trader_id='de', max_iterations=10):
        self.trader_id = trader_id
        self.max_iterations = max_iterations
        self.backtest = BacktestSystem(trader_id)
        self.db = TraderDBManager(trader_id)
        
        # 优化历史
        self.optimization_history = []
        
        # 当前最佳结果
        self.best_results = None
        self.best_iteration = 0
    
    def analyze_backtest_results(self, results: Dict) -> Dict:
        """分析回测结果，找出优化点"""
        analysis = {
            'issues': [],
            'suggestions': [],
            'priority': []
        }
        
        # 分析胜率
        win_rate = results.get('win_rate', 0)
        if win_rate < 50:
            analysis['issues'].append(f"胜率过低: {win_rate:.2f}%")
            analysis['suggestions'].append("优化止损止盈比例")
            analysis['priority'].append('high')
        
        # 分析平均收益
        avg_profit = results.get('avg_profit_pct', 0)
        if avg_profit < 1:
            analysis['issues'].append(f"平均收益过低: {avg_profit:.2f}%")
            analysis['suggestions'].append("优化止盈目标")
            analysis['priority'].append('high')
        
        # 分析最大回撤
        max_drawdown = results.get('max_drawdown', 0)
        if max_drawdown > 20:
            analysis['issues'].append(f"最大回撤过大: {max_drawdown:.2f}%")
            analysis['suggestions'].append("优化止损策略")
            analysis['priority'].append('high')
        
        # 分析Sharpe比率
        sharpe = results.get('sharpe_ratio', 0)
        if sharpe < 1:
            analysis['issues'].append(f"Sharpe比率过低: {sharpe:.2f}")
            analysis['suggestions'].append("优化风险收益比")
            analysis['priority'].append('medium')
        
        # 分析信号分布
        completed = results.get('completed', 0)
        stopped = results.get('stopped', 0)
        missed = results.get('missed', 0)
        
        if stopped > completed * 1.5:
            analysis['issues'].append(f"止损过多: {stopped} vs {completed}")
            analysis['suggestions'].append("放宽止损距离")
            analysis['priority'].append('high')
        
        if missed > completed + stopped:
            analysis['issues'].append(f"错过信号过多: {missed}")
            analysis['suggestions'].append("优化入场时机")
            analysis['priority'].append('medium')
        
        return analysis
    
    def optimize_parameters(self, analysis: Dict, current_results: Dict) -> Dict:
        """根据分析结果优化参数"""
        optimizations = {}
        
        # 根据优先级处理
        high_priority = [s for i, s in enumerate(analysis['suggestions']) 
                        if analysis['priority'][i] == 'high']
        
        for suggestion in high_priority:
            if '止损' in suggestion:
                # 优化止损：如果止损过多，放宽止损距离
                if '放宽' in suggestion:
                    optimizations['stop_loss_multiplier'] = 1.2  # 增加20%止损距离
            elif '止盈' in suggestion:
                # 优化止盈：如果收益过低，提高止盈目标
                if '优化止盈目标' in suggestion:
                    optimizations['take_profit_multiplier'] = 1.1  # 增加10%止盈目标
            elif '入场时机' in suggestion:
                # 优化入场时机：如果错过信号过多，调整入场逻辑
                optimizations['entry_timing_adjustment'] = True
        
        return optimizations
    
    def apply_optimizations(self, optimizations: Dict):
        """应用优化（这里只是示例，实际需要修改信号生成逻辑）"""
        print("=" * 80)
        print("应用优化")
        print("=" * 80)
        print()
        
        for key, value in optimizations.items():
            print(f"  {key}: {value}")
        
        print()
        print("注意: 实际优化需要修改信号生成逻辑")
        print("当前优化建议已记录，可在下次信号生成时应用")
        print()
    
    def run_iteration(self, iteration: int) -> Dict:
        """运行一次迭代"""
        print("=" * 80)
        print(f"迭代 {iteration}/{self.max_iterations}")
        print("=" * 80)
        print()
        
        # 1. 回测
        print("【1/3】运行回测...")
        results = self.backtest.run_backtest(limit=100)
        print()
        
        # 2. 分析结果
        print("【2/3】分析回测结果...")
        analysis = self.analyze_backtest_results(results)
        
        print("发现的问题:")
        for issue in analysis['issues']:
            print(f"  - {issue}")
        print()
        
        print("优化建议:")
        for suggestion in analysis['suggestions']:
            print(f"  - {suggestion}")
        print()
        
        # 3. 优化参数
        print("【3/3】生成优化方案...")
        optimizations = self.optimize_parameters(analysis, results)
        
        if optimizations:
            self.apply_optimizations(optimizations)
        else:
            print("  当前无需优化")
            print()
        
        # 记录迭代历史
        iteration_record = {
            'iteration': iteration,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'results': results,
            'analysis': analysis,
            'optimizations': optimizations
        }
        
        self.optimization_history.append(iteration_record)
        
        # 更新最佳结果
        if not self.best_results or results.get('total_profit_pct', 0) > self.best_results.get('total_profit_pct', 0):
            self.best_results = results
            self.best_iteration = iteration
        
        return iteration_record
    
    def run_optimization_loop(self):
        """运行优化循环"""
        print("=" * 80)
        print("迭代优化系统")
        print("=" * 80)
        print()
        print(f"最大迭代次数: {self.max_iterations}")
        print()
        
        for i in range(1, self.max_iterations + 1):
            try:
                iteration_record = self.run_iteration(i)
                
                # 检查是否达到目标
                results = iteration_record['results']
                if results.get('win_rate', 0) >= 60 and results.get('avg_profit_pct', 0) >= 2:
                    print("=" * 80)
                    print("达到目标性能，停止优化")
                    print("=" * 80)
                    break
                
                print()
                
            except KeyboardInterrupt:
                print("\n优化被用户中断")
                break
            except Exception as e:
                print(f"\n迭代失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 打印总结
        self._print_summary()
        
        # 保存历史
        self._save_history()
    
    def _print_summary(self):
        """打印优化总结"""
        print()
        print("=" * 80)
        print("优化总结")
        print("=" * 80)
        print()
        print(f"总迭代次数: {len(self.optimization_history)}")
        print(f"最佳迭代: {self.best_iteration}")
        print()
        
        if self.best_results:
            print("最佳结果:")
            print(f"  总收益率: {self.best_results.get('total_profit_pct', 0):.2f}%")
            print(f"  平均收益率: {self.best_results.get('avg_profit_pct', 0):.2f}%")
            print(f"  胜率: {self.best_results.get('win_rate', 0):.2f}%")
            print(f"  最大回撤: {self.best_results.get('max_drawdown', 0):.2f}%")
            print()
    
    def _save_history(self):
        """保存优化历史"""
        output_path = Path(__file__).parent.parent.parent / "trading_signals" / ".ml_models" / "optimization_history.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'optimization_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_iterations': len(self.optimization_history),
            'best_iteration': self.best_iteration,
            'best_results': self.best_results,
            'history': self.optimization_history
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ 优化历史已保存到: {output_path}")
    
    def close(self):
        """关闭连接"""
        self.backtest.close()
        self.db.close()


def main():
    """主函数"""
    optimizer = IterativeOptimizer(trader_id='de', max_iterations=5)
    
    try:
        optimizer.run_optimization_loop()
    except Exception as e:
        print(f"优化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        optimizer.close()

if __name__ == '__main__':
    main()





