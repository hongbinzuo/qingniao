#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成RAVEUSDT.P 15分钟交易计划（结合De.交易系统）
使用Bybit交易所数据
"""

import requests
from datetime import datetime, timedelta
import sys

def get_bybit_kline_data(symbol='RAVEUSDT', timeframe='15', limit=200, category='linear'):
    """从Bybit获取K线数据"""
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': category,  # 'linear' = 永续合约, 'spot' = 现货
            'symbol': symbol,
            'interval': timeframe,  # '15' = 15分钟
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get('retCode') == 0 and result.get('result', {}).get('list'):
                data = result['result']['list']
                # Bybit返回的是从新到旧，需要反转
                data.reverse()
                
                klines = []
                for k in data:
                    # Bybit格式: [startTime, open, high, low, close, volume, turnover]
                    klines.append({
                        'timestamp': int(k[0]) // 1000,  # 转换为秒
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5]),
                        'turnover': float(k[6])
                    })
                return klines
    except Exception as e:
        print(f"获取K线数据失败: {e}")
        import traceback
        traceback.print_exc()
    return None

def get_current_rave_price(symbol='RAVEUSDT', category='linear'):
    """获取当前RAVE价格"""
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {
            'category': category,
            'symbol': symbol
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('retCode') == 0 and result.get('result', {}).get('list'):
                data = result['result']['list']
                if data and len(data) > 0:
                    return float(data[0]['lastPrice'])
    except Exception as e:
        print(f"获取价格失败: {e}")
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

def calculate_vwap(klines):
    """计算VWAP（成交量加权平均价）"""
    if not klines:
        return None
    
    total_pv = 0  # price * volume
    total_volume = 0
    
    for k in klines:
        typical_price = (k['high'] + k['low'] + k['close']) / 3
        total_pv += typical_price * k['volume']
        total_volume += k['volume']
    
    if total_volume > 0:
        return total_pv / total_volume
    return None

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

def identify_support_resistance_advanced(klines_15m, klines_1h=None, klines_4h=None):
    """使用科学的综合方法识别支撑阻力位"""
    from advanced_support_resistance import calculate_advanced_support_resistance
    
    if not klines_15m or len(klines_15m) < 50:
        return None
    
    closes_15m = [k['close'] for k in klines_15m]
    current_price = closes_15m[-1]
    
    # 1. Vegas通道（EMA144/169）
    ema_144_15m = calculate_ema(closes_15m, 144)
    ema_169_15m = calculate_ema(closes_15m, 169)
    
    # 2. VWAP
    vwap_15m = calculate_vwap(klines_15m[-100:])  # 使用更多K线计算VWAP
    
    # 3. 使用综合方法计算支撑阻力
    sr_results = calculate_advanced_support_resistance(
        klines_15m, 
        current_price,
        ema_144=ema_144_15m,
        ema_169=ema_169_15m,
        vwap=vwap_15m
    )
    
    # 4. 多时间框架确认（如果有）
    ema_144_1h = None
    ema_169_1h = None
    if klines_1h and len(klines_1h) >= 169:
        closes_1h = [k['close'] for k in klines_1h]
        ema_144_1h = calculate_ema(closes_1h, 144)
        ema_169_1h = calculate_ema(closes_1h, 169)
    
    # 整理结果
    support_levels = [l['price'] for l in sr_results['support_levels']] if sr_results else []
    resistance_levels = [l['price'] for l in sr_results['resistance_levels']] if sr_results else []
    
    return {
        'vegas_144': ema_144_15m,
        'vegas_169': ema_169_15m,
        'vwap': vwap_15m,
        'resistance_1': resistance_levels[0] if resistance_levels else max([k['high'] for k in klines_15m[-50:]]),
        'support_1': support_levels[0] if support_levels else min([k['low'] for k in klines_15m[-50:]]),
        'support_levels': sr_results['support_levels'] if sr_results else [],
        'resistance_levels': sr_results['resistance_levels'] if sr_results else [],
        'ema_144_1h': ema_144_1h,
        'ema_169_1h': ema_169_1h,
        'sr_details': sr_results  # 保存详细信息
    }

def generate_trading_plan():
    """生成RAVEUSDT.P交易计划"""
    print("=" * 80)
    print("RAVEUSDT.P 15分钟交易计划生成（De.交易系统）")
    print("=" * 80)
    print()
    
    # 获取数据
    print("正在获取市场数据...")
    symbol = 'RAVEUSDT'
    category = 'linear'  # 永续合约
    
    # 先尝试linear，如果失败再尝试spot
    current_price = get_current_rave_price(symbol, category)
    klines_15m = get_bybit_kline_data(symbol, '15', 200, category)
    
    if not current_price or not klines_15m:
        print("尝试使用spot类别...")
        category = 'spot'
        current_price = get_current_rave_price(symbol, category)
        klines_15m = get_bybit_kline_data(symbol, '15', 200, category)
    
    klines_1h = get_bybit_kline_data(symbol, '60', 200, category)  # 1小时数据用于多时间框架
    
    if not current_price or not klines_15m:
        print("获取数据失败，请检查网络连接或交易对名称")
        return
    
    # 使用最新K线价格
    if abs(klines_15m[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_15m[-1]['close']
    
    print(f"当前价格: ${current_price:.6f}")
    print(f"获取到 {len(klines_15m)} 根15分钟K线")
    print()
    
    # 识别支撑阻力
    sr_levels = identify_support_resistance_advanced(klines_15m, klines_1h)
    
    # 计算技术指标
    closes_15m = [k['close'] for k in klines_15m]
    rsi_15m = calculate_rsi(closes_15m)
    
    # 生成报告
    plan = []
    plan.append("=" * 80)
    plan.append("RAVEUSDT.P 15分钟交易计划（De.交易系统）")
    plan.append("=" * 80)
    plan.append("")
    plan.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plan.append(f"当前价格: ${current_price:.6f}")
    plan.append(f"数据来源: Bybit交易所")
    plan.append(f"时间级别: 15分钟")
    plan.append("")
    
    # 一、市场概况
    plan.append("## 一、当前市场概况")
    plan.append("")
    if sr_levels:
        plan.append("**Vegas通道（EMA144/169）**:")
        if sr_levels['vegas_144']:
            plan.append(f"  - EMA144: ${sr_levels['vegas_144']:.6f}")
        if sr_levels['vegas_169']:
            plan.append(f"  - EMA169: ${sr_levels['vegas_169']:.6f}")
        if sr_levels['vegas_144'] and sr_levels['vegas_169']:
            if current_price > sr_levels['vegas_169']:
                plan.append("  → 价格在Vegas通道上方，偏多")
            elif current_price < sr_levels['vegas_144']:
                plan.append("  → 价格在Vegas通道下方，偏空")
            else:
                plan.append("  → 价格在Vegas通道内，震荡行情")
        plan.append("")
        
        if sr_levels['vwap']:
            plan.append(f"**VWAP（15分钟）**: ${sr_levels['vwap']:.6f}")
            if current_price > sr_levels['vwap']:
                plan.append("  → 价格在VWAP上方，VWAP作为支撑")
            else:
                plan.append("  → 价格在VWAP下方，VWAP作为阻力")
            plan.append("")
        
        plan.append("**关键阻力位（综合多种方法）**:")
        if sr_levels.get('resistance_levels'):
            for i, level in enumerate(sr_levels['resistance_levels'][:5], 1):
                if isinstance(level, dict):
                    methods_str = ', '.join(level.get('methods', []))
                    score = level.get('score', 0)
                    plan.append(f"  - 阻力位{i}: ${level['price']:.6f}（方法: {methods_str}, 强度: {score:.1f}）")
                else:
                    plan.append(f"  - 阻力位{i}: ${level:.6f}")
        else:
            plan.append(f"  - 主要阻力位: ${sr_levels['resistance_1']:.6f}")
        plan.append("")
        
        plan.append("**关键支撑位（综合多种方法）**:")
        if sr_levels.get('support_levels'):
            for i, level in enumerate(sr_levels['support_levels'][:5], 1):
                if isinstance(level, dict):
                    methods_str = ', '.join(level.get('methods', []))
                    score = level.get('score', 0)
                    plan.append(f"  - 支撑位{i}: ${level['price']:.6f}（方法: {methods_str}, 强度: {score:.1f}）")
                else:
                    plan.append(f"  - 支撑位{i}: ${level:.6f}")
        else:
            plan.append(f"  - 主要支撑位: ${sr_levels['support_1']:.6f}")
        plan.append("")
        
        if sr_levels['ema_144_1h'] and sr_levels['ema_169_1h']:
            plan.append("**1小时级别Vegas通道（多时间框架确认）**:")
            plan.append(f"  - EMA144: ${sr_levels['ema_144_1h']:.6f}")
            plan.append(f"  - EMA169: ${sr_levels['ema_169_1h']:.6f}")
            plan.append("")
    
    if rsi_15m:
        plan.append(f"**RSI（15分钟）**: {rsi_15m:.2f}")
        if rsi_15m > 70:
            plan.append("  → 超买，可能回调")
        elif rsi_15m < 30:
            plan.append("  → 超卖，可能反弹")
        else:
            plan.append("  → 正常区域")
        plan.append("")
    
    # 二、做多交易计划
    plan.append("## 二、做多交易计划")
    plan.append("")
    
    if sr_levels:
        # 方案1：回调到Vegas通道下沿（EMA144）做多
        if sr_levels['vegas_144'] and current_price > sr_levels['vegas_144']:
            long_entry_1 = sr_levels['vegas_144'] * 1.005  # EMA144上方0.5%
            long_stop_loss_1 = sr_levels['vegas_144'] * 0.98  # EMA144下方2%
            # 第一目标应该是Vegas通道上沿或阻力位，不能低于入场价
            if sr_levels['vegas_169'] and sr_levels['vegas_169'] > long_entry_1:
                long_take_profit_1_1 = sr_levels['vegas_169'] * 0.98
            elif sr_levels['resistance_1'] and sr_levels['resistance_1'] > long_entry_1:
                long_take_profit_1_1 = sr_levels['resistance_1'] * 0.95
            else:
                long_take_profit_1_1 = long_entry_1 * 1.05  # 至少5%涨幅
            long_take_profit_1_2 = sr_levels['resistance_1'] * 0.95
            
            risk_1 = long_entry_1 - long_stop_loss_1
            reward_1_1 = long_take_profit_1_1 - long_entry_1
            reward_1_2 = long_take_profit_1_2 - long_entry_1
            rr_ratio_1 = reward_1_1 / risk_1 if risk_1 > 0 else 0
            
            plan.append("### 做多方案1：回调到Vegas通道下沿（EMA144）做多")
            plan.append("")
            plan.append("**适用时间级别**: 15分钟")
            plan.append("**计划有效期**: 12小时")
            plan.append("")
            plan.append("**入场条件**:")
            plan.append(f"  - 价格回调至: ${long_entry_1:.6f}（EMA144上方0.5%）")
            plan.append("  - 确认条件：")
            plan.append("    * 价格在EMA144附近获得支撑")
            plan.append("    * 15分钟K线出现看涨信号（长下影线、锤子线等）")
            plan.append("    * RSI从超卖区域反弹（<30后回升）")
            plan.append("    * 成交量放大")
            plan.append("")
            plan.append("**止损设置**:")
            plan.append(f"  - 止损位: ${long_stop_loss_1:.6f}（EMA144下方2%）")
            plan.append(f"  - 止损距离: ${risk_1:.6f} ({risk_1/long_entry_1*100:.2f}%)")
            plan.append("")
            plan.append("**止盈设置**:")
            plan.append(f"  - 第一目标: ${long_take_profit_1_1:.6f}（Vegas通道上沿或阻力位，止盈50%）")
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
        
        # 方案2：回调到VWAP做多
        if sr_levels['vwap'] and current_price > sr_levels['vwap']:
            long_entry_2 = sr_levels['vwap'] * 1.005
            long_stop_loss_2 = sr_levels['vwap'] * 0.98
            if sr_levels['vegas_169'] and sr_levels['vegas_169'] > long_entry_2:
                long_take_profit_2_1 = sr_levels['vegas_169'] * 0.98
            elif sr_levels['resistance_1'] and sr_levels['resistance_1'] > long_entry_2:
                long_take_profit_2_1 = sr_levels['resistance_1'] * 0.95
            else:
                long_take_profit_2_1 = long_entry_2 * 1.05
            long_take_profit_2_2 = sr_levels['resistance_1'] * 0.95
            
            risk_2 = long_entry_2 - long_stop_loss_2
            reward_2_1 = long_take_profit_2_1 - long_entry_2
            reward_2_2 = long_take_profit_2_2 - long_entry_2
            rr_ratio_2 = reward_2_1 / risk_2 if risk_2 > 0 else 0
            
            plan.append("### 做多方案2：回调到VWAP做多")
            plan.append("")
            plan.append("**适用时间级别**: 15分钟")
            plan.append("**计划有效期**: 8小时")
            plan.append("")
            plan.append("**入场条件**:")
            plan.append(f"  - 价格回调至: ${long_entry_2:.6f}（VWAP上方0.5%）")
            plan.append("  - 确认条件：")
            plan.append("    * 价格在VWAP附近获得支撑")
            plan.append("    * 15分钟K线出现看涨信号")
            plan.append("")
            plan.append("**止损设置**:")
            plan.append(f"  - 止损位: ${long_stop_loss_2:.6f}（VWAP下方2%）")
            plan.append(f"  - 止损距离: ${risk_2:.6f} ({risk_2/long_entry_2*100:.2f}%)")
            plan.append("")
            plan.append("**止盈设置**:")
            plan.append(f"  - 第一目标: ${long_take_profit_2_1:.6f}（止盈50%）")
            plan.append(f"  - 第二目标: ${long_take_profit_2_2:.6f}（止盈50%）")
            plan.append("")
            plan.append(f"**盈亏比（第一目标）**: {rr_ratio_2:.2f}:1")
            plan.append(f"**盈亏比（第二目标）**: {reward_2_2/risk_2:.2f}:1")
            plan.append("")
    
    # 三、做空交易计划
    plan.append("## 三、做空交易计划")
    plan.append("")
    
    if sr_levels:
        # 方案1：反弹到阻力位做空
        # 优先使用成交量密集区（POC、价值区域边界），而不是简单的前高
        short_entry_1 = None
        short_stop_loss_1 = None
        short_take_profit_1_1 = None
        short_take_profit_1_2 = None
        resistance_method = None
        resistance_price = None
        resistance_score = 0
        
        # 优先级1：成交量密集区（POC - 最强阻力位，分数10分）
        if sr_levels.get('sr_details') and sr_levels['sr_details'].get('methods', {}).get('volume_profile'):
            volume_profile = sr_levels['sr_details']['methods']['volume_profile']
            if volume_profile and volume_profile.get('poc'):
                poc_price = volume_profile['poc']
                if poc_price > current_price:
                    # POC在价格上方，优先使用POC作为阻力位
                    resistance_price = poc_price
                    resistance_method = 'volume_poc'
                    resistance_score = 10
                    short_entry_1 = resistance_price * 0.99  # 阻力位下方1%
                    short_stop_loss_1 = resistance_price * 1.02  # 阻力位上方2%
        
        # 优先级2：价值区域上沿（成交量密集区边界，分数8分）
        if not short_entry_1 and sr_levels.get('sr_details') and sr_levels['sr_details'].get('methods', {}).get('volume_profile'):
            volume_profile = sr_levels['sr_details']['methods']['volume_profile']
            if volume_profile and volume_profile.get('value_area_high'):
                value_area_high = volume_profile['value_area_high']
                if value_area_high > current_price:
                    resistance_price = value_area_high
                    resistance_method = 'volume_value_area'
                    resistance_score = 8
                    short_entry_1 = resistance_price * 0.99
                    short_stop_loss_1 = resistance_price * 1.02
        
        # 优先级2.5：价格上方的成交量密集区（如果POC和价值区域都在下方）
        if not short_entry_1 and sr_levels.get('resistance_levels') and len(sr_levels['resistance_levels']) > 0:
            # 找出成交量密集区相关的阻力位（volume_dense方法）
            volume_dense_resistances = [r for r in sr_levels['resistance_levels'] 
                                       if r['price'] > current_price and 'volume_dense' in ', '.join(r.get('methods', []))]
            if volume_dense_resistances:
                # 选择成交量最大的（分数最高的）
                best_volume_resistance = max(volume_dense_resistances, key=lambda x: x.get('score', 0))
                resistance_price = best_volume_resistance['price']
                resistance_method = ', '.join(best_volume_resistance.get('methods', []))
                resistance_score = best_volume_resistance.get('score', 0)
                short_entry_1 = resistance_price * 0.99
                short_stop_loss_1 = resistance_price * 1.02
        
        # 优先级3：价格行为法识别的阻力位（多次测试的位置，更可靠）
        if not short_entry_1 and sr_levels.get('resistance_levels') and len(sr_levels['resistance_levels']) > 0:
            valid_resistances = [r for r in sr_levels['resistance_levels'] if r['price'] > current_price]
            if valid_resistances:
                # 优先选择价格行为法（多次测试）或成交量相关的阻力位
                price_action_resistances = [r for r in valid_resistances if 'price_action' in ', '.join(r.get('methods', [])) or 'volume' in ', '.join(r.get('methods', []))]
                if price_action_resistances:
                    # 选择分数最高的价格行为阻力位
                    best_resistance = max(price_action_resistances, key=lambda x: x.get('score', 0))
                else:
                    # 如果没有价格行为阻力位，选择分数最高的
                    best_resistance = max(valid_resistances, key=lambda x: x.get('score', 0))
                
                resistance_price = best_resistance['price']
                resistance_method = ', '.join(best_resistance.get('methods', []))
                resistance_score = best_resistance.get('score', 0)
                short_entry_1 = resistance_price * 0.99
                short_stop_loss_1 = resistance_price * 1.02
        
        # 优先级4：历史高点（但需要多次测试才可靠，至少3次）
        if not short_entry_1 and sr_levels.get('sr_details') and sr_levels['sr_details'].get('methods', {}).get('historical'):
            historical = sr_levels['sr_details']['methods']['historical']
            if historical and historical.get('resistance'):
                hist_resistance = historical['resistance']
                if hist_resistance['price'] > current_price and hist_resistance.get('touches', 0) >= 3:
                    # 历史高点且测试次数>=3次，才使用
                    resistance_price = hist_resistance['price']
                    resistance_method = 'historical_high'
                    resistance_score = hist_resistance.get('touches', 0) * 2
                    short_entry_1 = resistance_price * 0.99
                    short_stop_loss_1 = resistance_price * 1.02
        
        # 如果价格在Vegas通道下方，也可以使用EMA169作为阻力位
        if not short_entry_1 and sr_levels.get('vegas_169') and current_price < sr_levels['vegas_169']:
            resistance_price = sr_levels['vegas_169']
            resistance_method = 'ema169'
            short_entry_1 = resistance_price * 0.995  # EMA169下方0.5%
            short_stop_loss_1 = resistance_price * 1.02  # EMA169上方2%
        
        # 如果还是没有，使用当前价格上方1%作为临时阻力位
        if not short_entry_1:
            resistance_price = current_price * 1.01
            resistance_method = 'current_price_1pct'
            short_entry_1 = resistance_price
            short_stop_loss_1 = current_price * 1.03
        
        # 设置止盈目标
        if sr_levels.get('vegas_144'):
            short_take_profit_1_1 = sr_levels['vegas_144'] * 1.02  # Vegas通道下沿
            short_take_profit_1_2 = sr_levels['vegas_144'] * 1.02
        elif sr_levels.get('support_1'):
            short_take_profit_1_1 = sr_levels['support_1'] * 1.05  # 主要支撑位上方5%
            short_take_profit_1_2 = sr_levels['support_1'] * 1.05
        else:
            short_take_profit_1_1 = short_entry_1 * 0.95  # 至少5%跌幅
            short_take_profit_1_2 = short_entry_1 * 0.95
        
        if short_entry_1:
            risk_1_short = short_stop_loss_1 - short_entry_1
            reward_1_short_1 = short_entry_1 - short_take_profit_1_1
            reward_1_short_2 = short_entry_1 - short_take_profit_1_2
            rr_ratio_1_short = reward_1_short_1 / risk_1_short if risk_1_short > 0 else 0
            
            plan.append("### 做空方案1：反弹到阻力位做空")
            plan.append("")
            plan.append("**适用时间级别**: 15分钟")
            plan.append("**计划有效期**: 12小时")
            plan.append("")
            plan.append("**入场条件**:")
            plan.append(f"  - 价格反弹至: ${short_entry_1:.6f}（阻力位下方1%）")
            plan.append(f"  - **阻力位判断方法**: {resistance_method}")
            if resistance_score > 0:
                plan.append(f"  - **阻力位强度**: {resistance_score:.1f}分")
            plan.append("  - 确认条件：")
            plan.append("    * 价格在阻力位附近受阻（出现看跌K线信号）")
            plan.append("    * 15分钟K线出现看跌信号（长上影线、倒锤子线、吞没形态等）")
            plan.append("    * RSI从超买区域回落（>70后下降）")
            plan.append("    * 成交量放大（确认阻力有效）")
            plan.append("    * 价格多次测试该阻力位但未能突破（如果可能）")
            plan.append("")
            plan.append("**阻力位判断方法说明**:")
            if resistance_method:
                methods_list = [m.strip() for m in resistance_method.split(',')]
                plan.append("  - **使用的方法**: " + ", ".join(methods_list))
                
                # 详细说明每种方法
                method_descriptions = []
                priority_note = ""
                
                if 'volume_poc' in resistance_method:
                    method_descriptions.append("**成交量分布POC法（优先）**：成交量最大的单一价格点，代表市场平均成本，是最强的阻力位")
                    priority_note = "✓ 优先使用成交量密集区（POC）"
                elif 'volume_value_area' in resistance_method:
                    method_descriptions.append("**成交量分布价值区域法（优先）**：价值区域上沿，70%成交量集中的区域边界，是强阻力位")
                    priority_note = "✓ 优先使用成交量密集区（价值区域边界）"
                if any('price_action' in m for m in methods_list):
                    method_descriptions.append("价格行为法（多次测试但未能突破的位置，更可靠）")
                if any('pivot' in m for m in methods_list):
                    method_descriptions.append("枢轴点法（基于前一个周期的最高价、最低价、收盘价计算R1/R2/R3）")
                if any('fib' in m for m in methods_list):
                    method_descriptions.append("斐波那契回撤法（重点关注618/786回撤位，OTE区间）")
                if any('ema' in m for m in methods_list):
                    method_descriptions.append("Vegas通道（EMA169作为动态阻力）")
                if any('historical' in m for m in methods_list):
                    method_descriptions.append("历史高低点法（历史高点，需多次测试≥3次才可靠）")
                if any('vwap' in m for m in methods_list):
                    method_descriptions.append("VWAP（成交量加权平均价）")
                
                if method_descriptions:
                    plan.append("  - **方法说明**: " + "；".join(method_descriptions))
                else:
                    plan.append("  - **方法说明**: 综合方法计算（多种方法确认）")
                
                if priority_note:
                    plan.append(f"  - **选择理由**: {priority_note}")
                
                if resistance_score > 0:
                    plan.append(f"  - **强度评分**: {resistance_score:.1f}分（分数越高，阻力越强）")
                    if resistance_score >= 10:
                        plan.append("  - **强度等级**: 极强（POC，成交量最大点）")
                    elif resistance_score >= 8:
                        plan.append("  - **强度等级**: 非常强（价值区域边界或多种方法确认）")
                    elif resistance_score >= 6:
                        plan.append("  - **强度等级**: 强（单一强方法或多方法确认）")
                    else:
                        plan.append("  - **强度等级**: 中等（一般方法）")
                
                # 特别说明：为什么不用简单的前高
                if 'historical' in resistance_method and resistance_score < 6:
                    plan.append("  - **注意**: 历史高点如果测试次数少（<3次），可能不够可靠，已优先考虑成交量密集区")
            plan.append("")
            plan.append("**止损设置**:")
            plan.append(f"  - 止损位: ${short_stop_loss_1:.6f}（阻力位上方2%）")
            plan.append(f"  - 止损距离: ${risk_1_short:.6f} ({risk_1_short/short_entry_1*100:.2f}%)")
            plan.append("")
            plan.append("**止盈设置**:")
            plan.append(f"  - 第一目标: ${short_take_profit_1_1:.6f}（Vegas通道下沿或支撑位，止盈50%）")
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
        
        # 方案2：反弹到VWAP做空
        if sr_levels['vwap'] and current_price < sr_levels['vwap']:
            short_entry_2 = sr_levels['vwap'] * 0.995
            short_stop_loss_2 = sr_levels['vwap'] * 1.02
            short_take_profit_2_1 = sr_levels['vegas_144'] * 1.02 if sr_levels['vegas_144'] else sr_levels['support_1'] * 1.05
            short_take_profit_2_2 = sr_levels['support_1'] * 1.05
            
            risk_2_short = short_stop_loss_2 - short_entry_2
            reward_2_short_1 = short_entry_2 - short_take_profit_2_1
            reward_2_short_2 = short_entry_2 - short_take_profit_2_2
            rr_ratio_2_short = reward_2_short_1 / risk_2_short if risk_2_short > 0 else 0
            
            plan.append("### 做空方案2：反弹到VWAP做空")
            plan.append("")
            plan.append("**适用时间级别**: 15分钟")
            plan.append("**计划有效期**: 8小时")
            plan.append("")
            plan.append("**入场条件**:")
            plan.append(f"  - 价格反弹至: ${short_entry_2:.6f}（VWAP下方0.5%）")
            plan.append("  - 确认条件：")
            plan.append("    * 价格在VWAP附近受阻")
            plan.append("    * 15分钟K线出现看跌信号")
            plan.append("")
            plan.append("**止损设置**:")
            plan.append(f"  - 止损位: ${short_stop_loss_2:.6f}（VWAP上方2%）")
            plan.append(f"  - 止损距离: ${risk_2_short:.6f} ({risk_2_short/short_entry_2*100:.2f}%)")
            plan.append("")
            plan.append("**止盈设置**:")
            plan.append(f"  - 第一目标: ${short_take_profit_2_1:.6f}（止盈50%）")
            plan.append(f"  - 第二目标: ${short_take_profit_2_2:.6f}（止盈50%）")
            plan.append("")
            plan.append(f"**盈亏比（第一目标）**: {rr_ratio_2_short:.2f}:1")
            plan.append(f"**盈亏比（第二目标）**: {reward_2_short_2/risk_2_short:.2f}:1")
            plan.append("")
    
    # 四、交易执行检查清单（De.系统）
    plan.append("## 四、交易执行检查清单（De.系统）")
    plan.append("")
    plan.append("**入场前检查**:")
    plan.append("□ 1. 价格是否到达计划入场位（Vegas通道/VWAP/支撑阻力）")
    plan.append("□ 2. 确认K线信号（看涨/看跌形态）")
    plan.append("□ 3. 成交量是否放大")
    plan.append("□ 4. RSI是否在合理区域（超买/超卖）")
    plan.append("□ 5. 是否在计划有效期内")
    plan.append("□ 6. 多时间框架确认（1小时Vegas通道方向）")
    plan.append("□ 7. 是否避开周末（周六不适合交易）")
    plan.append("")
    plan.append("**风险管理检查**:")
    plan.append("□ 8. 已设置止损（必须，窄止损）")
    plan.append("□ 9. 已设置止盈（分批，50%+50%）")
    plan.append("□ 10. 仓位大小已计算（风险2-3%）")
    plan.append("□ 11. 使用逐仓模式")
    plan.append("□ 12. 盈亏比≥2:1")
    plan.append("")
    
    # 五、重要风险提示
    plan.append("## 五、重要风险提示")
    plan.append("")
    plan.append("1. **市场风险**: 加密货币市场波动剧烈，价格可能快速反向运行")
    plan.append("2. **流动性风险**: RAVEUSDT流动性可能不足，注意滑点")
    plan.append("3. **时间风险**: 计划有效期过后，市场条件可能已改变")
    plan.append("4. **仓位风险**: 严格控制仓位，单笔交易风险不超过账户的3%")
    plan.append("5. **止损必须**: 必须设置止损，不要抱有侥幸心理")
    plan.append("6. **周末风险**: 周六不适合交易，流动性低")
    plan.append("")
    plan.append("**免责声明**: 本交易计划仅供参考，不构成投资建议。交易有风险，入市需谨慎。")
    plan.append("")
    plan.append("=" * 80)
    
    # 保存计划
    plan_text = "\n".join(plan)
    output_file = f"RAVEUSDT_15m_trading_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(plan_text)
    
    sys.stdout.buffer.write(plan_text.encode('utf-8'))
    sys.stdout.buffer.write(f"\n\n交易计划已保存到: {output_file}\n".encode('utf-8'))

if __name__ == "__main__":
    generate_trading_plan()

