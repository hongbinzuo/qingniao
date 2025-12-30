#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/25 18:34-18:39的De.对话
核心内容：15分钟空单信号、期权到期影响、止损策略
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
        'stop_loss': {}
    }
    
    # 提取价格
    prices = re.findall(r'(\d{3,4})', content)
    if prices:
        analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    # 15分钟空单信号
    if '15分' in content or '15分钟' in content:
        analysis['concepts'].append('15分钟时间框架')
        if '很好空' in content or '空' in content:
            analysis['trading_signal'] = {
                'timeframe': '15m',
                'direction': 'short',
                'strength': 'strong'
            }
            analysis['strategy'].append('15分钟空单')
            analysis['actions'].append('做空')
    
    # 期权到期影响
    if '期权到期' in content or '期权' in content:
        analysis['concepts'].append('期权到期影响')
        analysis['theories'].append('期权到期理论')
        if '杀' in content or '杀提前仓' in content:
            analysis['concepts'].append('期权到期杀仓')
            analysis['market_state'].append('期权到期波动')
    
    # 目标价格
    if '88-885' in content or '88到885' in content:
        analysis['prices'].extend([8800, 8850])
        analysis['trading_signal']['target'] = [8800, 8850]
        analysis['concepts'].append('目标价格区间')
    
    # 等待价格
    if '858' in content or '85' in content:
        wait_prices = []
        if '858' in content:
            wait_prices.append(8580)
        if '85' in content and '858' not in content:
            wait_prices.append(8500)
        if wait_prices:
            analysis['prices'].extend(wait_prices)
            analysis['strategy'].append('等待策略')
            analysis['concepts'].append('等待价格')
    
    # 止损策略
    if '止损' in content:
        analysis['concepts'].append('止损策略')
        if '879' in content:
            analysis['stop_loss'] = {
                'initial': 8790,
                'type': 'fixed'
            }
            analysis['prices'].append(8790)
        if '872' in content:
            analysis['prices'].append(8720)
            if '扫过872' in content:
                analysis['concepts'].append('止损调整触发')
        if '876' in content:
            analysis['prices'].append(8760)
            if '挂放876' in content or '挂876' in content:
                analysis['stop_loss']['adjusted'] = 8760
                analysis['concepts'].append('保本止损')
                analysis['strategy'].append('保本策略')
    
    # 保本理念
    if '保本' in content:
        analysis['philosophy'].append('保本优先')
        analysis['concepts'].append('保本策略')
        if '不亏就是赚' in content:
            analysis['philosophy'].append('不亏就是赚')
    
    # 交易动作
    if '撸上一把' in content:
        analysis['actions'].append('快速交易')
        analysis['concepts'].append('短期交易')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/25 18:34-18:39的De.对话")
    print("核心：15分钟空单信号、止损策略")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/25 18:34',
            'speaker': 'De.',
            'content': '15分看起来很好空，撸上一把，明天还有期权到期，晚上来一波杀提前仓的头寸，可以进空:emoji_1:，估计最多杀到88-885，下面继续等待858/85的止损',
            'context': '15分钟空单信号和期权到期分析',
            'importance': 'high',
            'has_screenshot': True
        },
        {
            'timestamp': '2025/12/25 18:39',
            'speaker': 'De.',
            'content': '这单止损放在879即可，如果扫过872，可以挂放876，保本，主打不亏就是赚，',
            'context': '止损策略详解',
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
            'has_screenshot': conv.get('has_screenshot', False),
            'has_trading_signal': bool(analysis.get('trading_signal')),
            'has_stop_loss': bool(analysis.get('stop_loss')),
            'has_options_expiry': '期权' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251225_1834.json")
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
            print(f"    交易信号: {signal.get('timeframe', '')} {signal.get('direction', '')}")
        if r.get('analysis', {}).get('stop_loss'):
            sl = r['analysis']['stop_loss']
            print(f"    止损: {sl.get('initial', '')} (初始)")
            if sl.get('adjusted'):
                print(f"            {sl.get('adjusted', '')} (调整后保本)")
        if r.get('analysis', {}).get('prices'):
            print(f"    价格: {', '.join(map(str, r['analysis']['prices']))}")

if __name__ == '__main__':
    main()


