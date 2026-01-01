#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置De.对话录入的起始时间
用于手动指定从哪条消息开始处理
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from record_de_dialog_progress import update_progress, show_progress

def parse_timestamp(ts):
    """解析时间戳"""
    if not ts:
        return None
    try:
        if isinstance(ts, str):
            if 'T' in ts:
                dt = datetime.fromisoformat(ts.replace('+08:00', ''))
                return dt
            else:
                return datetime.fromisoformat(ts)
        return None
    except:
        return None

def set_start_time(timestamp=None):
    """设置起始时间"""
    if timestamp:
        # 更新进度，设置为已处理到该时间戳（这样下次会从该时间戳之后开始）
        update_progress(timestamp, "手动设置起始时间", 0)
        print(f"已设置起始时间戳: {timestamp}")
        
        dt = parse_timestamp(timestamp)
        if dt:
            print(f"对应时间: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("请提供时间戳，格式: 2025-12-20T00:39:15.261+08:00")

def main():
    """主函数"""
    print("=" * 80)
    print("设置De.对话录入起始时间")
    print("=" * 80)
    print()
    
    # 显示当前进度
    show_progress()
    print()
    
    # 显示最后一条消息
    file_path = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        messages = data.get('messages', [])
        de_messages = [m for m in messages if m.get('author', {}).get('nickname') == 'De.']
        de_messages.sort(key=lambda x: x.get('timestamp', ''))
        
        if de_messages:
            last_msg = de_messages[-1]
            last_timestamp = last_msg.get('timestamp', '')
            last_content = last_msg.get('content', '')[:100]
            
            print("对话文件中的最后一条消息:")
            print(f"  时间戳: {last_timestamp}")
            print(f"  内容: {last_content}")
            print()
            
            # 询问是否使用最后一条消息的时间戳
            print("选项:")
            print("1. 从最后一条消息之后开始（首次录入，处理所有消息）")
            print("2. 从最后一条消息开始（跳过最后一条，从倒数第二条之后开始）")
            print("3. 手动输入时间戳")
            print("4. 取消")
            print()
            
            choice = input("请选择 (1/2/3/4): ").strip()
            
            if choice == '1':
                # 从最后一条消息之后开始，意味着处理所有消息
                # 不设置进度，让系统从第一条开始
                print("\n已清除进度，下次运行将从第一条消息开始处理所有消息")
                # 清空进度文件
                progress_file = Path(__file__).parent / "de_dialog_progress.json"
                if progress_file.exists():
                    progress_file.write_text(json.dumps({
                        "last_processed_timestamp": None,
                        "last_processed_time": None,
                        "total_processed": 0,
                        "last_processed_content": None,
                        "processing_history": []
                    }, ensure_ascii=False, indent=2), encoding='utf-8')
            elif choice == '2':
                # 从最后一条消息开始，意味着跳过最后一条
                # 找到倒数第二条消息
                if len(de_messages) > 1:
                    second_last = de_messages[-2]
                    set_start_time(second_last.get('timestamp'))
                    print("\n已设置：下次将从倒数第二条消息之后开始（跳过最后一条）")
                else:
                    print("只有一条消息，无法设置")
            elif choice == '3':
                timestamp = input("请输入时间戳 (格式: 2025-12-20T00:39:15.261+08:00): ").strip()
                if timestamp:
                    set_start_time(timestamp)
                else:
                    print("时间戳不能为空")
            else:
                print("已取消")
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        if len(sys.argv) > 1:
            # 命令行参数模式
            timestamp = sys.argv[1]
            set_start_time(timestamp)

if __name__ == '__main__':
    main()

