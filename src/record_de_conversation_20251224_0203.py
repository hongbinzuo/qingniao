#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/24 2:03-2:13的De.对话
特别关注拍卖理论和正态分布
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
        'concepts': []
    }
    
    # 提取价格
    prices = re.findall(r'(\d{3,4})', content)
    analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    # 提取交易动作
    if '挂' in content:
        analysis['actions'].append('挂单')
    if '加' in content or '加仓' in content:
        analysis['actions'].append('加仓')
    if '止损' in content:
        analysis['actions'].append('止损')
    if '头仓' in content:
        analysis['actions'].append('头仓')
    
    # 提取策略
    if '中线' in content:
        analysis['strategy'].append('中线')
    if '长线' in content:
        analysis['strategy'].append('长线')
    if '短线' in content:
        analysis['strategy'].append('短线')
    
    # 提取理论概念
    if '拍卖理论' in content:
        analysis['concepts'].append('拍卖理论')
    if '正态分布' in content:
        analysis['concepts'].append('正态分布')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/24 2:03-2:13的De.对话")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/24 2:03',
            'speaker': 'De.',
            'content': '中线858不止损\n下来加',
            'context': '用户说"866不挂了啊，直接858头仓"'
        },
        {
            'timestamp': '2025/12/24 2:04',
            'speaker': 'De.',
            'content': '对呀\n也可以说长线\n哈哈哈',
            'context': '用户问"你这是中线"'
        },
        {
            'timestamp': '2025/12/24 2:05',
            'speaker': 'De.',
            'content': '最短和最长最容易玩\n中线最难\n拍卖理论，正态分布，中间那60-80%最难',
            'context': '用户说"我的资金不允许我玩长线哈哈"'
        }
    ]
    
    results = []
    
    for conv in conversations:
        timestamp_str = conv['timestamp']
        content = conv['content']
        
        print(f"处理: {timestamp_str}")
        print(f"内容: {content[:80]}...")
        
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
            'has_theory': '拍卖理论' in content or '正态分布' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251224_0203.json")
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

