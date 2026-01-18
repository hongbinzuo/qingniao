#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化回测脚本

自动扫描交易计划文件，进行回测并生成报告。
支持定时任务和批量回测。
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import json

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from abu.backtest_engine import BacktestEngine, BacktestMetrics
    from scripts.backtest_trading_plan import parse_trading_plan_markdown, format_backtest_report
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def find_trading_plan_files(directory: Path, pattern: str = "*trading_plan*.md") -> List[Path]:
    """查找交易计划文件"""
    files = []
    
    # 查找匹配的文件
    for file_path in directory.glob(pattern):
        if file_path.is_file():
            files.append(file_path)
    
    # 按修改时间排序（最新的在前）
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    return files


def auto_backtest_all_plans(
    plans_dir: Path = None,
    output_dir: Path = None,
    initial_balance: float = 10000.0,
    fee_bps: float = 5.0,
    slippage_bps: float = 2.0,
    position_size_pct: float = 0.1,
    limit: int = None
) -> Dict:
    """
    自动回测所有交易计划
    
    Args:
        plans_dir: 交易计划目录（默认trading_signals）
        output_dir: 输出目录（默认trading_signals/backtest_reports）
        initial_balance: 初始资金
        fee_bps: 手续费基点
        slippage_bps: 滑点基点
        position_size_pct: 仓位百分比
        limit: 限制回测文件数量（None表示全部）
    
    Returns:
        回测结果汇总
    """
    if plans_dir is None:
        plans_dir = ROOT / 'trading_signals'
    if output_dir is None:
        output_dir = ROOT / 'trading_signals' / 'backtest_reports'
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("自动化回测系统")
    print("=" * 80)
    print()
    print(f"扫描目录: {plans_dir}")
    print(f"输出目录: {output_dir}")
    print()
    
    # 查找交易计划文件
    print("1. 查找交易计划文件...")
    plan_files = find_trading_plan_files(plans_dir, "*trading_plan*.md")
    plan_files.extend(find_trading_plan_files(plans_dir, "*vision_enhanced*.md"))
    plan_files.extend(find_trading_plan_files(plans_dir, "*ABU_v3*.md"))
    
    if limit:
        plan_files = plan_files[:limit]
    
    if not plan_files:
        print("   [WARN] 未找到交易计划文件")
        return {}
    
    print(f"   找到 {len(plan_files)} 个交易计划文件")
    print()
    
    # 汇总结果
    all_results = {
        'backtest_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_plans': len(plan_files),
        'plans': []
    }
    
    # 回测每个文件
    print("2. 回测交易计划...")
    for i, plan_file in enumerate(plan_files, 1):
        print(f"   [{i}/{len(plan_files)}] {plan_file.name}...", end=' ', flush=True)
        
        try:
            # 解析信号
            signals = parse_trading_plan_markdown(plan_file)
            if not signals:
                print("✗ (无信号)")
                continue
            
            # 初始化回测引擎
            engine = BacktestEngine(
                initial_balance=initial_balance,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
                position_size_pct=position_size_pct
            )
            
            # 回测所有信号
            success_count = 0
            for signal in signals:
                result = engine.backtest_signal(signal, timeframe=signal.get('timeframe', '5m'))
                if result.get('success'):
                    success_count += 1
            
            # 计算指标
            metrics = engine.calculate_metrics()
            
            # 生成报告
            report = format_backtest_report(engine, metrics, signals)
            
            # 保存报告
            report_file = output_dir / f"backtest_{plan_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            report_file.write_text(report, encoding='utf-8')
            
            # 保存JSON结果
            json_file = output_dir / f"backtest_{plan_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            json_data = {
                'plan_file': str(plan_file),
                'backtest_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'signals_count': len(signals),
                'successful_signals': success_count,
                'metrics': {
                    'total_return_pct': metrics.total_return_pct,
                    'max_drawdown_pct': metrics.max_drawdown_pct,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'profit_factor': metrics.profit_factor,
                    'win_rate': metrics.win_rate,
                    'total_trades': metrics.total_trades,
                    'winning_trades': metrics.winning_trades,
                    'losing_trades': metrics.losing_trades
                },
                'signals': engine.completed_signals
            }
            json_file.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding='utf-8')
            
            print(f"✓ ({len(signals)}信号, {metrics.total_return_pct:+.2f}%, 胜率{metrics.win_rate:.1f}%)")
            
            # 记录结果
            all_results['plans'].append({
                'file': str(plan_file),
                'signals_count': len(signals),
                'metrics': {
                    'total_return_pct': metrics.total_return_pct,
                    'max_drawdown_pct': metrics.max_drawdown_pct,
                    'win_rate': metrics.win_rate,
                    'total_trades': metrics.total_trades
                }
            })
            
            engine.close()
        
        except Exception as e:
            print(f"✗ (错误: {e})")
            import traceback
            traceback.print_exc()
    
    print()
    
    # 生成汇总报告
    print("3. 生成汇总报告...")
    summary = []
    summary.append("# 自动化回测汇总报告")
    summary.append("")
    summary.append(f"**回测时间**: {all_results['backtest_time']}")
    summary.append(f"**回测计划数**: {all_results['total_plans']}")
    summary.append("")
    summary.append("---")
    summary.append("")
    
    if all_results['plans']:
        summary.append("## 回测结果汇总")
        summary.append("")
        summary.append("| 计划文件 | 信号数 | 总收益率 | 最大回撤 | 胜率 | 交易数 |")
        summary.append("|---------|--------|---------|---------|------|--------|")
        
        for plan in all_results['plans']:
            file_name = Path(plan['file']).name
            metrics = plan['metrics']
            summary.append(f"| {file_name} | {plan['signals_count']} | "
                          f"{metrics['total_return_pct']:+.2f}% | "
                          f"{metrics['max_drawdown_pct']:.2f}% | "
                          f"{metrics['win_rate']:.2f}% | "
                          f"{metrics['total_trades']} |")
        
        summary.append("")
        
        # 统计
        avg_return = sum(p['metrics']['total_return_pct'] for p in all_results['plans']) / len(all_results['plans'])
        avg_win_rate = sum(p['metrics']['win_rate'] for p in all_results['plans']) / len(all_results['plans'])
        total_signals = sum(p['signals_count'] for p in all_results['plans'])
        
        summary.append("## 统计摘要")
        summary.append("")
        summary.append(f"- **平均收益率**: {avg_return:+.2f}%")
        summary.append(f"- **平均胜率**: {avg_win_rate:.2f}%")
        summary.append(f"- **总信号数**: {total_signals}")
        summary.append("")
    
    summary_file = output_dir / f"backtest_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    summary_file.write_text("\n".join(summary), encoding='utf-8')
    
    print(f"   [OK] 汇总报告已保存: {summary_file}")
    print()
    
    print("=" * 80)
    print("自动化回测完成！")
    print("=" * 80)
    print(f"回测计划数: {all_results['total_plans']}")
    print(f"报告目录: {output_dir}")
    print()
    
    return all_results


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='自动化回测交易计划')
    parser.add_argument('--plans-dir', type=str, help='交易计划目录（默认trading_signals）')
    parser.add_argument('--output-dir', type=str, help='输出目录（默认trading_signals/backtest_reports）')
    parser.add_argument('--initial-balance', type=float, default=10000.0, help='初始资金')
    parser.add_argument('--fee-bps', type=float, default=5.0, help='手续费基点')
    parser.add_argument('--slippage-bps', type=float, default=2.0, help='滑点基点')
    parser.add_argument('--position-size', type=float, default=0.1, help='仓位百分比')
    parser.add_argument('--limit', type=int, help='限制回测文件数量')
    
    args = parser.parse_args()
    
    plans_dir = Path(args.plans_dir) if args.plans_dir else None
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    try:
        results = auto_backtest_all_plans(
            plans_dir=plans_dir,
            output_dir=output_dir,
            initial_balance=args.initial_balance,
            fee_bps=args.fee_bps,
            slippage_bps=args.slippage_bps,
            position_size_pct=args.position_size,
            limit=args.limit
        )
        return 0
    except Exception as e:
        print(f"[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
