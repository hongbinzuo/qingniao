#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录信号评估结果到交易记录系统
"""

import sys
from datetime import datetime
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from signal_tracker import SignalTracker
    SIGNAL_TRACKER_AVAILABLE = True
except ImportError:
    SIGNAL_TRACKER_AVAILABLE = False
    print("警告: 无法导入signal_tracker模块", file=sys.stderr)

def record_evaluated_signals(evaluation_results: list):
    """
    将评估结果记录到交易记录系统
    
    Args:
        evaluation_results: 评估结果列表，每个元素包含：
            - signal_time: 信号生成时间
            - timeframe: 时间框架
            - type: 信号类型 (long/short)
            - entry: 入场价
            - stop_loss: 止损价
            - take_profit_1: 第一止盈价
            - take_profit_2: 第二止盈价
            - model: 入场模型
            - strength: 信号强度
            - status: 结果状态 (full_tp/partial_tp/stopped/open)
            - max_profit: 最大浮盈百分比
            - max_loss: 最大浮亏百分比
            - current_price: 当前价格
            - current_pnl_pct: 当前盈亏百分比
    """
    if not SIGNAL_TRACKER_AVAILABLE:
        print("⚠️ 信号追踪器不可用，无法记录", file=sys.stderr)
        return
    
    tracker = SignalTracker()
    signals_data = tracker.load_signals()
    
    recorded_count = 0
    
    for result in evaluation_results:
        # 确定系统名称
        system_name = 'de'  # 默认使用de系统
        
        # 创建信号记录
        signal_time_str = result['signal_time']
        signal_id = f"{system_name}_{result['timeframe']}_{signal_time_str.replace(':', '-').replace(' ', '_')}"
        
        # 确定最终状态
        status = result['status']
        if status == 'full_tp':
            final_status = 'full_tp'
        elif status == 'partial_tp':
            final_status = 'partial_tp'
        elif status == 'stopped':
            final_status = 'stopped'
        else:
            final_status = 'open'
        
        # 计算完成时间（使用当前时间）
        completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        signal_record = {
            'id': signal_id,
            'system': system_name,
            'timeframe': result['timeframe'],
            'generated_time': signal_time_str,
            'status': final_status,
            'type': result['type'],
            'entry': result['entry'],
            'stop_loss': result['stop_loss'],
            'take_profit_1': result.get('take_profit_1'),
            'take_profit_2': result.get('take_profit_2'),
            'entry_model': result.get('model', 'unknown'),
            'reason': '',
            'strength': result.get('strength', 'medium'),
            # 追踪字段
            'last_check_time': completion_time,
            'entry_time': signal_time_str,  # 假设信号生成时即入场
            'current_price': result.get('current_price', result['entry']),
            'max_profit': result.get('max_profit', 0),
            'max_loss': result.get('max_loss', 0),
            'tp1_hit': result.get('reached_tp1', False),
            'tp2_hit': result.get('reached_tp2', False),
            'stop_hit': result.get('hit_stop_loss', False),
            'analyzed': False,  # 标记为未分析，等待性能分析
        }
        
        # 初始化系统信号列表
        if system_name not in signals_data:
            signals_data[system_name] = []
        
        # 检查是否已存在（避免重复）
        existing_ids = [s['id'] for s in signals_data[system_name]]
        if signal_id not in existing_ids:
            signals_data[system_name].append(signal_record)
            recorded_count += 1
            print(f"✅ 已记录信号: {signal_id} ({final_status})", file=sys.stderr)
        else:
            print(f"⚠️ 信号已存在: {signal_id}，跳过", file=sys.stderr)
    
    # 保存
    if recorded_count > 0:
        tracker.save_signals(signals_data)
        print(f"\n✅ 共记录 {recorded_count} 个信号到交易记录系统", file=sys.stderr)
        print(f"💡 提示: 可以运行以下命令进行性能分析:", file=sys.stderr)
        print(f"   python src/train_ml_model.py", file=sys.stderr)
    else:
        print(f"\n⚠️ 没有新信号需要记录", file=sys.stderr)

if __name__ == "__main__":
    # 从评估结果创建记录
    # 这里需要从评估报告或评估结果中读取
    print("请使用 evaluate_signal_results.py 生成评估结果，然后调用此脚本记录", file=sys.stderr)


