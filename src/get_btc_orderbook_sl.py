#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC实时订单簿止损查询工具
显示做多和做空两个方向的止损建议
"""

import sys
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 添加src目录到路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

try:
    from get_realtime_stop_loss import (
        get_order_book_with_retry,
        get_current_price,
        calculate_stop_loss_by_orderbook
    )
except ImportError as e:
    print(f"导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def format_price(price):
    """格式化价格"""
    return f"${price:,.2f}"


def format_distance(entry, stop_loss, signal_type):
    """计算并格式化止损距离"""
    if signal_type == 'long':
        distance = entry - stop_loss
        distance_pct = (distance / entry) * 100
    else:
        distance = stop_loss - entry
        distance_pct = (distance / entry) * 100
    
    return distance, distance_pct


def get_stop_loss_info(symbol='BTC', entry_price=None, signal_type='long'):
    """获取止损信息"""
    # 获取当前价格
    current_price = get_current_price(symbol)
    if not current_price:
        return None, None, None, None
    
    # 如果没有提供入场价，使用当前价格
    if entry_price is None:
        entry_price = current_price
    
    # 获取订单簿
    order_book, exchange_name = get_order_book_with_retry(symbol, limit=100)
    if not order_book:
        return None, None, None, None
    
    # 计算止损
    stop_loss, info = calculate_stop_loss_by_orderbook(
        entry_price, signal_type, order_book, current_price
    )
    
    return stop_loss, info, exchange_name, current_price


def main():
    """主函数"""
    print("=" * 80)
    print("BTC 实时订单簿止损查询")
    print("=" * 80)
    print()
    
    # 获取做多止损
    print("📈 做多方向止损分析")
    print("-" * 80)
    stop_loss_long, info_long, exchange_long, current_price = get_stop_loss_info(
        'BTC', None, 'long'
    )
    
    if current_price:
        print(f"当前价格: {format_price(current_price)}")
        print(f"数据来源: {exchange_long}")
        print()
    
    if stop_loss_long and info_long:
        distance, distance_pct = format_distance(current_price, stop_loss_long, 'long')
        print(f"✅ **做多止损**: {format_price(stop_loss_long)}")
        print(f"   止损距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
        if info_long.get('source_info'):
            print(f"   来源: {info_long['source_info']}")
        if info_long.get('is_from_orderbook'):
            print(f"   ✅ 基于实时订单簿")
        else:
            print(f"   ⚠️  备用方案（非订单簿实际价格）")
    else:
        print("❌ 无法获取做多止损")
    
    print()
    print()
    
    # 获取做空止损
    print("📉 做空方向止损分析")
    print("-" * 80)
    stop_loss_short, info_short, exchange_short, _ = get_stop_loss_info(
        'BTC', None, 'short'
    )
    
    if stop_loss_short and info_short:
        distance, distance_pct = format_distance(current_price, stop_loss_short, 'short')
        print(f"✅ **做空止损**: {format_price(stop_loss_short)}")
        print(f"   止损距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
        if info_short.get('source_info'):
            print(f"   来源: {info_short['source_info']}")
        if info_short.get('is_from_orderbook'):
            print(f"   ✅ 基于实时订单簿")
        else:
            print(f"   ⚠️  备用方案（非订单簿实际价格）")
    else:
        print("❌ 无法获取做空止损")
        print("   提示: 做空止损可能需要指定入场价")
        print("   用法: python src/get_realtime_stop_loss.py BTC short sl <入场价>")
    
    print()
    print("=" * 80)
    print()
    
    # 如果有指定入场价，也计算一下
    if len(sys.argv) > 1:
        try:
            entry_price = float(sys.argv[1])
            print(f"📊 指定入场价分析: {format_price(entry_price)}")
            print("-" * 80)
            
            # 做多
            if entry_price < current_price:
                sl_long, info_long, _, _ = get_stop_loss_info('BTC', entry_price, 'long')
                if sl_long:
                    distance, distance_pct = format_distance(entry_price, sl_long, 'long')
                    print(f"做多止损: {format_price(sl_long)} (距离: {distance:,.0f}点, {distance_pct:.2f}%)")
            
            # 做空
            if entry_price > current_price:
                sl_short, info_short, _, _ = get_stop_loss_info('BTC', entry_price, 'short')
                if sl_short:
                    distance, distance_pct = format_distance(entry_price, sl_short, 'short')
                    print(f"做空止损: {format_price(sl_short)} (距离: {distance:,.0f}点, {distance_pct:.2f}%)")
            
            print()
        except ValueError:
            pass
    
    print("💡 提示: 如需指定入场价，运行:")
    print("   python src/get_realtime_stop_loss.py BTC long sl <入场价>")
    print("   python src/get_realtime_stop_loss.py BTC short sl <入场价>")


if __name__ == "__main__":
    main()


