#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/26 0:36-0:38的De.对话
核心内容：策略评价、U本位vs币本位、多时间框架策略
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
        'strategy_evaluation': {}
    }
    
    # 策略评价
    if '最差' in content or '差' in content:
        analysis['concepts'].append('策略评价')
        if '无极帕尔' in content:
            analysis['strategy_evaluation'] = {
                'target': '无极帕尔',
                'rating': 'negative',
                'reason': '最差'
            }
            analysis['concepts'].append('策略负面评价')
    
    # SMC策略
    if 'smc策略' in content.lower() or 'smc' in content.lower():
        analysis['concepts'].append('SMC策略')
        analysis['strategy_evaluation']['strategy_type'] = 'SMC'
    
    # U本位vs币本位
    if 'U本位' in content:
        analysis['concepts'].append('U本位')
        if '看不到净流入数据' in content:
            analysis['concepts'].append('U本位数据限制')
            analysis['concepts'].append('数据观察问题')
    
    if '币本位' in content or 'BTC币安现货' in content:
        analysis['concepts'].append('币本位')
        if 'BTC币安现货的数据' in content:
            analysis['concepts'].append('币安现货数据')
            analysis['concepts'].append('币本位数据优势')
    
    # 多时间框架策略
    if '中线' in content:
        analysis['concepts'].append('中线交易')
        analysis['strategy'].append('中线策略')
        if '一直做低多' in content:
            analysis['strategy'].append('中线低多')
            analysis['actions'].append('做多')
            analysis['philosophy'].append('中线低多持续')
    
    if '长线' in content:
        analysis['concepts'].append('长线交易')
        analysis['strategy'].append('长线策略')
        if '还没开始布局' in content:
            analysis['concepts'].append('长线未布局')
            analysis['market_state'].append('长线等待')
    
    if '短线' in content:
        analysis['concepts'].append('短线交易')
        analysis['strategy'].append('短线策略')
        if '明天应该是空' in content:
            analysis['strategy'].append('短线做空')
            analysis['actions'].append('做空')
            analysis['concepts'].append('明天短线空')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/26 0:36-0:38的De.对话")
    print("核心：策略评价、多时间框架策略")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/26 0:36',
            'speaker': 'De.',
            'content': '无极帕尔是最差的:emoji_8:吧，哈哈哈，他做smc策略的',
            'context': '策略评价 - SMC策略',
            'importance': 'normal'
        },
        {
            'timestamp': '2025/12/26 0:38',
            'speaker': 'De.',
            'content': '我的中线一直做低多，长线还没开始布局，短线明天应该是空，哈哈哈哈',
            'context': '多时间框架策略规划',
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
            'category': 'strategy',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_strategy_evaluation': bool(analysis.get('strategy_evaluation')),
            'has_multi_timeframe': '中线' in content or '长线' in content or '短线' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251226_0036.json")
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
        if r.get('analysis', {}).get('strategy_evaluation'):
            eval_info = r['analysis']['strategy_evaluation']
            if eval_info.get('target'):
                print(f"    策略评价: {eval_info['target']} - {eval_info.get('rating', '')}")
        if r.get('analysis', {}).get('strategy'):
            print(f"    策略: {', '.join(r['analysis']['strategy'])}")
        if r.get('analysis', {}).get('concepts'):
            key_concepts = [c for c in r['analysis']['concepts'] if '线' in c or '本位' in c or 'SMC' in c]
            if key_concepts:
                print(f"    关键概念: {', '.join(key_concepts)}")

if __name__ == '__main__':
    main()


