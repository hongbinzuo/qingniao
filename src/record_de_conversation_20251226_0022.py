#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/26 0:22-0:25的De.对话
核心内容：杀提前仓、神秘组织砸盘、1小时做多止损、结构突破
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
    
    # 杀提前仓
    if '杀提前仓' in content or '杀提前' in content:
        analysis['concepts'].append('杀提前仓')
        analysis['market_state'].append('提前仓清理')
        analysis['theories'].append('期权到期理论')
    
    # 神秘组织砸盘
    if '神秘组织' in content or '砸盘' in content:
        analysis['concepts'].append('神秘组织')
        analysis['concepts'].append('机构砸盘')
        analysis['theories'].append('机构行为理论')
        if '微策略' in content:
            analysis['concepts'].append('微策略')
    
    # 量能分析
    if '量能' in content:
        analysis['concepts'].append('量能分析')
        if '小级别' in content:
            analysis['concepts'].append('小级别量能')
        if '还行' in content:
            analysis['market_state'].append('量能正常')
    
    # 1小时做多止损
    if '1小时' in content or '1h' in content.lower():
        analysis['concepts'].append('1小时时间框架')
        if '做多' in content:
            analysis['trading_signal'] = {
                'timeframe': '1h',
                'direction': 'long',
                'stop_loss': 8730
            }
            analysis['strategy'].append('1小时做多')
            analysis['actions'].append('做多')
        if '止损873' in content or '止损 873' in content:
            analysis['stop_loss'] = {
                'price': 8730,
                'type': 'long_stop_loss'
            }
            analysis['prices'].append(8730)
    
    # 结构突破
    if '结构突破' in content or '突破' in content:
        analysis['concepts'].append('结构突破')
        analysis['strategy'].append('突破策略')
        if '879' in content:
            analysis['prices'].append(8790)
            analysis['trading_signal']['breakout'] = 8790
            analysis['concepts'].append('879结构突破')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/26 0:22-0:25的De.对话")
    print("核心：杀提前仓、机构砸盘、1小时做多策略")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/26 0:22',
            'speaker': 'De.',
            'content': '杀提前仓，明天神秘组织砸盘',
            'context': '市场分析和机构行为预测',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/26 0:23',
            'speaker': 'De.',
            'content': '目前1小时的是做多止损873，有879的结构突破',
            'context': '1小时做多策略和结构突破',
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
            'has_trading_signal': bool(analysis.get('trading_signal')),
            'has_stop_loss': bool(analysis.get('stop_loss')),
            'has_institutional_analysis': '神秘组织' in content or '砸盘' in content,
            'has_structure_breakout': '结构突破' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251226_0022.json")
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
            if signal.get('timeframe'):
                print(f"    交易信号: {signal.get('timeframe', '')} {signal.get('direction', '')}")
            if signal.get('stop_loss'):
                print(f"    止损: ${signal.get('stop_loss', 0):,.0f}")
            if signal.get('breakout'):
                print(f"    突破: ${signal.get('breakout', 0):,.0f}")
        if r.get('analysis', {}).get('concepts'):
            key_concepts = [c for c in r['analysis']['concepts'] if '神秘' in c or '结构' in c or '量能' in c]
            if key_concepts:
                print(f"    关键概念: {', '.join(key_concepts)}")

if __name__ == '__main__':
    main()


