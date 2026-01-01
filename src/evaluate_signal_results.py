#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估交易信号结果
对照历史价格数据，评估信号的实际表现
"""

import requests
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

# 导入缓存系统
try:
    from src.signal_evaluation_cache import (
        save_evaluation_cache,
        get_cached_evaluation,
        load_evaluation_cache
    )
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    print("⚠️ 缓存系统不可用，将每次都重新计算", file=sys.stderr)

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def get_btc_kline_gateio(timeframe='5m', limit=200, from_timestamp=None, to_timestamp=None):
    """
    从Gate.io获取BTC K线数据
    
    Args:
        timeframe: 时间框架
        limit: 获取的K线数量
        from_timestamp: 起始时间戳（秒），如果提供，会获取从该时间开始的数据
        to_timestamp: 结束时间戳（秒），如果提供，会获取到该时间的数据
    """
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h'}
        interval = tf_map.get(timeframe, '5m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': interval,
            'limit': limit
        }
        
        # 如果提供了起始时间戳，添加到参数中
        if from_timestamp:
            params['from'] = from_timestamp
        
        # 如果提供了结束时间戳，添加到参数中
        if to_timestamp:
            params['to'] = to_timestamp
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
                klines = []
                for k in data:
                    # Gate.io返回的时间戳是秒，需要转换为毫秒
                    ts = int(k[0])
                    # 如果时间戳小于1e10，说明是秒，需要乘以1000
                    if ts < 1e10:
                        ts = ts * 1000
                    klines.append({
                        'timestamp': ts,
                        'open': float(k[5]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'close': float(k[2]),
                        'volume': float(k[1])
                    })
                return klines
    except Exception as e:
        print(f"Gate.io获取失败: {e}", file=sys.stderr)
    return None

def get_btc_current_price():
    """获取BTC当前价格"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': 'BTC_USDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data:
                return float(data[0].get('last', 0))
    except:
        pass
    return None

def evaluate_signal(signal: Dict, klines: List[Dict], signal_time: datetime) -> Dict:
    """
    评估单个信号的结果（考虑保本止损逻辑）
    
    保本止损逻辑：
    - 当触及第一止盈位后，止损位移动到入场价（保本）
    - 如果之后触及保本止损，状态为"部分止盈"而不是"止损"
    
    Args:
        signal: 信号字典，包含 entry, stop_loss, take_profit_1, take_profit_2, type
        klines: K线数据列表
        signal_time: 信号生成时间
    
    Returns:
        评估结果字典
    """
    entry = signal['entry']
    initial_stop_loss = signal['stop_loss']
    take_profit_1 = signal.get('take_profit_1')
    take_profit_2 = signal.get('take_profit_2')
    signal_type = signal['type']  # 'long' or 'short'
    
    # 找到信号时间对应的K线索引
    signal_timestamp = int(signal_time.timestamp() * 1000)
    start_idx = 0
    for i, k in enumerate(klines):
        if k['timestamp'] >= signal_timestamp:
            start_idx = i
            break
    
    # 评估结果
    result = {
        'signal_time': signal_time.strftime('%Y-%m-%d %H:%M:%S'),
        'entry': entry,
        'stop_loss': initial_stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'type': signal_type,
        'status': 'unknown',
        'outcome': None,
        'max_profit': 0,
        'max_loss': 0,
        'reached_tp1': False,
        'reached_tp2': False,
        'hit_stop_loss': False,
        'hit_breakeven_stop': False,
        'current_price': None,
        'current_pnl_pct': 0,
        'details': [],
        'timeline': []  # 详细时间线
    }
    
    # 保本止损逻辑：当触及TP1后，止损移动到入场价
    current_stop_loss = initial_stop_loss
    tp1_hit_time = None
    tp2_hit_time = None
    stop_hit_time = None
    entry_reached = False
    entry_reached_time = None
    invalid_signal = False  # 标记信号是否无效（入场价未到但先到止盈1）
    
    if signal_type == 'long':
        # 做多信号：检查是否触及止损、止盈
        for i in range(start_idx, len(klines)):
            k = klines[i]
            k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
            low = k['low']
            high = k['high']
            
            # 检查是否到达入场价（允许±0.1%的容差）
            if not entry_reached and low <= entry * 1.001:
                entry_reached = True
                entry_reached_time = k_time
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 到达入场价 ${entry:,.2f} (价格: ${low:,.2f})")
                result['timeline'].append({
                    'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event': '到达入场价',
                    'price': low,
                    'target_price': entry
                })
            
            # 检查止盈1（优先检查，因为触及后要移动止损）
            # 重要规则：如果入场价未到但先到达止盈1，信号无效
            if take_profit_1 and not result['reached_tp1'] and high >= take_profit_1:
                # 检查是否先到达入场价
                if not entry_reached:
                    # 入场价未到但先到达止盈1，信号无效
                    invalid_signal = True
                    result['status'] = 'invalid'
                    result['outcome'] = 'invalid'
                    result['details'].append(f"❌ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 信号无效：入场价未到但先到达止盈1 ${take_profit_1:,.2f} (价格: ${high:,.2f})")
                    result['timeline'].append({
                        'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'event': '信号无效（入场价未到但先到止盈1）',
                        'price': high,
                        'target_price': take_profit_1
                    })
                    break
                result['reached_tp1'] = True
                tp1_hit_time = k_time
                profit_pct = ((take_profit_1 - entry) / entry) * 100
                if profit_pct > result['max_profit']:
                    result['max_profit'] = profit_pct
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及止盈1 ${take_profit_1:,.2f} (价格: ${high:,.2f})")
                result['timeline'].append({
                    'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event': '触及止盈1',
                    'price': high,
                    'target_price': take_profit_1
                })
                # 移动止损到入场价（保本）
                current_stop_loss = entry
                result['details'].append(f"📌 止损已移动到保本位 ${entry:,.2f}")
            
            # 检查止盈2
            if take_profit_2 and not result['reached_tp2'] and high >= take_profit_2:
                result['reached_tp2'] = True
                tp2_hit_time = k_time
                profit_pct = ((take_profit_2 - entry) / entry) * 100
                if profit_pct > result['max_profit']:
                    result['max_profit'] = profit_pct
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及止盈2 ${take_profit_2:,.2f} (价格: ${high:,.2f})")
                result['timeline'].append({
                    'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event': '触及止盈2',
                    'price': high,
                    'target_price': take_profit_2
                })
                result['status'] = 'full_tp'
                result['outcome'] = 'full_tp'
                break
            
            # 检查止损（使用当前止损位，可能是初始止损或保本止损）
            if low <= current_stop_loss:
                result['hit_stop_loss'] = True
                stop_hit_time = k_time
                loss_pct = ((current_stop_loss - entry) / entry) * 100
                if loss_pct < result['max_loss']:
                    result['max_loss'] = loss_pct
                
                if current_stop_loss == entry:
                    # 保本止损
                    result['hit_breakeven_stop'] = True
                    result['status'] = 'partial_tp'
                    result['outcome'] = 'partial_tp'
                    result['details'].append(f"⚠️ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及保本止损 ${entry:,.2f} (价格: ${low:,.2f}) - 部分止盈")
                else:
                    # 初始止损
                    result['status'] = 'stopped'
                    result['outcome'] = 'stopped'
                    result['details'].append(f"❌ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及初始止损 ${initial_stop_loss:,.2f} (价格: ${low:,.2f})")
                
                result['timeline'].append({
                    'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event': '触及止损' if current_stop_loss != entry else '触及保本止损',
                    'price': low,
                    'target_price': current_stop_loss
                })
                break
            
            # 计算最大浮盈
            profit_pct = ((high - entry) / entry) * 100
            if profit_pct > result['max_profit']:
                result['max_profit'] = profit_pct
            
            # 计算最大浮亏
            loss_pct = ((low - entry) / entry) * 100
            if loss_pct < result['max_loss']:
                result['max_loss'] = loss_pct
    
    elif signal_type == 'short':
        # 做空信号：检查是否触及止损、止盈
        for i in range(start_idx, len(klines)):
            k = klines[i]
            k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
            low = k['low']
            high = k['high']
            
            # 检查止盈1（优先检查，因为需要验证入场价规则）
            # 重要规则：如果入场价未到但先到达止盈1，信号无效
            if take_profit_1 and not result['reached_tp1'] and low <= take_profit_1:
                # 对于做空：止盈1应该低于入场价，如果先到达止盈1，说明入场价未到
                if not entry_reached:
                    # 入场价未到但先到达止盈1，信号无效
                    invalid_signal = True
                    result['status'] = 'invalid'
                    result['outcome'] = 'invalid'
                    result['details'].append(f"❌ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 信号无效：入场价未到但先到达止盈1 ${take_profit_1:,.2f} (价格: ${low:,.2f})")
                    result['timeline'].append({
                        'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'event': '信号无效（入场价未到但先到止盈1）',
                        'price': low,
                        'target_price': take_profit_1
                    })
                    break
                
                # 正常触及止盈1
                result['reached_tp1'] = True
                tp1_hit_time = k_time
                profit_pct = ((entry - take_profit_1) / entry) * 100
                if profit_pct > result['max_profit']:
                    result['max_profit'] = profit_pct
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及止盈1 ${take_profit_1:,.2f} (价格: ${low:,.2f})")
                result['timeline'].append({
                    'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event': '触及止盈1',
                    'price': low,
                    'target_price': take_profit_1
                })
                # 移动止损到入场价（保本）
                current_stop_loss = entry
                result['details'].append(f"📌 止损已移动到保本位 ${entry:,.2f}")
            
            # 检查是否到达入场价（允许±0.1%的容差）
            # 注意：对于做空，如果价格从高位下跌，会先到达入场价
            if not entry_reached and high >= entry * 0.999:
                entry_reached = True
                entry_reached_time = k_time
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 到达入场价 ${entry:,.2f} (价格: ${high:,.2f})")
                result['timeline'].append({
                    'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event': '到达入场价',
                    'price': high,
                    'target_price': entry
                })
            
            # 检查止盈2（只有在已触及止盈1的情况下才检查）
            if result['reached_tp1'] and take_profit_2 and not result['reached_tp2'] and low <= take_profit_2:
                result['reached_tp2'] = True
                tp2_hit_time = k_time
                profit_pct = ((entry - take_profit_2) / entry) * 100
                if profit_pct > result['max_profit']:
                    result['max_profit'] = profit_pct
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及止盈2 ${take_profit_2:,.2f} (价格: ${low:,.2f})")
                result['timeline'].append({
                    'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event': '触及止盈2',
                    'price': low,
                    'target_price': take_profit_2
                })
                result['status'] = 'full_tp'
                result['outcome'] = 'full_tp'
                break
            
            # 检查止损（使用当前止损位，可能是初始止损或保本止损）
            if high >= current_stop_loss:
                result['hit_stop_loss'] = True
                stop_hit_time = k_time
                loss_pct = ((entry - current_stop_loss) / entry) * 100
                if loss_pct < result['max_loss']:
                    result['max_loss'] = loss_pct
                
                if current_stop_loss == entry:
                    # 保本止损
                    result['hit_breakeven_stop'] = True
                    result['status'] = 'partial_tp'
                    result['outcome'] = 'partial_tp'
                    result['details'].append(f"⚠️ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及保本止损 ${entry:,.2f} (价格: ${high:,.2f}) - 部分止盈")
                else:
                    # 初始止损
                    result['status'] = 'stopped'
                    result['outcome'] = 'stopped'
                    result['details'].append(f"❌ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及初始止损 ${initial_stop_loss:,.2f} (价格: ${high:,.2f})")
                
                result['timeline'].append({
                    'time': k_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'event': '触及止损' if current_stop_loss != entry else '触及保本止损',
                    'price': high,
                    'target_price': current_stop_loss
                })
                break
            
            # 计算最大浮盈
            profit_pct = ((entry - low) / entry) * 100
            if profit_pct > result['max_profit']:
                result['max_profit'] = profit_pct
            
            # 计算最大浮亏
            loss_pct = ((entry - high) / entry) * 100
            if loss_pct < result['max_loss']:
                result['max_loss'] = loss_pct
    
    # 如果既没有止损也没有止盈，标记为持仓中
    if result['status'] == 'unknown':
        if result['reached_tp1']:
            result['status'] = 'partial_tp'
            result['outcome'] = 'partial_tp'
        else:
            result['status'] = 'open'
            result['outcome'] = 'open'
    
    # 获取当前价格和盈亏
    if klines:
        current_price = klines[-1]['close']
        result['current_price'] = current_price
        if signal_type == 'long':
            result['current_pnl_pct'] = ((current_price - entry) / entry) * 100
        else:
            result['current_pnl_pct'] = ((entry - current_price) / entry) * 100
    
    # 添加时间摘要
    result['time_summary'] = {
        'entry_time': entry_reached_time.strftime('%Y-%m-%d %H:%M:%S') if entry_reached_time else None,
        'tp1_time': tp1_hit_time.strftime('%Y-%m-%d %H:%M:%S') if tp1_hit_time else None,
        'tp2_time': tp2_hit_time.strftime('%Y-%m-%d %H:%M:%S') if tp2_hit_time else None,
        'stop_time': stop_hit_time.strftime('%Y-%m-%d %H:%M:%S') if stop_hit_time else None,
        'entry_reached': entry_reached,
        'invalid_signal': invalid_signal,
    }
    
    return result

def evaluate_signals_from_report(signals_data: List[Dict], signal_time: datetime, 
                                  auto_sync: bool = True) -> List[Dict]:
    """评估多个信号"""
    # 自动补充价格数据
    if auto_sync:
        try:
            from src.auto_sync_prices_for_evaluation import auto_sync_prices_for_evaluation
            # 获取所有需要的时间框架
            timeframes = list(set([s.get('timeframe', '15m') for s in signals_data]))
            # 计算需要同步多少小时后的数据（默认24小时，或从信号生成到现在的时间）
            hours_ahead = max(24, int((datetime.now() - signal_time).total_seconds() / 3600) + 1)
            print("", file=sys.stderr)
            auto_sync_prices_for_evaluation(signal_time, timeframes=timeframes, 
                                           hours_ahead=hours_ahead, verbose=True)
            print("", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ 自动补充价格数据失败: {e}", file=sys.stderr)
            print("  将继续使用API获取数据", file=sys.stderr)
    
    results = []
    
    # 计算信号生成时间戳（秒）
    signal_timestamp_sec = int(signal_time.timestamp())
    # 计算当前时间戳（秒）
    current_timestamp_sec = int(datetime.now().timestamp())
    
    print(f"信号生成时间: {signal_time.strftime('%Y-%m-%d %H:%M:%S')} (时间戳: {signal_timestamp_sec})", file=sys.stderr)
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (时间戳: {current_timestamp_sec})", file=sys.stderr)
    print(f"时间跨度: {(current_timestamp_sec - signal_timestamp_sec) / 3600:.1f} 小时", file=sys.stderr)
    print("", file=sys.stderr)
    
    for signal in signals_data:
        timeframe = signal.get('timeframe', '15m')
        
        # 获取对应时间框架的K线数据（从信号生成时间开始到现在）
        print(f"正在获取{timeframe}K线数据（从信号生成时间开始）...", file=sys.stderr)
        klines = get_btc_kline_gateio(
            timeframe, 
            limit=200, 
            from_timestamp=signal_timestamp_sec,
            to_timestamp=current_timestamp_sec
        )
        
        if not klines:
            # 如果指定时间戳获取失败，尝试获取最新数据，然后过滤
            print(f"⚠️ 无法从指定时间获取{timeframe}K线数据，尝试获取最新数据并过滤", file=sys.stderr)
            klines = get_btc_kline_gateio(timeframe, limit=500)
            if klines:
                # 过滤出信号生成时间之后的K线
                klines = [k for k in klines if k['timestamp'] >= signal_timestamp_sec * 1000]
        
        if not klines:
            print(f"⚠️ 无法获取{timeframe}K线数据", file=sys.stderr)
            continue
        
        print(f"✅ 获取到 {len(klines)} 根K线（从信号生成时间开始）", file=sys.stderr)
        if klines:
            first_k_time = datetime.fromtimestamp(klines[0]['timestamp'] / 1000)
            last_k_time = datetime.fromtimestamp(klines[-1]['timestamp'] / 1000)
            print(f"   第一根K线: {first_k_time.strftime('%Y-%m-%d %H:%M:%S')} (价格: ${klines[0]['close']:,.2f})", file=sys.stderr)
            print(f"   最后一根K线: {last_k_time.strftime('%Y-%m-%d %H:%M:%S')} (价格: ${klines[-1]['close']:,.2f})", file=sys.stderr)
        print("", file=sys.stderr)
        
        # 评估信号
        result = evaluate_signal(signal, klines, signal_time)
        result['timeframe'] = timeframe
        result['model'] = signal.get('model', 'unknown')
        result['strength'] = signal.get('strength', 'unknown')
        results.append(result)
    
    return results

def format_evaluation_report(results: List[Dict]) -> str:
    """格式化评估报告"""
    report = []
    report.append("# 交易信号评估报告")
    report.append("")
    report.append(f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    current_price = get_btc_current_price()
    if current_price:
        report.append(f"**当前BTC价格**: ${current_price:,.2f}")
        report.append("")
    
    report.append("---")
    report.append("")
    
    for i, result in enumerate(results, 1):
        report.append(f"## 信号 {i}: {result['timeframe']} {result['type'].upper()}")
        report.append("")
        report.append(f"**生成时间**: {result['signal_time']}")
        report.append(f"**模型**: {result['model']}")
        report.append(f"**强度**: {result['strength']}")
        report.append(f"**入场**: ${result['entry']:,.2f}")
        report.append(f"**止损**: ${result['stop_loss']:,.2f}")
        if result['take_profit_1']:
            report.append(f"**止盈1**: ${result['take_profit_1']:,.2f} (50%)")
        if result['take_profit_2']:
            report.append(f"**止盈2**: ${result['take_profit_2']:,.2f} (50%)")
        report.append("")
        
        # 结果状态
        status_emoji = {
            'full_tp': '✅',
            'partial_tp': '⚠️',
            'stopped': '❌',
            'open': '🔄',
            'invalid': '🚫'
        }
        emoji = status_emoji.get(result['status'], '❓')
        
        status_text = result['status'].upper()
        if result['status'] == 'invalid':
            status_text = '无效（入场价未到但先到止盈1）'
        
        report.append(f"**结果状态**: {emoji} {status_text}")
        report.append("")
        
        if result['current_price']:
            pnl_emoji = '📈' if result['current_pnl_pct'] > 0 else '📉'
            report.append(f"**当前价格**: ${result['current_price']:,.2f} {pnl_emoji}")
            report.append(f"**当前盈亏**: {result['current_pnl_pct']:+.2f}%")
            report.append("")
        
        report.append(f"**最大浮盈**: {result['max_profit']:+.2f}%")
        report.append(f"**最大浮亏**: {result['max_loss']:+.2f}%")
        report.append("")
        
        # 时间摘要
        time_summary = result.get('time_summary', {})
        report.append("**时间线摘要**:")
        
        # 检查信号是否无效
        if time_summary.get('invalid_signal'):
            report.append(f"⚠️ **信号无效**：入场价未到但先到达止盈1")
            if time_summary.get('tp1_time'):
                report.append(f"- 先到达止盈1: {time_summary['tp1_time']} (价格: ${result['take_profit_1']:,.2f})")
            report.append("")
        else:
            # 正常信号的时间线
            if time_summary.get('entry_time'):
                report.append(f"- 到达入场价: {time_summary['entry_time']} (价格: ${result['entry']:,.2f})")
            if time_summary.get('tp1_time'):
                report.append(f"- 触及止盈1: {time_summary['tp1_time']} (价格: ${result['take_profit_1']:,.2f})")
            if time_summary.get('tp2_time'):
                report.append(f"- 触及止盈2: {time_summary['tp2_time']} (价格: ${result['take_profit_2']:,.2f})")
            if time_summary.get('stop_time'):
                stop_type = "保本止损" if result.get('hit_breakeven_stop') else "初始止损"
                stop_price = result['entry'] if result.get('hit_breakeven_stop') else result['stop_loss']
                report.append(f"- 触及{stop_type}: {time_summary['stop_time']} (价格: ${stop_price:,.2f})")
            if not any([time_summary.get('entry_time'), time_summary.get('tp1_time'), time_summary.get('tp2_time'), time_summary.get('stop_time')]):
                report.append("- 暂无关键事件")
        report.append("")
        
        # 详细事件时间线
        if result.get('timeline'):
            report.append("**详细时间线**:")
            for event in result['timeline']:
                report.append(f"- {event['time']}: {event['event']} (目标: ${event['target_price']:,.2f}, 实际: ${event['price']:,.2f})")
            report.append("")
        
        # 详细事件（保留原有格式）
        if result['details']:
            report.append("**关键事件详情**:")
            for detail in result['details']:
                report.append(f"- {detail}")
            report.append("")
        
        report.append("---")
        report.append("")
    
    # 统计摘要
    report.append("## 统计摘要")
    report.append("")
    total = len(results)
    full_tp = sum(1 for r in results if r['status'] == 'full_tp')
    partial_tp = sum(1 for r in results if r['status'] == 'partial_tp')
    stopped = sum(1 for r in results if r['status'] == 'stopped')
    open_count = sum(1 for r in results if r['status'] == 'open')
    invalid_count = sum(1 for r in results if r['status'] == 'invalid')
    valid_total = total - invalid_count  # 有效信号数（排除无效信号）
    
    report.append(f"- **总信号数**: {total}")
    if invalid_count > 0:
        report.append(f"- **无效信号**: {invalid_count} ({invalid_count/total*100:.1f}%) - 入场价未到但先到止盈1")
    report.append(f"- **有效信号数**: {valid_total}")
    if valid_total > 0:
        report.append(f"- **完全止盈**: {full_tp} ({full_tp/valid_total*100:.1f}%)")
        report.append(f"- **部分止盈**: {partial_tp} ({partial_tp/valid_total*100:.1f}%)")
        report.append(f"- **止损**: {stopped} ({stopped/valid_total*100:.1f}%)")
        report.append(f"- **持仓中**: {open_count} ({open_count/valid_total*100:.1f}%)")
        report.append("")
        report.append(f"- **有效信号胜率**: {(full_tp + partial_tp)/valid_total*100:.1f}%")
    report.append("")
    
    return "\n".join(report)

if __name__ == "__main__":
    # 从用户提供的信号数据创建信号列表
    signal_time = datetime(2025, 12, 29, 10, 55, 44)
    
    signals = [
        {
            'timeframe': '5m',
            'type': 'long',
            'entry': 88093,
            'stop_loss': 87800,
            'take_profit_1': 89531,
            'take_profit_2': 90250,
            'model': '反转形态-三重底',
            'strength': 'strong'
        },
        {
            'timeframe': '15m',
            'type': 'long',
            'entry': 89335,
            'stop_loss': 89067,
            'take_profit_1': 89465,
            'take_profit_2': 89600,
            'model': '区间突破',
            'strength': 'strong'
        },
        {
            'timeframe': '1h',
            'type': 'short',
            'entry': 89090,
            'stop_loss': 91054,
            'take_profit_1': 88353,
            'take_profit_2': 87461,
            'model': '阻力位回落',
            'strength': 'medium'
        }
    ]
    
    print("正在评估信号...", file=sys.stderr)
    
    # 检查是否有缓存
    use_cache = True
    force_refresh = False
    
    # 检查命令行参数
    if len(sys.argv) > 1 and '--refresh' in sys.argv:
        force_refresh = True
        use_cache = False
        print("🔄 强制刷新模式，忽略缓存", file=sys.stderr)
    
    # 尝试从缓存加载
    results = None
    if CACHE_AVAILABLE and use_cache and not force_refresh:
        cached_results = get_cached_evaluation(signal_time, force_refresh=force_refresh)
        if cached_results:
            print(f"✅ 使用缓存的评估结果（共 {len(cached_results)} 个信号）", file=sys.stderr)
            results = cached_results
    
    # 如果没有缓存，重新评估
    if results is None:
        print("📊 重新评估信号...", file=sys.stderr)
        results = evaluate_signals_from_report(signals, signal_time)
        
        # 保存到缓存
        if CACHE_AVAILABLE:
            current_price = get_btc_current_price()
            metadata = {
                'current_price': current_price,
                'signal_count': len(signals)
            }
            save_evaluation_cache(signal_time, results, metadata)
    
    # 生成报告
    report = format_evaluation_report(results)
    
    # 保存报告
    output_file = Path(f"信号评估报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n评估报告已保存到: {output_file}", file=sys.stderr)
    print("\n" + "="*60, file=sys.stderr)
    print(report, file=sys.stdout)

