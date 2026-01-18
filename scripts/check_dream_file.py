#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查哪个Discord导出文件包含Dream的消息"""
import json
import sys
from pathlib import Path
import glob

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

DREAM_AUTHOR = 'qimeng0104_49398'

# 查找所有JSON文件
discord_dir = Path(r'C:\Users\zuoho\Downloads\discord-msg')
if not discord_dir.exists():
    print(f"目录不存在: {discord_dir}")
    sys.exit(1)

json_files = list(discord_dir.glob('*.json'))
print(f"找到 {len(json_files)} 个JSON文件\n")

for file_path in json_files:
    try:
        print(f"检查文件: {file_path.name}")
        print(f"  大小: {file_path.stat().st_size / 1024 / 1024:.2f} MB")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查格式
        if isinstance(data, dict) and 'messages' in data:
            msgs = data['messages']
            print(f"  格式: Discord导出格式 (dict with messages)")
        elif isinstance(data, list):
            msgs = data
            print(f"  格式: 列表格式")
        else:
            print(f"  格式: 未知格式")
            continue
        
        print(f"  总消息数: {len(msgs)}")
        
        # 统计Dream的消息
        dream_count = 0
        for m in msgs[:1000]:  # 只检查前1000条以加快速度
            if isinstance(m, dict):
                author = m.get('author')
                if isinstance(author, dict):
                    name = author.get('name', '')
                else:
                    name = str(author) if author else ''
                
                if name == DREAM_AUTHOR:
                    dream_count += 1
        
        if dream_count > 0:
            # 如果前1000条有，再统计全部
            dream_count = 0
            for m in msgs:
                if isinstance(m, dict):
                    author = m.get('author')
                    if isinstance(author, dict):
                        name = author.get('name', '')
                    else:
                        name = str(author) if author else ''
                    if name == DREAM_AUTHOR:
                        dream_count += 1
            
            print(f"  Dream消息数: {dream_count}")
            print(f"  ✅ 包含Dream的消息！")
            print(f"  📍 文件路径: {file_path}")
        else:
            print(f"  ⚠️  未找到Dream的消息（检查了前1000条）")
            
    except Exception as e:
        print(f"  ❌ 读取失败: {e}")
    
    print()
