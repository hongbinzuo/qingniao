#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/25 20:35-20:36的De.对话
核心内容：交易执行记录、部分止盈、加仓机会分析
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
        'trading_execution': {}
    }
    
    # 提取价格
    prices = re.findall(r'(\d{5})', content)  # 5位数字（如87218）
    if prices:
        analysis['prices'] = [int(p) for p in prices]
    
    # 提取4位数字价格（如874, 876）
    prices_4 = re.findall(r'(\d{3,4})', content)
    if prices_4:
        for p in prices_4:
            if len(p) == 3 or len(p) == 4:
                price_val = int(p)
                if 800 <= price_val <= 900:  # 合理的价格范围
                    if price_val not in analysis['prices']:
                        analysis['prices'].append(price_val)
    
    # 挂单止盈
    if '挂单' in content and '止盈' in content:
        analysis['actions'].append('挂单止盈')
        analysis['concepts'].append('部分止盈')
        analysis['strategy'].append('分批止盈策略')
        if '87218' in content:
            analysis['trading_execution'] = {
                'action': 'partial_take_profit',
                'price': 87218,
                'type': 'limit_order'
            }
    
    # 止损等待
    if '876' in content and '止损' in content:
        analysis['concepts'].append('止损等待')
        analysis['prices'].append(8760)
        analysis['trading_execution']['stop_loss_wait'] = 8760
    
    # 加仓机会
    if '加仓' in content or '加仓空' in content:
        analysis['strategy'].append('加仓策略')
        analysis['concepts'].append('加仓机会')
        if '874-876' in content or '874到876' in content:
            analysis['prices'].extend([8740, 8760])
            analysis['trading_execution']['add_position_zone'] = [8740, 8760]
            analysis['concepts'].append('加仓区间')
    
    # 市场状态
    if '不开市' in content or '休息' in content:
        analysis['market_state'].append('市场休市')
        analysis['concepts'].append('交易暂停')
    
    # 正常逻辑
    if '正常来讲' in content:
        analysis['concepts'].append('正常市场逻辑')
        analysis['theories'].append('市场逻辑理论')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/25 20:35-20:36的De.对话")
    print("核心：交易执行记录、部分止盈、加仓机会")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/25 20:35',
            'speaker': 'De.',
            'content': '挂单87218止盈了部分剩下的留给876打止损:emoji_8:',
            'context': '交易执行记录 - 部分止盈',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/25 20:36',
            'speaker': 'De.',
            'content': '正常来讲这个874-876是加仓空的机会，但是今天好像不开市吧',
            'context': '加仓机会分析',
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
            'category': 'trading_execution',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_trading_execution': bool(analysis.get('trading_execution')),
            'has_partial_tp': '部分' in content and '止盈' in content,
            'has_add_position': '加仓' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251225_2035.json")
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
        if r.get('analysis', {}).get('trading_execution'):
            exec_info = r['analysis']['trading_execution']
            if exec_info.get('action') == 'partial_take_profit':
                print(f"    执行: 部分止盈 @ ${exec_info.get('price', 0):,.0f}")
            if exec_info.get('add_position_zone'):
                print(f"    加仓区间: ${exec_info['add_position_zone'][0]:,.0f} - ${exec_info['add_position_zone'][1]:,.0f}")
        if r.get('analysis', {}).get('strategy'):
            print(f"    策略: {', '.join(r['analysis']['strategy'])}")

if __name__ == '__main__':
    main()


