#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/26 0:43-0:53的De.对话
核心内容：数据来源、多空双杀单交易记录、交易策略
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
        'trading_execution': {},
        'data_sources': []
    }
    
    # 数据来源
    if 'coinb' in content.lower() or 'coinglass' in content.lower():
        if 'coinb' in content.lower():
            analysis['data_sources'].append('CoinB')
        if 'coinglass' in content.lower():
            analysis['data_sources'].append('Coinglass')
        analysis['concepts'].append('数据来源')
    
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
    
    # 多空双杀单
    if '多空双杀' in content or '多空双杀单' in content:
        analysis['concepts'].append('多空双杀')
        analysis['strategy'].append('多空双杀策略')
        analysis['theories'].append('多空双杀理论')
    
    # 交易执行记录
    if '扫了866下方' in content or '866下方' in content:
        analysis['prices'].append(8660)
        analysis['concepts'].append('866下方扫单')
        analysis['actions'].append('扫单')
    
    if '突上868追单' in content or '868追单' in content:
        analysis['prices'].append(8680)
        analysis['actions'].append('追单')
        analysis['strategy'].append('突破追单策略')
        if '目标是885' in content:
            analysis['prices'].append(8850)
            analysis['trading_execution']['target'] = 8850
    
    # 止盈记录
    if '止盈' in content:
        analysis['concepts'].append('止盈')
        if '883止盈' in content or '止盈第一883' in content:
            analysis['prices'].append(8830)
            analysis['trading_execution']['tp1'] = 8830
            analysis['concepts'].append('第一止盈')
        if '88618止盈' in content or '全部88618' in content:
            analysis['prices'].append(88618)
            analysis['trading_execution']['tp2'] = 88618
            analysis['concepts'].append('全部止盈')
    
    # 止损记录
    if '止损' in content:
        analysis['concepts'].append('止损')
        if '杀84止损' in content or '84止损' in content:
            analysis['prices'].append(8400)
            analysis['trading_execution']['stop_loss'] = 8400
        if '876也止损' in content or '876止损' in content:
            analysis['prices'].append(8760)
            analysis['trading_execution']['stop_loss_2'] = 8760
    
    # 挂单
    if '挂单' in content:
        analysis['actions'].append('挂单')
        if '挂保本' in content:
            analysis['strategy'].append('保本挂单')
            analysis['concepts'].append('保本策略')
        if '吃100点' in content:
            analysis['trading_signal']['target_points'] = 100
            analysis['concepts'].append('目标100点')
    
    # 实时交易
    if '实时的' in content or '实时' in content:
        analysis['concepts'].append('实时交易')
        analysis['strategy'].append('实时策略')
    
    # 400年
    if '400年' in content:
        analysis['concepts'].append('400年')
        if '拿下' in content:
            analysis['actions'].append('400年拿下')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/26 0:43-0:53的De.对话")
    print("核心：数据来源、多空双杀单交易记录")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/26 0:43',
            'speaker': 'De.',
            'content': '我看的coinb，coinglass',
            'context': '数据来源说明',
            'importance': 'normal'
        },
        {
            'timestamp': '2025/12/26 0:44',
            'speaker': 'De.',
            'content': '这单883止盈过',
            'context': '交易执行记录',
            'importance': 'normal'
        },
        {
            'timestamp': '2025/12/26 0:45',
            'speaker': 'De.',
            'content': '这是昨天的多空双杀单，我昨天做的实时的，昨天扫了866下方，后面突上868追单目标是885，止盈第一883，全部88618，杀84止损，目前挂单876也止损，88618止盈也在，今天差一点',
            'context': '多空双杀单完整交易记录',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/26 0:53',
            'speaker': 'De.',
            'content': '400年拿下，可以挂保本吃100点',
            'context': '交易策略建议',
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
            'category': 'trading_execution',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_data_sources': len(analysis.get('data_sources', [])) > 0,
            'has_trading_execution': bool(analysis.get('trading_execution')),
            'has_double_kill_strategy': '多空双杀' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251226_0043.json")
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
        if r.get('analysis', {}).get('data_sources'):
            print(f"    数据来源: {', '.join(r['analysis']['data_sources'])}")
        if r.get('analysis', {}).get('trading_execution'):
            exec_info = r['analysis']['trading_execution']
            if exec_info.get('tp1'):
                print(f"    止盈1: ${exec_info['tp1']:,.0f}")
            if exec_info.get('tp2'):
                print(f"    止盈2: ${exec_info['tp2']:,.0f}")
            if exec_info.get('target'):
                print(f"    目标: ${exec_info['target']:,.0f}")
            if exec_info.get('stop_loss'):
                print(f"    止损: ${exec_info['stop_loss']:,.0f}")
        if r.get('analysis', {}).get('trading_signal'):
            signal = r['analysis']['trading_signal']
            if signal.get('target_points'):
                print(f"    目标点数: {signal['target_points']}点")

if __name__ == '__main__':
    main()


