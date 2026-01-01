#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为做空信号获取订单簿止损（处理入场价高于当前价格的情况）
"""

import sys
from get_realtime_stop_loss import (
    get_order_book_with_retry,
    get_current_price,
    calculate_stop_loss_by_orderbook
)

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def main():
    entry_price = 88738  # 5分钟做空信号入场价
    
    print("=" * 80)
    print("为5分钟做空信号获取订单簿止损")
    print("=" * 80)
    print()
    
    # 获取当前价格
    current_price = get_current_price('BTC')
    if not current_price:
        print("❌ 无法获取当前价格")
        return
    
    print(f"入场价: ${entry_price:,.2f}")
    print(f"当前价格: ${current_price:,.2f}")
    print()
    
    # 获取订单簿
    print("正在获取BTC实时订单簿...", file=sys.stderr)
    order_book, exchange_name = get_order_book_with_retry('BTC', limit=100)
    
    if not order_book:
        print("❌ 无法获取订单簿数据")
        return
    
    # 尝试使用入场价计算止损
    print("尝试基于入场价计算止损...", file=sys.stderr)
    stop_loss, info = calculate_stop_loss_by_orderbook(
        entry_price, 'short', order_book, current_price
    )
    
    if stop_loss:
        distance = stop_loss - entry_price
        distance_pct = (distance / entry_price) * 100
        print(f"✅ **订单簿止损**: ${stop_loss:,.2f}")
        print(f"   止损距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
        if info:
            print(f"   来源: {info.get('source_info', '订单簿分析')}")
        print(f"   交易所: {exchange_name}")
    else:
        # 如果无法计算，尝试使用当前价格作为参考
        print("⚠️  无法基于入场价计算止损，尝试使用当前价格作为参考...", file=sys.stderr)
        stop_loss_ref, info_ref = calculate_stop_loss_by_orderbook(
            current_price, 'short', order_book, current_price
        )
        
        if stop_loss_ref:
            # 计算入场价对应的止损（保持相同的距离百分比）
            distance_pct_ref = ((stop_loss_ref - current_price) / current_price) * 100
            stop_loss_estimated = entry_price * (1 + distance_pct_ref / 100)
            distance = stop_loss_estimated - entry_price
            distance_pct = (distance / entry_price) * 100
            
            print(f"✅ **估算止损**: ${stop_loss_estimated:,.2f} (基于当前价格止损距离{distance_pct_ref:.2f}%)")
            print(f"   止损距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
            print(f"   ⚠️  注意: 这是基于当前价格的估算，建议在价格接近入场价时重新计算")
            print(f"   交易所: {exchange_name}")
        else:
            print("❌ 无法获取订单簿止损")
            print("   建议: 等待价格接近入场价$88,738时，使用以下命令重新计算:")
            print(f"   python src/get_realtime_stop_loss.py BTC short sl {entry_price}")

if __name__ == "__main__":
    main()



