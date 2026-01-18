#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gate.io扩展K线数据获取
支持超过单次限制的数据获取（通过from/to参数）
"""
import requests
import time

def get_kline_gateio_extended(symbol='BTC', timeframe='15m', days=90):
    """
    从Gate.io获取扩展的K线数据（支持超过单次限制）
    
    Args:
        symbol: 交易对
        timeframe: 时间框架（如'15m'）
        days: 需要的天数
    
    Returns:
        K线数据列表（按时间从早到晚排序）
    """
    # 计算每天需要的K线数
    klines_per_day_map = {
        '5m': 288,   # 24 * 60 / 5
        '15m': 96,   # 24 * 60 / 15
        '1h': 24,
        '4h': 6,
        '1d': 1
    }
    klines_per_day = klines_per_day_map.get(timeframe, 96)
    total_needed = days * klines_per_day
    max_per_request = 1000  # Gate.io单次最大1000
    
    tf_map = {
        '5m': '5m',
        '15m': '15m',
        '1h': '1h',
        '4h': '4h',
        '1d': '1d'
    }
    interval = tf_map.get(timeframe, '15m')
    
    # 构建交易对
    if symbol == 'BTC':
        pair = 'BTC_USDT'
    else:
        pair = f'{symbol}_USDT'
    
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    all_klines = []
    
    try:
        # 第一次请求：获取最新的数据
        params = {
            'currency_pair': pair,
            'interval': interval,
            'limit': min(max_per_request, total_needed)
        }
        
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            return []
        
        data = response.json()
        if not data:
            return []
        
        # Gate.io返回的是从新到旧，需要反转
        data.reverse()
        klines = []
        for k in data:
            klines.append({
                'timestamp': int(k[0]),
                'open': float(k[5]),
                'high': float(k[3]),
                'low': float(k[4]),
                'close': float(k[2]),
                'volume': float(k[1])
            })
        
        all_klines = klines
        
        # 如果还需要更多数据，继续请求
        while len(all_klines) < total_needed:
            # 获取当前最旧的时间戳
            oldest_timestamp = all_klines[0]['timestamp']
            
            # 计算还需要的数据量
            remaining = total_needed - len(all_klines)
            if remaining <= 0:
                break
            
            # 请求更早的数据
            params = {
                'currency_pair': pair,
                'interval': interval,
                'from': oldest_timestamp - 1,  # 从更早的时间开始
                'to': oldest_timestamp,
                'limit': min(remaining, max_per_request)
            }
            
            response = requests.get(url, params=params, timeout=30)
            if response.status_code != 200:
                break
            
            data = response.json()
            if not data or len(data) == 0:
                break  # 没有更多数据了
            
            # Gate.io返回的是从新到旧，需要反转
            data.reverse()
            new_klines = []
            for k in data:
                new_klines.append({
                    'timestamp': int(k[0]),
                    'open': float(k[5]),
                    'high': float(k[3]),
                    'low': float(k[4]),
                    'close': float(k[2]),
                    'volume': float(k[1])
                })
            
            if not new_klines:
                break
            
            # 合并数据（从早到晚）
            all_klines = new_klines + all_klines
            
            # 避免请求过快
            time.sleep(0.1)
        
        # 去重（按timestamp）
        seen = set()
        unique_klines = []
        for k in all_klines:
            ts = k['timestamp']
            if ts not in seen:
                seen.add(ts)
                unique_klines.append(k)
        
        # 确保按时间排序（从早到晚）
        unique_klines.sort(key=lambda x: x['timestamp'])
        
        # 只返回需要的数量（最新的N根）
        if len(unique_klines) > total_needed:
            return unique_klines[-total_needed:]
        
        return unique_klines
        
    except Exception as e:
        # 如果扩展API失败，返回空列表或使用标准API
        return []



