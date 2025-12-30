#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于De.的交易系统生成15分钟BTC交易计划
"""

import requests
from datetime import datetime
import json

def get_current_btc_price():
    """获取当前BTC价格（使用Gate.io API）"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': 'BTC_USDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['last'])
    except:
        pass
    return None

def get_btc_kline_data(timeframe='15m', limit=100):
    """获取BTC K线数据"""
    try:
        # 转换为Gate.io的interval格式
        interval_map = {
            '15m': '15m',
            '5m': '5m',
            '1h': '1h',
            '4h': '4h'
        }
        interval = interval_map.get(timeframe, '15m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # K线格式: [timestamp, volume, close, high, low, open]
            return data
    except Exception as e:
        print(f"获取K线数据失败: {e}")
    return None

def calculate_ema(prices, period):
    """计算EMA"""
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = [prices[0]]
    
    for price in prices[1:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    
    return ema[-1]

def calculate_vwap(kline_data):
    """计算VWAP（简化版，使用最近数据）"""
    if not kline_data or len(kline_data) < 1:
        return None
    
    total_volume_price = 0
    total_volume = 0
    
    for candle in kline_data:
        # K线格式: [timestamp, volume, close, high, low, open]
        volume = float(candle[1])
        close = float(candle[2])
        high = float(candle[3])
        low = float(candle[4])
        
        # 使用典型价格
        typical_price = (high + low + close) / 3
        total_volume_price += typical_price * volume
        total_volume += volume
    
    if total_volume > 0:
        return total_volume_price / total_volume
    return None

def analyze_trading_plan():
    """分析并生成交易计划"""
    print("=" * 80)
    print("基于De.交易系统的15分钟BTC交易计划")
    print("=" * 80)
    print()
    
    # 获取当前价格
    print("正在获取BTC价格数据...")
    current_price = get_current_btc_price()
    if current_price:
        print(f"当前BTC价格: ${current_price:,.2f}")
    else:
        print("无法获取当前价格，请手动查询")
        current_price = 0
    
    # 获取K线数据
    print("正在获取15分钟K线数据...")
    kline_15m = get_btc_kline_data('15m', 200)
    kline_1h = get_btc_kline_data('1h', 100)
    kline_4h = get_btc_kline_data('4h', 50)
    
    if not kline_15m:
        print("无法获取K线数据，将生成交易计划模板")
        return generate_template_plan(current_price)
    
    # 提取价格数据
    closes_15m = [float(c[2]) for c in kline_15m]
    closes_1h = [float(c[2]) for c in kline_1h] if kline_1h else []
    closes_4h = [float(c[2]) for c in kline_4h] if kline_4h else []
    
    # 计算指标
    print("正在计算技术指标...")
    ema144_15m = calculate_ema(closes_15m, 144) if len(closes_15m) >= 144 else None
    ema169_15m = calculate_ema(closes_15m, 169) if len(closes_15m) >= 169 else None
    vwap_15m = calculate_vwap(kline_15m)
    
    ema144_1h = calculate_ema(closes_1h, 144) if len(closes_1h) >= 144 and kline_1h else None
    ema169_1h = calculate_ema(closes_1h, 169) if len(closes_1h) >= 169 and kline_1h else None
    
    ema144_4h = calculate_ema(closes_4h, 144) if len(closes_4h) >= 144 and kline_4h else None
    ema169_4h = calculate_ema(closes_4h, 169) if len(closes_4h) >= 169 and kline_4h else None
    
    # 分析区间
    if ema144_15m and ema169_15m:
        vegas_lower = min(ema144_15m, ema169_15m)
        vegas_upper = max(ema144_15m, ema169_15m)
        vegas_range = vegas_upper - vegas_lower
        
        # 判断价格位置
        if current_price:
            if vegas_lower <= current_price <= vegas_upper:
                price_position = "在Vegas通道内（震荡区间）"
            elif current_price > vegas_upper:
                price_position = "在Vegas通道上方（可能突破）"
            else:
                price_position = "在Vegas通道下方（可能下跌）"
        else:
            price_position = "需要手动确认"
    else:
        vegas_lower = None
        vegas_upper = None
        vegas_range = None
        price_position = "需要更多数据计算"
    
    # 生成交易计划
    plan = []
    plan.append("=" * 80)
    plan.append("15分钟BTC交易计划")
    plan.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plan.append("=" * 80)
    plan.append("")
    
    # 一、当前市场状况
    plan.append("## 一、当前市场状况")
    plan.append("")
    if current_price:
        plan.append(f"**当前BTC价格**: ${current_price:,.2f}")
    plan.append("")
    
    # 二、技术指标分析
    plan.append("## 二、技术指标分析（15分钟图）")
    plan.append("")
    
    if ema144_15m and ema169_15m:
        plan.append("### Vegas通道（EMA144 + EMA169）")
        plan.append("")
        plan.append(f"- **EMA144**: ${ema144_15m:,.2f}")
        plan.append(f"- **EMA169**: ${ema169_15m:,.2f}")
        plan.append(f"- **Vegas通道范围**: ${vegas_lower:,.2f} - ${vegas_upper:,.2f}")
        plan.append(f"- **通道宽度**: ${vegas_range:,.2f} ({vegas_range/current_price*100:.2f}%)")
        plan.append(f"- **价格位置**: {price_position}")
        plan.append("")
        
        if vegas_range and vegas_range < current_price * 0.01:  # 小于1%
            plan.append("⚠️ **注意**: Vegas通道宽度较窄，可能不是好的交易区间")
        elif vegas_range and vegas_range > current_price * 0.05:  # 大于5%
            plan.append("⚠️ **注意**: Vegas通道宽度较大，需要确认是否在震荡区间内")
        plan.append("")
    else:
        plan.append("### Vegas通道")
        plan.append("需要至少144根K线数据才能计算EMA144/169")
        plan.append("请在交易软件上手动添加EMA144和EMA169指标")
        plan.append("")
    
    if vwap_15m:
        plan.append("### VWAP（成交量加权平均价格）")
        plan.append("")
        plan.append(f"- **15分钟VWAP**: ${vwap_15m:,.2f}")
        if current_price:
            if current_price > vwap_15m:
                plan.append(f"- **价格在VWAP上方** (${current_price - vwap_15m:,.2f})，VWAP作为支撑")
            else:
                plan.append(f"- **价格在VWAP下方** (${vwap_15m - current_price:,.2f})，VWAP作为阻力")
        plan.append("")
    else:
        plan.append("### VWAP")
        plan.append("请在交易软件上添加15分钟VWAP指标")
        plan.append("")
    
    # 三、多时间框架确认
    plan.append("## 三、多时间框架趋势确认")
    plan.append("")
    
    if ema144_1h and ema169_1h:
        plan.append("### 1小时图趋势")
        plan.append(f"- **1小时EMA144**: ${ema144_1h:,.2f}")
        plan.append(f"- **1小时EMA169**: ${ema169_1h:,.2f}")
        if current_price:
            if current_price > max(ema144_1h, ema169_1h):
                plan.append("- **趋势**: 上升趋势（价格在1小时Vegas通道上方）")
            elif current_price < min(ema144_1h, ema169_1h):
                plan.append("- **趋势**: 下降趋势（价格在1小时Vegas通道下方）")
            else:
                plan.append("- **趋势**: 震荡（价格在1小时Vegas通道内）")
        plan.append("")
    
    if ema144_4h and ema169_4h:
        plan.append("### 4小时图趋势（大趋势）")
        plan.append(f"- **4小时EMA144**: ${ema144_4h:,.2f}")
        plan.append(f"- **4小时EMA169**: ${ema169_4h:,.2f}")
        if current_price:
            if current_price > max(ema144_4h, ema169_4h):
                plan.append("- **大趋势**: 上升趋势（价格在4小时Vegas通道上方）")
            elif current_price < min(ema144_4h, ema169_4h):
                plan.append("- **大趋势**: 下降趋势（价格在4小时Vegas通道下方）")
            else:
                plan.append("- **大趋势**: 震荡（价格在4小时Vegas通道内）")
        plan.append("")
    
    # 四、交易区间识别
    plan.append("## 四、交易区间识别")
    plan.append("")
    plan.append("### 步骤1: 在图表上确认区间")
    plan.append("")
    plan.append("**操作**:")
    plan.append("1. 打开15分钟BTC图表")
    plan.append("2. 添加EMA144和EMA169指标")
    plan.append("3. 添加15分钟VWAP指标")
    plan.append("4. 观察价格在EMA144和EMA169之间的震荡区间")
    plan.append("")
    
    if ema144_15m and ema169_15m:
        plan.append("**当前计算的区间边界**:")
        plan.append(f"- **区间下沿（支撑）**: ${vegas_lower:,.2f} (EMA144附近)")
        plan.append(f"- **区间上沿（阻力）**: ${vegas_upper:,.2f} (EMA169附近)")
        plan.append(f"- **区间宽度**: ${vegas_range:,.2f}")
        plan.append("")
        plan.append("⚠️ **重要**: 请在图表上手动确认实际的区间边界，可能不是精确的EMA值")
        plan.append("")
    
    # 五、支撑阻力判断
    plan.append("## 五、支撑阻力判断")
    plan.append("")
    plan.append("### 综合判断方法")
    plan.append("")
    plan.append("**支撑位（多单入场参考）**:")
    plan.append("1. 区间下沿（EMA144附近）")
    if vwap_15m:
        plan.append(f"2. 15分钟VWAP: ${vwap_15m:,.2f}")
    plan.append("3. 大周期EMA144/169（如4小时EMA144）")
    plan.append("4. 流动性区域（大量挂单的位置）")
    plan.append("")
    plan.append("**阻力位（空单入场参考）**:")
    plan.append("1. 区间上沿（EMA169附近）")
    if vwap_15m:
        plan.append(f"2. 15分钟VWAP: ${vwap_15m:,.2f}")
    plan.append("3. 大周期EMA144/169（如4小时EMA169）")
    plan.append("4. 流动性区域（大量挂单的位置）")
    plan.append("")
    plan.append("**关键原则**:")
    plan.append("- 如果支撑阻力线与Vegas通道重合 = 绝杀信号（信号更强）")
    plan.append("- 如果支撑阻力线在Vegas通道外 = 按Vegas通道止盈止损")
    plan.append("")
    
    # 六、交易计划
    plan.append("## 六、具体交易计划")
    plan.append("")
    plan.append("### 交易前检查清单")
    plan.append("")
    plan.append("□ 1. 已识别明确的震荡区间（15分钟Vegas通道内）")
    plan.append("□ 2. 区间宽度足够（至少200-500点）")
    plan.append("□ 3. 已确认支撑阻力位置（Vegas + VWAP）")
    plan.append("□ 4. 已确认大趋势方向（4小时Vegas通道）")
    plan.append("□ 5. 已设置止损（假突破不能打到）")
    plan.append("□ 6. 已设置止盈（2倍以上盈亏比）")
    plan.append("□ 7. 已计算仓位大小（风险不超过5%）")
    plan.append("□ 8. 已使用逐仓模式")
    plan.append("□ 9. 确认不是单边行情")
    plan.append("□ 10. 盈亏比≥2倍")
    plan.append("")
    plan.append("**只有所有项目都确认后，才能执行交易！**")
    plan.append("")
    
    # 七、多单计划
    plan.append("### 多单交易计划")
    plan.append("")
    plan.append("**入场条件（全部满足）**:")
    plan.append("1. 价格回落到区间下沿（EMA144附近）")
    if vwap_15m:
        plan.append(f"2. VWAP在下方作为支撑（当前VWAP: ${vwap_15m:,.2f}）")
    plan.append("3. 大周期趋势向上（4小时EMA144/169向上）")
    plan.append("4. 在区间下沿+10-20点挂买单")
    plan.append("")
    plan.append("**止损设置**:")
    plan.append("- 位置：区间下沿下方，假突破不能打到的位置")
    plan.append("- 距离：通常30-100点（根据区间大小调整）")
    plan.append("- 参考：不要破大周期EMA144")
    plan.append("")
    plan.append("**止盈设置**:")
    plan.append("- 第一目标：区间上沿附近（EMA169附近）")
    if vwap_15m:
        plan.append(f"- 第二目标：VWAP位置（${vwap_15m:,.2f}）")
    plan.append("- 分批止盈：50%在目标位置，50%看情况")
    plan.append("- 盈亏比：至少2倍（止损30点，止盈至少60点）")
    plan.append("")
    
    # 八、空单计划
    plan.append("### 空单交易计划")
    plan.append("")
    plan.append("**入场条件（全部满足）**:")
    plan.append("1. 价格反弹到区间上沿（EMA169附近）")
    if vwap_15m:
        plan.append(f"2. VWAP在上方作为阻力（当前VWAP: ${vwap_15m:,.2f}）")
    plan.append("3. 大周期趋势向下（4小时EMA144/169向下）")
    plan.append("4. 在区间上沿-10-20点挂卖单")
    plan.append("")
    plan.append("**止损设置**:")
    plan.append("- 位置：区间上沿上方，假突破不能打到的位置")
    plan.append("- 距离：通常30-100点（根据区间大小调整）")
    plan.append("- 参考：不要破大周期EMA169")
    plan.append("")
    plan.append("**止盈设置**:")
    plan.append("- 第一目标：区间下沿附近（EMA144附近）")
    if vwap_15m:
        plan.append(f"- 第二目标：VWAP位置（${vwap_15m:,.2f}）")
    plan.append("- 分批止盈：50%在目标位置，50%看情况")
    plan.append("- 盈亏比：至少2倍（止损30点，止盈至少60点）")
    plan.append("")
    
    # 九、风险提示
    plan.append("## 七、风险提示")
    plan.append("")
    plan.append("1. **单边行情回避**")
    plan.append("   - 如果价格突破Vegas通道并站稳，立即止损")
    plan.append("   - 震荡能赚，单边死亏")
    plan.append("")
    plan.append("2. **区间失效处理**")
    plan.append("   - 震荡区间挂单，越到后面越不灵")
    plan.append("   - 如果区间被突破，撤销挂单")
    plan.append("   - 突破后重新识别新区间")
    plan.append("")
    plan.append("3. **不要追涨杀跌**")
    plan.append("   - 必须挂单等待，不要追价")
    plan.append("   - 挂单价格要合理，不要偏离区间太远")
    plan.append("")
    plan.append("4. **严格止损**")
    plan.append("   - 止损是生命线，必须严格执行")
    plan.append("   - 不要移动止损，不要心存侥幸")
    plan.append("")
    
    # 十、注意事项
    plan.append("## 八、重要注意事项")
    plan.append("")
    plan.append("⚠️ **本交易计划基于技术指标计算，但实际交易需要：**")
    plan.append("")
    plan.append("1. **在图表上手动确认**")
    plan.append("   - 实际区间边界可能与计算值有差异")
    plan.append("   - 需要结合K线形态、成交量等综合判断")
    plan.append("")
    plan.append("2. **实时监控**")
    plan.append("   - 市场情况随时变化")
    plan.append("   - 需要根据实时价格调整计划")
    plan.append("")
    plan.append("3. **风险控制**")
    plan.append("   - 单次交易风险不超过账户的5%")
    plan.append("   - 使用逐仓模式")
    plan.append("   - 严格执行止损")
    plan.append("")
    
    return "\n".join(plan)

def generate_template_plan(current_price):
    """生成交易计划模板"""
    plan = []
    plan.append("=" * 80)
    plan.append("15分钟BTC交易计划（模板）")
    plan.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if current_price:
        plan.append(f"当前BTC价格: ${current_price:,.2f}")
    plan.append("=" * 80)
    plan.append("")
    plan.append("⚠️ **注意**: 无法获取完整数据，请按照以下步骤手动分析")
    plan.append("")
    plan.append("## 一、设置图表指标")
    plan.append("")
    plan.append("1. 打开15分钟BTC图表")
    plan.append("2. 添加EMA144指标")
    plan.append("3. 添加EMA169指标（Vegas通道）")
    plan.append("4. 添加15分钟VWAP指标")
    plan.append("5. 添加1小时EMA144/169（趋势确认）")
    plan.append("6. 添加4小时EMA144/169（大趋势确认）")
    plan.append("")
    plan.append("## 二、识别交易区间")
    plan.append("")
    plan.append("1. 观察价格在EMA144和EMA169之间的震荡")
    plan.append("2. 确定区间上沿（通常是EMA169或更高点）")
    plan.append("3. 确定区间下沿（通常是EMA144或更低点）")
    plan.append("4. 确认区间宽度至少200-500点")
    plan.append("")
    plan.append("## 三、判断支撑阻力")
    plan.append("")
    plan.append("**支撑位**:")
    plan.append("- 区间下沿（EMA144附近）")
    plan.append("- 15分钟VWAP位置")
    plan.append("- 4小时EMA144（大周期支撑）")
    plan.append("")
    plan.append("**阻力位**:")
    plan.append("- 区间上沿（EMA169附近）")
    plan.append("- 15分钟VWAP位置")
    plan.append("- 4小时EMA169（大周期阻力）")
    plan.append("")
    plan.append("## 四、交易计划")
    plan.append("")
    plan.append("按照De.交易系统的完整流程执行：")
    plan.append("1. 确认所有检查清单项目")
    plan.append("2. 在支撑/阻力位置挂单")
    plan.append("3. 设置止损（假突破不能打到）")
    plan.append("4. 设置止盈（2倍以上盈亏比）")
    plan.append("5. 严格执行风险控制")
    plan.append("")
    return "\n".join(plan)

def main():
    plan = analyze_trading_plan()
    
    # 保存计划
    output_file = "BTC_15m_trading_plan.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(plan)
    
    print()
    print("=" * 80)
    print("交易计划已生成！")
    print("=" * 80)
    print(f"文件已保存到: {output_file}")
    print()
    print("交易计划已成功生成，请查看文件内容")

if __name__ == "__main__":
    main()

