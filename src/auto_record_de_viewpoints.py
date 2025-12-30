#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动识别并记录De.观点
从对话日志中自动提取带"De."标记的内容
"""

import re
from datetime import datetime
from db_config import get_db_manager

def extract_de_content(text: str) -> list:
    """从文本中提取De.相关内容"""
    de_patterns = [
        r'De\.\s*[：:]\s*(.+?)(?:\n|$)',
        r'De\.\s+说[：:]\s*(.+?)(?:\n|$)',
        r'De\.\s+观点[：:]\s*(.+?)(?:\n|$)',
        r'De\.\s+指令[：:]\s*(.+?)(?:\n|$)',
        r'De\.\s+原话[：:]\s*(.+?)(?:\n|$)',
        r'De\.\s+([^。！？\n]+[。！？])',
        r'\"De\.\s*([^\"]+)\"',
        r'De\.\s+([^\n]+)',
    ]
    
    de_contents = []
    
    for pattern in de_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            content = match.group(1).strip()
            if content and len(content) > 5:  # 至少5个字符
                de_contents.append(content)
    
    # 去重
    seen = set()
    unique_contents = []
    for content in de_contents:
        if content not in seen:
            seen.add(content)
            unique_contents.append(content)
    
    return unique_contents

def process_conversation_for_de(user_message: str, assistant_message: str = None) -> list:
    """处理对话，提取De.观点"""
    de_contents = []
    
    # 从用户消息中提取
    user_de = extract_de_content(user_message)
    de_contents.extend(user_de)
    
    # 从助手回复中提取
    if assistant_message:
        assistant_de = extract_de_content(assistant_message)
        de_contents.extend(assistant_de)
    
    return de_contents

def auto_record_from_conversation(user_message: str, assistant_message: str = None,
                                 session_id: str = None):
    """自动从对话中提取并记录De.观点"""
    db = get_db_manager()
    
    # 提取De.内容
    de_contents = process_conversation_for_de(user_message, assistant_message)
    
    if not de_contents:
        return []
    
    # 记录到数据库
    recorded_ids = []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for content in de_contents:
        # 尝试从内容中提取时间信息
        time_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', content)
        if time_match:
            timestamp = time_match.group(1)
            content = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', '', content).strip()
        
        # 判断类别
        category = None
        if any(kw in content for kw in ['做多', '做空', '多单', '空单', '挂单', '止损', '止盈']):
            category = 'trading'
        elif any(kw in content for kw in ['分析', '观点', '看法']):
            category = 'analysis'
        elif any(kw in content for kw in ['指令', '计划', '策略']):
            category = 'instruction'
        
        vp_id = db.add_de_viewpoint(
            content=content,
            timestamp=timestamp,
            source='conversation',
            category=category
        )
        recorded_ids.append(vp_id)
    
    # 记录对话日志
    de_content_combined = '\n'.join(de_contents) if de_contents else None
    db.add_conversation_log(
        user_message=user_message,
        assistant_message=assistant_message or '',
        session_id=session_id,
        de_content=de_content_combined
    )
    
    return recorded_ids

if __name__ == '__main__':
    # 测试
    test_message = "De.说：明天低多，多在863下面损一次，85附近再多一次，新低止损"
    de_contents = extract_de_content(test_message)
    print(f"提取到的De.内容: {de_contents}")

