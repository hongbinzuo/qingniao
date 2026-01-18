#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续信号评估后台进程

定期检查新生成的交易计划，评估信号质量，并将结果反馈给系统用于自动改进。
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import argparse

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
OUTPUTS = ROOT / 'outputs'
TRADING_PLANS = OUTPUTS / 'trading_plans'
BACKTEST_RESULTS = OUTPUTS / 'backtest_results'
FEEDBACK_DIR = OUTPUTS / 'feedback'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# 确保目录存在
FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

try:
    from abu.auto_evaluator import AutoEvaluator
    from abu.feedback_loop import FeedbackLoop
    from abu.auto_backtest_integration import AutoBacktestIntegration
    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] 部分模块导入失败: {e}", file=sys.stderr)
    IMPORTS_AVAILABLE = False


class ContinuousSignalEvaluator:
    """持续信号评估器"""
    
    def __init__(
        self,
        check_interval: int = 1800,  # 30分钟检查一次
        lookback_hours: int = 24,  # 检查最近24小时的交易计划
        feedback_dir: Optional[Path] = None
    ):
        """
        初始化持续信号评估器
        
        Args:
            check_interval: 检查间隔（秒）
            lookback_hours: 检查最近多少小时的交易计划
            feedback_dir: 反馈报告保存目录
        """
        self.check_interval = check_interval
        self.lookback_hours = lookback_hours
        self.feedback_dir = feedback_dir or FEEDBACK_DIR
        
        # 初始化组件
        if IMPORTS_AVAILABLE:
            self.auto_evaluator = AutoEvaluator()
            self.feedback_loop = FeedbackLoop()
            self.backtest_integration = AutoBacktestIntegration()
        else:
            self.auto_evaluator = None
            self.feedback_loop = None
            self.backtest_integration = None
        
        # 已处理的文件记录
        self.processed_files = set()
        self.processed_file_log = self.feedback_dir / 'processed_files.json'
        self._load_processed_files()
    
    def _load_processed_files(self):
        """加载已处理的文件列表"""
        if self.processed_file_log.exists():
            try:
                with open(self.processed_file_log, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_files = set(data.get('processed_files', []))
            except Exception:
                self.processed_files = set()
    
    def _save_processed_files(self):
        """保存已处理的文件列表"""
        try:
            with open(self.processed_file_log, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed_files': list(self.processed_files),
                    'last_update': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[WARN] 保存已处理文件列表失败: {e}", file=sys.stderr)
    
    def find_new_trading_plans(self) -> List[Path]:
        """
        查找新的交易计划文件
        
        Returns:
            新的交易计划文件列表
        """
        if not TRADING_PLANS.exists():
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=self.lookback_hours)
        new_plans = []
        
        # 查找所有交易计划文件
        for plan_file in TRADING_PLANS.glob('*.md'):
            # 跳过已处理的文件
            if str(plan_file) in self.processed_files:
                continue
            
            # 检查文件修改时间
            try:
                mtime = datetime.fromtimestamp(plan_file.stat().st_mtime)
                if mtime >= cutoff_time:
                    new_plans.append(plan_file)
            except Exception:
                continue
        
        # 按修改时间排序（最新的在前）
        new_plans.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        
        return new_plans
    
    def evaluate_trading_plan(self, plan_file: Path) -> Dict:
        """
        评估交易计划
        
        Args:
            plan_file: 交易计划文件路径
        
        Returns:
            评估结果字典
        """
        if not IMPORTS_AVAILABLE:
            return {'error': '模块不可用'}
        
        try:
            # 解析交易计划
            from abu.auto_backtest_integration import parse_trading_plan_markdown
            signals = parse_trading_plan_markdown(plan_file)
            
            if not signals:
                return {'error': '未找到有效信号', 'file': str(plan_file)}
            
            # 评估每个信号
            evaluation_results = []
            for signal in signals:
                evaluation = self.auto_evaluator.evaluate_signal(signal)
                evaluation_results.append({
                    'signal': signal,
                    'evaluation': {
                        'score': evaluation.score,
                        'quality': evaluation.quality.value,
                        'issues': evaluation.issues,
                        'recommendations': evaluation.recommendations,
                        'warnings': evaluation.warnings,
                        'strengths': evaluation.strengths
                    }
                })
            
            # 运行回测（如果可能）
            backtest_result = None
            try:
                backtest_result, error = self.backtest_integration.run_backtest(plan_file)
                if error:
                    print(f"[WARN] 回测失败: {error}", file=sys.stderr)
            except Exception as e:
                print(f"[WARN] 回测异常: {e}", file=sys.stderr)
            
            # 收集反馈
            if backtest_result and self.feedback_loop:
                # 将回测结果添加到反馈循环
                for i, signal in enumerate(signals):
                    signal_result = None
                    # 尝试从回测结果中找到对应的信号结果
                    signal_results = backtest_result.get('signal_results', [])
                    if i < len(signal_results):
                        signal_result = signal_results[i]
                    elif signal_results:
                        # 尝试通过symbol和timeframe匹配
                        for sr in signal_results:
                            if (sr.get('symbol', '').upper() == signal.get('symbol', '').upper() and
                                sr.get('timeframe', '') == signal.get('timeframe', '')):
                                signal_result = sr
                                break
                    
                    if signal_result:
                        # 获取对应的评估结果
                        eval_result = evaluation_results[i] if i < len(evaluation_results) else None
                        eval_data = eval_result.get('evaluation', {}) if eval_result else {}
                        
                        # 使用add_backtest_result方法
                        self.feedback_loop.add_backtest_result(
                            signal=signal,
                            backtest_result=signal_result,
                            evaluation={
                                'score': eval_data.get('score', 0),
                                'quality': eval_data.get('quality', 'unknown'),
                                'issues': eval_data.get('issues', [])
                            }
                        )
            
            return {
                'file': str(plan_file),
                'signal_count': len(signals),
                'evaluations': evaluation_results,
                'backtest_result': backtest_result,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[ERROR] 评估交易计划失败 {plan_file}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return {'error': str(e), 'file': str(plan_file)}
    
    def generate_feedback_report(self, evaluation_results: List[Dict]) -> Path:
        """
        生成反馈报告
        
        Args:
            evaluation_results: 评估结果列表
        
        Returns:
            报告文件路径
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.feedback_dir / f'continuous_evaluation_{timestamp}.md'
        
        lines = []
        lines.append("# 持续信号评估报告")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**评估文件数**: {len(evaluation_results)}")
        lines.append("")
        
        # 统计信息
        total_signals = 0
        evaluation_scores = []
        quality_counts = {}
        
        for result in evaluation_results:
            if 'error' in result:
                continue
            
            total_signals += result.get('signal_count', 0)
            for eval_result in result.get('evaluations', []):
                eval_data = eval_result.get('evaluation', {})
                score = eval_data.get('score', 0)
                quality = eval_data.get('quality', 'unknown')
                
                evaluation_scores.append(score)
                quality_counts[quality] = quality_counts.get(quality, 0) + 1
        
        lines.append("## 统计信息")
        lines.append("")
        lines.append(f"- **总信号数**: {total_signals}")
        if evaluation_scores:
            avg_score = sum(evaluation_scores) / len(evaluation_scores)
            lines.append(f"- **平均评估分数**: {avg_score:.1f}/100")
        lines.append(f"- **质量分布**:")
        for quality, count in sorted(quality_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  - {quality}: {count}")
        lines.append("")
        
        # 详细评估结果
        lines.append("## 详细评估结果")
        lines.append("")
        
        for i, result in enumerate(evaluation_results, 1):
            if 'error' in result:
                lines.append(f"### {i}. {Path(result['file']).name}")
                lines.append("")
                lines.append(f"**错误**: {result['error']}")
                lines.append("")
                continue
            
            plan_file = Path(result['file'])
            lines.append(f"### {i}. {plan_file.name}")
            lines.append("")
            lines.append(f"- **文件**: `{plan_file.name}`")
            lines.append(f"- **信号数**: {result.get('signal_count', 0)}")
            lines.append(f"- **评估时间**: {result.get('timestamp', 'N/A')}")
            lines.append("")
            
            # 信号评估详情
            for j, eval_result in enumerate(result.get('evaluations', []), 1):
                signal = eval_result.get('signal', {})
                eval_data = eval_result.get('evaluation', {})
                
                lines.append(f"#### 信号 {j}: {signal.get('symbol', 'N/A')} {signal.get('timeframe', 'N/A')}")
                lines.append("")
                lines.append(f"- **模式**: {signal.get('pattern_name', 'N/A')}")
                lines.append(f"- **方向**: {signal.get('direction', 'N/A').upper()}")
                lines.append(f"- **评估分数**: {eval_data.get('score', 0):.1f}/100")
                lines.append(f"- **质量等级**: {eval_data.get('quality', 'unknown')}")
                
                issues = eval_data.get('issues', [])
                if issues:
                    lines.append(f"- **问题**:")
                    for issue in issues:
                        lines.append(f"  - {issue}")
                
                recommendations = eval_data.get('recommendations', [])
                if recommendations:
                    lines.append(f"- **改进建议**:")
                    for recommendation in recommendations:
                        lines.append(f"  - {recommendation}")
                
                lines.append("")
        
        # 系统改进建议
        if self.feedback_loop:
            improvements = self.feedback_loop.analyze_feedback()
            if improvements:
                lines.append("## 系统改进建议")
                lines.append("")
                for improvement in improvements:
                    lines.append(f"### {improvement.category}")
                    lines.append("")
                    lines.append(f"- **问题**: {improvement.description}")
                    lines.append(f"- **当前值**: {improvement.current_value}")
                    lines.append(f"- **建议值**: {improvement.suggested_value}")
                    lines.append(f"- **优先级**: {improvement.priority}")
                    lines.append(f"- **置信度**: {improvement.confidence:.1f}%")
                    lines.append(f"- **证据数**: {improvement.evidence_count}")
                    lines.append("")
        
        # 保存报告
        report_file.write_text('\n'.join(lines), encoding='utf-8')
        
        return report_file
    
    def run_once(self):
        """运行一次评估"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 检查新的交易计划...", file=sys.stderr)
        
        # 查找新的交易计划
        new_plans = self.find_new_trading_plans()
        
        if not new_plans:
            print("✓ 没有新的交易计划需要评估", file=sys.stderr)
            return
        
        print(f"发现 {len(new_plans)} 个新的交易计划文件", file=sys.stderr)
        
        # 评估每个交易计划
        evaluation_results = []
        for plan_file in new_plans:
            print(f"  评估: {plan_file.name}...", file=sys.stderr)
            result = self.evaluate_trading_plan(plan_file)
            evaluation_results.append(result)
            
            # 标记为已处理
            self.processed_files.add(str(plan_file))
        
        # 保存已处理文件列表
        self._save_processed_files()
        
        # 生成反馈报告
        if evaluation_results:
            report_file = self.generate_feedback_report(evaluation_results)
            print(f"✅ 反馈报告已保存: {report_file.name}", file=sys.stderr)
        
        # 生成系统改进建议
        if self.feedback_loop:
            improvements = self.feedback_loop.analyze_feedback()
            if improvements:
                print(f"📊 生成了 {len(improvements)} 条系统改进建议", file=sys.stderr)
                # 保存改进建议
                improvements_file = self.feedback_dir / f'improvements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                with open(improvements_file, 'w', encoding='utf-8') as f:
                    json.dump([{
                        'category': imp.category,
                        'description': imp.description,
                        'current_value': imp.current_value,
                        'suggested_value': imp.suggested_value,
                        'priority': imp.priority,
                        'confidence': imp.confidence,
                        'evidence_count': imp.evidence_count
                    } for imp in improvements], f, ensure_ascii=False, indent=2)
                print(f"✅ 改进建议已保存: {improvements_file.name}", file=sys.stderr)
    
    def run_continuous(self):
        """持续运行评估"""
        print("=" * 80, file=sys.stderr)
        print("持续信号评估系统启动", file=sys.stderr)
        print(f"检查间隔: {self.check_interval}秒 ({self.check_interval/60:.1f}分钟)", file=sys.stderr)
        print(f"检查范围: 最近 {self.lookback_hours} 小时的交易计划", file=sys.stderr)
        print(f"反馈目录: {self.feedback_dir}", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print("", file=sys.stderr)
        
        try:
            while True:
                self.run_once()
                print(f"\n等待 {self.check_interval}秒后再次检查...\n", file=sys.stderr)
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            print("\n\n评估系统已停止", file=sys.stderr)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='持续信号评估后台进程')
    parser.add_argument('--interval', type=int, default=1800,
                       help='检查间隔（秒），默认1800秒（30分钟）')
    parser.add_argument('--lookback', type=int, default=24,
                       help='检查最近多少小时的交易计划，默认24小时')
    parser.add_argument('--once', action='store_true',
                       help='只运行一次评估，不持续监控')
    parser.add_argument('--feedback-dir', type=str, default=None,
                       help='反馈报告保存目录')
    
    args = parser.parse_args()
    
    feedback_dir = Path(args.feedback_dir) if args.feedback_dir else None
    
    evaluator = ContinuousSignalEvaluator(
        check_interval=args.interval,
        lookback_hours=args.lookback,
        feedback_dir=feedback_dir
    )
    
    if args.once:
        evaluator.run_once()
    else:
        evaluator.run_continuous()


if __name__ == '__main__':
    main()
