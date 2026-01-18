#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Gemini分析结果质量（独立模块的一部分）

功能：
- 检查pattern_library表中gemini_annotation_json的覆盖率
- 统计模式组合分布、交易参数完整性
- 生成质量报告

使用：
    python scripts/abu_verify_gemini_analysis.py \
        --output outputs/abu_gemini_verification_report.md
"""

import sys
import json
from pathlib import Path
from collections import Counter
from typing import Dict, List, Any

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


def verify_gemini_analysis(output_file: Path = None):
    """验证Gemini分析结果质量"""
    db = TraderDBManager('abu')
    conn = db._get_connection()
    
    # 统计总数
    total_count = conn.execute('SELECT COUNT(*) FROM pattern_library').fetchone()[0]
    
    # 统计有Gemini标注的数量
    with_gemini = conn.execute('''
        SELECT COUNT(*) FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL 
          AND gemini_annotation_json != ''
    ''').fetchone()[0]
    
    # 统计各种质量指标
    patterns_with_signals = 0
    patterns_with_probability = 0
    patterns_with_entry = 0
    patterns_with_combo = 0
    
    pattern_combos = Counter()
    pattern_types = Counter()
    confidence_scores = []
    probability_scores = []
    
    records_with_gemini = conn.execute('''
        SELECT id, gemini_annotation_json, pattern_type
        FROM pattern_library
        WHERE gemini_annotation_json IS NOT NULL 
          AND gemini_annotation_json != ''
    ''').fetchall()
    
    for record_id, gemini_json, pattern_type in records_with_gemini:
        try:
            ann = json.loads(gemini_json)
            
            # 统计模式类型
            if pattern_type:
                pattern_types[pattern_type] += 1
            
            # 统计模式组合
            combo = ann.get('pattern_combination', '')
            if combo:
                patterns_with_combo += 1
                pattern_combos[combo] += 1
            
            # 统计交易信号
            signals = ann.get('trading_signals', [])
            if signals:
                patterns_with_signals += 1
                
                for sig in signals:
                    if sig.get('probability'):
                        patterns_with_probability += 1
                        probability_scores.append(sig['probability'])
                    if sig.get('entry_price_hint'):
                        patterns_with_entry += 1
            
            # 统计置信度
            conf = ann.get('confidence', 0)
            if conf > 0:
                confidence_scores.append(conf)
        
        except Exception as e:
            print(f"  解析失败 (id={record_id}): {e}", file=sys.stderr)
            continue
    
    # 计算覆盖率
    coverage_pct = (with_gemini / total_count * 100) if total_count > 0 else 0
    
    # 计算平均置信度
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    avg_probability = sum(probability_scores) / len(probability_scores) if probability_scores else 0
    
    # 生成报告
    report = {
        "summary": {
            "total_patterns": total_count,
            "with_gemini_annotation": with_gemini,
            "coverage_percentage": round(coverage_pct, 2),
            "patterns_with_combination": patterns_with_combo,
            "patterns_with_signals": patterns_with_signals,
            "patterns_with_probability": patterns_with_probability,
            "patterns_with_entry_price": patterns_with_entry,
            "average_confidence": round(avg_confidence, 3),
            "average_probability": round(avg_probability, 1) if avg_probability > 0 else None
        },
        "pattern_type_distribution": dict(pattern_types.most_common(20)),
        "pattern_combination_top10": dict(pattern_combos.most_common(10)),
        "quality_metrics": {
            "signal_completeness": round(patterns_with_signals / with_gemini * 100, 2) if with_gemini > 0 else 0,
            "probability_completeness": round(patterns_with_probability / with_gemini * 100, 2) if with_gemini > 0 else 0,
            "entry_price_completeness": round(patterns_with_entry / with_gemini * 100, 2) if with_gemini > 0 else 0
        }
    }
    
    db.close()
    return report


def generate_markdown_report(report: Dict, output_file: Path):
    """生成Markdown格式的报告"""
    lines = [
        "# Gemini分析结果验证报告",
        "",
        f"生成时间: {Path(__file__).stat().st_mtime}",
        "",
        "## 📊 总体统计",
        "",
        f"- **总模式数**: {report['summary']['total_patterns']}",
        f"- **有Gemini标注**: {report['summary']['with_gemini_annotation']}",
        f"- **覆盖率**: {report['summary']['coverage_percentage']}%",
        "",
        "## 📈 质量指标",
        "",
        f"- **平均置信度**: {report['summary']['average_confidence']:.3f}",
        f"- **平均概率**: {report['summary']['average_probability']:.1f}%" if report['summary']['average_probability'] else "- **平均概率**: N/A",
        f"- **有模式组合**: {report['summary']['patterns_with_combination']} 条",
        f"- **有交易信号**: {report['summary']['patterns_with_signals']} 条",
        f"- **有概率信息**: {report['summary']['patterns_with_probability']} 条",
        f"- **有入场价格**: {report['summary']['patterns_with_entry_price']} 条",
        "",
        "## 📋 完整性指标",
        "",
        f"- **交易信号完整性**: {report['quality_metrics']['signal_completeness']:.1f}%",
        f"- **概率信息完整性**: {report['quality_metrics']['probability_completeness']:.1f}%",
        f"- **入场价格完整性**: {report['quality_metrics']['entry_price_completeness']:.1f}%",
        "",
        "## 🏷️ 模式类型分布",
        "",
        "| 模式类型 | 数量 |",
        "|---|---|"
    ]
    
    for ptype, count in report['pattern_type_distribution'].items():
        lines.append(f"| {ptype} | {count} |")
    
    lines.extend([
        "",
        "## 🔗 模式组合 Top10",
        "",
        "| 组合 | 数量 |",
        "|---|---|"
    ])
    
    for combo, count in report['pattern_combination_top10'].items():
        lines.append(f"| {combo} | {count} |")
    
    output_file.write_text('\n'.join(lines), encoding='utf-8')


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='验证Gemini分析结果质量')
    parser.add_argument('--output', type=str, help='输出报告文件（Markdown格式）')
    
    args = parser.parse_args()
    
    print("开始验证Gemini分析结果...\n")
    
    report = verify_gemini_analysis()
    
    # 打印统计
    print("=" * 80)
    print("验证结果")
    print("=" * 80)
    print(f"总模式数: {report['summary']['total_patterns']}")
    print(f"有Gemini标注: {report['summary']['with_gemini_annotation']}")
    print(f"覆盖率: {report['summary']['coverage_percentage']}%")
    print(f"平均置信度: {report['summary']['average_confidence']:.3f}")
    if report['summary']['average_probability']:
        print(f"平均概率: {report['summary']['average_probability']:.1f}%")
    print()
    print("质量指标:")
    print(f"  交易信号完整性: {report['quality_metrics']['signal_completeness']:.1f}%")
    print(f"  概率信息完整性: {report['quality_metrics']['probability_completeness']:.1f}%")
    print(f"  入场价格完整性: {report['quality_metrics']['entry_price_completeness']:.1f}%")
    print()
    
    # 生成Markdown报告
    if args.output:
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        generate_markdown_report(report, output_file)
        print(f"报告已保存: {output_file}")
    else:
        # 输出JSON格式
        print("\n详细报告 (JSON):")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

