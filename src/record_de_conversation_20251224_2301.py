#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/24 22:57-23:24的De.对话
核心内容：订单簿流动性理论 - 价格区间没有对手单的逻辑
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
        'orderbook_insights': [],
        'theories': []
    }
    
    # 提取价格
    prices = re.findall(r'(\d{3,4})', content)
    if prices:
        analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    # 核心理论：订单簿流动性逻辑
    if '没有卖单' in content or '没有单子' in content or '区间没有' in content:
        analysis['theories'].append('订单簿流动性理论')
        analysis['concepts'].append('价格区间流动性缺失')
        analysis['orderbook_insights'].append('订单簿稀疏区分析')
    
    # 庄家行为理论
    if '庄家' in content or '后台数据' in content:
        analysis['theories'].append('庄家行为理论')
        analysis['concepts'].append('庄家数据优势')
        if '不划算' in content:
            analysis['concepts'].append('庄家成本效益分析')
    
    # 价格区间分析
    if '86-8635' in content or '86到8635' in content:
        analysis['prices'].extend([8600, 8635])
        analysis['strategy'].append('价格区间86-8635流动性分析')
    
    # 最低成交价
    if '最低成交' in content:
        analysis['concepts'].append('最低成交价')
        if '8635' in content:
            analysis['prices'].append(8635)
    
    # 挂单逻辑
    if '买单价格' in content or '卖单' in content:
        analysis['strategy'].append('挂单策略')
        analysis['orderbook_insights'].append('对手单分析')
    
    # 市场微观结构
    if '价格没到' in content or '不是价格没到' in content:
        analysis['theories'].append('市场微观结构理论')
        analysis['concepts'].append('价格vs流动性')
    
    # 观察价格
    if '862' in content:
        analysis['prices'].append(862)
        analysis['strategy'].append('观察862价格')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/24 22:57-23:24的De.对话")
    print("核心：订单簿流动性理论")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/24 23:01',
            'speaker': 'De.',
            'content': '也不是止损，就比如，如果庄家把买单价格放到了86，但是86-8635这个区间没有卖单，最低成交在8635，所以不是价格没到86，而是这个区间没有单子交易，大概这个逻辑吧',
            'context': '订单簿流动性理论核心解释',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/24 23:02',
            'speaker': 'De.',
            'content': '现实是这个逻辑不成立了，大庄家肯定能看后台数据，下去不划算，就不会下去了',
            'context': '庄家行为理论 - 数据优势',
            'importance': 'high'
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
            'category': 'theory',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_orderbook_theory': '没有卖单' in content or '没有单子' in content,
            'has_market_microstructure': '价格没到' in content or '不是价格没到' in content,
            'has_whale_behavior': '庄家' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251224_2301.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"已保存到: {output_file}")
    print()
    print("=" * 80)
    print("处理完成！")
    print("=" * 80)
    print(f"\n✅ 处理De.对话: {len(results)} 条")
    
    # 显示关键理论
    print("\n📚 核心理论:")
    for r in results:
        print(f"\n  ⭐ {r['content']}")
        if r.get('btc_price'):
            print(f"    BTC: ${r['btc_price']:,.2f}")
        if r.get('analysis', {}).get('theories'):
            print(f"    理论: {', '.join(r['analysis']['theories'])}")
        if r.get('analysis', {}).get('concepts'):
            print(f"    概念: {', '.join(r['analysis']['concepts'])}")

if __name__ == '__main__':
    main()


