#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
青鸟交易系统管理器
整合De.交易系统和梦多空策略
"""

import sys
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 获取当前文件所在目录
CURRENT_DIR = Path(__file__).parent

# 导入信号追踪模块
try:
    from signal_tracker import SignalTracker
    SIGNAL_TRACKER_AVAILABLE = True
except ImportError as e:
    SIGNAL_TRACKER_AVAILABLE = False
    print(f"警告: 无法导入信号追踪模块 ({e})", file=sys.stderr)

# 导入信号性能分析模块
try:
    from signal_performance_analyzer import SignalPerformanceAnalyzer
    PERFORMANCE_ANALYZER_AVAILABLE = True
except ImportError as e:
    PERFORMANCE_ANALYZER_AVAILABLE = False
    print(f"警告: 无法导入信号性能分析模块 ({e})", file=sys.stderr)

# 导入机器学习预测模块
try:
    from ml_signal_predictor import MLSignalPredictor
    ML_PREDICTOR_AVAILABLE = True
except ImportError as e:
    ML_PREDICTOR_AVAILABLE = False
    print(f"提示: 机器学习模块未安装 ({e})，如需使用请安装: pip install scikit-learn pandas", file=sys.stderr)


def import_module_from_path(module_name: str, file_path: Path):
    """动态导入模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UnifiedTradingSystem:
    """青鸟交易系统管理器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        # 创建输出目录
        self.output_dir = self.base_dir / "trading_signals"
        self.output_dir.mkdir(exist_ok=True)
        
        # 初始化信号追踪器
        if SIGNAL_TRACKER_AVAILABLE:
            storage_dir = self.base_dir / "trading_signals" / ".signal_history"
            self.signal_tracker = SignalTracker(storage_dir)
        else:
            self.signal_tracker = None
        
        # 初始化机器学习预测器
        if ML_PREDICTOR_AVAILABLE:
            self.ml_predictor = MLSignalPredictor()
        else:
            self.ml_predictor = None
        
        # 动态导入梦多空策略模块
        meng_module_path = CURRENT_DIR / "scan_meng_duo_kong_strategy.py"
        self.meng_module = import_module_from_path("meng_strategy", meng_module_path)
        
        # 动态导入De.交易系统模块
        de_module_path = CURRENT_DIR / "generate_btc_de_signals.py"
        self.de_module = import_module_from_path("de_strategy", de_module_path)
    
    def run_de_system(self, symbol: str = 'BTC') -> Optional[Path]:
        """
        运行De.交易系统（分析单个币种）
        
        Args:
            symbol: 币种符号，默认BTC
        
        Returns:
            生成的交易计划文件路径
        """
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"运行De.交易系统 - 分析 {symbol}", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)
        
        try:
            if symbol.upper() == 'BTC':
                # 临时修改工作目录到输出目录，让De.系统将文件保存到指定目录
                original_cwd = Path.cwd()
                import os
                os.chdir(self.output_dir)
                
                try:
                    # 调用De.系统的BTC分析函数
                    self.de_module.generate_trading_plan()
                finally:
                    # 恢复原始工作目录
                    os.chdir(original_cwd)
                
                # 查找最新生成的BTC信号文件（在输出目录中）
                de_file = self._find_latest_file('BTC_de_signals_*.md')
                
                # 提取并追踪信号
                if de_file and self.signal_tracker:
                    self._extract_and_track_de_signals(de_file)
                
                return de_file
            else:
                print(f"⚠️  暂不支持 {symbol} 的分析，仅支持 BTC", file=sys.stderr)
                return None
        except Exception as e:
            print(f"❌ De.系统运行失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None
    
    def run_meng_system(self, exchange: str = 'auto', limit: int = 100) -> Optional[Path]:
        """
        运行梦多空策略（扫描涨幅榜）
        
        Args:
            exchange: 交易所，默认auto
            limit: 扫描币种数，默认100
        
        Returns:
            生成的交易计划文件路径
        """
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"运行梦多空策略 - 扫描涨幅榜", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)
        
        try:
            # 修改梦多空策略模块的输出目录
            original_output_dir = getattr(self.meng_module, 'OUTPUT_DIR', None)
            
            # 临时修改输出目录（如果模块支持）
            # 由于scan_and_generate_plan函数内部使用了硬编码的路径
            # 我们需要在调用前修改它的工作目录
            original_cwd = Path.cwd()
            import os
            os.chdir(self.output_dir)
            
            try:
                # 调用梦多空策略的扫描函数
                output_file = self.meng_module.scan_and_generate_plan(exchange, limit)
            finally:
                # 恢复原始工作目录
                os.chdir(original_cwd)
            
            if output_file and isinstance(output_file, Path):
                # 如果文件已经在输出目录，直接返回
                if output_file.parent == self.output_dir:
                    return output_file
                # 否则移动到输出目录
                target_file = self.output_dir / output_file.name
                if output_file.exists():
                    output_file.rename(target_file)
                    return target_file
                return output_file
            elif output_file and isinstance(output_file, str):
                output_path = Path(output_file)
                # 如果文件已经在输出目录，直接返回
                if output_path.parent == self.output_dir:
                    return output_path
                # 否则移动到输出目录
                target_file = self.output_dir / output_path.name
                if output_path.exists():
                    output_path.rename(target_file)
                    return target_file
                return output_path
            else:
                # 如果返回None，尝试查找最新文件
                return self._find_latest_file('梦多空策略_交易计划_*.md')
        except Exception as e:
            print(f"❌ 梦多空策略运行失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None
    
    def run_all_systems(self, exchange: str = 'auto', limit: int = 100, 
                            de_symbol: str = 'BTC') -> List[Path]:
        """
        运行所有交易系统
            
            Args:
                exchange: 交易所，默认auto
                limit: 扫描币种数，默认100
                de_symbol: De.系统分析的币种，默认BTC
            
        Returns:
            生成的交易计划文件路径列表
        """
        files = []
        
        print(f"\n{'='*80}", file=sys.stderr)
        print("青鸟交易系统 - 运行所有系统", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
        
        # 获取当前价格（用于信号状态更新）
        current_price = None
        try:
            current_price = self.de_module.get_btc_current_price()
            if current_price:
                print(f"当前价格: ${current_price:,.2f}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  获取当前价格失败: {e}", file=sys.stderr)
        
        # 0. 更新历史信号状态
        if self.signal_tracker and current_price:
            print(f"\n[0/3] 更新历史信号状态...", file=sys.stderr)
            status_report = self.update_signal_status(current_price)
            if status_report:
                # 将状态报告保存到文件
                status_file = self.output_dir / f"信号状态_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                status_file.write_text('\n'.join(status_report), encoding='utf-8')
                print(f"✓ 信号状态已更新: {status_file.name}", file=sys.stderr)
        
        # 1. 运行De.系统
        print(f"\n[1/3] 运行De.交易系统（{de_symbol}）...", file=sys.stderr)
        de_file = self.run_de_system(de_symbol)
        if de_file:
            files.append(de_file)
            print(f"✓ De.系统完成: {de_file.name}", file=sys.stderr)
        else:
            print("⚠️  De.系统未生成文件", file=sys.stderr)
        
        # 2. 运行梦多空策略
        print(f"\n[2/4] 运行梦多空策略（交易所: {exchange}, 币种数: {limit}）...", file=sys.stderr)
        meng_file = self.run_meng_system(exchange, limit)
        if meng_file:
            files.append(meng_file)
            print(f"✓ 梦多空策略完成: {meng_file.name}", file=sys.stderr)
        else:
            print("⚠️  梦多空策略未生成文件", file=sys.stderr)
        
        # 3. 生成综合状态报告
        if self.signal_tracker and current_price:
            print(f"\n[3/4] 生成综合状态报告...", file=sys.stderr)
            status_report = self.update_signal_status(current_price)
            if status_report:
                # 将状态报告追加到最新生成的文件中
                if files:
                    latest_file = files[-1]
                    existing_content = latest_file.read_text(encoding='utf-8')
                    status_content = '\n\n---\n\n' + '\n'.join(status_report)
                    latest_file.write_text(existing_content + status_content, encoding='utf-8')
                    print(f"✓ 综合状态报告已添加到: {latest_file.name}", file=sys.stderr)
        
        # 4. 分析已完成信号并生成改进建议
        if self.signal_tracker and PERFORMANCE_ANALYZER_AVAILABLE:
            print(f"\n[4/4] 分析已完成信号性能...", file=sys.stderr)
            self.analyze_and_generate_suggestions()
        
        print(f"\n{'='*80}", file=sys.stderr)
        print("所有系统运行完成！", file=sys.stderr)
        print(f"生成了 {len(files)} 个交易计划文件:", file=sys.stderr)
        for f in files:
            print(f"  - {f.name}", file=sys.stderr)
        print(f"{'='*80}", file=sys.stderr)
        
        return files
    
    def _find_latest_file(self, pattern: str) -> Optional[Path]:
        """查找最新生成的文件（在输出目录中）"""
        files = list(self.output_dir.glob(pattern))
        if files:
            return max(files, key=lambda p: p.stat().st_mtime)
        return None
    
    def _extract_and_track_de_signals(self, signal_file: Path):
        """
        从De.系统生成的信号文件中提取信号并添加到追踪器
        
        Args:
            signal_file: 信号文件路径
        """
        if not self.signal_tracker or not signal_file.exists():
            return
        
        try:
            # 尝试从De.系统模块获取最新分析结果
            try:
                import importlib
                import generate_btc_de_signals
                importlib.reload(generate_btc_de_signals)
                if hasattr(generate_btc_de_signals, '_last_analysis_result'):
                    analysis_result = generate_btc_de_signals._last_analysis_result
                    if analysis_result:
                        for tf_name, tf_data in analysis_result.items():
                            if isinstance(tf_data, dict) and 'signals' in tf_data and tf_data['signals']:
                                # 选择最强的信号
                                best_signal = max(tf_data['signals'], 
                                                 key=lambda x: 3 if x.get('strength') == 'strong' else 2 if x.get('strength') == 'medium' else 1)
                                signal_id = self.signal_tracker.add_signal('de', tf_name, best_signal)
                                
                                # 信号生成后立即检查价格接近度并通知
                                try:
                                    current_price = self.de_module.get_btc_current_price()
                                    if current_price:
                                        from signal_monitor import SignalMonitor
                                        monitor = SignalMonitor()
                                        proximity = monitor.check_signal_proximity(best_signal, current_price)
                                        
                                        # 强信号或价格接近时立即通知
                                        if (best_signal.get('strength') == 'strong' or 
                                            proximity['status'] in ['warning', 'alert', 'ready']):
                                            notification = monitor.format_signal_notification(
                                                best_signal, proximity, current_price
                                            )
                                            monitor.save_notifications([notification])
                                            print(f"  ✓ 已生成信号接近提醒", file=sys.stderr)
                                except Exception as e:
                                    print(f"  ⚠️  生成信号提醒失败: {e}", file=sys.stderr)
            except Exception as e:
                print(f"  ⚠️  提取De.系统信号失败: {e}", file=sys.stderr)
        except Exception as e:
            print(f"提取信号失败: {e}", file=sys.stderr)
    
    def update_signal_status(self, current_price: float) -> Optional[List[str]]:
        """
        更新所有信号的状态
        
        Args:
            current_price: 当前价格
        
        Returns:
            状态报告行列表，如果追踪器不可用则返回None
        """
        if not self.signal_tracker:
            return None
        
        try:
            signals_by_status = self.signal_tracker.update_signal_status(current_price)
            report = self.signal_tracker.format_signal_status_report(signals_by_status)
            return report
        except Exception as e:
            print(f"更新信号状态失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return None
    
    def analyze_and_generate_suggestions(self):
        """
        分析已完成信号的性能并生成改进建议报告
        """
        if not self.signal_tracker or not PERFORMANCE_ANALYZER_AVAILABLE:
            return
        
        try:
            # 获取信号数据
            signals_data = self.signal_tracker.load_signals()
            if not signals_data:
                print("  ℹ️  暂无信号数据", file=sys.stderr)
                return
            
            # 创建分析器
            analyzer = SignalPerformanceAnalyzer(signals_data)
            
            # 分析已完成信号
            analysis = analyzer.analyze_completed_signals()
            
            if analysis['total_completed'] == 0:
                print("  ℹ️  暂无已完成的信号", file=sys.stderr)
                return
            
            # 生成改进建议
            suggestions = analyzer.generate_improvement_suggestions(analysis)
            
            # 格式化报告
            report = analyzer.format_analysis_report(analysis, suggestions)
            
            # 保存到文件（单独的报告）
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_file = self.output_dir / f"信号性能分析_{timestamp}.md"
            report_file.write_text(report, encoding='utf-8')
            print(f"  ✓ 性能分析报告已保存: {report_file.name}", file=sys.stderr)
            
            # 追加到总改进建议文档（整合所有改进建议）
            consolidated_file = self.output_dir / "系统改进建议汇总.md"
            self._append_to_consolidated_suggestions(consolidated_file, report, timestamp)
            print(f"  ✓ 改进建议已追加到: {consolidated_file.name}", file=sys.stderr)
            
            # 标记信号已分析
            completed_signal_ids = [s['id'] for s in analysis['completed_signals'] 
                                   if not s.get('analyzed', False)]
            if completed_signal_ids:
                self.signal_tracker.mark_signals_as_analyzed(completed_signal_ids)
            
            # 5. 提示ML模型训练（如果有足够的数据）
            if self.ml_predictor and analysis['total_completed'] >= 10:
                if not self.ml_predictor.is_trained:
                    print(f"  💡 检测到{analysis['total_completed']}个已完成信号，可以训练ML模型", file=sys.stderr)
                    print(f"  💡 运行命令训练: cd src && python train_ml_model.py", file=sys.stderr)
            
        except Exception as e:
            print(f"  ❌ 分析信号性能失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
    
    def _append_to_consolidated_suggestions(self, consolidated_file: Path, new_report: str, timestamp: str):
        """
        将新的改进建议追加到总改进建议文档
        
        Args:
            consolidated_file: 总改进建议文件路径
            new_report: 新的分析报告内容
            timestamp: 时间戳
        """
        separator = f"\n\n{'='*80}\n\n"
        timestamp_header = f"## 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (ID: {timestamp})\n\n"
        
        if consolidated_file.exists():
            # 读取现有内容
            existing_content = consolidated_file.read_text(encoding='utf-8')
            # 追加新内容（最新的在最前面）
            new_content = timestamp_header + new_report + separator + existing_content
        else:
            # 创建新文件
            header = "# 系统改进建议汇总\n\n"
            header += "本文档整合所有性能分析报告的改进建议，按时间倒序排列（最新的在最前面）\n\n"
            header += "---\n\n"
            new_content = header + timestamp_header + new_report
        
        consolidated_file.write_text(new_content, encoding='utf-8')


def run_periodic_all_systems(interval_hours: int = 2, exchange: str = 'auto', 
                             limit: int = 100, de_symbol: str = 'BTC'):
    """
    周期性运行所有系统（每N小时）
    
    Args:
        interval_hours: 扫描间隔（小时）
        exchange: 交易所
        limit: 扫描币种数
        de_symbol: De.系统分析的币种
    """
    import time
    
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"青鸟交易系统 - 定时运行模式", file=sys.stderr)
    print(f"{'='*80}", file=sys.stderr)
    print(f"运行间隔: 每 {interval_hours} 小时", file=sys.stderr)
    print(f"按 Ctrl+C 停止", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    interval_seconds = interval_hours * 3600
    system = UnifiedTradingSystem()
    
    try:
        while True:
            print(f"\n{'='*80}", file=sys.stderr)
            print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
            print(f"{'='*80}", file=sys.stderr)
            
            # 运行所有系统
            system.run_all_systems(exchange, limit, de_symbol)
            
            print(f"\n{'='*80}", file=sys.stderr)
            print(f"下次运行将在 {interval_hours} 小时后...", file=sys.stderr)
            print(f"{'='*80}\n", file=sys.stderr)
            
            time.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        print("\n定时运行已停止", file=sys.stderr)


def main():
    """主函数 - 命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='青鸟交易系统 - 整合De.交易系统和梦多空策略',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 运行所有系统（一次性）
  python src/unified_trading_system.py --system all
  
  # 定时运行所有系统（每2小时）
  python src/unified_trading_system.py --system all --interval 2
  
  # 只运行De.系统（BTC）
  python src/unified_trading_system.py --system de
  
  # 只运行梦多空策略（一次性）
  python src/unified_trading_system.py --system meng
  
  # 定时运行梦多空策略（每4小时）
  python src/unified_trading_system.py --system meng --interval 4
  
  # 运行所有系统，自定义参数
  python src/unified_trading_system.py --system all --exchange bybit --limit 50
        """
    )
    
    parser.add_argument('--system', choices=['de', 'meng', 'all'], 
                       default='all', 
                       help='选择要运行的系统: de=De.系统, meng=梦多空策略, all=全部 (默认: all)')
    parser.add_argument('--symbol', default='BTC', 
                       help='De.系统分析的币种 (默认: BTC)')
    parser.add_argument('--exchange', choices=['auto', 'bitget', 'bybit', 'binance'], 
                       default='auto', 
                       help='交易所选择 (默认: auto)')
    parser.add_argument('--limit', type=int, default=100, 
                       help='扫描币种数 (默认: 100)')
    parser.add_argument('--interval', type=int, default=0,
                       help='定时运行间隔（小时），0表示只运行一次 (默认: 0)')
    
    args = parser.parse_args()
    
    system = UnifiedTradingSystem()
    
    # 如果有定时间隔，使用定时运行
    if args.interval > 0:
        if args.system == 'all':
            run_periodic_all_systems(args.interval, args.exchange, args.limit, args.symbol)
        elif args.system == 'meng':
            # 梦多空策略有自己的定时功能
            meng_module_path = CURRENT_DIR / "scan_meng_duo_kong_strategy.py"
            meng_module = import_module_from_path("meng_strategy", meng_module_path)
            meng_module.run_periodic_scan(args.interval, args.exchange, args.limit)
        else:
            print(f"⚠️  De.系统不支持定时运行，请使用系统定时任务", file=sys.stderr)
            system.run_de_system(args.symbol)
    else:
        # 一次性运行
        if args.system == 'de':
            system.run_de_system(args.symbol)
        elif args.system == 'meng':
            system.run_meng_system(args.exchange, args.limit)
        elif args.system == 'all':
            system.run_all_systems(args.exchange, args.limit, args.symbol)


if __name__ == "__main__":
    main()

