#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/25 1:23-1:24的De.对话
核心内容：等待耐心、稳健交易系统、低风险投资策略
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
    
    # 等待耐心
    if '等待' in content or '耐心' in content:
        analysis['philosophy'].append('等待耐心')
        analysis['concepts'].append('耐心投资')
        analysis['strategy'].append('等待策略')
    
    # 稳健交易系统
    if '稳健' in content or '交易系统' in content:
        analysis['concepts'].append('稳健交易系统')
        analysis['strategy'].append('稳健策略')
        if '稳健的交易系统' in content:
            analysis['theories'].append('稳健系统理论')
    
    # 低风险投资
    if '低风险' in content or '更低风险' in content:
        analysis['strategy'].append('低风险投资策略')
        analysis['concepts'].append('风险控制')
        analysis['philosophy'].append('风险优先')
    
    # 资金对比
    if '有钱' in content or '没他有钱' in content:
        analysis['concepts'].append('资金规模对比')
        analysis['concepts'].append('小资金策略')
    
    # 价格判断
    prices = re.findall(r'(\d{2,4})', content)
    if prices:
        analysis['prices'] = [int(p) for p in prices if len(p) >= 2]
    
    if '60' in content and '给脸' in content:
        analysis['concepts'].append('价格判断')
        analysis['concepts'].append('价格预期')
        analysis['prices'].append(60000)
    
    # 投资优势
    if '比他' in content or '更低' in content:
        analysis['concepts'].append('相对优势')
        analysis['strategy'].append('差异化策略')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/25 1:23-1:24的De.对话")
    print("核心：等待耐心、稳健系统、低风险投资")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/25 1:23',
            'speaker': 'De.',
            'content': '没他有钱，但是我比他有等待的耐心也行，在他稳健的交易系统下拿下比他更低风险的投资',
            'context': '等待耐心与稳健系统',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/25 1:24',
            'speaker': 'De.',
            'content': '60都是给脸了',
            'context': '价格判断',
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
            'category': 'strategy',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_patience_philosophy': '等待' in content or '耐心' in content,
            'has_robust_system': '稳健' in content or '交易系统' in content,
            'has_low_risk_strategy': '低风险' in content or '更低风险' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251225_0123.json")
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
            key_concepts = [c for c in r['analysis']['concepts'] if c not in ['价格判断']]
            if key_concepts:
                print(f"    概念: {', '.join(key_concepts[:5])}")

if __name__ == '__main__':
    main()


