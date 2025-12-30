#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/25 1:29-1:31的De.对话
核心内容：SOL交易经历、基本面分析、交易策略反思
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
        'philosophy': [],
        'trading_history': []
    }
    
    # SOL相关
    if 'sol' in content.lower():
        analysis['concepts'].append('SOL币种')
        if '软蛋子' in content:
            analysis['concepts'].append('SOL负面评价')
    
    # 交易历史
    prices = re.findall(r'(\d{3,4})', content)
    if prices:
        analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    if '225空到179' in content:
        analysis['trading_history'].append({
            'type': 'short',
            'entry': 225,
            'exit': 179,
            'result': 'profit'
        })
        analysis['strategy'].append('做空策略')
        analysis['concepts'].append('历史做空成功')
    
    if '低多' in content:
        analysis['strategy'].append('低多策略')
        analysis['concepts'].append('做多策略')
        if '没赚到什么' in content:
            analysis['concepts'].append('低多策略失效')
            analysis['trading_history'].append({
                'type': 'long',
                'strategy': '低多',
                'result': 'low_profit'
            })
        if '130' in content:
            analysis['prices'].append(130)
            analysis['trading_history'].append({
                'type': 'long',
                'entry': 130,
                'strategy': '低多',
                'result': 'last_attempt'
            })
    
    # 基本面分析
    if '基本面' in content:
        analysis['concepts'].append('基本面分析')
        if 'meme' in content.lower():
            analysis['concepts'].append('Meme币属性')
            analysis['theories'].append('Meme币理论')
            if 'meme不行' in content or 'meme不行了' in content:
                analysis['concepts'].append('Meme币风险')
                analysis['concepts'].append('基本面风险')
    
    # 图表分析
    if '图表' in content:
        analysis['concepts'].append('图表分析')
        if '吓人' in content or '挺吓人' in content:
            analysis['concepts'].append('图表看跌')
            analysis['market_state'].append('图表不利')
    
    # 交易策略
    if '一直不做多' in content or '再也不做了' in content:
        analysis['strategy'].append('不做多策略')
        analysis['concepts'].append('避免做多')
        analysis['philosophy'].append('策略坚持')
    
    # 情绪表达
    if '沮丧' in content:
        analysis['concepts'].append('交易情绪')
        analysis['concepts'].append('策略反思')
    
    # 关注度
    if '关注的少' in content:
        analysis['concepts'].append('关注度影响')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/25 1:29-1:31的De.对话")
    print("核心：SOL交易经历、基本面分析、策略反思")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/25 1:29',
            'speaker': 'De.',
            'content': '以前关注的少，225空到179，后面一直低多，基本没赚到什么，后面最后一次低多还是130',
            'context': 'SOL交易历史回顾',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/25 1:31',
            'speaker': 'De.',
            'content': '真是不行，我在我们自己技术群还经常沮丧，多sol这个软蛋子',
            'context': 'SOL交易策略反思',
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
            'category': 'trading_history',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_trading_history': len(analysis.get('trading_history', [])) > 0,
            'has_strategy_reflection': '沮丧' in content or '不行' in content,
            'coin': 'SOL'
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251225_0129.json")
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
        if r.get('analysis', {}).get('trading_history'):
            print(f"    交易历史: {len(r['analysis']['trading_history'])} 条")
        if r.get('analysis', {}).get('strategy'):
            print(f"    策略: {', '.join(r['analysis']['strategy'])}")
        if r.get('analysis', {}).get('concepts'):
            key_concepts = [c for c in r['analysis']['concepts'] if 'SOL' in c or 'Meme' in c or '低多' in c]
            if key_concepts:
                print(f"    关键概念: {', '.join(key_concepts)}")

if __name__ == '__main__':
    main()


