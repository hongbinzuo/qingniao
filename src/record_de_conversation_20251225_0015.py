#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/25 0:15-0:43的De.对话
核心内容：BTC长期信念、市场操纵理论、震荡磨损策略
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
    
    # BTC长期信念
    if '别放弃大饼' in content or '大饼' in content:
        analysis['philosophy'].append('BTC长期信念')
        analysis['concepts'].append('BTC价值坚持')
    
    # 市场操纵理论
    if '假象' in content or '阴谋' in content:
        analysis['theories'].append('市场操纵理论')
        analysis['concepts'].append('市场假象')
        if '坏人' in content:
            analysis['concepts'].append('市场操纵者')
    
    # 替代品理论
    if '代替品' in content or '三无确能换真金' in content:
        analysis['theories'].append('BTC替代品理论')
        analysis['concepts'].append('BTC不可替代性')
    
    # 震荡磨损策略
    if '洗多头' in content or '震荡磨损' in content:
        analysis['strategy'].append('震荡磨损策略')
        analysis['market_state'].append('震荡市场')
        analysis['concepts'].append('洗盘策略')
    
    # 反复收割
    if '反复收割' in content:
        analysis['strategy'].append('反复收割策略')
        analysis['market_state'].append('收割市场')
    
    # 期权策略
    if '期权' in content:
        analysis['strategy'].append('期权策略')
        if '错了归零对了翻倍' in content:
            analysis['concepts'].append('期权风险收益')
        if '永远洗不掉' in content:
            analysis['concepts'].append('期权优势')
    
    # 市场情绪
    if '都麻了' in content or '人越少' in content:
        analysis['market_state'].append('市场麻木')
        analysis['concepts'].append('市场情绪指标')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/25 0:15-0:43的De.对话")
    print("核心：BTC长期信念、市场操纵理论")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/25 0:15',
            'speaker': 'De.',
            'content': '别放弃大饼，都是假象，只要坏人还存在，大饼的下跌永远都是阴谋，除非出了三无确能换真金的，代替品',
            'context': 'BTC长期信念和市场操纵理论',
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
            'has_long_term_belief': '别放弃' in content or '大饼' in content,
            'has_manipulation_theory': '假象' in content or '阴谋' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251225_0015.json")
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
        if r.get('analysis', {}).get('theories'):
            print(f"    理论: {', '.join(r['analysis']['theories'])}")

if __name__ == '__main__':
    main()


