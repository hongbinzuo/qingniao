#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
千叶交易系统 - 主系统
根据提取的规则生成BTC、黄金、白银的交易信号
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json
import requests

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


class ChibaTradingSystem:
    """千叶交易系统"""
    
    def __init__(self):
        self.rules_file = Path(__file__).parent.parent.parent / "data" / "chiba_videos" / "rules" / "chiba_trading_rules.json"
        self.rules = self._load_rules()
        
        # 支持的市场
        self.markets = {
            'BTC': {
                'symbol': 'BTCUSDT',
                'exchange': 'bybit',
                'name': '比特币',
                'base_currency': 'BTC',
                'quote_currency': 'USDT',
                'alternative_exchanges': ['binance', 'bitget', 'gateio']  # 备用交易所
            },
            'GOLD': {
                'symbol': 'XAUTUSDT',  # Bybit使用XAUTUSDT（黄金交易对）
                'exchange': 'bybit',
                'name': '黄金',
                'base_currency': 'XAUT',
                'quote_currency': 'USDT',
                'alternative_symbols': ['PAXGUSDT'],  # 备用符号（其他交易所可能用PAXG）
                'alternative_exchanges': ['binance', 'gateio']  # 备用交易所
            },
            'SILVER': {
                'symbol': 'XAG',  # 暂时保留，等待检查Bybit是否有白银交易对
                'exchange': 'bybit',
                'name': '白银',
                'base_currency': 'XAG',
                'quote_currency': 'USD',
                'alternative_exchanges': []  # 待检查
            }
        }
    
    def _load_rules(self) -> Dict:
        """加载交易规则"""
        if self.rules_file.exists():
            try:
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('rules', {})
            except:
                pass
        
        # 默认规则（待从视频中提取）
        return {
            'entry_conditions': [],
            'stop_loss_rules': [],
            'take_profit_rules': [],
            'risk_management': [],
            'indicators': [],
            'patterns': []
        }
    
    def get_market_data(self, market: str, timeframe: str = '15m', limit: int = 200) -> Optional[List]:
        """获取市场数据"""
        market_info = self.markets.get(market)
        if not market_info:
            return None
        
        symbol = market_info['symbol']
        exchange = market_info['exchange']
        
        try:
            if exchange == 'bybit':
                return self._get_bybit_data(market_info, timeframe, limit)
            elif exchange == 'gateio':
                # 转换时间框架
                tf_map = {
                    '5m': '5m',
                    '15m': '15m',
                    '1h': '1h',
                    '4h': '4h',
                    '1d': '1d'
                }
                interval = tf_map.get(timeframe, '15m')
                
                url = "https://api.gateio.ws/api/v4/spot/candlesticks"
                
                # 尝试多个符号（如果主符号失败）
                symbols_to_try = [symbol]
                if 'alternative_symbols' in market_info:
                    symbols_to_try.extend(market_info['alternative_symbols'])
                
                for try_symbol in symbols_to_try:
                    params = {
                        'currency_pair': try_symbol,
                        'interval': interval,
                        'limit': limit
                    }
                    
                    try:
                        response = requests.get(url, params=params, timeout=15)
                        if response.status_code == 200:
                            data = response.json()
                            if data and len(data) > 0:
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
                                # 更新使用的符号
                                if try_symbol != symbol:
                                    market_info['symbol'] = try_symbol
                                return klines
                    except:
                        continue
        except Exception as e:
            print(f"获取{market_info['name']}数据失败: {e}", file=sys.stderr)
        
        return None
    
    def _get_bybit_data(self, market_info: Dict, timeframe: str, limit: int) -> Optional[List]:
        """从Bybit获取K线数据"""
        symbol = market_info['symbol']
        tf_map = {
            '5m': '5',
            '15m': '15',
            '1h': '60',
            '4h': '240',
            '1d': 'D'
        }
        interval = tf_map.get(timeframe, '15')
        
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': 'spot',
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0 and data.get('result'):
                    klines_data = data['result'].get('list', [])
                    if klines_data:
                        klines = []
                        # Bybit返回的是倒序，需要反转
                        for k in reversed(klines_data):
                            klines.append({
                                'timestamp': int(k[0]),
                                'open': float(k[1]),
                                'high': float(k[2]),
                                'low': float(k[3]),
                                'close': float(k[4]),
                                'volume': float(k[5])
                            })
                        return klines
        except Exception as e:
            print(f"Bybit获取K线数据失败: {e}", file=sys.stderr)
        
        return None
    
    def get_current_price(self, market: str) -> Optional[float]:
        """获取当前价格"""
        market_info = self.markets.get(market)
        if not market_info:
            return None
        
        exchange = market_info['exchange']
        symbol = market_info['symbol']
        
        try:
            if exchange == 'bybit':
                # 使用Bybit ticker API获取实时价格
                url = "https://api.bybit.com/v5/market/tickers"
                params = {
                    'category': 'spot',
                    'symbol': symbol
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('retCode') == 0 and data.get('result'):
                        ticker_list = data['result'].get('list', [])
                        if ticker_list and len(ticker_list) > 0:
                            return float(ticker_list[0].get('lastPrice', 0))
            
            elif exchange == 'gateio':
                # 使用ticker API获取实时价格
                url = "https://api.gateio.ws/api/v4/spot/tickers"
                params = {'currency_pair': symbol}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return float(data[0].get('last', 0))
            
            elif exchange == 'binance':
                # 使用Binance ticker API
                trading_pair = symbol.replace('_', '')
                url = "https://api.binance.com/api/v3/ticker/price"
                params = {'symbol': trading_pair}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return float(data.get('price', 0))
            
            elif exchange == 'bitget':
                # 使用Bitget ticker API
                trading_pair = symbol.replace('_', '')
                url = "https://api.bitget.com/api/spot/v1/market/ticker"
                params = {'symbol': trading_pair}
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == '00000' and data.get('data'):
                        return float(data['data'].get('last', 0))
            
            elif exchange == 'metals_api':
                # 获取黄金/白银价格
                # 注意：免费API有限制，建议使用专业API服务
                metal_code = 'XAU' if market == 'GOLD' else 'XAG'
                
                # 方法1: 尝试从某些交易所获取（如果有贵金属交易对）
                # 某些交易所可能有XAU/USD或XAG/USD交易对
                try:
                    trading_pairs = {
                        'GOLD': ['XAUUSD', 'GOLDUSD', 'XAUUSDT'],
                        'SILVER': ['XAGUSD', 'SILVERUSD', 'XAGUSDT']
                    }
                    
                    for pair in trading_pairs.get(market, []):
                        try:
                            # 尝试Binance
                            url = "https://api.binance.com/api/v3/ticker/price"
                            params = {'symbol': pair}
                            response = requests.get(url, params=params, timeout=10)
                            if response.status_code == 200:
                                data = response.json()
                                if 'price' in data:
                                    price = float(data['price'])
                                    if price > 0:
                                        return price
                        except:
                            continue
                        
                        # 尝试Gate.io
                        try:
                            url = "https://api.gateio.ws/api/v4/spot/tickers"
                            params = {'currency_pair': pair}
                            response = requests.get(url, params=params, timeout=10)
                            if response.status_code == 200:
                                data = response.json()
                                if data and len(data) > 0:
                                    price = float(data[0].get('last', 0))
                                    if price > 0:
                                        return price
                        except:
                            continue
                except:
                    pass
                
                # 方法2: 使用免费的贵金属API（需要API key）
                # 例如：metals-api.com, goldapi.io等
                # 用户需要配置API key才能使用
                
                # 方法3: 使用网页爬取（不推荐，不稳定）
                # 暂时返回None，提示用户需要配置API或使用其他数据源
                print(f"⚠️ {market_info['name']}价格获取失败：请配置贵金属API key或使用支持贵金属交易的交易所", file=sys.stderr)
                return None
                
        except Exception as e:
            print(f"获取{market_info['name']}价格失败: {e}", file=sys.stderr)
        
        # 如果主交易所失败，尝试备用交易所
        if 'alternative_exchanges' in market_info:
            for alt_exchange in market_info['alternative_exchanges']:
                try:
                    if alt_exchange == 'bybit':
                        trading_pair = market_info['symbol']
                        url = "https://api.bybit.com/v5/market/tickers"
                        params = {
                            'category': 'spot',
                            'symbol': trading_pair
                        }
                        response = requests.get(url, params=params, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('retCode') == 0 and data.get('result'):
                                ticker_list = data['result'].get('list', [])
                                if ticker_list and len(ticker_list) > 0:
                                    return float(ticker_list[0].get('lastPrice', 0))
                    elif alt_exchange == 'binance':
                        trading_pair = market_info['symbol']
                        url = "https://api.binance.com/api/v3/ticker/price"
                        params = {'symbol': trading_pair}
                        response = requests.get(url, params=params, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            return float(data.get('price', 0))
                    elif alt_exchange == 'bitget':
                        trading_pair = market_info['symbol']
                        url = "https://api.bitget.com/api/spot/v1/market/ticker"
                        params = {'symbol': trading_pair}
                        response = requests.get(url, params=params, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('code') == '00000' and data.get('data'):
                                return float(data['data'].get('last', 0))
                    elif alt_exchange == 'gateio':
                        trading_pair = market_info['symbol'].replace('USDT', '_USDT')
                        url = "https://api.gateio.ws/api/v4/spot/tickers"
                        params = {'currency_pair': trading_pair}
                        response = requests.get(url, params=params, timeout=10)
                        if response.status_code == 200:
                            data = response.json()
                            if data and len(data) > 0:
                                return float(data[0].get('last', 0))
                except:
                    continue
        
        # 最后尝试从K线获取
        klines = self.get_market_data(market, timeframe='5m', limit=1)
        if klines:
            return klines[-1]['close']
        
        return None
    
    def generate_signals(self, markets: List[str] = None) -> Dict:
        """生成交易信号"""
        if markets is None:
            markets = ['BTC', 'GOLD', 'SILVER']
        
        print("=" * 80)
        print("千叶交易系统 - 交易信号生成")
        print("=" * 80)
        print()
        print(f"目标市场: {', '.join([self.markets[m]['name'] for m in markets])}")
        print()
        
        all_signals = {}
        
        for market in markets:
            market_name = self.markets[market]['name']
            print(f"分析 {market_name} ({market})...")
            
            # 获取市场数据（多时间框架）
            klines_1h = self.get_market_data(market, timeframe='1h')
            klines_4h = self.get_market_data(market, timeframe='4h')
            klines_1d = self.get_market_data(market, timeframe='1d')
            
            if not klines_1h:
                print(f"  ⚠️ 无法获取{market_name}数据")
                all_signals[market] = []
                continue
            
            # 获取当前价格
            current_price = klines_1h[-1]['close']
            print(f"  当前价格: ${current_price:,.2f}")
            
            # 生成信号（基于规则，使用多时间框架）
            signals = self._generate_market_signals(market, klines_1h, klines_4h, klines_1d, current_price)
            all_signals[market] = signals
            
            if signals:
                print(f"  ✓ 生成 {len(signals)} 个信号")
                for sig in signals:
                    print(f"    - {sig['direction']} @ {sig['entry']:.2f}")
            else:
                print(f"  - 暂无信号")
            print()
        
        return all_signals
    
    def _generate_market_signals(self, market: str, klines_1h: List[Dict], 
                                 klines_4h: List[Dict], klines_1d: List[Dict], 
                                 current_price: float) -> List[Dict]:
        """为特定市场生成信号（基于千叶交易系统规则，使用多时间框架）"""
        signals = []
        
        if not klines_1h or len(klines_1h) < 55:
            return signals
        
        # 计算技术指标（基于视频提取的规则）
        def calculate_sma(klines, period):
            if len(klines) < period:
                return None
            closes = [k['close'] for k in klines[-period:]]
            return sum(closes) / len(closes)
        
        def calculate_ema(klines, period):
            if len(klines) < period:
                return None
            multiplier = 2.0 / (period + 1)
            ema = klines[0]['close']
            for k in klines[1:]:
                ema = (k['close'] - ema) * multiplier + ema
            return ema
        
        # 根据市场使用不同的均线策略
        # 黄金：使用12/24/55均线（1小时和4小时级别）
        # BTC和白银：使用其他策略
        
        if market == 'GOLD':
            # 黄金：12/24/55均线系统
            ma_1h_12 = calculate_sma(klines_1h, 12) if len(klines_1h) >= 12 else None
            ma_1h_24 = calculate_sma(klines_1h, 24) if len(klines_1h) >= 24 else None
            ma_1h_55 = calculate_sma(klines_1h, 55) if len(klines_1h) >= 55 else None
            
            if not ma_1h_12 or not ma_1h_24 or not ma_1h_55:
                return signals
            
            # 4小时数据已在参数中传入
            if klines_4h and len(klines_4h) >= 24:
                ma_4h_24 = calculate_sma(klines_4h, 24)
            else:
                ma_4h_24 = None
            
            # 黄金趋势判断：价格在55均线之上为上升趋势
            is_uptrend = current_price > ma_1h_55
            is_downtrend = current_price < ma_1h_55
            
        elif market == 'BTC':
            # BTC：不使用固定均线，关注关键价位和突破
            ma_1h_20 = calculate_sma(klines_1h, 20) if len(klines_1h) >= 20 else None
            ma_1h_50 = calculate_sma(klines_1h, 50) if len(klines_1h) >= 50 else None
            
            if not ma_1h_20 or not ma_1h_50:
                return signals
            
            # BTC趋势判断：简单的均线判断
            is_uptrend = current_price > ma_1h_50 and ma_1h_20 > ma_1h_50
            is_downtrend = current_price < ma_1h_50 and ma_1h_20 < ma_1h_50
            
            ma_1h_12 = None
            ma_1h_24 = None
            ma_1h_55 = None
            ma_4h_24 = None
            
        elif market == 'SILVER':
            # 白银：可以使用类似黄金的策略，但参数可能不同
            # 或者使用其他技术分析方法
            ma_1h_20 = calculate_sma(klines_1h, 20) if len(klines_1h) >= 20 else None
            ma_1h_50 = calculate_sma(klines_1h, 50) if len(klines_1h) >= 50 else None
            
            if not ma_1h_20 or not ma_1h_50:
                return signals
            
            # 白银趋势判断
            is_uptrend = current_price > ma_1h_50 and ma_1h_20 > ma_1h_50
            is_downtrend = current_price < ma_1h_50 and ma_1h_20 < ma_1h_50
            
            ma_1h_12 = None
            ma_1h_24 = None
            ma_1h_55 = None
            ma_4h_24 = None
        else:
            return signals
        
        # 计算最近的高点和低点
        recent_high = max([k['high'] for k in klines_1h[-50:]])
        recent_low = min([k['low'] for k in klines_1h[-50:]])
        
        # 根据市场生成不同策略
        if market == 'BTC':
            # BTC策略：等待区间突破（使用日线判断关键价位）
            # 关键价位：9万、8万5、8万6.5
            # 根据视频：应该使用日线收盘来判断突破，而不是1小时
            btc_key_levels = {
                'upper': 90000,
                'lower': 85000,
                'lower_alt': 86500
            }
            
            # 使用日线数据判断关键价位突破（更准确）
            if klines_1d and len(klines_1d) > 0:
                latest_daily_close = klines_1d[-1]['close']
                latest_daily_high = klines_1d[-1]['high']
                latest_daily_low = klines_1d[-1]['low']
                
                # 检查是否突破9万（日线收盘确认）
                if latest_daily_close > btc_key_levels['upper']:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '1d',
                        'direction': 'long',
                        'entry': current_price,
                        'stop_loss': btc_key_levels['upper'] * 0.98,
                        'take_profit_1': btc_key_levels['upper'] * 1.05,
                        'take_profit_2': btc_key_levels['upper'] * 1.10,
                        'risk_reward_ratio': 2.0,
                        'strength': 'high',
                        'reason': '突破9万关键阻力位（日线收盘确认）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
                
                # 检查是否跌破8万5（日线收盘确认）
                elif latest_daily_close < btc_key_levels['lower']:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '1d',
                        'direction': 'short',
                        'entry': current_price,
                        'stop_loss': btc_key_levels['lower'] * 1.02,
                        'take_profit_1': btc_key_levels['lower'] * 0.95,
                        'take_profit_2': btc_key_levels['lower'] * 0.90,
                        'risk_reward_ratio': 2.0,
                        'strength': 'high',
                        'reason': '跌破8万5关键支撑位（日线收盘确认）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
                
                # 检查是否跌破8万6.5（备用支撑位）
                elif latest_daily_close < btc_key_levels['lower_alt']:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '1d',
                        'direction': 'short',
                        'entry': current_price,
                        'stop_loss': btc_key_levels['lower_alt'] * 1.02,
                        'take_profit_1': btc_key_levels['lower_alt'] * 0.95,
                        'take_profit_2': btc_key_levels['lower_alt'] * 0.90,
                        'risk_reward_ratio': 2.0,
                        'strength': 'medium',
                        'reason': '跌破8万6.5关键支撑位（日线收盘确认）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
            
            # 如果价格在区间内，等待突破信号
            if not signals:
                # 检查是否在均线附近回调
                if ma_1h_50:
                    price_to_ma_ratio = abs(current_price - ma_1h_50) / ma_1h_50
                    if price_to_ma_ratio < 0.01 and is_uptrend:  # 价格接近均线且在上升趋势
                        signal = {
                            'market': market,
                            'market_name': self.markets[market]['name'],
                            'timeframe': '1h',
                            'direction': 'long',
                            'entry': current_price,
                            'stop_loss': ma_1h_50 * 0.98,
                            'take_profit_1': current_price * 1.03,
                            'take_profit_2': current_price * 1.06,
                            'risk_reward_ratio': 1.5,
                            'strength': 'medium',
                            'reason': '回调至1小时50均线附近（趋势中）',
                            'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        signals.append(signal)
        
        elif market == 'GOLD':
            # 黄金策略：使用12/24/55均线系统
            # 规则：突破历史新高后的第一次回调是非常好的交易机会
            # 趋势中按均线执行操作
            
            # 检查是否在上升趋势中（价格在55均线之上）
            if is_uptrend:
                # 根据视频规则：优先使用4小时24均线
                # "接下来就是四小时的24所以这要是24能或许是下一次的这样的一个机会"
                # 如果4小时24均线错过了，再使用1小时12/24均线
                
                # 优先检查4小时24均线（更可靠）
                if ma_4h_24 and abs(current_price - ma_4h_24) / ma_4h_24 < 0.005:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '4h',
                        'direction': 'long',
                        'entry': current_price,
                        'stop_loss': ma_4h_24 * 0.995,
                        'take_profit_1': current_price * 1.03,
                        'take_profit_2': current_price * 1.06,
                        'risk_reward_ratio': 2.5,
                        'strength': 'high',
                        'reason': '回调至4小时24均线（趋势中，按均线执行，优先信号）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
                
                # 如果4小时24均线没有信号，再检查1小时均线
                # 1小时12均线
                elif ma_1h_12 and abs(current_price - ma_1h_12) / ma_1h_12 < 0.005:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '1h',
                        'direction': 'long',
                        'entry': current_price,
                        'stop_loss': ma_1h_12 * 0.995,
                        'take_profit_1': current_price * 1.02,
                        'take_profit_2': current_price * 1.04,
                        'risk_reward_ratio': 2.0,
                        'strength': 'high',
                        'reason': '回调至1小时12均线（趋势中，按均线执行）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
                
                # 1小时24均线
                elif ma_1h_24 and abs(current_price - ma_1h_24) / ma_1h_24 < 0.005:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '1h',
                        'direction': 'long',
                        'entry': current_price,
                        'stop_loss': ma_1h_24 * 0.995,
                        'take_profit_1': current_price * 1.02,
                        'take_profit_2': current_price * 1.04,
                        'risk_reward_ratio': 2.0,
                        'strength': 'high',
                        'reason': '回调至1小时24均线（趋势中，按均线执行）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
                
                # 检查是否突破新高后的第一次回调（高盈亏比机会）
                if recent_high > max([k['high'] for k in klines_1h[-200:-50]]):
                    # 最近创了新高
                    if current_price < recent_high * 0.98:  # 回调了2%以上
                        # 检查是否回调到55均线
                        if ma_1h_55 and abs(current_price - ma_1h_55) / ma_1h_55 < 0.01:
                            signal = {
                                'market': market,
                                'market_name': self.markets[market]['name'],
                                'timeframe': '1h',
                                'direction': 'long',
                                'entry': current_price,
                                'stop_loss': ma_1h_55 * 0.99,
                                'take_profit_1': recent_high * 1.01,
                                'take_profit_2': recent_high * 1.03,
                                'risk_reward_ratio': 3.0,
                                'strength': 'very_high',
                                'reason': '突破新高后第一次回调至55均线（高盈亏比机会）',
                                'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            }
                            signals.append(signal)
            
            # 如果均线走坏，趋势可能结束
            if is_downtrend and ma_1h_55:
                # 检查是否跌破关键均线
                if current_price < ma_1h_55 * 0.995:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '1h',
                        'direction': 'short',
                        'entry': current_price,
                        'stop_loss': ma_1h_55 * 1.005,
                        'take_profit_1': current_price * 0.98,
                        'take_profit_2': current_price * 0.96,
                        'risk_reward_ratio': 1.5,
                        'strength': 'medium',
                        'reason': '跌破55均线（趋势可能结束）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
        
        elif market == 'SILVER':
            # 白银策略：不使用12/24/55均线，使用其他技术分析方法
            # 根据视频，白银比黄金更强势，可以使用突破策略
            
            # 检查是否在上升趋势中
            if is_uptrend:
                # 白银可以使用简单的突破策略
                # 检查是否突破近期高点
                if current_price > recent_high * 0.99:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '1h',
                        'direction': 'long',
                        'entry': current_price,
                        'stop_loss': ma_1h_20 * 0.98 if ma_1h_20 else current_price * 0.98,
                        'take_profit_1': current_price * 1.03,
                        'take_profit_2': current_price * 1.06,
                        'risk_reward_ratio': 2.0,
                        'strength': 'medium',
                        'reason': '突破近期高点（白银强势品种）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
                
                # 回调到均线附近
                elif ma_1h_20 and abs(current_price - ma_1h_20) / ma_1h_20 < 0.01:
                    signal = {
                        'market': market,
                        'market_name': self.markets[market]['name'],
                        'timeframe': '1h',
                        'direction': 'long',
                        'entry': current_price,
                        'stop_loss': ma_1h_20 * 0.98,
                        'take_profit_1': current_price * 1.04,
                        'take_profit_2': current_price * 1.08,
                        'risk_reward_ratio': 2.0,
                        'strength': 'medium',
                        'reason': '回调至20均线（白银趋势中）',
                        'signal_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    signals.append(signal)
        
        return signals
    
    def save_signals(self, signals: Dict, output_path: Path = None):
        """保存信号"""
        if output_path is None:
            output_path = Path(__file__).parent.parent.parent / "trading_signals" / f"chiba_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成Markdown报告
        content = self._generate_signal_report(signals)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 信号已保存: {output_path}")
        return output_path
    
    def _generate_signal_report(self, signals: Dict) -> str:
        """生成信号报告"""
        lines = []
        lines.append("# 千叶交易系统 - 交易信号")
        lines.append("")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**系统**: 千叶交易系统")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        total_signals = sum(len(s) for s in signals.values())
        lines.append(f"**总信号数**: {total_signals}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        for market, market_signals in signals.items():
            market_name = self.markets[market]['name']
            current_price = self.get_current_price(market)
            
            lines.append(f"## {market_name} ({market})")
            lines.append("")
            
            if current_price:
                lines.append(f"**当前价格**: ${current_price:,.2f}")
                lines.append("")
            
            if not market_signals:
                lines.append("**状态**: 暂无信号")
                lines.append("")
                lines.append("建议：等待更好的交易机会")
                lines.append("")
            else:
                for i, signal in enumerate(market_signals, 1):
                    lines.append(f"### 信号 {i}: {signal['direction'].upper()} ({signal['strength']})")
                    lines.append("")
                    lines.append(f"**时间框架**: {signal['timeframe']}")
                    lines.append(f"**入场**: ${signal['entry']:,.2f}")
                    lines.append(f"**止损**: ${signal['stop_loss']:,.2f} ({abs((signal['stop_loss']-signal['entry'])/signal['entry']*100):.2f}%)")
                    lines.append(f"**第一止盈**: ${signal['take_profit_1']:,.2f} (50%仓位)")
                    lines.append(f"**第二止盈**: ${signal['take_profit_2']:,.2f} (50%仓位)")
                    lines.append(f"**盈亏比**: {signal['risk_reward_ratio']:.2f}:1")
                    lines.append(f"**信号原因**: {signal['reason']}")
                    lines.append(f"**信号时间**: {signal['signal_time']}")
                    lines.append("")
                    
                    # 计算风险收益
                    if signal['direction'] == 'long':
                        risk = signal['entry'] - signal['stop_loss']
                        reward_1 = signal['take_profit_1'] - signal['entry']
                        reward_2 = signal['take_profit_2'] - signal['entry']
                    else:
                        risk = signal['stop_loss'] - signal['entry']
                        reward_1 = signal['entry'] - signal['take_profit_1']
                        reward_2 = signal['entry'] - signal['take_profit_2']
                    
                    lines.append("**风险分析**:")
                    lines.append(f"- 风险: ${risk:,.2f} ({abs(risk/signal['entry']*100):.2f}%)")
                    lines.append(f"- 第一止盈收益: ${reward_1:,.2f} ({abs(reward_1/signal['entry']*100):.2f}%)")
                    lines.append(f"- 第二止盈收益: ${reward_2:,.2f} ({abs(reward_2/signal['entry']*100):.2f}%)")
                    lines.append("")
            
            lines.append("---")
            lines.append("")
        
        lines.append("## ⚠️ 风险提示")
        lines.append("")
        lines.append("1. 本信号基于千叶交易系统自动生成，仅供参考")
        lines.append("2. 交易有风险，入市需谨慎")
        lines.append("3. 请根据自身风险承受能力设置仓位")
        lines.append("4. 严格执行止损，控制风险")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"**免责声明**: 本交易信号基于千叶交易系统自动生成，仅供参考。交易有风险，入市需谨慎。")
        
        return "\n".join(lines)


def main():
    """主函数"""
    system = ChibaTradingSystem()
    
    # 生成信号
    signals = system.generate_signals(['BTC', 'GOLD', 'SILVER'])
    
    # 保存信号
    output_path = system.save_signals(signals)
    
    print()
    print("=" * 80)
    print("信号生成完成")
    print("=" * 80)
    print()
    print(f"报告已保存: {output_path}")
    print()
    
    # 打印摘要
    total_signals = sum(len(s) for s in signals.values())
    print(f"总信号数: {total_signals}")
    for market, market_signals in signals.items():
        if market_signals:
            print(f"  {system.markets[market]['name']}: {len(market_signals)} 个信号")

if __name__ == '__main__':
    main()

