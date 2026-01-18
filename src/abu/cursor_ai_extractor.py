#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor AI特征提取器 - ABU系统v3.0

统一的Cursor AI特征提取接口，从识别结果中提取结构化特征。
"""

from __future__ import annotations
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class CursorAIFeatureExtractor:
    """
    Cursor AI特征提取器
    
    功能：
    1. 从识别结果文件（TXT）中提取结构化JSON特征
    2. 从结构化特征文件（JSON）中加载特征
    3. 统一特征格式
    """
    
    def __init__(self):
        """初始化提取器"""
        self.results_dir = ROOT / 'outputs' / 'cursor_ai_recognition' / 'results'
        self.features_dir = ROOT / 'outputs' / 'cursor_ai_recognition' / 'structured_features'
    
    def extract_from_text(self, text: str) -> Optional[Dict]:
        """
        从文本中提取JSON特征
        
        Args:
            text: 识别结果文本
        
        Returns:
            提取的特征字典，如果无法提取则返回None
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
    
    def extract_from_file(self, filepath: Path) -> Optional[Dict]:
        """
        从文件中提取特征
        
        Args:
            filepath: 文件路径（TXT或JSON）
        
        Returns:
            提取的特征字典
        """
        try:
            with filepath.open('r', encoding='utf-8') as f:
                content = f.read()
            
            # 如果是JSON文件，直接解析
            if filepath.suffix.lower() == '.json':
                return json.loads(content)
            
            # 如果是TXT文件，提取JSON
            return self.extract_from_text(content)
        
        except Exception as e:
            print(f"[WARN] 提取特征失败 {filepath.name}: {e}", file=sys.stderr)
            return None
    
    def load_all_features(self) -> List[Dict]:
        """
        加载所有结构化特征
        
        Returns:
            特征列表，每个包含source_file信息
        """
        features_list = []
        
        # 优先从结构化特征目录加载
        if self.features_dir.exists():
            feature_files = list(self.features_dir.glob('*.json'))
            for feature_file in feature_files:
                try:
                    with feature_file.open('r', encoding='utf-8') as f:
                        feature = json.load(f)
                    
                    # 添加元数据
                    if '_metadata' not in feature:
                        feature['_metadata'] = {}
                    feature['_metadata']['source_file'] = feature_file.name
                    feature['_metadata']['extracted_at'] = None
                    
                    features_list.append(feature)
                
                except Exception as e:
                    print(f"[WARN] 加载特征文件失败 {feature_file.name}: {e}", file=sys.stderr)
                    continue
        
        # 如果结构化特征不存在，尝试从原始结果文件提取
        elif self.results_dir.exists():
            result_files = list(self.results_dir.glob('*.txt'))
            for result_file in result_files:
                feature = self.extract_from_file(result_file)
                if feature:
                    if '_metadata' not in feature:
                        feature['_metadata'] = {}
                    feature['_metadata']['source_file'] = result_file.name
                    features_list.append(feature)
        
        return features_list
    
    def standardize_features(self, features: Dict) -> Dict:
        """
        标准化特征格式
        
        Args:
            features: 原始特征字典
        
        Returns:
            标准化后的特征字典
        """
        standardized = {
            'pattern_type': features.get('pattern_type') or features.get('pattern_subtype', 'unknown'),
            'pattern_subtype': features.get('pattern_subtype', ''),
            'direction': features.get('direction', 'neutral').lower(),
            'confidence': float(features.get('confidence', 0.5)),
            'kline_features': features.get('kline_features', {}),
            'price_levels': features.get('price_levels', {}),
            'pattern_structure': features.get('pattern_structure', {}),
            'trading_signals': features.get('trading_signals', []),
            'quantified_indicators': features.get('quantified_indicators', {}),
            'market_conditions': features.get('market_conditions', {})
        }
        
        # 确保kline_features是列表或字典
        if isinstance(standardized['kline_features'], str):
            standardized['kline_features'] = [standardized['kline_features']]
        
        return standardized
    
    def get_pattern_name(self, features: Dict) -> str:
        """从特征中提取模式名称"""
        return (
            features.get('pattern_name') or
            features.get('pattern_type') or
            features.get('pattern_subtype') or
            'Unknown'
        )


def main():
    """测试函数"""
    print("=" * 80)
    print("Cursor AI特征提取器测试")
    print("=" * 80)
    print()
    
    extractor = CursorAIFeatureExtractor()
    
    # 测试从文本提取
    test_text = """
    这是模式识别结果。
    
    ```json
    {
        "pattern_type": "triangle",
        "pattern_subtype": "ascending",
        "direction": "long",
        "confidence": 0.85,
        "kline_features": {
            "type": "ascending_triangle",
            "breakout": true
        }
    }
    ```
    """
    
    print("测试1: 从文本提取JSON特征")
    features = extractor.extract_from_text(test_text)
    if features:
        print("  提取成功:")
        print(f"    模式类型: {features.get('pattern_type')}")
        print(f"    方向: {features.get('direction')}")
        print(f"    置信度: {features.get('confidence')}")
    else:
        print("  提取失败")
    print()
    
    # 测试标准化
    print("测试2: 标准化特征")
    if features:
        standardized = extractor.standardize_features(features)
        print(f"  标准化后的特征:")
        print(f"    模式类型: {standardized['pattern_type']}")
        print(f"    方向: {standardized['direction']}")
        print(f"    置信度: {standardized['confidence']}")
    print()
    
    # 测试加载所有特征
    print("测试3: 加载所有特征文件")
    all_features = extractor.load_all_features()
    print(f"  找到 {len(all_features)} 个特征文件")
    if all_features:
        print(f"  示例: {all_features[0].get('_metadata', {}).get('source_file', 'unknown')}")


if __name__ == '__main__':
    main()
