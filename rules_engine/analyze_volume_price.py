"""
BTC日线图量价分析
基于用户提供的TradingView图表数据
"""

import sys
import io
from datetime import datetime, timedelta
from generate_btc_multi_tf_plan import get_btc_kline_gateio, get_btc_current_price

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def analyze_volume_price():
    """量价分析"""
    print("=" * 70)
    print("BTC日线图量价分析")
    print("=" * 70)
    
    # 获取日线数据
    print("\n正在获取BTC日线数据...")
    klines_1d = get_btc_kline_gateio('1d', limit=200)
    if not klines_1d:
        print("无法获取日线数据")
        return
    
    current_price = get_btc_current_price() or klines_1d[-1]['close']
    
    print(f"当前价格: ${current_price:,.2f}")
    print(f"数据范围: {len(klines_1d)}根K线")
    
    # 提取价格和成交量数据
    closes = [k['close'] for k in klines_1d]
    highs = [k['high'] for k in klines_1d]
    lows = [k['low'] for k in klines_1d]
    volumes = [k['volume'] for k in klines_1d]
    opens = [k['open'] for k in klines_1d]
    
    # 计算价格变化
    price_changes = [(closes[i] - closes[i-1]) / closes[i-1] * 100 if i > 0 else 0 
                     for i in range(len(closes))]
    
    # 计算成交量变化
    volume_changes = [(volumes[i] - volumes[i-1]) / volumes[i-1] * 100 if i > 0 and volumes[i-1] > 0 else 0 
                      for i in range(len(volumes))]
    
    # 计算平均成交量
    avg_volume = sum(volumes) / len(volumes)
    
    print(f"\n平均成交量: {avg_volume:,.0f}")
    
    # 分析最近30天的量价关系
    print("\n" + "=" * 70)
    print("最近30天量价分析")
    print("=" * 70)
    
    recent_klines = klines_1d[-30:]
    recent_closes = closes[-30:]
    recent_volumes = volumes[-30:]
    recent_highs = highs[-30:]
    recent_lows = lows[-30:]
    
    # 1. 价格上涨时的成交量
    print("\n1. 价格上涨时的成交量分析:")
    print("-" * 70)
    bullish_days = []
    for i in range(len(recent_klines)):
        if recent_klines[i]['close'] > recent_klines[i]['open']:
            bullish_days.append({
                'day': i,
                'price_change': recent_klines[i]['close'] - recent_klines[i]['open'],
                'volume': recent_volumes[i],
                'volume_ratio': recent_volumes[i] / avg_volume
            })
    
    if bullish_days:
        avg_bullish_volume = sum([d['volume'] for d in bullish_days]) / len(bullish_days)
        print(f"  上涨天数: {len(bullish_days)}天")
        print(f"  平均成交量: {avg_bullish_volume:,.0f} ({avg_bullish_volume/avg_volume:.2f}倍平均量)")
        
        # 找出放量上涨
        high_volume_bullish = [d for d in bullish_days if d['volume_ratio'] > 1.5]
        if high_volume_bullish:
            print(f"  放量上涨天数: {len(high_volume_bullish)}天")
            for d in high_volume_bullish[-3:]:
                day_idx = len(recent_klines) - 30 + d['day']
                print(f"    - 第{day_idx}天: 涨幅{d['price_change']:,.0f}点, 成交量{d['volume_ratio']:.2f}倍")
    
    # 2. 价格下跌时的成交量
    print("\n2. 价格下跌时的成交量分析:")
    print("-" * 70)
    bearish_days = []
    for i in range(len(recent_klines)):
        if recent_klines[i]['close'] < recent_klines[i]['open']:
            bearish_days.append({
                'day': i,
                'price_change': recent_klines[i]['open'] - recent_klines[i]['close'],
                'volume': recent_volumes[i],
                'volume_ratio': recent_volumes[i] / avg_volume
            })
    
    if bearish_days:
        avg_bearish_volume = sum([d['volume'] for d in bearish_days]) / len(bearish_days)
        print(f"  下跌天数: {len(bearish_days)}天")
        print(f"  平均成交量: {avg_bearish_volume:,.0f} ({avg_bearish_volume/avg_volume:.2f}倍平均量)")
        
        # 找出放量下跌
        high_volume_bearish = [d for d in bearish_days if d['volume_ratio'] > 1.5]
        if high_volume_bearish:
            print(f"  放量下跌天数: {len(high_volume_bearish)}天")
            for d in high_volume_bearish[-3:]:
                day_idx = len(recent_klines) - 30 + d['day']
                print(f"    - 第{day_idx}天: 跌幅{d['price_change']:,.0f}点, 成交量{d['volume_ratio']:.2f}倍")
    
    # 3. 量价背离分析
    print("\n3. 量价背离分析:")
    print("-" * 70)
    
    # 计算价格趋势（最近10天）
    recent_10_price_trend = (recent_closes[-1] - recent_closes[-10]) / recent_closes[-10] * 100
    recent_10_volume_trend = (sum(recent_volumes[-5:]) - sum(recent_volumes[-10:-5])) / sum(recent_volumes[-10:-5]) * 100 if sum(recent_volumes[-10:-5]) > 0 else 0
    
    print(f"  最近10天价格变化: {recent_10_price_trend:+.2f}%")
    print(f"  最近10天成交量变化: {recent_10_volume_trend:+.2f}%")
    
    if recent_10_price_trend > 0 and recent_10_volume_trend < -10:
        print(f"  ⚠️ 顶背离：价格上涨但成交量萎缩，可能见顶")
    elif recent_10_price_trend < 0 and recent_10_volume_trend < -10:
        print(f"  ✅ 底背离：价格下跌但成交量萎缩，可能见底")
    elif recent_10_price_trend > 0 and recent_10_volume_trend > 10:
        print(f"  ✅ 量价齐升：价格上涨伴随成交量放大，健康上涨")
    elif recent_10_price_trend < 0 and recent_10_volume_trend > 10:
        print(f"  ⚠️ 量价齐跌：价格下跌伴随成交量放大，可能继续下跌")
    
    # 4. 关键位置的量价关系
    print("\n4. 关键位置的量价关系:")
    print("-" * 70)
    
    # 找出最近的高点和低点
    recent_high = max(recent_highs)
    recent_low = min(recent_lows)
    high_idx = recent_highs.index(recent_high)
    low_idx = recent_lows.index(recent_low)
    
    print(f"  最近高点: ${recent_high:,.2f} (第{high_idx}天)")
    print(f"    当日成交量: {recent_volumes[high_idx]:,.0f} ({recent_volumes[high_idx]/avg_volume:.2f}倍平均量)")
    if recent_volumes[high_idx] > avg_volume * 1.5:
        print(f"    ⚠️ 放量见顶，可能是阻力位")
    else:
        print(f"    ✅ 缩量见顶，可能是假突破")
    
    print(f"  最近低点: ${recent_low:,.2f} (第{low_idx}天)")
    print(f"    当日成交量: {recent_volumes[low_idx]:,.0f} ({recent_volumes[low_idx]/avg_volume:.2f}倍平均量)")
    if recent_volumes[low_idx] > avg_volume * 1.5:
        print(f"    ✅ 放量见底，可能是支撑位")
    else:
        print(f"    ⚠️ 缩量见底，可能继续下跌")
    
    # 5. 当前量价状态
    print("\n5. 当前量价状态:")
    print("-" * 70)
    
    last_k = recent_klines[-1]
    last_volume = recent_volumes[-1]
    last_volume_ratio = last_volume / avg_volume
    
    print(f"  当前价格: ${last_k['close']:,.2f}")
    print(f"  当日涨跌: {last_k['close'] - last_k['open']:+,.2f} ({(last_k['close'] - last_k['open'])/last_k['open']*100:+.2f}%)")
    print(f"  当日成交量: {last_volume:,.0f} ({last_volume_ratio:.2f}倍平均量)")
    
    if last_k['close'] > last_k['open']:
        if last_volume_ratio > 1.5:
            print(f"  ✅ 放量上涨：价格上涨伴随成交量放大，多头力量强")
        elif last_volume_ratio > 1.0:
            print(f"  ✅ 温和放量上涨：价格上涨，成交量略增")
        else:
            print(f"  ⚠️ 缩量上涨：价格上涨但成交量萎缩，可能缺乏持续性")
    else:
        if last_volume_ratio > 1.5:
            print(f"  ⚠️ 放量下跌：价格下跌伴随成交量放大，空头力量强")
        elif last_volume_ratio > 1.0:
            print(f"  ⚠️ 温和放量下跌：价格下跌，成交量略增")
        else:
            print(f"  ✅ 缩量下跌：价格下跌但成交量萎缩，可能是正常回调")
    
    # 6. 成交量分布分析
    print("\n6. 成交量分布分析:")
    print("-" * 70)
    
    # 计算不同价格区间的成交量
    price_ranges = [
        (85000, 87000, "当前区间"),
        (87000, 90000, "上方区间"),
        (83000, 85000, "下方区间"),
    ]
    
    for low, high, label in price_ranges:
        range_volumes = []
        for i, k in enumerate(klines_1d):
            if low <= k['close'] <= high:
                range_volumes.append(volumes[i])
        
        if range_volumes:
            avg_range_volume = sum(range_volumes) / len(range_volumes)
            print(f"  {label} (${low:,.0f}-${high:,.0f}):")
            print(f"    平均成交量: {avg_range_volume:,.0f} ({avg_range_volume/avg_volume:.2f}倍)")
            print(f"    交易天数: {len(range_volumes)}天")
    
    # 7. 交易建议
    print("\n" + "=" * 70)
    print("量价分析交易建议")
    print("=" * 70)
    
    # 基于量价关系给出建议
    if last_k['close'] > last_k['open'] and last_volume_ratio > 1.5:
        print("\n✅ 看涨信号：")
        print("  - 放量上涨，多头力量强")
        print("  - 建议：关注做多机会，等待回调入场")
    elif last_k['close'] < last_k['open'] and last_volume_ratio > 1.5:
        print("\n⚠️ 看跌信号：")
        print("  - 放量下跌，空头力量强")
        print("  - 建议：谨慎做多，等待企稳")
    elif last_k['close'] > last_k['open'] and last_volume_ratio < 0.8:
        print("\n⚠️ 谨慎看涨：")
        print("  - 缩量上涨，可能缺乏持续性")
        print("  - 建议：等待放量确认后再入场")
    elif last_k['close'] < last_k['open'] and last_volume_ratio < 0.8:
        print("\n✅ 可能见底：")
        print("  - 缩量下跌，可能是正常回调")
        print("  - 建议：关注支撑位，等待反弹信号")
    
    # 结合图表中的阻力位
    print("\n结合图表阻力位分析：")
    print("  - 主要阻力: $117,150 (34.07%), $109,617.5 (25.45%), $100,100 (14.56%)")
    print("  - 当前价格: $87,380")
    print("  - 距离最近阻力 ($93,377-$94,589): 约6.9%")
    print("  - 建议：关注$93,377-$94,589阻力位，观察成交量变化")
    
    print("\n" + "=" * 70)
    print("分析完成")
    print("=" * 70)


if __name__ == "__main__":
    analyze_volume_price()


