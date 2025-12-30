#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录2025/12/26 0:27-0:30的De.对话
核心内容：期权交割影响分析、价格预测、交易策略
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
        'price_prediction': {}
    }
    
    # 提取价格
    prices = re.findall(r'(\d{3,4})', content)
    if prices:
        analysis['prices'] = [int(p) for p in prices if len(p) >= 3]
    
    # 期权交割影响
    if '期权交割' in content or '期权' in content:
        analysis['concepts'].append('期权交割')
        analysis['theories'].append('期权交割理论')
        if '砸' in content:
            analysis['concepts'].append('期权交割砸盘')
            if '1-3%' in content or '1%' in content or '3%' in content:
                analysis['price_prediction']['drop_range'] = '1-3%'
                analysis['concepts'].append('期权交割跌幅预测')
            if '900-2700点' in content or '900' in content or '2700' in content:
                analysis['price_prediction']['drop_points'] = [900, 2700]
                analysis['concepts'].append('期权交割点数预测')
    
    # 价格预测
    if '最低' in content or '到哪里' in content:
        analysis['concepts'].append('价格预测')
        analysis['concepts'].append('最低价预测')
    
    # 交易策略
    if '884吃了' in content or '884' in content:
        analysis['prices'].append(8840)
        analysis['actions'].append('884止盈')
        analysis['strategy'].append('分批止盈')
        analysis['trading_signal']['tp1'] = 8840
    
    if '889' in content:
        analysis['prices'].append(8890)
        if '下个就889' in content:
            analysis['trading_signal']['tp2'] = 8890
            analysis['strategy'].append('下一个目标889')
        if '889吃完' in content:
            analysis['concepts'].append('889止盈完成')
            analysis['actions'].append('889止盈')
    
    # 空单策略
    if '空进去' in content or '空' in content:
        analysis['strategy'].append('做空策略')
        analysis['actions'].append('做空')
        if '吃到864' in content:
            analysis['prices'].append(8640)
            analysis['trading_signal']['target'] = 8640
            analysis['concepts'].append('空单目标864')
    
    # 时间条件
    if '一小时内' in content or '一小时' in content:
        analysis['concepts'].append('时间条件')
        analysis['concepts'].append('1小时时间窗口')
        if '收进884下面' in content:
            analysis['concepts'].append('价格回调确认')
            analysis['trading_signal']['entry_condition'] = 'price_below_8840_after_1h'
    
    # 华尔街假期
    if '华尔街' in content or '放假' in content:
        analysis['concepts'].append('华尔街假期')
        analysis['market_state'].append('市场假期')
    
    return analysis

def calculate_min_price(current_price, drop_pct_range, drop_points_range):
    """计算最低价格"""
    if not current_price:
        return None
    
    results = []
    
    # 基于百分比计算
    if drop_pct_range:
        if '1-3%' in drop_pct_range or '1%' in drop_pct_range:
            min_pct = 0.01
            max_pct = 0.03
            min_price_pct = current_price * (1 - max_pct)
            max_price_pct = current_price * (1 - min_pct)
            results.append({
                'method': 'percentage',
                'min': min_price_pct,
                'max': max_price_pct,
                'range': f'{min_price_pct:.0f}-{max_price_pct:.0f}'
            })
    
    # 基于点数计算
    if drop_points_range:
        min_points = min(drop_points_range)
        max_points = max(drop_points_range)
        min_price_points = current_price - max_points
        max_price_points = current_price - min_points
        results.append({
            'method': 'points',
            'min': min_price_points,
            'max': max_price_points,
            'range': f'{min_price_points:.0f}-{max_price_points:.0f}'
        })
    
    return results

def main():
    """主函数"""
    print("=" * 80)
    print("记录2025/12/26 0:27-0:30的De.对话")
    print("核心：期权交割影响、价格预测、交易策略")
    print("=" * 80)
    print()
    
    conversations = [
        {
            'timestamp': '2025/12/26 0:27',
            'speaker': 'De.',
            'content': '明天期权交割啊，不得得砸1-3% .吗，900-2700点，自己算算最低到哪里，今天既然上来了884吃了，下个就889了',
            'context': '期权交割影响分析和价格预测',
            'importance': 'high'
        },
        {
            'timestamp': '2025/12/26 0:30',
            'speaker': 'De.',
            'content': '如果889吃完一小时后内收进884下面老实空进去吃到864',
            'context': '交易策略 - 条件空单',
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
        
        # 计算最低价格（如果是第一个消息）
        if '最低到哪里' in content and btc_price:
            price_pred = analysis.get('price_prediction', {})
            drop_range = price_pred.get('drop_range')
            drop_points = price_pred.get('drop_points')
            if drop_range or drop_points:
                min_price_calc = calculate_min_price(btc_price, drop_range, drop_points)
                if min_price_calc:
                    analysis['price_prediction']['calculated_min'] = min_price_calc
                    print(f"价格预测计算: {min_price_calc}")
        
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
            'has_options_expiry': '期权交割' in content,
            'has_price_prediction': '最低' in content or '到哪里' in content,
            'has_trading_strategy': '空进去' in content or '吃到' in content
        }
        
        results.append(record)
        print("-" * 80)
        print()
    
    # 保存到JSON文件
    output_file = Path("data/de_conversations_20251226_0027.json")
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
        if r.get('analysis', {}).get('price_prediction'):
            pred = r['analysis']['price_prediction']
            if pred.get('drop_range'):
                print(f"    跌幅预测: {pred['drop_range']}")
            if pred.get('drop_points'):
                print(f"    点数预测: {pred['drop_points']}")
            if pred.get('calculated_min'):
                for calc in pred['calculated_min']:
                    print(f"    最低价({calc['method']}): ${calc['range']}")
        if r.get('analysis', {}).get('trading_signal'):
            signal = r['analysis']['trading_signal']
            if signal.get('tp1'):
                print(f"    止盈1: ${signal['tp1']:,.0f}")
            if signal.get('tp2'):
                print(f"    止盈2: ${signal['tp2']:,.0f}")
            if signal.get('target'):
                print(f"    目标: ${signal['target']:,.0f}")
            if signal.get('entry_condition'):
                print(f"    入场条件: {signal['entry_condition']}")

if __name__ == '__main__':
    main()


