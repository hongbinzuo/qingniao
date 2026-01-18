#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动回测集成模块

在交易计划生成后自动运行回测，记录结果，并检测问题。
"""

import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from abu.backtest_engine import BacktestEngine, BacktestMetrics
    
    # 尝试导入解析函数
    try:
        from scripts.backtest_trading_plan import parse_trading_plan_markdown
    except ImportError:
        # 如果导入失败，直接定义解析函数
        import re
        def parse_trading_plan_markdown(file_path: Path) -> List[Dict]:
            """从Markdown文件解析交易计划信号"""
            signals = []
            try:
                content = file_path.read_text(encoding='utf-8')
            except Exception:
                return []
            
            current_symbol = None
            current_timeframe = None
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                symbol_match = re.match(r'^##\s+(\w+)(?:\s+\([^)]+\))?', line)
                if symbol_match:
                    current_symbol = symbol_match.group(1)
                    i += 1
                    continue
                
                timeframe_match = re.match(r'^###\s+(\d+)分钟信号', line)
                if timeframe_match:
                    current_timeframe = timeframe_match.group(1) + 'm'
                    i += 1
                    continue
                
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
                    
                    while i < len(lines):
                        line = lines[i].strip()
                        if line.startswith('##') or line.startswith('###'):
                            break
                        
                        if line.startswith('- **入场价**:'):
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
                        
                        elif line.startswith('- **方向**:'):
                            match = re.search(r'方向\*\*:\s*(\w+)', line)
                            if match:
                                signal['direction'] = match.group(1).lower()
                        
                        if line == '' and signal.get('entry_price', 0) > 0:
                            if signal['entry_price'] > 0 and signal['stop_loss'] > 0 and signal['take_profit_1'] > 0:
                                signals.append(signal.copy())
                            break
                        
                        i += 1
                    
                    if i >= len(lines) and signal.get('entry_price', 0) > 0:
                        if signal['entry_price'] > 0 and signal['stop_loss'] > 0 and signal['take_profit_1'] > 0:
                            signals.append(signal)
                
                i += 1
            
            return signals
    
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[WARN] 回测模块导入失败: {e}", file=sys.stderr)


class AutoBacktestIntegration:
    """自动回测集成"""
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        fee_bps: float = 5.0,
        slippage_bps: float = 2.0,
        position_size_pct: float = 0.1
    ):
        """
        初始化自动回测集成
        
        Args:
            initial_balance: 初始资金
            fee_bps: 手续费基点
            slippage_bps: 滑点基点
            position_size_pct: 仓位百分比
        """
        self.initial_balance = initial_balance
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.position_size_pct = position_size_pct
        
        # 问题阈值
        self.warning_thresholds = {
            'min_win_rate': 0.40,  # 最低胜率40%
            'max_drawdown': 0.30,  # 最大回撤30%
            'min_profit_factor': 1.2,  # 最低盈亏比1.2
            'min_sharpe': 0.5,  # 最低Sharpe比率0.5
        }
    
    def run_backtest(self, plan_file: Path) -> Tuple[Dict, Optional[str]]:
        """
        运行回测
        
        Args:
            plan_file: 交易计划文件路径
        
        Returns:
            (回测结果字典, 错误信息)
        """
        if not IMPORTS_AVAILABLE:
            return {}, "回测模块不可用"
        
        if not plan_file.exists():
            return {}, f"交易计划文件不存在: {plan_file}"
        
        try:
            # 解析信号
            signals = parse_trading_plan_markdown(plan_file)
            if not signals:
                return {}, "未找到有效信号"
            
            # 初始化回测引擎
            engine = BacktestEngine(
                initial_balance=self.initial_balance,
                fee_bps=self.fee_bps,
                slippage_bps=self.slippage_bps,
                position_size_pct=self.position_size_pct
            )
            
            # Brooks规则验证统计
            try:
                from abu.brooks_trading_validator import BrooksTradingValidator, ValidationLevel
                validator = BrooksTradingValidator()
                validation_stats = validator.validate_batch(signals)
            except ImportError:
                validator = None
                validation_stats = None
            
            # 初始化性能分析器
            try:
                from abu.performance_analyzer import PerformanceAnalyzer
                performance_analyzer = PerformanceAnalyzer()
            except ImportError:
                performance_analyzer = None
            
            # 初始化自动评估器
            try:
                from abu.auto_evaluator import AutoEvaluator
                auto_evaluator = AutoEvaluator()
            except ImportError:
                auto_evaluator = None
            
            # 初始化反馈循环系统
            try:
                from abu.feedback_loop import FeedbackLoop
                feedback_loop = FeedbackLoop()
            except ImportError:
                feedback_loop = None
            
            # 回测所有信号
            successful_signals = 0
            failed_signals = []
            brooks_rejected = 0
            backtest_results = []  # 保存回测结果用于性能分析
            
            for signal in signals:
                timeframe = signal.get('timeframe', '5m')
                
                # 先进行Brooks验证
                if validator:
                    validation_result = validator.validate_signal(signal)
                    if not validation_result.is_valid:
                        brooks_rejected += 1
                        failed_signals.append({
                            'symbol': signal.get('symbol', 'Unknown'),
                            'timeframe': timeframe,
                            'reason': f"Brooks规则验证失败: {'; '.join(validation_result.issues[:2])}",
                            'validation_level': validation_result.level.value,
                            'validation_score': validation_result.score
                        })
                        continue  # 跳过回测
                
                # 自动评估信号（在回测前）
                evaluation = None
                if auto_evaluator:
                    try:
                        # 获取当前价格（用于检查信号是否过期）
                        current_price = None
                        if signal.get('symbol'):
                            try:
                                from scripts.generate_comprehensive_trading_plans import get_kline_gateio
                                klines = get_kline_gateio(signal['symbol'], timeframe, limit=1)
                                if klines:
                                    current_price = klines[-1]['close']
                            except Exception:
                                pass
                        
                        eval_result = auto_evaluator.evaluate_signal(signal, current_price)
                        evaluation = {
                            'score': eval_result.score,
                            'quality': eval_result.quality.value,
                            'issues': eval_result.issues,
                            'warnings': eval_result.warnings,
                            'strengths': eval_result.strengths,
                            'recommendations': eval_result.recommendations,
                            'is_tradable': eval_result.is_tradable,
                            'adjusted_params': eval_result.adjusted_params
                        }
                        
                        # 如果评估为不可交易，跳过回测
                        if not eval_result.is_tradable:
                            failed_signals.append({
                                'symbol': signal.get('symbol', 'Unknown'),
                                'timeframe': timeframe,
                                'reason': f"自动评估: 信号不可交易 - {'; '.join(eval_result.issues[:2])}",
                                'evaluation_score': eval_result.score
                            })
                            continue
                    except Exception as e:
                        print(f"[WARN] 自动评估失败: {e}", file=sys.stderr)
                
                result = engine.backtest_signal(signal, timeframe=timeframe, validate_brooks_rules=True)
                if result.get('success'):
                    successful_signals += 1
                    backtest_results.append((signal, result))
                    # 添加到性能分析器
                    if performance_analyzer:
                        performance_analyzer.add_signal_result(signal, result)
                    # 添加到反馈循环系统
                    if feedback_loop:
                        try:
                            feedback_loop.add_backtest_result(signal, result, evaluation)
                        except Exception as e:
                            print(f"[WARN] 反馈循环失败: {e}", file=sys.stderr)
                else:
                    failed_signals.append({
                        'symbol': signal.get('symbol', 'Unknown'),
                        'timeframe': timeframe,
                        'reason': result.get('reason', 'Unknown')
                    })
                    # 即使回测失败，也添加到反馈循环
                    if feedback_loop and evaluation:
                        try:
                            feedback_loop.add_backtest_result(signal, result, evaluation)
                        except Exception:
                            pass
            
            # 计算指标
            metrics = engine.calculate_metrics()
            
            # 性能分析
            performance_analysis = None
            if performance_analyzer and backtest_results:
                try:
                    # 分析模式表现
                    pattern_stats = performance_analyzer.analyze_pattern_performance()
                    timeframe_stats = performance_analyzer.analyze_by_timeframe()
                    symbol_stats = performance_analyzer.analyze_by_symbol()
                    best_patterns = performance_analyzer.identify_best_patterns(min_signals=2)
                    worst_patterns = performance_analyzer.identify_worst_patterns(min_signals=2)
                    
                    performance_analysis = {
                        'pattern_stats': {k: {
                            'total_signals': v.total_signals,
                            'win_rate': v.win_rate,
                            'avg_return_pct': v.avg_return_pct,
                            'total_pnl': v.total_pnl
                        } for k, v in pattern_stats.items()},
                        'timeframe_stats': timeframe_stats,
                        'symbol_stats': symbol_stats,
                        'best_patterns': [(k, {
                            'pattern_name': v.pattern_name,
                            'pattern_type': v.pattern_type,
                            'win_rate': v.win_rate,
                            'avg_return_pct': v.avg_return_pct,
                            'total_pnl': v.total_pnl
                        }) for k, v in best_patterns[:5]],
                        'worst_patterns': [(k, {
                            'pattern_name': v.pattern_name,
                            'pattern_type': v.pattern_type,
                            'win_rate': v.win_rate,
                            'avg_return_pct': v.avg_return_pct,
                            'total_pnl': v.total_pnl
                        }) for k, v in worst_patterns[:5]]
                    }
                except Exception as e:
                    print(f"[WARN] 性能分析失败: {e}", file=sys.stderr)
            
            # 生成改进建议（如果反馈循环系统可用）
            improvement_report = None
            if feedback_loop:
                try:
                    improvements = feedback_loop.analyze_feedback()
                    if improvements:
                        improvement_report = feedback_loop.generate_improvement_report()
                        # 保存改进报告
                        feedback_dir = Path('outputs/feedback_loop')
                        feedback_dir.mkdir(parents=True, exist_ok=True)
                        improvement_file = feedback_dir / f"improvement_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                        improvement_file.write_text(improvement_report, encoding='utf-8')
                except Exception as e:
                    print(f"[WARN] 生成改进建议失败: {e}", file=sys.stderr)
            
            # 获取评估统计
            evaluation_stats = None
            if auto_evaluator:
                try:
                    evaluation_stats = auto_evaluator.get_statistics()
                    # 确保包含total_evaluated字段
                    if evaluation_stats:
                        total_eval = evaluation_stats.get('total_evaluated', 0)
                        if total_eval == 0:
                            # 如果没有评估历史，尝试从实际评估的信号数计算
                            # 注意：只有通过Brooks验证的信号才会被评估
                            actual_evaluated = len(signals) - brooks_rejected
                            if actual_evaluated > 0:
                                evaluation_stats['total_evaluated'] = actual_evaluated
                                print(f"[INFO] AutoEvaluator历史为空，使用实际评估数: {actual_evaluated}", file=sys.stderr)
                            else:
                                print(f"[WARN] 没有信号被评估: 总信号{len(signals)}，Brooks拒绝{brooks_rejected}", file=sys.stderr)
                        else:
                            print(f"[INFO] AutoEvaluator统计: {total_eval} 个信号已评估，平均分数: {evaluation_stats.get('average_score', 0):.1f}", file=sys.stderr)
                except Exception as e:
                    print(f"[WARN] 获取评估统计失败: {e}", file=sys.stderr)
                    import traceback
                    traceback.print_exc()
            else:
                print(f"[WARN] AutoEvaluator未初始化，无法获取评估统计", file=sys.stderr)
            
            # 构建结果
            result = {
                'plan_file': str(plan_file),
                'backtest_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_signals': len(signals),
                'successful_signals': successful_signals,
                'failed_signals': failed_signals,
                'brooks_rejected': brooks_rejected if validator else 0,
                'brooks_validation': validation_stats['stats'] if validation_stats else None,
                'evaluation_stats': evaluation_stats,
                'metrics': {
                    'total_return_pct': metrics.total_return_pct,
                    'max_drawdown_pct': metrics.max_drawdown_pct,
                    'sharpe_ratio': metrics.sharpe_ratio,
                    'profit_factor': metrics.profit_factor,
                    'win_rate': metrics.win_rate,
                    'total_trades': metrics.total_trades,
                    'winning_trades': metrics.winning_trades,
                    'losing_trades': metrics.losing_trades,
                    'avg_win': metrics.avg_win,
                    'avg_loss': metrics.avg_loss,
                    'final_equity': engine.account.equity,
                },
                'performance_analysis': performance_analysis,
                'improvement_report': improvement_report,
                'warnings': self._check_warnings(metrics),
                'issues': self._check_issues(metrics, failed_signals)
            }
            
            engine.close()
            
            return result, None
            
        except Exception as e:
            import traceback
            return {}, f"回测失败: {str(e)}\n{traceback.format_exc()}"
    
    def _check_warnings(self, metrics: BacktestMetrics) -> List[str]:
        """检查警告"""
        warnings = []
        
        if metrics.win_rate < self.warning_thresholds['min_win_rate']:
            warnings.append(f"胜率过低: {metrics.win_rate:.1%} < {self.warning_thresholds['min_win_rate']:.1%}")
        
        if metrics.max_drawdown_pct > self.warning_thresholds['max_drawdown']:
            warnings.append(f"回撤过大: {metrics.max_drawdown_pct:.1%} > {self.warning_thresholds['max_drawdown']:.1%}")
        
        if metrics.profit_factor < self.warning_thresholds['min_profit_factor']:
            warnings.append(f"盈亏比过低: {metrics.profit_factor:.2f} < {self.warning_thresholds['min_profit_factor']:.2f}")
        
        if metrics.sharpe_ratio < self.warning_thresholds['min_sharpe']:
            warnings.append(f"Sharpe比率过低: {metrics.sharpe_ratio:.2f} < {self.warning_thresholds['min_sharpe']:.2f}")
        
        return warnings
    
    def _check_issues(self, metrics: BacktestMetrics, failed_signals: List[Dict]) -> List[str]:
        """检查严重问题"""
        issues = []
        
        # 如果所有信号都失败
        if metrics.total_trades == 0 and failed_signals:
            issues.append(f"⚠️ 严重问题: 所有{len(failed_signals)}个信号回测失败")
            # 统计失败原因
            failure_reasons = {}
            for fs in failed_signals:
                reason = fs.get('reason', 'Unknown')
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
            issues.append(f"   失败原因统计: {failure_reasons}")
        
        # 如果收益率严重为负
        if metrics.total_return_pct < -0.20:
            issues.append(f"⚠️ 严重问题: 总收益率严重为负: {metrics.total_return_pct:.1%}")
        
        # 如果回撤超过50%
        if metrics.max_drawdown_pct > 0.50:
            issues.append(f"⚠️ 严重问题: 最大回撤超过50%: {metrics.max_drawdown_pct:.1%}")
        
        # 如果胜率极低且交易数足够
        if metrics.total_trades >= 10 and metrics.win_rate < 0.30:
            issues.append(f"⚠️ 严重问题: 胜率极低: {metrics.win_rate:.1%} (交易数: {metrics.total_trades})")
        
        return issues
    
    def save_backtest_result(self, result: Dict, output_dir: Path) -> Path:
        """
        保存回测结果
        
        Args:
            result: 回测结果字典
            output_dir: 输出目录
        
        Returns:
            保存的文件路径
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        plan_file = Path(result['plan_file'])
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_file = output_dir / f"backtest_{plan_file.stem}_{timestamp}.json"
        md_file = output_dir / f"backtest_{plan_file.stem}_{timestamp}.md"
        
        # 保存JSON
        json_file.write_text(
            json.dumps(result, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        # 生成Markdown报告
        md_content = self._format_backtest_report(result)
        md_file.write_text(md_content, encoding='utf-8')
        
        return md_file
    
    def _format_backtest_report(self, result: Dict) -> str:
        """格式化回测报告"""
        lines = []
        lines.append("# 自动回测报告")
        lines.append("")
        lines.append(f"**回测时间**: {result['backtest_time']}")
        lines.append(f"**交易计划**: {Path(result['plan_file']).name}")
        lines.append("")
        
        # 信号统计
        lines.append("## 信号统计")
        lines.append("")
        lines.append(f"- **总信号数**: {result['total_signals']}")
        lines.append(f"- **成功回测**: {result['successful_signals']}")
        lines.append(f"- **失败信号**: {len(result['failed_signals'])}")
        lines.append("")
        
        if result['failed_signals']:
            lines.append("### 失败信号详情")
            lines.append("")
            for fs in result['failed_signals']:
                lines.append(f"- {fs['symbol']} {fs['timeframe']}: {fs['reason']}")
            lines.append("")
        
        # 性能指标
        metrics = result['metrics']
        lines.append("## 性能指标")
        lines.append("")
        lines.append(f"- **总收益率**: {metrics['total_return_pct']:+.2f}%")
        lines.append(f"- **最大回撤**: {metrics['max_drawdown_pct']:.2f}%")
        lines.append(f"- **Sharpe比率**: {metrics['sharpe_ratio']:.2f}")
        lines.append(f"- **盈亏比**: {metrics['profit_factor']:.2f}")
        lines.append(f"- **胜率**: {metrics['win_rate']:.2f}%")
        lines.append(f"- **总交易数**: {metrics['total_trades']}")
        lines.append(f"  - 盈利: {metrics['winning_trades']}")
        lines.append(f"  - 亏损: {metrics['losing_trades']}")
        lines.append(f"- **平均盈利**: ${metrics['avg_win']:.2f}")
        lines.append(f"- **平均亏损**: ${metrics['avg_loss']:.2f}")
        lines.append(f"- **最终权益**: ${metrics['final_equity']:.2f}")
        lines.append("")
        
        # 警告
        if result['warnings']:
            lines.append("## ⚠️ 警告")
            lines.append("")
            for warning in result['warnings']:
                lines.append(f"- {warning}")
            lines.append("")
        
        # 严重问题
        if result['issues']:
            lines.append("## 🚨 严重问题")
            lines.append("")
            for issue in result['issues']:
                lines.append(f"- {issue}")
            lines.append("")
        
        return "\n".join(lines)
    
    def print_feedback(self, result: Dict):
        """打印反馈信息"""
        print()
        print("=" * 80)
        print("自动回测反馈")
        print("=" * 80)
        print()
        
        metrics = result['metrics']
        
        # 基本统计
        print(f"信号统计: {result['successful_signals']}/{result['total_signals']} 成功")
        if result.get('brooks_rejected', 0) > 0:
            print(f"Brooks规则拒绝: {result['brooks_rejected']} 个信号")
        if result.get('brooks_validation'):
            bv = result['brooks_validation']
            print(f"Brooks验证: {bv['valid']}通过, {bv['invalid']}失败 (平均分数: {bv['avg_score']:.1f}/100)")
        print(f"总收益率: {metrics['total_return_pct']:+.2f}%")
        print(f"胜率: {metrics['win_rate']:.2f}%")
        print(f"总交易数: {metrics['total_trades']}")
        
        # 性能分析摘要
        if result.get('performance_analysis'):
            perf = result['performance_analysis']
            if perf.get('best_patterns'):
                print(f"\n最佳模式: {perf['best_patterns'][0][1]['pattern_name']} "
                      f"(胜率: {perf['best_patterns'][0][1]['win_rate']:.1%}, "
                      f"盈亏: ${perf['best_patterns'][0][1]['total_pnl']:,.2f})")
            if perf.get('worst_patterns'):
                print(f"最差模式: {perf['worst_patterns'][0][1]['pattern_name']} "
                      f"(胜率: {perf['worst_patterns'][0][1]['win_rate']:.1%}, "
                      f"盈亏: ${perf['worst_patterns'][0][1]['total_pnl']:,.2f})")
        
        print()
        
        # 警告
        if result['warnings']:
            print("⚠️ 警告:")
            for warning in result['warnings']:
                print(f"  - {warning}")
            print()
        
        # 严重问题
        if result['issues']:
            print("🚨 严重问题:")
            for issue in result['issues']:
                print(f"  {issue}")
            print()
        
        # 如果一切正常
        if not result['warnings'] and not result['issues']:
            print("✅ 回测结果正常，未发现明显问题")
            print()
