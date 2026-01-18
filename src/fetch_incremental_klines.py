#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增量获取K线数据
如果数据库中的数据不够新，调用Go程序获取增量数据
"""
from __future__ import annotations
import subprocess
import time
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from src.kline_db import get_latest_timestamp

ROOT = Path(__file__).resolve().parent.parent
GO_FETCHER = ROOT / 'scripts' / 'abu_kline_fetcher_simple.exe'


def ensure_fresh_klines(symbol: str, timeframe: str, days: int = 90, 
                        exchange: str = 'gate', max_age_minutes: int = 30) -> bool:
    """
    确保K线数据足够新，如果不够新则增量获取
    
    Args:
        symbol: 币种
        timeframe: 时间框架（如'15m'）
        days: 需要的天数
        exchange: 交易所
        max_age_minutes: 最大允许的年龄（分钟），超过此时间则需要更新
    
    Returns:
        是否成功（数据足够新或成功获取增量数据）
    """
    # 检查Go程序是否存在
    if not GO_FETCHER.exists():
        print(f"Warning: Go fetcher not found: {GO_FETCHER}", file=__import__('sys').stderr)
        return False
    
    # 获取数据库中最新的时间戳
    latest_ts = get_latest_timestamp(symbol, timeframe, exchange)
    now = int(time.time())
    
    # 如果数据库中没有数据，需要全量获取
    if latest_ts is None:
        print(f"[增量获取] {symbol} {timeframe}: 数据库中没有数据，全量获取...")
        return fetch_klines(symbol, timeframe, days, exchange)
    
    # 计算时间差（秒）
    age_seconds = now - latest_ts
    
    # 根据时间框架计算最大年龄
    timeframe_minutes_map = {
        '5m': 5,
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    }
    timeframe_minutes = timeframe_minutes_map.get(timeframe, 15)
    
    # 如果数据足够新（距离当前时间小于最大年龄），不需要更新
    if age_seconds < max_age_minutes * 60:
        return True
    
    # 需要增量获取
    print(f"[增量获取] {symbol} {timeframe}: 数据已过期（{age_seconds//60}分钟前），增量获取...")
    
    # 计算需要获取的天数（从最新时间戳到现在）
    age_days = max(1, (age_seconds // 86400) + 1)  # 至少1天
    
    # 调用Go程序获取增量数据
    return fetch_klines(symbol, timeframe, age_days, exchange, from_ts=latest_ts + 1)


def fetch_klines(symbol: str, timeframe: str, days: int, 
                 exchange: str = 'gate', from_ts: Optional[int] = None) -> bool:
    """
    调用Go程序获取K线数据
    
    Args:
        symbol: 币种
        timeframe: 时间框架
        days: 天数
        exchange: 交易所
        from_ts: 起始时间戳（如果提供，则从此时间戳开始获取）
    
    Returns:
        是否成功
    """
    try:
        # 构建输出文件名
        output_file = ROOT / 'data' / 'kline_data' / f'temp_{symbol}_{timeframe}_{int(time.time())}.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 构建Go程序命令
        cmd = [
            str(GO_FETCHER),
            '--symbols', symbol,
            '--timeframe', timeframe,
            '--days', str(days),
            '--output', str(output_file),
            '--concurrency', '1'
        ]
        
        if from_ts:
            cmd.extend(['--from', str(from_ts)])
        
        # 调用Go程序
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode != 0:
            print(f"Error fetching klines: {result.stderr}", file=__import__('sys').stderr)
            return False
        
        # 导入JSON到数据库
        try:
            # 动态导入，避免循环依赖
            import sys
            scripts_path = ROOT / 'scripts'
            if str(scripts_path) not in sys.path:
                sys.path.insert(0, str(scripts_path))
            from import_klines_json import import_json_file
            import_result = import_json_file(output_file, exchange)
            
            # 清理临时文件
            if output_file.exists():
                output_file.unlink()
            
            if import_result.get('success', 0) > 0:
                print(f"[增量获取] {symbol} {timeframe}: 成功获取 {import_result.get('inserted', 0)} 根K线")
                return True
            else:
                return False
        except Exception as e:
            print(f"Error importing klines: {e}", file=__import__('sys').stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print(f"Error: Go fetcher timeout for {symbol} {timeframe}", file=__import__('sys').stderr)
        return False
    except Exception as e:
        print(f"Error calling Go fetcher: {e}", file=__import__('sys').stderr)
        return False

