#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/26 0:34-0:35的De.对话
核心内容：币本位vs油本位、中线低多策略
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
        'theories': [],
        'philosophy': []
    }
    
    # 币本位vs油本位
    if '币本位' in content:
        analysis['concepts'].append('币本位')
        analysis['philosophy'].append('币本位思维')
        analysis['theories'].append('币本位理论')
    
    if '油本位' in content:
        analysis['concepts'].append('油本位')
        if '意义不是很大' in content:
            analysis['concepts'].append('油本位意义有限')
            analysis['philosophy'].append('油本位不重要')
    
    # 中线策略
    if '中线' in content:
        analysis['concepts'].append('中线交易')
        analysis['strategy'].append('中线策略')
        if '低多为主' in content:
            analysis['strategy'].append('中线低多')
            analysis['actions'].append('做多')
            analysis['philosophy'].append('中线低多为主')
    
    # 价格提及
    prices = re.findall(r'(\d{3,4})', content)
    if prices:
        analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    if '862' in content:
        analysis['prices'].append(8620)
        analysis['concepts'].append('862价格')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/26 0:34-0:35的De.对话")
    print("核心：币本位vs油本位、中线低多策略")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/26 0:34',
            'speaker': 'De.',
            'content': '看币本位，油本位，意义不是很大',
            'context': '币本位vs油本位的观点',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/26 0:35',
            'speaker': 'De.',
            'content': '中线还是低多为主',
            'context': '中线交易策略',
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
            'category': 'philosophy',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_coin_standard': '币本位' in content,
            'has_oil_standard': '油本位' in content,
            'has_mid_term_strategy': '中线' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251226_0034.json")
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
    print("\n📚 核心观点:")
    for r in results:
        print(f"\n  ⭐ {r['content']}")
        if r.get('btc_price'):
            print(f"    BTC: ${r['btc_price']:,.2f}")
        if r.get('analysis', {}).get('philosophy'):
            print(f"    哲学: {', '.join(r['analysis']['philosophy'])}")
        if r.get('analysis', {}).get('strategy'):
            print(f"    策略: {', '.join(r['analysis']['strategy'])}")
        if r.get('analysis', {}).get('concepts'):
            key_concepts = [c for c in r['analysis']['concepts'] if '本位' in c or '中线' in c]
            if key_concepts:
                print(f"    关键概念: {', '.join(key_concepts)}")

if __name__ == '__main__':
    main()


