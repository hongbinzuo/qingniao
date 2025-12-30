#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练机器学习模型的独立脚本
用于手动训练或更新模型
"""

import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from signal_tracker import SignalTracker
    from ml_signal_predictor import MLSignalPredictor
except ImportError as e:
    print(f"导入失败: {e}", file=sys.stderr)
    print("请确保在src目录下运行此脚本", file=sys.stderr)
    sys.exit(1)


def main():
    """主函数"""
    print("=" * 80)
    print("机器学习模型训练工具")
    print("=" * 80)
    print()
    
    # 加载信号数据
    print("正在加载信号数据...")
    tracker = SignalTracker()
    signals_data = tracker.load_signals()
    
    if not signals_data:
        print("❌ 未找到信号数据")
        print("提示: 需要先运行系统生成一些信号")
        return
    
    # 统计信号数量
    total_signals = sum(len(signals) for signals in signals_data.values())
    completed_signals = 0
    missed_signals = 0
    for signals in signals_data.values():
        for signal in signals:
            if signal.get('status') in ['stopped', 'full_tp']:
                completed_signals += 1
            elif signal.get('status') == 'missed':
                missed_signals += 1
                completed_signals += 1  # missed状态也计入已完成（用于训练）
    
    print(f"总信号数: {total_signals}")
    print(f"已完成信号数: {completed_signals} (包括 {missed_signals} 个错过信号)")
    print()
    
    if completed_signals < 10:
        print(f"❌ 数据不足：仅{completed_signals}个已完成信号，至少需要10个")
        print("提示: 请等待更多信号完成后再训练")
        return
    
    # 训练模型
    print("正在训练模型...")
    predictor = MLSignalPredictor()
    
    result = predictor.train_model(signals_data)
    
    if 'error' in result:
        print(f"❌ 训练失败: {result['error']}")
        return
    
    # 显示结果
    print()
    print("=" * 80)
    print("训练完成！")
    print("=" * 80)
    print(f"模型准确率: {result['accuracy']:.2%}")
    print(f"训练样本数: {result['train_samples']}")
    print(f"测试样本数: {result['test_samples']}")
    print(f"总样本数: {result['total_samples']}")
    print()
    
    if result.get('feature_importance'):
        print("特征重要性排序:")
        for feature, importance in list(result['feature_importance'].items())[:5]:
            print(f"  - {feature}: {importance:.4f}")
    print()
    print("模型已保存，可以开始使用预测功能")


if __name__ == '__main__':
    main()



