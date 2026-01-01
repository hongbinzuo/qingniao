#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/25 1:11-1:14的De.对话
核心内容：巨鲸狙杀理论、模型跟随风险、事以密成理念
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
    
    # 巨鲸狙杀理论
    if '巨鲸' in content or '狙杀' in content:
        analysis['theories'].append('巨鲸狙杀理论')
        analysis['concepts'].append('巨鲸行为')
        analysis['concepts'].append('模型狙杀')
    
    # 模型跟随风险
    if '模型' in content:
        analysis['concepts'].append('交易模型')
        if '跟随' in content or '跟随的人多了' in content:
            analysis['concepts'].append('模型跟随风险')
            analysis['theories'].append('模型失效理论')
        if '被狙杀' in content:
            analysis['concepts'].append('模型被狙杀')
    
    # 事以密成理念
    if '事以密成' in content:
        analysis['philosophy'].append('事以密成')
        analysis['concepts'].append('策略保密')
        analysis['strategy'].append('保密策略')
    
    # 阻止理论
    if '阻止' in content:
        analysis['concepts'].append('市场阻止机制')
    
    # 频道规模
    if '频道' in content:
        analysis['concepts'].append('信息传播')
        if '不够' in content or '全上也不够' in content:
            analysis['concepts'].append('规模限制')
    
    # 资金体量
    if '资金体量' in content or '体量' in content:
        analysis['concepts'].append('资金规模')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/25 1:11-1:14的De.对话")
    print("核心：巨鲸狙杀理论、模型跟随风险")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/25 1:11',
            'speaker': 'De.',
            'content': '是巨鲸狙杀阻止，一个好的模型，跟随的人多了，最后结果都是被狙杀',
            'context': '巨鲸狙杀理论和模型跟随风险',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/25 1:14',
            'speaker': 'De.',
            'content': '这个频道全上也不够啊',
            'context': '频道规模限制',
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
            'category': 'theory',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_whale_hunt_theory': '巨鲸' in content or '狙杀' in content,
            'has_model_follow_risk': '跟随' in content and '模型' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251225_0111.json")
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
            print(f"    概念: {', '.join(r['analysis']['concepts'][:5])}")  # 只显示前5个

if __name__ == '__main__':
    main()


