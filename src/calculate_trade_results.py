#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易结果计算器
准确计算交易信号的盈亏结果和盈亏比
"""

import requests
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def get_btc_kline_gateio(timeframe='15m', limit=500, from_timestamp=None, to_timestamp=None):
    """
    从Gate.io获取BTC K线数据
    
    Args:
        timeframe: 时间框架 ('5m', '15m', '1h', '4h')
        limit: 获取的K线数量
        from_timestamp: 起始时间戳（秒）
        to_timestamp: 结束时间戳（秒）
    """
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h'}
        interval = tf_map.get(timeframe, '15m')
        
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


def calculate_trade_result(
    entry_price: float,
    stop_loss: float,
    take_profit_1: Optional[float],
    take_profit_2: Optional[float],
    signal_type: str,  # 'long' or 'short'
    timeframe: str,
    signal_time: Optional[datetime] = None,
    klines: Optional[List[Dict]] = None
) -> Dict:
    """
    计算交易结果
    
    Args:
        entry_price: 入场价格
        stop_loss: 止损价格
        take_profit_1: 第一止盈价格（50%仓位）
        take_profit_2: 第二止盈价格（50%仓位）
        signal_type: 信号类型 ('long' or 'short')
        timeframe: 时间框架
        signal_time: 信号生成时间（如果提供，会从该时间开始评估）
        klines: K线数据（如果提供，直接使用；否则会获取）
    
    Returns:
        交易结果字典
    """
    # 如果没有提供K线数据，获取数据
    if klines is None:
        if signal_time:
            signal_timestamp = int(signal_time.timestamp())
            current_timestamp = int(datetime.now().timestamp())
            klines = get_btc_kline_gateio(
                timeframe=timeframe,
                limit=500,
                from_timestamp=signal_timestamp,
                to_timestamp=current_timestamp
            )
        else:
            # 如果没有信号时间，获取最近的数据
            klines = get_btc_kline_gateio(timeframe=timeframe, limit=500)
    
    if not klines:
        return {
            'error': '无法获取K线数据',
            'status': 'error'
        }
    
    # 找到信号时间对应的K线索引
    start_idx = 0
    if signal_time:
        signal_timestamp = int(signal_time.timestamp() * 1000)
        for i, k in enumerate(klines):
            if k['timestamp'] >= signal_timestamp:
                start_idx = i
                break
    
    # 初始化结果
    result = {
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'signal_type': signal_type,
        'timeframe': timeframe,
        'status': 'open',  # open, stopped, partial_tp, full_tp
        'outcome': None,
        'entry_reached': False,
        'entry_time': None,
        'stop_hit': False,
        'stop_time': None,
        'stop_price': None,
        'tp1_hit': False,
        'tp1_time': None,
        'tp2_hit': False,
        'tp2_time': None,
        'max_profit_pct': 0.0,
        'max_loss_pct': 0.0,
        'final_pnl_pct': 0.0,
        'final_pnl_amount': 0.0,
        'risk_reward_ratio': 0.0,
        'actual_risk_reward_ratio': 0.0,
        'current_price': None,
        'timeline': [],
        'details': []
    }
    
    # 计算理论盈亏比
    if signal_type == 'long':
        risk_amount = entry_price - stop_loss
        if take_profit_1:
            reward_amount = take_profit_1 - entry_price
            if risk_amount > 0:
                result['risk_reward_ratio'] = reward_amount / risk_amount
    else:  # short
        risk_amount = stop_loss - entry_price
        if take_profit_1:
            reward_amount = entry_price - take_profit_1
            if risk_amount > 0:
                result['risk_reward_ratio'] = reward_amount / risk_amount
    
    # 保本止损逻辑：当触及TP1后，止损移动到入场价
    current_stop_loss = stop_loss
    entry_reached = False
    
    # 遍历K线，检查是否触及止损、止盈
    for i in range(start_idx, len(klines)):
        k = klines[i]
        k_time = datetime.fromtimestamp(k['timestamp'] / 1000)
        low = k['low']
        high = k['high']
        close = k['close']
        
        if signal_type == 'long':
            # 做多信号
            # 检查是否到达入场价
            if not entry_reached and low <= entry_price * 1.001:
                entry_reached = True
                result['entry_reached'] = True
                result['entry_time'] = k_time
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 到达入场价 ${entry_price:,.2f}")
            
            # 检查止盈1
            if take_profit_1 and not result['tp1_hit'] and high >= take_profit_1:
                if not entry_reached:
                    # 入场价未到但先到止盈1，信号无效
                    result['status'] = 'invalid'
                    result['outcome'] = 'invalid'
                    result['details'].append(f"❌ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 信号无效：入场价未到但先到达止盈1")
                    break
                
                result['tp1_hit'] = True
                result['tp1_time'] = k_time
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及止盈1 ${take_profit_1:,.2f}")
                # 移动止损到保本位
                current_stop_loss = entry_price
                result['details'].append(f"📌 止损已移动到保本位 ${entry_price:,.2f}")
            
            # 检查止盈2
            if result['tp1_hit'] and take_profit_2 and not result['tp2_hit'] and high >= take_profit_2:
                result['tp2_hit'] = True
                result['tp2_time'] = k_time
                result['status'] = 'full_tp'
                result['outcome'] = 'full_tp'
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及止盈2 ${take_profit_2:,.2f}")
                break
            
            # 检查止损
            if low <= current_stop_loss:
                result['stop_hit'] = True
                result['stop_time'] = k_time
                result['stop_price'] = current_stop_loss
                if current_stop_loss == entry_price:
                    result['status'] = 'partial_tp'
                    result['outcome'] = 'partial_tp'
                    result['details'].append(f"⚠️ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及保本止损 ${entry_price:,.2f}")
                else:
                    result['status'] = 'stopped'
                    result['outcome'] = 'stopped'
                    result['details'].append(f"❌ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及初始止损 ${stop_loss:,.2f}")
                break
            
            # 计算最大浮盈和浮亏
            if entry_reached:
                profit_pct = ((high - entry_price) / entry_price) * 100
                if profit_pct > result['max_profit_pct']:
                    result['max_profit_pct'] = profit_pct
                
                loss_pct = ((low - entry_price) / entry_price) * 100
                if loss_pct < result['max_loss_pct']:
                    result['max_loss_pct'] = loss_pct
        
        else:  # short
            # 做空信号
            # 检查止盈1（优先检查，因为需要验证入场价规则）
            if take_profit_1 and not result['tp1_hit'] and low <= take_profit_1:
                if not entry_reached:
                    # 入场价未到但先到止盈1，信号无效
                    result['status'] = 'invalid'
                    result['outcome'] = 'invalid'
                    result['details'].append(f"❌ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 信号无效：入场价未到但先到达止盈1")
                    break
                
                result['tp1_hit'] = True
                result['tp1_time'] = k_time
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及止盈1 ${take_profit_1:,.2f}")
                # 移动止损到保本位
                current_stop_loss = entry_price
                result['details'].append(f"📌 止损已移动到保本位 ${entry_price:,.2f}")
            
            # 检查是否到达入场价
            if not entry_reached and high >= entry_price * 0.999:
                entry_reached = True
                result['entry_reached'] = True
                result['entry_time'] = k_time
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 到达入场价 ${entry_price:,.2f}")
            
            # 检查止盈2
            if result['tp1_hit'] and take_profit_2 and not result['tp2_hit'] and low <= take_profit_2:
                result['tp2_hit'] = True
                result['tp2_time'] = k_time
                result['status'] = 'full_tp'
                result['outcome'] = 'full_tp'
                result['details'].append(f"✅ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及止盈2 ${take_profit_2:,.2f}")
                break
            
            # 检查止损
            if high >= current_stop_loss:
                result['stop_hit'] = True
                result['stop_time'] = k_time
                result['stop_price'] = current_stop_loss
                if current_stop_loss == entry_price:
                    result['status'] = 'partial_tp'
                    result['outcome'] = 'partial_tp'
                    result['details'].append(f"⚠️ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及保本止损 ${entry_price:,.2f}")
                else:
                    result['status'] = 'stopped'
                    result['outcome'] = 'stopped'
                    result['details'].append(f"❌ {k_time.strftime('%Y-%m-%d %H:%M:%S')} 触及初始止损 ${stop_loss:,.2f}")
                break
            
            # 计算最大浮盈和浮亏
            if entry_reached:
                profit_pct = ((entry_price - low) / entry_price) * 100
                if profit_pct > result['max_profit_pct']:
                    result['max_profit_pct'] = profit_pct
                
                loss_pct = ((entry_price - high) / entry_price) * 100
                if loss_pct < result['max_loss_pct']:
                    result['max_loss_pct'] = loss_pct
    
    # 计算最终盈亏
    if klines:
        current_price = klines[-1]['close']
        result['current_price'] = current_price
        
        if result['status'] == 'full_tp':
            # 完全止盈：50%在TP1，50%在TP2
            if signal_type == 'long':
                pnl1 = (take_profit_1 - entry_price) / entry_price * 100 * 0.5
                pnl2 = (take_profit_2 - entry_price) / entry_price * 100 * 0.5
            else:
                pnl1 = (entry_price - take_profit_1) / entry_price * 100 * 0.5
                pnl2 = (entry_price - take_profit_2) / entry_price * 100 * 0.5
            result['final_pnl_pct'] = pnl1 + pnl2
        elif result['status'] == 'partial_tp':
            # 部分止盈：50%在TP1，50%在保本止损
            if signal_type == 'long':
                pnl1 = (take_profit_1 - entry_price) / entry_price * 100 * 0.5
                pnl2 = 0.0  # 保本
            else:
                pnl1 = (entry_price - take_profit_1) / entry_price * 100 * 0.5
                pnl2 = 0.0  # 保本
            result['final_pnl_pct'] = pnl1 + pnl2
        elif result['status'] == 'stopped':
            # 止损
            if signal_type == 'long':
                result['final_pnl_pct'] = (stop_loss - entry_price) / entry_price * 100
            else:
                result['final_pnl_pct'] = (entry_price - stop_loss) / entry_price * 100
        else:
            # 持仓中，使用当前价格计算
            if signal_type == 'long':
                result['final_pnl_pct'] = (current_price - entry_price) / entry_price * 100
            else:
                result['final_pnl_pct'] = (entry_price - current_price) / entry_price * 100
        
        # 计算实际盈亏比
        if result['status'] in ['full_tp', 'partial_tp', 'stopped']:
            if signal_type == 'long':
                risk = (entry_price - stop_loss) / entry_price * 100
            else:
                risk = (stop_loss - entry_price) / entry_price * 100
            
            if risk > 0:
                result['actual_risk_reward_ratio'] = abs(result['final_pnl_pct']) / risk
    
    return result


def format_trade_result_report(result: Dict) -> str:
    """格式化交易结果报告"""
    report = []
    
    # 信号基本信息
    report.append(f"## {result['timeframe']} {result['signal_type'].upper()} 信号")
    report.append("")
    report.append(f"**入场价格**: ${result['entry_price']:,.2f}")
    report.append(f"**止损价格**: ${result['stop_loss']:,.2f}")
    if result['take_profit_1']:
        report.append(f"**止盈1**: ${result['take_profit_1']:,.2f} (50%)")
    if result['take_profit_2']:
        report.append(f"**止盈2**: ${result['take_profit_2']:,.2f} (50%)")
    report.append("")
    
    # 止损距离
    if result['signal_type'] == 'long':
        stop_distance_pct = ((result['entry_price'] - result['stop_loss']) / result['entry_price']) * 100
    else:
        stop_distance_pct = ((result['stop_loss'] - result['entry_price']) / result['entry_price']) * 100
    report.append(f"**止损距离**: {stop_distance_pct:.2f}%")
    report.append("")
    
    # 理论盈亏比
    if result['risk_reward_ratio'] > 0:
        report.append(f"**理论盈亏比**: {result['risk_reward_ratio']:.2f}:1")
    report.append("")
    
    # 交易结果
    status_emoji = {
        'full_tp': '✅',
        'partial_tp': '⚠️',
        'stopped': '❌',
        'open': '🔄',
        'invalid': '🚫'
    }
    emoji = status_emoji.get(result['status'], '❓')
    
    status_text = {
        'full_tp': '完全止盈',
        'partial_tp': '部分止盈（保本止损）',
        'stopped': '止损',
        'open': '持仓中',
        'invalid': '信号无效'
    }
    report.append(f"**交易结果**: {emoji} {status_text.get(result['status'], result['status'])}")
    report.append("")
    
    # 最终盈亏
    pnl_emoji = '📈' if result['final_pnl_pct'] >= 0 else '📉'
    report.append(f"**最终盈亏**: {pnl_emoji} {result['final_pnl_pct']:+.2f}%")
    if result['current_price']:
        report.append(f"**当前价格**: ${result['current_price']:,.2f}")
    report.append("")
    
    # 实际盈亏比
    if result['actual_risk_reward_ratio'] > 0:
        report.append(f"**实际盈亏比**: {result['actual_risk_reward_ratio']:.2f}:1")
    report.append("")
    
    # 最大浮盈/浮亏
    report.append(f"**最大浮盈**: {result['max_profit_pct']:+.2f}%")
    report.append(f"**最大浮亏**: {result['max_loss_pct']:+.2f}%")
    report.append("")
    
    # 时间线
    if result['entry_time']:
        report.append(f"**入场时间**: {result['entry_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    if result['tp1_time']:
        report.append(f"**止盈1时间**: {result['tp1_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    if result['tp2_time']:
        report.append(f"**止盈2时间**: {result['tp2_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    if result['stop_time']:
        report.append(f"**止损时间**: {result['stop_time'].strftime('%Y-%m-%d %H:%M:%S')} (价格: ${result['stop_price']:,.2f})")
    report.append("")
    
    # 详细事件
    if result['details']:
        report.append("**关键事件**:")
        for detail in result['details']:
            report.append(f"- {detail}")
        report.append("")
    
    return "\n".join(report)


def analyze_stop_loss_optimization(result: Dict, atr_pct: Optional[float] = None) -> Dict:
    """
    分析止损设置是否合理，提供优化建议
    
    Args:
        result: 交易结果字典
        atr_pct: ATR百分比（如果提供）
    
    Returns:
        优化建议字典
    """
    suggestions = {
        'current_stop_distance_pct': 0.0,
        'recommended_stop_distance_pct': 0.0,
        'is_stop_too_tight': False,
        'is_stop_too_wide': False,
        'suggestions': []
    }
    
    # 计算当前止损距离
    if result['signal_type'] == 'long':
        stop_distance_pct = ((result['entry_price'] - result['stop_loss']) / result['entry_price']) * 100
    else:
        stop_distance_pct = ((result['stop_loss'] - result['entry_price']) / result['entry_price']) * 100
    
    suggestions['current_stop_distance_pct'] = stop_distance_pct
    
    # 如果止损了，分析是否止损太紧
    if result['status'] == 'stopped':
        # 如果最大浮盈很大但最终还是止损了，说明止损可能太紧
        if result['max_profit_pct'] > abs(result['final_pnl_pct']) * 2:
            suggestions['is_stop_too_tight'] = True
            suggestions['suggestions'].append(
                f"⚠️ 止损可能太紧：最大浮盈达到 {result['max_profit_pct']:.2f}%，但最终止损 {result['final_pnl_pct']:.2f}%"
            )
    
    # 根据ATR建议止损距离
    if atr_pct:
        # 高波动建议止损距离为ATR的1.5-2倍
        if atr_pct > 0.5:  # 高波动
            recommended_stop = atr_pct * 1.5
            suggestions['recommended_stop_distance_pct'] = recommended_stop
            if stop_distance_pct < recommended_stop * 0.8:
                suggestions['is_stop_too_tight'] = True
                suggestions['suggestions'].append(
                    f"⚠️ 高波动市场建议止损距离: {recommended_stop:.2f}% (当前: {stop_distance_pct:.2f}%)"
                )
        else:  # 低波动
            recommended_stop = max(0.3, atr_pct * 1.2)
            suggestions['recommended_stop_distance_pct'] = recommended_stop
            if stop_distance_pct < recommended_stop * 0.7:
                suggestions['is_stop_too_tight'] = True
                suggestions['suggestions'].append(
                    f"⚠️ 低波动市场建议止损距离: {recommended_stop:.2f}% (当前: {stop_distance_pct:.2f}%)"
                )
    
    # 如果止损距离太小（<0.2%），建议调整
    if stop_distance_pct < 0.2:
        suggestions['is_stop_too_tight'] = True
        suggestions['suggestions'].append(
            f"⚠️ 止损距离过小 ({stop_distance_pct:.2f}%)，建议至少 0.3%"
        )
    
    # 如果止损距离太大（>3%），建议调整
    if stop_distance_pct > 3.0:
        suggestions['is_stop_too_wide'] = True
        suggestions['suggestions'].append(
            f"⚠️ 止损距离过大 ({stop_distance_pct:.2f}%)，建议不超过 2.5%"
        )
    
    return suggestions


if __name__ == "__main__":
    # 测试：评估用户提供的两个信号
    print("正在评估交易信号...", file=sys.stderr)
    
    # 15分钟做空信号
    signal_15m = {
        'entry_price': 87824,
        'stop_loss': 88087,
        'take_profit_1': 86493,
        'take_profit_2': 85620,
        'signal_type': 'short',
        'timeframe': '15m',
        'atr_pct': 0.08  # 低波动
    }
    
    # 1小时做多信号
    signal_1h = {
        'entry_price': 87018,
        'stop_loss': 86700,
        'take_profit_1': 88241,
        'take_profit_2': 89114,
        'signal_type': 'long',
        'timeframe': '1h',
        'atr_pct': 0.81  # 高波动
    }
    
    # 假设信号生成时间是当前时间往前推24小时
    signal_time = datetime.now() - timedelta(hours=24)
    
    print("\n" + "="*60, file=sys.stderr)
    print("评估 15分钟做空信号", file=sys.stderr)
    print("="*60, file=sys.stderr)
    
    result_15m = calculate_trade_result(
        entry_price=signal_15m['entry_price'],
        stop_loss=signal_15m['stop_loss'],
        take_profit_1=signal_15m['take_profit_1'],
        take_profit_2=signal_15m['take_profit_2'],
        signal_type=signal_15m['signal_type'],
        timeframe=signal_15m['timeframe'],
        signal_time=signal_time
    )
    
    report_15m = format_trade_result_report(result_15m)
    print(report_15m)
    
    # 止损优化分析
    suggestions_15m = analyze_stop_loss_optimization(result_15m, signal_15m.get('atr_pct'))
    if suggestions_15m['suggestions']:
        print("\n**止损优化建议**:")
        for suggestion in suggestions_15m['suggestions']:
            print(f"- {suggestion}")
        print("")
    
    print("\n" + "="*60, file=sys.stderr)
    print("评估 1小时做多信号", file=sys.stderr)
    print("="*60, file=sys.stderr)
    
    result_1h = calculate_trade_result(
        entry_price=signal_1h['entry_price'],
        stop_loss=signal_1h['stop_loss'],
        take_profit_1=signal_1h['take_profit_1'],
        take_profit_2=signal_1h['take_profit_2'],
        signal_type=signal_1h['signal_type'],
        timeframe=signal_1h['timeframe'],
        signal_time=signal_time
    )
    
    report_1h = format_trade_result_report(result_1h)
    print(report_1h)
    
    # 止损优化分析
    suggestions_1h = analyze_stop_loss_optimization(result_1h, signal_1h.get('atr_pct'))
    if suggestions_1h['suggestions']:
        print("\n**止损优化建议**:")
        for suggestion in suggestions_1h['suggestions']:
            print(f"- {suggestion}")
        print("")










