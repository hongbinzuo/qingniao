#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录De.对话处理进度
用于跟踪上次处理到哪条消息，下次继续处理
"""

import json
import os
from datetime import datetime
from pathlib import Path

PROGRESS_FILE = Path(__file__).parent / "de_dialog_progress.json"

def load_progress():
    """加载处理进度"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    
    # 默认进度
    return {
        "last_processed_timestamp": None,
        "last_processed_time": None,
        "total_processed": 0,
        "last_processed_content": None,
        "processing_history": []
    }

def save_progress(progress):
    """保存处理进度"""
    PROGRESS_FILE.parent.mkdir(exist_ok=True)
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)

def update_progress(timestamp, content=None, processed_count=0):
    """更新处理进度"""
    progress = load_progress()
    
    # 更新最后处理的时间戳
    if timestamp:
        progress["last_processed_timestamp"] = timestamp
        
        # 解析时间戳为可读格式
        try:
            if isinstance(timestamp, str):
                if 'T' in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('+08:00', ''))
                    progress["last_processed_time"] = dt.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    progress["last_processed_time"] = timestamp
            else:
                progress["last_processed_time"] = str(timestamp)
        except:
            progress["last_processed_time"] = str(timestamp)
    
    # 更新最后处理的内容
    if content:
        progress["last_processed_content"] = content[:200]  # 只保存前200字符
    
    # 更新处理总数
    if processed_count > 0:
        progress["total_processed"] = processed_count
    
    # 添加到历史记录
    if timestamp:
        progress["processing_history"].append({
            "timestamp": timestamp,
            "processed_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "content": content[:100] if content else None
        })
        # 只保留最近20条历史记录
        if len(progress["processing_history"]) > 20:
            progress["processing_history"] = progress["processing_history"][-20:]
    
    save_progress(progress)
    return progress

def get_last_processed_time():
    """获取上次处理的时间"""
    progress = load_progress()
    return progress.get("last_processed_timestamp"), progress.get("last_processed_time")

def show_progress():
    """显示当前处理进度"""
    progress = load_progress()
    
    print("=" * 80)
    print("De.对话处理进度")
    print("=" * 80)
    print()
    
    if progress.get("last_processed_timestamp"):
        print(f"最后处理时间戳: {progress['last_processed_timestamp']}")
        if progress.get("last_processed_time"):
            print(f"最后处理时间: {progress['last_processed_time']}")
        if progress.get("last_processed_content"):
            print(f"最后处理内容: {progress['last_processed_content']}")
        if progress.get("total_processed"):
            print(f"已处理消息数: {progress['total_processed']}")
    else:
        print("尚未开始处理，或进度已重置")
    
    print()
    
    if progress.get("processing_history"):
        print("最近处理历史:")
        print("-" * 80)
        for i, record in enumerate(progress["processing_history"][-5:], 1):
            print(f"{i}. {record.get('processed_time')} - {record.get('timestamp')}")
            if record.get('content'):
                print(f"   内容: {record['content']}")
    
    print()
    print("=" * 80)

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        show_progress()
    else:
        print("用法: python record_de_dialog_progress.py show")
        print("或者在其他脚本中导入使用:")
        print("  from record_de_dialog_progress import update_progress, get_last_processed_time")

