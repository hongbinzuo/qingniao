#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理De.对话并关联BTC价格
结合De.交易系统进行学习
"""

import re
from datetime import datetime
from db_config import get_db_manager
from conversation_logger import log_conversation

def get_btc_price_at_time(timestamp_str, exchange='gateio'):
    """获取指定时间的BTC价格"""
    try:
        # 解析时间戳
        if isinstance(timestamp_str, str):
            # 处理格式: 2025/12/24 1:47
            if '/' in timestamp_str:
                dt = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M')
            else:
                dt = datetime.fromisoformat(timestamp_str.replace('+08:00', ''))
        else:
            dt = timestamp_str
        
        # 转换为Unix时间戳
        unix_ts = int(dt.timestamp())
        
        # 查询Gate.io API
        import requests
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': '1m',  # 1分钟K线
            'from': unix_ts - 60,  # 往前1分钟
            'to': unix_ts + 60,    # 往后1分钟
            'limit': 3
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                # K线格式: [timestamp, volume, close, high, low, open]
                closest_candle = min(data, key=lambda x: abs(int(x[0]) - unix_ts))
                return float(closest_candle[2])  # close price
        
        # 如果1分钟K线没有，尝试5分钟
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

def parse_de_instructions(text):
    """解析De.的交易指令"""
    instructions = []
    
    # 提取价格
    prices = re.findall(r'(\d{3,4})', text)
    
    # 提取交易方向
    if '多单' in text or '做多' in text:
        direction = 'long'
    elif '空单' in text or '做空' in text:
        direction = 'short'
    else:
        direction = None
    
    # 提取挂单价格
    if '挂' in text:
        # 提取所有价格
        price_list = [int(p) for p in prices if len(p) >= 3]
        
        # 根据上下文判断
        if '多单' in text:
            # 多单挂单价格
            long_prices = [p for p in price_list if p < 90000]  # 假设当前价格在8-9万
            if long_prices:
                instructions.append({
                    'type': 'long',
                    'entry': long_prices,
                    'action': '挂单'
                })
        
        if '空单' in text:
            # 空单挂单价格
            short_prices = [p for p in price_list if p < 90000]
            if short_prices:
                instructions.append({
                    'type': 'short',
                    'entry': short_prices,
                    'action': '挂单'
                })
    
    # 提取止损/止盈
    if '保本' in text:
        # 多单保本价格
        btc_prices = re.findall(r'(\d{3,4})', text)
        if btc_prices:
            instructions.append({
                'type': 'stop_loss',
                'price': int(btc_prices[0]),
                'action': '保本止损'
            })
    
    return instructions

def process_conversation_with_price(conversations):
    """处理对话并关联价格"""
    db = get_db_manager()
    
    results = []
    
    for conv in conversations:
        timestamp_str = conv.get('timestamp')
        speaker = conv.get('speaker')
        content = conv.get('content')
        
        # 只处理De.的消息
        if speaker != 'De.':
            continue
        
        # 获取当时BTC价格
        btc_price = get_btc_price_at_time(timestamp_str)
        
        # 解析交易指令
        instructions = parse_de_instructions(content)
        
        # 构建完整的观点内容（包含价格上下文）
        full_content = content
        if btc_price:
            full_content = f"[BTC价格: ${btc_price:,.2f}] {content}"
        
        # 判断类别
        category = None
        if any(kw in content for kw in ['挂', '多单', '空单', '止损', '止盈', '保本']):
            category = 'trading'
        elif any(kw in content for kw in ['稳住', '绝望', '日常']):
            category = 'analysis'
        
        # 提取标签
        tags = []
        if '挂单' in content:
            tags.append('挂单')
        if '保本' in content:
            tags.append('保本')
        if '止损' in content:
            tags.append('止损')
        
        # 记录到数据库
        viewpoint_id = db.add_de_viewpoint(
            content=full_content,
            timestamp=timestamp_str,
            source='conversation',
            category=category,
            tags=tags
        )
        
        # 记录对话日志
        log_id = db.add_conversation_log(
            user_message=conv.get('user_message', ''),
            assistant_message=content,
            session_id=conv.get('session_id'),
            de_content=content
        )
        
        results.append({
            'viewpoint_id': viewpoint_id,
            'log_id': log_id,
            'timestamp': timestamp_str,
            'btc_price': btc_price,
            'instructions': instructions,
            'content': content
        })
    
    return results

def main():
    """处理用户提供的对话"""
    conversations = [
        {
            'timestamp': '2025/12/24 1:47',
            'speaker': '用户',
            'content': '866下不来了',
            'user_message': '866下不来了'
        },
        {
            'timestamp': '2025/12/24 1:47',
            'speaker': 'De.',
            'content': '稳住\n你绝望了，也许就来了\n你止损了，方向就变了\n这是日常',
            'user_message': '866下不来了'
        },
        {
            'timestamp': '2025/12/24 1:53',
            'speaker': '用户',
            'content': '那我挂好866\n睡觉嘿嘿',
            'user_message': '那我挂好866\n睡觉嘿嘿'
        },
        {
            'timestamp': '2025/12/24 1:54',
            'speaker': 'De.',
            'content': '858挂好\n焊死\n多单都挂885保本\n空单866下面\n858-837-817-8-78-74-69\n都挂上了',
            'user_message': '那我挂好866\n睡觉嘿嘿'
        }
    ]
    
    print("=" * 80)
    print("处理De.对话并关联BTC价格")
    print("=" * 80)
    print()
    
    results = process_conversation_with_price(conversations)
    
    print(f"处理完成，共处理 {len(results)} 条De.消息")
    print()
    
    for result in results:
        print(f"时间: {result['timestamp']}")
        if result['btc_price']:
            print(f"BTC价格: ${result['btc_price']:,.2f}")
        print(f"内容: {result['content']}")
        if result['instructions']:
            print(f"解析指令: {result['instructions']}")
        print(f"观点ID: {result['viewpoint_id']}")
        print("-" * 80)

if __name__ == '__main__':
    main()

