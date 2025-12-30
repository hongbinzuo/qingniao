#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查分析进度"""

import json

file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

messages = data.get('messages', [])
print(f"总消息数: {len(messages)}")

de_messages = [m for m in messages if m.get('author', {}).get('nickname') == 'De.']
print(f"De.的消息数: {len(de_messages)}")

# 统计包含价格的消息
price_keywords = ['1052', '1064', '1074', '1057', '1077', '1060', '1062', '1066', '1073', '1103']
trading_keywords = ['多单', '空单', '平', '挂单', '开', '加仓', '止损', '止盈']

trading_msgs = []
for msg in de_messages:
    content = msg.get('content', '')
    if any(kw in content for kw in trading_keywords) or any(kw in content for kw in price_keywords):
        trading_msgs.append({
            'timestamp': msg.get('timestamp', ''),
            'content': content[:100]  # 前100个字符
        })

print(f"\n包含交易信息的消息数: {len(trading_msgs)}")
print("\n前5条交易相关消息:")
for i, msg in enumerate(trading_msgs[:5], 1):
    print(f"{i}. [{msg['timestamp']}] {msg['content']}")





