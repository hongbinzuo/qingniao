#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信号监控和通知系统
实时监控pending信号，当价格接近入场价时及时通知
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from signal_tracker import SignalTracker
except ImportError:
    print("无法导入signal_tracker模块", file=sys.stderr)
    sys.exit(1)

try:
    # 导入价格获取函数
    from generate_btc_de_signals import get_btc_current_price
except ImportError:
    try:
        from get_realtime_stop_loss import get_current_price
        def get_btc_current_price():
            return get_current_price('BTC')
    except ImportError:
        print("无法导入价格获取函数", file=sys.stderr)
        sys.exit(1)


class SignalMonitor:
    """信号监控器"""
    
    def __init__(self, check_interval: int = 900):  # 默认15分钟检查一次
        """
        初始化信号监控器
        
        Args:
            check_interval: 检查间隔（秒），默认900秒（15分钟）
        """
        self.check_interval = check_interval
        base_dir = Path(__file__).parent.parent
        storage_dir = base_dir / "trading_signals" / ".signal_history"
        self.signal_tracker = SignalTracker(storage_dir)
        
        # 通知阈值
        self.warning_distance_pct = 3.0  # 距离入场价3%时提醒
        self.alert_distance_pct = 1.5   # 距离入场价1.5%时强烈提醒
        self.entry_distance_pct = 1.0   # 距离入场价1%时标记为可入场
    
    def get_pending_signals(self) -> List[Dict]:
        """获取所有pending状态的信号"""
        signals_data = self.signal_tracker.load_signals()
        pending_signals = []
        
        for system_name, signals in signals_data.items():
            for signal in signals:
                if signal.get('status') == 'pending':
                    pending_signals.append(signal)
        
        return pending_signals
    
    def check_signal_proximity(self, signal: Dict, current_price: float) -> Dict:
        """
        检查信号价格接近度
        
        Returns:
            {
                'distance_pct': 距离百分比,
                'status': 'far' | 'warning' | 'alert' | 'ready',
                'message': 消息
            }
        """
        entry = signal.get('entry', 0)
        signal_type = signal.get('type', 'long')
        
        if not entry or entry == 0:
            return {'distance_pct': 100, 'status': 'far', 'message': '入场价无效'}
        
        if signal_type == 'long':
            distance = current_price - entry
            distance_pct = (distance / entry) * 100 if entry > 0 else 100
        else:  # short
            distance = entry - current_price
            distance_pct = (distance / entry) * 100 if entry > 0 else 100
        
        if abs(distance_pct) <= self.entry_distance_pct:
            status = 'ready'
            message = f"✅ 价格已接近入场价！距离: {abs(distance_pct):.2f}%"
        elif abs(distance_pct) <= self.alert_distance_pct:
            status = 'alert'
            message = f"⚠️  价格接近入场价！距离: {abs(distance_pct):.2f}%"
        elif abs(distance_pct) <= self.warning_distance_pct:
            status = 'warning'
            message = f"📊 价格正在接近入场价，距离: {abs(distance_pct):.2f}%"
        else:
            status = 'far'
            message = f"距离入场价: {abs(distance_pct):.2f}%"
        
        return {
            'distance_pct': abs(distance_pct),
            'distance': abs(distance),
            'status': status,
            'message': message,
            'direction': 'above' if distance_pct > 0 else 'below'
        }
    
    def format_signal_notification(self, signal: Dict, proximity: Dict, current_price: float) -> str:
        """格式化信号通知消息"""
        signal_type = "做多" if signal.get('type') == 'long' else "做空"
        strength = signal.get('strength', 'medium')
        strength_cn = {'strong': '强', 'medium': '中', 'weak': '弱'}.get(strength, strength)
        
        entry = signal.get('entry', 0)
        stop_loss = signal.get('stop_loss', 0)
        tp1 = signal.get('take_profit_1', 0)
        tp2 = signal.get('take_profit_2', 0)
        
        msg = []
        msg.append("=" * 80)
        msg.append(f"🚨 信号接近提醒")
        msg.append("=" * 80)
        msg.append(f"系统: {signal.get('system', 'unknown').upper()}")
        msg.append(f"时间框架: {signal.get('timeframe', 'unknown')}")
        msg.append(f"信号类型: {signal_type} ({strength_cn})")
        msg.append(f"生成时间: {signal.get('generated_time', 'unknown')}")
        msg.append("")
        msg.append(f"当前价格: ${current_price:,.2f}")
        msg.append(f"入场价: ${entry:,.2f}")
        msg.append(f"{proximity['message']}")
        msg.append("")
        msg.append(f"止损: ${stop_loss:,.2f}")
        msg.append(f"止盈1: ${tp1:,.2f} (50%)")
        msg.append(f"止盈2: ${tp2:,.2f} (50%)")
        msg.append(f"入场模型: {signal.get('entry_model', 'unknown')}")
        if signal.get('reason'):
            msg.append(f"理由: {signal.get('reason', '')}")
        msg.append("=" * 80)
        
        return "\n".join(msg)
    
    def check_and_notify(self) -> List[str]:
        """
        检查所有pending信号并生成通知
        
        Returns:
            通知消息列表
        """
        notifications = []
        
        # 获取当前价格
        try:
            current_price = get_btc_current_price()
            if not current_price:
                return notifications
        except Exception as e:
            print(f"获取价格失败: {e}", file=sys.stderr)
            return notifications
        
        # 获取所有pending信号
        pending_signals = self.get_pending_signals()
        
        if not pending_signals:
            return notifications
        
        # 检查每个信号
        for signal in pending_signals:
            proximity = self.check_signal_proximity(signal, current_price)
            
            # 只通知需要关注的信号（warning, alert, ready）
            if proximity['status'] in ['warning', 'alert', 'ready']:
                notification = self.format_signal_notification(signal, proximity, current_price)
                notifications.append(notification)
        
        return notifications
    
    def save_notifications(self, notifications: List[str]):
        """保存通知到文件"""
        if not notifications:
            return
        
        base_dir = Path(__file__).parent.parent
        output_dir = base_dir / "trading_signals"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        notification_file = output_dir / f"信号提醒_{timestamp}.md"
        
        content = "\n\n".join(notifications)
        notification_file.write_text(content, encoding='utf-8')
        
        print(f"✅ 已保存 {len(notifications)} 条通知到: {notification_file.name}", file=sys.stderr)
    
    def run_once(self):
        """运行一次检查"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查pending信号...", file=sys.stderr)
        
        notifications = self.check_and_notify()
        
        if notifications:
            print(f"⚠️  发现 {len(notifications)} 个信号需要关注！", file=sys.stderr)
            for i, notif in enumerate(notifications, 1):
                print(f"\n通知 {i}/{len(notifications)}:", file=sys.stderr)
                print(notif, file=sys.stderr)
            
            # 保存通知
            self.save_notifications(notifications)
        else:
            print("✓ 暂无需要关注的信号", file=sys.stderr)
    
    def run_continuous(self):
        """持续运行监控"""
        print("=" * 80, file=sys.stderr)
        print("信号监控系统启动", file=sys.stderr)
        print(f"检查间隔: {self.check_interval}秒 ({self.check_interval/60:.1f}分钟)", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        
        try:
            while True:
                self.run_once()
                print(f"\n等待 {self.check_interval}秒后再次检查...\n", file=sys.stderr)
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n\n监控已停止", file=sys.stderr)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='信号监控和通知系统')
    parser.add_argument('--interval', type=int, default=900,
                       help='检查间隔（秒），默认900秒（15分钟）')
    parser.add_argument('--once', action='store_true',
                       help='只运行一次检查，不持续监控')
    
    args = parser.parse_args()
    
    monitor = SignalMonitor(check_interval=args.interval)
    
    if args.once:
        monitor.run_once()
    else:
        monitor.run_continuous()


if __name__ == "__main__":
    main()


