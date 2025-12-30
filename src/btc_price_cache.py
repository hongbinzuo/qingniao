#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC价格历史缓存系统
避免每次请求网络API，提高处理速度
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict
import requests

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

CACHE_DIR = Path(__file__).parent.parent / "data" / "btc_price_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 缓存文件：按日期存储
def get_cache_file_path(date_str: str = None) -> Path:
    """获取缓存文件路径"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    return CACHE_DIR / f"btc_prices_{date_str}.json"

class BTCPriceCache:
    """BTC价格缓存管理器"""
    
    def __init__(self, trader_id='de'):
        self.trader_id = trader_id
        self.cache: Dict[str, float] = {}
        self.db_conn = None
        self.load_cache()
    
    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db_conn is None:
            try:
                import duckdb
                db_file = Path(__file__).parent / "data" / f"qingniao_{self.trader_id}.duckdb"
                if db_file.exists():
                    self.db_conn = duckdb.connect(str(db_file))
            except Exception as e:
                print(f"  数据库连接失败: {e}", file=sys.stderr)
        return self.db_conn
    
    def _get_timeseries_connection(self):
        """获取时序库连接"""
        if not hasattr(self, '_ts_conn') or self._ts_conn is None:
            try:
                import duckdb
                ts_file = Path(__file__).parent / "data" / "btc_price_timeseries.duckdb"
                if ts_file.exists():
                    self._ts_conn = duckdb.connect(str(ts_file))
            except Exception as e:
                print(f"  时序库连接失败: {e}", file=sys.stderr)
        return getattr(self, '_ts_conn', None)
    
    def load_cache(self):
        """加载所有缓存（从文件和数据库）"""
        # 1. 从文件加载
        cache_files = sorted(CACHE_DIR.glob("btc_prices_*.json"))
        for cache_file in cache_files:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.cache.update(data)
            except Exception as e:
                print(f"  加载缓存文件失败 {cache_file.name}: {e}", file=sys.stderr)
        
        # 2. 从时序库加载（优先）
        ts_conn = self._get_timeseries_connection()
        if ts_conn:
            try:
                # 从5分钟K线表加载（最精确）
                result = ts_conn.execute('''
                    SELECT timestamp, close 
                    FROM btc_price_5m
                    ORDER BY timestamp DESC
                ''').fetchall()
                loaded_count = 0
                for timestamp, price in result:
                    if timestamp and price:
                        # timestamp已经是Unix时间戳（秒）
                        five_min_ts = (int(timestamp) // 300) * 300  # 对齐到5分钟
                        self.cache[str(five_min_ts)] = float(price)
                        loaded_count += 1
                
                print(f"  从时序库加载了 {loaded_count} 条价格记录（5分钟K线）")
            except Exception as e:
                print(f"  从时序库加载价格失败: {e}", file=sys.stderr)
        
        # 3. 从业务数据库加载（作为补充）
        conn = self._get_db_connection()
        if conn:
            try:
                # 从conversations表加载
                result = conn.execute('''
                    SELECT timestamp, btc_price 
                    FROM conversations 
                    WHERE btc_price IS NOT NULL
                ''').fetchall()
                for timestamp, price in result:
                    if timestamp and price:
                        unix_ts = self._normalize_timestamp(timestamp)
                        if unix_ts:
                            minute_ts = (unix_ts // 60) * 60
                            self.cache[str(minute_ts)] = float(price)
                
                # 从trader_viewpoints表加载
                result = conn.execute('''
                    SELECT timestamp, btc_price 
                    FROM trader_viewpoints 
                    WHERE btc_price IS NOT NULL
                ''').fetchall()
                for timestamp, price in result:
                    if timestamp and price:
                        unix_ts = self._normalize_timestamp(timestamp)
                        if unix_ts:
                            minute_ts = (unix_ts // 60) * 60
                            self.cache[str(minute_ts)] = float(price)
            except Exception as e:
                print(f"  从业务数据库加载价格失败: {e}", file=sys.stderr)
        
        print(f"  已加载 {len(self.cache)} 条BTC价格缓存记录（文件+时序库+数据库）")
    
    def get_price(self, timestamp_str: str) -> Optional[float]:
        """
        从缓存获取价格（优先从时序库查询）
        
        Args:
            timestamp_str: 时间戳字符串（ISO格式或Unix时间戳）
        
        Returns:
            BTC价格，如果缓存中没有则返回None
        """
        # 标准化时间戳为Unix时间戳（秒）
        unix_ts = self._normalize_timestamp(timestamp_str)
        if unix_ts is None:
            return None
        
        # 1. 先尝试从内存缓存获取
        # 尝试精确匹配
        if str(unix_ts) in self.cache:
            return self.cache[str(unix_ts)]
        
        # 尝试匹配到分钟级别（向下取整到分钟）
        minute_ts = (unix_ts // 60) * 60
        if str(minute_ts) in self.cache:
            return self.cache[str(minute_ts)]
        
        # 尝试匹配到5分钟级别
        five_min_ts = (unix_ts // 300) * 300
        if str(five_min_ts) in self.cache:
            return self.cache[str(five_min_ts)]
        
        # 2. 如果内存缓存没有，尝试从时序库直接查询
        ts_conn = self._get_timeseries_connection()
        if ts_conn:
            try:
                # 查询5分钟K线（最接近的时间）
                result = ts_conn.execute('''
                    SELECT close 
                    FROM btc_price_5m
                    WHERE timestamp <= ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                ''', [unix_ts]).fetchone()
                
                if result and result[0]:
                    price = float(result[0])
                    # 缓存到内存
                    self.cache[str(five_min_ts)] = price
                    return price
            except Exception as e:
                pass  # 静默失败，继续其他方法
        
        return None
    
    def set_price(self, timestamp_str: str, price: float):
        """设置价格到缓存"""
        unix_ts = self._normalize_timestamp(timestamp_str)
        if unix_ts is None:
            return
        
        # 存储到分钟级别
        minute_ts = (unix_ts // 60) * 60
        self.cache[str(minute_ts)] = price
    
    def save_cache(self, date_str: str = None):
        """保存缓存到文件"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        cache_file = get_cache_file_path(date_str)
        
        # 按日期分组保存
        date_cache = {}
        for ts_str, price in self.cache.items():
            try:
                ts = int(ts_str)
                dt = datetime.fromtimestamp(ts)
                file_date = dt.strftime('%Y%m%d')
                if file_date == date_str:
                    date_cache[ts_str] = price
            except:
                continue
        
        if date_cache:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(date_cache, f, indent=2)
    
    def _normalize_timestamp(self, timestamp_str: str) -> Optional[int]:
        """标准化时间戳为Unix时间戳（秒）"""
        try:
            # 尝试ISO格式
            if isinstance(timestamp_str, str):
                # 处理ISO格式: 2025-10-18T00:15:42.698+08:00
                if 'T' in timestamp_str:
                    dt_str = timestamp_str.replace('+08:00', '').split('.')[0]
                    try:
                        dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')
                        # 假设是北京时间（UTC+8）
                        dt = dt - timedelta(hours=8)
                        return int(dt.timestamp())
                    except:
                        pass
                
                # 尝试其他格式
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y/%m/%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y/%m/%d %H:%M'
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(timestamp_str, fmt)
                        return int(dt.timestamp())
                    except:
                        continue
                
                # 尝试Unix时间戳
                try:
                    ts = float(timestamp_str)
                    if ts > 1e10:  # 毫秒
                        return int(ts / 1000)
                    else:  # 秒
                        return int(ts)
                except:
                    pass
            
            elif isinstance(timestamp_str, (int, float)):
                if timestamp_str > 1e10:  # 毫秒
                    return int(timestamp_str / 1000)
                else:  # 秒
                    return int(timestamp_str)
            
            return None
        except Exception as e:
            print(f"  时间戳标准化失败: {e}", file=sys.stderr)
            return None
    
    def get_price_with_fallback(self, timestamp_str: str, use_api: bool = True) -> Optional[float]:
        """
        获取价格，优先使用缓存，如果缓存没有且use_api=True则请求API
        
        Args:
            timestamp_str: 时间戳字符串
            use_api: 如果缓存中没有，是否请求API
        
        Returns:
            BTC价格
        """
        # 先尝试从缓存获取
        price = self.get_price(timestamp_str)
        if price is not None:
            return price
        
        # 如果缓存没有且允许使用API，则请求API
        if use_api:
            price = self._fetch_price_from_api(timestamp_str)
            if price is not None:
                # 保存到缓存
                self.set_price(timestamp_str, price)
                return price
        
        return None
    
    def _fetch_price_from_api(self, timestamp_str: str) -> Optional[float]:
        """从API获取价格"""
        try:
            unix_ts = self._normalize_timestamp(timestamp_str)
            if unix_ts is None:
                return None
            
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
            print(f"  API请求失败: {e}", file=sys.stderr)
            return None

# 全局缓存实例
_global_cache: Optional[BTCPriceCache] = None

def get_price_cache() -> BTCPriceCache:
    """获取全局缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = BTCPriceCache()
    return _global_cache

def get_btc_price_cached(timestamp_str: str, use_api: bool = False) -> Optional[float]:
    """
    获取BTC价格（优先使用缓存）
    
    Args:
        timestamp_str: 时间戳字符串
        use_api: 如果缓存中没有，是否请求API（默认False，只使用缓存）
    
    Returns:
        BTC价格
    """
    cache = get_price_cache()
    return cache.get_price_with_fallback(timestamp_str, use_api=use_api)

if __name__ == '__main__':
    # 测试
    cache = BTCPriceCache()
    test_ts = "2025-10-18T00:15:42.698+08:00"
    price = cache.get_price_with_fallback(test_ts, use_api=True)
    print(f"测试时间: {test_ts}")
    print(f"BTC价格: ${price:,.2f}" if price else "未找到价格")

