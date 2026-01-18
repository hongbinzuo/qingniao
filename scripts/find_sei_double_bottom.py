#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析SEI的K线数据，找出Page 269匹配时的双底结构
"""
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime

ROOT = Path(__file__).parent.parent
SRC = ROOT / 'src'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SRC))

sys.stdout.reconfigure(encoding='utf-8')

from generate_comprehensive_trading_plans import get_kline_binance
from db_manager_trader import TraderDBManager

def find_swing_lows(klines: List[Dict], window: int = 5) -> List[Tuple[int, float, int]]:
    """
    寻找摆动低点
    
    Returns:
        List of (index, price, timestamp)
    """
    if not klines or len(klines) < window * 2 + 1:
        return []
    
    swing_lows = []
    
    for i in range(window, len(klines) - window):
        current_low = klines[i]['low']
        # 检查是否比前后window根K线都低
        is_swing_low = True
        for j in range(i - window, i + window + 1):
            if j != i and klines[j]['low'] < current_low:
                is_swing_low = False
                break
        
        if is_swing_low:
            timestamp = klines[i].get('timestamp', klines[i].get('time', 0))
            swing_lows.append((i, current_low, timestamp))
    
    return swing_lows

def find_double_bottom_pattern(klines: List[Dict], lookback: int = 100) -> Optional[Dict]:
    """
    寻找双底模式（Higher Low Double Bottom）
    
    Returns:
        {
            'first_low': (index, price, timestamp),
            'second_low': (index, price, timestamp),
            'is_higher_low': bool,
            'pattern_type': str
        }
    """
    if len(klines) < lookback:
        lookback = len(klines)
    
    recent_klines = klines[-lookback:]
    swing_lows = find_swing_lows(recent_klines, window=5)
    
    if len(swing_lows) < 2:
        return None
    
    # 按时间排序（从早到晚）
    swing_lows_sorted = sorted(swing_lows, key=lambda x: x[0])
    
    # 寻找双底：两个低点之间有高点，且第二个低点高于或等于第一个
    best_match = None
    best_score = 0
    
    for i in range(len(swing_lows_sorted) - 1):
        first_idx, first_price, first_ts = swing_lows_sorted[i]
        second_idx, second_price, second_ts = swing_lows_sorted[i + 1]
        
        # 检查两个低点之间是否有明显的高点（回撤）
        if second_idx - first_idx > 5:  # 至少间隔5根K线
            # 找到两个低点之间的最高点
            between_high = max(k['high'] for k in recent_klines[first_idx:second_idx+1])
            pullback_pct = (between_high - first_price) / first_price if first_price > 0 else 0
            
            # 降低回撤要求，只要回撤超过1%即可
            if pullback_pct > 0.01:
                is_higher_low = second_price >= first_price * 0.995  # 允许0.5%的误差
                pattern_type = "Higher Low Double Bottom" if is_higher_low else "Double Bottom"
                
                # 计算匹配分数（回撤幅度越大，间隔越合适，分数越高）
                score = pullback_pct * 10 + min(1.0, (second_idx - first_idx) / 50)
                
                if score > best_score:
                    # 调整索引（因为使用的是recent_klines）
                    first_actual_idx = len(klines) - lookback + first_idx
                    second_actual_idx = len(klines) - lookback + second_idx
                    
                    best_match = {
                        'first_low': (first_actual_idx, first_price, first_ts),
                        'second_low': (second_actual_idx, second_price, second_ts),
                        'is_higher_low': is_higher_low,
                        'pattern_type': pattern_type,
                        'pullback_high': between_high,
                        'pullback_pct': pullback_pct * 100,
                        'score': score
                    }
                    best_score = score
    
    return best_match

def format_timestamp(ts: int) -> str:
    """格式化时间戳"""
    try:
        if ts > 1e10:  # 毫秒时间戳
            ts = ts / 1000
        dt = datetime.fromtimestamp(ts)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(ts)

def get_sei_signal_info():
    """获取SEI的Page 269信号信息"""
    db = TraderDBManager('abu')
    conn = db._get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT signal_time, entry_price, stop_loss, take_profit_1, notes
        FROM trading_signals
        WHERE symbol = 'SEI' 
          AND (notes LIKE '%page 269%' OR notes LIKE '%269%' OR entry_model LIKE '%269%')
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    db.close()
    
    if row:
        return {
            'signal_time': row[0],
            'entry_price': row[1],
            'stop_loss': row[2],
            'take_profit_1': row[3],
            'notes': row[4]
        }
    return None

def main():
    print("=" * 80)
    print("SEI Page 269 双底结构分析")
    print("=" * 80)
    print()
    
    # 获取信号信息
    signal_info = get_sei_signal_info()
    if signal_info:
        print(f"信号时间: {signal_info['signal_time']}")
        print(f"入场价格: {signal_info['entry_price']:.4f}")
        print(f"止损价格: {signal_info['stop_loss']:.4f}")
        print(f"止盈价格: {signal_info['take_profit_1']:.4f}")
        print(f"说明: {signal_info['notes']}")
        print()
    
    print("正在获取SEI的15分钟K线数据...")
    klines = get_kline_binance('SEI', '15m', 200)
    if not klines:
        print("无法获取K线数据")
        return
    
    print(f"获取到 {len(klines)} 根K线")
    current_price = klines[-1]['close']
    print(f"当前价格: {current_price:.4f}")
    print()
    
    # 寻找双底结构
    print("正在分析双底结构...")
    double_bottom = find_double_bottom_pattern(klines, lookback=150)
    
    if double_bottom:
        print("=" * 80)
        print(f"找到双底模式: {double_bottom['pattern_type']}")
        print("=" * 80)
        print()
        
        first_idx, first_price, first_ts = double_bottom['first_low']
        second_idx, second_price, second_ts = double_bottom['second_low']
        
        print(f"第一个低点:")
        print(f"  K线索引: {first_idx}")
        print(f"  时间: {format_timestamp(first_ts)}")
        print(f"  价格: {first_price:.4f}")
        print()
        
        print(f"第二个低点:")
        print(f"  K线索引: {second_idx}")
        print(f"  时间: {format_timestamp(second_ts)}")
        print(f"  价格: {second_price:.4f}")
        print()
        
        price_diff = second_price - first_price
        price_diff_pct = (price_diff / first_price) * 100 if first_price > 0 else 0
        
        print(f"价格差异:")
        print(f"  绝对差异: {price_diff:.4f} ({price_diff_pct:+.2f}%)")
        print(f"  是否更高低点: {'是' if double_bottom['is_higher_low'] else '否'}")
        print()
        
        print(f"回撤信息:")
        print(f"  回撤高点: {double_bottom['pullback_high']:.4f}")
        print(f"  回撤幅度: {double_bottom['pullback_pct']:.2f}%")
        print()
        
        # 显示两个低点之间的K线数量
        kline_count = second_idx - first_idx
        time_span_hours = kline_count * 0.25  # 15分钟 = 0.25小时
        print(f"时间跨度:")
        print(f"  K线数量: {kline_count}根 (约{time_span_hours:.1f}小时)")
        print()
        
        # 显示最近的几个摆动低点
        print("所有摆动低点 (最近150根K线):")
        recent_klines = klines[-150:]
        swing_lows = find_swing_lows(recent_klines, window=5)
        swing_lows_sorted = sorted(swing_lows, key=lambda x: x[0])
        
        for i, (idx, price, ts) in enumerate(swing_lows_sorted[-10:], 1):  # 显示最后10个
            actual_idx = len(klines) - 150 + idx
            print(f"  {i}. {format_timestamp(ts)} | 价格: {price:.4f} | 索引: {actual_idx}")
        
    else:
        print("未找到明显的双底结构")
        print()
        print("最近的摆动低点:")
        recent_klines = klines[-100:]
        swing_lows = find_swing_lows(recent_klines, window=5)
        swing_lows_sorted = sorted(swing_lows, key=lambda x: x[0])
        
        for i, (idx, price, ts) in enumerate(swing_lows_sorted[-5:], 1):
            actual_idx = len(klines) - 100 + idx
            print(f"  {i}. {format_timestamp(ts)} | 价格: {price:.4f} | 索引: {actual_idx}")

if __name__ == '__main__':
    main()

