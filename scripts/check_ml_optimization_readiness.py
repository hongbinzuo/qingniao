#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查机器学习优化就绪状态
评估当前数据积累情况，判断何时可以进行ML优化
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("⚠️  数据库模块不可用", file=sys.stderr)


class MLOptimizationReadinessChecker:
    """机器学习优化就绪状态检查器"""
    
    def __init__(self, trader_id='abu'):
        self.trader_id = trader_id
        if DB_AVAILABLE:
            self.db = TraderDBManager(trader_id)
        else:
            self.db = None
    
    def check_all(self) -> Dict:
        """检查所有指标"""
        print("=" * 80)
        print("机器学习优化就绪状态检查")
        print("=" * 80)
        print()
        
        if not DB_AVAILABLE or not self.db:
            print("❌ 数据库不可用，无法进行检查")
            return {}
        
        results = {}
        
        # 1. 检查已完成信号数
        print("【1/5】检查已完成信号数...")
        completed_stats = self._check_completed_signals()
        results['completed_signals'] = completed_stats
        self._print_completed_signals_status(completed_stats)
        print()
        
        # 2. 检查评估数据数
        print("【2/5】检查评估数据数...")
        evaluation_stats = self._check_evaluations()
        results['evaluations'] = evaluation_stats
        self._print_evaluations_status(evaluation_stats)
        print()
        
        # 3. 检查数据时间跨度
        print("【3/5】检查数据时间跨度...")
        time_span_stats = self._check_time_span()
        results['time_span'] = time_span_stats
        self._print_time_span_status(time_span_stats)
        print()
        
        # 4. 检查信号质量分布
        print("【4/5】检查信号质量分布...")
        quality_stats = self._check_signal_quality()
        results['quality'] = quality_stats
        self._print_quality_status(quality_stats)
        print()
        
        # 5. 综合评估和建议
        print("【5/5】综合评估和建议...")
        recommendations = self._generate_recommendations(results)
        results['recommendations'] = recommendations
        self._print_recommendations(recommendations)
        print()
        
        return results
    
    def _check_completed_signals(self) -> Dict:
        """检查已完成信号数"""
        try:
            # 查询所有状态的信号
            all_signals = self.db.get_trading_signals(limit=1000)
            
            # 统计各状态
            status_counts = {}
            completed_count = 0
            pending_count = 0
            active_count = 0
            
            for signal in all_signals:
                status = signal.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
                if status in ['completed', 'stopped', 'missed', 'quick_tp', 'full_tp']:
                    completed_count += 1
                elif status == 'pending':
                    pending_count += 1
                elif status == 'active':
                    active_count += 1
            
            # 查询signal_evaluations表
            conn = self.db._get_connection()
            eval_count = conn.execute('SELECT COUNT(*) FROM signal_evaluations').fetchone()[0]
            
            return {
                'total_signals': len(all_signals),
                'completed_count': completed_count,
                'pending_count': pending_count,
                'active_count': active_count,
                'evaluation_count': eval_count,
                'status_counts': status_counts
            }
        except Exception as e:
            print(f"  [ERROR] 检查失败: {e}", file=sys.stderr)
            return {}
    
    def _check_evaluations(self) -> Dict:
        """检查评估数据数"""
        try:
            conn = self.db._get_connection()
            
            # 统计评估结果
            eval_results = conn.execute('''
                SELECT result, COUNT(*) as count
                FROM signal_evaluations
                GROUP BY result
            ''').fetchall()
            
            total_eval = conn.execute('SELECT COUNT(*) FROM signal_evaluations').fetchone()[0]
            
            result_counts = {row[0]: row[1] for row in eval_results}
            
            return {
                'total_evaluations': total_eval,
                'result_counts': result_counts
            }
        except Exception as e:
            print(f"  [ERROR] 检查失败: {e}", file=sys.stderr)
            return {}
    
    def _check_time_span(self) -> Dict:
        """检查数据时间跨度"""
        try:
            # 查询最早和最晚的信号时间
            conn = self.db._get_connection()
            
            earliest = conn.execute('''
                SELECT MIN(signal_time) FROM trading_signals
                WHERE signal_time IS NOT NULL
            ''').fetchone()[0]
            
            latest = conn.execute('''
                SELECT MAX(signal_time) FROM trading_signals
                WHERE signal_time IS NOT NULL
            ''').fetchone()[0]
            
            if earliest and latest:
                try:
                    earliest_dt = datetime.fromisoformat(earliest.replace('Z', '+00:00'))
                    latest_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
                    time_span = (latest_dt - earliest_dt).days
                except:
                    time_span = 0
            else:
                time_span = 0
            
            return {
                'earliest_signal': earliest,
                'latest_signal': latest,
                'time_span_days': time_span
            }
        except Exception as e:
            print(f"  [ERROR] 检查失败: {e}", file=sys.stderr)
            return {}
    
    def _check_signal_quality(self) -> Dict:
        """检查信号质量分布"""
        try:
            conn = self.db._get_connection()
            
            # 查询已完成的信号及其评估
            completed_signals = conn.execute('''
                SELECT s.id, s.symbol, s.timeframe, s.signal_type, s.status,
                       e.result, e.actual_profit_pct
                FROM trading_signals s
                LEFT JOIN signal_evaluations e ON s.id = e.signal_id
                WHERE s.status IN ('completed', 'stopped', 'missed', 'quick_tp', 'full_tp')
                LIMIT 100
            ''').fetchall()
            
            if not completed_signals:
                return {'total': 0}
            
            # 统计胜率
            wins = 0
            losses = 0
            missed = 0
            total_profit = 0.0
            
            for row in completed_signals:
                result = row[5]  # e.result
                profit_pct = row[6] if row[6] is not None else 0.0
                
                if result == 'completed' or profit_pct > 0:
                    wins += 1
                elif result == 'stopped' or profit_pct < 0:
                    losses += 1
                elif result == 'missed':
                    missed += 1
                
                total_profit += profit_pct
            
            total = len(completed_signals)
            win_rate = (wins / total * 100) if total > 0 else 0
            avg_profit = total_profit / total if total > 0 else 0
            
            return {
                'total': total,
                'wins': wins,
                'losses': losses,
                'missed': missed,
                'win_rate': win_rate,
                'avg_profit_pct': avg_profit
            }
        except Exception as e:
            print(f"  [ERROR] 检查失败: {e}", file=sys.stderr)
            return {}
    
    def _print_completed_signals_status(self, stats: Dict):
        """打印已完成信号状态"""
        if not stats:
            print("  ❌ 无法获取数据")
            return
        
        total = stats.get('total_signals', 0)
        completed = stats.get('completed_count', 0)
        pending = stats.get('pending_count', 0)
        active = stats.get('active_count', 0)
        eval_count = stats.get('evaluation_count', 0)
        
        print(f"  📊 总信号数: {total}")
        print(f"  ✅ 已完成: {completed}")
        print(f"  ⏳ 待激活: {pending}")
        print(f"  🔄 交易中: {active}")
        print(f"  📝 评估数据: {eval_count}")
        
        # 评估状态
        if completed >= 100:
            print(f"  ✅ 数据充足（≥ 100条），可以进行完整ML训练")
        elif completed >= 50:
            print(f"  ⚠️  数据中等（50-99条），可以进行基础ML训练")
        elif completed >= 10:
            print(f"  ⚠️  数据较少（10-49条），可以开始增量学习")
        else:
            print(f"  ❌ 数据不足（< 10条），需要继续积累")
    
    def _print_evaluations_status(self, stats: Dict):
        """打印评估数据状态"""
        if not stats:
            print("  ❌ 无法获取数据")
            return
        
        total = stats.get('total_evaluations', 0)
        result_counts = stats.get('result_counts', {})
        
        print(f"  📝 总评估数: {total}")
        if result_counts:
            for result, count in result_counts.items():
                print(f"    - {result}: {count}")
        
        if total >= 100:
            print(f"  ✅ 评估数据充足（≥ 100条）")
        elif total >= 50:
            print(f"  ⚠️  评估数据中等（50-99条）")
        elif total >= 10:
            print(f"  ⚠️  评估数据较少（10-49条）")
        else:
            print(f"  ❌ 评估数据不足（< 10条）")
    
    def _print_time_span_status(self, stats: Dict):
        """打印时间跨度状态"""
        if not stats:
            print("  ❌ 无法获取数据")
            return
        
        time_span = stats.get('time_span_days', 0)
        earliest = stats.get('earliest_signal', 'N/A')
        latest = stats.get('latest_signal', 'N/A')
        
        print(f"  📅 时间跨度: {time_span} 天")
        print(f"  📅 最早信号: {earliest}")
        print(f"  📅 最新信号: {latest}")
        
        if time_span >= 28:
            print(f"  ✅ 时间跨度充足（≥ 4周）")
        elif time_span >= 14:
            print(f"  ⚠️  时间跨度中等（2-4周）")
        elif time_span >= 7:
            print(f"  ⚠️  时间跨度较短（1-2周）")
        else:
            print(f"  ❌ 时间跨度不足（< 1周）")
    
    def _print_quality_status(self, stats: Dict):
        """打印信号质量状态"""
        if not stats or stats.get('total', 0) == 0:
            print("  ❌ 无已完成信号，无法评估质量")
            return
        
        total = stats.get('total', 0)
        wins = stats.get('wins', 0)
        losses = stats.get('losses', 0)
        win_rate = stats.get('win_rate', 0)
        avg_profit = stats.get('avg_profit_pct', 0)
        
        print(f"  📊 已完成信号: {total}")
        print(f"  ✅ 盈利: {wins}")
        print(f"  ❌ 亏损: {losses}")
        print(f"  📈 胜率: {win_rate:.1f}%")
        print(f"  💰 平均收益: {avg_profit:.2f}%")
        
        if win_rate >= 50:
            print(f"  ✅ 胜率良好（≥ 50%）")
        elif win_rate >= 40:
            print(f"  ⚠️  胜率一般（40-50%）")
        else:
            print(f"  ❌ 胜率偏低（< 40%），需要优化")
    
    def _generate_recommendations(self, results: Dict) -> List[Dict]:
        """生成优化建议"""
        recommendations = []
        
        completed_stats = results.get('completed_signals', {})
        completed_count = completed_stats.get('completed_count', 0)
        eval_count = completed_stats.get('evaluation_count', 0)
        
        time_span_stats = results.get('time_span', {})
        time_span = time_span_stats.get('time_span_days', 0)
        
        quality_stats = results.get('quality', {})
        win_rate = quality_stats.get('win_rate', 0)
        
        # 建议1: 数据积累
        if completed_count < 10:
            recommendations.append({
                'priority': 'P0',
                'type': 'data_accumulation',
                'action': '继续运行系统，积累已完成信号',
                'target': f'目标: {10 - completed_count} 条已完成信号',
                'script': None
            })
        elif completed_count < 50:
            recommendations.append({
                'priority': 'P0',
                'type': 'incremental_learning',
                'action': '可以开始增量学习',
                'target': f'当前: {completed_count} 条，目标: 50 条',
                'script': 'python scripts/abu/abu_incremental_learning.py'
            })
        elif completed_count < 100:
            recommendations.append({
                'priority': 'P0',
                'type': 'ml_training',
                'action': '可以开始ML模型训练',
                'target': f'当前: {completed_count} 条，目标: 100 条',
                'script': 'python src/ml_dl/comprehensive_training.py'
            })
        else:
            recommendations.append({
                'priority': 'P0',
                'type': 'full_retrain',
                'action': '数据充足，可以进行完整模型重训练',
                'target': f'当前: {completed_count} 条',
                'script': 'python scripts/abu/abu_full_ml_retrain.py'
            })
        
        # 建议2: 评估数据
        if eval_count < completed_count:
            recommendations.append({
                'priority': 'P1',
                'type': 'evaluation',
                'action': '需要为已完成信号创建评估数据',
                'target': f'缺少: {completed_count - eval_count} 条评估',
                'script': 'python src/ml_dl/prepare_training_data.py'
            })
        
        # 建议3: 时间跨度
        if time_span < 7:
            recommendations.append({
                'priority': 'P1',
                'type': 'time_span',
                'action': '数据时间跨度较短，建议继续积累',
                'target': f'当前: {time_span} 天，建议: ≥ 7 天',
                'script': None
            })
        
        # 建议4: 胜率优化
        if win_rate < 40 and completed_count >= 10:
            recommendations.append({
                'priority': 'P0',
                'type': 'quality_optimization',
                'action': '胜率偏低，建议立即优化',
                'target': f'当前胜率: {win_rate:.1f}%，目标: ≥ 50%',
                'script': 'python scripts/abu/abu_optimize_signal_quality.py'
            })
        
        return recommendations
    
    def _print_recommendations(self, recommendations: List[Dict]):
        """打印优化建议"""
        if not recommendations:
            print("  ✅ 当前状态良好，无需特殊操作")
            return
        
        print("  📋 优化建议:")
        for i, rec in enumerate(recommendations, 1):
            priority = rec.get('priority', 'P?')
            action = rec.get('action', 'N/A')
            target = rec.get('target', '')
            script = rec.get('script', '')
            
            print(f"  {i}. [{priority}] {action}")
            if target:
                print(f"     {target}")
            if script:
                print(f"     执行: {script}")
    
    def close(self):
        """关闭连接"""
        if self.db:
            self.db.close()


def main():
    """主函数"""
    checker = MLOptimizationReadinessChecker('abu')
    
    try:
        results = checker.check_all()
        
        # 生成报告文件
        report_file = ROOT / 'outputs' / 'ml_optimization_readiness_report.md'
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        report_lines = []
        report_lines.append("# 机器学习优化就绪状态报告")
        report_lines.append("")
        report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # 添加检查结果
        completed_stats = results.get('completed_signals', {})
        report_lines.append("## 数据积累情况")
        report_lines.append("")
        report_lines.append(f"- **总信号数**: {completed_stats.get('total_signals', 0)}")
        report_lines.append(f"- **已完成信号**: {completed_stats.get('completed_count', 0)}")
        report_lines.append(f"- **评估数据**: {completed_stats.get('evaluation_count', 0)}")
        report_lines.append("")
        
        # 添加建议
        recommendations = results.get('recommendations', [])
        if recommendations:
            report_lines.append("## 优化建议")
            report_lines.append("")
            for rec in recommendations:
                report_lines.append(f"### [{rec.get('priority', 'P?')}] {rec.get('action', 'N/A')}")
                report_lines.append(f"- **目标**: {rec.get('target', '')}")
                if rec.get('script'):
                    report_lines.append(f"- **执行**: `{rec.get('script')}`")
                report_lines.append("")
        
        report_file.write_text('\n'.join(report_lines), encoding='utf-8')
        print(f"\n✅ 报告已保存到: {report_file}")
        
    finally:
        checker.close()


if __name__ == '__main__':
    main()
