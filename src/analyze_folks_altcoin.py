#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析FOLKS（或山寨币）4小时和1天级别走势
结合De.交易系统和山寨币一般走势特征
"""

import requests
import sys
from datetime import datetime

def get_kline_gateio(symbol='FOLKS', timeframe='4h', limit=200):
    """从Gate.io获取K线数据"""
    try:
        tf_map = {
            '4h': '4h',
            '1d': '1d'
        }
        interval = tf_map.get(timeframe, '4h')
        
        # 尝试多种交易对格式
        pairs = [f'{symbol}_USDT', f'{symbol}USDT']
        
        for pair in pairs:
            url = "https://api.gateio.ws/api/v4/spot/candlesticks"
            params = {
                'currency_pair': pair,
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
                    return klines, pair
    except Exception as e:
        print(f"Gate.io获取失败: {e}", file=sys.stderr)
    return None, None

def get_kline_bitget(symbol='FOLKS', timeframe='4h', limit=200):
    """从Bitget获取K线数据"""
    try:
        tf_map = {
            '4h': '4hour',
            '1d': '1day'
        }
        interval = tf_map.get(timeframe, '4hour')
        
        # 尝试多种交易对格式
        symbols = [f'{symbol}USDT', f'{symbol}_USDT']
        
        for sym in symbols:
            url = "https://api.bitget.com/api/spot/v1/market/candles"
            params = {
                'symbol': sym,
                'granularity': interval,
                'limit': limit
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '00000' and data.get('data'):
                    klines_data = data['data']
                    klines_data.reverse()
                    klines = []
                    for k in klines_data:
                        klines.append({
                            'timestamp': int(k[0]) // 1000,
                            'open': float(k[1]),
                            'high': float(k[3]),
                            'low': float(k[4]),
                            'close': float(k[2]),
                            'volume': float(k[5])
                        })
                    return klines, sym
    except Exception as e:
        print(f"Bitget获取失败: {e}", file=sys.stderr)
    return None, None

def get_current_price(symbol='FOLKS'):
    """获取当前价格"""
    # 尝试Gate.io
    pairs = [f'{symbol}_USDT', f'{symbol}USDT']
    for pair in pairs:
        try:
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            params = {'currency_pair': pair}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    return float(data[0]['last']), pair, 'gateio'
        except:
            pass
    
    # 尝试Bitget
    symbols = [f'{symbol}USDT', f'{symbol}_USDT']
    for sym in symbols:
        try:
            url = "https://api.bitget.com/api/v2/spot/market/ticker"
            params = {'symbol': sym}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '00000' and data.get('data'):
                    return float(data['data']['last']), sym, 'bitget'
        except:
            pass
    
    return None, None, None

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

def analyze_trend(klines):
    """分析趋势"""
    if not klines or len(klines) < 20:
        return None
    
    closes = [k['close'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    # 计算均线
    sma_20 = calculate_sma(closes, 20)
    sma_50 = calculate_sma(closes, 50)
    ema_20 = calculate_ema(closes, 20)
    ema_50 = calculate_ema(closes, 50)
    
    # 计算RSI
    rsi = calculate_rsi(closes)
    
    # 趋势判断
    current_price = closes[-1]
    price_20_ago = closes[-20] if len(closes) >= 20 else closes[0]
    price_change_pct = ((current_price - price_20_ago) / price_20_ago) * 100
    
    # 判断趋势
    if sma_20 and sma_50:
        if current_price > sma_20 > sma_50:
            trend = 'uptrend'
        elif current_price < sma_20 < sma_50:
            trend = 'downtrend'
        else:
            trend = 'sideways'
    else:
        if price_change_pct > 5:
            trend = 'uptrend'
        elif price_change_pct < -5:
            trend = 'downtrend'
        else:
            trend = 'sideways'
    
    # 波动率
    recent_high = max(highs[-20:])
    recent_low = min(lows[-20:])
    volatility_pct = ((recent_high - recent_low) / current_price) * 100
    
    # 成交量趋势
    avg_volume = sum(volumes[-20:]) / 20
    recent_volume = sum(volumes[-5:]) / 5
    volume_trend = 'increasing' if recent_volume > avg_volume * 1.2 else 'decreasing' if recent_volume < avg_volume * 0.8 else 'stable'
    
    return {
        'trend': trend,
        'price_change_pct': price_change_pct,
        'volatility_pct': volatility_pct,
        'sma_20': sma_20,
        'sma_50': sma_50,
        'ema_20': ema_20,
        'ema_50': ema_50,
        'rsi': rsi,
        'current_price': current_price,
        'volume_trend': volume_trend,
        'recent_high': recent_high,
        'recent_low': recent_low
    }

def identify_support_resistance(klines):
    """识别支撑阻力位"""
    if not klines or len(klines) < 50:
        return {'support': [], 'resistance': []}
    
    highs = [k['high'] for k in klines[-50:]]
    lows = [k['low'] for k in klines[-50:]]
    
    sorted_highs = sorted(set(highs), reverse=True)[:3]
    sorted_lows = sorted(set(lows))[:3]
    
    current_price = klines[-1]['close']
    
    support = [l for l in sorted_lows if l < current_price]
    resistance = [h for h in sorted_highs if h > current_price]
    
    return {
        'support': support[:3],
        'resistance': resistance[:3]
    }

def analyze_altcoin_patterns(klines_4h, klines_1d):
    """分析山寨币常见走势模式"""
    patterns = []
    
    if not klines_4h or not klines_1d:
        return patterns
    
    closes_4h = [k['close'] for k in klines_4h]
    closes_1d = [k['close'] for k in klines_1d]
    volumes_4h = [k['volume'] for k in klines_4h]
    volumes_1d = [k['volume'] for k in klines_1d]
    
    # 1. 检查是否在底部区域（山寨币常见反弹点）
    if len(closes_1d) >= 30:
        recent_low_1d = min([k['low'] for k in klines_1d[-30:]])
        current_price_1d = closes_1d[-1]
        low_distance_pct = ((current_price_1d - recent_low_1d) / recent_low_1d) * 100
        
        if low_distance_pct < 10:
            patterns.append({
                'type': 'bottom_area',
                'description': '价格接近近期低点，可能形成底部',
                'strength': 'medium'
            })
    
    # 2. 检查突破形态（山寨币常见暴涨信号）
    if len(closes_4h) >= 20:
        recent_high_4h = max([k['high'] for k in klines_4h[-20:]])
        current_price_4h = closes_4h[-1]
        recent_volume_4h = sum(volumes_4h[-3:]) / 3
        avg_volume_4h = sum(volumes_4h[-20:]) / 20
        
        if current_price_4h > recent_high_4h * 0.98 and recent_volume_4h > avg_volume_4h * 1.5:
            patterns.append({
                'type': 'breakout',
                'description': '价格接近近期高点且成交量放大，可能突破',
                'strength': 'strong'
            })
    
    # 3. 检查下跌趋势（山寨币常见回调）
    if len(closes_1d) >= 10:
        price_change_10d = ((closes_1d[-1] - closes_1d[-10]) / closes_1d[-10]) * 100
        if price_change_10d < -20:
            patterns.append({
                'type': 'deep_correction',
                'description': '近期跌幅较大，可能超跌反弹',
                'strength': 'medium'
            })
    
    # 4. 检查横盘整理（山寨币常见形态）
    if len(closes_4h) >= 20:
        recent_high_4h = max([k['high'] for k in klines_4h[-20:]])
        recent_low_4h = min([k['low'] for k in klines_4h[-20:]])
        range_pct = ((recent_high_4h - recent_low_4h) / closes_4h[-1]) * 100
        
        if range_pct < 15:
            patterns.append({
                'type': 'consolidation',
                'description': '价格在窄幅区间震荡，等待方向选择',
                'strength': 'weak'
            })
    
    return patterns

def generate_analysis_report(symbol='FOLKS'):
    """生成分析报告"""
    print(f"正在分析 {symbol} 的4小时和1天级别走势...", file=sys.stderr)
    
    # 获取数据
    klines_4h, pair_4h = get_kline_gateio(symbol, '4h', 200)
    if not klines_4h:
        klines_4h, pair_4h = get_kline_bitget(symbol, '4h', 200)
    
    klines_1d, pair_1d = get_kline_gateio(symbol, '1d', 200)
    if not klines_1d:
        klines_1d, pair_1d = get_kline_bitget(symbol, '1d', 200)
    
    current_price, price_pair, exchange = get_current_price(symbol)
    
    if not klines_4h or not klines_1d:
        print(f"无法获取 {symbol} 的数据，请确认币种名称是否正确", file=sys.stderr)
        print(f"尝试的交易对: {symbol}_USDT, {symbol}USDT", file=sys.stderr)
        return
    
    # 使用最新K线价格
    if not current_price:
        current_price = klines_1d[-1]['close']
    
    # 分析
    analysis_4h = analyze_trend(klines_4h)
    analysis_1d = analyze_trend(klines_1d)
    sr_4h = identify_support_resistance(klines_4h)
    sr_1d = identify_support_resistance(klines_1d)
    patterns = analyze_altcoin_patterns(klines_4h, klines_1d)
    
    # 生成报告
    report = []
    report.append(f"# {symbol} 4小时/1天级别走势分析（山寨币策略）")
    report.append("")
    report.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
    report.append(f"**当前价格**: ${current_price:,.6f}  ")
    report.append(f"**数据来源**: {exchange or 'Gate.io/Bitget'} ({price_pair or pair_1d})  ")
    report.append("")
    
    # 一、4小时级别分析
    report.append("## 一、4小时级别分析")
    report.append("")
    
    if analysis_4h:
        trend_cn = {'uptrend': '上升趋势', 'downtrend': '下降趋势', 'sideways': '横盘震荡'}[analysis_4h['trend']]
        report.append(f"**趋势**: {trend_cn}")
        report.append(f"**20周期涨跌幅**: {analysis_4h['price_change_pct']:+.2f}%")
        report.append(f"**波动率**: {analysis_4h['volatility_pct']:.2f}%")
        report.append("")
        
        if analysis_4h['sma_20'] and analysis_4h['sma_50']:
            report.append(f"**均线**:")
            report.append(f"  - SMA20: ${analysis_4h['sma_20']:,.6f}")
            report.append(f"  - SMA50: ${analysis_4h['sma_50']:,.6f}")
            if analysis_4h['current_price'] > analysis_4h['sma_20']:
                report.append("  → 价格在SMA20上方，偏多")
            else:
                report.append("  → 价格在SMA20下方，偏空")
            report.append("")
        
        if analysis_4h['rsi']:
            report.append(f"**RSI**: {analysis_4h['rsi']:.1f}")
            if analysis_4h['rsi'] > 70:
                report.append("  → 超买区域，可能回调")
            elif analysis_4h['rsi'] < 30:
                report.append("  → 超卖区域，可能反弹")
            else:
                report.append("  → 正常区域")
            report.append("")
        
        report.append(f"**成交量趋势**: {analysis_4h['volume_trend']}")
        report.append("")
        
        if sr_4h['support']:
            report.append("**支撑位**:")
            for i, sup in enumerate(sr_4h['support'][:3], 1):
                report.append(f"  - 支撑{i}: ${sup:,.6f}")
            report.append("")
        
        if sr_4h['resistance']:
            report.append("**阻力位**:")
            for i, res in enumerate(sr_4h['resistance'][:3], 1):
                report.append(f"  - 阻力{i}: ${res:,.6f}")
            report.append("")
    
    # 二、1天级别分析
    report.append("## 二、1天级别分析")
    report.append("")
    
    if analysis_1d:
        trend_cn = {'uptrend': '上升趋势', 'downtrend': '下降趋势', 'sideways': '横盘震荡'}[analysis_1d['trend']]
        report.append(f"**趋势**: {trend_cn}")
        report.append(f"**20周期涨跌幅**: {analysis_1d['price_change_pct']:+.2f}%")
        report.append(f"**波动率**: {analysis_1d['volatility_pct']:.2f}%")
        report.append("")
        
        if analysis_1d['sma_20'] and analysis_1d['sma_50']:
            report.append(f"**均线**:")
            report.append(f"  - SMA20: ${analysis_1d['sma_20']:,.6f}")
            report.append(f"  - SMA50: ${analysis_1d['sma_50']:,.6f}")
            if analysis_1d['current_price'] > analysis_1d['sma_20']:
                report.append("  → 价格在SMA20上方，偏多")
            else:
                report.append("  → 价格在SMA20下方，偏空")
            report.append("")
        
        if analysis_1d['rsi']:
            report.append(f"**RSI**: {analysis_1d['rsi']:.1f}")
            report.append("")
        
        if sr_1d['support']:
            report.append("**支撑位**:")
            for i, sup in enumerate(sr_1d['support'][:3], 1):
                report.append(f"  - 支撑{i}: ${sup:,.6f}")
            report.append("")
        
        if sr_1d['resistance']:
            report.append("**阻力位**:")
            for i, res in enumerate(sr_1d['resistance'][:3], 1):
                report.append(f"  - 阻力{i}: ${res:,.6f}")
            report.append("")
    
    # 三、山寨币走势模式识别
    report.append("## 三、山寨币走势模式识别")
    report.append("")
    
    if patterns:
        for pattern in patterns:
            strength_cn = {'strong': '强', 'medium': '中', 'weak': '弱'}[pattern['strength']]
            report.append(f"**{pattern['type']}** ({strength_cn}): {pattern['description']}")
            report.append("")
    else:
        report.append("未识别到明显的山寨币走势模式")
        report.append("")
    
    # 四、交易建议
    report.append("## 四、交易建议（基于De.交易系统 + 山寨币策略）")
    report.append("")
    
    # 综合判断
    if analysis_4h and analysis_1d:
        # 多空判断
        if analysis_1d['trend'] == 'uptrend' and analysis_4h['trend'] == 'uptrend':
            report.append("**整体判断**: 多时间框架均显示上升趋势，偏多")
            report.append("")
            report.append("**做多建议**:")
            report.append("1. **入场时机**:")
            if sr_4h['support']:
                report.append(f"   - 回调到支撑位附近: ${sr_4h['support'][0]:,.6f}")
            if analysis_4h['sma_20']:
                report.append(f"   - 回调到SMA20附近: ${analysis_4h['sma_20']:,.6f}")
            report.append("2. **止损**: 设置在支撑位下方2-3%")
            if sr_4h['resistance']:
                report.append(f"3. **止盈**: 第一目标 ${sr_4h['resistance'][0]:,.6f}，第二目标 ${sr_4h['resistance'][1] if len(sr_4h['resistance']) > 1 else sr_4h['resistance'][0]:,.6f}")
            report.append("")
        
        elif analysis_1d['trend'] == 'downtrend' and analysis_4h['trend'] == 'downtrend':
            report.append("**整体判断**: 多时间框架均显示下降趋势，偏空")
            report.append("")
            report.append("**做空建议**:")
            report.append("1. **入场时机**:")
            if sr_4h['resistance']:
                report.append(f"   - 反弹到阻力位附近: ${sr_4h['resistance'][0]:,.6f}")
            if analysis_4h['sma_20']:
                report.append(f"   - 反弹到SMA20附近: ${analysis_4h['sma_20']:,.6f}")
            report.append("2. **止损**: 设置在阻力位上方2-3%")
            if sr_4h['support']:
                report.append(f"3. **止盈**: 第一目标 ${sr_4h['support'][0]:,.6f}，第二目标 ${sr_4h['support'][1] if len(sr_4h['support']) > 1 else sr_4h['support'][0]:,.6f}")
            report.append("")
        
        else:
            report.append("**整体判断**: 多时间框架趋势不一致，建议观望或区间交易")
            report.append("")
            report.append("**区间交易建议**:")
            if sr_4h['support'] and sr_4h['resistance']:
                report.append(f"  - 支撑位: ${sr_4h['support'][0]:,.6f}（做多）")
                report.append(f"  - 阻力位: ${sr_4h['resistance'][0]:,.6f}（做空）")
            report.append("")
    
    # 五、山寨币特殊注意事项
    report.append("## 五、山寨币交易注意事项")
    report.append("")
    report.append("**风险提示**:")
    report.append("1. ✅ 山寨币波动大，建议使用较小仓位（风险2-3%）")
    report.append("2. ✅ 必须设置止损（窄止损2-3%）")
    report.append("3. ✅ 使用逐仓模式（isolated margin）")
    report.append("4. ✅ 关注成交量变化（放量突破更可靠）")
    report.append("5. ✅ 关注BTC走势（山寨币通常跟随BTC）")
    report.append("6. ✅ 避免在垃圾时间内交易（窄幅震荡）")
    report.append("")
    report.append("**山寨币常见走势**:")
    report.append("1. **底部反弹**: 价格接近近期低点，可能形成底部")
    report.append("2. **突破暴涨**: 价格突破阻力位且放量，可能快速上涨")
    report.append("3. **深度回调**: 大幅下跌后可能超跌反弹")
    report.append("4. **横盘整理**: 窄幅震荡，等待方向选择")
    report.append("")
    
    report.append("---")
    report.append("")
    report.append("**免责声明**: 本分析基于技术分析自动生成，仅供参考。交易有风险，入市需谨慎。")
    
    # 输出报告
    output = "\n".join(report)
    try:
        print(output)
    except UnicodeEncodeError:
        pass
    
    # 保存到文件
    filename = f"{symbol}_4h_1d_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f"\n分析报告已保存到: {filename}", file=sys.stderr)

if __name__ == '__main__':
    symbol = 'FOLKS'
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    generate_analysis_report(symbol)




