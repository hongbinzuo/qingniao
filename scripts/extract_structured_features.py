#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Cursor识别结果中提取结构化JSON特征

扫描识别结果文件，提取其中的JSON部分，单独保存为JSON文件。
"""
from __future__ import annotations
import sys
import json
import re
from pathlib import Path
from typing import Dict, Optional, List

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / 'outputs' / 'cursor_ai_recognition' / 'results'
FEATURES_DIR = ROOT / 'outputs' / 'cursor_ai_recognition' / 'structured_features'

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

def extract_json_from_text(text: str) -> Optional[Dict]:
    """
    从文本中提取JSON对象
    
    Args:
        text: 识别结果文本
        
    Returns:
        提取的JSON字典，如果无法提取则返回None
    """
    # 尝试找到 ```json 代码块
    json_block_pattern = r'```json\s*\n(.*?)\n```'
    match = re.search(json_block_pattern, text, re.DOTALL)
    
    if match:
        json_str = match.group(1).strip()
    else:
        # 尝试找到 { ... } JSON对象
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            json_str = match.group(0)
        else:
            return None
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # 尝试修复常见的JSON格式问题
        try:
            # 移除尾随逗号
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None

def extract_features_from_file(result_file: Path) -> Optional[Dict]:
    """
    从单个识别结果文件中提取结构化特征
    
    Args:
        result_file: 识别结果文件路径
        
    Returns:
        提取的特征字典，包含source_file信息
    """
    try:
        with result_file.open('r', encoding='utf-8') as f:
            content = f.read()
        
        features = extract_json_from_text(content)
        if features:
            # 添加源文件信息
            features['_metadata'] = {
                'source_file': result_file.name,
                'extracted_at': None  # 可以在后续添加时间戳
            }
            return features
    except Exception as e:
        print(f"处理文件 {result_file.name} 失败: {e}", file=sys.stderr)
    
    return None

def process_all_results() -> Dict[str, any]:
    """
    处理所有识别结果文件
    
    Returns:
        统计信息字典
    """
    if not RESULTS_DIR.exists():
        print(f"错误: 结果目录不存在: {RESULTS_DIR}", file=sys.stderr)
        return {'total': 0, 'extracted': 0, 'failed': 0}
    
    # 创建特征目录
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    
    result_files = list(RESULTS_DIR.glob('*.txt'))
    stats = {
        'total': len(result_files),
        'extracted': 0,
        'failed': 0,
        'files': []
    }
    
    for result_file in result_files:
        features = extract_features_from_file(result_file)
        
        if features:
            # 保存为JSON文件
            feature_file = FEATURES_DIR / f"{result_file.stem}.json"
            try:
                with feature_file.open('w', encoding='utf-8') as f:
                    json.dump(features, f, indent=2, ensure_ascii=False)
                stats['extracted'] += 1
                stats['files'].append(result_file.name)
            except Exception as e:
                print(f"保存特征文件失败 {feature_file.name}: {e}", file=sys.stderr)
                stats['failed'] += 1
        else:
            stats['failed'] += 1
    
    return stats

def main():
    """主函数"""
    print("=" * 80)
    print("提取Cursor识别结果中的结构化特征")
    print("=" * 80)
    print()
    
    print(f"扫描目录: {RESULTS_DIR}")
    print(f"输出目录: {FEATURES_DIR}")
    print()
    
    stats = process_all_results()
    
    print(f"处理完成:")
    print(f"  总文件数: {stats['total']}")
    print(f"  成功提取: {stats['extracted']}")
    print(f"  提取失败: {stats['failed']}")
    print()
    
    if stats['extracted'] > 0:
        print(f"✅ 结构化特征已保存到: {FEATURES_DIR}")
        print(f"   共提取 {stats['extracted']} 个JSON特征文件")
    
    if stats['failed'] > 0:
        print(f"⚠️  {stats['failed']} 个文件未能提取JSON特征")
        print("   可能原因:")
        print("   1. 文件格式为旧版本（不包含JSON）")
        print("   2. JSON格式错误或无法解析")
        print("   3. 文件为空或损坏")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())

