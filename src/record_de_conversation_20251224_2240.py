#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/24 22:40-22:42的De.对话
特别关注"猴市行情"概念
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
        'market_state': [],
        'concepts': []
    }
    
    # 提取市场状态
    if '猴市' in content:
        analysis['market_state'].append('猴市')
        analysis['concepts'].append('猴市行情')
    if '空单' in content:
        analysis['strategy'].append('空单')
    if '焊死' in content or '焊的死死的' in content:
        analysis['actions'].append('固定持仓')
    if '尾巴' in content:
        analysis['actions'].append('剩余持仓')
    
    # 提取交易动作
    if '空单' in content:
        analysis['strategy'].append('空单')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/24 22:40-22:42的De.对话")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/24 22:40',
            'speaker': 'De.',
            'content': '空单焊的死死的',
            'context': '持仓状态确认'
        },
        {
            'timestamp': '2025/12/24 22:41',
            'speaker': 'De.',
            'content': '这一针插进了心坎，哈哈哈',
            'context': '价格快速下跌，空单盈利'
        },
        {
            'timestamp': '2025/12/24 22:41',
            'speaker': 'De.',
            'content': '猴市行情',
            'context': '用户问"这是啥行情"'
        },
        {
            'timestamp': '2025/12/24 22:42',
            'speaker': 'De.',
            'content': '还有点空单还剩点尾巴了:emoji_1:',
            'context': '剩余持仓'
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
            'source': 'conversation',
            'has_market_concept': '猴市' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251224_2240.json")
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

