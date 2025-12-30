#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/26 0:31-0:34的De.对话
核心内容：期权交割陷阱、利空消息陷阱、交易记录、89关键位
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
        'trading_execution': {},
        'traps': []
    }
    
    # 提取价格
    prices = re.findall(r'(\d{2,4})', content)
    if prices:
        analysis['prices'] = [int(p) for p in prices if len(p) >= 2]
    
    # 期权交割陷阱
    if '期权交割' in content:
        analysis['concepts'].append('期权交割')
        if '提前空' in content and '被爆' in content:
            analysis['traps'].append('期权交割陷阱')
            analysis['concepts'].append('提前空陷阱')
            analysis['concepts'].append('被爆仓')
            analysis['theories'].append('期权交割陷阱理论')
    
    # 利空消息陷阱
    if '利空消息' in content:
        analysis['traps'].append('利空消息陷阱')
        analysis['concepts'].append('消息陷阱')
        if '提前知道' in content and '被爆' in content:
            analysis['concepts'].append('提前消息陷阱')
            analysis['concepts'].append('消息爆仓')
        if '暴完才是真的开始' in content:
            analysis['concepts'].append('爆仓后才是真行情')
            analysis['theories'].append('消息陷阱理论')
    
    # 交易记录
    if '今天下午空' in content or '下午空' in content:
        analysis['actions'].append('做空')
        analysis['concepts'].append('交易记录')
        if '空头模型' in content:
            analysis['concepts'].append('空头模型')
            analysis['strategy'].append('空头模型策略')
        if '吃了500点' in content:
            analysis['trading_execution'] = {
                'direction': 'short',
                'profit_points': 500,
                'profit_usdt': 500  # 假设1点=1 USDT
            }
            analysis['concepts'].append('盈利500点')
        if '止损吃100点' in content:
            if 'trading_execution' not in analysis:
                analysis['trading_execution'] = {}
            analysis['trading_execution']['stop_loss_points'] = 100
            analysis['concepts'].append('止损100点')
            analysis['concepts'].append('风险控制')
    
    # 关键位置
    if '89' in content and '关键' in content:
        analysis['prices'].append(8900)
        analysis['concepts'].append('关键位置')
        analysis['concepts'].append('889关键位')
        analysis['strategy'].append('关键位策略')
    
    # 明天可以空
    if '明天可以空' in content or '明天' in content and '空' in content:
        analysis['strategy'].append('明天做空')
        analysis['concepts'].append('未来交易计划')
    
    # 组织行为
    if '组织' in content:
        analysis['concepts'].append('机构组织')
        if '期权交割组织' in content:
            analysis['concepts'].append('期权交割组织')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/26 0:31-0:34的De.对话")
    print("核心：期权交割陷阱、利空消息陷阱、交易记录")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/26 0:31',
            'speaker': 'De.',
            'content': '期权交割组织，知道这个消息的会提前空，然后被爆，哈哈哈',
            'context': '期权交割陷阱理论',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/26 0:32',
            'speaker': 'De.',
            'content': '就跟一个利空消息提前让人知道，就是为了爆这个提前消息的，暴完才是真的开始，哈哈哈，今天下午空是看到了空头模型，吃了500点止损吃100点',
            'context': '利空消息陷阱理论和交易记录',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/26 0:34',
            'speaker': 'De.',
            'content': '是的，不过明天可以空，哈啊哈',
            'context': '未来交易计划',
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
            'has_trap_theory': len(analysis.get('traps', [])) > 0,
            'has_trading_execution': bool(analysis.get('trading_execution')),
            'has_key_level': '89' in content and '关键' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251226_0031.json")
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
        if r.get('analysis', {}).get('traps'):
            print(f"    陷阱理论: {', '.join(r['analysis']['traps'])}")
        if r.get('analysis', {}).get('trading_execution'):
            exec_info = r['analysis']['trading_execution']
            if exec_info.get('profit_points'):
                print(f"    交易记录: 盈利{exec_info['profit_points']}点")
            if exec_info.get('stop_loss_points'):
                print(f"              止损{exec_info['stop_loss_points']}点")
        if r.get('analysis', {}).get('concepts'):
            key_concepts = [c for c in r['analysis']['concepts'] if '陷阱' in c or '关键' in c or '模型' in c]
            if key_concepts:
                print(f"    关键概念: {', '.join(key_concepts[:5])}")

if __name__ == '__main__':
    main()


