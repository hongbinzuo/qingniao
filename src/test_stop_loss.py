#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试止损计算"""

from get_realtime_stop_loss import get_order_book_with_retry, get_current_price, calculate_stop_loss_by_orderbook

# 获取订单簿
print("获取订单簿...")
order_book, exchange = get_order_book_with_retry('BTC', 50)
print(f"订单簿: {order_book is not None}, 交易所: {exchange}")
if order_book:
    print(f"买单数量: {len(order_book.get('bids', []))}")
    print(f"卖单数量: {len(order_book.get('asks', []))}")

# 获取当前价格
print("\n获取当前价格...")
current_price = get_current_price('BTC')
print(f"当前价格: {current_price}")

# 计算止损
print("\n计算止损...")
entry_price = 87503
result = calculate_stop_loss_by_orderbook(entry_price, 'long', order_book, current_price)
print(f"结果: {result}")
if result[0]:
    print(f"止损价: {result[0]}")
    print(f"信息: {result[1]}")

