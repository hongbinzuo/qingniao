#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易计划回测脚本

从交易计划Markdown文件读取信号，进行回测并生成报告。
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

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
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def parse_trading_plan_markdown(file_path: Path) -> List[Dict]:
    """
    从Markdown文件解析交易计划信号
    
    Args:
        file_path: Markdown文件路径
    
    Returns:
        信号列表
    """
    signals = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"[ERROR] 读取文件失败: {e}", file=sys.stderr)
        return []
    
    # 解析币种和信号
    current_symbol = None
    current_timeframe = None
    
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # 检测币种标题 (## SYMBOL 或 ## SYMBOL ($price))
        symbol_match = re.match(r'^##\s+(\w+)(?:\s+\([^)]+\))?', line)
        if symbol_match:
            current_symbol = symbol_match.group(1)
            i += 1
            continue
        
        # 检测时间框架标题 (### 5分钟信号 或 ### 15分钟信号)
        timeframe_match = re.match(r'^###\s+(\d+)分钟信号', line)
        if timeframe_match:
            current_timeframe = timeframe_match.group(1) + 'm'
            i += 1
            continue
        
        # 解析信号字段
        if current_symbol and current_timeframe:
            signal = {
                'symbol': current_symbol,
                'timeframe': current_timeframe,
                'pattern_name': '',
                'pattern_type': '',
                'source': '',
                'direction': 'long',
                'entry_price': 0.0,
                'stop_loss': 0.0,
                'take_profit_1': 0.0,
                'take_profit_2': 0.0,
                'confidence': 0.0,
                'pattern_id': f"{current_symbol}_{current_timeframe}_{len(signals)}"
            }
            
            # 读取信号字段
            while i < len(lines):
                line = lines[i].strip()
                
                # 如果遇到新的标题，结束当前信号
                if line.startswith('##') or line.startswith('###'):
                    break
                
                # 解析字段
                if line.startswith('- **模式**:'):
                    match = re.search(r'模式\*\*:\s*(.+?)\s*\((.+?)\)', line)
                    if match:
                        signal['pattern_name'] = match.group(1).strip()
                        signal['pattern_type'] = match.group(2).strip()
                
                elif line.startswith('- **数据源**:'):
                    match = re.search(r'数据源\*\*:\s*(.+)', line)
                    if match:
                        sources = [s.strip() for s in match.group(1).split(',')]
                        signal['source'] = sources[0] if sources else ''
                        signal['all_sources'] = sources
                
                elif line.startswith('- **方向**:'):
                    match = re.search(r'方向\*\*:\s*(\w+)', line)
                    if match:
                        signal['direction'] = match.group(1).lower()
                
                elif line.startswith('- **入场价**:'):
                    match = re.search(r'入场价\*\*:\s*\$([\d,]+\.?\d*)', line)
                    if match:
                        signal['entry_price'] = float(match.group(1).replace(',', ''))
                
                elif line.startswith('- **止损价**:') or line.startswith('- **止损**:'):
                    match = re.search(r'止损(?:价)?\*\*:\s*\$([\d,]+\.?\d*)', line)
                    if match:
                        signal['stop_loss'] = float(match.group(1).replace(',', ''))
                
                elif line.startswith('- **止盈1**:'):
                    match = re.search(r'止盈1\*\*:\s*\$([\d,]+\.?\d*)', line)
                    if match:
                        signal['take_profit_1'] = float(match.group(1).replace(',', ''))
                
                elif line.startswith('- **止盈2**:'):
                    match = re.search(r'止盈2\*\*:\s*\$([\d,]+\.?\d*)', line)
                    if match:
                        signal['take_profit_2'] = float(match.group(1).replace(',', ''))
                
                elif line.startswith('- **置信度**:'):
                    match = re.search(r'置信度\*\*:\s*([\d.]+)%', line)
                    if match:
                        signal['confidence'] = float(match.group(1)) / 100.0
                
                # 如果遇到空行或下一个信号，结束当前信号
                if line == '' and signal.get('entry_price', 0) > 0:
                    # 验证信号完整性
                    if signal['entry_price'] > 0 and signal['stop_loss'] > 0 and signal['take_profit_1'] > 0:
                        signals.append(signal.copy())
                    break
                
                i += 1
            
            # 如果文件结束，保存最后一个信号
            if i >= len(lines) and signal.get('entry_price', 0) > 0:
                if signal['entry_price'] > 0 and signal['stop_loss'] > 0 and signal['take_profit_1'] > 0:
                    signals.append(signal)
        
        i += 1
    
    return signals


def format_backtest_report(engine: BacktestEngine, metrics: BacktestMetrics, 
                          signals: List[Dict]) -> str:
    """格式化回测报告"""
    output = []
    
    output.append("# 交易计划回测报告")
    output.append("")
    output.append(f"**回测时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"**初始资金**: ${engine.account.initial_balance:,.2f}")
    output.append(f"**最终权益**: ${engine.account.equity:,.2f}")
    output.append("")
    output.append("---")
    output.append("")
    
    # 性能指标
    output.append("## 性能指标")
    output.append("")
    output.append(f"- **总收益率**: {metrics.total_return_pct:.2f}%")
    output.append(f"- **最大回撤**: {metrics.max_drawdown_pct:.2f}%")
    output.append(f"- **Sharpe比率**: {metrics.sharpe_ratio:.2f}")
    output.append(f"- **盈亏比**: {metrics.profit_factor:.2f}")
    output.append(f"- **胜率**: {metrics.win_rate:.2f}%")
    output.append(f"- **总交易数**: {metrics.total_trades}")
    output.append(f"  - 盈利: {metrics.winning_trades}")
    output.append(f"  - 亏损: {metrics.losing_trades}")
    output.append(f"- **平均盈利**: ${metrics.avg_win:,.2f}")
    output.append(f"- **平均亏损**: ${metrics.avg_loss:,.2f}")
    output.append(f"- **总手续费**: ${metrics.total_fees:,.2f}")
    output.append(f"- **总滑点**: ${metrics.total_slippage:,.2f}")
    output.append("")
    
    # 信号详情
    output.append("## 信号详情")
    output.append("")
    
    for i, result in enumerate(engine.completed_signals, 1):
        output.append(f"### {i}. {result.get('pattern_name', 'Unknown')}")
        output.append("")
        output.append(f"- **模式类型**: {result.get('pattern_type', '')}")
        output.append(f"- **数据源**: {result.get('source', '')}")
        output.append(f"- **方向**: {result.get('direction', '').upper()}")
        output.append(f"- **状态**: {result.get('status', '')}")
        output.append(f"- **退出原因**: {result.get('exit_reason', '')}")
        output.append(f"- **入场价**: ${result.get('entry_price', 0):,.2f}")
        output.append(f"- **退出价**: ${result.get('exit_price', 0):,.2f}")
        output.append(f"- **盈亏**: ${result.get('pnl', 0):,.2f} ({result.get('pnl_pct', 0):.2f}%)")
        output.append(f"- **最大浮盈**: {result.get('max_profit_pct', 0):.2f}%")
        output.append(f"- **最大浮亏**: {result.get('max_loss_pct', 0):.2f}%")
        output.append(f"- **持仓时长**: {result.get('duration_hours', 0):.1f}小时")
        if result.get('tp1_reached'):
            output.append(f"- **止盈1**: ✓")
        if result.get('tp2_reached'):
            output.append(f"- **止盈2**: ✓")
        if result.get('stop_loss_hit'):
            output.append(f"- **止损**: ✓")
        if result.get('breakeven_stop_hit'):
            output.append(f"- **保本止损**: ✓")
        output.append("")
    
    return "\n".join(output)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Backtest trading plan')
    parser.add_argument('plan_file', type=str, help='Trading plan markdown file path')
    parser.add_argument('--initial-balance', type=float, default=10000.0, help='Initial balance (default: 10000)')
    parser.add_argument('--fee-bps', type=float, default=5.0, help='Fee in basis points (default: 5, i.e. 0.05%%)')
    parser.add_argument('--slippage-bps', type=float, default=2.0, help='Slippage in basis points (default: 2, i.e. 0.02%%)')
    parser.add_argument('--position-size', type=float, default=0.1, help='Position size percentage (default: 0.1, i.e. 10%%)')
    parser.add_argument('--output', type=str, help='Output report file path (optional)')
    
    args = parser.parse_args()
    
    plan_file = Path(args.plan_file)
    if not plan_file.exists():
        print(f"[ERROR] 文件不存在: {plan_file}")
        return 1
    
    print("=" * 80)
    print("交易计划回测")
    print("=" * 80)
    print()
    
    # 1. 解析交易计划
    print("1. 解析交易计划...")
    signals = parse_trading_plan_markdown(plan_file)
    if not signals:
        print("[ERROR] 未找到有效信号")
        return 1
    
    print(f"   找到 {len(signals)} 个信号")
    print()
    
    # 2. 初始化回测引擎
    print("2. 初始化回测引擎...")
    engine = BacktestEngine(
        initial_balance=args.initial_balance,
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        position_size_pct=args.position_size
    )
    print("   [OK] 回测引擎初始化完成")
    print()
    
    # 3. 回测信号
    print("3. 回测信号...")
    for i, signal in enumerate(signals, 1):
        symbol = signal.get('symbol', 'BTC')
        timeframe = signal.get('timeframe', '5m')
        print(f"   [{i}/{len(signals)}] {symbol} {timeframe} {signal.get('direction', '').upper()} @ ${signal.get('entry_price', 0):,.2f}...", 
              end=' ', flush=True)
        
        result = engine.backtest_signal(signal, timeframe=timeframe)
        
        if result.get('success'):
            status = result.get('status', 'unknown')
            pnl_pct = result.get('pnl_pct', 0)
            print(f"✓ ({status}, {pnl_pct:+.2f}%)")
        else:
            print(f"✗ ({result.get('reason', '失败')})")
    
    print()
    
    # 4. 计算指标
    print("4. 计算性能指标...")
    metrics = engine.calculate_metrics()
    print("   [OK] 指标计算完成")
    print()
    
    # 5. 生成报告
    print("5. 生成报告...")
    report = format_backtest_report(engine, metrics, signals)
    
    # 保存报告
    if args.output:
        output_file = Path(args.output)
    else:
        output_file = ROOT / 'trading_signals' / f'backtest_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding='utf-8')
    
    print(f"   [OK] 报告已保存: {output_file}")
    print()
    
    # 6. 打印摘要
    print("=" * 80)
    print("回测摘要")
    print("=" * 80)
    print(f"总收益率: {metrics.total_return_pct:+.2f}%")
    print(f"最大回撤: {metrics.max_drawdown_pct:.2f}%")
    print(f"胜率: {metrics.win_rate:.2f}%")
    print(f"总交易: {metrics.total_trades} (盈利: {metrics.winning_trades}, 亏损: {metrics.losing_trades})")
    print(f"盈亏比: {metrics.profit_factor:.2f}")
    print(f"Sharpe比率: {metrics.sharpe_ratio:.2f}")
    print()
    
    # 清理
    engine.close()
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
