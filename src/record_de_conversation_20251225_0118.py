#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/25 1:18-1:20的De.对话
核心内容：预言与价值的关系、币种价值评估标准、定投策略
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
    
    # 预言与价值理论
    if '预言' in content:
        analysis['theories'].append('预言与价值理论')
        if '价值' in content:
            analysis['concepts'].append('价值基础')
        if '未来趋势' in content:
            analysis['concepts'].append('趋势判断')
    
    # 币种价值评估标准
    if '价值' in content:
        analysis['concepts'].append('价值评估')
        if '共情' in content:
            analysis['concepts'].append('市场共情')
        if '市场信誉度' in content:
            analysis['concepts'].append('市场信誉')
        if '归零' in content:
            analysis['concepts'].append('归零风险')
    
    # 三无币种
    if '没有价值' in content or '没有共情' in content or '没有市场信誉度' in content:
        analysis['concepts'].append('三无币种')
        analysis['concepts'].append('高风险币种')
    
    # 定投策略
    if '定投' in content:
        analysis['strategy'].append('定投策略')
        analysis['concepts'].append('长期投资')
    
    # 新低投资策略
    if '新低' in content:
        analysis['strategy'].append('新低投资策略')
        analysis['concepts'].append('抄底策略')
        if '大饼新低' in content:
            analysis['concepts'].append('BTC新低买入')
        if '还投' in content or '我再投' in content:
            analysis['concepts'].append('跟随投资')
    
    # 币种提及
    if 'link' in content.lower():
        analysis['concepts'].append('LINK币种')
        if '基础价值' in content:
            analysis['concepts'].append('LINK价值评估')
    
    if 'sol' in content.lower():
        analysis['concepts'].append('SOL币种')
    
    # 投资理念
    if '不在意价格' in content:
        analysis['philosophy'].append('价值投资')
        analysis['concepts'].append('价格无关投资')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/25 1:18-1:20的De.对话")
    print("核心：预言与价值、币种评估标准、投资策略")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/25 1:18',
            'speaker': 'De.',
            'content': '预言是对未来趋势的判断，但是基本基础是价值',
            'context': '预言与价值的关系',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/25 1:19',
            'speaker': 'De.',
            'content': '没有价值，没有共情，没有市场信誉度的币子最后难逃归零的结局:emoji_1:',
            'context': '币种价值评估标准',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/25 1:20',
            'speaker': 'De.',
            'content': '大饼新低的时候，他们还投，我再投',
            'context': '新低投资策略',
            'importance': 'normal'
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
            'has_value_theory': '价值' in content,
            'has_prediction_theory': '预言' in content,
            'has_investment_strategy': '新低' in content or '定投' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251225_0118.json")
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
        if r.get('analysis', {}).get('philosophy'):
            print(f"    哲学: {', '.join(r['analysis']['philosophy'])}")
        if r.get('analysis', {}).get('concepts'):
            key_concepts = [c for c in r['analysis']['concepts'] if c not in ['价值评估', '价值基础']]
            if key_concepts:
                print(f"    概念: {', '.join(key_concepts[:5])}")

if __name__ == '__main__':
    main()


