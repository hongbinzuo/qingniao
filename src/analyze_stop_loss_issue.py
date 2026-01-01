"""
分析止损问题：为什么止损那么宽
"""

import sys
import io
from generate_btc_multi_tf_plan import (
    get_btc_kline_gateio, get_btc_current_price,
    calculate_ema, calculate_smart_stop_loss,
    identify_fvg, identify_support_resistance,
    find_recent_key_levels
)

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def analyze_stop_loss_issue():
    """分析止损问题"""
    print("=" * 70)
    print("止损问题分析")
    print("=" * 70)
    
    # 获取数据
    klines_15m = get_btc_kline_gateio('15m', limit=200)
    if not klines_15m:
        print("无法获取K线数据")
        return
    
    current_price = get_btc_current_price() or klines_15m[-1]['close']
    closes = [k['close'] for k in klines_15m]
    ema_144 = calculate_ema(closes, 144)
    ema_169 = calculate_ema(closes, 169)
    
    print(f"\n当前价格: ${current_price:,.2f}")
    print(f"EMA144: ${ema_144:,.2f}")
    print(f"EMA169: ${ema_169:,.2f}")
    
    # 模拟最新信号的参数
    entry_price = 87639  # 做空入场价
    print(f"\n信号参数:")
    print(f"  入场价: ${entry_price:,.2f}")
    print(f"  信号类型: 做空")
    
    # 计算技术指标
    fvgs = identify_fvg(klines_15m[-50:])
    sr = identify_support_resistance(klines_15m, current_price)
    key_levels = find_recent_key_levels(klines_15m, current_price)
    
    # 使用calculate_smart_stop_loss计算止损
    stop_loss = calculate_smart_stop_loss(
        entry_price, 'short', klines_15m, fvgs, sr, key_levels, ema_144, ema_169
    )
    
    print(f"\n计算出的止损: ${stop_loss:,.2f}")
    print(f"止损距离: {stop_loss - entry_price:,.0f}点 ({(stop_loss - entry_price)/entry_price*100:.2f}%)")
    
    # 分析止损计算过程
    print(f"\n" + "-" * 70)
    print("止损计算分析:")
    print("-" * 70)
    
    # 检查各个候选止损
    stop_candidates = []
    
    # 1. 摆动高点
    if key_levels['swing_high'] and key_levels['swing_high'] > entry_price:
        candidate = key_levels['swing_high'] * 1.005
        stop_candidates.append(('摆动高点上方', candidate))
        print(f"  1. 摆动高点上方: ${candidate:,.2f} (摆动高点: ${key_levels['swing_high']:,.2f})")
    
    # 2. 最近高点
    if key_levels['recent_high'] and key_levels['recent_high'] > entry_price:
        candidate = key_levels['recent_high'] * 1.005
        stop_candidates.append(('最近高点上方', candidate))
        print(f"  2. 最近高点上方: ${candidate:,.2f} (最近高点: ${key_levels['recent_high']:,.2f})")
    
    # 3. FVG上沿
    for fvg in fvgs:
        if fvg['type'] == 'bearish' and fvg['high'] > entry_price:
            candidate = fvg['high'] * 1.01
            stop_candidates.append(('FVG上沿上方', candidate))
            print(f"  3. FVG上沿上方: ${candidate:,.2f} (FVG上沿: ${fvg['high']:,.2f})")
    
    # 4. 阻力位
    if sr['resistance']:
        nearest_resistance = min([r for r in sr['resistance'] if r > entry_price], default=None)
        if nearest_resistance:
            candidate = nearest_resistance * 1.02
            stop_candidates.append(('阻力位上方', candidate))
            print(f"  4. 阻力位上方: ${candidate:,.2f} (阻力位: ${nearest_resistance:,.2f})")
    
    # 5. Vegas通道上方（关键！）
    if ema_144 and ema_169 and entry_price < ema_144:
        candidate = ema_169 * 1.005
        stop_candidates.append(('Vegas通道上方', candidate))
        print(f"  5. Vegas通道上方: ${candidate:,.2f} (EMA169: ${ema_169:,.2f})")
        print(f"     ⚠️ 这是最合理的止损位置！")
    
    # 分析为什么止损宽
    print(f"\n" + "-" * 70)
    print("问题分析:")
    print("-" * 70)
    
    if stop_candidates:
        valid_stops = [s for _, s in stop_candidates if s > entry_price]
        if valid_stops:
            min_stop = min(valid_stops)
            print(f"\n候选止损中最小的: ${min_stop:,.2f}")
            print(f"距离入场价: {min_stop - entry_price:,.0f}点 ({(min_stop - entry_price)/entry_price*100:.2f}%)")
            
            # 检查是否被最小止损距离限制
            min_stop_distance = entry_price * 0.015  # 至少1.5%
            if (min_stop - entry_price) < min_stop_distance:
                print(f"\n⚠️ 问题发现：")
                print(f"  候选止损距离 ({min_stop - entry_price:,.0f}点) 小于最小要求 ({min_stop_distance:,.0f}点)")
                print(f"  系统强制将止损放宽到至少1.5%: ${entry_price * 1.015:,.2f}")
                print(f"  这就是为什么止损看起来比较宽的原因！")
            else:
                print(f"\n✅ 候选止损距离合理，应该使用: ${min_stop:,.2f}")
                print(f"  但实际止损是: ${stop_loss:,.2f}")
                if stop_loss > min_stop * 1.01:
                    print(f"  ⚠️ 实际止损比候选止损高，可能被最大止损距离限制了")
    else:
        print("\n⚠️ 没有找到合适的候选止损，使用默认止损（入场价上方1.5%）")
    
    # 建议
    print(f"\n" + "=" * 70)
    print("优化建议:")
    print("=" * 70)
    
    # 计算基于Vegas的合理止损
    if ema_169:
        vegas_stop = ema_169 * 1.01  # Vegas上方1%
        vegas_distance = vegas_stop - entry_price
        vegas_pct = (vegas_distance / entry_price) * 100
        
        print(f"\n基于Vegas通道的合理止损:")
        print(f"  Vegas通道 (EMA169): ${ema_169:,.2f}")
        print(f"  建议止损: ${vegas_stop:,.2f} (Vegas上方1%)")
        print(f"  止损距离: {vegas_distance:,.0f}点 ({vegas_pct:.2f}%)")
        
        if vegas_pct < 1.5:
            print(f"\n  ⚠️ 这个止损距离 ({vegas_pct:.2f}%) 小于系统要求的最小值 (1.5%)")
            print(f"  建议：调整最小止损距离限制，允许更紧的止损（如果技术位支持）")
        elif vegas_pct > 3.0:
            print(f"\n  ⚠️ 这个止损距离 ({vegas_pct:.2f}%) 大于系统要求的最大值 (3.0%)")
            print(f"  建议：使用Vegas通道上方0.5%而不是1%")
        else:
            print(f"\n  ✅ 这个止损距离合理，应该使用这个止损而不是默认的1.5%")
    
    print(f"\n具体建议:")
    print(f"  1. 优先使用技术位止损（Vegas通道上方），而不是固定的1.5%")
    print(f"  2. 如果技术位止损距离小于1.5%，应该允许使用（但要标注风险）")
    print(f"  3. 改进订单簿分析，更好地识别卖单密集区")
    print(f"  4. 对于Vegas通道信号，止损应该优先放在Vegas通道上方")

if __name__ == "__main__":
    analyze_stop_loss_issue()


