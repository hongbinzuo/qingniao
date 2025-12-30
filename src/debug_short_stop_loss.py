#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试做空止损计算
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

from get_realtime_stop_loss import (
    get_order_book_with_retry,
    get_current_price,
    analyze_liquidity_zones,
    calculate_stop_loss_by_orderbook
)

def main():
    entry_price = 88900
    symbol = 'BTC'
    
    print("=" * 80)
    print(f"调试做空止损计算 - 入场价: ${entry_price:,.2f}")
    print("=" * 80)
    print()
    
    # 获取当前价格
    current_price = get_current_price(symbol)
    print(f"当前价格: ${current_price:,.2f}")
    print()
    
    # 获取订单簿
    order_book, exchange_name = get_order_book_with_retry(symbol, limit=100)
    if not order_book:
        print("❌ 无法获取订单簿")
        return
    
    print(f"数据来源: {exchange_name}")
    print()
    
    # 分析流动性
    liquidity_analysis = analyze_liquidity_zones(order_book, current_price)
    
    asks = order_book.get('asks', [])
    bids = order_book.get('bids', [])
    
    print("订单簿分析:")
    print(f"  买单数量: {len(bids)}")
    print(f"  卖单数量: {len(asks)}")
    print()
    
    # 显示入场价上方的卖单
    above_entry = [(price, amount) for price, amount in asks if price > entry_price]
    print(f"入场价(${entry_price:,.2f})上方的卖单: {len(above_entry)} 个")
    if above_entry:
        print("前10个卖单:")
        for i, (price, amount) in enumerate(above_entry[:10], 1):
            distance = price - entry_price
            distance_pct = (distance / entry_price) * 100
            print(f"  {i}. ${price:,.2f} - 挂单量: {amount:.4f} BTC - 距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
    print()
    
    # 显示流动性分析结果
    if liquidity_analysis:
        dense_ask_zones = liquidity_analysis.get('dense_ask_zones', [])
        sparse_ask_zones = liquidity_analysis.get('sparse_ask_zones', [])
        
        print("流动性分析:")
        print(f"  卖单密集区: {len(dense_ask_zones)} 个")
        if dense_ask_zones:
            print("  密集区列表:")
            for price, vol in dense_ask_zones[:5]:
                if price > entry_price:
                    distance = price - entry_price
                    distance_pct = (distance / entry_price) * 100
                    print(f"    ${price:,.2f} - 挂单量: {vol:.2f} - 距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
        
        print(f"  卖单稀疏区: {len(sparse_ask_zones)} 个")
        if sparse_ask_zones:
            print("  稀疏区列表（入场价上方）:")
            for price, vol in sparse_ask_zones:
                if price > entry_price:
                    distance = price - entry_price
                    distance_pct = (distance / entry_price) * 100
                    print(f"    ${price:,.2f} - 挂单量: {vol:.2f} - 距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
    print()
    
    # 尝试计算止损
    print("尝试计算止损...")
    stop_loss, info = calculate_stop_loss_by_orderbook(
        entry_price, 'short', order_book, current_price
    )
    
    if stop_loss:
        distance = stop_loss - entry_price
        distance_pct = (distance / entry_price) * 100
        print(f"✅ 止损计算成功: ${stop_loss:,.2f}")
        print(f"   距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
        if info:
            print(f"   信息: {info.get('source_info', 'N/A')}")
    else:
        print("❌ 无法计算止损")
        print()
        print("可能的原因:")
        print("  1. 入场价上方没有找到合适的阻力位")
        print("  2. 阻力位上方没有找到稀疏区")
        print("  3. 止损距离超出限制（0.3%-3%）")
        print("  4. 订单簿数据不足")
        
        # 尝试使用备用方案
        print()
        print("尝试备用方案...")
        # 找到当前价格上方的卖单
        above_current = [(price, amount) for price, amount in asks if price > current_price]
        print(f"当前价格(${current_price:,.2f})上方的卖单: {len(above_current)} 个")
        if above_current:
            print("前5个卖单:")
            for i, (price, amount) in enumerate(above_current[:5], 1):
                distance_from_current = price - current_price
                distance_pct_from_current = (distance_from_current / current_price) * 100
                print(f"  {i}. ${price:,.2f} - 挂单量: {amount:.4f} BTC - 距当前价: {distance_from_current:,.0f}点 ({distance_pct_from_current:.2f}%)")
            
            # 找到挂单量最大的作为阻力位
            above_current.sort(key=lambda x: x[1], reverse=True)
            top_resistances = sorted([x for x in above_current[:3]], key=lambda x: x[0])
            if top_resistances:
                resistance_price, resistance_amount = top_resistances[0]
                print()
                print(f"选择阻力位: ${resistance_price:,.2f} (挂单量: {resistance_amount:.4f} BTC)")
                
                # 计算入场价相对于当前价格的偏移
                price_offset = entry_price - current_price
                print(f"入场价偏移: {price_offset:,.0f}点 ({(price_offset/current_price)*100:.2f}%)")
                
                # 在阻力位上方，加上相同的偏移量
                estimated_stop_loss = resistance_price + price_offset
                print(f"估算止损: ${estimated_stop_loss:,.2f}")
                
                # 确保止损在入场价上方
                if estimated_stop_loss <= entry_price:
                    estimated_stop_loss = entry_price * 1.003  # 至少0.3%
                    print(f"调整后止损: ${estimated_stop_loss:,.2f} (至少0.3%)")
                
                distance = estimated_stop_loss - entry_price
                distance_pct = (distance / entry_price) * 100
                print(f"止损距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
                
                if 0.3 <= distance_pct <= 3.0:
                    print(f"✅ 备用方案可行: ${estimated_stop_loss:,.2f}")
                else:
                    print(f"❌ 距离不在范围内 (需要0.3%-3%)")
        
        if above_entry:
            # 找到挂单量最大的作为阻力位
            above_entry.sort(key=lambda x: x[1], reverse=True)
            resistance_price, resistance_amount = above_entry[0]
            
            # 在阻力位上方找价格档位
            above_resistance = [price for price, amount in asks if price > resistance_price]
            if above_resistance:
                nearest_above = min(above_resistance)
                stop_loss_manual = nearest_above
                distance = stop_loss_manual - entry_price
                distance_pct = (distance / entry_price) * 100
                
                print(f"  阻力位: ${resistance_price:,.2f} (挂单量: {resistance_amount:.4f} BTC)")
                print(f"  建议止损: ${stop_loss_manual:,.2f}")
                print(f"  距离: {distance:,.0f}点 ({distance_pct:.2f}%)")
                
                if distance_pct < 0.3:
                    print(f"  ⚠️  距离太近，建议至少0.3%: ${entry_price * 1.003:,.2f}")
                elif distance_pct > 3.0:
                    print(f"  ⚠️  距离太远，建议不超过3%: ${entry_price * 1.03:,.2f}")

if __name__ == "__main__":
    main()

