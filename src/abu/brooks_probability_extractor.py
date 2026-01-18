#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brooks PA概率分类提取器

从Brooks的PA概率分类电子书中提取概率分类知识，并集成到ABU系统。
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import json
import re

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    try:
        import pdfplumber
        PDF_AVAILABLE = True
        USE_PDFPLUMBER = True
    except ImportError:
        PDF_AVAILABLE = False
        USE_PDFPLUMBER = False


class BrooksProbabilityExtractor:
    """Brooks PA概率分类提取器"""
    
    def __init__(self, pdf_path: Optional[Path] = None):
        """
        初始化提取器
        
        Args:
            pdf_path: PDF文件路径，如果为None，则使用默认路径
        """
        if pdf_path is None:
            # 默认路径
            pdf_path = Path.home() / 'Downloads' / 'Brooks Price Action概率.pdf'
        
        self.pdf_path = Path(pdf_path)
        self.probability_rules: List[Dict] = []
        
    def extract_from_pdf(self) -> List[Dict]:
        """
        从PDF中提取概率分类知识
        
        Returns:
            概率分类规则列表
        """
        if not self.pdf_path.exists():
            print(f"[WARN] PDF文件不存在: {self.pdf_path}", file=sys.stderr)
            return []
        
        if not PDF_AVAILABLE:
            print("[WARN] 未安装PDF处理库，请安装: pip install PyPDF2 或 pip install pdfplumber", file=sys.stderr)
            return []
        
        try:
            if USE_PDFPLUMBER:
                return self._extract_with_pdfplumber()
            else:
                return self._extract_with_pypdf2()
        except Exception as e:
            print(f"[ERROR] 提取PDF失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return []
    
    def _extract_with_pdfplumber(self) -> List[Dict]:
        """使用pdfplumber提取"""
        import pdfplumber
        
        rules = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    # 提取概率分类信息
                    page_rules = self._parse_probability_text(text, page_num)
                    rules.extend(page_rules)
        
        return rules
    
    def _extract_with_pypdf2(self) -> List[Dict]:
        """使用PyPDF2提取"""
        import PyPDF2
        
        rules = []
        
        with open(self.pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text:
                    # 提取概率分类信息
                    page_rules = self._parse_probability_text(text, page_num)
                    rules.extend(page_rules)
        
        return rules
    
    def _parse_probability_text(self, text: str, page_num: int) -> List[Dict]:
        """
        解析概率分类文本
        
        Args:
            text: 页面文本
            page_num: 页码
        
        Returns:
            概率分类规则列表
        """
        rules = []
        
        # 查找概率相关的模式
        # 1. 概率百分比（如：60%, 70%, 80%）
        probability_pattern = r'(\d+)%'
        
        # 2. 模式名称（更全面的模式匹配）
        pattern_name_patterns = [
            r'(Bull|Bear)\s+(Flag|Trend|Channel|Triangle|Reversal|Breakout)',
            r'(Double|Triple)\s+(Top|Bottom)',
            r'(Head|Shoulders)',
            r'(Breakout|Breakdown)',
            r'(Pullback|Reversal)',
            r'(Wedge|Pennant|Cup|Handle)',
            r'(Ascending|Descending)\s+(Triangle|Wedge)',
            r'(Small|Large)\s+(Pullback|Reversal)',
        ]
        
        # 3. 概率分类关键词
        probability_keywords = [
            '概率', 'probability', 'likely', 'unlikely',
            '高概率', '低概率', '中等概率',
            'high probability', 'low probability', 'medium probability',
            '成功率', 'success rate', 'win rate'
        ]
        
        # 提取概率信息（更精确的匹配）
        # 查找"模式名称 + 概率"的组合
        text_lower = text.lower()
        probabilities = []
        pattern_probability_map = {}  # {pattern_name: probability}
        
        # 方法1: 查找明确的概率数值
        prob_matches = re.findall(probability_pattern, text)
        probabilities = [int(p) for p in prob_matches if 0 <= int(p) <= 100]
        
        # 方法2: 查找模式名称附近的概率
        for pattern_regex in pattern_name_patterns:
            pattern_matches = re.finditer(pattern_regex, text, re.IGNORECASE)
            for match in pattern_matches:
                pattern_name = match.group(0)
                # 在模式名称前后100字符内查找概率
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]
                
                # 在上下文中查找概率
                context_probs = re.findall(probability_pattern, context)
                if context_probs:
                    # 取第一个概率值
                    prob = int(context_probs[0])
                    if 0 <= prob <= 100:
                        pattern_probability_map[pattern_name] = prob
        
        # 查找模式名称
        pattern_names = []
        for pattern in pattern_name_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            pattern_names.extend([m[0] + ' ' + m[1] if isinstance(m, tuple) else m for m in matches])
        
        # 如果找到概率信息，创建规则
        if probabilities or pattern_probability_map or any(kw in text_lower for kw in probability_keywords):
            # 为每个模式创建单独的规则
            if pattern_probability_map:
                for pattern_name, prob in pattern_probability_map.items():
                    rule = {
                        'page': page_num,
                        'pattern_name': pattern_name,
                        'probability': prob,
                        'text': text[:500],
                        'has_probability_info': True
                    }
                    rules.append(rule)
            elif pattern_names and probabilities:
                # 如果有模式名称和概率，尝试关联
                for pattern_name in pattern_names[:3]:  # 最多3个模式
                    prob = probabilities[0] if probabilities else None
                    rule = {
                        'page': page_num,
                        'pattern_name': pattern_name if isinstance(pattern_name, str) else ' '.join(pattern_name),
                        'probability': prob,
                        'text': text[:500],
                        'has_probability_info': True
                    }
                    rules.append(rule)
            else:
                # 通用规则
                rule = {
                    'page': page_num,
                    'text': text[:500],
                    'probabilities': list(set([str(p) for p in probabilities])),
                    'pattern_names': list(set([p if isinstance(p, str) else ' '.join(p) for p in pattern_names])),
                    'has_probability_info': True
                }
                rules.append(rule)
        
        return rules
    
    def save_to_json(self, output_path: Path):
        """
        保存提取的规则到JSON文件
        
        Args:
            output_path: 输出文件路径
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.probability_rules, f, ensure_ascii=False, indent=2)
    
    def integrate_to_pattern_library(self, pattern_library):
        """
        将概率分类知识集成到模式库
        
        Args:
            pattern_library: UnifiedPatternLibrary实例
        """
        # TODO: 实现集成逻辑
        # 1. 将概率分类规则转换为模式库格式
        # 2. 添加到模式库
        # 3. 更新匹配逻辑以考虑概率
        pass


def main():
    """主函数"""
    print("=" * 80)
    print("Brooks PA概率分类提取器")
    print("=" * 80)
    print()
    
    # 初始化提取器
    extractor = BrooksProbabilityExtractor()
    
    # 提取概率分类知识
    print("1. 从PDF提取概率分类知识...")
    rules = extractor.extract_from_pdf()
    extractor.probability_rules = rules
    
    print(f"   提取了 {len(rules)} 条概率分类规则")
    print()
    
    # 保存到JSON
    output_path = ROOT / 'data' / 'brooks_probability_rules.json'
    print(f"2. 保存到: {output_path}")
    extractor.save_to_json(output_path)
    print("   [OK] 保存完成")
    print()
    
    # 显示示例
    if rules:
        print("3. 示例规则:")
        for i, rule in enumerate(rules[:3], 1):
            print(f"   规则 {i} (第{rule['page']}页):")
            print(f"     概率: {rule.get('probabilities', [])}")
            print(f"     模式: {rule.get('pattern_names', [])}")
            print()
    
    print("=" * 80)
    print("提取完成")
    print("=" * 80)


if __name__ == '__main__':
    main()
