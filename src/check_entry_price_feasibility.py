#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查信号入场价格的成交可行性
分析指定时间点的价格情况，评估挂单成交可能性
"""

import requests
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def get_btc_kline_gateio(timeframe='1h', limit=200, from_timestamp=None, to_timestamp=None):
    """从Gate.io获取BTC K线数据"""
    try:
        tf_map = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h'}
        interval = tf_map.get(timeframe, '1h')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': interval,
            'limit': min(limit, 1000)
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
        print(f"Gate.io获取失败: {e}", file=sys.stderr)
    return None


def get_btc_kline_1m_gateio(from_timestamp, to_timestamp):
    """获取1分钟K线数据（更精确）"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': '1m',
            'from': from_timestamp,
            'to': to_timestamp,
            'limit': 200
        }
        
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
        print(f"获取1分钟K线失败: {e}", file=sys.stderr)
    return None


def check_entry_price_feasibility(
    entry_price: float,
    signal_time: datetime,
    signal_type: str,  # 'long' or 'short'
    timeframe: str = '1h',
    tolerance_pct: float = 0.1  # 允许的价格偏差百分比
) -> Dict:
    """
    检查入场价格的成交可行性
    
    Args:
        entry_price: 入场价格
        signal_time: 信号生成时间
        signal_type: 信号类型 ('long' or 'short')
        timeframe: 时间框架
        tolerance_pct: 允许的价格偏差百分比
    
    Returns:
        可行性分析结果
    """
    result = {
        'entry_price': entry_price,
        'signal_time': signal_time.strftime('%Y-%m-%d %H:%M:%S'),
        'signal_type': signal_type,
        'timeframe': timeframe,
        'can_fill': False,
        'price_reached': False,
        'closest_price': None,
        'closest_time': None,
        'price_diff_pct': None,
        'price_range': {},
        'analysis': []
    }
    
    # 计算时间范围（信号生成时间前后各1小时）
    signal_timestamp = int(signal_time.timestamp())
    from_timestamp = signal_timestamp - 3600  # 往前1小时
    to_timestamp = signal_timestamp + 3600    # 往后1小时
    
    # 获取1分钟K线数据（更精确）
    print(f"正在获取 {signal_time.strftime('%Y-%m-%d %H:%M:%S')} 前后的价格数据...", file=sys.stderr)
    klines_1m = get_btc_kline_1m_gateio(from_timestamp, to_timestamp)
    
    if not klines_1m:
        # 如果1分钟K线获取失败，尝试1小时K线
        print("⚠️ 无法获取1分钟K线，尝试1小时K线...", file=sys.stderr)
        klines_1h = get_btc_kline_gateio('1h', limit=10, from_timestamp=from_timestamp, to_timestamp=to_timestamp)
        if klines_1h:
            klines_1m = klines_1h
        else:
            result['analysis'].append("❌ 无法获取价格数据")
            return result
    
    if not klines_1m:
        result['analysis'].append("❌ 无法获取价格数据")
        return result
    
    print(f"✅ 获取到 {len(klines_1m)} 根K线", file=sys.stderr)
    
    # 分析价格范围
    prices = []
    for k in klines_1m:
        prices.append(k['low'])
        prices.append(k['high'])
    
    if prices:
        min_price = min(prices)
        max_price = max(prices)
        result['price_range'] = {
            'min': min_price,
            'max': max_price,
            'range_pct': ((max_price - min_price) / min_price) * 100
        }
    
    # 检查入场价格是否在价格范围内
    if signal_type == 'long':
        # 做多：需要价格低于或等于入场价
        # 检查是否有K线的low <= entry_price
        for k in klines_1m:
            k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
            if k['low'] <= entry_price * (1 + tolerance_pct / 100):
                result['price_reached'] = True
                result['can_fill'] = True
                result['closest_price'] = k['low']
                result['closest_time'] = k_time
                result['price_diff_pct'] = ((entry_price - k['low']) / entry_price) * 100
                result['analysis'].append(
                    f"✅ 价格可达: {k_time.strftime('%Y-%m-%d %H:%M:%S')} 最低价 ${k['low']:,.2f} <= 入场价 ${entry_price:,.2f}"
                )
                break
    else:  # short
        # 做空：需要价格高于或等于入场价
        # 检查是否有K线的high >= entry_price
        for k in klines_1m:
            k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
            if k['high'] >= entry_price * (1 - tolerance_pct / 100):
                result['price_reached'] = True
                result['can_fill'] = True
                result['closest_price'] = k['high']
                result['closest_time'] = k_time
                result['price_diff_pct'] = ((k['high'] - entry_price) / entry_price) * 100
                result['analysis'].append(
                    f"✅ 价格可达: {k_time.strftime('%Y-%m-%d %H:%M:%S')} 最高价 ${k['high']:,.2f} >= 入场价 ${entry_price:,.2f}"
                )
                break
    
    # 如果没有找到精确匹配，找最接近的价格
    if not result['price_reached']:
        closest_k = None
        min_diff = float('inf')
        
        for k in klines_1m:
            k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
            if signal_type == 'long':
                # 做多：找最接近的低点
                diff = abs(k['low'] - entry_price)
            else:
                # 做空：找最接近的高点
                diff = abs(k['high'] - entry_price)
            
            if diff < min_diff:
                min_diff = diff
                closest_k = k
                result['closest_time'] = k_time
        
        if closest_k:
            if signal_type == 'long':
                result['closest_price'] = closest_k['low']
            else:
                result['closest_price'] = closest_k['high']
            
            result['price_diff_pct'] = ((result['closest_price'] - entry_price) / entry_price) * 100
            
            result['analysis'].append(
                f"⚠️ 价格未完全达到: 最接近价格 ${result['closest_price']:,.2f} "
                f"(偏差 {result['price_diff_pct']:+.2f}%)"
            )
            result['analysis'].append(
                f"   时间: {result['closest_time'].strftime('%Y-%m-%d %H:%M:%S')}"
            )
    
    # 添加价格范围信息
    if result['price_range']:
        result['analysis'].append("")
        result['analysis'].append(f"价格范围分析:")
        result['analysis'].append(f"  - 最低价: ${result['price_range']['min']:,.2f}")
        result['analysis'].append(f"  - 最高价: ${result['price_range']['max']:,.2f}")
        result['analysis'].append(f"  - 价格波动: {result['price_range']['range_pct']:.2f}%")
        
        # 检查入场价是否在范围内
        if result['price_range']['min'] <= entry_price <= result['price_range']['max']:
            result['analysis'].append(f"  - ✅ 入场价在价格范围内")
        else:
            if entry_price < result['price_range']['min']:
                diff = ((result['price_range']['min'] - entry_price) / entry_price) * 100
                result['analysis'].append(f"  - ⚠️ 入场价低于最低价 {diff:.2f}%")
            else:
                diff = ((entry_price - result['price_range']['max']) / entry_price) * 100
                result['analysis'].append(f"  - ⚠️ 入场价高于最高价 {diff:.2f}%")
    
    return result


def format_feasibility_report(result: Dict) -> str:
    """格式化可行性报告"""
    report = []
    
    report.append(f"## 入场价格成交可行性分析")
    report.append("")
    report.append(f"**信号生成时间**: {result['signal_time']}")
    report.append(f"**信号类型**: {result['signal_type'].upper()}")
    report.append(f"**时间框架**: {result['timeframe']}")
    report.append(f"**入场价格**: ${result['entry_price']:,.2f}")
    report.append("")
    
    # 成交可行性
    if result['can_fill']:
        report.append(f"**成交可行性**: ✅ **可以成交**")
        report.append("")
        report.append(f"**成交时间**: {result['closest_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**成交价格**: ${result['closest_price']:,.2f}")
        if result['price_diff_pct']:
            report.append(f"**价格偏差**: {result['price_diff_pct']:+.2f}%")
    else:
        report.append(f"**成交可行性**: ⚠️ **可能无法成交**")
        report.append("")
        if result['closest_price']:
            report.append(f"**最接近价格**: ${result['closest_price']:,.2f}")
            report.append(f"**最接近时间**: {result['closest_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            if result['price_diff_pct']:
                report.append(f"**价格偏差**: {result['price_diff_pct']:+.2f}%")
    
    report.append("")
    
    # 详细分析
    if result['analysis']:
        report.append("**详细分析**:")
        for line in result['analysis']:
            report.append(line)
        report.append("")
    
    # 建议
    report.append("**建议**:")
    if result['can_fill']:
        report.append("- ✅ 可以在入场价格挂单，成交可能性高")
        if result['price_diff_pct'] and abs(result['price_diff_pct']) > 0.1:
            report.append(f"- ⚠️ 注意：实际成交价格可能与入场价有 {abs(result['price_diff_pct']):.2f}% 的偏差")
    else:
        report.append("- ⚠️ 入场价格可能无法成交，建议：")
        if result['price_diff_pct']:
            if result['signal_type'] == 'long':
                report.append(f"  - 考虑在 ${result['closest_price']:,.2f} 附近挂单（当前入场价偏低）")
            else:
                report.append(f"  - 考虑在 ${result['closest_price']:,.2f} 附近挂单（当前入场价偏高）")
        report.append("  - 或者等待价格回到入场价附近再挂单")
    
    report.append("")
    
    return "\n".join(report)


if __name__ == "__main__":
    # 分析14:22生成的1小时做多信号
    signal_time = datetime(2025, 12, 30, 14, 22, 27)
    entry_price = 87018
    signal_type = 'long'
    
    print("="*80)
    print("入场价格成交可行性分析")
    print("="*80)
    print("")
    
    result = check_entry_price_feasibility(
        entry_price=entry_price,
        signal_time=signal_time,
        signal_type=signal_type,
        timeframe='1h',
        tolerance_pct=0.1
    )
    
    report = format_feasibility_report(result)
    print(report)





