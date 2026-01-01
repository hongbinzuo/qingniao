#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/25 1:05-1:06的De.对话
核心内容：蝴蝶效应理论、模型公开的影响
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
    
    # 蝴蝶效应理论
    if '蝴蝶效应' in content:
        analysis['theories'].append('蝴蝶效应理论')
        analysis['concepts'].append('市场影响传播')
        if '小的' in content:
            analysis['concepts'].append('小影响')
        if '大可' in content or '大' in content:
            analysis['concepts'].append('大影响')
    
    # 模型公开的影响
    if '模型' in content:
        analysis['concepts'].append('交易模型')
        if '一千倍' in content:
            analysis['concepts'].append('高收益模型')
        if '公开' in content or '掏出' in content:
            analysis['concepts'].append('模型公开风险')
        if '吃一顿很惨' in content:
            analysis['concepts'].append('模型失效风险')
    
    # 数据整理
    if '整理数据' in content:
        analysis['actions'].append('数据整理')
        analysis['concepts'].append('数据分析')
    
    # 市场影响
    if '影响' in content:
        analysis['concepts'].append('市场影响')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/25 1:05-1:06的De.对话")
    print("核心：蝴蝶效应理论、模型公开影响")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/25 1:06',
            'speaker': 'De.',
            'content': '蝴蝶效应很正常，但是都是小的，大可就会影响，比如予以掏出他一千倍的模型，大家都会吃一顿很惨的',
            'context': '蝴蝶效应理论和模型公开风险',
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
            'has_butterfly_effect': '蝴蝶效应' in content,
            'has_model_risk': '模型' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251225_0106.json")
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
        if r.get('analysis', {}).get('theories'):
            print(f"    理论: {', '.join(r['analysis']['theories'])}")
        if r.get('analysis', {}).get('concepts'):
            print(f"    概念: {', '.join(r['analysis']['concepts'])}")

if __name__ == '__main__':
    main()


