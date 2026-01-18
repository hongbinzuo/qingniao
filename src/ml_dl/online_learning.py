#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在线学习模块 - 从实际执行结果学习
基于信号执行报告分析失败原因，自动更新系统参数
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from db_manager_trader import TraderDBManager

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 尝试导入优化结果记录器
try:
    from ml_dl.optimization_result_recorder import OptimizationResultRecorder
    RECORDER_AVAILABLE = True
except ImportError:
    RECORDER_AVAILABLE = False
    OptimizationResultRecorder = None


class OnlineLearner:
    """在线学习模块 - 从实际执行结果学习"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.learning_data_path = Path(__file__).parent.parent.parent / "trading_signals" / ".ml_models"
        self.learning_data_path.mkdir(parents=True, exist_ok=True)
        self.params_file = self.learning_data_path / "system_parameters.json"
        
        # 初始化优化结果记录器
        if RECORDER_AVAILABLE:
            self.recorder = OptimizationResultRecorder(trader_id)
        else:
            self.recorder = None
    
    def analyze_execution_results(self, signals_data: List[Dict]) -> Dict:
        """
        分析执行结果，提取失败模式和改进建议
        
        Args:
            signals_data: 信号执行数据列表，每个包含：
                - timeframe: 时间框架
                - signal_type: 信号类型
                - entry_price: 入场价格
                - stop_loss: 止损价格
                - stop_distance_pct: 止损距离百分比
                - atr_pct: ATR百分比
                - volatility: 波动率水平
                - result: 执行结果 (stopped/missed/completed)
                - profit_pct: 盈亏百分比
                - max_profit_pct: 最大浮盈
                - failure_reasons: 失败原因列表
        
        Returns:
            分析结果字典
        """
        analysis = {
            'total_signals': len(signals_data),
            'stopped_count': 0,
            'missed_count': 0,
            'completed_count': 0,
            'stop_loss_issues': [],
            'entry_price_issues': [],
            'recommendations': []
        }
        
        for signal in signals_data:
            result = signal.get('result', 'pending')
            
            if result == 'stopped':
                analysis['stopped_count'] += 1
                # 分析止损问题
                self._analyze_stop_loss_issue(signal, analysis)
            elif result == 'missed':
                analysis['missed_count'] += 1
                # 分析入场价格问题
                if 'entry_price_unreachable' in signal.get('failure_reasons', []):
                    analysis['entry_price_issues'].append({
                        'timeframe': signal.get('timeframe'),
                        'issue': 'entry_price_unreachable'
                    })
            elif result == 'completed':
                analysis['completed_count'] += 1
        
        # 生成建议
        self._generate_recommendations(analysis)
        
        return analysis
    
    def _analyze_stop_loss_issue(self, signal: Dict, analysis: Dict):
        """分析止损问题"""
        stop_distance_pct = signal.get('stop_distance_pct')
        volatility = signal.get('volatility')
        max_profit_pct = signal.get('max_profit_pct', 0)
        
        if not stop_distance_pct or not volatility:
            return
        
        # 检查止损是否过小
        issue = None
        if volatility == 'low' and stop_distance_pct < 0.4:
            issue = 'stop_loss_too_tight_low_vol'
        elif volatility == 'high' and stop_distance_pct < 1.0:
            issue = 'stop_loss_too_tight_high_vol'
        
        if issue:
            analysis['stop_loss_issues'].append({
                'timeframe': signal.get('timeframe'),
                'stop_distance_pct': stop_distance_pct,
                'volatility': volatility,
                'issue': issue,
                'max_profit_pct': max_profit_pct
            })
    
    def _generate_recommendations(self, analysis: Dict):
        """生成改进建议"""
        # 止损建议
        if analysis['stop_loss_issues']:
            low_vol_issues = [i for i in analysis['stop_loss_issues'] if i['volatility'] == 'low']
            high_vol_issues = [i for i in analysis['stop_loss_issues'] if i['volatility'] == 'high']
            
            if low_vol_issues:
                avg_stop = sum(i['stop_distance_pct'] for i in low_vol_issues) / len(low_vol_issues)
                analysis['recommendations'].append({
                    'type': 'stop_loss',
                    'volatility': 'low',
                    'current_avg': avg_stop,
                    'recommended': 0.4,
                    'reason': '低波动市场止损距离过小，建议至少0.4%'
                })
            
            if high_vol_issues:
                avg_stop = sum(i['stop_distance_pct'] for i in high_vol_issues) / len(high_vol_issues)
                analysis['recommendations'].append({
                    'type': 'stop_loss',
                    'volatility': 'high',
                    'current_avg': avg_stop,
                    'recommended': 1.0,
                    'reason': '高波动市场止损距离过小，建议至少1.0%'
                })
        
        # 入场价格建议
        if analysis['entry_price_issues']:
            analysis['recommendations'].append({
                'type': 'entry_price',
                'issue': '入场价无法成交',
                'recommended': '添加成交可行性检查',
                'reason': '入场价可能是技术位而非当前价格，需要检查成交可行性'
            })
    
    def update_parameters(self, analysis: Dict) -> Dict:
        """
        根据分析结果更新系统参数
        
        Args:
            analysis: 分析结果字典
        
        Returns:
            更新后的参数字典
        """
        # 读取当前参数
        if self.params_file.exists():
            current_params = json.loads(self.params_file.read_text(encoding='utf-8'))
        else:
            current_params = {
                'stop_loss_multipliers': {
                    'low_volatility': 1.0,
                    'medium_volatility': 1.0,
                    'high_volatility': 1.0
                },
                'min_stop_distances': {
                    'low_volatility': 0.3,
                    'medium_volatility': 0.5,
                    'high_volatility': 0.8
                },
                'entry_price_check': False
            }
        
        # 根据分析结果更新参数
        updated = False
        
        for rec in analysis.get('recommendations', []):
            if rec['type'] == 'stop_loss':
                vol = rec['volatility']
                if vol == 'low':
                    new_value = max(current_params['min_stop_distances']['low_volatility'], rec['recommended'])
                    if new_value > current_params['min_stop_distances']['low_volatility']:
                        current_params['min_stop_distances']['low_volatility'] = new_value
                        updated = True
                        print(f"✅ 更新低波动市场最小止损距离: {new_value:.2f}%", file=sys.stderr)
                elif vol == 'high':
                    new_value = max(current_params['min_stop_distances']['high_volatility'], rec['recommended'])
                    if new_value > current_params['min_stop_distances']['high_volatility']:
                        current_params['min_stop_distances']['high_volatility'] = new_value
                        updated = True
                        print(f"✅ 更新高波动市场最小止损距离: {new_value:.2f}%", file=sys.stderr)
            
            elif rec['type'] == 'entry_price':
                if not current_params['entry_price_check']:
                    current_params['entry_price_check'] = True
                    updated = True
                    print(f"✅ 启用入场价格成交可行性检查", file=sys.stderr)
        
        # 保存更新后的参数
        if updated:
            self.params_file.write_text(
                json.dumps(current_params, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            print(f"✅ 系统参数已更新并保存到: {self.params_file}", file=sys.stderr)
        else:
            print("ℹ️ 无需更新系统参数", file=sys.stderr)
        
        return current_params
    
    def learn_from_signals(self, signals_data: List[Dict]) -> Dict:
        """
        从信号数据学习（主入口）
        
        Args:
            signals_data: 信号执行数据列表
        
        Returns:
            学习结果字典，包含分析结果和更新后的参数
        """
        print("="*80)
        print("在线学习 - 从执行结果学习")
        print("="*80)
        print("", file=sys.stderr)
        
        # 分析执行结果
        analysis = self.analyze_execution_results(signals_data)
        
        # 更新参数
        params = self.update_parameters(analysis)
        
        # 记录优化结果到数据库
        if self.recorder:
            try:
                # 计算数据量
                data_count = analysis.get('total_signals', 0)
                
                # 计算时间跨度（如果有信号数据）
                time_span_days = None
                if signals_data:
                    try:
                        from datetime import datetime
                        times = [s.get('signal_time') for s in signals_data if s.get('signal_time')]
                        if len(times) >= 2:
                            earliest = min(times)
                            latest = max(times)
                            if earliest and latest:
                                earliest_dt = datetime.fromisoformat(earliest.replace('Z', '+00:00'))
                                latest_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
                                time_span_days = (latest_dt - earliest_dt).days
                    except:
                        pass
                
                # 准备性能指标
                metrics = {
                    'total_signals': analysis.get('total_signals', 0),
                    'stopped_count': analysis.get('stopped_count', 0),
                    'missed_count': analysis.get('missed_count', 0),
                    'completed_count': analysis.get('completed_count', 0)
                }
                
                # 获取当前参数作为优化前参数
                current_params = self.get_current_parameters()
                
                # 记录结果
                self.recorder.record_incremental_learning(
                    data_count=data_count,
                    time_span_days=time_span_days or 0,
                    metrics=metrics,
                    parameters_before=current_params,
                    parameters_after=params,
                    improvements=[rec.get('reason', rec.get('suggestion', '')) for rec in analysis.get('recommendations', [])],
                    notes=f"在线学习：分析了{data_count}个信号"
                )
            except Exception as e:
                print(f"  [WARN] 记录优化结果失败: {e}", file=sys.stderr)
        
        return {
            'analysis': analysis,
            'parameters': params
        }
    
    def get_current_parameters(self) -> Dict:
        """获取当前系统参数"""
        if self.params_file.exists():
            return json.loads(self.params_file.read_text(encoding='utf-8'))
        else:
            return {
                'stop_loss_multipliers': {
                    'low_volatility': 1.0,
                    'medium_volatility': 1.0,
                    'high_volatility': 1.0
                },
                'min_stop_distances': {
                    'low_volatility': 0.3,
                    'medium_volatility': 0.5,
                    'high_volatility': 0.8
                },
                'entry_price_check': False
            }
    
    def close(self):
        """关闭连接"""
        if self.recorder:
            self.recorder.close()
        self.db.close()


if __name__ == "__main__":
    # 测试代码
    learner = OnlineLearner()
    
    # 示例数据
    test_signals = [
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
        },
        {
            'timeframe': '1h',
            'signal_type': 'long',
            'entry_price': 87018,
            'stop_loss': 86700,
            'stop_distance_pct': 0.37,
            'atr_pct': 0.81,
            'volatility': 'high',
            'result': 'missed',
            'profit_pct': 0,
            'failure_reasons': ['entry_price_unreachable']
        }
    ]
    
    result = learner.learn_from_signals(test_signals)
    
    print("\n学习结果:")
    print(f"总信号数: {result['analysis']['total_signals']}")
    print(f"止损: {result['analysis']['stopped_count']}")
    print(f"错过: {result['analysis']['missed_count']}")
    print(f"建议数: {len(result['analysis']['recommendations'])}")
    
    learner.close()

