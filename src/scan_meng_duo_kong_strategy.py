#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
梦多空策略 - 涨幅榜扫描和交易计划生成
每2小时扫描一次，筛选符合做空和做多条件的币种
"""

import requests
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 黑名单：这些币种将被排除，不再出现
BLACKLIST = {
    'MEE',      # 只有现货，且是小所
    'LAVA',     # 加入黑名单
    'OBOL',     # 加入黑名单
    'LITKEY',   # 加入黑名单
}

# ==================== 交易所API函数 ====================

def get_tickers_bitget(limit: int = 100) -> List[Dict]:
    """从Bitget获取涨幅榜数据（按24小时涨幅从高到低排序）"""
    try:
        url = "https://api.bitget.com/api/spot/v1/market/tickers"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                tickers = data['data']
                # 筛选USDT交易对
                usdt_pairs = [t for t in tickers if t.get('symbol', '').endswith('USDT')]
                # 按24h涨跌幅排序（从高到低）- 这就是涨幅榜排序
                usdt_pairs.sort(key=lambda x: float(x.get('changePercent24h', 0)), reverse=True)
                return usdt_pairs[:limit]  # 返回涨幅榜前N名
    except Exception as e:
        print(f"Bitget获取失败: {e}", file=sys.stderr)
    return []


def get_tickers_bybit(limit: int = 100) -> List[Dict]:
    """从Bybit获取涨幅榜数据（按24小时涨幅从高到低排序）"""
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {
            'category': 'spot'
        }
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0 and data.get('result') and data['result'].get('list'):
                tickers = data['result']['list']
                # 筛选USDT交易对
                usdt_pairs = [t for t in tickers if t.get('symbol', '').endswith('USDT')]
                # 按24h涨跌幅排序（从高到低）- 这就是涨幅榜排序
                usdt_pairs.sort(key=lambda x: float(x.get('price24hPcnt', 0)) * 100, reverse=True)
                return usdt_pairs[:limit]  # 返回涨幅榜前N名
    except Exception as e:
        print(f"Bybit获取失败: {e}", file=sys.stderr)
    return []


def get_tickers_binance(limit: int = 100) -> List[Dict]:
    """从Binance获取涨幅榜数据"""
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 筛选USDT交易对
            usdt_pairs = [t for t in data if t.get('symbol', '').endswith('USDT')]
            # 按24h涨跌幅排序（从高到低）
            usdt_pairs.sort(key=lambda x: float(x.get('priceChangePercent', 0)), reverse=True)
            return usdt_pairs[:limit]
    except Exception as e:
        print(f"Binance获取失败: {e}", file=sys.stderr)
    return []


def get_top_gainers(limit: int = 100, exchange: str = 'bitget') -> List[Dict]:
    """获取涨幅榜数据（优先顺序：Bitget -> Bybit -> Binance）"""
    tickers = []
    
    if exchange == 'bitget' or exchange == 'auto':
        tickers = get_tickers_bitget(limit)
        if tickers:
            return tickers, 'Bitget'
    
    if exchange == 'bybit' or (exchange == 'auto' and not tickers):
        tickers = get_tickers_bybit(limit)
        if tickers:
            return tickers, 'Bybit'
    
    if exchange == 'binance' or (exchange == 'auto' and not tickers):
        tickers = get_tickers_binance(limit)
        if tickers:
            return tickers, 'Binance'
    
    return [], None


# ==================== 数据标准化 ====================

def normalize_ticker_data(ticker: Dict, exchange: str) -> Optional[Dict]:
    """将不同交易所的数据格式标准化"""
    try:
        if exchange == 'Bitget':
            symbol = ticker.get('symbol', '').replace('USDT', '')
            price = float(ticker.get('lastPr', 0))
            change_24h = float(ticker.get('changePercent24h', 0))
            high_24h = float(ticker.get('high24h', 0))
            low_24h = float(ticker.get('low24h', 0))
            volume_24h = float(ticker.get('baseVolume', 0))
            
        elif exchange == 'Bybit':
            symbol = ticker.get('symbol', '').replace('USDT', '')
            price = float(ticker.get('lastPrice', 0))
            change_24h = float(ticker.get('price24hPcnt', 0)) * 100  # Bybit是小数形式
            high_24h = float(ticker.get('highPrice24h', 0))
            low_24h = float(ticker.get('lowPrice24h', 0))
            volume_24h = float(ticker.get('volume24h', 0))
            
        elif exchange == 'Binance':
            symbol = ticker.get('symbol', '').replace('USDT', '')
            price = float(ticker.get('lastPrice', 0))
            change_24h = float(ticker.get('priceChangePercent', 0))
            high_24h = float(ticker.get('highPrice', 0))
            low_24h = float(ticker.get('lowPrice', 0))
            volume_24h = float(ticker.get('volume', 0))
        else:
            return None
        
        if price <= 0 or symbol == '':
            return None
        
        # 检查是否在黑名单中
        if symbol.upper() in BLACKLIST:
            return None  # 黑名单币种，直接返回None，会被后续过滤掉
        
        return {
            'symbol': symbol,
            'price': price,
            'change_24h': change_24h,
            'high_24h': high_24h,
            'low_24h': low_24h,
            'volume_24h': volume_24h,
            'exchange': exchange
        }
    except Exception as e:
        print(f"数据标准化失败: {e}", file=sys.stderr)
        return None


# ==================== K线数据获取（用于计算斐波那契扩展位）====================

def get_daily_klines(symbol: str, exchange: str) -> Optional[List[Dict]]:
    """获取日线K线数据（用于计算斐波那契扩展位）"""
    try:
        if exchange == 'Bitget':
            url = "https://api.bitget.com/api/spot/v1/market/candles"
            params = {
                'symbol': f'{symbol}USDT',
                'granularity': '1day',
                'limit': 60  # 获取60天数据，确保有足够数据识别三个点
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '00000' and data.get('data'):
                    klines_data = data['data']
                    klines_data.reverse()
                    klines = []
                    for k in klines_data:
                        klines.append({
                            'timestamp': int(k[0]) // 1000,
                            'open': float(k[1]),
                            'high': float(k[3]),
                            'low': float(k[4]),
                            'close': float(k[2]),
                            'volume': float(k[5])
                        })
                    return klines
        
        elif exchange == 'Bybit':
            url = "https://api.bybit.com/v5/market/kline"
            params = {
                'category': 'spot',
                'symbol': f'{symbol}USDT',
                'interval': 'D',
                'limit': 60  # 获取60天数据
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0 and data.get('result') and data['result'].get('list'):
                    klines_data = data['result']['list']
                    klines_data.reverse()
                    klines = []
                    for k in klines_data:
                        klines.append({
                            'timestamp': int(k[0]) // 1000,
                            'open': float(k[1]),
                            'high': float(k[2]),
                            'low': float(k[3]),
                            'close': float(k[4]),
                            'volume': float(k[5])
                        })
                    return klines
        
        elif exchange == 'Binance':
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': f'{symbol}USDT',
                'interval': '1d',
                'limit': 60  # 获取60天数据
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                klines = []
                for k in data:
                    klines.append({
                        'timestamp': int(k[0]) // 1000,
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    })
                return klines
    except Exception as e:
        print(f"获取{symbol}的K线数据失败: {e}", file=sys.stderr)
    
    return None


def find_swing_points(klines: List[Dict], current_price: float, lookback: int = 5) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
    """找到三点法的三个关键点（做空场景 - 标准三点法）
    
    标准三点法画法：
    - A点：最近一轮上涨的起始低点（不是历史最低点）
    - B点：最近一轮上涨的终点高点
    - C点：如果价格回调了，用回调低点；如果价格还在上涨，用B点本身
    """
    if len(klines) < 10:
        return None, None, None
    
    try:
        # 1. 先找到最近的高点作为B点（从后往前找）
        b_point = None
        b_idx = None
        max_high = float('-inf')
        
        # 从后往前找，找到最近一个显著高点
        for i in range(len(klines) - 1, max(0, len(klines) - 30), -1):
            is_swing_high = True
            # 检查是否是摆动高点
            for j in range(max(0, i - lookback), min(len(klines), i + lookback + 1)):
                if j != i and klines[j]['high'] > klines[i]['high']:
                    is_swing_high = False
                    break
            
            if is_swing_high and klines[i]['high'] > max_high:
                max_high = klines[i]['high']
                b_point = {'price': klines[i]['high'], 'index': i, 'timestamp': klines[i]['timestamp']}
                b_idx = i
        
        # 如果没有找到显著高点，使用最近30根K线中的最高点
        if b_idx is None:
            recent_klines = klines[-30:] if len(klines) >= 30 else klines
            max_high = max([k['high'] for k in recent_klines])
            for i in range(len(klines) - 1, -1, -1):
                if klines[i]['high'] == max_high:
                    b_point = {'price': klines[i]['high'], 'index': i, 'timestamp': klines[i]['timestamp']}
                    b_idx = i
                    break
        
        if b_idx is None:
            return None, None, None
        
        # 2. 找到这轮上涨的起始点A点（B点之前的显著低点）
        a_point = None
        a_idx = None
        if b_idx > 0:
            min_low = float('inf')
            # 在B点之前寻找低点（最多往前看30根K线）
            start_idx = max(0, b_idx - 30)
            for i in range(start_idx, b_idx):
                if klines[i]['low'] < min_low:
                    min_low = klines[i]['low']
                    a_point = {'price': klines[i]['low'], 'index': i, 'timestamp': klines[i]['timestamp']}
                    a_idx = i
        
        if a_idx is None or a_point is None:
            return None, None, None
        
        # 3. 确定C点
        # 如果当前价格 < B点，说明有回调，寻找回调低点
        # 如果当前价格 >= B点，说明还在上涨，C点 = B点（标准三点法）
        c_point = None
        
        if current_price < b_point['price']:
            # 有回调，寻找B点之后的最低点
            min_after_b = float('inf')
            c_idx = None
            for i in range(b_idx + 1, len(klines)):
                if klines[i]['low'] < min_after_b:
                    min_after_b = klines[i]['low']
                    c_idx = i
            
            if c_idx is not None and min_after_b < b_point['price']:
                c_point = {'price': min_after_b, 'index': c_idx, 'timestamp': klines[c_idx]['timestamp']}
            else:
                # 使用当前价格作为C点
                c_point = {'price': current_price, 'index': len(klines) - 1, 'timestamp': klines[-1]['timestamp']}
        else:
            # 价格还在上涨或等于B点，C点 = B点（标准三点法）
            c_point = {'price': b_point['price'], 'index': b_idx, 'timestamp': b_point['timestamp']}
        
        return a_point, b_point, c_point
    except Exception as e:
        print(f"寻找摆动点失败: {e}", file=sys.stderr)
        return None, None, None


def calculate_fibonacci_extension(klines: List[Dict], current_price: float) -> Optional[Dict]:
    """计算斐波那契扩展位（两点法 - 参考图表画法）
    
    两点法（图表上的标准画法）：
    - 低点（0点）：整个上涨周期的最低点
    - 高点（100%/1点）：整个上涨周期的最高点（或当前价格，如果更高）
    - 扩展位计算：目标位 = 高点 + (高点 - 低点) × 倍数
    - 从高点直接延伸，不经过回调点
    """
    if not klines or len(klines) < 2:
        return None
    
    try:
        # 找到整个周期的最低点和最高点
        low = min([k['low'] for k in klines])
        high = max([k['high'] for k in klines], default=current_price)
        
        # 如果当前价格更高，使用当前价格作为高点
        if current_price > high:
            high = current_price
        
        # 计算价格差
        price_diff = high - low
        
        if price_diff <= 0:
            return None
        
        # 计算扩展位（从高点延伸）
        # 扩展位 = 高点 + (高点 - 低点) × 倍数
        fib_1618 = high + (price_diff * 0.618)
        fib_200 = high + (price_diff * 1.0)
        
        return {
            'a_point': low,  # 低点（0点）
            'b_point': high,  # 高点（100%/1点）
            'c_point': high,  # 两点法中C点等于B点（从高点延伸）
            'wave_amplitude': price_diff,  # 波段幅度 (高点 - 低点)
            'fib_1618': fib_1618,
            'fib_200': fib_200,
            'entry_zone_low': fib_1618 * 0.98,  # 允许±2%容差
            'entry_zone_high': fib_200 * 1.02,
            'method': 'two_point'  # 标记使用两点法
        }
    except Exception as e:
        print(f"计算斐波那契扩展位（两点法）失败: {e}", file=sys.stderr)
        return None


# ==================== 币种风险检查 ====================

def check_futures_support(symbol: str) -> Dict:
    """检查币种是否支持合约交易（做空）"""
    result = {
        'has_futures': False,
        'exchanges': [],
        'risk_level': 'unknown'
    }
    
    # 检查主要交易所的合约支持
    exchanges_to_check = ['binance', 'bybit', 'bitget', 'okx', 'gateio']
    
    for ex in exchanges_to_check:
        try:
            if ex == 'binance':
                # 检查Binance合约
                url = f"https://fapi.binance.com/fapi/v1/exchangeInfo"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    symbols = [s['symbol'] for s in data.get('symbols', [])]
                    if f"{symbol}USDT" in symbols:
                        result['has_futures'] = True
                        result['exchanges'].append('Binance')
            
            elif ex == 'bybit':
                # 检查Bybit合约
                url = "https://api.bybit.com/v5/market/instruments-info"
                params = {'category': 'linear', 'symbol': f'{symbol}USDT'}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('retCode') == 0 and data.get('result') and data['result'].get('list'):
                        if len(data['result']['list']) > 0:
                            result['has_futures'] = True
                            result['exchanges'].append('Bybit')
            
            elif ex == 'bitget':
                # 检查Bitget合约
                url = "https://api.bitget.com/api/mix/v1/market/contracts"
                params = {'productType': 'USDT-FUTURES'}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == '00000' and data.get('data'):
                        symbols = [s['symbolName'] for s in data['data']]
                        if f"{symbol}USDT" in symbols:
                            result['has_futures'] = True
                            result['exchanges'].append('Bitget')
            
            elif ex == 'okx':
                # 检查OKX合约
                url = "https://www.okx.com/api/v5/public/instruments"
                params = {'instType': 'SWAP', 'instId': f'{symbol}-USDT-SWAP'}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == '0' and data.get('data'):
                        if len(data['data']) > 0:
                            result['has_futures'] = True
                            result['exchanges'].append('OKX')
            
            elif ex == 'gateio':
                # 检查Gate.io合约
                url = "https://api.gateio.ws/api/v4/futures/usdt/contracts"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    symbols = [s['name'] for s in data if s.get('name', '').startswith(f'{symbol}_')]
                    if symbols:
                        result['has_futures'] = True
                        result['exchanges'].append('Gate.io')
            
            time.sleep(0.2)  # 避免请求过快
        except Exception as e:
            continue
    
    # 评估风险等级
    if result['has_futures']:
        if len(result['exchanges']) >= 3:
            result['risk_level'] = 'low'
        elif len(result['exchanges']) >= 2:
            result['risk_level'] = 'medium'
        else:
            result['risk_level'] = 'high'
    else:
        result['risk_level'] = 'very_high'  # 只有现货，无法做空
    
    return result


def check_exchange_listings(symbol: str) -> Dict:
    """检查币种在哪些交易所上市（评估控盘风险）"""
    result = {
        'exchanges': [],
        'exchange_count': 0,
        'major_exchanges': [],
        'risk_level': 'unknown'
    }
    
    # 使用CoinGecko API检查交易所列表
    try:
        # 先获取币种ID
        url = "https://api.coingecko.com/api/v3/search"
        params = {'query': symbol}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            coins = data.get('coins', [])
            if coins:
                coin_id = coins[0].get('id')
                if coin_id:
                    # 获取交易所列表
                    url2 = f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers"
                    response2 = requests.get(url2, timeout=10)
                    if response2.status_code == 200:
                        data2 = response2.json()
                        tickers = data2.get('tickers', [])
                        exchanges = set()
                        major_exchanges = ['binance', 'coinbase', 'kraken', 'bitfinex', 'huobi', 'okx', 'bybit', 'bitget', 'gate.io']
                        
                        for ticker in tickers:
                            market_name = ticker.get('market', {}).get('name', '').lower()
                            if market_name:
                                exchanges.add(market_name)
                                if any(major in market_name for major in major_exchanges):
                                    result['major_exchanges'].append(market_name)
                        
                        result['exchanges'] = sorted(list(exchanges))
                        result['exchange_count'] = len(exchanges)
                        
                        # 评估控盘风险
                        if result['exchange_count'] >= 10:
                            result['risk_level'] = 'low'
                        elif result['exchange_count'] >= 5:
                            result['risk_level'] = 'medium'
                        elif result['exchange_count'] >= 3:
                            result['risk_level'] = 'high'
                        else:
                            result['risk_level'] = 'very_high'  # 只有3个或更少交易所
    except Exception as e:
        print(f"检查{symbol}交易所列表失败: {e}", file=sys.stderr)
    
    return result


def check_delisting_history(symbol: str) -> Dict:
    """检查币种是否曾被下架（评估风险）"""
    result = {
        'was_delisted': False,
        'delisted_from': [],
        'risk_level': 'unknown'
    }
    
    # 使用CoinGecko API检查历史
    try:
        url = "https://api.coingecko.com/api/v3/search"
        params = {'query': symbol}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            coins = data.get('coins', [])
            if coins:
                coin_id = coins[0].get('id')
                if coin_id:
                    # 获取币种详情
                    url2 = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
                    response2 = requests.get(url2, timeout=10)
                    if response2.status_code == 200:
                        data2 = response2.json()
                        # 检查是否有下架历史（通过社区数据或描述）
                        description = data2.get('description', {}).get('en', '')
                        if 'delist' in description.lower() or 'removed' in description.lower():
                            result['was_delisted'] = True
                            result['risk_level'] = 'high'
                        
                        # 检查当前交易所数量
                        tickers_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/tickers"
                        tickers_response = requests.get(tickers_url, timeout=10)
                        if tickers_response.status_code == 200:
                            tickers_data = tickers_response.json()
                            current_exchanges = len(set([t.get('market', {}).get('name', '') for t in tickers_data.get('tickers', [])]))
                            
                            # 如果币种在主流交易所（如Binance）曾经存在但现在不在，可能被下架
                            # 这里需要更详细的检查，暂时标记为需要人工确认
                            if current_exchanges < 3:
                                result['risk_level'] = 'high'
    except Exception as e:
        print(f"检查{symbol}下架历史失败: {e}", file=sys.stderr)
    
    return result


# ==================== 策略筛选 ====================

def filter_short_opportunities(tickers: List[Dict], exchange: str) -> List[Dict]:
    """筛选做空机会：24小时涨幅 > 20%，并检查是否支持合约交易"""
    short_opportunities = []
    
    for ticker_data in tickers:
        normalized = normalize_ticker_data(ticker_data, exchange)
        if not normalized:
            continue
        
        change_24h = normalized['change_24h']
        
        # 做空条件：24小时涨幅 > 20%
        if change_24h > 20:
            symbol = normalized['symbol']
            
            # 检查是否支持合约交易
            futures_check = check_futures_support(symbol)
            normalized['futures_support'] = futures_check
            
            # 检查交易所列表
            exchange_check = check_exchange_listings(symbol)
            normalized['exchange_listings'] = exchange_check
            
            # 检查下架历史
            delisting_check = check_delisting_history(symbol)
            normalized['delisting_history'] = delisting_check
            
            # 只有支持合约交易的币种才加入做空列表
            if futures_check['has_futures']:
                short_opportunities.append(normalized)
            else:
                print(f"⚠️ {symbol} 只有现货，不支持做空，已过滤", file=sys.stderr)
            
            time.sleep(0.5)  # 避免API请求过快
    
    return short_opportunities


def filter_long_opportunities(tickers: List[Dict], exchange: str) -> List[Dict]:
    """筛选做多机会：24小时涨幅在8%-12%之间"""
    long_opportunities = []
    
    for ticker_data in tickers:
        normalized = normalize_ticker_data(ticker_data, exchange)
        if not normalized:
            continue
        
        change_24h = normalized['change_24h']
        
        # 做多条件：24小时涨幅在8%-12%之间
        if 8 <= change_24h <= 12:
            long_opportunities.append(normalized)
    
    return long_opportunities


# ==================== 交易计划生成 ====================

def generate_short_plan(coin: Dict, fib_data: Optional[Dict] = None) -> str:
    """生成做空交易计划"""
    symbol = coin['symbol']
    price = coin['price']
    change_24h = coin['change_24h']
    
    plan = []
    plan.append(f"### {symbol} 做空计划")
    plan.append("")
    plan.append(f"**当前价格**: ${price:.8f}")
    plan.append(f"**24小时涨幅**: {change_24h:.2f}%")
    
    # 添加合约支持信息
    futures_support = coin.get('futures_support', {})
    if futures_support:
        if futures_support.get('has_futures'):
            plan.append(f"**合约支持**: ✅ 支持（交易所: {', '.join(futures_support.get('exchanges', []))}）")
            risk_level = futures_support.get('risk_level', 'unknown')
            risk_text = {'low': '低', 'medium': '中', 'high': '高', 'very_high': '极高'}.get(risk_level, '未知')
            plan.append(f"**合约风险等级**: {risk_text}")
        else:
            plan.append("**合约支持**: ❌ 不支持（只有现货，无法做空）")
    
    # 添加交易所列表信息
    exchange_listings = coin.get('exchange_listings', {})
    if exchange_listings:
        exchange_count = exchange_listings.get('exchange_count', 0)
        major_exchanges = exchange_listings.get('major_exchanges', [])
        plan.append(f"**上市交易所数**: {exchange_count} 个")
        if major_exchanges:
            plan.append(f"**主流交易所**: {', '.join(major_exchanges[:5])}")  # 只显示前5个
        
        # 控盘风险提示
        risk_level = exchange_listings.get('risk_level', 'unknown')
        if risk_level == 'very_high':
            plan.append("⚠️ **控盘风险**: 极高（只有3个或更少交易所，控盘程度可能很高）")
        elif risk_level == 'high':
            plan.append("⚠️ **控盘风险**: 高（只有3-4个交易所）")
        elif risk_level == 'medium':
            plan.append("⚠️ **控盘风险**: 中（5-9个交易所）")
        else:
            plan.append("✅ **控盘风险**: 低（10个以上交易所）")
    
    # 添加下架历史信息
    delisting_history = coin.get('delisting_history', {})
    if delisting_history:
        was_delisted = delisting_history.get('was_delisted', False)
        if was_delisted:
            plan.append("⚠️ **下架历史**: 该币种曾被下架，风险较高")
            delisted_from = delisting_history.get('delisted_from', [])
            if delisted_from:
                plan.append(f"**曾被下架交易所**: {', '.join(delisted_from)}")
        else:
            risk_level = delisting_history.get('risk_level', 'unknown')
            if risk_level == 'high':
                plan.append("⚠️ **下架风险**: 高（交易所数量少，可能曾被下架）")
    
    if fib_data:
        method = fib_data.get('method', 'two_point')
        plan.append(f"**低点（0点）**: ${fib_data['a_point']:.8f}")
        plan.append(f"**高点（100%/1点）**: ${fib_data['b_point']:.8f}")
        plan.append(f"**波段幅度**: ${fib_data['wave_amplitude']:.8f}")
        plan.append(f"**计算方法**: {fib_data.get('method', 'two_point')}")
        plan.append(f"**1.618扩展位**: ${fib_data['fib_1618']:.8f}")
        plan.append(f"**2.0扩展位**: ${fib_data['fib_200']:.8f}")
        plan.append("")
        plan.append("**交易计划**:")
        plan.append(f"- **入场区间**: ${fib_data['entry_zone_low']:.8f} - ${fib_data['entry_zone_high']:.8f}")
        plan.append(f"- **止损价**: ${fib_data['entry_zone_high'] * 1.02:.8f} (入场价上方2%)")
        plan.append("- **止盈策略**: 分批止盈")
        plan.append("  - 第一档：50%收益率止盈30%仓位")
        plan.append("  - 第二档：100%收益率止盈30%仓位")
        plan.append("  - 第三档：200%收益率止盈剩余40%仓位")
        plan.append("- **持仓时间**: 第二天上午到下午2点，最迟下午2点平仓")
        plan.append("")
        plan.append("**注意**: 等待价格达到1.618-2.0扩展位区间后再做空，不是立即做空")
    else:
        plan.append("")
        plan.append("**交易计划**:")
        plan.append("- **入场条件**: 24小时涨幅 > 20% ✓")
        plan.append("- **需要**: 获取K线数据计算斐波那契扩展位")
        plan.append("- **止损**: 入场价上方1%-2%")
        plan.append("- **止盈**: 分批止盈（50%/100%/200%）")
    
    plan.append("")
    return "\n".join(plan)


def generate_long_plan(coin: Dict) -> str:
    """生成做多交易计划"""
    symbol = coin['symbol']
    price = coin['price']
    change_24h = coin['change_24h']
    high_24h = coin['high_24h']
    
    # 计算止损价（从高点下跌7%）
    # 注意：如果当前价格就是高点，或者高点无效，使用当前价格下跌7%
    if high_24h > 0 and high_24h >= price:
        stop_loss_price = high_24h * 0.93
    else:
        stop_loss_price = price * 0.93
    
    plan = []
    plan.append(f"### {symbol} 做多计划")
    plan.append("")
    plan.append(f"**当前价格**: ${price:.8f}")
    plan.append(f"**24小时涨幅**: {change_24h:.2f}%")
    plan.append(f"**24小时高点**: ${high_24h:.8f}")
    plan.append("")
    plan.append("**交易计划**:")
    plan.append(f"- **入场价**: ${price:.8f} (追涨入场)")
    plan.append(f"- **止损价**: ${stop_loss_price:.8f} (从高点下跌7%)")
    plan.append("- **止盈策略**: 分批止盈")
    plan.append("  - 涨幅达到20%开始分批止盈")
    plan.append("  - 20%-60%分批止盈")
    plan.append("  - 挂保本单")
    plan.append("- **持仓时间**: 不限定日内，根据市场情况决定")
    plan.append("")
    plan.append("**风险提示**: 假突破率高（70-80%），需要严格止损")
    plan.append("")
    
    return "\n".join(plan)


def generate_trading_plan_report(short_coins: List[Dict], long_coins: List[Dict], 
                                  exchange: str, scan_time: str) -> str:
    """生成完整的交易计划报告"""
    report = []
    report.append("# 梦多空策略 - 交易计划")
    report.append("")
    report.append(f"**生成时间**: {scan_time}")
    report.append(f"**数据来源**: {exchange}")
    report.append(f"**扫描币种数**: 前100个")
    report.append("")
    
    # 做空机会
    report.append("## 一、做空机会（24小时涨幅 > 20%）")
    report.append("")
    report.append(f"**符合条件的币种数**: {len(short_coins)}")
    report.append("")
    
    if short_coins:
        # 对做空币种计算斐波那契扩展位
        for coin in short_coins[:10]:  # 只处理前10个，避免API调用过多
            try:
                klines = get_daily_klines(coin['symbol'], coin['exchange'])
                fib_data = None
                if klines:
                    fib_data = calculate_fibonacci_extension(klines, coin['price'])
                
                plan = generate_short_plan(coin, fib_data)
                report.append(plan)
                report.append("---")
                report.append("")
                
                # 避免API调用过快
                time.sleep(0.5)
            except Exception as e:
                print(f"处理{coin['symbol']}失败: {e}", file=sys.stderr)
                # 即使计算失败，也生成基本计划
                plan = generate_short_plan(coin, None)
                report.append(plan)
                report.append("---")
                report.append("")
    else:
        report.append("暂无符合条件的做空机会")
        report.append("")
    
    # 做多机会
    report.append("## 二、做多机会（24小时涨幅 8%-12%）")
    report.append("")
    report.append(f"**符合条件的币种数**: {len(long_coins)}")
    report.append("")
    
    if long_coins:
        for coin in long_coins[:20]:  # 最多显示20个
            plan = generate_long_plan(coin)
            report.append(plan)
            report.append("---")
            report.append("")
    else:
        report.append("暂无符合条件的做多机会")
        report.append("")
    
    # 统计信息
    report.append("## 三、统计信息")
    report.append("")
    report.append(f"- **做空机会**: {len(short_coins)} 个")
    report.append(f"- **做多机会**: {len(long_coins)} 个")
    report.append("")
    report.append("**注意事项**:")
    report.append("1. 做空需要检查费率，费率超过1%/4小时不做")
    report.append("2. 做空需要等待价格达到1.618-2.0扩展位区间")
    report.append("3. 做多需要严格止损，假突破率70-80%")
    report.append("4. 大盘下杀5000点以上暂停交易")
    report.append("")
    report.append("**风险提示**:")
    report.append("1. ⚠️ 只有现货的币种已自动过滤，不会出现在做空列表中")
    report.append("2. ⚠️ 只有3个或更少交易所的币种控盘风险极高，需谨慎")
    report.append("3. ⚠️ 曾被主流交易所下架的币种风险较高，建议避免")
    report.append("4. ⚠️ 交易所数量少于5个的币种可能存在流动性风险")
    report.append("")
    
    return "\n".join(report)


# ==================== 主函数 ====================

def scan_and_generate_plan(exchange: str = 'auto', limit: int = 100):
    """扫描涨幅榜并生成交易计划"""
    print(f"开始扫描涨幅榜（交易所: {exchange}, 币种数: {limit}）...", file=sys.stderr)
    
    # 获取涨幅榜数据
    tickers, exchange_name = get_top_gainers(limit, exchange)
    
    if not tickers:
        print("无法获取涨幅榜数据", file=sys.stderr)
        return
    
    print(f"成功获取 {len(tickers)} 个币种数据（数据源: {exchange_name}）", file=sys.stderr)
    
    # 筛选做空和做多机会
    short_coins = filter_short_opportunities(tickers, exchange_name)
    long_coins = filter_long_opportunities(tickers, exchange_name)
    
    print(f"做空机会: {len(short_coins)} 个", file=sys.stderr)
    print(f"做多机会: {len(long_coins)} 个", file=sys.stderr)
    
    # 生成交易计划报告
    scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    report = generate_trading_plan_report(short_coins, long_coins, exchange_name, scan_time)
    
    # 保存报告（如果通过统一系统调用，会使用统一系统的输出目录）
    output_dir = Path.cwd()  # 使用当前工作目录，统一系统会设置
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"梦多空策略_交易计划_{timestamp}.md"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"交易计划已保存到: {output_file}", file=sys.stderr)
    
    return output_file


def run_periodic_scan(interval_hours: int = 2, exchange: str = 'auto', limit: int = 100):
    """周期性扫描（每N小时）"""
    print(f"开始周期性扫描（每{interval_hours}小时扫描一次）...", file=sys.stderr)
    print("按 Ctrl+C 停止", file=sys.stderr)
    
    interval_seconds = interval_hours * 3600
    
    try:
        while True:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"扫描时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            
            scan_and_generate_plan(exchange, limit)
            
            print(f"\n下次扫描将在 {interval_hours} 小时后进行...", file=sys.stderr)
            time.sleep(interval_seconds)
    
    except KeyboardInterrupt:
        print("\n扫描已停止", file=sys.stderr)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='梦多空策略 - 涨幅榜扫描和交易计划生成')
    parser.add_argument('--exchange', choices=['auto', 'bitget', 'bybit', 'binance'], 
                       default='auto', help='选择交易所（默认: auto）')
    parser.add_argument('--limit', type=int, default=100, help='扫描币种数（默认: 100）')
    parser.add_argument('--interval', type=int, default=2, 
                       help='周期性扫描间隔（小时，默认: 2，0表示只扫描一次）')
    
    args = parser.parse_args()
    
    if args.interval > 0:
        # 周期性扫描
        run_periodic_scan(args.interval, args.exchange, args.limit)
    else:
        # 只扫描一次
        scan_and_generate_plan(args.exchange, args.limit)


if __name__ == "__main__":
    main()

