#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估De.交易系统2025-12-30生成的信号结果
确保价格对齐准确
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

# 添加src目录到路径
current_dir = Path(__file__).parent.parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# 导入评估函数
from src.evaluate_signal_results import (
    evaluate_signals_from_report,
    format_evaluation_report,
    evaluate_signal
)

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def get_eth_kline_gateio(timeframe='5m', limit=200, from_timestamp=None, to_timestamp=None):
    """从Gate.io获取ETH K线数据"""
    try:
        import requests
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h'}
        interval = tf_map.get(timeframe, '5m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'ETH_USDT',
            'interval': interval,
            'limit': limit
        }
        
        if from_timestamp:
            params['from'] = from_timestamp
        if to_timestamp:
            params['to'] = to_timestamp
        
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
                klines = []
                for k in data:
                    ts = int(k[0])
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
        print(f"Gate.io获取ETH数据失败: {e}", file=sys.stderr)
    return None

def evaluate_eth_signals(signals_data: List[Dict], signal_time: datetime) -> List[Dict]:
    """评估ETH信号"""
    
    results = []
    signal_timestamp_sec = int(signal_time.timestamp())
    current_timestamp_sec = int(datetime.now().timestamp())
    
    print(f"ETH信号生成时间: {signal_time.strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
    
    for signal in signals_data:
        timeframe = signal.get('timeframe', '15m')
        print(f"正在获取ETH {timeframe}K线数据...", file=sys.stderr)
        
        klines = get_eth_kline_gateio(
            timeframe,
            limit=200,
            from_timestamp=signal_timestamp_sec,
            to_timestamp=current_timestamp_sec
        )
        
        if not klines:
            klines = get_eth_kline_gateio(timeframe, limit=500)
            if klines:
                klines = [k for k in klines if k['timestamp'] >= signal_timestamp_sec * 1000]
        
        if not klines:
            print(f"⚠️ 无法获取ETH {timeframe}K线数据", file=sys.stderr)
            continue
        
        print(f"✅ 获取到 {len(klines)} 根ETH K线", file=sys.stderr)
        
        result = evaluate_signal(signal, klines, signal_time)
        result['timeframe'] = timeframe
        result['model'] = signal.get('model', 'unknown')
        result['strength'] = signal.get('strength', 'unknown')
        results.append(result)
    
    return results

def main():
    # BTC信号生成时间：2025-12-30 18:11:00
    btc_signal_time = datetime(2025, 12, 30, 18, 11, 0)
    
    # ETH信号生成时间：2025-12-30 21:25:41
    eth_signal_time = datetime(2025, 12, 30, 21, 25, 41)
    
    # 解析BTC信号
    btc_signals = [
        {
            'timeframe': '5m',
            'type': 'long',
            'entry': 87328,
            'stop_loss': 87000,
            'take_profit_1': 88877,
            'take_profit_2': 89757,
            'model': 'De.交易系统',
            'strength': 'strong'
        },
        {
            'timeframe': '1h',
            'type': 'long',
            'entry': 87956,
            'stop_loss': 87612,  # 优化后的止损
            'take_profit_1': 91430,
            'take_profit_2': 93168,
            'model': 'De.交易系统',
            'strength': 'medium'
        },
        {
            'timeframe': '15m',
            'type': 'short',
            'entry': 87622,
            'stop_loss': 88000,
            'take_profit_1': 85814,
            'take_profit_2': 84911,
            'model': 'De.交易系统',
            'strength': 'medium'
        }
    ]
    
    # 解析ETH信号
    eth_signals = [
        # 5分钟信号
        {
            'timeframe': '5m',
            'type': 'long',
            'entry': 2959.97,
            'stop_loss': 2886.33,
            'take_profit_1': 3006.80,
            'take_profit_2': 3050.54,
            'model': 'De.交易系统',
            'strength': 'medium'
        },
        {
            'timeframe': '5m',
            'type': 'short',
            'entry': 3005.68,
            'stop_loss': 3050.54,
            'take_profit_1': 2967.95,
            'take_profit_2': 2938.57,
            'model': 'De.交易系统',
            'strength': 'weak'
        },
        {
            'timeframe': '5m',
            'type': 'long',
            'entry': 2993.72,
            'stop_loss': 2938.58,
            'take_profit_1': 3000.91,
            'take_profit_2': 3007.20,
            'model': 'De.交易系统',
            'strength': 'strong'
        },
        # 15分钟信号
        {
            'timeframe': '15m',
            'type': 'long',
            'entry': 2974.94,
            'stop_loss': 2900.94,
            'take_profit_1': 3020.83,
            'take_profit_2': 3050.54,
            'model': 'De.交易系统',
            'strength': 'medium'
        },
        {
            'timeframe': '15m',
            'type': 'long',
            'entry': 2993.72,
            'stop_loss': 2953.18,
            'take_profit_1': 3010.58,
            'take_profit_2': 3022.84,
            'model': 'De.交易系统',
            'strength': 'strong'
        },
        # 1小时信号
        {
            'timeframe': '1h',
            'type': 'short',
            'entry': 3005.68,
            'stop_loss': 3050.54,
            'take_profit_1': 2986.13,
            'take_profit_2': 2956.57,
            'model': 'De.交易系统',
            'strength': 'weak'
        },
        {
            'timeframe': '1h',
            'type': 'long',
            'entry': 2993.72,
            'stop_loss': 2975.19,
            'take_profit_1': 3041.21,
            'take_profit_2': 3072.41,
            'model': 'De.交易系统',
            'strength': 'strong'
        }
    ]
    
    print("="*80, file=sys.stderr)
    print("De.交易系统信号评估报告", file=sys.stderr)
    print("="*80, file=sys.stderr)
    print("", file=sys.stderr)
    
    # 评估BTC信号
    print("📊 正在评估BTC信号...", file=sys.stderr)
    print("", file=sys.stderr)
    btc_results = evaluate_signals_from_report(btc_signals, btc_signal_time)
    
    # 评估ETH信号
    print("", file=sys.stderr)
    print("📊 正在评估ETH信号...", file=sys.stderr)
    print("", file=sys.stderr)
    eth_results = evaluate_eth_signals(eth_signals, eth_signal_time)
    
    # 生成报告
    all_results = btc_results + eth_results
    
    # 分别生成BTC和ETH报告
    btc_report = format_evaluation_report(btc_results)
    eth_report = format_evaluation_report(eth_results)
    
    # 保存报告
    output_dir = Path("signal_evaluations")
    output_dir.mkdir(exist_ok=True)
    
    btc_output_file = output_dir / f"BTC信号评估_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    eth_output_file = output_dir / f"ETH信号评估_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(btc_output_file, 'w', encoding='utf-8') as f:
        f.write("# BTC交易信号评估报告\n\n")
        f.write(btc_report)
    
    with open(eth_output_file, 'w', encoding='utf-8') as f:
        f.write("# ETH交易信号评估报告\n\n")
        f.write(eth_report)
    
    print("", file=sys.stderr)
    print("="*80, file=sys.stderr)
    print(f"✅ BTC评估报告已保存: {btc_output_file}", file=sys.stderr)
    print(f"✅ ETH评估报告已保存: {eth_output_file}", file=sys.stderr)
    print("="*80, file=sys.stderr)
    print("", file=sys.stderr)
    
    # 输出到stdout
    print("# De.交易系统信号评估报告")
    print("")
    print("## BTC信号评估")
    print("")
    print(btc_report)
    print("")
    print("---")
    print("")
    print("## ETH信号评估")
    print("")
    print(eth_report)

if __name__ == "__main__":
    main()

