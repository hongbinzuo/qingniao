#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对比Cursor识别结果和Gemini识别结果
"""
import sys
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

def load_selected_images() -> List[Dict]:
    """加载选中的50张图片列表"""
    list_file = ROOT / 'data' / 'abu' / 'comparison_test' / 'selected_50_images.json'
    if not list_file.exists():
        print(f"❌ 未找到图片列表文件: {list_file}")
        print("   请先运行: python scripts/select_50_random_images.py")
        return []
    
    with open(list_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_gemini_result(image_name: str) -> Optional[Dict]:
    """从Gemini输出文件中加载结果"""
    output_file = ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'
    
    if not output_file.exists():
        return None
    
    with open(output_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                record_image = Path(record.get('image', record.get('image_path', ''))).name
                if record_image == image_name:
                    return record
            except:
                continue
    
    return None

def load_cursor_result(image_name: str) -> Optional[str]:
    """加载Cursor识别结果"""
    cursor_file = ROOT / 'data' / 'abu' / 'comparison_test' / 'cursor_results' / f'{image_name}.txt'
    
    if not cursor_file.exists():
        return None
    
    try:
        with open(cursor_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"⚠️  读取Cursor结果失败 {image_name}: {e}")
        return None

def extract_gemini_summary(gemini_record: Dict) -> Dict:
    """提取Gemini结果的关键信息"""
    result = gemini_record.get('result', {})
    analysis = {}
    
    # 尝试解析raw JSON
    raw = result.get('raw', '')
    if raw:
        try:
            # 尝试提取JSON
            import re
            if raw.startswith('```json'):
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw, re.DOTALL)
                if json_match:
                    raw = json_match.group(1)
            elif raw.startswith('```'):
                json_match = re.search(r'```\s*(\{.*?\})\s*```', raw, re.DOTALL)
                if json_match:
                    raw = json_match.group(1)
            
            # 找到第一个{到最后一个}
            if not raw.strip().startswith('{'):
                first_brace = raw.find('{')
                last_brace = raw.rfind('}')
                if first_brace >= 0 and last_brace > first_brace:
                    raw = raw[first_brace:last_brace+1]
            
            analysis = json.loads(raw)
        except:
            pass
    
    return {
        'status': result.get('status', 'unknown'),
        'parse_error': result.get('parse_error', ''),
        'complete_narrative': analysis.get('complete_narrative', ''),
        'patterns': analysis.get('patterns', []),
        'trading_signals': analysis.get('trading_signals', []),
        'chart_overview': analysis.get('chart_overview', {}),
        'has_key_fields': bool(analysis.get('complete_narrative') and 
                               analysis.get('chart_overview') and
                               analysis.get('complete_price_path'))
    }

def compare_results(cursor_text: str, gemini_result: Dict) -> Dict:
    """对比两个结果"""
    gemini_summary = extract_gemini_summary(gemini_result)
    
    comparison = {
        'image_name': gemini_result.get('image', '').split('\\')[-1] if gemini_result.get('image') else '',
        'cursor_available': bool(cursor_text),
        'gemini_status': gemini_summary.get('status'),
        'gemini_has_key_fields': gemini_summary.get('has_key_fields', False),
        'cursor_length': len(cursor_text) if cursor_text else 0,
        'gemini_narrative_length': len(gemini_summary.get('complete_narrative', '')),
        'cursor_has_patterns': False,  # 需要分析
        'gemini_patterns_count': len(gemini_summary.get('patterns', [])),
        'cursor_has_trading_info': False,  # 需要分析
        'gemini_signals_count': len(gemini_summary.get('trading_signals', [])),
    }
    
    # 分析Cursor结果
    if cursor_text:
        cursor_lower = cursor_text.lower()
        # 检查是否包含模式相关关键词
        pattern_keywords = ['wedge', 'triangle', 'inside bar', 'engulfing', 'pin bar', 
                           'head and shoulders', 'double top', 'double bottom', 'channel',
                           'trend', 'reversal', 'breakout', 'pullback']
        comparison['cursor_has_patterns'] = any(kw in cursor_lower for kw in pattern_keywords)
        
        # 检查是否包含交易相关信息
        trading_keywords = ['buy', 'sell', 'long', 'short', 'entry', 'stop', 'target', 
                           'take profit', 'stop loss', '入场', '止损', '止盈', '做多', '做空']
        comparison['cursor_has_trading_info'] = any(kw in cursor_lower for kw in trading_keywords)
    
    return comparison

def generate_report(comparisons: List[Dict]) -> str:
    """生成对比报告"""
    total = len(comparisons)
    cursor_available = sum(1 for c in comparisons if c['cursor_available'])
    gemini_success = sum(1 for c in comparisons if c['gemini_status'] == 'success' or c['gemini_has_key_fields'])
    
    report = f"""# Cursor vs Gemini 识别结果对比报告

## 基本信息

- **测试图片数**: {total} 张
- **Cursor结果可用**: {cursor_available}/{total} ({cursor_available/total*100:.1f}%)
- **Gemini结果可用**: {gemini_success}/{total} ({gemini_success/total*100:.1f}%)

## 详细对比

"""
    
    # 统计信息
    cursor_avg_length = sum(c['cursor_length'] for c in comparisons if c['cursor_available']) / cursor_available if cursor_available > 0 else 0
    gemini_avg_length = sum(c['gemini_narrative_length'] for c in comparisons) / total if total > 0 else 0
    
    cursor_patterns_count = sum(1 for c in comparisons if c['cursor_has_patterns'])
    gemini_patterns_count = sum(c['gemini_patterns_count'] for c in comparisons)
    
    cursor_trading_count = sum(1 for c in comparisons if c['cursor_has_trading_info'])
    gemini_trading_count = sum(1 for c in comparisons if c['gemini_signals_count'] > 0)
    
    report += f"""### 内容长度对比

- **Cursor平均长度**: {cursor_avg_length:.0f} 字符
- **Gemini平均长度**: {gemini_avg_length:.0f} 字符
- **差异**: {abs(cursor_avg_length - gemini_avg_length):.0f} 字符

### 模式识别对比

- **Cursor识别到模式**: {cursor_patterns_count}/{cursor_available} ({cursor_patterns_count/cursor_available*100:.1f}% if cursor_available > 0 else 0)
- **Gemini识别到模式**: {gemini_patterns_count} 个模式（总计）
- **Gemini平均每张**: {gemini_patterns_count/total:.1f} 个模式

### 交易信息对比

- **Cursor包含交易信息**: {cursor_trading_count}/{cursor_available} ({cursor_trading_count/cursor_available*100:.1f}% if cursor_available > 0 else 0)
- **Gemini包含交易信号**: {gemini_trading_count}/{total} ({gemini_trading_count/total*100:.1f}%)

## 逐项对比

"""
    
    for idx, comp in enumerate(comparisons, 1):
        report += f"""### {idx}. {comp['image_name']}

**Cursor结果**:
- 可用: {'是' if comp['cursor_available'] else '否'}
- 长度: {comp['cursor_length']} 字符
- 包含模式: {'是' if comp['cursor_has_patterns'] else '否'}
- 包含交易信息: {'是' if comp['cursor_has_trading_info'] else '否'}

**Gemini结果**:
- 状态: {comp['gemini_status']}
- 关键字段完整: {'是' if comp['gemini_has_key_fields'] else '否'}
- 叙述长度: {comp['gemini_narrative_length']} 字符
- 模式数量: {comp['gemini_patterns_count']} 个
- 交易信号数: {comp['gemini_signals_count']} 个

---

"""
    
    # 优势和劣势分析
    report += f"""## 优势劣势分析

### Cursor的优势

1. **自然语言理解**: 可能更符合人类的表达习惯
2. **上下文理解**: 可能在理解图表意图方面更强
3. **简洁性**: 可能提供更简洁、直接的答案

### Gemini的优势

1. **结构化输出**: 提供结构化的JSON格式数据
2. **完整性**: 包含图表概览、价格路径、模式、交易信号等多个维度
3. **标准化**: 输出格式统一，便于程序处理
4. **详细信息**: 提供更详细的模式描述和交易参数

### 建议

1. **如果注重自然语言表达**: Cursor可能更适合
2. **如果注重结构化数据和程序处理**: Gemini更适合
3. **如果注重完整性**: Gemini提供的信息更全面
4. **如果注重简洁性**: Cursor可能更简洁

## 生成时间

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return report

def main():
    print("=" * 80)
    print("Cursor vs Gemini 识别结果对比")
    print("=" * 80)
    print()
    
    # 加载选中的图片
    selected_images = load_selected_images()
    if not selected_images:
        return
    
    print(f"加载了 {len(selected_images)} 张图片")
    print()
    
    # 对比每张图片
    comparisons = []
    cursor_missing = []
    gemini_missing = []
    
    for item in selected_images:
        image_name = item['image_name']
        print(f"处理: {image_name}...", end=' ')
        
        # 加载Cursor结果
        cursor_text = load_cursor_result(image_name)
        
        # 加载Gemini结果
        gemini_result = load_gemini_result(image_name)
        
        if not cursor_text:
            cursor_missing.append(image_name)
            print("❌ Cursor结果缺失")
        elif not gemini_result:
            gemini_missing.append(image_name)
            print("❌ Gemini结果缺失")
        else:
            comparison = compare_results(cursor_text, gemini_result)
            comparisons.append(comparison)
            print("✅")
    
    print()
    print(f"✅ 完成对比: {len(comparisons)}/{len(selected_images)}")
    
    if cursor_missing:
        print(f"\n⚠️  Cursor结果缺失 ({len(cursor_missing)}张):")
        for img in cursor_missing[:10]:
            print(f"  - {img}")
        if len(cursor_missing) > 10:
            print(f"  ... (共{len(cursor_missing)}张)")
    
    if gemini_missing:
        print(f"\n⚠️  Gemini结果缺失 ({len(gemini_missing)}张):")
        for img in gemini_missing[:10]:
            print(f"  - {img}")
        if len(gemini_missing) > 10:
            print(f"  ... (共{len(gemini_missing)}张)")
    
    if not comparisons:
        print("\n❌ 没有可对比的结果")
        print("   请确保Cursor结果已保存到: data/abu/comparison_test/cursor_results/")
        return
    
    # 生成报告
    report = generate_report(comparisons)
    
    # 保存报告
    output_dir = ROOT / 'data' / 'abu' / 'comparison_test'
    report_file = output_dir / '对比报告.md'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # 保存详细数据
    data_file = output_dir / '对比数据.json'
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(comparisons, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 报告已生成: {report_file}")
    print(f"✅ 数据已保存: {data_file}")
    print()
    print("=" * 80)
    print("对比完成")
    print("=" * 80)

if __name__ == '__main__':
    main()

