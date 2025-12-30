#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成LUMIA做多交易计划（结合De.交易系统和山寨币做多策略）
数据来源：Bitget交易所
时间框架：15分钟、1小时
"""

import requests
import sys
from datetime import datetime

def get_bitget_kline_data(symbol='LUMIAUSDT', timeframe='15m', limit=200):
    """从Bitget获取K线数据"""
    try:
        # 转换时间框架
        tf_map = {
            '15m': '15min',
            '1h': '1hour',
            '4h': '4hour',
            '1d': '1day'
        }
        interval = tf_map.get(timeframe, '15min')
        
        url = "https://api.bitget.com/api/spot/v1/market/candles"
        params = {
            'symbol': symbol,
            'granularity': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                klines_data = data['data']
                # Bitget返回的是从新到旧，需要反转
                klines_data.reverse()
                klines = []
                for k in klines_data:
                    # Bitget格式: [timestamp, open, close, high, low, volume]
                    klines.append({
                        'timestamp': int(k[0]) // 1000,  # 转换为秒
                        'open': float(k[1]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'close': float(k[2]),
                        'volume': float(k[5])
                    })
                return klines
            else:
                print(f"Bitget API返回错误: {data}", file=sys.stderr)
        else:
            print(f"Bitget API请求失败: {response.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"Bitget获取失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    return None

def get_current_price(symbol='LUMIAUSDT'):
    """获取当前价格"""
    try:
        # 尝试v2 API
        url = "https://api.bitget.com/api/v2/spot/market/ticker"
        params = {'symbol': symbol}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == '00000' and data.get('data'):
                return float(data['data']['last'])
        
        # 尝试v1 API
        url_v1 = "https://api.bitget.com/api/spot/v1/market/ticker"
        params_v1 = {'symbol': symbol}
        response_v1 = requests.get(url_v1, params=params_v1, timeout=10)
        if response_v1.status_code == 200:
            data_v1 = response_v1.json()
            if data_v1.get('code') == '00000' and data_v1.get('data'):
                return float(data_v1['data']['last'])
    except Exception as e:
        print(f"获取价格失败: {e}", file=sys.stderr)
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

def calculate_sma(prices, period):
    """计算SMA"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def calculate_vwap(klines):
    """计算VWAP"""
    if not klines:
        return None
    total_pv = 0
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

def identify_support_levels(klines, current_price, lookback=50):
    """识别支撑位（山寨币做多策略）"""
    if not klines or len(klines) < lookback:
        return []
    
    # 方法1: 历史低点
    lows = [k['low'] for k in klines[-lookback:]]
    sorted_lows = sorted(set(lows))[:5]
    support_levels = [l for l in sorted_lows if l < current_price * 1.05]  # 在当前价格附近5%以内
    
    # 方法2: EMA支撑
    closes = [k['close'] for k in klines]
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)
    if ema_20 and ema_20 < current_price * 1.05:
        support_levels.append(ema_20)
    if ema_50 and ema_50 < current_price * 1.05:
        support_levels.append(ema_50)
    
    # 方法3: VWAP支撑
    vwap = calculate_vwap(klines[-50:])
    if vwap and vwap < current_price * 1.05:
        support_levels.append(vwap)
    
    # 去重并排序
    support_levels = sorted(set(support_levels), reverse=True)
    return support_levels[:3]  # 返回前3个最强的支撑位

def check_breakout_pattern(klines, current_price):
    """检查突破形态（山寨币常见做多信号）"""
    if len(klines) < 20:
        return False, None
    
    # 检查是否突破近期高点
    recent_highs = [k['high'] for k in klines[-20:]]
    recent_high = max(recent_highs)
    
    # 检查成交量是否放大
    recent_volumes = [k['volume'] for k in klines[-20:]]
    avg_volume = sum(recent_volumes[:-5]) / len(recent_volumes[:-5])
    current_volume = recent_volumes[-1]
    
    # 突破 + 放量 = 做多信号
    if current_price > recent_high * 0.98 and current_volume > avg_volume * 1.5:
        return True, {
            'breakout_level': recent_high,
            'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 0
        }
    
    return False, None

def check_uptrend(klines):
    """检查上升趋势（山寨币中线做多策略）"""
    if len(klines) < 50:
        return False, None
    
    closes = [k['close'] for k in klines]
    
    # 计算多个EMA
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)
    ema_144 = calculate_ema(closes, 144) if len(closes) >= 144 else None
    
    # 判断趋势
    is_uptrend = False
    trend_strength = 0
    
    if ema_20 and ema_50:
        if closes[-1] > ema_20 > ema_50:
            is_uptrend = True
            trend_strength = 1
        if ema_144 and closes[-1] > ema_20 > ema_50 > ema_144:
            trend_strength = 2
    
    return is_uptrend, {
        'ema_20': ema_20,
        'ema_50': ema_50,
        'ema_144': ema_144,
        'strength': trend_strength
    }

def analyze_long_opportunity(klines, timeframe_name, current_price):
    """分析做多机会"""
    if not klines or len(klines) < 50:
        return None
    
    closes = [k['close'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # 计算技术指标
    ema_144 = calculate_ema(closes, 144) if len(closes) >= 144 else None
    ema_169 = calculate_ema(closes, 169) if len(closes) >= 169 else None
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)
    vwap = calculate_vwap(klines[-100:])
    rsi = calculate_rsi(closes)
    
    # 识别支撑位
    support_levels = identify_support_levels(klines, current_price)
    
    # 检查突破形态
    is_breakout, breakout_info = check_breakout_pattern(klines, current_price)
    
    # 检查上升趋势
    is_uptrend, trend_info = check_uptrend(klines)
    
    # 生成做多信号
    signals = []
    
    # 1. 趋势跟随做多（中线策略）
    if is_uptrend and trend_info['strength'] >= 1:
        # 在EMA20附近做多
        entry = trend_info['ema_20'] * 0.995 if trend_info['ema_20'] else current_price * 0.98
        stop_loss = trend_info['ema_50'] * 0.97 if trend_info['ema_50'] else entry * 0.95
        take_profit_1 = current_price * 1.05
        take_profit_2 = current_price * 1.10
        
        signals.append({
            'type': 'trend_follow',
            'strength': 'strong' if trend_info['strength'] == 2 else 'medium',
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'reason': f'上升趋势确认，EMA20({trend_info["ema_20"]:.4f})附近做多'
        })
    
    # 2. 支撑位做多（短线策略）
    if support_levels:
        nearest_support = max(support_levels)
        if current_price < nearest_support * 1.03:  # 价格在支撑位上方3%以内
            entry = nearest_support * 1.01
            stop_loss = nearest_support * 0.97
            take_profit_1 = current_price * 1.05
            take_profit_2 = current_price * 1.10
            
            signals.append({
                'type': 'support_bounce',
                'strength': 'medium',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'reason': f'价格接近支撑位{nearest_support:.4f}，可能反弹'
            })
    
    # 3. 突破做多（山寨币常见策略）
    if is_breakout:
        entry = current_price * 1.01
        stop_loss = breakout_info['breakout_level'] * 0.98
        take_profit_1 = current_price * 1.10
        take_profit_2 = current_price * 1.20
        
        signals.append({
            'type': 'breakout',
            'strength': 'strong',
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'reason': f'突破近期高点{breakout_info["breakout_level"]:.4f}，成交量放大{breakout_info["volume_ratio"]:.1f}倍'
        })
    
    # 4. Vegas通道做多（De.系统）
    if ema_144 and ema_169:
        if current_price > ema_144 and current_price < ema_169:
            # 价格在Vegas通道内，回调到通道下沿做多
            entry = ema_144 * 1.005
            stop_loss = ema_144 * 0.98
            take_profit_1 = ema_169 * 1.01
            take_profit_2 = current_price * 1.05
            
            signals.append({
                'type': 'vegas_channel',
                'strength': 'medium',
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit_1': take_profit_1,
                'take_profit_2': take_profit_2,
                'reason': f'价格在Vegas通道内，回调到EMA144({ema_144:.4f})做多'
            })
    
    # 5. VWAP做多（De.系统）
    if vwap and current_price < vwap * 1.02:
        entry = current_price * 0.998
        stop_loss = vwap * 0.97
        take_profit_1 = vwap * 1.02
        take_profit_2 = vwap * 1.05
        
        signals.append({
            'type': 'vwap_bounce',
            'strength': 'weak',
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'reason': f'价格在VWAP下方，可能反弹到VWAP({vwap:.4f})'
        })
    
    return {
        'timeframe': timeframe_name,
        'current_price': current_price,
        'ema_144': ema_144,
        'ema_169': ema_169,
        'ema_20': ema_20,
        'ema_50': ema_50,
        'vwap': vwap,
        'rsi': rsi,
        'support_levels': support_levels,
        'is_breakout': is_breakout,
        'breakout_info': breakout_info,
        'is_uptrend': is_uptrend,
        'trend_info': trend_info,
        'signals': signals
    }

def get_gateio_kline_data(symbol='LUMIA_USDT', timeframe='15m', limit=200):
    """从Gate.io获取K线数据（备用）"""
    try:
        tf_map = {'15m': '15m', '1h': '1h', '4h': '4h', '1d': '1d'}
        interval = tf_map.get(timeframe, '15m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': symbol,
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
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
                return klines
    except:
        pass
    return None

def get_gateio_price(symbol='LUMIA_USDT'):
    """从Gate.io获取价格（备用）"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': symbol}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['last'])
    except:
        pass
    return None

def generate_trading_plan():
    """生成交易计划"""
    print("正在获取LUMIA市场数据...", file=sys.stderr)
    
    # 优先使用Bitget，失败则使用Gate.io
    current_price = None
    klines_15m = None
    klines_1h = None
    
    # 尝试Bitget
    symbols_bitget = ['LUMIAUSDT', 'LUMIA_USDT']
    for symbol in symbols_bitget:
        print(f"尝试Bitget交易对: {symbol}", file=sys.stderr)
        current_price = get_current_price(symbol)
        klines_15m = get_bitget_kline_data(symbol, '15m', 200)
        klines_1h = get_bitget_kline_data(symbol, '1h', 200)
        if current_price and klines_15m and klines_1h:
            print(f"成功从Bitget获取数据: {symbol}", file=sys.stderr)
            break
    
    # 如果Bitget失败，尝试Gate.io
    if not current_price or not klines_15m or not klines_1h:
        print("Bitget获取失败，尝试Gate.io...", file=sys.stderr)
        symbols_gateio = ['LUMIA_USDT']
        for symbol in symbols_gateio:
            current_price = get_gateio_price(symbol)
            klines_15m = get_gateio_kline_data(symbol, '15m', 200)
            klines_1h = get_gateio_kline_data(symbol, '1h', 200)
            if current_price and klines_15m and klines_1h:
                print(f"成功从Gate.io获取数据: {symbol}", file=sys.stderr)
                break
    
    if not current_price or not klines_15m or not klines_1h:
        print("无法获取市场数据", file=sys.stderr)
        print("提示: 请确认LUMIA在Bitget或Gate.io上的交易对名称", file=sys.stderr)
        return
    
    # 使用最新K线价格
    if abs(klines_1h[-1]['close'] - current_price) / current_price > 0.1:
        current_price = klines_1h[-1]['close']
    
    # 分析各时间框架
    analysis_15m = analyze_long_opportunity(klines_15m, '15分钟', current_price)
    analysis_1h = analyze_long_opportunity(klines_1h, '1小时', current_price)
    
    # 判断数据来源
    data_source = "Gate.io"  # 默认
    if current_price and klines_15m and klines_1h:
        # 检查是否从Bitget获取（通过价格特征判断，或添加标志）
        # 这里简化处理，实际应该添加标志
        pass
    
    # 生成交易计划
    plan = []
    plan.append("# LUMIA 做多交易计划（De.交易系统 + 山寨币策略）")
    plan.append("")
    plan.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    plan.append(f"**当前价格**: ${current_price:.6f}  ")
    plan.append("**数据来源**: Bitget交易所（优先）/ Gate.io（备用）  ")
    plan.append("")
    
    # 一、15分钟做多信号（简明）
    plan.append("## 一、15分钟做多信号")
    plan.append("")
    
    if analysis_15m:
        if analysis_15m['signals']:
            # 选择最强的信号
            best_signal = max(analysis_15m['signals'], key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
            strength = "强" if best_signal['strength'] == 'strong' else "中" if best_signal['strength'] == 'medium' else "弱"
            
            plan.append(f"**做多** ({strength})")
            plan.append(f"入场: ${best_signal['entry']:.6f} | 止损: ${best_signal['stop_loss']:.6f}")
            plan.append(f"止盈: ${best_signal['take_profit_1']:.6f} (50%) / ${best_signal['take_profit_2']:.6f} (50%)")
            plan.append(f"理由: {best_signal['reason']}")
            plan.append("")
        else:
            plan.append("无明确做多信号，建议观望")
            plan.append("")
    
    # 二、1小时做多信号（简明）
    plan.append("## 二、1小时做多信号")
    plan.append("")
    
    if analysis_1h:
        if analysis_1h['signals']:
            # 选择最强的信号
            best_signal = max(analysis_1h['signals'], key=lambda x: 3 if x['strength'] == 'strong' else 2 if x['strength'] == 'medium' else 1)
            strength = "强" if best_signal['strength'] == 'strong' else "中" if best_signal['strength'] == 'medium' else "弱"
            
            plan.append(f"**做多** ({strength})")
            plan.append(f"入场: ${best_signal['entry']:.6f} | 止损: ${best_signal['stop_loss']:.6f}")
            plan.append(f"止盈: ${best_signal['take_profit_1']:.6f} (50%) / ${best_signal['take_profit_2']:.6f} (50%)")
            plan.append(f"理由: {best_signal['reason']}")
            plan.append("")
        else:
            plan.append("无明确做多信号，建议观望")
            plan.append("")
    
    # 三、详细技术分析说明
    plan.append("---")
    plan.append("")
    plan.append("## 三、详细技术分析说明")
    plan.append("")
    plan.append("### 3.1 数据来源")
    plan.append("")
    plan.append("**Bitget API**:")
    plan.append("- API端点: `https://api.bitget.com/api/spot/v1/market/candles`")
    plan.append("- 交易对: `LUMIAUSDT`")
    plan.append("- 时间框架: `15min` (15分钟), `1hour` (1小时)")
    plan.append("- 数据量: 200根K线")
    plan.append("")
    plan.append("### 3.2 山寨币做多策略（结合De.系统）")
    plan.append("")
    plan.append("**策略1: 趋势跟随做多（中线策略）**")
    plan.append("- 识别上升趋势：价格 > EMA20 > EMA50 > EMA144")
    plan.append("- 入场：价格回调到EMA20附近")
    plan.append("- 止损：EMA50下方2-3%")
    plan.append("- 止盈：目标5-10%")
    plan.append("- 适用：中线持仓（1-7天）")
    plan.append("")
    plan.append("**策略2: 支撑位反弹做多（短线策略）**")
    plan.append("- 识别支撑位：历史低点、EMA20/50、VWAP")
    plan.append("- 入场：价格接近支撑位（支撑位上方1-3%）")
    plan.append("- 止损：支撑位下方3%")
    plan.append("- 止盈：目标5-10%")
    plan.append("- 适用：短线交易（几小时到1天）")
    plan.append("")
    plan.append("**策略3: 突破做多（山寨币常见策略）**")
    plan.append("- 识别突破：价格突破近期高点 + 成交量放大1.5倍以上")
    plan.append("- 入场：突破后回调1-2%")
    plan.append("- 止损：突破位下方2%")
    plan.append("- 止盈：目标10-20%")
    plan.append("- 适用：短线/中线（1-3天）")
    plan.append("")
    plan.append("**策略4: Vegas通道做多（De.系统）**")
    plan.append("- 识别：价格在EMA144/169通道内")
    plan.append("- 入场：回调到EMA144（通道下沿）")
    plan.append("- 止损：EMA144下方2%")
    plan.append("- 止盈：EMA169（通道上沿）或更高")
    plan.append("- 适用：短线交易（几小时）")
    plan.append("")
    plan.append("**策略5: VWAP反弹做多（De.系统）**")
    plan.append("- 识别：价格在VWAP下方")
    plan.append("- 入场：价格接近VWAP")
    plan.append("- 止损：VWAP下方3%")
    plan.append("- 止盈：VWAP上方2-5%")
    plan.append("- 适用：短线交易（几小时）")
    plan.append("")
    plan.append("### 3.3 技术指标说明")
    plan.append("")
    plan.append("**EMA (指数移动平均线)**:")
    plan.append("- EMA20: 短期趋势，支撑/阻力")
    plan.append("- EMA50: 中期趋势，支撑/阻力")
    plan.append("- EMA144/169: Vegas通道，De.系统核心指标")
    plan.append("")
    plan.append("**VWAP (成交量加权平均价)**:")
    plan.append("- 代表市场平均成本")
    plan.append("- 价格在VWAP上方 = VWAP作为支撑")
    plan.append("- 价格在VWAP下方 = VWAP作为阻力")
    plan.append("")
    plan.append("**RSI (相对强弱指标)**:")
    plan.append("- RSI > 70: 超买，可能回调")
    plan.append("- RSI < 30: 超卖，可能反弹")
    plan.append("- RSI 30-70: 正常区域")
    plan.append("")
    plan.append("**支撑位识别方法**:")
    plan.append("1. 历史低点（最近50根K线）")
    plan.append("2. EMA20/50（动态支撑）")
    plan.append("3. VWAP（成交量加权支撑）")
    plan.append("")
    plan.append("### 3.4 信号优先级")
    plan.append("")
    plan.append("**优先级排序**:")
    plan.append("1. **突破做多** (最强): 突破 + 放量，山寨币常见暴涨信号")
    plan.append("2. **趋势跟随做多** (强): 上升趋势确认，EMA排列良好")
    plan.append("3. **Vegas通道做多** (中等): De.系统核心策略")
    plan.append("4. **支撑位反弹做多** (中等): 价格接近支撑位")
    plan.append("5. **VWAP反弹做多** (弱): 价格在VWAP下方")
    plan.append("")
    plan.append("### 3.5 15分钟级别详细分析")
    plan.append("")
    if analysis_15m:
        plan.append(f"**当前价格**: ${analysis_15m['current_price']:.6f}")
        plan.append("")
        if analysis_15m['ema_144'] and analysis_15m['ema_169']:
            plan.append(f"**Vegas通道**:")
            plan.append(f"  - EMA144: ${analysis_15m['ema_144']:.6f}")
            plan.append(f"  - EMA169: ${analysis_15m['ema_169']:.6f}")
            if analysis_15m['current_price'] > analysis_15m['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif analysis_15m['current_price'] < analysis_15m['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
            plan.append("")
        if analysis_15m['ema_20']:
            plan.append(f"**EMA20**: ${analysis_15m['ema_20']:.6f}")
            plan.append("")
        if analysis_15m['vwap']:
            plan.append(f"**VWAP**: ${analysis_15m['vwap']:.6f}")
            if analysis_15m['current_price'] > analysis_15m['vwap']:
                plan.append("  → 价格在VWAP上方，VWAP作为支撑")
            else:
                plan.append("  → 价格在VWAP下方，VWAP作为阻力")
            plan.append("")
        if analysis_15m['rsi']:
            plan.append(f"**RSI**: {analysis_15m['rsi']:.1f}")
            if analysis_15m['rsi'] > 70:
                plan.append("  → 超买区域，可能回调")
            elif analysis_15m['rsi'] < 30:
                plan.append("  → 超卖区域，可能反弹")
            else:
                plan.append("  → 正常区域")
            plan.append("")
        if analysis_15m['support_levels']:
            plan.append("**支撑位**:")
            for s in analysis_15m['support_levels']:
                plan.append(f"  - ${s:.6f}")
            plan.append("")
        if analysis_15m['is_breakout']:
            plan.append(f"**突破信号**: ✅ 已突破近期高点")
            plan.append(f"  - 突破位: ${analysis_15m['breakout_info']['breakout_level']:.6f}")
            plan.append(f"  - 成交量放大: {analysis_15m['breakout_info']['volume_ratio']:.1f}倍")
            plan.append("")
        if analysis_15m['is_uptrend']:
            plan.append(f"**上升趋势**: ✅ 已确认")
            plan.append(f"  - 趋势强度: {analysis_15m['trend_info']['strength']}级")
            plan.append("")
    
    plan.append("### 3.6 1小时级别详细分析")
    plan.append("")
    if analysis_1h:
        plan.append(f"**当前价格**: ${analysis_1h['current_price']:.6f}")
        plan.append("")
        if analysis_1h['ema_144'] and analysis_1h['ema_169']:
            plan.append(f"**Vegas通道**:")
            plan.append(f"  - EMA144: ${analysis_1h['ema_144']:.6f}")
            plan.append(f"  - EMA169: ${analysis_1h['ema_169']:.6f}")
            if analysis_1h['current_price'] > analysis_1h['ema_169']:
                plan.append("  → 价格在通道上方，偏多")
            elif analysis_1h['current_price'] < analysis_1h['ema_144']:
                plan.append("  → 价格在通道下方，偏空")
            else:
                plan.append("  → 价格在通道内，震荡")
            plan.append("")
        if analysis_1h['ema_20']:
            plan.append(f"**EMA20**: ${analysis_1h['ema_20']:.6f}")
            plan.append("")
        if analysis_1h['vwap']:
            plan.append(f"**VWAP**: ${analysis_1h['vwap']:.6f}")
            if analysis_1h['current_price'] > analysis_1h['vwap']:
                plan.append("  → 价格在VWAP上方，VWAP作为支撑")
            else:
                plan.append("  → 价格在VWAP下方，VWAP作为阻力")
            plan.append("")
        if analysis_1h['rsi']:
            plan.append(f"**RSI**: {analysis_1h['rsi']:.1f}")
            if analysis_1h['rsi'] > 70:
                plan.append("  → 超买区域，可能回调")
            elif analysis_1h['rsi'] < 30:
                plan.append("  → 超卖区域，可能反弹")
            else:
                plan.append("  → 正常区域")
            plan.append("")
        if analysis_1h['support_levels']:
            plan.append("**支撑位**:")
            for s in analysis_1h['support_levels']:
                plan.append(f"  - ${s:.6f}")
            plan.append("")
        if analysis_1h['is_breakout']:
            plan.append(f"**突破信号**: ✅ 已突破近期高点")
            plan.append(f"  - 突破位: ${analysis_1h['breakout_info']['breakout_level']:.6f}")
            plan.append(f"  - 成交量放大: {analysis_1h['breakout_info']['volume_ratio']:.1f}倍")
            plan.append("")
        if analysis_1h['is_uptrend']:
            plan.append(f"**上升趋势**: ✅ 已确认")
            plan.append(f"  - 趋势强度: {analysis_1h['trend_info']['strength']}级")
            plan.append("")
    
    # 四、交易执行检查清单
    plan.append("## 四、交易执行检查清单")
    plan.append("")
    plan.append("**入场前**:")
    plan.append("□ 是否确认上升趋势？（EMA排列：价格 > EMA20 > EMA50）")
    plan.append("□ 是否有突破信号？（突破 + 放量）")
    plan.append("□ 价格是否接近支撑位？")
    plan.append("□ RSI是否在合理区域？（<70，避免超买）")
    plan.append("□ 多时间框架是否确认？（15分钟 + 1小时）")
    plan.append("")
    plan.append("**风险管理**:")
    plan.append("□ 已设置止损（支撑位下方3-5%）")
    plan.append("□ 已设置分批止盈（50%+50%）")
    plan.append("□ 仓位大小已计算（风险2-3%）")
    plan.append("□ 盈亏比≥2:1（目标5-10%，止损3-5%）")
    plan.append("□ 山寨币波动大，建议使用较小仓位")
    plan.append("")
    
    plan.append("---")
    plan.append("")
    plan.append("**免责声明**: 本交易计划基于De.交易系统和山寨币做多策略自动生成，仅供参考。山寨币波动大，风险高，请谨慎交易。")
    
    # 输出计划
    output = "\n".join(plan)
    try:
        print(output)
    except UnicodeEncodeError:
        pass
    
    # 保存到文件
    filename = f"LUMIA_long_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n交易计划已保存到: {filename}", file=sys.stderr)

if __name__ == '__main__':
    generate_trading_plan()

