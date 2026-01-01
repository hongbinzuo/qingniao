"""
检查止损逻辑和订单簿使用情况
"""

import sys
import io
from generate_btc_multi_tf_plan import (
    get_order_book_gateio, get_order_book_bitget,
    analyze_liquidity_zones, suggest_stop_loss_by_liquidity,
    get_btc_current_price
)

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def check_stop_loss():
    """检查止损逻辑"""
    print("=" * 70)
    print("止损逻辑检查")
    print("=" * 70)
    
    # 获取当前价格
    current_price = get_btc_current_price()
    if not current_price:
        print("无法获取当前价格")
        return
    
    print(f"\n当前BTC价格: ${current_price:,.2f}")
    
    # 获取订单簿
    print("\n正在获取订单簿...")
    order_book = get_order_book_gateio(limit=50)
    if not order_book:
        print("Gate.io订单簿获取失败，尝试Bitget...")
        order_book = get_order_book_bitget(limit=50)
    
    if not order_book:
        print("❌ 无法获取订单簿数据")
        print("\n问题分析:")
        print("  - 系统尝试获取实时订单簿，但API调用失败")
        print("  - 因此使用了默认止损（入场价上方1.5%）")
        print("  - 这就是为什么止损看起来比较宽的原因")
        return
    
    print("✅ 订单簿获取成功")
    
    # 分析流动性
    liquidity_analysis = analyze_liquidity_zones(order_book, current_price)
    if not liquidity_analysis:
        print("❌ 无法分析流动性")
        return
    
    print("\n" + "-" * 70)
    print("流动性分析结果:")
    print("-" * 70)
    
    # 显示卖单密集区（做空止损相关）
    dense_ask_zones = liquidity_analysis.get('dense_ask_zones', [])
    sparse_ask_zones = liquidity_analysis.get('sparse_ask_zones', [])
    no_trade_ask_zones = liquidity_analysis.get('no_trade_ask_zones', [])
    
    print(f"\n卖单密集区（阻力位）: {len(dense_ask_zones)}个")
    if dense_ask_zones:
        for i, zone in enumerate(dense_ask_zones[:5], 1):
            print(f"  {i}. ${zone:,.0f}")
    else:
        print("  ⚠️ 未发现明显的卖单密集区")
    
    print(f"\n卖单稀疏区（适合止损）: {len(sparse_ask_zones)}个")
    if sparse_ask_zones:
        for i, zone in enumerate(sparse_ask_zones[:5], 1):
            print(f"  {i}. ${zone:,.0f}")
    else:
        print("  ⚠️ 未发现明显的卖单稀疏区")
    
    if no_trade_ask_zones:
        print(f"\n不开单区域（De.规则）: {len(no_trade_ask_zones)}个")
        for i, zone in enumerate(no_trade_ask_zones[:3], 1):
            print(f"  {i}. 密集区${zone['center']:,.0f}的不开单区域: ${zone['lower_bound']:,.0f} - ${zone['upper_bound']:,.0f}")
    
    # 测试止损计算
    print("\n" + "-" * 70)
    print("止损计算测试（基于最新信号）:")
    print("-" * 70)
    
    # 最新信号的入场价
    entry_price = 87639  # 15分钟做空信号的入场价
    print(f"\n入场价: ${entry_price:,.2f}")
    
    # 计算基于流动性的止损
    liquidity_stop_loss, liquidity_info = suggest_stop_loss_by_liquidity(
        entry_price, 'short', liquidity_analysis
    )
    
    if liquidity_stop_loss:
        print(f"\n✅ 基于流动性的止损: ${liquidity_stop_loss:,.2f}")
        if liquidity_info:
            print(f"  止损距离: {liquidity_info['distance']:,.0f}点 ({liquidity_info['distance_pct']:.2f}%)")
            print(f"  止损理由: {liquidity_info['reason']}")
            if liquidity_info.get('resistance_zone'):
                print(f"  卖单密集区（阻力）: ${liquidity_info['resistance_zone']:,.0f}")
    else:
        print("\n❌ 无法计算基于流动性的止损")
        print("  原因: 未发现明显的卖单密集区")
        print("  系统使用默认止损: 入场价上方1.5%")
        default_stop = entry_price * 1.015
        print(f"  默认止损: ${default_stop:,.2f} (距离: {default_stop - entry_price:,.0f}点)")
    
    # 对比
    print("\n" + "-" * 70)
    print("止损对比:")
    print("-" * 70)
    print(f"  入场价: ${entry_price:,.2f}")
    if liquidity_stop_loss:
        print(f"  流动性止损: ${liquidity_stop_loss:,.2f} (距离: {liquidity_stop_loss - entry_price:,.0f}点)")
    default_stop = entry_price * 1.015
    print(f"  默认止损: ${default_stop:,.2f} (距离: {default_stop - entry_price:,.0f}点)")
    print(f"  信号文件中的止损: $88,954 (距离: 1315点)")
    
    # 分析为什么止损宽
    print("\n" + "=" * 70)
    print("止损宽度分析:")
    print("=" * 70)
    
    if not dense_ask_zones:
        print("\n问题1: 未发现明显的卖单密集区")
        print("  - 订单簿中可能没有明显的卖单集中区域")
        print("  - 或者卖单分布比较均匀，没有形成密集区")
        print("  - 系统因此使用默认止损（1.5%）")
    
    if liquidity_stop_loss and liquidity_stop_loss == default_stop:
        print("\n问题2: 流动性止损等于默认止损")
        print("  - 说明订单簿分析没有找到更好的止损位置")
        print("  - 可能的原因:")
        print("    1. 订单簿深度不够")
        print("    2. 卖单分布均匀，没有明显的密集/稀疏区")
        print("    3. 所有候选止损都在不开单区域内")
    
    print("\n建议:")
    print("  1. 手动观察订单簿，找到真实的卖单密集区")
    print("  2. 根据实际流动性设置止损")
    print("  3. 如果订单簿数据不准确，可以调整止损计算逻辑")
    print("  4. 考虑使用技术指标止损作为补充（如Vegas通道上方）")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    check_stop_loss()


