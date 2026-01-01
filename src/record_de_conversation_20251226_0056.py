#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/26 0:56-1:01的De.对话
核心内容：交易策略、实时交易理念、市场分析
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
        'trading_philosophy': {}
    }
    
    # 提取价格（3-6位数字）
    prices = re.findall(r'(\d{3,6})', content)
    for p in prices:
        price_val = int(p)
        if 400 <= price_val <= 90000:  # 合理的价格范围
            analysis['prices'].append(price_val)
    
    # 交易策略
    if '400点' in content:
        analysis['trading_signal']['target_points'] = 400
        analysis['concepts'].append('目标400点')
    
    if '87888' in content:
        analysis['prices'].append(87888)
        analysis['trading_signal']['entry'] = 87888
        if '吃上跑路' in content:
            analysis['strategy'].append('吃上跑路策略')
            analysis['concepts'].append('快速止盈')
    
    if '跌破再空吃864' in content or '吃864' in content:
        analysis['prices'].append(8640)
        analysis['trading_signal']['target'] = 8640
        analysis['strategy'].append('跌破做空策略')
        analysis['concepts'].append('条件空单')
    
    # 1小时vegas反弹策略
    if '跌破1小时vegas反弹不破空' in content or '1小时vegas' in content:
        analysis['trading_signal']['timeframe'] = '1h'
        analysis['trading_signal']['strategy'] = 'vegas反弹不破空'
        analysis['concepts'].append('Vegas隧道')
        analysis['concepts'].append('反弹不破策略')
        analysis['theories'].append('Vegas隧道理论')
    
    if '876左右空' in content:
        analysis['prices'].append(8760)
        analysis['trading_signal']['entry'] = 8760
        analysis['trading_signal']['direction'] = 'short'
    
    if '止损488点' in content:
        analysis['trading_signal']['stop_loss_points'] = 488
        analysis['concepts'].append('止损488点')
    
    # 实时交易理念
    if '实时的' in content or '实时' in content:
        analysis['trading_philosophy']['type'] = '实时交易'
        analysis['concepts'].append('实时交易')
        analysis['philosophy'].append('实时交易理念')
    
    if '市价点位说出来且准的我觉得是大神' in content:
        analysis['trading_philosophy']['viewpoint'] = '预判点位难度'
        analysis['concepts'].append('预判点位')
        analysis['concepts'].append('点位准确性')
        analysis['philosophy'].append('交易难度认知')
    
    if '真的撸短根本看不准具体点位' in content:
        analysis['trading_philosophy']['viewpoint'] = '短线点位不可预测'
        analysis['concepts'].append('短线交易')
        analysis['concepts'].append('点位预测困难')
        analysis['philosophy'].append('短线交易理念')
    
    if '都是看强弱套模型看大概止损位，提前布置的' in content:
        analysis['trading_philosophy']['method'] = '强弱模型+提前布置'
        analysis['concepts'].append('强弱模型')
        analysis['concepts'].append('提前布置')
        analysis['strategy'].append('模型套用策略')
        analysis['theories'].append('强弱模型理论')
    
    if '且准确的真的是高手' in content:
        analysis['trading_philosophy']['viewpoint'] = '准确预判是高手'
        analysis['concepts'].append('交易水平')
        analysis['philosophy'].append('交易能力认知')
    
    # 市场分析
    if '今天这个上涨是对的，杀提前单' in content:
        analysis['market_state'].append('杀提前单')
        analysis['concepts'].append('杀提前单')
        analysis['concepts'].append('市场验证')
        analysis['theories'].append('杀提前单理论')
    
    if '88-885' in content:
        analysis['prices'].extend([8800, 8850])
        analysis['concepts'].append('价格区间88-885')
        if '这个区间是有点大' in content:
            analysis['concepts'].append('区间较大')
    
    if '到那个时候价格也才872' in content:
        analysis['prices'].append(8720)
        analysis['concepts'].append('价格预期')
        analysis['concepts'].append('区间调整')
    
    # 预判主力的预判
    if '预判了主力的预判' in content:
        analysis['concepts'].append('预判主力')
        analysis['theories'].append('主力预判理论')
        analysis['philosophy'].append('市场博弈')
    
    return analysis

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/26 0:56-1:01的De.对话")
    print("核心：交易策略、实时交易理念、市场分析")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/26 0:56',
            'speaker': 'De.',
            'content': '400点，87888，吃上跑路，跌破再空吃864，解释一下，跌破1小时vegas反弹不破空，876左右空，吃864，止损488点，gn今天完毕',
            'context': '交易策略说明',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/26 0:59',
            'speaker': 'De.',
            'content': '市价点位说出来且准的我觉得是大神，我做实时的，真的撸短根本看不准具体点位，都是看强弱套模型看大概止损位，提前布置的，且准确的真的是高手，不过今天这个上涨是对的，杀提前单，88-885，这个区间是有点大，到那个时候价格也才872',
            'context': '实时交易理念',
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
            'category': 'viewpoint' if '理念' in conv.get('context', '') else 'trading_signal',
            'source': 'conversation',
            'importance': conv.get('importance', 'normal'),
            'has_trading_philosophy': bool(analysis.get('trading_philosophy')),
            'has_trading_signal': bool(analysis.get('trading_signal'))
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251226_0056.json")
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
        print(f"\n  ⭐ {r['content'][:80]}...")
        if r.get('btc_price'):
            print(f"    BTC: ${r['btc_price']:,.2f}")
        if r.get('analysis', {}).get('trading_philosophy'):
            philo = r['analysis']['trading_philosophy']
            print(f"    交易理念: {philo}")
        if r.get('analysis', {}).get('trading_signal'):
            signal = r['analysis']['trading_signal']
            if signal.get('entry'):
                print(f"    入场: ${signal['entry']:,.0f}")
            if signal.get('target'):
                print(f"    目标: ${signal['target']:,.0f}")
            if signal.get('stop_loss_points'):
                print(f"    止损: {signal['stop_loss_points']}点")

if __name__ == '__main__':
    main()

