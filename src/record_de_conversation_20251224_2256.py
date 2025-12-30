#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/24 22:49-22:56的De.对话
关注挂单策略和订单簿流动性分析
"""

import re
import requests
from datetime import datetime
import json
from pathlib import Path
import sys

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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
        'concepts': [],
        'orderbook_insights': []
    }
    
    # 提取价格
    prices = re.findall(r'(\d{3,4})', content)
    if prices:
        analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    # 提取挂单相关
    if '挂' in content:
        analysis['actions'].append('挂单')
        if '858' in content:
            analysis['prices'].append(858)
            analysis['strategy'].append('挂单858')
        if '864' in content:
            analysis['prices'].append(864)
            analysis['strategy'].append('挂单864')
        if '866' in content:
            analysis['prices'].append(866)
            analysis['strategy'].append('挂单866')
    
    # 提取市场状态
    if '多空双杀' in content:
        analysis['market_state'].append('多空双杀')
        analysis['concepts'].append('多空双杀局')
    
    # 提取订单簿相关观点
    if '单子少' in content or '没打进去' in content:
        analysis['orderbook_insights'].append('订单簿流动性分析')
        if '864下方单子少' in content:
            analysis['concepts'].append('订单簿稀疏区')
            analysis['strategy'].append('挂单在流动性稀疏区')
    
    # 提取价格区间
    if '866-858' in content:
        analysis['prices'].extend([866, 858])
        analysis['strategy'].append('价格区间866-858')
    
    # 提取交易所信息
    if '欧易' in content or 'OKX' in content:
        analysis['strategy'].append('关注欧易价格')
        if '8635' in content:
            analysis['prices'].append(8635)
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/24 22:49-22:56的De.对话")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/24 22:49',
            'speaker': '用户',
            'content': '空仓了',
            'context': '用户状态'
        },
        {
            'timestamp': '2025/12/24 22:53',
            'speaker': 'De.',
            'content': '今晚多空双杀局吗',
            'context': '市场状态判断'
        },
        {
            'timestamp': '2025/12/24 22:54',
            'speaker': 'De.',
            'content': '我挂的858没到',
            'context': '挂单策略'
        },
        {
            'timestamp': '2025/12/24 22:55',
            'speaker': 'De.',
            'content': '欧易最低8635',
            'context': '交易所价格观察'
        },
        {
            'timestamp': '2025/12/24 22:56',
            'speaker': 'De.',
            'content': '看来866-858，这里864下方单子少，没打进去',
            'context': '订单簿流动性分析'
        }
    ]
    
    results = []
    
    for conv in conversations:
        timestamp_str = conv['timestamp']
        speaker = conv['speaker']
        content = conv['content']
        
        # 只处理De.的消息
        if speaker != 'De.':
            continue
        
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
            'has_orderbook_insight': '单子少' in content or '没打进去' in content,
            'has_market_state': '多空双杀' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251224_2256.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"已保存到: {output_file}")
    print()
    print("=" * 80)
    print("处理完成！")
    print("=" * 80)
    print(f"\n✅ 处理De.对话: {len(results)} 条")
    
    # 显示关键观点
    print("\n📝 关键观点:")
    for r in results:
        print(f"  - {r['content']}")
        if r.get('btc_price'):
            print(f"    BTC: ${r['btc_price']:,.2f}")
        if r.get('has_orderbook_insight'):
            print(f"    ⭐ 订单簿流动性洞察")

if __name__ == '__main__':
    main()
