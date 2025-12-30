#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号状态追踪模块
追踪每个交易信号的状态：挂单中、交易中、已止损、已部分止盈、已全部止盈
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import os

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class SignalTracker:
    """信号状态追踪器"""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        初始化信号追踪器
        
        Args:
            storage_dir: 信号存储目录，默认使用 trading_signals/.signal_history
        """
        if storage_dir is None:
            base_dir = Path(__file__).parent.parent
            storage_dir = base_dir / "trading_signals" / ".signal_history"
        
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 信号存储文件：按日期和系统分类
        self.signals_file = self.storage_dir / "signals.json"
    
    def load_signals(self) -> Dict[str, List[Dict]]:
        """加载历史信号"""
        if not self.signals_file.exists():
            return {}
        
        try:
            with open(self.signals_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"加载历史信号失败: {e}", file=sys.stderr)
            return {}
    
    def save_signals(self, signals_data: Dict[str, List[Dict]]):
        """保存信号数据"""
        try:
            with open(self.signals_file, 'w', encoding='utf-8') as f:
                json.dump(signals_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存信号失败: {e}", file=sys.stderr)
    
    def add_signal(self, system_name: str, timeframe: str, signal: Dict, 
                   generated_time: Optional[str] = None):
        """
        添加新信号
        
        Args:
            system_name: 系统名称（如 'de', 'meng'）
            timeframe: 时间框架（如 '5分钟', '15分钟'）
            signal: 信号数据
            generated_time: 生成时间，默认使用当前时间
        """
        if generated_time is None:
            generated_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        signals_data = self.load_signals()
        
        # 创建信号记录
        signal_id = f"{system_name}_{timeframe}_{generated_time.replace(':', '-').replace(' ', '_')}"
        
        signal_record = {
            'id': signal_id,
            'system': system_name,
            'timeframe': timeframe,
            'generated_time': generated_time,
            'status': 'pending',  # pending: 挂单中, active: 交易中, stopped: 已止损, partial_tp: 已部分止盈, full_tp: 已全部止盈
            'type': signal.get('type', 'unknown'),  # 'long' or 'short'
            'entry': signal.get('entry', 0),
            'stop_loss': signal.get('stop_loss', 0),
            'take_profit_1': signal.get('take_profit_1', 0),
            'take_profit_2': signal.get('take_profit_2', 0),
            'entry_model': signal.get('entry_model', '未知模型'),
            'reason': signal.get('reason', ''),
            'strength': signal.get('strength', 'medium'),
            # 追踪字段
            'last_check_time': generated_time,
            'entry_time': None,  # 实际入场时间
            'current_price': None,  # 最新价格
            'max_profit': None,  # 最大浮盈（百分比）
            'max_loss': None,  # 最大浮亏（百分比）
            'tp1_hit': False,  # 是否触及第一止盈位
            'tp2_hit': False,  # 是否触及第二止盈位
            'stop_hit': False,  # 是否触及止损位
        }
        
        # 初始化系统信号列表
        if system_name not in signals_data:
            signals_data[system_name] = []
        
        # 添加信号
        signals_data[system_name].append(signal_record)
        
        # 保存
        self.save_signals(signals_data)
        
        return signal_id
    
    def update_signal_status(self, current_price: float) -> Dict[str, List[Dict]]:
        """
        更新所有信号的状态
        
        Args:
            current_price: 当前价格
        
        Returns:
            更新后的信号数据（按状态分类）
        """
        signals_data = self.load_signals()
        updated_signals = {'pending': [], 'active': [], 'stopped': [], 'partial_tp': [], 'full_tp': []}
        
        for system_name, signals in signals_data.items():
            for signal in signals:
                if signal.get('status') in ['stopped', 'full_tp']:
                    # 已结束的信号，不再更新
                    updated_signals[signal['status']].append(signal)
                    continue
                
                # 更新最新价格和检查时间
                signal['current_price'] = current_price
                signal['last_check_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 判断状态
                status = self._determine_status(signal, current_price)
                signal['status'] = status
                
                # 计算浮盈浮亏
                if signal.get('entry_time'):
                    # 已入场，计算浮盈浮亏
                    entry = signal['entry']
                    if signal['type'] == 'long':
                        profit_pct = ((current_price - entry) / entry) * 100
                    else:  # short
                        profit_pct = ((entry - current_price) / entry) * 100
                    
                    # 更新最大浮盈/浮亏
                    if signal['max_profit'] is None or profit_pct > signal['max_profit']:
                        signal['max_profit'] = profit_pct
                    if signal['max_loss'] is None or profit_pct < signal['max_loss']:
                        signal['max_loss'] = profit_pct
                
                updated_signals[status].append(signal)
        
        # 保存更新后的数据
        self.save_signals(signals_data)
        
        return updated_signals
    
    def _determine_status(self, signal: Dict, current_price: float) -> str:
        """
        判断信号状态
        
        Args:
            signal: 信号数据
            current_price: 当前价格
        
        Returns:
            状态字符串
        """
        status = signal.get('status', 'pending')
        entry = signal.get('entry', 0)
        stop_loss = signal.get('stop_loss', 0)
        tp1 = signal.get('take_profit_1', 0)
        tp2 = signal.get('take_profit_2', 0)
        signal_type = signal.get('type', 'long')
        entry_time = signal.get('entry_time')
        
        if not entry or not stop_loss or not tp1 or not tp2:
            return status
        
        # 检查是否已入场（价格接近入场价，或已标记为入场）
        if status == 'pending':
            # 判断是否已经入场（价格接近入场价1%以内）
            price_diff_pct = abs(current_price - entry) / entry * 100 if entry > 0 else 100
            if price_diff_pct < 1.0:
                # 标记为已入场
                signal['entry_time'] = signal['entry_time'] or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                status = 'active'
        
        if status == 'pending':
            return 'pending'
        
        # 已入场，检查止损和止盈
        if signal_type == 'long':
            # 做多：检查止损（价格低于止损位）
            if current_price <= stop_loss and not signal.get('stop_hit'):
                signal['stop_hit'] = True
                return 'stopped'
            
            # 检查止盈（价格高于止盈位）
            if current_price >= tp2:
                if not signal.get('tp2_hit'):
                    signal['tp2_hit'] = True
                return 'full_tp'
            elif current_price >= tp1:
                if not signal.get('tp1_hit'):
                    signal['tp1_hit'] = True
                return 'partial_tp'
        
        else:  # short
            # 做空：检查止损（价格高于止损位）
            if current_price >= stop_loss and not signal.get('stop_hit'):
                signal['stop_hit'] = True
                return 'stopped'
            
            # 检查止盈（价格低于止盈位）
            if current_price <= tp2:
                if not signal.get('tp2_hit'):
                    signal['tp2_hit'] = True
                return 'full_tp'
            elif current_price <= tp1:
                if not signal.get('tp1_hit'):
                    signal['tp1_hit'] = True
                return 'partial_tp'
        
        # 其他情况，保持active状态
        return 'active'
    
    def get_active_signals(self, system_name: Optional[str] = None) -> List[Dict]:
        """
        获取活跃信号（挂单中或交易中）
        
        Args:
            system_name: 系统名称，如果为None则返回所有系统的信号
        """
        signals_data = self.load_signals()
        active_signals = []
        
        for sys_name, signals in signals_data.items():
            if system_name and sys_name != system_name:
                continue
            
            for signal in signals:
                status = signal.get('status', 'pending')
                if status in ['pending', 'active', 'partial_tp']:
                    active_signals.append(signal)
        
        return active_signals
    
    def format_signal_status_report(self, signals_by_status: Dict[str, List[Dict]]) -> List[str]:
        """
        格式化信号状态报告
        
        Args:
            signals_by_status: 按状态分类的信号数据
        
        Returns:
            报告行列表
        """
        report = []
        
        # 统计
        total_pending = len(signals_by_status.get('pending', []))
        total_active = len(signals_by_status.get('active', []))
        total_partial_tp = len(signals_by_status.get('partial_tp', []))
        total_stopped = len(signals_by_status.get('stopped', []))
        total_full_tp = len(signals_by_status.get('full_tp', []))
        
        report.append("## 历史信号状态追踪")
        report.append("")
        report.append(f"**统计**: 挂单中 {total_pending} | 交易中 {total_active} | 部分止盈 {total_partial_tp} | 已止损 {total_stopped} | 全部止盈 {total_full_tp}")
        report.append("")
        
        # 挂单中
        if signals_by_status.get('pending'):
            report.append("### 🔵 挂单中")
            report.append("")
            for signal in signals_by_status['pending'][:10]:  # 最多显示10个
                direction = "做多" if signal['type'] == 'long' else "做空"
                report.append(f"- **{signal['system']} {signal['timeframe']}** {direction} ({signal['strength']})")
                report.append(f"  - 入场: ${signal['entry']:,.0f} | 止损: ${signal['stop_loss']:,.0f} | 止盈1: ${signal['take_profit_1']:,.0f} | 止盈2: ${signal['take_profit_2']:,.0f}")
                report.append(f"  - 模型: {signal['entry_model']}")
                report.append(f"  - 生成时间: {signal['generated_time']}")
                report.append("")
        
        # 交易中
        if signals_by_status.get('active'):
            report.append("### 🟢 交易中")
            report.append("")
            for signal in signals_by_status['active'][:10]:  # 最多显示10个
                direction = "做多" if signal['type'] == 'long' else "做空"
                current_price = signal.get('current_price', 0)
                entry = signal['entry']
                
                # 计算当前浮盈浮亏
                if signal['type'] == 'long':
                    profit_pct = ((current_price - entry) / entry) * 100 if entry > 0 else 0
                else:
                    profit_pct = ((entry - current_price) / entry) * 100 if entry > 0 else 0
                
                profit_symbol = "📈" if profit_pct > 0 else "📉"
                report.append(f"- **{signal['system']} {signal['timeframe']}** {direction} ({signal['strength']}) {profit_symbol} {profit_pct:+.2f}%")
                report.append(f"  - 入场: ${entry:,.0f} | 当前: ${current_price:,.0f} | 止损: ${signal['stop_loss']:,.0f} | 止盈1: ${signal['take_profit_1']:,.0f} | 止盈2: ${signal['take_profit_2']:,.0f}")
                report.append(f"  - 模型: {signal['entry_model']}")
                if signal.get('entry_time'):
                    report.append(f"  - 入场时间: {signal['entry_time']}")
                report.append("")
        
        # 部分止盈
        if signals_by_status.get('partial_tp'):
            report.append("### 🟡 部分止盈")
            report.append("")
            for signal in signals_by_status['partial_tp'][:10]:
                direction = "做多" if signal['type'] == 'long' else "做空"
                report.append(f"- **{signal['system']} {signal['timeframe']}** {direction} ({signal['strength']})")
                report.append(f"  - 入场: ${signal['entry']:,.0f} | 止损: ${signal['stop_loss']:,.0f} | 止盈1: ${signal['take_profit_1']:,.0f} ✅ | 止盈2: ${signal['take_profit_2']:,.0f}")
                report.append(f"  - 模型: {signal['entry_model']}")
                report.append("")
        
        # 已止损
        if signals_by_status.get('stopped'):
            recent_stopped = sorted(signals_by_status['stopped'], 
                                   key=lambda x: x.get('last_check_time', ''), 
                                   reverse=True)[:5]  # 最近5个
            report.append("### 🔴 已止损（最近5个）")
            report.append("")
            for signal in recent_stopped:
                direction = "做多" if signal['type'] == 'long' else "做空"
                max_loss = signal.get('max_loss', 0)
                report.append(f"- **{signal['system']} {signal['timeframe']}** {direction} | 最大浮亏: {max_loss:.2f}%")
                report.append(f"  - 入场: ${signal['entry']:,.0f} | 止损: ${signal['stop_loss']:,.0f}")
                report.append(f"  - 模型: {signal['entry_model']} | 生成时间: {signal['generated_time']}")
                report.append("")
        
        # 全部止盈
        if signals_by_status.get('full_tp'):
            recent_full_tp = sorted(signals_by_status['full_tp'], 
                                   key=lambda x: x.get('last_check_time', ''), 
                                   reverse=True)[:5]  # 最近5个
            report.append("### ✅ 全部止盈（最近5个）")
            report.append("")
            for signal in recent_full_tp:
                direction = "做多" if signal['type'] == 'long' else "做空"
                max_profit = signal.get('max_profit', 0)
                report.append(f"- **{signal['system']} {signal['timeframe']}** {direction} | 最大浮盈: {max_profit:.2f}%")
                report.append(f"  - 入场: ${signal['entry']:,.0f} | 止盈1: ${signal['take_profit_1']:,.0f} ✅ | 止盈2: ${signal['take_profit_2']:,.0f} ✅")
                report.append(f"  - 模型: {signal['entry_model']} | 生成时间: {signal['generated_time']}")
                report.append("")
        
        return report
    
    def mark_signals_as_analyzed(self, signal_ids: List[str]):
        """
        标记信号已被分析（避免重复分析）
        
        Args:
            signal_ids: 信号ID列表
        """
        signals_data = self.load_signals()
        for system_name, signals in signals_data.items():
            for signal in signals:
                if signal.get('id') in signal_ids:
                    signal['analyzed'] = True
        self.save_signals(signals_data)
    
    def get_unanalyzed_completed_signals(self) -> List[Dict]:
        """
        获取未分析的已完成信号
        
        Returns:
            未分析的已完成信号列表
        """
        signals_data = self.load_signals()
        unanalyzed = []
        for system_name, signals in signals_data.items():
            for signal in signals:
                if (signal.get('status') in ['stopped', 'full_tp'] and 
                    not signal.get('analyzed', False)):
                    unanalyzed.append(signal)
        return unanalyzed
    
    def mark_signals_as_analyzed(self, signal_ids: List[str]):
        """
        标记信号已被分析（避免重复分析）
        
        Args:
            signal_ids: 信号ID列表
        """
        signals_data = self.load_signals()
        for system_name, signals in signals_data.items():
            for signal in signals:
                if signal.get('id') in signal_ids:
                    signal['analyzed'] = True
        self.save_signals(signals_data)
    
    def get_unanalyzed_completed_signals(self) -> List[Dict]:
        """
        获取未分析的已完成信号
        
        Returns:
            未分析的已完成信号列表
        """
        signals_data = self.load_signals()
        unanalyzed = []
        for system_name, signals in signals_data.items():
            for signal in signals:
                if (signal.get('status') in ['stopped', 'full_tp'] and 
                    not signal.get('analyzed', False)):
                    unanalyzed.append(signal)
        return unanalyzed

