#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/26 0:42的De.对话
核心内容：币本位净流入策略、交易信号、交易执行记录
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
        'trading_signal': {},
        'trading_execution': {}
    }
    
    # 提取价格（5位数字）
    prices_5 = re.findall(r'(\d{5})', content)
    if prices_5:
        analysis['prices'].extend([int(p) for p in prices_5])
    
    # 提取4位数字价格
    prices_4 = re.findall(r'(\d{3,4})', content)
    if prices_4:
        for p in prices_4:
            if len(p) >= 3:
                price_val = int(p)
                if 800 <= price_val <= 900:  # 合理的价格范围
                    if price_val not in analysis['prices']:
                        analysis['prices'].append(price_val)
    
    # 币本位净流入策略
    if '币本位' in content:
        analysis['concepts'].append('币本位')
        if '净流入' in content:
            analysis['concepts'].append('净流入数据')
            analysis['strategy'].append('币本位净流入策略')
            if '高位' in content:
                analysis['concepts'].append('净流入高位')
                if '空' in content:
                    analysis['strategy'].append('净流入高位做空')
                    analysis['theories'].append('净流入反向策略')
                    analysis['concepts'].append('净流入反向交易')
    
    # 交易信号
    if '88418空' in content or '88418' in content:
        analysis['prices'].append(88418)
        analysis['trading_signal'] = {
            'entry': 88418,
            'direction': 'short',
            'stop_loss': 'breakeven',
            'target': 87888
        }
        analysis['actions'].append('做空')
        analysis['strategy'].append('保本止损策略')
    
    if '87888' in content:
        analysis['prices'].append(87888)
        if '吃87888' in content:
            analysis['trading_signal']['target'] = 87888
            analysis['concepts'].append('目标价格')
    
    # 保本止损
    if '保本损' in content or '保本' in content:
        analysis['concepts'].append('保本止损')
        analysis['strategy'].append('保本策略')
        analysis['philosophy'].append('保本优先')
    
    # 交易执行记录
    if '已经200点' in content or '200点' in content:
        analysis['trading_execution'] = {
            'profit_points': 200,
            'status': 'in_profit'
        }
        analysis['concepts'].append('盈利200点')
    
    # 做多策略
    if '87的多' in content or '87多' in content:
        analysis['prices'].append(8700)
        analysis['actions'].append('做多')
        analysis['strategy'].append('做多策略')
        if '875止损' in content:
            analysis['prices'].append(8750)
            analysis['trading_signal']['long_stop_loss'] = 8750
        if '吃五百' in content or '吃500' in content:
            analysis['trading_signal']['long_target'] = 9200  # 87 + 5 = 92
            analysis['concepts'].append('目标500点')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/26 0:42的De.对话")
    print("核心：币本位净流入策略、交易信号")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/26 0:42',
            'speaker': 'De.',
            'content': '币本位做多，现在显示净流入，净流入目前高位，我空，哈哈哈，88418空，保本损，吃87888',
            'context': '币本位净流入策略和交易信号',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/26 0:42',
            'speaker': 'De.',
            'content': '已经200点的:emoji_8:，87的多875止损，吃五百够了',
            'context': '交易执行记录和多单策略',
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
            'category': 'trading_signal',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_netflow_strategy': '净流入' in content,
            'has_trading_signal': bool(analysis.get('trading_signal')),
            'has_trading_execution': bool(analysis.get('trading_execution'))
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251226_0042.json")
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
        if r.get('analysis', {}).get('trading_signal'):
            signal = r['analysis']['trading_signal']
            if signal.get('entry'):
                print(f"    交易信号: {signal.get('direction', '')} @ ${signal['entry']:,.0f}")
            if signal.get('target'):
                print(f"    目标: ${signal['target']:,.0f}")
            if signal.get('stop_loss'):
                print(f"    止损: {signal['stop_loss']}")
        if r.get('analysis', {}).get('trading_execution'):
            exec_info = r['analysis']['trading_execution']
            if exec_info.get('profit_points'):
                print(f"    执行: 盈利{exec_info['profit_points']}点")
        if r.get('analysis', {}).get('concepts'):
            key_concepts = [c for c in r['analysis']['concepts'] if '净流入' in c or '保本' in c]
            if key_concepts:
                print(f"    关键概念: {', '.join(key_concepts)}")

if __name__ == '__main__':
    main()


