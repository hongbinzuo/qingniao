#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAVE新币做空交易计划生成器
基于币安新币砸盘策略和De.交易系统
"""

import requests
import sys
from datetime import datetime

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

def get_rave_kline_data(timeframe='15', limit=200, category='linear'):
    """获取RAVEUSDT的K线数据"""
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            'category': category,
            'symbol': 'RAVEUSDT',
            'interval': timeframe,  # '15' = 15分钟, '60' = 1小时
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                klines = data['result']['list']
                klines.reverse()  # 反转，让时间从旧到新
                return [{
                    'timestamp': int(k[0]) // 1000,  # 转换为秒
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                } for k in klines]
    except Exception as e:
        print(f"获取K线数据失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    return None

def get_current_price(category='linear'):
    """获取当前价格"""
    try:
        url = "https://api.bybit.com/v5/market/tickers"
        params = {'category': category, 'symbol': 'RAVEUSDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0 and data.get('result', {}).get('list'):
                return float(data['result']['list'][0]['lastPrice'])
    except Exception as e:
        print(f"获取当前价格失败: {e}", file=sys.stderr)
    return None

def calculate_rsi(prices, period=14):
    """计算RSI"""
    if len(prices) < period + 1:
        return None
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_new_listing_pattern(klines):
    """分析是否符合新币砸盘模式，并判断是否可能创新高"""
    if not klines or len(klines) < 50:
        return None
    
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]
    
    current_price = closes[-1]
    
    # 1. 计算价格变化
    price_change_pct = ((current_price - closes[0]) / closes[0]) * 100 if closes[0] > 0 else 0
    
    # 2. 找出最高点
    max_price = max(highs)
    max_price_idx = highs.index(max_price)
    max_price_change_pct = ((max_price - closes[0]) / closes[0]) * 100 if closes[0] > 0 else 0
    
    # 3. 计算从最高点的跌幅
    drop_from_high_pct = ((max_price - current_price) / max_price) * 100 if max_price > 0 else 0
    
    # 4. 成交量分析
    max_volume = max(volumes)
    max_volume_idx = volumes.index(max_volume)
    recent_volume = sum(volumes[-10:]) / 10
    early_volume = sum(volumes[:10]) / 10 if len(volumes) >= 10 else recent_volume
    volume_ratio = recent_volume / early_volume if early_volume > 0 else 1
    
    # 5. RSI分析
    rsi = calculate_rsi(closes)
    
    # 6. 判断是否可能创新高（关键分析）
    may_break_high = False
    break_high_signals = []
    no_break_high_signals = []
    
    # 可能创新高的信号
    if current_price > max_price * 0.95:  # 接近最高点（5%以内）
        break_high_signals.append("⚠ 价格接近历史最高点（5%以内），可能突破")
        may_break_high = True
    
    if len(volumes) >= 10 and sum(volumes[-5:]) > sum(volumes[-10:-5]):  # 最近5根K线成交量增加
        break_high_signals.append("⚠ 成交量在增加，可能推动价格上涨")
        may_break_high = True
    
    if rsi and rsi < 70 and rsi > 50:  # RSI在正常区域，还有上涨空间
        break_high_signals.append("⚠ RSI未超买（{:.1f}），还有上涨空间".format(rsi))
        may_break_high = True
    
    if max_price_idx >= len(closes) - 5:  # 最高点就在最近5根K线
        break_high_signals.append("⚠ 最高点就在最近，可能再次测试")
        may_break_high = True
    
    # 不太可能创新高的信号
    if drop_from_high_pct > 20:
        no_break_high_signals.append("✓ 价格从最高点已下跌 {:.1f}%，距离较远".format(drop_from_high_pct))
    
    if volume_ratio < 0.5:
        no_break_high_signals.append("✓ 成交量萎缩（当前/初期 = {:.2f}），买盘力量减弱".format(volume_ratio))
    
    if rsi and rsi < 50:
        no_break_high_signals.append("✓ RSI偏低（{:.1f}），上涨动能不足".format(rsi))
    
    if max_price_idx < len(closes) - 20:  # 最高点在20根K线之前
        no_break_high_signals.append("✓ 最高点在 {} 根K线前，已确认顶部".format(max_price_idx))
    
    # 7. 判断是否符合新币砸盘模式
    is_new_listing_pattern = False
    signals = []
    
    # 信号1：价格从高点大幅回落
    if drop_from_high_pct > 20:
        signals.append(f"✓ 价格从最高点已下跌 {drop_from_high_pct:.1f}%")
        is_new_listing_pattern = True
    
    # 信号2：成交量萎缩
    if volume_ratio < 0.5:
        signals.append(f"✓ 成交量萎缩（当前/初期 = {volume_ratio:.2f}）")
        is_new_listing_pattern = True
    
    # 信号3：RSI超买后回落
    if rsi and rsi > 70:
        signals.append(f"✓ RSI超买（{rsi:.1f}）")
        is_new_listing_pattern = True
    elif rsi and rsi < 70 and max_price_idx < len(closes) - 10:
        # 之前超买，现在回落
        signals.append(f"✓ RSI从超买区域回落（当前 {rsi:.1f}）")
        is_new_listing_pattern = True
    
    # 信号4：价格达到高点后持续下跌
    if max_price_idx < len(closes) - 20:  # 最高点在20根K线之前
        signals.append(f"✓ 价格在 {max_price_idx} 根K线前达到最高点，随后下跌")
        is_new_listing_pattern = True
    
    return {
        'is_new_listing_pattern': is_new_listing_pattern,
        'signals': signals,
        'current_price': current_price,
        'max_price': max_price,
        'max_price_idx': max_price_idx,
        'price_change_pct': price_change_pct,
        'max_price_change_pct': max_price_change_pct,
        'drop_from_high_pct': drop_from_high_pct,
        'volume_ratio': volume_ratio,
        'rsi': rsi,
        'max_volume_idx': max_volume_idx,
        'may_break_high': may_break_high,
        'break_high_signals': break_high_signals,
        'no_break_high_signals': no_break_high_signals
    }

def identify_resistance_levels(klines, current_price):
    """识别阻力位（用于做空）"""
    if not klines or len(klines) < 50:
        return None
    
    highs = [k['high'] for k in klines]
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # 1. 历史最高点
    max_high = max(highs)
    
    # 2. 成交量峰值对应的价格
    max_volume_idx = volumes.index(max(volumes))
    volume_peak_price = klines[max_volume_idx]['high']
    
    # 3. 最近的高点（如果价格已从高点回落）
    recent_highs = highs[-20:]
    recent_max = max(recent_highs)
    
    # 4. EMA144/169（Vegas通道）
    ema_144 = calculate_ema(closes, 144) if len(closes) >= 144 else None
    ema_169 = calculate_ema(closes, 169) if len(closes) >= 169 else None
    
    # 5. VWAP
    vwap = calculate_vwap(klines[-100:]) if len(klines) >= 100 else None
    
    resistance_levels = []
    
    # 优先级1：历史最高点（如果价格在下方）
    if max_high > current_price:
        resistance_levels.append({
            'price': max_high,
            'method': 'historical_high',
            'strength': 10,
            'description': '历史最高点'
        })
    
    # 优先级2：成交量峰值价格（如果价格在下方）
    if volume_peak_price > current_price and volume_peak_price < max_high * 1.1:
        resistance_levels.append({
            'price': volume_peak_price,
            'method': 'volume_peak',
            'strength': 9,
            'description': '成交量峰值对应的价格'
        })
    
    # 优先级3：最近高点
    if recent_max > current_price and recent_max < max_high:
        resistance_levels.append({
            'price': recent_max,
            'method': 'recent_high',
            'strength': 7,
            'description': '最近20根K线的最高点'
        })
    
    # 优先级4：EMA169（如果价格在下方）
    if ema_169 and ema_169 > current_price:
        resistance_levels.append({
            'price': ema_169,
            'method': 'ema169',
            'strength': 8,
            'description': 'Vegas通道上沿（EMA169）'
        })
    
    # 优先级5：EMA144（如果价格在下方）
    if ema_144 and ema_144 > current_price:
        resistance_levels.append({
            'price': ema_144,
            'method': 'ema144',
            'strength': 7,
            'description': 'Vegas通道下沿（EMA144）'
        })
    
    # 优先级6：VWAP（如果价格在下方）
    if vwap and vwap > current_price:
        resistance_levels.append({
            'price': vwap,
            'method': 'vwap',
            'strength': 6,
            'description': 'VWAP（成交量加权平均价）'
        })
    
    # 按强度排序，选择最强的阻力位
    resistance_levels.sort(key=lambda x: x['strength'], reverse=True)
    
    return resistance_levels[0] if resistance_levels else None

def generate_short_plan():
    """生成做空交易计划"""
    print("正在获取RAVE市场数据...", file=sys.stderr)
    
    # 获取数据（先尝试linear，如果失败再尝试spot）
    category = 'linear'
    klines_15m = get_rave_kline_data('15', 200, category)
    klines_1h = get_rave_kline_data('60', 100, category)
    current_price = get_current_price(category)
    
    if not klines_15m or not current_price:
        print("尝试使用spot类别...", file=sys.stderr)
        category = 'spot'
        klines_15m = get_rave_kline_data('15', 200, category)
        klines_1h = get_rave_kline_data('60', 100, category)
        current_price = get_current_price(category)
    
    if not klines_15m or not current_price:
        print("无法获取市场数据", file=sys.stderr)
        return
    
    # 使用最新K线价格
    if abs(klines_15m[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_15m[-1]['close']
    
    # 分析新币砸盘模式
    pattern_analysis = analyze_new_listing_pattern(klines_15m)
    
    # 识别阻力位
    resistance = identify_resistance_levels(klines_15m, current_price)
    
    # 计算技术指标
    closes_15m = [k['close'] for k in klines_15m]
    volumes_15m = [k['volume'] for k in klines_15m]
    rsi = calculate_rsi(closes_15m)
    ema_144 = calculate_ema(closes_15m, 144) if len(closes_15m) >= 144 else None
    ema_169 = calculate_ema(closes_15m, 169) if len(closes_15m) >= 169 else None
    vwap = calculate_vwap(klines_15m[-100:])
    
    # 生成交易计划
    plan = []
    plan.append("=" * 80)
    plan.append("RAVEUSDT 新币做空交易计划（基于新币砸盘策略）")
    plan.append("=" * 80)
    plan.append("")
    plan.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plan.append(f"当前价格: ${current_price:.6f}")
    plan.append("数据来源: Bybit交易所")
    plan.append("时间级别: 15分钟（主要）+ 1小时（确认）")
    plan.append("")
    
    # 一、新币砸盘模式分析
    plan.append("## 一、新币砸盘模式分析")
    plan.append("")
    
    # 重要提醒：是否可能创新高
    plan.append("### ⚠️ 重要提醒：价格可能创新高")
    plan.append("")
    plan.append("**当前高点不一定是最终最高点！**价格完全有可能突破之前的高点继续上涨。")
    plan.append("")
    plan.append("**可能创新高的信号**:")
    if pattern_analysis['break_high_signals']:
        for signal in pattern_analysis['break_high_signals']:
            plan.append(f"  - {signal}")
    else:
        plan.append("  - 暂无明显创新高信号")
    plan.append("")
    
    plan.append("**不太可能创新高的信号**:")
    if pattern_analysis['no_break_high_signals']:
        for signal in pattern_analysis['no_break_high_signals']:
            plan.append(f"  - {signal}")
    else:
        plan.append("  - 暂无明显不创新高信号")
    plan.append("")
    
    plan.append("**综合判断**:")
    if pattern_analysis['may_break_high']:
        plan.append("  - ⚠️ **风险较高**：价格可能突破之前的高点，做空需谨慎")
        plan.append("  - 建议：等待价格**确认无法突破**后再做空，或使用**更小的仓位**")
    else:
        plan.append("  - ✓ **风险较低**：价格不太可能突破之前的高点")
        plan.append("  - 建议：可以按照计划执行，但仍需设置止损")
    plan.append("")
    
    if pattern_analysis['is_new_listing_pattern']:
        plan.append("**✓ 符合新币砸盘模式**")
        plan.append("")
        plan.append("**识别到的信号**:")
        for signal in pattern_analysis['signals']:
            plan.append(f"  - {signal}")
        plan.append("")
    else:
        plan.append("**⚠ 不完全符合新币砸盘模式，但可以观察**")
        plan.append("")
        if pattern_analysis['signals']:
            plan.append("**部分信号**:")
            for signal in pattern_analysis['signals']:
                plan.append(f"  - {signal}")
            plan.append("")
    
    plan.append("**关键数据**:")
    plan.append(f"  - 当前价格: ${current_price:.6f}")
    plan.append(f"  - 历史最高点: ${pattern_analysis['max_price']:.6f}")
    plan.append(f"  - 距离最高点: {((current_price - pattern_analysis['max_price']) / pattern_analysis['max_price'] * 100):.1f}%")
    plan.append(f"  - 从最高点跌幅: {pattern_analysis['drop_from_high_pct']:.1f}%")
    plan.append(f"  - 最高点涨幅: {pattern_analysis['max_price_change_pct']:.1f}%")
    plan.append(f"  - 成交量比率: {pattern_analysis['volume_ratio']:.2f}（<0.5表示萎缩）")
    plan.append(f"  - RSI: {pattern_analysis['rsi']:.1f}" if pattern_analysis['rsi'] else "  - RSI: 计算中")
    plan.append("")
    
    # 二、技术指标分析
    plan.append("## 二、技术指标分析")
    plan.append("")
    
    if ema_144 and ema_169:
        plan.append("**Vegas通道（EMA144/169）**:")
        plan.append(f"  - EMA144: ${ema_144:.6f}")
        plan.append(f"  - EMA169: ${ema_169:.6f}")
        if current_price > ema_169:
            plan.append("  → 价格在Vegas通道上方（偏多，但可能见顶）")
        elif current_price > ema_144:
            plan.append("  → 价格在Vegas通道内（震荡）")
        else:
            plan.append("  → 价格在Vegas通道下方（偏空）")
        plan.append("")
    
    if vwap:
        plan.append(f"**VWAP（15分钟）**: ${vwap:.6f}")
        if current_price > vwap:
            plan.append("  → 价格在VWAP上方（可能见顶）")
        else:
            plan.append("  → 价格在VWAP下方（偏空）")
        plan.append("")
    
    if rsi:
        plan.append(f"**RSI（15分钟）**: {rsi:.1f}")
        if rsi > 70:
            plan.append("  → 超买区域（做空信号）")
        elif rsi > 50:
            plan.append("  → 正常区域（观察）")
        else:
            plan.append("  → 正常或超卖区域")
        plan.append("")
    
    # 三、做空交易计划
    plan.append("## 三、做空交易计划")
    plan.append("")
    
    # 策略说明
    plan.append("### 策略说明")
    plan.append("")
    plan.append("**重要**：由于价格可能创新高，我们采用以下策略：")
    plan.append("")
    plan.append("1. **保守策略**：等待价格**确认无法突破**历史高点后再做空")
    plan.append("   - 价格接近历史高点但**未能突破**")
    plan.append("   - 出现**看跌K线信号**（长上影线、倒锤子线等）")
    plan.append("   - 成交量**放大后萎缩**")
    plan.append("   - RSI**从超买区域回落**")
    plan.append("")
    plan.append("2. **激进策略**：在历史高点附近做空（风险更高）")
    plan.append("   - 使用**更小的仓位**（0.5-1%）")
    plan.append("   - 设置**更紧的止损**（1-2%）")
    plan.append("   - 如果价格突破，**立即止损**")
    plan.append("")
    plan.append("3. **动态调整**：")
    plan.append("   - 如果价格**突破历史高点**，取消做空计划或等待新的高点")
    plan.append("   - 如果价格**在历史高点附近反复测试但无法突破**，这是做空的好机会")
    plan.append("   - 如果价格**远离历史高点**（>10%），做空风险降低")
    plan.append("")
    
    if not resistance:
        plan.append("**⚠ 未找到合适的阻力位，建议等待更好的入场机会**")
        plan.append("")
    else:
        # 入场位
        entry_price = resistance['price'] * 0.99  # 阻力位下方1%
        
        # 止损位
        stop_loss = resistance['price'] * 1.02  # 阻力位上方2%
        
        # 止盈位（基于新币砸盘特征，目标跌幅50-70%）
        take_profit_1 = current_price * 0.80  # 第一目标：20%跌幅
        take_profit_2 = current_price * 0.50  # 第二目标：50%跌幅（新币常见跌幅）
        take_profit_3 = current_price * 0.30  # 第三目标：70%跌幅（极端情况）
        
        # 计算盈亏比
        risk = stop_loss - entry_price
        reward_1 = entry_price - take_profit_1
        reward_2 = entry_price - take_profit_2
        reward_3 = entry_price - take_profit_3
        rr_ratio_1 = reward_1 / risk if risk > 0 else 0
        rr_ratio_2 = reward_2 / risk if risk > 0 else 0
        rr_ratio_3 = reward_3 / risk if risk > 0 else 0
        
        plan.append("### 做空方案：反弹到阻力位做空")
        plan.append("")
        plan.append("**适用时间级别**: 15分钟（主要）+ 1小时（确认）")
        plan.append("**计划有效期**: 7天（新币通常在上市后3-7天达到高点）")
        plan.append("")
        
        plan.append("**入场条件**（必须全部满足）:")
        plan.append(f"  - 价格反弹至: ${entry_price:.6f}（阻力位下方1%）")
        plan.append(f"  - **阻力位**: ${resistance['price']:.6f}（{resistance['description']}）")
        plan.append(f"  - **阻力位强度**: {resistance['strength']}/10")
        plan.append("  - **关键确认条件**（防止创新高）：")
        plan.append("    * ✅ 价格**接近但未能突破**历史最高点（必须）")
        plan.append("    * ✅ 价格在阻力位附近**受阻**（出现看跌K线信号）")
        plan.append("    * ✅ 15分钟K线出现**看跌信号**（长上影线、倒锤子线、吞没形态等）")
        plan.append("    * ✅ RSI从**超买区域回落**（>70后下降）")
        plan.append("    * ✅ 成交量**放大后开始萎缩**（确认阻力有效）")
        plan.append("    * ✅ 价格**多次测试**该阻力位但**未能突破**（至少2-3次）")
        plan.append("    * ✅ 价格**突破失败后立即回落**（确认顶部）")
        plan.append("")
        plan.append("  - **如果价格突破历史最高点**：")
        plan.append("    * ❌ **立即取消做空计划**")
        plan.append("    * 等待价格形成**新的高点**后再分析")
        plan.append("    * 或等待价格从新高点**回落20%以上**后再考虑做空")
        plan.append("")
        
        plan.append("**止损设置**:")
        plan.append(f"  - 止损位: ${stop_loss:.6f}（阻力位上方2%）")
        plan.append(f"  - 止损距离: ${risk:.6f} ({risk/entry_price*100:.2f}%)")
        plan.append("")
        
        plan.append("**止盈设置**（基于新币砸盘特征）:")
        plan.append(f"  - 第一目标: ${take_profit_1:.6f}（20%跌幅，止盈30%）")
        plan.append(f"  - 第二目标: ${take_profit_2:.6f}（50%跌幅，止盈40%）")
        plan.append(f"  - 第三目标: ${take_profit_3:.6f}（70%跌幅，止盈30%）")
        plan.append(f"  - 第一目标距离: ${reward_1:.6f} ({reward_1/entry_price*100:.2f}%)")
        plan.append(f"  - 第二目标距离: ${reward_2:.6f} ({reward_2/entry_price*100:.2f}%)")
        plan.append(f"  - 第三目标距离: ${reward_3:.6f} ({reward_3/entry_price*100:.2f}%)")
        plan.append("")
        
        plan.append(f"**盈亏比（第一目标）**: {rr_ratio_1:.2f}:1")
        plan.append(f"**盈亏比（第二目标）**: {rr_ratio_2:.2f}:1")
        plan.append(f"**盈亏比（第三目标）**: {rr_ratio_3:.2f}:1")
        if rr_ratio_1 >= 3:
            plan.append("  → ✓ 盈亏比优秀（≥3:1）")
        elif rr_ratio_1 >= 2:
            plan.append("  → ✓ 盈亏比良好（≥2:1）")
        else:
            plan.append("  → ⚠ 盈亏比较低，需要谨慎")
        plan.append("")
        
        plan.append("**仓位管理**:")
        plan.append("  - 风险：账户的**1-2%**（新币波动大，降低风险）")
        plan.append("  - 根据止损距离计算仓位大小")
        plan.append("  - 使用**逐仓模式**")
        plan.append("  - 建议**小仓位**，因为新币风险极高")
        plan.append("")
    
    # 四、新币砸盘策略检查清单
    plan.append("## 四、新币砸盘策略检查清单")
    plan.append("")
    plan.append("**入场前检查**:")
    plan.append("□ 1. 价格是否从高点回落超过20%")
    plan.append("□ 2. 成交量是否从峰值开始萎缩（比率<0.5）")
    plan.append("□ 3. RSI是否从超买区域回落（>70后下降）")
    plan.append("□ 4. 价格是否在阻力位附近受阻")
    plan.append("□ 5. 15分钟K线是否出现看跌信号")
    plan.append("□ 6. 是否在上市后3-7天内（通常达到高点的时间）")
    plan.append("□ 7. 价格是否突破新高后立即回落")
    plan.append("")
    
    plan.append("**风险管理检查**:")
    plan.append("□ 8. 已设置止损（必须，窄止损2-3%）")
    plan.append("□ 9. 已设置分批止盈（30%+40%+30%）")
    plan.append("□ 10. 仓位大小已计算（风险1-2%，新币降低风险）")
    plan.append("□ 11. 使用逐仓模式")
    plan.append("□ 12. 盈亏比≥2:1")
    plan.append("")
    
    # 五、重要风险提示
    plan.append("## 五、重要风险提示")
    plan.append("")
    plan.append("1. **新币风险极高**: 新币波动极大，可能快速反向运行，导致巨大亏损")
    plan.append("2. **流动性风险**: 新币流动性可能不足，注意滑点和无法平仓的风险")
    plan.append("3. **时间风险**: 计划有效期过后，市场条件可能已改变")
    plan.append("4. **仓位风险**: 严格控制仓位，单笔交易风险不超过账户的**1-2%**（比普通交易更低）")
    plan.append("5. **止损必须**: 必须设置止损，不要抱有侥幸心理")
    plan.append("6. **数据风险**: 新币数据可能不完整，技术指标可能不准确")
    plan.append("7. **情绪风险**: 避免FOMO情绪，理性分析市场")
    plan.append("")
    plan.append("**免责声明**: 本交易计划仅供参考，不构成投资建议。新币交易存在极高风险，可能导致本金全部损失。投资前请充分了解风险，谨慎决策。")
    plan.append("")
    plan.append("=" * 80)
    
    # 输出计划
    output = "\n".join(plan)
    try:
        print(output)
    except UnicodeEncodeError:
        # Windows控制台编码问题，直接保存文件
        pass
    
    # 保存到文件
    filename = f"RAVE_new_listing_short_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n交易计划已保存到: {filename}", file=sys.stderr)

if __name__ == '__main__':
    generate_short_plan()

