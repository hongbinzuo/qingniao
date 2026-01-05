#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户评价提取模块
从对话中提取 freelemon() 格式的评价
"""

import re
from typing import Dict, List, Optional, Tuple

class UserEvaluationExtractor:
    """用户评价提取器"""
    
    def __init__(self):
        # freelemon() 格式的正则表达式
        # 支持多种格式：
        # - freelemon(评价内容)
        # - freelemon（评价内容）
        # - freelemon(评价内容，可以包含逗号)
        self.pattern = re.compile(
            r'freelemon[（(]([^）)]+)[）)]',
            re.IGNORECASE | re.MULTILINE
        )
    
    def extract_evaluations(self, text: str) -> List[Dict]:
        """
        从文本中提取所有评价
        
        Returns:
            评价列表，每个评价包含：
            - content: 评价内容
            - start_pos: 起始位置
            - end_pos: 结束位置
        """
        evaluations = []
        
        for match in self.pattern.finditer(text):
            evaluation_content = match.group(1).strip()
            evaluations.append({
                'content': evaluation_content,
                'start_pos': match.start(),
                'end_pos': match.end(),
                'full_match': match.group(0)
            })
        
        return evaluations
    
    def remove_evaluations_from_text(self, text: str) -> Tuple[str, List[str]]:
        """
        从文本中移除评价标记，返回清理后的文本和评价列表
        
        Returns:
            (清理后的文本, 评价内容列表)
        """
        evaluations = self.extract_evaluations(text)
        evaluation_contents = [e['content'] for e in evaluations]
        
        # 移除所有评价标记
        cleaned_text = self.pattern.sub('', text)
        # 清理多余的空白
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text, evaluation_contents
    
    def extract_and_clean(self, text: str) -> Dict:
        """
        提取评价并清理文本
        
        Returns:
            包含以下字段的字典：
            - original_text: 原始文本
            - cleaned_text: 清理后的文本（移除评价标记）
            - evaluations: 评价列表
            - has_evaluation: 是否包含评价
        """
        evaluations = self.extract_evaluations(text)
        cleaned_text, evaluation_contents = self.remove_evaluations_from_text(text)
        
        return {
            'original_text': text,
            'cleaned_text': cleaned_text,
            'evaluations': evaluations,
            'evaluation_contents': evaluation_contents,
            'has_evaluation': len(evaluations) > 0,
            'evaluation_text': ' | '.join(evaluation_contents) if evaluation_contents else None
        }



