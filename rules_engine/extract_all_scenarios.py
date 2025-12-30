#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提取De.的所有情景分析语句
"""

import json
import re

def parse_json_file(file_path: str):
    """解析JSON文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('messages', [])

def extract_de_scenarios(messages):
    """提取De.的情景分析消息"""
    scenarios = []
    keywords = ['要么', '或者', '可能', '如果', '那么', '接下来', '要么在', '或者去']
    
    for msg in messages:
        author = msg.get('author', {})
        if author.get('nickname') == 'De.':
            content = msg.get('content', '')
            if any(kw in content for kw in keywords):
                scenarios.append({
                    'content': content,
                    'timestamp': msg.get('timestamp', '')
                })
    
    return scenarios

def main():
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    
    messages = parse_json_file(file_path)
    scenarios = extract_de_scenarios(messages)
    
    import sys
    sys.stdout.buffer.write(f"找到 {len(scenarios)} 条情景分析消息\n\n".encode('utf-8'))
    
    for i, scenario in enumerate(scenarios[:30], 1):
        content = scenario['content']
        timestamp = scenario['timestamp']
        output = f"{i}. {content}\n   时间: {timestamp}\n\n"
        sys.stdout.buffer.write(output.encode('utf-8'))

if __name__ == "__main__":
    main()

