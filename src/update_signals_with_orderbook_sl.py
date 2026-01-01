#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为信号更新实时订单簿止损
"""

import sys
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    from get_realtime_stop_loss import (
        get_order_book_with_retry,
        get_current_price,
        calculate_stop_loss_by_orderbook
    )
except ImportError as e:
    print(f"导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def get_orderbook_stop_loss_for_signal(entry_price, signal_type, current_price=None):
    """为信号获取订单簿止损"""
    if current_price is None:
        print(f"正在获取BTC当前价格...", file=sys.stderr)
        current_price = get_current_price('BTC')
        if not current_price:
            return None, None, None
    
    print(f"正在获取BTC实时订单簿...", file=sys.stderr)
    order_book, exchange_name = get_order_book_with_retry('BTC', limit=50)
    
    if not order_book:
        return None, None, exchange_name
    
    # 计算止损
    stop_loss, info = calculate_stop_loss_by_orderbook(
        entry_price, signal_type, order_book, current_price
    )
    
    return stop_loss, info, exchange_name


def main():
    """主函数"""
    print("=" * 80)
    print("为BTC信号获取实时订单簿止损")
    print("=" * 80)
    print()
    
    # 获取当前价格
    current_price = get_current_price('BTC')
    if not current_price:
        print("❌ 无法获取当前价格")
        return
    
    print(f"当前BTC价格: ${current_price:,.2f}")
    print()
    
    # 信号1: 5分钟做空
    print("=" * 80)
    print("信号1: 5分钟做空")
    print("=" * 80)
    entry_short = 88738
    print(f"入场价: ${entry_short:,.2f}")
    print(f"当前价格: ${current_price:,.2f}")
    
    # 对于做空，如果入场价高于当前价格，使用当前价格作为参考
    if entry_short > current_price:
        print(f"⚠️  入场价高于当前价格，使用当前价格作为参考计算止损")
        reference_price = current_price
    else:
        reference_price = entry_short
    
    stop_loss_short, info_short, exchange_short = get_orderbook_stop_loss_for_signal(
        entry_short, 'short', current_price
    )
    
    if stop_loss_short:
        distance = abs(entry_short - stop_loss_short)
        distance_pct = (distance / entry_short) * 100
        print(f"✅ **订单簿止损**: ${stop_loss_short:,.2f}")
        print(f"   止损距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
        if info_short:
            print(f"   来源: {info_short.get('source_info', '订单簿分析')}")
        print(f"   交易所: {exchange_short}")
    else:
        print("❌ 无法获取订单簿止损，建议手动观察订单簿设置")
    
    print()
    
    # 信号2: 15分钟做多
    print("=" * 80)
    print("信号2: 15分钟做多")
    print("=" * 80)
    entry_long = 87702
    print(f"入场价: ${entry_long:,.2f}")
    print(f"当前价格: ${current_price:,.2f}")
    
    stop_loss_long, info_long, exchange_long = get_orderbook_stop_loss_for_signal(
        entry_long, 'long', current_price
    )
    
    if stop_loss_long:
        distance = abs(entry_long - stop_loss_long)
        distance_pct = (distance / entry_long) * 100
        print(f"✅ **订单簿止损**: ${stop_loss_long:,.2f}")
        print(f"   止损距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
        if info_long:
            print(f"   来源: {info_long.get('source_info', '订单簿分析')}")
        print(f"   交易所: {exchange_long}")
    else:
        print("❌ 无法获取订单簿止损，建议手动观察订单簿设置")
    
    print()
    print("=" * 80)
    print("完成")
    print("=" * 80)
    
    # 输出更新后的信号信息
    print()
    print("更新后的信号信息:")
    print()
    print("## 5分钟做空信号")
    print(f"入场: ${entry_short:,.0f}")
    if stop_loss_short:
        distance_pct = (abs(entry_short - stop_loss_short) / entry_short) * 100
        print(f"止损: ${stop_loss_short:,.0f} ✅ [基于实时订单簿] ({distance_pct:.2f}%)")
    else:
        print(f"止损: 需手动设置（无法获取订单簿止损）")
    print()
    
    print("## 15分钟做多信号")
    print(f"入场: ${entry_long:,.0f}")
    if stop_loss_long:
        distance_pct = (abs(entry_long - stop_loss_long) / entry_long) * 100
        print(f"止损: ${stop_loss_long:,.0f} ✅ [基于实时订单簿] ({distance_pct:.2f}%)")
    else:
        print(f"止损: 需手动设置（无法获取订单簿止损）")


if __name__ == "__main__":
    main()



