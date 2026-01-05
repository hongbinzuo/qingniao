#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从报告分析并学习，生成系统改进建议
不直接操作数据库，只生成学习报告和参数更新文件
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def main():
    """主函数 - 分析14:22信号报告并生成学习建议"""
    
    print("="*80)
    print("从14:22信号报告学习并生成改进建议")
    print("="*80)
    print("")
    
    # 从报告中提取的关键数据
    signals_data = [
        {
            'timeframe': '15m',
            'signal_type': 'short',
            'entry_price': 87824,
            'stop_loss': 88087,
            'stop_distance_pct': 0.30,
            'atr_pct': 0.08,
            'volatility': 'low',
            'result': 'stopped',
            'profit_pct': -0.30,
            'max_profit_pct': 0.16,
            'issue': '止损距离过小'
        },
        {
            'timeframe': '1h',
            'signal_type': 'long',
            'entry_price': 87018,
            'stop_loss': 86700,
            'stop_distance_pct': 0.37,
            'atr_pct': 0.81,
            'volatility': 'high',
            'result': 'missed',
            'profit_pct': 0,
            'issue': '入场价无法成交'
        }
    ]
    
    # 分析数据
    analysis = {
        'total_signals': len(signals_data),
        'stopped_count': sum(1 for s in signals_data if s['result'] == 'stopped'),
        'missed_count': sum(1 for s in signals_data if s['result'] == 'missed'),
        'stop_loss_issues': [],
        'entry_price_issues': [],
        'recommendations': []
    }
    
    # 分析止损问题
    for signal in signals_data:
        if signal['result'] == 'stopped':
            if signal['volatility'] == 'low' and signal['stop_distance_pct'] < 0.4:
                analysis['stop_loss_issues'].append({
                    'timeframe': signal['timeframe'],
                    'stop_distance_pct': signal['stop_distance_pct'],
                    'volatility': signal['volatility'],
                    'issue': '止损距离过小',
                    'max_profit_pct': signal.get('max_profit_pct', 0)
                })
            elif signal['volatility'] == 'high' and signal['stop_distance_pct'] < 1.0:
                analysis['stop_loss_issues'].append({
                    'timeframe': signal['timeframe'],
                    'stop_distance_pct': signal['stop_distance_pct'],
                    'volatility': signal['volatility'],
                    'issue': '止损距离过小'
                })
        
        elif signal['result'] == 'missed':
            analysis['entry_price_issues'].append({
                'timeframe': signal['timeframe'],
                'issue': signal['issue']
            })
    
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
    
    # 读取/创建系统参数文件
    params_file = Path(__file__).parent.parent / "trading_signals" / ".ml_models" / "system_parameters.json"
    params_file.parent.mkdir(parents=True, exist_ok=True)
    
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
    
    # 更新参数
    updated = False
    for rec in analysis['recommendations']:
        if rec['type'] == 'stop_loss':
            vol = rec['volatility']
            if vol == 'low':
                new_value = max(current_params['min_stop_distances']['low_volatility'], rec['recommended'])
                if new_value > current_params['min_stop_distances']['low_volatility']:
                    current_params['min_stop_distances']['low_volatility'] = new_value
                    updated = True
                    print(f"✅ 更新低波动市场最小止损距离: {new_value:.2f}%", file=sys.stderr)
            elif vol == 'high':
                new_value = max(current_params['min_stop_distances']['high_volatility'], rec['recommended'])
                if new_value > current_params['min_stop_distances']['high_volatility']:
                    current_params['min_stop_distances']['high_volatility'] = new_value
                    updated = True
                    print(f"✅ 更新高波动市场最小止损距离: {new_value:.2f}%", file=sys.stderr)
        
        elif rec['type'] == 'entry_price':
            if not current_params['entry_price_check']:
                current_params['entry_price_check'] = True
                updated = True
                print(f"✅ 启用入场价格成交可行性检查", file=sys.stderr)
    
    # 保存参数
    if updated:
        params_file.write_text(json.dumps(current_params, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"✅ 系统参数已更新并保存到: {params_file}", file=sys.stderr)
    else:
        print("ℹ️ 无需更新系统参数", file=sys.stderr)
    
    print("")
    
    # 生成学习报告
    report = []
    report.append("# 信号学习报告")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("## 数据统计")
    report.append("")
    report.append(f"- **总信号数**: {analysis['total_signals']}")
    report.append(f"- **止损**: {analysis['stopped_count']}")
    report.append(f"- **错过**: {analysis['missed_count']}")
    report.append("")
    
    if analysis['stop_loss_issues']:
        report.append("## 止损问题分析")
        report.append("")
        report.append(f"发现 {len(analysis['stop_loss_issues'])} 个止损相关问题:")
        report.append("")
        for issue in analysis['stop_loss_issues']:
            report.append(f"- **{issue['timeframe']} {issue['volatility']}波动**: 止损距离 {issue['stop_distance_pct']:.2f}%")
            if 'max_profit_pct' in issue:
                report.append(f"  - 最大浮盈曾达到 {issue['max_profit_pct']:.2f}%，但最终止损")
        report.append("")
    
    if analysis['entry_price_issues']:
        report.append("## 入场价格问题分析")
        report.append("")
        report.append(f"发现 {len(analysis['entry_price_issues'])} 个入场价格问题:")
        report.append("")
        for issue in analysis['entry_price_issues']:
            report.append(f"- **{issue['timeframe']}**: {issue['issue']}")
        report.append("")
    
    if analysis['recommendations']:
        report.append("## 改进建议")
        report.append("")
        for rec in analysis['recommendations']:
            report.append(f"### {rec['type']}")
            report.append("")
            report.append(f"- **问题**: {rec.get('reason', 'N/A')}")
            if 'recommended' in rec:
                if isinstance(rec['recommended'], (int, float)):
                    report.append(f"- **建议**: {rec['recommended']:.2f}%")
                else:
                    report.append(f"- **建议**: {rec['recommended']}")
            report.append("")
    
    report.append("## 系统参数更新")
    report.append("")
    report.append("```json")
    report.append(json.dumps(current_params, indent=2, ensure_ascii=False))
    report.append("```")
    report.append("")
    
    report.append("## 下一步行动")
    report.append("")
    report.append("1. ✅ 系统参数已更新")
    report.append("2. 📝 在信号生成时应用新的止损距离规则")
    report.append("3. 🔍 添加入场价格成交可行性检查功能")
    report.append("4. 📊 持续监控信号执行情况，继续学习改进")
    report.append("")
    
    # 保存报告
    report_file = Path(__file__).parent.parent / "信号学习报告_20251230.md"
    report_file.write_text("\n".join(report), encoding='utf-8')
    print(f"✅ 学习报告已保存到: {report_file}", file=sys.stderr)
    print("")
    
    # 输出报告
    print("\n".join(report))


if __name__ == "__main__":
    main()






