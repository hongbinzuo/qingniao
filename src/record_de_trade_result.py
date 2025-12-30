#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
记录De.的交易结果
从交易截图或交易记录中提取信息并录入系统
"""

import re
from datetime import datetime
from db_config import get_db_manager

def parse_trade_screenshot(text):
    """解析交易截图信息"""
    trade_info = {}
    
    # 提取时间
    time_match = re.search(r'(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})', text)
    if time_match:
        trade_info['timestamp'] = time_match.group(1)
    
    # 提取交易对
    if 'BTC/USDT' in text:
        trade_info['symbol'] = 'BTC/USDT'
    
    # 提取方向
    if '空' in text or 'short' in text.lower():
        trade_info['direction'] = 'short'
    elif '多' in text or 'long' in text.lower():
        trade_info['direction'] = 'long'
    
    # 提取杠杆
    leverage_match = re.search(r'(\d+)x', text)
    if leverage_match:
        trade_info['leverage'] = int(leverage_match.group(1))
    
    # 提取收益率
    profit_pct_match = re.search(r'\+?([\d.]+)%', text)
    if profit_pct_match:
        trade_info['profit_pct'] = float(profit_pct_match.group(1))
    
    # 提取盈利金额
    profit_usdt_match = re.search(r'\+?([\d.]+)\s*USDT', text)
    if profit_usdt_match:
        trade_info['profit_usdt'] = float(profit_usdt_match.group(1))
    
    # 提取开仓均价
    entry_match = re.search(r'開倉均價[：:]\s*([\d,.]+)', text)
    if entry_match:
        price_str = entry_match.group(1).replace(',', '')
        trade_info['entry_price'] = float(price_str)
    
    # 提取最新价格
    current_match = re.search(r'最新價格[：:]\s*([\d,.]+)', text)
    if current_match:
        price_str = current_match.group(1).replace(',', '')
        trade_info['current_price'] = float(price_str)
    
    return trade_info

def calculate_trade_analysis(trade_info):
    """计算交易分析"""
    analysis = {}
    
    entry = trade_info.get('entry_price')
    current = trade_info.get('current_price')
    direction = trade_info.get('direction')
    profit_pct = trade_info.get('profit_pct')
    
    if entry and current:
        if direction == 'short':
            # 空单：价格下跌盈利
            price_change = entry - current
            price_change_pct = (price_change / entry) * 100
        else:
            # 多单：价格上涨盈利
            price_change = current - entry
            price_change_pct = (price_change / entry) * 100
        
        analysis['price_change'] = price_change
        analysis['price_change_pct'] = price_change_pct
    
    # 计算盈亏比（如果有止损信息）
    # 这里可以根据实际情况计算
    
    return analysis

def record_trade_result(trade_info):
    """记录交易结果到数据库"""
    try:
        db = get_db_manager()
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        return None
    
    # 构建交易记录内容
    timestamp = trade_info.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    direction = trade_info.get('direction', 'unknown')
    symbol = trade_info.get('symbol', 'BTC/USDT')
    leverage = trade_info.get('leverage', 0)
    entry_price = trade_info.get('entry_price', 0)
    current_price = trade_info.get('current_price', 0)
    profit_pct = trade_info.get('profit_pct', 0)
    profit_usdt = trade_info.get('profit_usdt', 0)
    
    # 计算分析
    analysis = calculate_trade_analysis(trade_info)
    
    # 构建完整内容
    content_parts = [
        f"交易记录: {symbol} {direction.upper()} {leverage}x",
        f"时间: {timestamp}",
        f"开仓均价: ${entry_price:,.2f}",
        f"最新价格: ${current_price:,.2f}",
        f"收益率: +{profit_pct:.2f}%",
        f"盈利: +{profit_usdt:.2f} USDT"
    ]
    
    if analysis.get('price_change'):
        content_parts.append(f"价格变化: ${analysis['price_change']:,.2f} ({analysis['price_change_pct']:.2f}%)")
    
    content = "\n".join(content_parts)
    
    # 判断类别
    category = 'trading'
    
    # 提取标签
    tags = ['交易记录', '实盘']
    if direction == 'short':
        tags.append('空单')
    elif direction == 'long':
        tags.append('多单')
    if leverage > 1:
        tags.append(f'{leverage}x杠杆')
    if profit_pct > 0:
        tags.append('盈利')
    
    # 转换为标准时间格式
    try:
        if '/' in timestamp:
            dt = datetime.strptime(timestamp, '%Y/%m/%d %H:%M:%S')
        else:
            dt = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
        timestamp_std = dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        timestamp_std = timestamp
    
    # 添加到数据库
    try:
        vp_id = db.add_de_viewpoint(
            content=content,
            timestamp=timestamp_std,
            source='trade_record',
            category=category,
            tags=tags
        )
        
        # 关闭数据库连接
        if hasattr(db, 'close'):
            db.close()
        
        return vp_id
    except Exception as e:
        print(f"记录失败: {e}")
        return None

def main():
    """主函数"""
    # 从截图描述中提取的信息
    trade_info = {
        'timestamp': '2025/12/24 01:55:37',
        'symbol': 'BTC/USDT',
        'direction': 'short',
        'leverage': 33,
        'profit_pct': 89.61,
        'profit_usdt': 243.93,
        'entry_price': 89820.3,
        'current_price': 87381.0
    }
    
    print("=" * 80)
    print("记录De.交易结果")
    print("=" * 80)
    print()
    
    print("交易信息:")
    print(f"  时间: {trade_info['timestamp']}")
    print(f"  交易对: {trade_info['symbol']}")
    print(f"  方向: {trade_info['direction'].upper()}")
    print(f"  杠杆: {trade_info['leverage']}x")
    print(f"  开仓均价: ${trade_info['entry_price']:,.2f}")
    print(f"  最新价格: ${trade_info['current_price']:,.2f}")
    print(f"  收益率: +{trade_info['profit_pct']:.2f}%")
    print(f"  盈利: +{trade_info['profit_usdt']:.2f} USDT")
    print()
    
    # 计算分析
    analysis = calculate_trade_analysis(trade_info)
    if analysis.get('price_change'):
        print(f"价格变化: ${analysis['price_change']:,.2f} ({analysis['price_change_pct']:.2f}%)")
    print()
    
    # 记录到数据库
    vp_id = record_trade_result(trade_info)
    
    if vp_id:
        print(f"[OK] 已记录到数据库 (观点ID: {vp_id})")
    else:
        print("[ERROR] 记录失败，请检查数据库配置")
    
    print()
    print("=" * 80)

if __name__ == '__main__':
    main()

