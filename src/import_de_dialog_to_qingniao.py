#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将De.的对话和交易记录录入青鸟系统
支持从上次处理的位置继续
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from record_de_dialog_progress import (
    load_progress,
    update_progress,
    get_last_processed_time,
    show_progress
)

# 对话文件路径
DIALOG_FILE = r"C:\Users\zuoho\Downloads\discord-msg\梦之队 - 梦梦 - 青沐 [1428778462981918951].html"

def parse_timestamp(ts):
    """解析Discord时间戳"""
    if not ts:
        return None
    try:
        if isinstance(ts, str):
            # 尝试ISO格式
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00').replace('+08:00', ''))
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
        print(f"解析时间戳失败: {e}", file=sys.stderr)
        return None
    return None

def compare_timestamps(ts1, ts2):
    """比较两个时间戳，返回ts1是否在ts2之后"""
    dt1 = parse_timestamp(ts1)
    dt2 = parse_timestamp(ts2)
    if dt1 and dt2:
        return dt1 > dt2
    # 如果无法解析，使用字符串比较
    return str(ts1) > str(ts2)

def extract_de_messages(messages, start_from_timestamp=None):
    """提取De.的消息，从指定时间戳开始"""
    de_messages = []
    for msg in messages:
        author = msg.get('author', {})
        if author.get('nickname') == 'De.':
            timestamp = msg.get('timestamp', '')
            
            # 如果指定了起始时间戳，只处理之后的消息
            if start_from_timestamp:
                if not compare_timestamps(timestamp, start_from_timestamp):
                    continue
            
            de_messages.append(msg)
    
    # 按时间戳排序
    de_messages.sort(key=lambda x: x.get('timestamp', ''))
    return de_messages

def process_de_messages(de_messages, output_file=None):
    """处理De.的消息，提取交易相关信息"""
    if not de_messages:
        print("没有需要处理的消息", file=sys.stderr)
        return
    
    print(f"开始处理 {len(de_messages)} 条De.的消息...", file=sys.stderr)
    
    # 提取交易相关信息
    trading_messages = []
    trading_records = []
    
    for i, msg in enumerate(de_messages):
        content = msg.get('content', '')
        timestamp = msg.get('timestamp', '')
        
        if not content or len(content) < 5:
            continue
        
        # 识别交易相关消息
        trading_keywords = [
            '多单', '空单', '做多', '做空', '挂单', '开', '平', '止损', '止盈',
            '加仓', '减仓', '入场', '出场', 'BTC', 'btc', '大饼',
            '区间', '突破', '回踩', '支撑', '阻力', 'Vegas', 'vegas',
            '盈亏比', '杠杆', '逐仓', '仓位'
        ]
        
        is_trading_related = any(kw in content for kw in trading_keywords)
        
        if is_trading_related:
            trading_messages.append({
                'timestamp': timestamp,
                'content': content,
                'type': 'trading'
            })
        
        # 识别交易记录（包含价格和方向）
        if any(kw in content for kw in ['多单', '空单', '做多', '做空']) and any(char.isdigit() for char in content):
            trading_records.append({
                'timestamp': timestamp,
                'content': content,
                'type': 'trade_record'
            })
        
        # 每处理100条消息更新一次进度
        if (i + 1) % 100 == 0:
            update_progress(timestamp, content, i + 1)
            print(f"  已处理: {i + 1}/{len(de_messages)}", file=sys.stderr)
    
    # 更新最终进度
    if de_messages:
        last_msg = de_messages[-1]
        update_progress(
            last_msg.get('timestamp'),
            last_msg.get('content'),
            len(de_messages)
        )
    
    print(f"处理完成:", file=sys.stderr)
    print(f"  - 交易相关消息: {len(trading_messages)} 条", file=sys.stderr)
    print(f"  - 交易记录: {len(trading_records)} 条", file=sys.stderr)
    
    # 生成报告
    report = []
    report.append("# De.对话和交易记录录入报告")
    report.append("")
    report.append(f"**处理时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report.append(f"**处理消息数**: {len(de_messages)}  ")
    report.append(f"**交易相关消息**: {len(trading_messages)} 条  ")
    report.append(f"**交易记录**: {len(trading_records)} 条  ")
    report.append("")
    
    # 显示最后处理的消息
    if de_messages:
        last_msg = de_messages[-1]
        last_timestamp = last_msg.get('timestamp', '')
        last_dt = parse_timestamp(last_timestamp)
        report.append("## 最后处理的消息")
        report.append("")
        if last_dt:
            report.append(f"**时间**: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}  ")
        else:
            report.append(f"**时间戳**: {last_timestamp}  ")
        report.append(f"**内容**: {last_msg.get('content', '')[:200])}  ")
        report.append("")
    
    # 显示交易相关消息（最近20条）
    if trading_messages:
        report.append("## 交易相关消息（最近20条）")
        report.append("")
        for i, msg in enumerate(trading_messages[-20:], 1):
            timestamp = msg.get('timestamp', '')
            dt = parse_timestamp(timestamp)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S') if dt else timestamp
            content = msg.get('content', '')[:150]
            report.append(f"### {i}. {time_str}")
            report.append(f"{content}")
            report.append("")
    
    # 显示交易记录（最近10条）
    if trading_records:
        report.append("## 交易记录（最近10条）")
        report.append("")
        for i, record in enumerate(trading_records[-10:], 1):
            timestamp = record.get('timestamp', '')
            dt = parse_timestamp(timestamp)
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S') if dt else timestamp
            content = record.get('content', '')[:200]
            report.append(f"### {i}. {time_str}")
            report.append(f"{content}")
            report.append("")
    
    report.append("---")
    report.append("")
    report.append("**说明**: 所有消息已处理完成，进度已保存。下次运行将从最后处理的消息继续。")
    
    # 保存报告
    if output_file:
        output_path = Path(output_file)
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path(f"De_对话录入报告_{timestamp}.md")
    
    output_path.write_text('\n'.join(report), encoding='utf-8')
    print(f"\n报告已保存到: {output_path}", file=sys.stderr)
    
    return {
        'total_processed': len(de_messages),
        'trading_messages': len(trading_messages),
        'trading_records': len(trading_records),
        'last_timestamp': de_messages[-1].get('timestamp') if de_messages else None
    }

def main():
    """主函数"""
    print("=" * 80)
    print("De.对话和交易记录录入系统")
    print("=" * 80)
    print()
    
    # 显示当前进度
    last_timestamp, last_time = get_last_processed_time()
    if last_timestamp:
        print(f"上次处理时间: {last_time}")
        print(f"上次处理时间戳: {last_timestamp}")
        print()
        choice = input("是否从上次位置继续？(y/n，默认y): ").strip().lower()
        if choice != 'n':
            start_from = last_timestamp
        else:
            start_from = None
            print("将从第一条消息开始处理")
    else:
        print("首次处理，将从第一条消息开始")
        start_from = None
    
    print()
    
    # 读取对话文件
    if not os.path.exists(DIALOG_FILE):
        print(f"错误: 对话文件不存在: {DIALOG_FILE}", file=sys.stderr)
        return
    
    print("正在读取对话文件...", file=sys.stderr)
    try:
        with open(DIALOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}", file=sys.stderr)
        return
    
    messages = data.get('messages', [])
    print(f"总消息数: {len(messages)}", file=sys.stderr)
    
    # 提取De.的消息
    de_messages = extract_de_messages(messages, start_from)
    print(f"需要处理的De.消息数: {len(de_messages)}", file=sys.stderr)
    
    if not de_messages:
        print("没有需要处理的新消息", file=sys.stderr)
        return
    
    # 处理消息
    result = process_de_messages(de_messages)
    
    print()
    print("=" * 80)
    print("处理完成！")
    print("=" * 80)
    print(f"处理消息数: {result['total_processed']}")
    print(f"交易相关消息: {result['trading_messages']} 条")
    print(f"交易记录: {result['trading_records']} 条")
    if result['last_timestamp']:
        last_dt = parse_timestamp(result['last_timestamp'])
        if last_dt:
            print(f"最后处理时间: {last_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("下次运行将自动从最后处理的消息继续")
    print("=" * 80)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        show_progress()
    else:
        main()

