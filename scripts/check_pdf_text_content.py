#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查PDF原始提取的文本内容"""

import json
from pathlib import Path

def main():
    f = Path('data/abu/raw_pages.jsonl')
    if not f.exists():
        print(f"文件不存在: {f}")
        return 1
    
    lines = f.read_text(encoding='utf-8').strip().split('\n')
    print(f"总页数: {len(lines)}\n")
    
    # 搜索包含交易信号的页面
    keywords = ['Gap bar', 'buy', 'PB', 'bull trend', 'test of high', 'chance']
    matches = []
    
    for line in lines:
        try:
            page_data = json.loads(line)
            text = page_data.get('text', '')
            page_num = page_data.get('page', 0)
            
            # 检查是否包含关键词
            text_lower = text.lower()
            if any(kw.lower() in text_lower for kw in keywords):
                matches.append((page_num, text))
        except:
            continue
    
    print(f"找到 {len(matches)} 页包含交易信号文字\n")
    
    # 显示前10页
    for page_num, text in matches[:10]:
        print(f"\n{'='*80}")
        print(f"页面 {page_num}")
        print(f"{'='*80}")
        # 显示前1000字符
        print(text[:1000])
        if len(text) > 1000:
            print("...")
        print()
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())



