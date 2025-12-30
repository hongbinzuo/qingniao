"""
分析De.规则：这把上去突破873可以进
不依赖experta，直接分析
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


def analyze_breakout_873():
    """分析突破873规则"""
    print("=" * 70)
    print("De.规则分析：这把上去突破873可以进")
    print("=" * 70)
    
    # 获取当前价格
    print("\n正在获取BTC市场数据...")
    klines_15m = get_btc_kline_gateio('15m', limit=200)
    if not klines_15m:
        print("❌ 无法获取K线数据，尝试使用备用方法...")
        klines_5m = get_btc_kline_gateio('5m', limit=50)
        if klines_5m:
            klines_15m = klines_5m
        else:
            print("❌ 无法获取K线数据")
            return
    
    current_price = get_btc_current_price()
    if not current_price:
        current_price = klines_15m[-1]['close']
    
    print(f"\n✅ 当前BTC价格: ${current_price:,.2f}")
    
    # De.规则：这把上去突破873可以进
    breakout_level = 87300  # $87,300
    print(f"📊 突破位: ${breakout_level:,.2f}")
    
    # 计算距离
    distance = current_price - breakout_level
    distance_pct = (distance / breakout_level) * 100
    
    print(f"\n" + "-" * 70)
    print("价格分析:")
    print("-" * 70)
    print(f"  当前价格: ${current_price:,.2f}")
    print(f"  突破位: ${breakout_level:,.2f}")
    print(f"  距离: ${distance:,.2f} ({distance_pct:+.2f}%)")
    
    # 计算技术指标
    closes = [k['close'] for k in klines_15m]
    ema_144 = calculate_ema(closes, 144) if len(closes) >= 144 else None
    ema_169 = calculate_ema(closes, 169) if len(closes) >= 169 else None
    vwap = calculate_vwap(klines_15m[-100:]) if len(klines_15m) >= 100 else None
    rsi = calculate_rsi(closes)
    
    print(f"\n技术指标:")
    if ema_144:
        print(f"  EMA144: ${ema_144:,.2f}")
    if ema_169:
        print(f"  EMA169: ${ema_169:,.2f}")
    if vwap:
        print(f"  VWAP: ${vwap:,.2f}")
    if rsi:
        print(f"  RSI: {rsi:.1f}")
    
    # 判断状态
    print(f"\n" + "=" * 70)
    if current_price > breakout_level:
        print(f"✅ 价格已突破 ${breakout_level:,.2f}")
        print(f"   突破幅度: {distance_pct:.2f}%")
        
        if distance_pct <= 1.0:
            print(f"\n🎯 交易建议（De.规则：这把上去突破873可以进）:")
            print("-" * 70)
            entry = breakout_level * 1.002  # 突破位上方0.2%
            stop_loss = breakout_level * 0.99  # 突破位下方1%
            risk = entry - stop_loss
            take_profit_1 = entry + risk * 2.5
            take_profit_2 = entry + risk * 3.5
            
            print(f"  ✅ 可以进场做多")
            print(f"  📍 入场价: ${entry:,.2f} (突破位上方0.2%，挂单等待)")
            print(f"  🛑 止损: ${stop_loss:,.2f} (突破位下方1%)")
            print(f"  🎯 止盈1: ${take_profit_1:,.2f} (50%仓位，盈亏比1:2.5)")
            print(f"  🎯 止盈2: ${take_profit_2:,.2f} (50%仓位，盈亏比1:3.5)")
            print(f"  💰 风险: ${risk:,.2f} ({risk/entry*100:.2f}%)")
            print(f"  📈 潜在收益1: ${take_profit_1 - entry:,.2f}")
            print(f"  📈 潜在收益2: ${take_profit_2 - entry:,.2f}")
            
            # 检查其他技术指标
            print(f"\n技术分析确认:")
            if ema_144 and current_price > ema_144:
                print(f"  ✅ 价格在EMA144上方")
            if ema_169 and current_price > ema_169:
                print(f"  ✅ 价格在EMA169上方")
            if vwap and current_price > vwap:
                print(f"  ✅ 价格在VWAP上方")
            if rsi and 30 < rsi < 70:
                print(f"  ✅ RSI在合理区间 ({rsi:.1f})")
        else:
            print(f"\n⚠️  价格已突破较远 ({distance_pct:.2f}%)")
            print(f"   建议：等待回调到突破位附近再考虑")
            print(f"   回调目标: ${breakout_level * 1.002:,.2f}")
    else:
        print(f"⏳ 价格尚未突破 ${breakout_level:,.2f}")
        print(f"   还需上涨: ${abs(distance):,.2f} ({abs(distance_pct):.2f}%)")
        
        print(f"\n🎯 交易计划（De.规则：这把上去突破873可以进）:")
        print("-" * 70)
        entry = breakout_level * 1.002  # 突破位上方0.2%
        stop_loss = breakout_level * 0.99  # 突破位下方1%
        risk = entry - stop_loss
        take_profit_1 = entry + risk * 2.5
        take_profit_2 = entry + risk * 3.5
        
        print(f"  📍 等待价格突破 ${breakout_level:,.2f}")
        print(f"  📍 突破后挂单在: ${entry:,.2f} (突破位上方0.2%)")
        print(f"  🛑 止损设置在: ${stop_loss:,.2f} (突破位下方1%)")
        print(f"  🎯 止盈1: ${take_profit_1:,.2f} (50%仓位)")
        print(f"  🎯 止盈2: ${take_profit_2:,.2f} (50%仓位)")
        print(f"  💰 风险: ${risk:,.2f} ({risk/entry*100:.2f}%)")
        
        # 计算需要上涨多少
        needed_increase = breakout_level - current_price
        needed_pct = (needed_increase / current_price) * 100
        print(f"\n  📊 需要上涨: ${needed_increase:,.2f} ({needed_pct:.2f}%) 才能触发")
    
    # 检查其他技术形态
    print(f"\n" + "=" * 70)
    print("其他技术形态分析:")
    print("-" * 70)
    
    fvgs = identify_fvg(klines_15m[-50:])
    if fvgs:
        print(f"  FVG形态: 发现 {len(fvgs)} 个FVG")
        for fvg in fvgs[-3:]:
            print(f"    - {fvg['type']} FVG: ${fvg.get('price', 0):,.2f}")
    
    m_top = detect_m_top(klines_15m, lookback=50)
    if m_top and m_top.get('is_valid'):
        print(f"  M顶形态: 已识别，腰线 ${m_top.get('neckline', 0):,.2f}")
    
    w_bottom = detect_w_bottom(klines_15m, lookback=50)
    if w_bottom and w_bottom.get('is_valid'):
        print(f"  W底形态: 已识别，腰线 ${w_bottom.get('neckline', 0):,.2f}")
    
    sr = identify_support_resistance(klines_15m, current_price)
    if sr.get('support'):
        nearest_support = min(sr['support'])
        print(f"  最近支撑: ${nearest_support:,.2f}")
    if sr.get('resistance'):
        nearest_resistance = min(sr['resistance'])
        print(f"  最近阻力: ${nearest_resistance:,.2f}")
    
    is_garbage, garbage_range = check_garbage_time(klines_15m, current_price)
    if is_garbage:
        print(f"  ⚠️  垃圾时间: 价格在 ${garbage_range[0]:,.2f} - ${garbage_range[1]:,.2f} 区间震荡")
    
    print(f"\n" + "=" * 70)
    print("分析完成")
    print("=" * 70)
    print(f"\n生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    try:
        analyze_breakout_873()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

