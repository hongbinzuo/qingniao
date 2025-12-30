#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找上次录入De.对话的时间
检查所有可能的记录文件
"""

import json
import os
from pathlib import Path
from datetime import datetime

def find_de_processing_records():
    """查找所有可能的De.对话处理记录"""
    
    print("=" * 80)
    print("查找De.对话处理记录")
    print("=" * 80)
    print()
    
    # 1. 检查对话文件本身
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    
    if os.path.exists(file_path):
        print("[1] 检查对话文件...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = data.get('messages', [])
            de_messages = [m for m in messages if m.get('author', {}).get('nickname') == 'De.']
            
            if de_messages:
                de_messages_sorted = sorted(de_messages, key=lambda x: x.get('timestamp', ''))
                last_msg = de_messages_sorted[-1]
                last_timestamp = last_msg.get('timestamp', '')
                
                print(f"  对话文件中的最后一条消息: {last_timestamp}")
                print(f"  内容: {last_msg.get('content', '')[:100]}")
        except Exception as e:
            print(f"  读取失败: {e}")
    
    print()
    
    # 2. 检查outputs目录下的De.相关文件
    print("[2] 检查outputs目录下的De.相关文件...")
    outputs_dir = Path("outputs")
    if outputs_dir.exists():
        de_files = list(outputs_dir.glob("De_*.md"))
        de_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if de_files:
            print(f"  找到 {len(de_files)} 个De.相关文件")
            print(f"  最新的5个文件:")
            for i, f in enumerate(de_files[:5], 1):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                print(f"    {i}. {f.name}")
                print(f"       修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 尝试读取文件，查找时间信息
                try:
                    content = f.read_text(encoding='utf-8', errors='ignore')
                    # 查找时间戳
                    if '2025-12-2' in content or '2025-12-3' in content:
                        lines = content.split('\n')
                        for line in lines[:20]:  # 只检查前20行
                            if '2025-12-2' in line or '2025-12-3' in line or '时间' in line:
                                print(f"       内容: {line[:80]}")
                                break
                except:
                    pass
        else:
            print("  未找到De.相关文件")
    
    print()
    
    # 3. 检查是否有进度记录文件
    print("[3] 检查进度记录文件...")
    possible_progress_files = [
        "de_processing_progress.json",
        "de_last_processed.json",
        "de_dialog_progress.json",
        ".de_progress",
        "data/de_progress.json"
    ]
    
    found_progress = False
    for progress_file in possible_progress_files:
        if os.path.exists(progress_file):
            found_progress = True
            print(f"  找到: {progress_file}")
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    print(f"    内容: {json.dumps(progress, ensure_ascii=False, indent=2)}")
            except Exception as e:
                print(f"    读取失败: {e}")
    
    if not found_progress:
        print("  未找到进度记录文件")
    
    print()
    
    # 4. 检查src目录下的相关脚本
    print("[4] 检查src目录下的相关脚本...")
    src_dir = Path("src")
    if src_dir.exists():
        de_scripts = list(src_dir.glob("*de*.py"))
        de_scripts.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if de_scripts:
            print(f"  找到 {len(de_scripts)} 个De.相关脚本")
            print(f"  最新的5个脚本:")
            for i, f in enumerate(de_scripts[:5], 1):
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                print(f"    {i}. {f.name} (修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
    
    print()
    
    # 5. 检查outputs目录下最新的De_trading_plan文件
    print("[5] 检查最新的De_trading_plan文件...")
    if outputs_dir.exists():
        plan_files = list(outputs_dir.glob("De_trading_plan_*.md"))
        if plan_files:
            plan_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            latest_plan = plan_files[0]
            mtime = datetime.fromtimestamp(latest_plan.stat().st_mtime)
            print(f"  最新文件: {latest_plan.name}")
            print(f"  修改时间: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 读取文件内容，查找时间信息
            try:
                content = latest_plan.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                for line in lines[:10]:
                    if '生成时间' in line or '时间' in line:
                        print(f"  文件内容: {line.strip()}")
            except:
                pass
    
    print()
    print("=" * 80)
    print("提示: 如果没有找到上次处理时间的记录，建议从对话文件的最后一条消息开始")
    print("=" * 80)

if __name__ == '__main__':
    find_de_processing_records()

