#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目文件整理脚本
1. 识别De.交易系统相关文件
2. 识别规则引擎相关文件
3. 识别最近生成的文件（不能删除）
4. 创建目录结构并移动文件
"""

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# 设置UTF-8编码
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 项目根目录
ROOT_DIR = Path('.')

# 最近生成的文件（7天内，不能删除）
RECENT_DAYS = 7
cutoff_date = datetime.now() - timedelta(days=RECENT_DAYS)

# De.交易系统相关文件关键词
DE_KEYWORDS = [
    'de_', 'De_', 'De.', 'generate_de', 'analyze_de', 'check_de',
    'update_de', 'get_realtime_stop_loss', 'generate_de_instruction',
    'De_trading', 'De_stop_loss', 'De_position', 'De_isolated',
    'De_vegas', '止损', '实时止损'
]

# 规则引擎相关文件关键词
RULES_ENGINE_KEYWORDS = [
    'rules_engine', 'trading_rules', 'simple_rules', 'dynamic_priority',
    'signal_confirmation', 'setup_rules', 'integrate_rules',
    'extract_trading_rules', 'deep_analyze_all_rules'
]

# 生成的文件（输出文件）
OUTPUT_KEYWORDS = [
    '_plan_', '_signals_', '_analysis_', '_trading_plan',
    '综合交易计划', 'De_trading_plan', 'BTC_signals', 'BNB_signals',
    'LUNA2_trading_signals', 'RAVE', 'BEAT', 'BCH', 'LUMIA',
    'FARTCOIN_leading_indicator', 'gate_bottom_formation',
    'binance_analysis', 'gate_21days_pattern'
]

# 无关文件（需要移到临时文件夹）
UNRELATED_KEYWORDS = [
    'qimeng2-app', 'download_notion', 'video_to_gif', 'convert_md_to_pdf',
    'md转pdf', 'analyze_peak_3x', 'analyze_3x_coins', 'analyze_gateio',
    'analyze_simple', 'crypto_analyzer', 'multi_source_analysis',
    'ml_crypto_analysis', 'deep_analysis_with_data', 'test_notion',
    'install_and_test', 'test_api', 'ffmpeg', 'downloads'
]

# 测试文件
TEST_KEYWORDS = [
    'test_', 'debug_', 'check_', 'simple_test', 'basic_test',
    'quick_test', 'test_output', 'test_simple', 'test_kline',
    'test_top200', 'test_beat', 'test_gate', 'test_stop_loss'
]

def is_recent_file(filepath):
    """判断是否为最近生成的文件"""
    try:
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        return mtime > cutoff_date
    except:
        return False

def classify_file(filename):
    """分类文件"""
    filename_lower = filename.lower()
    
    # 检查是否为无关文件
    for keyword in UNRELATED_KEYWORDS:
        if keyword.lower() in filename_lower:
            return 'unrelated'
    
    # 检查是否为规则引擎文件
    for keyword in RULES_ENGINE_KEYWORDS:
        if keyword.lower() in filename_lower:
            return 'rules_engine'
    
    # 检查是否为De.交易系统文件
    for keyword in DE_KEYWORDS:
        if keyword.lower() in filename_lower:
            return 'de_system'
    
    # 检查是否为输出文件
    for keyword in OUTPUT_KEYWORDS:
        if keyword.lower() in filename_lower:
            return 'output'
    
    # 检查是否为测试文件
    for keyword in TEST_KEYWORDS:
        if keyword.lower() in filename_lower:
            return 'test'
    
    # 默认：源代码
    return 'source'

def get_file_extension(filename):
    """获取文件扩展名"""
    return Path(filename).suffix.lower()

def organize_files():
    """整理文件"""
    print("="*70)
    print("项目文件整理")
    print("="*70)
    print()
    
    # 创建目录结构
    dirs = {
        'src': ROOT_DIR / 'src',
        'outputs': ROOT_DIR / 'outputs',
        'rules_engine': ROOT_DIR / 'rules_engine',
        'temp_unrelated': ROOT_DIR / 'temp_unrelated',
        'tests': ROOT_DIR / 'tests'
    }
    
    for dir_path in dirs.values():
        dir_path.mkdir(exist_ok=True)
        print(f"✓ 创建目录: {dir_path}")
    
    print()
    
    # 统计
    stats = {
        'de_system': [],
        'rules_engine': [],
        'output': [],
        'source': [],
        'test': [],
        'unrelated': [],
        'recent_protected': []
    }
    
    # 遍历所有文件
    all_files = []
    for item in ROOT_DIR.iterdir():
        if item.is_file() and not item.name.startswith('.'):
            all_files.append(item)
    
    print(f"发现 {len(all_files)} 个文件，开始分类...")
    print()
    
    # 分类文件
    for filepath in all_files:
        filename = filepath.name
        file_type = classify_file(filename)
        is_recent = is_recent_file(filepath)
        
        if is_recent:
            stats['recent_protected'].append(filename)
            # 最近的文件不移动，但记录
            continue
        
        # 根据类型移动到相应目录
        if file_type == 'unrelated':
            target_dir = dirs['temp_unrelated']
            stats['unrelated'].append(filename)
        elif file_type == 'rules_engine':
            target_dir = dirs['rules_engine']
            stats['rules_engine'].append(filename)
        elif file_type == 'de_system':
            # De.系统文件：源代码放src，输出放outputs
            if get_file_extension(filename) == '.py':
                target_dir = dirs['src']
                stats['de_system'].append(filename)
            else:
                target_dir = dirs['outputs']
                stats['output'].append(filename)
        elif file_type == 'output':
            target_dir = dirs['outputs']
            stats['output'].append(filename)
        elif file_type == 'test':
            target_dir = dirs['tests']
            stats['test'].append(filename)
        else:  # source
            target_dir = dirs['src']
            stats['source'].append(filename)
        
        # 移动文件
        try:
            target_path = target_dir / filename
            if target_path.exists():
                # 如果目标文件已存在，添加时间戳
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    new_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    new_filename = f"{filename}_{timestamp}"
                target_path = target_dir / new_filename
            
            shutil.move(str(filepath), str(target_path))
            print(f"✓ 移动: {filename} -> {target_dir.name}/")
        except Exception as e:
            print(f"✗ 移动失败: {filename} - {e}")
    
    print()
    print("="*70)
    print("整理完成！")
    print("="*70)
    print()
    
    # 输出统计
    print("【文件分类统计】")
    print(f"De.交易系统文件: {len(stats['de_system'])} 个")
    print(f"规则引擎文件: {len(stats['rules_engine'])} 个")
    print(f"输出文件: {len(stats['output'])} 个")
    print(f"源代码文件: {len(stats['source'])} 个")
    print(f"测试文件: {len(stats['test'])} 个")
    print(f"无关文件（临时）: {len(stats['unrelated'])} 个")
    print(f"最近生成的文件（未移动）: {len(stats['recent_protected'])} 个")
    print()
    
    # 生成报告
    report = f"""# 项目文件整理报告

**整理时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}

---

## 目录结构

- `src/` - 源代码文件
- `outputs/` - 生成的文件（交易计划、分析报告等）
- `rules_engine/` - 规则引擎相关文件
- `tests/` - 测试文件
- `temp_unrelated/` - 临时文件夹（无关文件，待确认删除）

---

## 文件统计

- **De.交易系统文件**: {len(stats['de_system'])} 个
- **规则引擎文件**: {len(stats['rules_engine'])} 个
- **输出文件**: {len(stats['output'])} 个
- **源代码文件**: {len(stats['source'])} 个
- **测试文件**: {len(stats['test'])} 个
- **无关文件（临时）**: {len(stats['unrelated'])} 个
- **最近生成的文件（未移动）**: {len(stats['recent_protected'])} 个

---

## 最近生成的文件（未移动，保留在原位置）

"""
    
    if stats['recent_protected']:
        for filename in sorted(stats['recent_protected']):
            report += f"- {filename}\n"
    else:
        report += "无\n"
    
    report += f"""

---

## 临时文件夹文件列表（待确认删除）

"""
    
    if stats['unrelated']:
        for filename in sorted(stats['unrelated']):
            report += f"- {filename}\n"
    else:
        report += "无\n"
    
    report += """

---

## 注意事项

1. **最近生成的文件**（7天内）未移动，保留在原位置
2. **临时文件夹** (`temp_unrelated/`) 中的文件请确认后删除
3. 所有文件已按类型分类到相应目录
4. 如有文件分类错误，请手动调整

---

*整理完成，请检查目录结构并确认临时文件夹中的文件是否可以删除。*

"""
    
    # 保存报告
    report_file = ROOT_DIR / f"文件整理报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✓ 整理报告已保存: {report_file}")
    print()
    print("="*70)

if __name__ == '__main__':
    organize_files()

