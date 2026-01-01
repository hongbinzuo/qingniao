#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/24的De.对话
结合BTC价格和De.交易系统
"""

import re
import requests
from datetime import datetime
import json
from pathlib import Path

def get_btc_price_at_time(timestamp_str):
    """获取指定时间的BTC价格"""
    try:
        # 解析时间: 2025/12/24 1:47
        dt = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M')
        unix_ts = int(dt.timestamp())
        
        # 查询Gate.io API
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
        
        # 尝试5分钟K线
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
    """解析De.的交易指令"""
    analysis = {
        'prices': [],
        'actions': [],
        'strategy': []
    }
    
    # 提取所有价格
    prices = re.findall(r'(\d{3,4})', content)
    analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    # 提取交易动作
    if '挂' in content:
        analysis['actions'].append('挂单')
    if '保本' in content:
        analysis['actions'].append('保本止损')
    if '焊死' in content:
        analysis['actions'].append('固定持仓')
    
    # 提取策略
    if '多单' in content:
        analysis['strategy'].append('多单')
    if '空单' in content:
        analysis['strategy'].append('空单')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/24的De.对话")
    print("=" * 80)
    print()
    
    # 对话数据
    conversations = [
        {
            'timestamp': '2025/12/24 1:47',
            'speaker': 'De.',
            'content': '稳住\n你绝望了，也许就来了\n你止损了，方向就变了\n这是日常',
            'context': '用户说"866下不来了"'
        },
        {
            'timestamp': '2025/12/24 1:54',
            'speaker': 'De.',
            'content': '858挂好\n焊死\n多单都挂885保本\n空单866下面\n858-837-817-8-78-74-69\n都挂上了',
            'context': '用户说"那我挂好866睡觉嘿嘿"'
        }
    ]
    
    results = []
    
    for conv in conversations:
        timestamp_str = conv['timestamp']
        content = conv['content']
        
        print(f"处理: {timestamp_str}")
        print(f"内容: {content[:50]}...")
        
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
            'category': 'trading',
            'source': 'conversation'
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件（临时，等数据库准备好后导入）
    output_file = Path("data/de_conversations_20251224.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"已保存到: {output_file}")
    print()
    print("=" * 80)
    print("处理完成！")
    print("=" * 80)
    print()
    print("下一步:")
    print("1. 安装数据库: pip install duckdb")
    print("2. 运行: python src/database_setup.py")
    print("3. 导入这些对话到数据库")

if __name__ == '__main__':
    main()

