#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从信号执行报告学习并改进系统
1. 解析报告数据
2. 录入数据库
3. 分析失败原因
4. 更新系统参数
"""

import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from db_manager_trader import TraderDBManager

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


class SignalLearningSystem:
    """信号学习系统"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        self.learning_data_path = Path(__file__).parent.parent / "trading_signals" / ".ml_models"
        self.learning_data_path.mkdir(parents=True, exist_ok=True)
    
    def parse_report(self, report_path: str) -> List[Dict]:
        """解析报告文件，提取信号数据"""
        # 尝试多种路径
        possible_paths = [
            Path(report_path),
            Path(__file__).parent.parent / report_path,
            Path(report_path).resolve()
        ]
        
        report_file = None
        for path in possible_paths:
            if path.exists():
                report_file = path
                break
        
        if not report_file or not report_file.exists():
            print(f"❌ 报告文件不存在: {report_path}", file=sys.stderr)
            print(f"   尝试的路径: {[str(p) for p in possible_paths]}", file=sys.stderr)
            return []
        
        content = report_file.read_text(encoding='utf-8')
        signals = []
        
        # 提取信号生成时间
        time_match = re.search(r'\*\*信号生成时间\*\*:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', content)
        signal_time = time_match.group(1) if time_match else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 解析信号1: 15分钟做空信号
        signal1_match = re.search(
            r'## 信号1: 15分钟做空信号.*?## 信号2:',
            content,
            re.DOTALL
        )
        if signal1_match:
            signal1_content = signal1_match.group(0)
            signal1 = self._parse_signal_details(signal1_content, signal_time, '15m', 'short')
            if signal1:
                signals.append(signal1)
        
        # 解析信号2: 1小时做多信号
        signal2_match = re.search(
            r'## 信号2: 1小时做多信号.*?(?=## |$)',
            content,
            re.DOTALL
        )
        if signal2_match:
            signal2_content = signal2_match.group(0)
            signal2 = self._parse_signal_details(signal2_content, signal_time, '1h', 'long')
            if signal2:
                signals.append(signal2)
        
        return signals
    
    def _parse_signal_details(self, content: str, signal_time: str, timeframe: str, signal_type: str) -> Optional[Dict]:
        """解析单个信号的详细信息"""
        signal = {
            'signal_time': signal_time,
            'timeframe': timeframe,
            'signal_type': signal_type,
            'system_name': 'de'
        }
        
        # 提取入场价格
        entry_match = re.search(r'\*\*入场价格\*\*:\s*\$?([\d,]+\.?\d*)', content)
        if entry_match:
            signal['entry_price'] = float(entry_match.group(1).replace(',', ''))
        
        # 提取止损价格
        stop_loss_match = re.search(r'\*\*止损价格\*\*:\s*\$?([\d,]+\.?\d*)', content)
        if stop_loss_match:
            signal['stop_loss'] = float(stop_loss_match.group(1).replace(',', ''))
        
        # 提取止盈1
        tp1_match = re.search(r'\*\*止盈1\*\*:\s*\$?([\d,]+\.?\d*)', content)
        if tp1_match:
            signal['take_profit_1'] = float(tp1_match.group(1).replace(',', ''))
        
        # 提取止盈2
        tp2_match = re.search(r'\*\*止盈2\*\*:\s*\$?([\d,]+\.?\d*)', content)
        if tp2_match:
            signal['take_profit_2'] = float(tp2_match.group(1).replace(',', ''))
        
        # 提取止损距离
        stop_distance_match = re.search(r'\*\*止损距离\*\*:\s*([\d.]+)%', content)
        if stop_distance_match:
            signal['stop_distance_pct'] = float(stop_distance_match.group(1))
        
        # 提取理论盈亏比
        rr_match = re.search(r'\*\*理论盈亏比\*\*:\s*([\d.]+):1', content)
        if rr_match:
            signal['risk_reward_ratio'] = float(rr_match.group(1))
        
        # 提取波动率
        atr_match = re.search(r'ATR:\s*([\d.]+)%', content)
        if atr_match:
            signal['atr_pct'] = float(atr_match.group(1))
        
        # 提取模型
        model_match = re.search(r'\*\*模型\*\*:\s*(.+)', content)
        if model_match:
            signal['entry_model'] = model_match.group(1).strip()
        
        # 提取强度
        strength_match = re.search(r'\*\*强度\*\*:\s*(\w+)', content)
        if strength_match:
            signal['strength'] = strength_match.group(1).lower()
        
        # 提取执行结果
        result_match = re.search(r'\*\*结果\*\*:\s*([❌✅⚠️🔄]+)?\s*(\w+)', content)
        if result_match:
            result_text = result_match.group(2).lower()
            if '止损' in result_text or 'stopped' in result_text:
                signal['result'] = 'stopped'
            elif '错过' in result_text or 'missed' in result_text:
                signal['result'] = 'missed'
            elif '止盈' in result_text or 'completed' in result_text:
                signal['result'] = 'completed'
            else:
                signal['result'] = 'pending'
        
        # 提取最终盈亏
        pnl_match = re.search(r'\*\*最终盈亏\*\*:\s*[📈📉]?\s*([+-]?[\d.]+)%', content)
        if pnl_match:
            signal['actual_profit_pct'] = float(pnl_match.group(1))
        
        # 提取最大浮盈/浮亏
        max_profit_match = re.search(r'\*\*最大浮盈\*\*:\s*([+-]?[\d.]+)%', content)
        if max_profit_match:
            signal['max_profit_pct'] = float(max_profit_match.group(1))
        
        max_loss_match = re.search(r'\*\*最大浮亏\*\*:\s*([+-]?[\d.]+)%', content)
        if max_loss_match:
            signal['max_loss_pct'] = float(max_loss_match.group(1))
        
        # 提取失败原因
        failure_reasons = []
        if '止损距离过小' in content:
            failure_reasons.append('stop_loss_too_tight')
        if '入场价无法成交' in content or '无法成交' in content:
            failure_reasons.append('entry_price_unreachable')
        if '错过' in content:
            failure_reasons.append('missed_opportunity')
        
        signal['failure_reasons'] = failure_reasons
        
        return signal if signal.get('entry_price') else None
    
    def record_signals(self, signals: List[Dict]) -> List[int]:
        """将信号录入数据库"""
        signal_ids = []
        
        for signal in signals:
            try:
                signal_id = self.db.add_trading_signal(
                    signal_time=signal['signal_time'],
                    timeframe=signal['timeframe'],
                    signal_type=signal['signal_type'],
                    entry_price=signal.get('entry_price'),
                    stop_loss=signal.get('stop_loss'),
                    take_profit_1=signal.get('take_profit_1'),
                    take_profit_2=signal.get('take_profit_2'),
                    entry_model=signal.get('entry_model'),
                    strength=signal.get('strength'),
                    risk_reward_ratio=signal.get('risk_reward_ratio'),
                    volatility_level=self._get_volatility_level(signal.get('atr_pct')),
                    system_name=signal.get('system_name', 'de')
                )
                signal_ids.append(signal_id)
                print(f"✅ 已录入信号: ID={signal_id}, {signal['timeframe']} {signal['signal_type']}", file=sys.stderr)
                
                # 如果有执行结果，添加评估记录
                if signal.get('result') and signal['result'] != 'pending':
                    self._add_evaluation(signal_id, signal)
                    
            except Exception as e:
                print(f"❌ 录入信号失败: {e}", file=sys.stderr)
                continue
        
        return signal_ids
    
    def _get_volatility_level(self, atr_pct: Optional[float]) -> Optional[str]:
        """根据ATR判断波动率水平"""
        if atr_pct is None:
            return None
        if atr_pct < 0.2:
            return 'low'
        elif atr_pct < 0.5:
            return 'medium'
        else:
            return 'high'
    
    def _add_evaluation(self, signal_id: int, signal: Dict):
        """添加信号评估记录"""
        try:
            result = signal.get('result', 'pending')
            evaluation_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 确定评估结果
            if result == 'stopped':
                stop_loss_hit = 1
                missed = 0
            elif result == 'missed':
                stop_loss_hit = 0
                missed = 1
            else:
                stop_loss_hit = 0
                missed = 0
            
            # 构建notes
            notes_parts = []
            if signal.get('failure_reasons'):
                notes_parts.append(f"失败原因: {', '.join(signal['failure_reasons'])}")
            if signal.get('stop_distance_pct'):
                notes_parts.append(f"止损距离: {signal['stop_distance_pct']:.2f}%")
            if signal.get('atr_pct'):
                notes_parts.append(f"ATR: {signal['atr_pct']:.2f}%")
            
            notes = "; ".join(notes_parts) if notes_parts else None
            
            self.db.add_signal_evaluation(
                signal_id=signal_id,
                evaluation_time=evaluation_time,
                result=result,
                actual_entry_price=signal.get('entry_price'),
                actual_exit_price=signal.get('stop_loss') if result == 'stopped' else None,
                actual_profit_pct=signal.get('actual_profit_pct', 0),
                stop_loss_hit=stop_loss_hit,
                take_profit_1_hit=1 if result == 'completed' and signal.get('take_profit_1') else 0,
                take_profit_2_hit=1 if result == 'completed' and signal.get('take_profit_2') else 0,
                missed=missed,
                notes=notes
            )
            print(f"✅ 已添加评估记录: signal_id={signal_id}, result={result}", file=sys.stderr)
        except Exception as e:
            print(f"❌ 添加评估记录失败: {e}", file=sys.stderr)
    
    def analyze_and_learn(self) -> Dict:
        """分析信号数据，提取经验教训"""
        print("="*80)
        print("分析信号数据，提取经验教训")
        print("="*80)
        print("", file=sys.stderr)
        
        # 查询最近的信号评估
        conn = self.db._get_connection()
        
        # 获取所有信号评估
        evaluations = conn.execute('''
            SELECT 
                s.timeframe,
                s.signal_type,
                s.entry_price,
                s.stop_loss,
                s.risk_reward_ratio,
                s.volatility_level,
                e.result,
                e.actual_profit_pct,
                e.stop_loss_hit,
                e.missed,
                e.notes
            FROM signal_evaluations e
            JOIN trading_signals s ON e.signal_id = s.id
            WHERE s.system_name = 'de'
            ORDER BY e.evaluation_time DESC
            LIMIT 100
        ''').fetchall()
        
        if not evaluations:
            print("⚠️ 没有找到评估数据", file=sys.stderr)
            return {}
        
        # 分析数据
        analysis = {
            'total_signals': len(evaluations),
            'stopped_count': 0,
            'missed_count': 0,
            'completed_count': 0,
            'stop_loss_issues': [],
            'entry_price_issues': [],
            'recommendations': []
        }
        
        for eval_data in evaluations:
            timeframe, signal_type, entry_price, stop_loss, rr, vol_level, result, profit_pct, stop_hit, missed, notes = eval_data
            
            if result == 'stopped':
                analysis['stopped_count'] += 1
                # 分析止损问题
                if entry_price and stop_loss:
                    if signal_type == 'long':
                        stop_distance_pct = ((entry_price - stop_loss) / entry_price) * 100
                    else:
                        stop_distance_pct = ((stop_loss - entry_price) / entry_price) * 100
                    
                    # 检查止损是否过小
                    if vol_level == 'low' and stop_distance_pct < 0.4:
                        analysis['stop_loss_issues'].append({
                            'timeframe': timeframe,
                            'stop_distance_pct': stop_distance_pct,
                            'volatility': vol_level,
                            'issue': 'stop_loss_too_tight_low_vol'
                        })
                    elif vol_level == 'high' and stop_distance_pct < 1.0:
                        analysis['stop_loss_issues'].append({
                            'timeframe': timeframe,
                            'stop_distance_pct': stop_distance_pct,
                            'volatility': vol_level,
                            'issue': 'stop_loss_too_tight_high_vol'
                        })
            
            elif result == 'missed' or missed:
                analysis['missed_count'] += 1
                if notes and 'entry_price_unreachable' in notes:
                    analysis['entry_price_issues'].append({
                        'timeframe': timeframe,
                        'issue': 'entry_price_unreachable'
                    })
            
            elif result == 'completed':
                analysis['completed_count'] += 1
        
        # 生成建议
        if analysis['stop_loss_issues']:
            low_vol_issues = [i for i in analysis['stop_loss_issues'] if i['volatility'] == 'low']
            high_vol_issues = [i for i in analysis['stop_loss_issues'] if i['volatility'] == 'high']
            
            if low_vol_issues:
                avg_stop = sum(i['stop_distance_pct'] for i in low_vol_issues) / len(low_vol_issues)
                analysis['recommendations'].append({
                    'type': 'stop_loss',
                    'volatility': 'low',
                    'current_avg': avg_stop,
                    'recommended': 0.4,
                    'reason': '低波动市场止损距离过小，建议至少0.4%'
                })
            
            if high_vol_issues:
                avg_stop = sum(i['stop_distance_pct'] for i in high_vol_issues) / len(high_vol_issues)
                analysis['recommendations'].append({
                    'type': 'stop_loss',
                    'volatility': 'high',
                    'current_avg': avg_stop,
                    'recommended': 1.0,
                    'reason': '高波动市场止损距离过小，建议至少1.0%'
                })
        
        if analysis['entry_price_issues']:
            analysis['recommendations'].append({
                'type': 'entry_price',
                'issue': '入场价无法成交',
                'recommended': '添加成交可行性检查',
                'reason': '入场价可能是技术位而非当前价格，需要检查成交可行性'
            })
        
        return analysis
    
    def update_system_parameters(self, analysis: Dict) -> Dict:
        """根据分析结果更新系统参数"""
        print("="*80)
        print("更新系统参数")
        print("="*80)
        print("", file=sys.stderr)
        
        # 读取当前参数
        params_file = self.learning_data_path / "system_parameters.json"
        if params_file.exists():
            current_params = json.loads(params_file.read_text(encoding='utf-8'))
        else:
            current_params = {
                'stop_loss_multipliers': {
                    'low_volatility': 1.0,
                    'medium_volatility': 1.0,
                    'high_volatility': 1.0
                },
                'min_stop_distances': {
                    'low_volatility': 0.3,
                    'medium_volatility': 0.5,
                    'high_volatility': 0.8
                },
                'entry_price_check': False
            }
        
        # 根据分析结果更新参数
        updated = False
        
        for rec in analysis.get('recommendations', []):
            if rec['type'] == 'stop_loss':
                vol = rec['volatility']
                if vol == 'low':
                    current_params['min_stop_distances']['low_volatility'] = max(
                        current_params['min_stop_distances']['low_volatility'],
                        rec['recommended']
                    )
                    updated = True
                    print(f"✅ 更新低波动市场最小止损距离: {rec['recommended']:.2f}%", file=sys.stderr)
                elif vol == 'high':
                    current_params['min_stop_distances']['high_volatility'] = max(
                        current_params['min_stop_distances']['high_volatility'],
                        rec['recommended']
                    )
                    updated = True
                    print(f"✅ 更新高波动市场最小止损距离: {rec['recommended']:.2f}%", file=sys.stderr)
            
            elif rec['type'] == 'entry_price':
                current_params['entry_price_check'] = True
                updated = True
                print(f"✅ 启用入场价格成交可行性检查", file=sys.stderr)
        
        # 保存更新后的参数
        if updated:
            params_file.write_text(json.dumps(current_params, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"✅ 系统参数已更新并保存到: {params_file}", file=sys.stderr)
        else:
            print("ℹ️ 无需更新系统参数", file=sys.stderr)
        
        print("", file=sys.stderr)
        return current_params
    
    def generate_learning_report(self, analysis: Dict, params: Dict):
        """生成学习报告"""
        report = []
        report.append("# 信号学习报告")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        report.append("## 数据统计")
        report.append("")
        report.append(f"- **总信号数**: {analysis.get('total_signals', 0)}")
        report.append(f"- **止损**: {analysis.get('stopped_count', 0)}")
        report.append(f"- **错过**: {analysis.get('missed_count', 0)}")
        report.append(f"- **完成**: {analysis.get('completed_count', 0)}")
        report.append("")
        
        if analysis.get('stop_loss_issues'):
            report.append("## 止损问题分析")
            report.append("")
            report.append(f"发现 {len(analysis['stop_loss_issues'])} 个止损相关问题")
            report.append("")
            for issue in analysis['stop_loss_issues'][:5]:
                report.append(f"- {issue['timeframe']} {issue['volatility']}波动: 止损距离 {issue['stop_distance_pct']:.2f}%")
            report.append("")
        
        if analysis.get('entry_price_issues'):
            report.append("## 入场价格问题分析")
            report.append("")
            report.append(f"发现 {len(analysis['entry_price_issues'])} 个入场价格问题")
            report.append("")
        
        if analysis.get('recommendations'):
            report.append("## 改进建议")
            report.append("")
            for rec in analysis['recommendations']:
                report.append(f"### {rec['type']}")
                report.append("")
                report.append(f"- **问题**: {rec.get('reason', 'N/A')}")
                if 'recommended' in rec:
                    report.append(f"- **建议**: {rec['recommended']}")
                report.append("")
        
        report.append("## 系统参数更新")
        report.append("")
        report.append("```json")
        report.append(json.dumps(params, indent=2, ensure_ascii=False))
        report.append("```")
        report.append("")
        
        return "\n".join(report)
    
    def close(self):
        """关闭连接"""
        self.db.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='从信号执行报告学习并改进系统')
    parser.add_argument('report_path', help='报告文件路径')
    parser.add_argument('--trader-id', default='de', help='交易员ID')
    
    args = parser.parse_args()
    
    system = SignalLearningSystem(trader_id=args.trader_id)
    
    try:
        # 1. 解析报告
        print("="*80)
        print("解析报告文件")
        print("="*80)
        print("", file=sys.stderr)
        
        signals = system.parse_report(args.report_path)
        print(f"✅ 解析到 {len(signals)} 个信号", file=sys.stderr)
        print("", file=sys.stderr)
        
        # 2. 录入数据库
        if signals:
            print("="*80)
            print("录入信号到数据库")
            print("="*80)
            print("", file=sys.stderr)
            
            signal_ids = system.record_signals(signals)
            print(f"✅ 成功录入 {len(signal_ids)} 个信号", file=sys.stderr)
            print("", file=sys.stderr)
        
        # 3. 分析学习
        analysis = system.analyze_and_learn()
        
        # 4. 更新参数
        params = system.update_system_parameters(analysis)
        
        # 5. 生成报告
        report = system.generate_learning_report(analysis, params)
        
        # 保存报告
        report_file = Path(__file__).parent.parent / "信号学习报告_20251230.md"
        report_file.write_text(report, encoding='utf-8')
        print(f"✅ 学习报告已保存到: {report_file}", file=sys.stderr)
        print("", file=sys.stderr)
        
        # 输出报告
        print(report)
        
    finally:
        system.close()


if __name__ == "__main__":
    main()

