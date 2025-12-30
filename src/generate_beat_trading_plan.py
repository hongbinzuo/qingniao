#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成BEAT/USDT完整交易计划（做多和做空）
包含盈亏比、时间级别、有效期
"""

import requests
from datetime import datetime, timedelta
import sys

def get_beat_kline_data(timeframe='1h', limit=1000):
    """获取BEAT/USDT K线数据"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BEAT_USDT',
            'interval': timeframe,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
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
            klines = list(reversed(klines))
            if len(klines) > 1 and klines[0]['timestamp'] > klines[-1]['timestamp']:
                klines = list(reversed(klines))
            return klines
    except Exception as e:
        print(f"获取K线数据失败: {e}")
    return None

def get_current_beat_price():
    """获取当前BEAT价格"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': 'BEAT_USDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['last'])
    except:
        pass
    return None

def calculate_ema(prices, period):
    """计算EMA"""
    if len(prices) < period:
        return None
    multiplier = 2.0 / (period + 1)
    ema = [prices[0]]
    for i in range(1, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    return ema[-1]

def identify_support_resistance(klines):
    """识别关键支撑阻力位"""
    if not klines or len(klines) < 50:
        return None
    
    # 使用最近50根K线
    recent = klines[-50:]
    highs = [k['high'] for k in recent]
    lows = [k['low'] for k in recent]
    closes = [k['close'] for k in recent]
    
    # 找出明显的支撑和阻力位
    resistance = max(highs)
    support = min(lows)
    
    # 计算EMA作为动态支撑阻力
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)
    
    # 找出次高点和次低点
    sorted_highs = sorted(set(highs), reverse=True)
    sorted_lows = sorted(set(lows))
    
    resistance_2 = sorted_highs[1] if len(sorted_highs) > 1 else resistance
    support_2 = sorted_lows[1] if len(sorted_lows) > 1 else support
    
    return {
        'resistance_1': resistance,
        'resistance_2': resistance_2,
        'support_1': support,
        'support_2': support_2,
        'ema_20': ema_20,
        'ema_50': ema_50
    }

def calculate_rsi(prices, period=14):
    """计算RSI"""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_trading_plans():
    """生成完整交易计划"""
    print("=" * 80)
    print("BEAT/USDT 完整交易计划生成")
    print("=" * 80)
    print()
    
    # 获取数据
    print("正在获取市场数据...")
    current_price = get_current_beat_price()
    klines_1h = get_beat_kline_data('1h', 200)
    klines_15m = get_beat_kline_data('15m', 200)
    klines_5m = get_beat_kline_data('5m', 200)
    
    if not current_price or not klines_1h:
        print("获取数据失败")
        return
    
    # 使用最新K线价格
    if abs(klines_1h[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_1h[-1]['close']
    
    print(f"当前价格: ${current_price:.6f}")
    print()
    
    # 识别支撑阻力
    sr_levels = identify_support_resistance(klines_1h)
    
    # 计算技术指标
    closes_1h = [k['close'] for k in klines_1h]
    rsi_1h = calculate_rsi(closes_1h)
    ema_20_1h = calculate_ema(closes_1h, 20)
    ema_50_1h = calculate_ema(closes_1h, 50)
    
    # 生成报告
    plan = []
    plan.append("=" * 80)
    plan.append("BEAT/USDT 完整交易计划（做多+做空）")
    plan.append("=" * 80)
    plan.append("")
    plan.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plan.append(f"当前价格: ${current_price:.6f}")
    plan.append("")
    
    # 一、市场概况
    plan.append("## 一、当前市场概况")
    plan.append("")
    if sr_levels:
        plan.append(f"**关键阻力位**:")
        plan.append(f"  - 主要阻力位: ${sr_levels['resistance_1']:.6f}（50小时高点）")
        plan.append(f"  - 次要阻力位: ${sr_levels['resistance_2']:.6f}")
        plan.append("")
        plan.append(f"**关键支撑位**:")
        plan.append(f"  - 主要支撑位: ${sr_levels['support_1']:.6f}（50小时低点）")
        plan.append(f"  - 次要支撑位: ${sr_levels['support_2']:.6f}")
        plan.append("")
        if ema_20_1h and ema_50_1h:
            plan.append(f"**动态支撑/阻力**:")
            plan.append(f"  - EMA20: ${ema_20_1h:.6f}")
            plan.append(f"  - EMA50: ${ema_50_1h:.6f}")
            plan.append("")
    
    if rsi_1h:
        plan.append(f"**RSI**: {rsi_1h:.2f}")
        if rsi_1h > 70:
            plan.append("  → 超买，可能回调")
        elif rsi_1h < 30:
            plan.append("  → 超卖，可能反弹")
        plan.append("")
    
    # 二、做多交易计划
    plan.append("## 二、做多交易计划")
    plan.append("")
    
    if sr_levels:
        # 计算做多方案
        # 方案1：回调到支撑位做多（如果当前价格高于支撑位）
        if current_price > sr_levels['support_1']:
            long_entry_1 = sr_levels['support_1'] * 1.01  # 支撑位上方1%
            long_stop_loss_1 = sr_levels['support_1'] * 0.98  # 支撑位下方2%
            # 止盈目标：第一目标次要阻力位，第二目标主要阻力位
            long_take_profit_1_1 = sr_levels['resistance_2'] * 0.98  # 次要阻力位下方2%
            long_take_profit_1_2 = sr_levels['resistance_1'] * 0.95  # 主要阻力位下方5%
            
            risk_1 = long_entry_1 - long_stop_loss_1
            reward_1_1 = long_take_profit_1_1 - long_entry_1
            reward_1_2 = long_take_profit_1_2 - long_entry_1
            # 使用第一目标计算盈亏比（更保守）
            rr_ratio_1 = reward_1_1 / risk_1 if risk_1 > 0 else 0
        else:
            long_entry_1 = None
            rr_ratio_1 = 0
        
        # 方案2：回调到EMA20做多（如果当前价格高于EMA20）
        if ema_20_1h and current_price > ema_20_1h:
            long_entry_2 = ema_20_1h * 1.005  # EMA20上方0.5%
            long_stop_loss_2 = ema_20_1h * 0.98  # EMA20下方2%
            # 止盈：第一目标次要阻力位，第二目标主要阻力位
            long_take_profit_2_1 = sr_levels['resistance_2'] * 0.98
            long_take_profit_2_2 = sr_levels['resistance_1'] * 0.95
            
            risk_2 = long_entry_2 - long_stop_loss_2
            reward_2_1 = long_take_profit_2_1 - long_entry_2
            reward_2_2 = long_take_profit_2_2 - long_entry_2
            rr_ratio_2 = reward_2_1 / risk_2 if risk_2 > 0 else 0
        else:
            long_entry_2 = None
            rr_ratio_2 = 0
        
        if long_entry_1:
            plan.append("### 做多方案1：回调到支撑位做多")
        plan.append("")
        plan.append("**适用时间级别**: 1小时")
        plan.append("**计划有效期**: 24小时")
        plan.append("")
        plan.append("**入场条件**:")
        plan.append(f"  - 价格回调至: ${long_entry_1:.6f}（支撑位${sr_levels['support_1']:.6f}上方1%）")
        plan.append("  - 确认条件：")
        plan.append("    * 价格在支撑位附近出现反弹信号（K线收阳）")
        plan.append("    * 成交量放大")
        plan.append("    * RSI从超卖区域反弹")
        plan.append("")
        plan.append("**止损设置**:")
        plan.append(f"  - 止损位: ${long_stop_loss_1:.6f}（支撑位下方2%）")
        plan.append(f"  - 止损距离: ${risk_1:.6f} ({risk_1/long_entry_1*100:.2f}%)")
        plan.append("")
        plan.append("**止盈设置**:")
        plan.append(f"  - 第一目标: ${long_take_profit_1_1:.6f}（次要阻力位下方2%，止盈50%）")
        plan.append(f"  - 第二目标: ${long_take_profit_1_2:.6f}（主要阻力位下方5%，止盈50%）")
        plan.append(f"  - 第一目标距离: ${reward_1_1:.6f} ({reward_1_1/long_entry_1*100:.2f}%)")
        plan.append(f"  - 第二目标距离: ${reward_1_2:.6f} ({reward_1_2/long_entry_1*100:.2f}%)")
        plan.append("")
        plan.append(f"**盈亏比（第一目标）**: {rr_ratio_1:.2f}:1")
        plan.append(f"**盈亏比（第二目标）**: {reward_1_2/risk_1:.2f}:1")
        if rr_ratio_1 >= 3:
            plan.append("  → ✓ 盈亏比优秀（≥3:1）")
        elif rr_ratio_1 >= 2:
            plan.append("  → ✓ 盈亏比良好（≥2:1）")
        else:
            plan.append("  → ⚠ 盈亏比较低，需要谨慎")
        plan.append("")
        plan.append("**仓位管理**:")
        plan.append("  - 风险：账户的2-3%")
        plan.append("  - 根据止损距离计算仓位大小")
        plan.append("  - 使用逐仓模式")
        plan.append("")
        
        if long_entry_2 and rr_ratio_2 > 0:
            plan.append("### 做多方案2：回调到EMA20做多")
            plan.append("")
            plan.append("**适用时间级别**: 15分钟或1小时")
            plan.append("**计划有效期**: 12小时")
            plan.append("")
            plan.append("**入场条件**:")
            plan.append(f"  - 价格回调至: ${long_entry_2:.6f}（EMA20上方0.5%）")
            plan.append("  - 确认条件：")
            plan.append("    * 价格在EMA20附近获得支撑")
            plan.append("    * 15分钟K线出现看涨信号")
            plan.append("")
            plan.append("**止损设置**:")
            plan.append(f"  - 止损位: ${long_stop_loss_2:.6f}（EMA20下方2%）")
            plan.append(f"  - 止损距离: ${risk_2:.6f} ({risk_2/long_entry_2*100:.2f}%)")
            plan.append("")
            plan.append("**止盈设置**:")
            plan.append(f"  - 第一目标: ${long_take_profit_2_1:.6f}（次要阻力位下方2%，止盈50%）")
            plan.append(f"  - 第二目标: ${long_take_profit_2_2:.6f}（主要阻力位下方5%，止盈50%）")
            plan.append(f"  - 第一目标距离: ${reward_2_1:.6f} ({reward_2_1/long_entry_2*100:.2f}%)")
            plan.append(f"  - 第二目标距离: ${reward_2_2:.6f} ({reward_2_2/long_entry_2*100:.2f}%)")
            plan.append("")
            plan.append(f"**盈亏比（第一目标）**: {rr_ratio_2:.2f}:1")
            plan.append(f"**盈亏比（第二目标）**: {reward_2_2/risk_2:.2f}:1")
            if rr_ratio_2 >= 3:
                plan.append("  → ✓ 盈亏比优秀（≥3:1）")
            elif rr_ratio_2 >= 2:
                plan.append("  → ✓ 盈亏比良好（≥2:1）")
            plan.append("")
    
    # 三、做空交易计划
    plan.append("## 三、做空交易计划")
    plan.append("")
    
    if sr_levels:
        # 计算做空方案
        # 方案1：反弹到阻力位做空（如果当前价格低于阻力位）
        if current_price < sr_levels['resistance_1']:
            short_entry_1 = sr_levels['resistance_1'] * 0.99  # 阻力位下方1%
            short_stop_loss_1 = sr_levels['resistance_1'] * 1.02  # 阻力位上方2%
            # 止盈：第一目标次要支撑位，第二目标主要支撑位
            short_take_profit_1_1 = sr_levels['support_2'] * 1.02  # 次要支撑位上方2%
            short_take_profit_1_2 = sr_levels['support_1'] * 1.05  # 主要支撑位上方5%
            
            risk_1_short = short_stop_loss_1 - short_entry_1
            reward_1_short_1 = short_entry_1 - short_take_profit_1_1
            reward_1_short_2 = short_entry_1 - short_take_profit_1_2
            # 使用第一目标计算盈亏比（更保守）
            rr_ratio_1_short = reward_1_short_1 / risk_1_short if risk_1_short > 0 else 0
        else:
            short_entry_1 = None
            rr_ratio_1_short = 0
        
        # 方案2：反弹到EMA20做空（如果价格在EMA20下方）
        if ema_20_1h and current_price < ema_20_1h:
            short_entry_2 = ema_20_1h * 0.995  # EMA20下方0.5%
            short_stop_loss_2 = ema_20_1h * 1.02  # EMA20上方2%
            short_take_profit_2 = sr_levels['support_1'] * 1.05
            
            risk_2_short = short_stop_loss_2 - short_entry_2
            reward_2_short = short_entry_2 - short_take_profit_2
            rr_ratio_2_short = reward_2_short / risk_2_short if risk_2_short > 0 else 0
        
        plan.append("### 做空方案1：反弹到阻力位做空（最佳盈亏比）")
        plan.append("")
        plan.append("**适用时间级别**: 1小时")
        plan.append("**计划有效期**: 24小时")
        plan.append("")
        plan.append("**入场条件**:")
        plan.append(f"  - 价格反弹至: ${short_entry_1:.6f}（阻力位${sr_levels['resistance_1']:.6f}下方1%）")
        plan.append("  - 确认条件：")
        plan.append("    * 价格在阻力位附近出现反转信号（K线收阴）")
        plan.append("    * 成交量放大")
        plan.append("    * RSI从超买区域回落")
        plan.append("")
        plan.append("**止损设置**:")
        plan.append(f"  - 止损位: ${short_stop_loss_1:.6f}（阻力位上方2%）")
        plan.append(f"  - 止损距离: ${risk_1_short:.6f} ({risk_1_short/current_price*100:.2f}%)")
        plan.append("")
        plan.append("**止盈设置**:")
        plan.append(f"  - 第一目标: ${short_take_profit_1_1:.6f}（次要支撑位上方2%，止盈50%）")
        plan.append(f"  - 第二目标: ${short_take_profit_1_2:.6f}（主要支撑位上方5%，止盈50%）")
        plan.append(f"  - 第一目标距离: ${reward_1_short_1:.6f} ({reward_1_short_1/short_entry_1*100:.2f}%)")
        plan.append(f"  - 第二目标距离: ${reward_1_short_2:.6f} ({reward_1_short_2/short_entry_1*100:.2f}%)")
        plan.append("")
        plan.append(f"**盈亏比（第一目标）**: {rr_ratio_1_short:.2f}:1")
        plan.append(f"**盈亏比（第二目标）**: {reward_1_short_2/risk_1_short:.2f}:1")
        if rr_ratio_1_short >= 3:
            plan.append("  → ✓ 盈亏比优秀（≥3:1）")
        elif rr_ratio_1_short >= 2:
            plan.append("  → ✓ 盈亏比良好（≥2:1）")
        else:
            plan.append("  → ⚠ 盈亏比较低，需要谨慎")
        plan.append("")
        plan.append("**仓位管理**:")
        plan.append("  - 风险：账户的2-3%")
        plan.append("  - 根据止损距离计算仓位大小")
        plan.append("  - 使用逐仓模式")
        plan.append("")
        
        if ema_20_1h and current_price < ema_20_1h and short_entry_2 and rr_ratio_2_short > 0:
            plan.append("### 做空方案2：反弹到EMA20做空")
            plan.append("")
            plan.append("**适用时间级别**: 15分钟或1小时")
            plan.append("**计划有效期**: 12小时")
            plan.append("")
            plan.append("**入场条件**:")
            plan.append(f"  - 价格反弹至: ${short_entry_2:.6f}（EMA20下方0.5%）")
            plan.append("  - 确认条件：")
            plan.append("    * 价格在EMA20附近受阻")
            plan.append("    * 15分钟K线出现看跌信号")
            plan.append("")
            plan.append("**止损设置**:")
            plan.append(f"  - 止损位: ${short_stop_loss_2:.6f}（EMA20上方2%）")
            plan.append(f"  - 止损距离: ${risk_2_short:.6f} ({risk_2_short/short_entry_2*100:.2f}%)")
            plan.append("")
            plan.append("**止盈设置**:")
            plan.append(f"  - 第一目标: ${short_take_profit_2_1:.6f}（次要支撑位上方2%，止盈50%）")
            plan.append(f"  - 第二目标: ${short_take_profit_2_2:.6f}（主要支撑位上方5%，止盈50%）")
            plan.append(f"  - 第一目标距离: ${reward_2_short_1:.6f} ({reward_2_short_1/short_entry_2*100:.2f}%)")
            plan.append(f"  - 第二目标距离: ${reward_2_short_2:.6f} ({reward_2_short_2/short_entry_2*100:.2f}%)")
            plan.append("")
            plan.append(f"**盈亏比（第一目标）**: {rr_ratio_2_short:.2f}:1")
            plan.append(f"**盈亏比（第二目标）**: {reward_2_short_2/risk_2_short:.2f}:1")
            if rr_ratio_2_short >= 3:
                plan.append("  → ✓ 盈亏比优秀（≥3:1）")
            elif rr_ratio_2_short >= 2:
                plan.append("  → ✓ 盈亏比良好（≥2:1）")
            plan.append("")
    
    # 四、最佳交易机会推荐
    plan.append("## 四、最佳交易机会推荐（按盈亏比排序）")
    plan.append("")
    
    opportunities = []
    if sr_levels:
        # 做多机会
        if long_entry_1 and rr_ratio_1 > 0:
            opportunities.append({
                'direction': '做多',
                'entry': long_entry_1,
                'stop_loss': long_stop_loss_1,
                'take_profit': long_take_profit_1_1,
                'take_profit_2': long_take_profit_1_2,
                'rr_ratio': rr_ratio_1,
                'rr_ratio_2': reward_1_2/risk_1 if risk_1 > 0 else 0,
                'timeframe': '1小时',
                'valid_hours': 24,
                'description': '回调到支撑位做多'
            })
        if long_entry_2 and rr_ratio_2 > 0:
            opportunities.append({
                'direction': '做多',
                'entry': long_entry_2,
                'stop_loss': long_stop_loss_2,
                'take_profit': long_take_profit_2_1,
                'take_profit_2': long_take_profit_2_2,
                'rr_ratio': rr_ratio_2,
                'rr_ratio_2': reward_2_2/risk_2 if risk_2 > 0 else 0,
                'timeframe': '15分钟/1小时',
                'valid_hours': 12,
                'description': '回调到EMA20做多'
            })
        # 做空机会
        if short_entry_1 and rr_ratio_1_short > 0:
            opportunities.append({
                'direction': '做空',
                'entry': short_entry_1,
                'stop_loss': short_stop_loss_1,
                'take_profit': short_take_profit_1_1,
                'take_profit_2': short_take_profit_1_2,
                'rr_ratio': rr_ratio_1_short,
                'rr_ratio_2': reward_1_short_2/risk_1_short if risk_1_short > 0 else 0,
                'timeframe': '1小时',
                'valid_hours': 24,
                'description': '反弹到阻力位做空'
            })
        if ema_20_1h and current_price < ema_20_1h and rr_ratio_2_short > 0:
            opportunities.append({
                'direction': '做空',
                'entry': short_entry_2,
                'stop_loss': short_stop_loss_2,
                'take_profit': short_take_profit_2,
                'rr_ratio': rr_ratio_2_short,
                'timeframe': '15分钟/1小时',
                'valid_hours': 12,
                'description': '反弹到EMA20做空'
            })
    
    # 按盈亏比排序
    opportunities.sort(key=lambda x: x['rr_ratio'], reverse=True)
    
    for i, opp in enumerate(opportunities, 1):
        plan.append(f"**{i}. {opp['direction']} - {opp['description']}**")
        plan.append(f"  - 盈亏比（第一目标）: {opp['rr_ratio']:.2f}:1")
        if 'rr_ratio_2' in opp and opp['rr_ratio_2'] > 0:
            plan.append(f"  - 盈亏比（第二目标）: {opp['rr_ratio_2']:.2f}:1")
        plan.append(f"  - 入场: ${opp['entry']:.6f}")
        plan.append(f"  - 止损: ${opp['stop_loss']:.6f}")
        plan.append(f"  - 第一目标: ${opp['take_profit']:.6f}")
        if 'take_profit_2' in opp:
            plan.append(f"  - 第二目标: ${opp['take_profit_2']:.6f}")
        plan.append(f"  - 时间级别: {opp['timeframe']}")
        plan.append(f"  - 有效期: {opp['valid_hours']}小时")
        plan.append("")
    
    # 五、交易执行检查清单
    plan.append("## 五、交易执行检查清单")
    plan.append("")
    plan.append("**入场前检查**:")
    plan.append("□ 1. 价格是否到达计划入场位")
    plan.append("□ 2. 确认K线信号（看涨/看跌形态）")
    plan.append("□ 3. 成交量是否放大")
    plan.append("□ 4. RSI是否在合理区域")
    plan.append("□ 5. 是否在计划有效期内")
    plan.append("")
    plan.append("**风险管理检查**:")
    plan.append("□ 6. 已设置止损（必须）")
    plan.append("□ 7. 已设置止盈（分批）")
    plan.append("□ 8. 仓位大小已计算（风险2-3%）")
    plan.append("□ 9. 使用逐仓模式")
    plan.append("□ 10. 盈亏比≥2:1")
    plan.append("")
    
    # 六、风险提示
    plan.append("## 六、重要风险提示")
    plan.append("")
    plan.append("1. **市场风险**: 加密货币市场波动剧烈，价格可能快速反向运行")
    plan.append("2. **流动性风险**: BEAT/USDT流动性可能不足，注意滑点")
    plan.append("3. **时间风险**: 计划有效期过后，市场条件可能已改变")
    plan.append("4. **仓位风险**: 严格控制仓位，单笔交易风险不超过账户的3%")
    plan.append("5. **止损必须**: 必须设置止损，不要抱有侥幸心理")
    plan.append("")
    plan.append("**免责声明**: 本交易计划仅供参考，不构成投资建议。交易有风险，入市需谨慎。")
    plan.append("")
    plan.append("=" * 80)
    
    # 保存计划
    plan_text = "\n".join(plan)
    output_file = f"BEAT_USDT_trading_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(plan_text)
    
    sys.stdout.buffer.write(plan_text.encode('utf-8'))
    sys.stdout.buffer.write(f"\n\n交易计划已保存到: {output_file}\n".encode('utf-8'))

if __name__ == "__main__":
    generate_trading_plans()

