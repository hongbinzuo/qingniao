#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""显示De.的最后几条消息"""

import json
from datetime import datetime

file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"

print("正在读取文件...")
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

messages = data.get('messages', [])
de_messages = [m for m in messages if m.get('author', {}).get('nickname') == 'De.']
de_messages.sort(key=lambda x: x.get('timestamp', ''))

print(f"\nDe.消息总数: {len(de_messages)}")
print(f"\n最后20条消息:")
print("=" * 80)

for i, msg in enumerate(de_messages[-20:], 1):
    timestamp = msg.get('timestamp', '')
    content = msg.get('content', '')
    
    # 解析时间戳
    try:
        if 'T' in timestamp:
            dt = datetime.fromisoformat(timestamp.replace('+08:00', ''))
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = timestamp
    except:
        time_str = timestamp
    
    print(f"{i}. [{time_str}]")
    print(f"   {content[:150]}")
    print()

print("=" * 80)
print(f"\n最后一条消息时间戳: {de_messages[-1].get('timestamp', '') if de_messages else 'N/A'}")
print(f"最后一条消息内容: {de_messages[-1].get('content', '')[:100] if de_messages else 'N/A'}")

