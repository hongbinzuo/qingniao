"""
分析当前BTC价格，应用De.的新规则：这把上去突破873可以进
"""

import sys
import io
from datetime import datetime

# 设置UTF-8编码输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
from generate_btc_multi_tf_plan import (
    get_btc_kline_gateio, get_btc_current_price,
    calculate_ema, calculate_vwap, calculate_rsi,
    identify_fvg, identify_support_resistance,
    detect_m_top, detect_w_bottom, check_ote_zone,
    check_garbage_time
)
# 使用简化版规则引擎（不依赖experta，兼容Python 3.12）
from simple_rules_engine import analyze_with_rules_engine, TradingSignal


def analyze_breakout_rule():
    """分析突破873规则"""
    print("=" * 60)
    print("De.规则分析：这把上去突破873可以进")
    print("=" * 60)
    
    # 获取当前价格
    print("\n正在获取BTC市场数据...")
    klines_15m = get_btc_kline_gateio('15m', limit=200)
    if not klines_15m:
        print("❌ 无法获取K线数据")
        return
    
    current_price = get_btc_current_price()
    if not current_price:
        current_price = klines_15m[-1]['close']
    
    print(f"\n当前BTC价格: ${current_price:,.2f}")
    
    # De.规则：这把上去突破873可以进
    breakout_level = 87300  # $87,300
    print(f"突破位: ${breakout_level:,.2f}")
    
    # 计算距离
    distance = current_price - breakout_level
    distance_pct = (distance / breakout_level) * 100
    
    print(f"\n价格分析:")
    print(f"  当前价格: ${current_price:,.2f}")
    print(f"  突破位: ${breakout_level:,.2f}")
    print(f"  距离: ${distance:,.2f} ({distance_pct:+.2f}%)")
    
    # 判断状态
    if current_price > breakout_level:
        print(f"\n✅ 价格已突破 ${breakout_level:,.2f}")
        print(f"   突破幅度: {distance_pct:.2f}%")
        
        if distance_pct <= 1.0:
            print(f"\n🎯 建议：")
            print(f"   - 价格刚突破，可以考虑进场做多")
            print(f"   - 入场价：${breakout_level * 1.002:,.2f} (突破位上方0.2%)")
            print(f"   - 止损：${breakout_level * 0.99:,.2f} (突破位下方1%)")
            print(f"   - 目标1：${breakout_level * 1.002 * 1.025:,.2f}")
            print(f"   - 目标2：${breakout_level * 1.002 * 1.035:,.2f}")
        else:
            print(f"\n⚠️  价格已突破较远 ({distance_pct:.2f}%)，可能错过最佳入场点")
            print(f"   建议：等待回调到突破位附近再考虑")
    else:
        print(f"\n⏳ 价格尚未突破 ${breakout_level:,.2f}")
        print(f"   还需上涨: ${abs(distance):,.2f} ({abs(distance_pct):.2f}%)")
        print(f"\n🎯 建议：")
        print(f"   - 等待价格突破 ${breakout_level:,.2f}")
        print(f"   - 突破后挂单在 ${breakout_level * 1.002:,.2f} 等待确认")
        print(f"   - 止损设置在 ${breakout_level * 0.99:,.2f}")
    
    # 使用规则引擎分析
    print("\n" + "=" * 60)
    print("使用规则引擎分析...")
    print("=" * 60)
    
    # 计算技术指标
    closes = [k['close'] for k in klines_15m]
    ema_144 = calculate_ema(closes, 144) if len(closes) >= 144 else None
    ema_169 = calculate_ema(closes, 169) if len(closes) >= 169 else None
    vwap = calculate_vwap(klines_15m[-100:])
    rsi = calculate_rsi(closes)
    
    # 识别技术形态
    fvgs = identify_fvg(klines_15m[-50:])
    sr = identify_support_resistance(klines_15m, current_price)
    m_top = detect_m_top(klines_15m, lookback=50)
    w_bottom = detect_w_bottom(klines_15m, lookback=50)
    ote_analysis = check_ote_zone(klines_15m, current_price, lookback=50)
    is_garbage, _ = check_garbage_time(klines_15m, current_price)
    
    # 构建市场数据
    market_data = {
        'current_price': current_price,
        'ema_144': ema_144,
        'ema_169': ema_169,
        'vwap': vwap,
        'rsi': rsi,
        'timeframe': '15m',
        'timestamp': datetime.now().timestamp()
    }
    
    # 转换技术形态
    patterns = []
    for fvg in fvgs:
        patterns.append({
            'pattern_type': f"fvg_{fvg['type']}",
            'is_valid': True,
            'price_level': fvg.get('price', fvg.get('high', 0)),
            'confidence': 0.8
        })
    
    if m_top and m_top.get('is_valid'):
        patterns.append({
            'pattern_type': 'm_top',
            'is_valid': True,
            'price_level': m_top.get('neckline', 0),
            'confidence': 0.85
        })
    
    if w_bottom and w_bottom.get('is_valid'):
        patterns.append({
            'pattern_type': 'w_bottom',
            'is_valid': True,
            'price_level': w_bottom.get('neckline', 0),
            'confidence': 0.85
        })
    
    support_resistance = {
        'nearest_support': min(sr.get('support', [0])) if sr.get('support') else None,
        'nearest_resistance': min(sr.get('resistance', [float('inf')])) if sr.get('resistance') else None,
        'support_levels': sr.get('support', []),
        'resistance_levels': sr.get('resistance', [])
    }
    
    # 添加突破位规则
    breakout_levels = [breakout_level]  # De.规则：突破873
    
    # 使用规则引擎分析
    signals = analyze_with_rules_engine(
        market_data=market_data,
        patterns=patterns,
        support_resistance=support_resistance,
        ote_analysis=ote_analysis,
        is_garbage_time=is_garbage,
        breakout_levels=breakout_levels
    )
    
    # 显示规则引擎生成的信号
    print(f"\n规则引擎生成了 {len(signals)} 个交易信号:")
    print("-" * 60)
    
    for signal in signals:
        if signal.signal_type == 'wait':
            print(f"\n⏸️  {signal.rule_name}")
            print(f"   理由: {signal.reason}")
        else:
            print(f"\n{'🟢' if signal.signal_type == 'long' else '🔴'} {signal.rule_name} ({signal.signal_type.upper()})")
            print(f"   强度: {signal.strength}")
            print(f"   入场: ${signal.entry:,.2f}")
            print(f"   止损: ${signal.stop_loss:,.2f}")
            print(f"   止盈1: ${signal.take_profit_1:,.2f} (50%)")
            print(f"   止盈2: ${signal.take_profit_2:,.2f} (50%)")
            print(f"   理由: {signal.reason}")
    
    # 特别关注突破规则信号
    breakout_signals = [s for s in signals if s.rule_name == 'Breakout_Long']
    if breakout_signals:
        print("\n" + "=" * 60)
        print("🎯 De.突破规则信号（这把上去突破873可以进）")
        print("=" * 60)
        for signal in breakout_signals:
            print(f"\n入场价: ${signal.entry:,.2f}")
            print(f"止损: ${signal.stop_loss:,.2f}")
            print(f"止盈1: ${signal.take_profit_1:,.2f}")
            print(f"止盈2: ${signal.take_profit_2:,.2f}")
            print(f"理由: {signal.reason}")
    
    print("\n" + "=" * 60)
    print("分析完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        analyze_breakout_rule()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

