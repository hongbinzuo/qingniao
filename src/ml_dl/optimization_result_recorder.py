#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化结果记录器
将机器学习优化结果保存到数据库
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

# 添加src目录到路径
ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  数据库模块不可用", file=sys.stderr)


class OptimizationResultRecorder:
    """优化结果记录器"""
    
    def __init__(self, trader_id='abu'):
        self.trader_id = trader_id
        if DB_AVAILABLE:
            self.db = TraderDBManager(trader_id)
        else:
            self.db = None
            print("⚠️  数据库不可用，优化结果将不会保存到数据库", file=sys.stderr)
    
    def record_incremental_learning(self, data_count: int, time_span_days: int,
                                    metrics: Dict, parameters_before: Dict,
                                    parameters_after: Dict, improvements: List[str],
                                    notes: str = None) -> Optional[int]:
        """
        记录增量学习结果
        
        Args:
            data_count: 使用的数据量
            time_span_days: 数据时间跨度
            metrics: 性能指标字典
            parameters_before: 优化前参数
            parameters_after: 优化后参数
            improvements: 改进建议列表
            notes: 备注
        
        Returns:
            记录ID，如果失败则返回None
        """
        if not self.db:
            return None
        
        try:
            return self.db.add_ml_optimization_result(
                optimization_type='incremental_learning',
                status='completed',
                data_count=data_count,
                time_span_days=time_span_days,
                metrics_json=json.dumps(metrics, ensure_ascii=False),
                parameters_before=json.dumps(parameters_before, ensure_ascii=False),
                parameters_after=json.dumps(parameters_after, ensure_ascii=False),
                improvements_json=json.dumps(improvements, ensure_ascii=False),
                notes=notes
            )
        except Exception as e:
            print(f"  [ERROR] 记录增量学习结果失败: {e}", file=sys.stderr)
            return None
    
    def record_ml_training(self, data_count: int, time_span_days: int,
                         metrics: Dict, model_file_path: str = None,
                         report_file_path: str = None, notes: str = None) -> Optional[int]:
        """
        记录ML模型训练结果
        
        Args:
            data_count: 使用的数据量
            time_span_days: 数据时间跨度
            metrics: 性能指标字典（如准确率、胜率等）
            model_file_path: 模型文件路径
            report_file_path: 报告文件路径
            notes: 备注
        
        Returns:
            记录ID，如果失败则返回None
        """
        if not self.db:
            return None
        
        try:
            return self.db.add_ml_optimization_result(
                optimization_type='ml_training',
                status='completed',
                data_count=data_count,
                time_span_days=time_span_days,
                metrics_json=json.dumps(metrics, ensure_ascii=False),
                model_file_path=model_file_path,
                report_file_path=report_file_path,
                notes=notes
            )
        except Exception as e:
            print(f"  [ERROR] 记录ML训练结果失败: {e}", file=sys.stderr)
            return None
    
    def record_full_retrain(self, data_count: int, time_span_days: int,
                           metrics: Dict, parameters_before: Dict = None,
                           parameters_after: Dict = None, model_file_path: str = None,
                           report_file_path: str = None, notes: str = None) -> Optional[int]:
        """
        记录完整模型重训练结果
        
        Args:
            data_count: 使用的数据量
            time_span_days: 数据时间跨度
            metrics: 性能指标字典
            parameters_before: 优化前参数（可选）
            parameters_after: 优化后参数（可选）
            model_file_path: 模型文件路径
            report_file_path: 报告文件路径
            notes: 备注
        
        Returns:
            记录ID，如果失败则返回None
        """
        if not self.db:
            return None
        
        try:
            return self.db.add_ml_optimization_result(
                optimization_type='full_retrain',
                status='completed',
                data_count=data_count,
                time_span_days=time_span_days,
                metrics_json=json.dumps(metrics, ensure_ascii=False),
                parameters_before=json.dumps(parameters_before, ensure_ascii=False) if parameters_before else None,
                parameters_after=json.dumps(parameters_after, ensure_ascii=False) if parameters_after else None,
                model_file_path=model_file_path,
                report_file_path=report_file_path,
                notes=notes
            )
        except Exception as e:
            print(f"  [ERROR] 记录完整重训练结果失败: {e}", file=sys.stderr)
            return None
    
    def record_parameter_optimization(self, data_count: int, time_span_days: int,
                                     metrics: Dict, parameters_before: Dict,
                                     parameters_after: Dict, improvements: List[str] = None,
                                     notes: str = None) -> Optional[int]:
        """
        记录参数优化结果
        
        Args:
            data_count: 使用的数据量
            time_span_days: 数据时间跨度
            metrics: 性能指标字典
            parameters_before: 优化前参数
            parameters_after: 优化后参数
            improvements: 改进建议列表（可选）
            notes: 备注
        
        Returns:
            记录ID，如果失败则返回None
        """
        if not self.db:
            return None
        
        try:
            return self.db.add_ml_optimization_result(
                optimization_type='parameter_optimization',
                status='completed',
                data_count=data_count,
                time_span_days=time_span_days,
                metrics_json=json.dumps(metrics, ensure_ascii=False),
                parameters_before=json.dumps(parameters_before, ensure_ascii=False),
                parameters_after=json.dumps(parameters_after, ensure_ascii=False),
                improvements_json=json.dumps(improvements, ensure_ascii=False) if improvements else None,
                notes=notes
            )
        except Exception as e:
            print(f"  [ERROR] 记录参数优化结果失败: {e}", file=sys.stderr)
            return None
    
    def record_pattern_weight_optimization(self, data_count: int, time_span_days: int,
                                          metrics: Dict, weights_before: Dict,
                                          weights_after: Dict, notes: str = None) -> Optional[int]:
        """
        记录模式权重优化结果
        
        Args:
            data_count: 使用的数据量
            time_span_days: 数据时间跨度
            metrics: 性能指标字典
            weights_before: 优化前权重
            weights_after: 优化后权重
            notes: 备注
        
        Returns:
            记录ID，如果失败则返回None
        """
        if not self.db:
            return None
        
        try:
            return self.db.add_ml_optimization_result(
                optimization_type='pattern_weight_optimization',
                status='completed',
                data_count=data_count,
                time_span_days=time_span_days,
                metrics_json=json.dumps(metrics, ensure_ascii=False),
                parameters_before=json.dumps(weights_before, ensure_ascii=False),
                parameters_after=json.dumps(weights_after, ensure_ascii=False),
                notes=notes
            )
        except Exception as e:
            print(f"  [ERROR] 记录模式权重优化结果失败: {e}", file=sys.stderr)
            return None
    
    def get_optimization_history(self, optimization_type: str = None,
                                limit: int = 10) -> List[Dict]:
        """
        获取优化历史记录
        
        Args:
            optimization_type: 优化类型过滤（可选）
            limit: 返回数量限制
        
        Returns:
            优化历史记录列表
        """
        if not self.db:
            return []
        
        try:
            results = self.db.get_ml_optimization_results(
                optimization_type=optimization_type,
                limit=limit
            )
            
            # 解析JSON字段
            for result in results:
                if result.get('metrics_json'):
                    try:
                        result['metrics'] = json.loads(result['metrics_json'])
                    except:
                        pass
                if result.get('parameters_before'):
                    try:
                        result['parameters_before'] = json.loads(result['parameters_before'])
                    except:
                        pass
                if result.get('parameters_after'):
                    try:
                        result['parameters_after'] = json.loads(result['parameters_after'])
                    except:
                        pass
                if result.get('improvements_json'):
                    try:
                        result['improvements'] = json.loads(result['improvements_json'])
                    except:
                        pass
            
            return results
        except Exception as e:
            print(f"  [ERROR] 获取优化历史失败: {e}", file=sys.stderr)
            return []
    
    def close(self):
        """关闭连接"""
        if self.db:
            self.db.close()


if __name__ == '__main__':
    # 测试代码
    recorder = OptimizationResultRecorder('abu')
    
    # 测试记录增量学习结果
    test_id = recorder.record_incremental_learning(
        data_count=25,
        time_span_days=3,
        metrics={'win_rate': 45.5, 'avg_profit': 0.8},
        parameters_before={'stop_loss_multiplier': 1.0},
        parameters_after={'stop_loss_multiplier': 1.2},
        improvements=['增加止损距离', '提高盈亏比']
    )
    
    if test_id:
        print(f"✅ 测试记录成功，ID: {test_id}")
    
    # 测试获取历史
    history = recorder.get_optimization_history(limit=5)
    print(f"✅ 获取到 {len(history)} 条历史记录")
    
    recorder.close()
