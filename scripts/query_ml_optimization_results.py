#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查询机器学习优化结果
方便查看历史优化记录
"""

import sys
from pathlib import Path
from datetime import datetime
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ml_dl.optimization_result_recorder import OptimizationResultRecorder


def print_optimization_result(result: dict):
    """打印优化结果"""
    print("=" * 80)
    print(f"优化类型: {result.get('optimization_type', 'N/A')}")
    print(f"优化时间: {result.get('optimization_time', 'N/A')}")
    print(f"状态: {result.get('status', 'N/A')}")
    print(f"数据量: {result.get('data_count', 'N/A')} 条")
    print(f"时间跨度: {result.get('time_span_days', 'N/A')} 天")
    print()
    
    # 性能指标
    if result.get('metrics'):
        print("性能指标:")
        metrics = result['metrics']
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"  - {key}: {value:.2f}")
            else:
                print(f"  - {key}: {value}")
        print()
    
    # 参数变化
    if result.get('parameters_before') and result.get('parameters_after'):
        print("参数变化:")
        params_before = result['parameters_before']
        params_after = result['parameters_after']
        
        # 找出变化的参数
        all_keys = set(params_before.keys()) | set(params_after.keys())
        for key in sorted(all_keys):
            before_val = params_before.get(key, 'N/A')
            after_val = params_after.get(key, 'N/A')
            if before_val != after_val:
                print(f"  - {key}: {before_val} → {after_val}")
        print()
    
    # 改进建议
    if result.get('improvements'):
        print("改进建议:")
        for improvement in result['improvements']:
            print(f"  - {improvement}")
        print()
    
    # 文件路径
    if result.get('model_file_path'):
        print(f"模型文件: {result['model_file_path']}")
    if result.get('report_file_path'):
        print(f"报告文件: {result['report_file_path']}")
    
    # 备注
    if result.get('notes'):
        print(f"备注: {result['notes']}")
    
    print()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='查询机器学习优化结果')
    parser.add_argument('--type', type=str, help='优化类型过滤（incremental_learning, ml_training, full_retrain, parameter_optimization, pattern_weight_optimization）')
    parser.add_argument('--limit', type=int, default=10, help='返回数量限制（默认10）')
    parser.add_argument('--trader', type=str, default='abu', help='交易员ID（默认abu）')
    parser.add_argument('--latest', action='store_true', help='只显示最新的优化结果')
    
    args = parser.parse_args()
    
    recorder = OptimizationResultRecorder(args.trader)
    
    try:
        if args.latest:
            # 只显示最新的
            result = recorder.db.get_latest_optimization_result(optimization_type=args.type)
            if result:
                # 解析JSON字段
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
                
                print_optimization_result(result)
            else:
                print("❌ 未找到优化结果")
        else:
            # 显示历史记录
            history = recorder.get_optimization_history(
                optimization_type=args.type,
                limit=args.limit
            )
            
            if not history:
                print("❌ 未找到优化结果")
                return
            
            print(f"找到 {len(history)} 条优化记录\n")
            
            for i, result in enumerate(history, 1):
                print(f"【记录 {i}/{len(history)}】")
                print_optimization_result(result)
    
    finally:
        recorder.close()


if __name__ == '__main__':
    main()
