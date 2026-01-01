#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查De.的最后发言时间"""

import json
from datetime import datetime

file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"

print("正在读取文件...")
with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

messages = data.get('messages', [])
print(f"总消息数: {len(messages)}")

# 提取De.的消息
de_messages = [m for m in messages if m.get('author', {}).get('nickname') == 'De.']
print(f"De.的消息数: {len(de_messages)}")

if not de_messages:
    print("未找到De.的消息")
    exit()

# 按时间戳排序，找出最后一条消息
de_messages_sorted = sorted(de_messages, key=lambda x: x.get('timestamp', ''))
last_message = de_messages_sorted[-1]
first_message = de_messages_sorted[0]

# 解析时间戳
def parse_timestamp(ts):
    """解析Discord时间戳"""
    if not ts:
        return None
    try:
        # Discord时间戳格式可能是ISO格式或Unix时间戳
        if isinstance(ts, str):
            # 尝试ISO格式
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                return dt
            except:
                # 尝试Unix时间戳（秒）
                try:
                    dt = datetime.fromtimestamp(float(ts))
                    return dt
                except:
                    # 尝试Unix时间戳（毫秒）
                    try:
                        dt = datetime.fromtimestamp(float(ts) / 1000)
                        return dt
                    except:
                        return None
        elif isinstance(ts, (int, float)):
            # Unix时间戳
            if ts > 1e10:  # 毫秒
                dt = datetime.fromtimestamp(ts / 1000)
            else:  # 秒
                dt = datetime.fromtimestamp(ts)
            return dt
    except Exception as e:
        print(f"解析时间戳失败: {e}")
        return None

last_timestamp = last_message.get('timestamp', '')
first_timestamp = first_message.get('timestamp', '')

last_dt = parse_timestamp(last_timestamp)
first_dt = parse_timestamp(first_timestamp)

print("\n" + "=" * 80)
print("De. 的消息时间统计")
print("=" * 80)
print(f"\n第一条消息:")
print(f"  时间戳: {first_timestamp}")
if first_dt:
    print(f"  时间: {first_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  内容: {first_message.get('content', '')[:100]}...")
else:
    print(f"  内容: {first_message.get('content', '')[:100]}...")

print(f"\n最后一条消息:")
print(f"  时间戳: {last_timestamp}")
if last_dt:
    print(f"  时间: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  内容: {last_message.get('content', '')[:200]}")
    
    # 计算距离现在的时间
    now = datetime.now()
    if last_dt.tzinfo:
        # 如果有时区信息，需要转换
        from datetime import timezone
        if last_dt.tzinfo.utcoffset(last_dt) is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
    
    time_diff = now - last_dt
    days = time_diff.days
    hours = time_diff.seconds // 3600
    minutes = (time_diff.seconds % 3600) // 60
    
    print(f"\n距离现在: {days}天 {hours}小时 {minutes}分钟")
else:
    print(f"  内容: {last_message.get('content', '')[:200]}")

# 显示最后5条消息
print(f"\n最后5条消息:")
print("-" * 80)
for i, msg in enumerate(de_messages_sorted[-5:], 1):
    ts = msg.get('timestamp', '')
    dt = parse_timestamp(ts)
    content = msg.get('content', '')[:150]
    if dt:
        time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    else:
        time_str = str(ts)
    print(f"{i}. [{time_str}] {content}")

print("\n" + "=" * 80)




