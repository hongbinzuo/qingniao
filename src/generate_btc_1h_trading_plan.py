#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于De.的交易系统生成1小时BTC交易计划
"""

import requests
from datetime import datetime

def get_current_btc_price():
    """获取当前BTC价格"""
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

def get_btc_kline_data(timeframe='1h', limit=200):
    """获取BTC K线数据"""
    try:
        interval_map = {
            '1h': '1h',
            '4h': '4h',
            '15m': '15m'
        }
        interval = interval_map.get(timeframe, '1h')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BTC_USDT',
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
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
    """计算VWAP"""
    if not kline_data or len(kline_data) < 1:
        return None
    
    total_volume_price = 0
    total_volume = 0
    
    for candle in kline_data:
        volume = float(candle[1])
        close = float(candle[2])
        high = float(candle[3])
        low = float(candle[4])
        
        typical_price = (high + low + close) / 3
        total_volume_price += typical_price * volume
        total_volume += volume
    
    if total_volume > 0:
        return total_volume_price / total_volume
    return None

def generate_1h_plan():
    """生成1小时交易计划"""
    print("正在生成1小时BTC交易计划...")
    
    current_price = get_current_btc_price()
    kline_1h = get_btc_kline_data('1h', 200)
    kline_4h = get_btc_kline_data('4h', 100)
    
    plan = []
    plan.append("=" * 80)
    plan.append("1小时BTC交易计划")
    plan.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plan.append("=" * 80)
    plan.append("")
    
    # 一、1小时级别交易特点
    plan.append("## 一、1小时级别交易特点")
    plan.append("")
    plan.append("根据De.的交易系统，1小时时间框架的特点：")
    plan.append("")
    plan.append("**优势**:")
    plan.append("- 区间更稳定，波动相对较小")
    plan.append("- 适合挂单后长时间等待")
    plan.append("- 适合不能经常看盘的交易者")
    plan.append("- 持仓时间：2-8小时")
    plan.append("")
    plan.append("**劣势**:")
    plan.append("- 持仓时间较长，需要更大资金承受波动")
    plan.append("- 止损距离较大（100-200点）")
    plan.append("- 需要更大的区间宽度（500-1000点）")
    plan.append("")
    
    # 二、当前市场状况
    plan.append("## 二、当前市场状况")
    plan.append("")
    if current_price:
        plan.append(f"**当前BTC价格**: ${current_price:,.2f}")
    plan.append("")
    
    # 三、技术指标分析
    plan.append("## 三、技术指标分析（1小时图）")
    plan.append("")
    
    if kline_1h:
        closes_1h = [float(c[2]) for c in kline_1h]
        ema144_1h = calculate_ema(closes_1h, 144) if len(closes_1h) >= 144 else None
        ema169_1h = calculate_ema(closes_1h, 169) if len(closes_1h) >= 169 else None
        vwap_1h = calculate_vwap(kline_1h)
        
        if ema144_1h and ema169_1h:
            vegas_lower = min(ema144_1h, ema169_1h)
            vegas_upper = max(ema144_1h, ema169_1h)
            vegas_range = vegas_upper - vegas_lower
            
            plan.append("### Vegas通道（EMA144 + EMA169）")
            plan.append("")
            plan.append(f"- **EMA144**: ${ema144_1h:,.2f}")
            plan.append(f"- **EMA169**: ${ema169_1h:,.2f}")
            plan.append(f"- **Vegas通道范围**: ${vegas_lower:,.2f} - ${vegas_upper:,.2f}")
            plan.append(f"- **通道宽度**: ${vegas_range:,.2f} ({vegas_range/current_price*100:.2f}%)")
            
            if current_price:
                if vegas_lower <= current_price <= vegas_upper:
                    plan.append(f"- **价格位置**: 在Vegas通道内（震荡区间）")
                elif current_price > vegas_upper:
                    plan.append(f"- **价格位置**: 在Vegas通道上方（可能突破）")
                else:
                    plan.append(f"- **价格位置**: 在Vegas通道下方（可能下跌）")
            
            # 判断是否适合交易
            if vegas_range and vegas_range < current_price * 0.005:  # 小于0.5%
                plan.append("")
                plan.append("⚠️ **注意**: Vegas通道宽度较窄，可能不是好的交易区间")
                plan.append("   建议：等待更大的区间形成，或查看4小时图")
            elif vegas_range and vegas_range >= current_price * 0.005:  # 大于0.5%
                plan.append("")
                plan.append("✓ **通道宽度**: 符合1小时级别交易要求（500-1000点）")
            plan.append("")
        
        if vwap_1h:
            plan.append("### VWAP（成交量加权平均价格）")
            plan.append("")
            plan.append(f"- **1小时VWAP**: ${vwap_1h:,.2f}")
            if current_price:
                if current_price > vwap_1h:
                    plan.append(f"- **价格在VWAP上方** (${current_price - vwap_1h:,.2f})，VWAP作为支撑")
                else:
                    plan.append(f"- **价格在VWAP下方** (${vwap_1h - current_price:,.2f})，VWAP作为阻力")
            plan.append("")
    
    # 四、4小时大趋势确认
    plan.append("## 四、4小时大趋势确认（重要）")
    plan.append("")
    plan.append("根据De.的系统，1小时交易必须确认4小时大趋势：")
    plan.append("")
    
    if kline_4h:
        closes_4h = [float(c[2]) for c in kline_4h]
        ema144_4h = calculate_ema(closes_4h, 144) if len(closes_4h) >= 144 else None
        ema169_4h = calculate_ema(closes_4h, 169) if len(closes_4h) >= 169 else None
        
        if ema144_4h and ema169_4h:
            plan.append("### 4小时Vegas通道")
            plan.append("")
            plan.append(f"- **4小时EMA144**: ${ema144_4h:,.2f}")
            plan.append(f"- **4小时EMA169**: ${ema169_4h:,.2f}")
            if current_price:
                if current_price > max(ema144_4h, ema169_4h):
                    plan.append("- **大趋势**: 上升趋势（价格在4小时Vegas通道上方）")
                    plan.append("- **交易建议**: 优先考虑多单，空单需谨慎")
                elif current_price < min(ema144_4h, ema169_4h):
                    plan.append("- **大趋势**: 下降趋势（价格在4小时Vegas通道下方）")
                    plan.append("- **交易建议**: 优先考虑空单，多单需谨慎")
                else:
                    plan.append("- **大趋势**: 震荡（价格在4小时Vegas通道内）")
                    plan.append("- **交易建议**: 可以双向交易，但需严格止损")
            plan.append("")
    
    # 五、1小时交易计划
    plan.append("## 五、1小时级别交易计划")
    plan.append("")
    plan.append("### 交易参数设置")
    plan.append("")
    plan.append("**区间要求**:")
    plan.append("- 区间宽度：500-1000点（BTC价格）")
    plan.append("- 区间边界：1小时Vegas通道（EMA144/169）")
    plan.append("")
    plan.append("**止损设置**:")
    plan.append("- 止损距离：100-200点")
    plan.append("- 止损位置：假突破不能打到的位置")
    plan.append("- 参考：不要破4小时EMA144/169")
    plan.append("")
    plan.append("**止盈设置**:")
    plan.append("- 止盈距离：200-400点（2倍以上盈亏比）")
    plan.append("- 止盈位置：区间上下沿或VWAP位置")
    plan.append("- 分批止盈：50%在目标位置，50%看情况")
    plan.append("")
    plan.append("**持仓时间**:")
    plan.append("- 预计持仓：2-8小时")
    plan.append("- 可以挂单后不看盘，等待成交")
    plan.append("")
    
    # 六、多单计划
    plan.append("### 多单交易计划")
    plan.append("")
    plan.append("**入场条件（全部满足）**:")
    plan.append("1. 价格回落到1小时区间下沿（EMA144附近）")
    plan.append("2. 1小时VWAP在下方作为支撑")
    plan.append("3. 4小时大趋势向上（价格在4小时Vegas通道上方）")
    plan.append("4. 在区间下沿+20-50点挂买单")
    plan.append("")
    plan.append("**止损**: 区间下沿下方100-200点")
    plan.append("**止盈**: 区间上沿附近，或200-400点")
    plan.append("")
    
    # 七、空单计划
    plan.append("### 空单交易计划")
    plan.append("")
    plan.append("**入场条件（全部满足）**:")
    plan.append("1. 价格反弹到1小时区间上沿（EMA169附近）")
    plan.append("2. 1小时VWAP在上方作为阻力")
    plan.append("3. 4小时大趋势向下（价格在4小时Vegas通道下方）")
    plan.append("4. 在区间上沿-20-50点挂卖单")
    plan.append("")
    plan.append("**止损**: 区间上沿上方100-200点")
    plan.append("**止盈**: 区间下沿附近，或200-400点")
    plan.append("")
    
    # 八、是否适合交易
    plan.append("## 六、1小时级别是否适合交易？")
    plan.append("")
    plan.append("### 适合交易的情况")
    plan.append("")
    plan.append("✓ **适合交易**，如果：")
    plan.append("1. 1小时Vegas通道宽度≥500点")
    plan.append("2. 价格在1小时Vegas通道内震荡")
    plan.append("3. 4小时大趋势明确（向上或向下）")
    plan.append("4. 有足够资金承受100-200点止损")
    plan.append("5. 可以持仓2-8小时")
    plan.append("6. 不能经常看盘（适合挂单交易）")
    plan.append("")
    plan.append("### 不适合交易的情况")
    plan.append("")
    plan.append("✗ **不适合交易**，如果：")
    plan.append("1. 1小时Vegas通道宽度<500点（区间太窄）")
    plan.append("2. 价格已突破Vegas通道（单边行情）")
    plan.append("3. 4小时大趋势不明确（震荡）")
    plan.append("4. 资金不足以承受100-200点止损")
    plan.append("5. 需要频繁看盘（建议用15分钟）")
    plan.append("")
    
    return "\n".join(plan)

def main():
    plan = generate_1h_plan()
    
    output_file = "BTC_1h_trading_plan.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(plan)
    
    print()
    print("=" * 80)
    print("1小时交易计划已生成！")
    print("=" * 80)
    print(f"文件已保存到: {output_file}")

if __name__ == "__main__":
    main()




