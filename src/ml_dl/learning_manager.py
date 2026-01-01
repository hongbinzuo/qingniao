#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一学习管理器
整合离线学习（回测+优化）和在线学习（执行结果学习）
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

from ml_dl.online_learning import OnlineLearner
from ml_dl.backtest_system import BacktestSystem
from ml_dl.iterative_optimization import IterativeOptimizer


class LearningManager:
    """统一学习管理器 - 整合离线学习和在线学习"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.online_learner = OnlineLearner(trader_id)
        self.backtest_system = BacktestSystem(trader_id)
        self.optimizer = IterativeOptimizer(trader_id)
        self.learning_data_path = Path(__file__).parent.parent.parent / "trading_signals" / ".ml_models"
        self.learning_data_path.mkdir(parents=True, exist_ok=True)
    
    def learn_from_backtest(self, signals: List[Dict] = None, limit: int = None) -> Dict:
        """
        从回测结果学习（离线学习）
        
        Args:
            signals: 信号列表，如果为None则从数据库获取
            limit: 限制信号数量
        
        Returns:
            优化结果字典
        """
        print("="*80)
        print("离线学习 - 从回测结果学习")
        print("="*80)
        print("", file=sys.stderr)
        
        # 运行回测
        backtest_results = self.backtest_system.run_backtest(signals=signals, limit=limit)
        
        # 分析回测结果
        analysis = self.optimizer.analyze_backtest_results(backtest_results)
        
        # 生成优化建议
        optimizations = self.optimizer.optimize_parameters(analysis, backtest_results)
        
        return {
            'backtest_results': backtest_results,
            'analysis': analysis,
            'optimizations': optimizations
        }
    
    def learn_from_execution(self, signals_data: List[Dict]) -> Dict:
        """
        从执行结果学习（在线学习）
        
        Args:
            signals_data: 信号执行数据列表
        
        Returns:
            学习结果字典
        """
        return self.online_learner.learn_from_signals(signals_data)
    
    def integrate_learning(self, execution_signals: List[Dict] = None, 
                          backtest_signals: List[Dict] = None) -> Dict:
        """
        整合离线学习和在线学习结果
        
        Args:
            execution_signals: 实际执行信号数据
            backtest_signals: 回测信号数据
        
        Returns:
            整合后的学习结果
        """
        print("="*80)
        print("整合学习 - 结合离线学习和在线学习")
        print("="*80)
        print("", file=sys.stderr)
        
        # 1. 在线学习（从实际执行结果）
        online_result = None
        if execution_signals:
            print("\n【1/2】在线学习（从实际执行结果）...", file=sys.stderr)
            online_result = self.learn_from_execution(execution_signals)
            print("✅ 在线学习完成", file=sys.stderr)
        
        # 2. 离线学习（从回测结果）
        offline_result = None
        if backtest_signals:
            print("\n【2/2】离线学习（从回测结果）...", file=sys.stderr)
            offline_result = self.learn_from_backtest(signals=backtest_signals)
            print("✅ 离线学习完成", file=sys.stderr)
        
        # 3. 整合结果
        print("\n整合学习结果...", file=sys.stderr)
        integrated_result = self._integrate_results(online_result, offline_result)
        
        # 4. 生成综合报告
        report = self._generate_integrated_report(integrated_result)
        
        # 保存报告
        report_file = self.learning_data_path / f"integrated_learning_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_file.write_text(report, encoding='utf-8')
        print(f"\n✅ 综合学习报告已保存到: {report_file}", file=sys.stderr)
        
        return integrated_result
    
    def _integrate_results(self, online_result: Optional[Dict], offline_result: Optional[Dict]) -> Dict:
        """整合在线学习和离线学习结果"""
        integrated = {
            'online_learning': online_result,
            'offline_learning': offline_result,
            'integrated_parameters': {},
            'recommendations': []
        }
        
        # 获取当前参数
        current_params = self.online_learner.get_current_parameters()
        integrated_params = current_params.copy()
        
        # 整合参数更新
        if online_result and online_result.get('parameters'):
            online_params = online_result['parameters']
            # 在线学习参数优先级更高（基于实际执行结果）
            integrated_params.update(online_params)
        
        if offline_result and offline_result.get('optimizations'):
            offline_opt = offline_result['optimizations']
            # 离线学习参数作为补充
            if 'stop_loss_multiplier' in offline_opt:
                # 应用止损倍数
                for vol in ['low_volatility', 'medium_volatility', 'high_volatility']:
                    if vol in integrated_params['stop_loss_multipliers']:
                        integrated_params['stop_loss_multipliers'][vol] *= offline_opt['stop_loss_multiplier']
        
        integrated['integrated_parameters'] = integrated_params
        
        # 整合建议
        if online_result and online_result.get('analysis'):
            integrated['recommendations'].extend(
                online_result['analysis'].get('recommendations', [])
            )
        
        if offline_result and offline_result.get('analysis'):
            for suggestion in offline_result['analysis'].get('suggestions', []):
                integrated['recommendations'].append({
                    'type': 'backtest_optimization',
                    'suggestion': suggestion
                })
        
        return integrated
    
    def _generate_integrated_report(self, integrated_result: Dict) -> str:
        """生成综合学习报告"""
        report = []
        report.append("# 综合学习报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 在线学习结果
        if integrated_result.get('online_learning'):
            report.append("## 在线学习结果（实际执行）")
            report.append("")
            online = integrated_result['online_learning']
            if online.get('analysis'):
                analysis = online['analysis']
                report.append(f"- **总信号数**: {analysis.get('total_signals', 0)}")
                report.append(f"- **止损**: {analysis.get('stopped_count', 0)}")
                report.append(f"- **错过**: {analysis.get('missed_count', 0)}")
                report.append(f"- **完成**: {analysis.get('completed_count', 0)}")
            report.append("")
        
        # 离线学习结果
        if integrated_result.get('offline_learning'):
            report.append("## 离线学习结果（回测优化）")
            report.append("")
            offline = integrated_result['offline_learning']
            if offline.get('backtest_results'):
                results = offline['backtest_results']
                report.append(f"- **胜率**: {results.get('win_rate', 0):.2f}%")
                report.append(f"- **总收益率**: {results.get('total_return', 0):.2f}%")
                report.append(f"- **最大回撤**: {results.get('max_drawdown', 0):.2f}%")
            report.append("")
        
        # 整合后的参数
        report.append("## 整合后的系统参数")
        report.append("")
        report.append("```json")
        report.append(json.dumps(integrated_result.get('integrated_parameters', {}), indent=2, ensure_ascii=False))
        report.append("```")
        report.append("")
        
        # 综合建议
        if integrated_result.get('recommendations'):
            report.append("## 综合改进建议")
            report.append("")
            for rec in integrated_result['recommendations']:
                if isinstance(rec, dict):
                    report.append(f"- **{rec.get('type', 'N/A')}**: {rec.get('reason', rec.get('suggestion', 'N/A'))}")
                else:
                    report.append(f"- {rec}")
            report.append("")
        
        return "\n".join(report)
    
    def close(self):
        """关闭所有连接"""
        self.online_learner.close()
        self.backtest_system.close()
        self.optimizer.close()


if __name__ == "__main__":
    # 测试代码
    manager = LearningManager()
    
    # 示例：在线学习
    test_execution_signals = [
        {
            'timeframe': '15m',
            'signal_type': 'short',
            'entry_price': 87824,
            'stop_loss': 88087,
            'stop_distance_pct': 0.30,
            'atr_pct': 0.08,
            'volatility': 'low',
            'result': 'stopped',
            'profit_pct': -0.30,
            'max_profit_pct': 0.16,
            'failure_reasons': ['stop_loss_too_tight']
        }
    ]
    
    print("测试在线学习...")
    online_result = manager.learn_from_execution(test_execution_signals)
    print(f"在线学习完成: {len(online_result['analysis']['recommendations'])} 条建议")
    
    manager.close()





