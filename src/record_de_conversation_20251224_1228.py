#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/24 12:28-12:31的De.对话
"""

import re
import requests
from datetime import datetime
import json
from pathlib import Path

def get_btc_price_at_time(timestamp_str):
    """获取指定时间的BTC价格"""
    try:
        dt = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M')
        unix_ts = int(dt.timestamp())
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': '1m',
            'from': unix_ts - 60,
            'to': unix_ts + 60,
            'limit': 3
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                closest_candle = min(data, key=lambda x: abs(int(x[0]) - unix_ts))
                return float(closest_candle[2])
        
        params['interval'] = '5m'
        params['from'] = unix_ts - 300
        params['to'] = unix_ts + 300
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                closest_candle = min(data, key=lambda x: abs(int(x[0]) - unix_ts))
                return float(closest_candle[2])
        
        return None
    except Exception as e:
        print(f"获取价格失败: {e}")
        return None

def parse_de_instructions(content):
    """解析De.的交易指令和观点"""
    analysis = {
        'prices': [],
        'actions': [],
        'strategy': [],
        'timeframe': [],
        'concepts': []
    }
    
    # 提取价格
    prices = re.findall(r'(\d{3,4})', content)
    analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    # 提取时间框架
    if '15分' in content or '15分钟' in content:
        analysis['timeframe'].append('15分钟')
    
    # 提取交易动作
    if '突破' in content:
        analysis['actions'].append('突破')
    if '反转' in content:
        analysis['actions'].append('反转')
    if '焊死' in content:
        analysis['actions'].append('固定持仓')
    if '空单' in content:
        analysis['strategy'].append('空单')
    
    # 提取概念
    if '反转' in content:
        analysis['concepts'].append('反转形态')
    if '突破' in content:
        analysis['concepts'].append('突破')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/24 12:28-12:31的De.对话")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/24 12:28',
            'speaker': 'De.',
            'content': '现在这个15分走的真垮，需要突破878，算15分的反转',
            'context': '分析15分钟走势'
        },
        {
            'timestamp': '2025/12/24 12:31',
            'speaker': 'De.',
            'content': '今天又是空单焊死了:emoji_8:',
            'context': '交易状态确认'
        }
    ]
    
    results = []
    
    for conv in conversations:
        timestamp_str = conv['timestamp']
        content = conv['content']
        
        print(f"处理: {timestamp_str}")
        print(f"内容: {content}")
        
        # 获取BTC价格
        btc_price = get_btc_price_at_time(timestamp_str)
        if btc_price:
            print(f"BTC价格: ${btc_price:,.2f}")
        else:
            print("BTC价格: 无法获取")
        
        # 解析指令
        analysis = parse_de_instructions(content)
        print(f"解析: {analysis}")
        
        # 构建完整记录
        record = {
            'timestamp': timestamp_str,
            'content': content,
            'btc_price': btc_price,
            'analysis': analysis,
            'context': conv.get('context', ''),
            'category': 'trading',
            'source': 'conversation'
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251224_1228.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"已保存到: {output_file}")
    print()
    print("=" * 80)
    print("处理完成！")
    print("=" * 80)

if __name__ == '__main__':
    main()

