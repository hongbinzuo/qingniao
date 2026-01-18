#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成每日总结报告
包括模式匹配和视觉匹配的效果对比（纵向和横向）
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
OUTPUTS = ROOT / 'outputs'
REPORTS_DIR = OUTPUTS / 'daily_reports'
VISION_RESULTS = OUTPUTS / 'vision_matching'
TRADING_PLANS = OUTPUTS / 'trading_plans'
STATUS_DIR = OUTPUTS / 'auto_signal_status'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  数据库模块不可用", file=sys.stderr)


class DailySummaryReportGenerator:
    """每日总结报告生成器"""
    
    def __init__(self, trader_id='abu'):
        self.trader_id = trader_id
        if DB_AVAILABLE:
            self.db = TraderDBManager(trader_id)
        else:
            self.db = None
    
    def generate_report(self, target_date: Optional[str] = None) -> Path:
        """
        生成每日总结报告
        
        Args:
            target_date: 目标日期（YYYY-MM-DD），如果为None则使用今天
        
        Returns:
            报告文件路径
        """
        if not target_date:
            target_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"生成每日总结报告: {target_date}", file=sys.stderr)
        
        # 收集数据
        pattern_matching_stats = self._collect_pattern_matching_stats(target_date)
        vision_matching_stats = self._collect_vision_matching_stats(target_date)
        signal_stats = self._collect_signal_stats(target_date)
        feedback_stats = self._collect_feedback_stats(target_date)
        
        # 生成报告
        report_lines = []
        report_lines.append("# ABU系统每日总结报告")
        report_lines.append("")
        report_lines.append(f"**报告日期**: {target_date}")
        report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # 1. 执行摘要
        report_lines.append("## 📊 执行摘要")
        report_lines.append("")
        report_lines.append(f"- **模式匹配运行次数**: {pattern_matching_stats.get('run_count', 0)}")
        report_lines.append(f"- **视觉匹配运行次数**: {vision_matching_stats.get('run_count', 0)}")
        report_lines.append(f"- **生成信号总数**: {signal_stats.get('total_signals', 0)}")
        report_lines.append(f"- **已完成信号数**: {feedback_stats.get('completed_count', 0)}")
        report_lines.append("")
        
        # 2. 模式匹配效果
        report_lines.append("## 🔍 模式匹配效果分析")
        report_lines.append("")
        self._add_pattern_matching_section(report_lines, pattern_matching_stats)
        report_lines.append("")
        
        # 3. 视觉匹配效果
        report_lines.append("## 👁️ 视觉匹配效果分析")
        report_lines.append("")
        self._add_vision_matching_section(report_lines, vision_matching_stats)
        report_lines.append("")
        
        # 4. 横向对比（模式匹配 vs 视觉匹配）
        report_lines.append("## ⚖️ 横向对比：模式匹配 vs 视觉匹配")
        report_lines.append("")
        self._add_comparison_section(report_lines, pattern_matching_stats, vision_matching_stats)
        report_lines.append("")
        
        # 5. 纵向对比（与前一天对比）
        report_lines.append("## 📈 纵向对比：与前一天对比")
        report_lines.append("")
        self._add_longitudinal_comparison(report_lines, target_date)
        report_lines.append("")
        
        # 6. 信号质量分析
        report_lines.append("## 📊 信号质量分析")
        report_lines.append("")
        self._add_signal_quality_section(report_lines, signal_stats, feedback_stats)
        report_lines.append("")
        
        # 7. 改进建议
        report_lines.append("## 💡 改进建议")
        report_lines.append("")
        self._add_improvement_suggestions(report_lines, pattern_matching_stats, vision_matching_stats, signal_stats)
        report_lines.append("")
        
        # 保存报告
        report_file = REPORTS_DIR / f'daily_summary_{target_date.replace("-", "")}.md'
        report_file.write_text('\n'.join(report_lines), encoding='utf-8')
        
        print(f"✅ 每日报告已生成: {report_file.name}", file=sys.stderr)
        return report_file
    
    def _collect_pattern_matching_stats(self, target_date: str) -> Dict:
        """收集模式匹配统计数据"""
        stats = {
            'run_count': 0,
            'total_signals': 0,
            'avg_signals_per_run': 0,
            'timeframes': {}
        }
        
        # 从状态文件或数据库收集
        try:
            # 查找当天的状态文件
            date_prefix = target_date.replace('-', '')
            status_files = list(STATUS_DIR.glob(f'summary_{date_prefix}*.md'))
            stats['run_count'] = len(status_files)
            
            # 从数据库查询信号
            if self.db:
                signals = self.db.get_trading_signals(limit=1000)
                day_signals = [
                    s for s in signals
                    if s.get('signal_time', '').startswith(target_date)
                ]
                stats['total_signals'] = len(day_signals)
                if stats['run_count'] > 0:
                    stats['avg_signals_per_run'] = stats['total_signals'] / stats['run_count']
                
                # 按时间框架统计
                for signal in day_signals:
                    tf = signal.get('timeframe', 'unknown')
                    stats['timeframes'][tf] = stats['timeframes'].get(tf, 0) + 1
        except Exception as e:
            print(f"  [WARN] 收集模式匹配统计失败: {e}", file=sys.stderr)
        
        return stats
    
    def _collect_vision_matching_stats(self, target_date: str) -> Dict:
        """收集视觉匹配统计数据"""
        stats = {
            'run_count': 0,
            'total_matches': 0,
            'avg_matches_per_run': 0,
            'avg_vision_score': 0.0,
            'avg_algorithm_score': 0.0,
            'avg_final_score': 0.0
        }
        
        try:
            # 查找当天的视觉匹配结果文件
            date_prefix = target_date.replace('-', '')
            vision_files = list(VISION_RESULTS.glob(f'vision_results_{date_prefix}*.json'))
            stats['run_count'] = len(vision_files)
            
            all_matches = []
            for vision_file in vision_files:
                try:
                    data = json.loads(vision_file.read_text(encoding='utf-8'))
                    if isinstance(data, list):
                        all_matches.extend(data)
                except:
                    pass
            
            stats['total_matches'] = len(all_matches)
            if stats['run_count'] > 0:
                stats['avg_matches_per_run'] = stats['total_matches'] / stats['run_count']
            
            # 计算平均分数
            if all_matches:
                vision_scores = [m.get('vision_score', 0) for m in all_matches if m.get('vision_score')]
                algo_scores = [m.get('algorithm_score', 0) for m in all_matches if m.get('algorithm_score')]
                final_scores = [m.get('final_score', 0) for m in all_matches if m.get('final_score')]
                
                if vision_scores:
                    stats['avg_vision_score'] = sum(vision_scores) / len(vision_scores)
                if algo_scores:
                    stats['avg_algorithm_score'] = sum(algo_scores) / len(algo_scores)
                if final_scores:
                    stats['avg_final_score'] = sum(final_scores) / len(final_scores)
        except Exception as e:
            print(f"  [WARN] 收集视觉匹配统计失败: {e}", file=sys.stderr)
        
        return stats
    
    def _collect_signal_stats(self, target_date: str) -> Dict:
        """收集信号统计数据"""
        stats = {
            'total_signals': 0,
            'by_timeframe': {},
            'by_symbol': {},
            'avg_score': 0.0
        }
        
        try:
            if self.db:
                signals = self.db.get_trading_signals(limit=1000)
                day_signals = [
                    s for s in signals
                    if s.get('signal_time', '').startswith(target_date)
                ]
                stats['total_signals'] = len(day_signals)
                
                scores = [s.get('score', 0) for s in day_signals if s.get('score')]
                if scores:
                    stats['avg_score'] = sum(scores) / len(scores)
                
                for signal in day_signals:
                    tf = signal.get('timeframe', 'unknown')
                    stats['by_timeframe'][tf] = stats['by_timeframe'].get(tf, 0) + 1
                    
                    symbol = signal.get('symbol', 'unknown')
                    stats['by_symbol'][symbol] = stats['by_symbol'].get(symbol, 0) + 1
        except Exception as e:
            print(f"  [WARN] 收集信号统计失败: {e}", file=sys.stderr)
        
        return stats
    
    def _collect_feedback_stats(self, target_date: str) -> Dict:
        """收集反馈统计数据"""
        stats = {
            'completed_count': 0,
            'win_count': 0,
            'loss_count': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0
        }
        
        try:
            if self.db:
                conn = self.db._get_connection()
                
                # 查询当天的已完成信号
                completed = conn.execute('''
                    SELECT s.id, s.status, e.result, e.actual_profit_pct
                    FROM trading_signals s
                    LEFT JOIN signal_evaluations e ON s.id = e.signal_id
                    WHERE s.signal_time LIKE ?
                      AND s.status IN ('completed', 'stopped', 'missed', 'quick_tp', 'full_tp')
                ''', (f'{target_date}%',)).fetchall()
                
                stats['completed_count'] = len(completed)
                
                wins = 0
                losses = 0
                total_profit = 0.0
                
                for row in completed:
                    result = row[2]  # e.result
                    profit_pct = row[3] if row[3] is not None else 0.0
                    
                    if result == 'completed' or profit_pct > 0:
                        wins += 1
                    elif result == 'stopped' or profit_pct < 0:
                        losses += 1
                    
                    total_profit += profit_pct
                
                stats['win_count'] = wins
                stats['loss_count'] = losses
                if stats['completed_count'] > 0:
                    stats['win_rate'] = (wins / stats['completed_count']) * 100
                    stats['avg_profit'] = total_profit / stats['completed_count']
        except Exception as e:
            print(f"  [WARN] 收集反馈统计失败: {e}", file=sys.stderr)
        
        return stats
    
    def _add_pattern_matching_section(self, lines: List[str], stats: Dict):
        """添加模式匹配部分"""
        lines.append(f"- **运行次数**: {stats.get('run_count', 0)} 次")
        lines.append(f"- **生成信号总数**: {stats.get('total_signals', 0)} 个")
        if stats.get('run_count', 0) > 0:
            lines.append(f"- **平均每次信号数**: {stats.get('avg_signals_per_run', 0):.1f} 个")
        
        if stats.get('timeframes'):
            lines.append("")
            lines.append("**按时间框架分布**:")
            for tf, count in sorted(stats['timeframes'].items()):
                lines.append(f"  - {tf}: {count} 个")
    
    def _add_vision_matching_section(self, lines: List[str], stats: Dict):
        """添加视觉匹配部分"""
        lines.append(f"- **运行次数**: {stats.get('run_count', 0)} 次")
        lines.append(f"- **匹配总数**: {stats.get('total_matches', 0)} 个")
        if stats.get('run_count', 0) > 0:
            lines.append(f"- **平均每次匹配数**: {stats.get('avg_matches_per_run', 0):.1f} 个")
        
        if stats.get('avg_vision_score', 0) > 0:
            lines.append("")
            lines.append("**平均分数**:")
            lines.append(f"  - 算法分数: {stats.get('avg_algorithm_score', 0):.3f}")
            lines.append(f"  - 视觉分数: {stats.get('avg_vision_score', 0):.3f}")
            lines.append(f"  - 综合分数: {stats.get('avg_final_score', 0):.3f}")
    
    def _add_comparison_section(self, lines: List[str], pattern_stats: Dict, vision_stats: Dict):
        """添加横向对比部分"""
        lines.append("### 匹配数量对比")
        lines.append("")
        lines.append(f"- **模式匹配信号数**: {pattern_stats.get('total_signals', 0)} 个")
        lines.append(f"- **视觉匹配数**: {vision_stats.get('total_matches', 0)} 个")
        
        if pattern_stats.get('total_signals', 0) > 0:
            ratio = vision_stats.get('total_matches', 0) / pattern_stats.get('total_signals', 0)
            lines.append(f"- **视觉匹配覆盖率**: {ratio:.1%}")
        
        lines.append("")
        lines.append("### 运行频率对比")
        lines.append("")
        lines.append(f"- **模式匹配**: {pattern_stats.get('run_count', 0)} 次/天（每小时1次）")
        lines.append(f"- **视觉匹配**: {vision_stats.get('run_count', 0)} 次/天（每4小时1次）")
        
        if vision_stats.get('avg_vision_score', 0) > 0:
            lines.append("")
            lines.append("### 质量对比")
            lines.append("")
            lines.append(f"- **模式匹配平均评分**: {pattern_stats.get('avg_score', 0):.2f}")
            lines.append(f"- **视觉匹配平均分数**: {vision_stats.get('avg_final_score', 0):.3f}")
    
    def _add_longitudinal_comparison(self, lines: List[str], target_date: str):
        """添加纵向对比部分"""
        try:
            # 获取前一天的日期
            target_dt = datetime.strptime(target_date, '%Y-%m-%d')
            prev_date = (target_dt - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 获取前一天的报告
            prev_report_file = REPORTS_DIR / f'daily_summary_{prev_date.replace("-", "")}.md'
            
            if prev_report_file.exists():
                lines.append(f"对比日期: {prev_date}")
                lines.append("")
                
                # 收集前一天的数据
                prev_pattern_stats = self._collect_pattern_matching_stats(prev_date)
                prev_vision_stats = self._collect_vision_matching_stats(prev_date)
                prev_signal_stats = self._collect_signal_stats(prev_date)
                
                # 收集今天的数据
                today_pattern_stats = self._collect_pattern_matching_stats(target_date)
                today_vision_stats = self._collect_vision_matching_stats(target_date)
                today_signal_stats = self._collect_signal_stats(target_date)
                
                # 对比
                lines.append("**模式匹配信号数**:")
                prev_count = prev_pattern_stats.get('total_signals', 0)
                today_count = today_pattern_stats.get('total_signals', 0)
                diff = today_count - prev_count
                diff_pct = (diff / prev_count * 100) if prev_count > 0 else 0
                lines.append(f"  - 前一天: {prev_count} 个")
                lines.append(f"  - 今天: {today_count} 个")
                lines.append(f"  - 变化: {diff:+.0f} 个 ({diff_pct:+.1f}%)")
                
                lines.append("")
                lines.append("**视觉匹配数**:")
                prev_vision = prev_vision_stats.get('total_matches', 0)
                today_vision = today_vision_stats.get('total_matches', 0)
                diff_vision = today_vision - prev_vision
                diff_vision_pct = (diff_vision / prev_vision * 100) if prev_vision > 0 else 0
                lines.append(f"  - 前一天: {prev_vision} 个")
                lines.append(f"  - 今天: {today_vision} 个")
                lines.append(f"  - 变化: {diff_vision:+.0f} 个 ({diff_vision_pct:+.1f}%)")
            else:
                lines.append("⚠️ 前一天报告不存在，无法进行纵向对比")
        except Exception as e:
            lines.append(f"⚠️ 纵向对比失败: {e}")
    
    def _add_signal_quality_section(self, lines: List[str], signal_stats: Dict, feedback_stats: Dict):
        """添加信号质量部分"""
        lines.append(f"- **总信号数**: {signal_stats.get('total_signals', 0)} 个")
        lines.append(f"- **平均评分**: {signal_stats.get('avg_score', 0):.2f}")
        
        if feedback_stats.get('completed_count', 0) > 0:
            lines.append("")
            lines.append("**已完成信号统计**:")
            lines.append(f"  - 已完成: {feedback_stats.get('completed_count', 0)} 个")
            lines.append(f"  - 盈利: {feedback_stats.get('win_count', 0)} 个")
            lines.append(f"  - 亏损: {feedback_stats.get('loss_count', 0)} 个")
            lines.append(f"  - 胜率: {feedback_stats.get('win_rate', 0):.1f}%")
            lines.append(f"  - 平均收益: {feedback_stats.get('avg_profit', 0):.2f}%")
    
    def _add_improvement_suggestions(self, lines: List[str], pattern_stats: Dict, vision_stats: Dict, signal_stats: Dict):
        """添加改进建议"""
        suggestions = []
        
        # 检查模式匹配覆盖率
        if vision_stats.get('total_matches', 0) > 0 and pattern_stats.get('total_signals', 0) > 0:
            coverage = vision_stats.get('total_matches', 0) / pattern_stats.get('total_signals', 0)
            if coverage < 0.5:
                suggestions.append("视觉匹配覆盖率较低，建议增加视觉匹配频率或优化匹配算法")
        
        # 检查信号质量
        if signal_stats.get('avg_score', 0) < 70:
            suggestions.append("信号平均评分偏低，建议优化模式匹配算法或提高筛选阈值")
        
        # 检查运行频率
        if pattern_stats.get('run_count', 0) < 20:
            suggestions.append("模式匹配运行次数偏少，检查系统是否正常运行")
        
        if vision_stats.get('run_count', 0) < 4:
            suggestions.append("视觉匹配运行次数偏少，检查定时任务是否正常")
        
        if suggestions:
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"{i}. {suggestion}")
        else:
            lines.append("✅ 系统运行正常，暂无改进建议")
    
    def close(self):
        """关闭连接"""
        if self.db:
            self.db.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='生成每日总结报告')
    parser.add_argument('--date', type=str, help='目标日期（YYYY-MM-DD），默认今天')
    parser.add_argument('--trader', type=str, default='abu', help='交易员ID（默认abu）')
    
    args = parser.parse_args()
    
    generator = DailySummaryReportGenerator(args.trader)
    
    try:
        report_file = generator.generate_report(args.date)
        print(f"\n✅ 报告已生成: {report_file}", file=sys.stderr)
    finally:
        generator.close()


if __name__ == '__main__':
    main()
