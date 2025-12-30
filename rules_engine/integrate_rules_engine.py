"""
将规则引擎集成到现有的交易信号生成系统
"""

import sys
from trading_rules_engine import analyze_with_rules_engine, TradingSignal
from generate_btc_multi_tf_plan import (
    get_btc_kline_gateio, get_btc_current_price,
    calculate_ema, calculate_vwap, calculate_rsi,
    identify_fvg, identify_support_resistance,
    detect_m_top, detect_w_bottom, check_ote_zone,
    check_garbage_time, check_vegas_breakthrough
)


def convert_to_rules_engine_format(analysis_result):
    """将现有分析结果转换为规则引擎格式"""
    market_data = {
        'current_price': analysis_result['current_price'],
        'ema_144': analysis_result.get('ema_144'),
        'ema_169': analysis_result.get('ema_169'),
        'vwap': analysis_result.get('vwap'),
        'rsi': analysis_result.get('rsi'),
        'timeframe': analysis_result.get('timeframe', '15m'),
        'timestamp': 0.0
    }
    
    # 转换技术形态
    patterns = []
    
    # FVG形态
    for fvg in analysis_result.get('fvgs', []):
        patterns.append({
            'pattern_type': f"fvg_{fvg['type']}",
            'is_valid': True,
            'price_level': fvg.get('price', fvg.get('high', 0)),
            'confidence': 0.8,
            'details': fvg
        })
    
    # M顶形态
    m_top = analysis_result.get('m_top')
    if m_top and m_top.get('is_valid'):
        patterns.append({
            'pattern_type': 'm_top',
            'is_valid': True,
            'price_level': m_top.get('neckline', 0),
            'confidence': 0.85,
            'details': m_top
        })
    
    # W底形态
    w_bottom = analysis_result.get('w_bottom')
    if w_bottom and w_bottom.get('is_valid'):
        patterns.append({
            'pattern_type': 'w_bottom',
            'is_valid': True,
            'price_level': w_bottom.get('neckline', 0),
            'confidence': 0.85,
            'details': w_bottom
        })
    
    # 支撑阻力
    sr = analysis_result.get('support_resistance', {})
    support_resistance = {
        'nearest_support': min(sr.get('support', [0])) if sr.get('support') else None,
        'nearest_resistance': min(sr.get('resistance', [float('inf')])) if sr.get('resistance') else None,
        'support_levels': sr.get('support', []),
        'resistance_levels': sr.get('resistance', [])
    }
    
    # OTE分析
    ote_analysis = analysis_result.get('ote_analysis')
    
    # 垃圾时间
    is_garbage_time = analysis_result.get('is_garbage_time', False)
    
    return market_data, patterns, support_resistance, ote_analysis, is_garbage_time


def generate_signals_with_rules_engine(timeframe='15m'):
    """使用规则引擎生成交易信号"""
    print(f"正在获取{timeframe} BTC市场数据...", file=sys.stderr)
    
    # 获取市场数据
    klines = get_btc_kline_gateio(timeframe, limit=200)
    if not klines:
        print(f"无法获取{timeframe} K线数据", file=sys.stderr)
        return []
    
    current_price = get_btc_current_price()
    if not current_price:
        current_price = klines[-1]['close']
    
    # 计算技术指标
    closes = [k['close'] for k in klines]
    ema_144 = calculate_ema(closes, 144) if len(closes) >= 144 else None
    ema_169 = calculate_ema(closes, 169) if len(closes) >= 169 else None
    vwap = calculate_vwap(klines[-100:])
    rsi = calculate_rsi(closes)
    
    # 识别技术形态
    fvgs = identify_fvg(klines[-50:])
    sr = identify_support_resistance(klines, current_price)
    m_top = detect_m_top(klines, lookback=50)
    w_bottom = detect_w_bottom(klines, lookback=50)
    ote_analysis = check_ote_zone(klines, current_price, lookback=50)
    is_garbage, _ = check_garbage_time(klines, current_price)
    
    # 构建分析结果
    analysis_result = {
        'timeframe': timeframe,
        'current_price': current_price,
        'ema_144': ema_144,
        'ema_169': ema_169,
        'vwap': vwap,
        'rsi': rsi,
        'fvgs': fvgs,
        'support_resistance': sr,
        'm_top': m_top,
        'w_bottom': w_bottom,
        'ote_analysis': ote_analysis,
        'is_garbage_time': is_garbage
    }
    
    # 转换为规则引擎格式
    market_data, patterns, support_resistance, ote_analysis, is_garbage_time = \
        convert_to_rules_engine_format(analysis_result)
    
    # 使用规则引擎分析
    signals = analyze_with_rules_engine(
        market_data=market_data,
        patterns=patterns,
        support_resistance=support_resistance,
        ote_analysis=ote_analysis,
        is_garbage_time=is_garbage_time
    )
    
    return signals, analysis_result


if __name__ == "__main__":
    # 测试规则引擎集成
    signals, analysis = generate_signals_with_rules_engine('15m')
    
    print(f"\n规则引擎生成了 {len(signals)} 个交易信号:")
    for signal in signals:
        print(f"\n{signal.rule_name} ({signal.signal_type.upper()}) - 优先级: {signal.priority}")
        print(f"  入场: ${signal.entry:.2f}")
        print(f"  止损: ${signal.stop_loss:.2f}")
        print(f"  止盈1: ${signal.take_profit_1:.2f} (50%)")
        print(f"  止盈2: ${signal.take_profit_2:.2f} (50%)")
        print(f"  理由: {signal.reason}")


