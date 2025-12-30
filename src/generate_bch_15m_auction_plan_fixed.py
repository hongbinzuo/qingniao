#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于De.交易系统（融入拍卖理论）生成BCH 15分钟交易计划
修正版：根据币种价格调整区间宽度判断标准
"""

import requests
from datetime import datetime, timezone
import json

def get_current_bch_price():
    """获取当前BCH价格"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {'currency_pair': 'BCH_USDT'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['last'])
    except Exception as e:
        print(f"获取价格失败: {e}")
    return None

def get_bch_kline_data(timeframe='15m', limit=200):
    """获取BCH K线数据"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': 'BCH_USDT',
            'interval': timeframe,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            klines = []
            for k in data:
                klines.append({
                    'timestamp': int(k[0]),
                    'open': float(k[5]),
                    'high': float(k[3]),
                    'low': float(k[4]),
                    'close': float(k[2]),
                    'volume': float(k[1])
                })
            return list(reversed(klines))
    except Exception as e:
        print(f"获取K线数据失败: {e}")
    return None

def calculate_ema(prices, period):
    """计算EMA"""
    if len(prices) < period:
        return None
    
    multiplier = 2.0 / (period + 1)
    ema = [prices[0]]
    
    for i in range(1, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    
    return ema[-1]

def calculate_vwap(klines):
    """计算VWAP（成交量加权平均价）"""
    if not klines:
        return None
    
    total_volume = sum(k['volume'] for k in klines)
    if total_volume == 0:
        return None
    
    typical_price_sum = sum(
        (k['high'] + k['low'] + k['close']) / 3 * k['volume']
        for k in klines
    )
    
    return typical_price_sum / total_volume

def analyze_trend(klines_15m, klines_1h, klines_4h):
    """分析趋势（多时间框架）"""
    trends = {}
    
    if klines_15m and len(klines_15m) >= 50:
        closes_15m = [k['close'] for k in klines_15m[-50:]]
        ema_50_15m = calculate_ema(closes_15m, 50)
        current_15m = klines_15m[-1]['close']
        if current_15m > ema_50_15m:
            trends['15m'] = '偏多'
        else:
            trends['15m'] = '偏空'
    
    if klines_1h and len(klines_1h) >= 50:
        closes_1h = [k['close'] for k in klines_1h[-50:]]
        ema_50_1h = calculate_ema(closes_1h, 50)
        current_1h = klines_1h[-1]['close']
        if current_1h > ema_50_1h:
            trends['1h'] = '偏多'
        else:
            trends['1h'] = '偏空'
    
    if klines_4h and len(klines_4h) >= 20:
        closes_4h = [k['close'] for k in klines_4h[-20:]]
        ema_20_4h = calculate_ema(closes_4h, 20)
        current_4h = klines_4h[-1]['close']
        if current_4h > ema_20_4h:
            trends['4h'] = '偏多'
        else:
            trends['4h'] = '偏空'
    
    return trends

def identify_value_area(klines):
    """识别价值区域"""
    if not klines or len(klines) < 20:
        return None
    
    recent = klines[-20:]
    high = max(k['high'] for k in recent)
    low = min(k['low'] for k in recent)
    
    price_volume = {}
    for k in recent:
        price_range = (k['high'] + k['low']) / 2
        if price_range not in price_volume:
            price_volume[price_range] = 0
        price_volume[price_range] += k['volume']
    
    if price_volume:
        poc = max(price_volume.items(), key=lambda x: x[1])[0]
        value_area_low = poc * 0.99
        value_area_high = poc * 1.01
        
        return {
            'poc': poc,
            'value_area_low': value_area_low,
            'value_area_high': value_area_high,
            'range_low': low,
            'range_high': high
        }
    
    return None

def identify_trading_range(klines, ema144, ema169, current_price):
    """识别交易区间（使用百分比判断）"""
    if not klines or len(klines) < 20:
        return None
    
    recent = klines[-20:]
    highs = [k['high'] for k in recent]
    lows = [k['low'] for k in recent]
    
    range_high = max(highs)
    range_low = min(lows)
    
    vegas_high = max(ema144, ema169) if ema144 and ema169 else range_high
    vegas_low = min(ema144, ema169) if ema144 and ema169 else range_low
    
    range_width = range_high - range_low
    range_width_percent = (range_width / current_price) * 100 if current_price > 0 else 0
    
    return {
        'range_high': range_high,
        'range_low': range_low,
        'vegas_high': vegas_high,
        'vegas_low': vegas_low,
        'width': range_width,
        'width_points': range_width,
        'width_percent': range_width_percent
    }

def analyze_auction_phase(klines):
    """分析拍卖阶段"""
    if not klines or len(klines) < 10:
        return None
    
    recent = klines[-10:]
    price_changes = []
    volumes = []
    for i in range(1, len(recent)):
        price_change = abs(recent[i]['close'] - recent[i-1]['close']) / recent[i-1]['close']
        price_changes.append(price_change)
        volumes.append(recent[i]['volume'])
    
    avg_price_change = sum(price_changes) / len(price_changes) if price_changes else 0
    avg_volume = sum(volumes) / len(volumes) if volumes else 0
    
    if avg_price_change < 0.001:
        phase = "价格接受阶段（Price Acceptance）"
        description = "价格在新区域震荡，成交量稳定，市场接受该价格"
    elif avg_price_change > 0.005:
        phase = "价格发现阶段（Price Discovery）"
        description = "价格快速移动，成交量增加，寻找新的价值区域"
    else:
        phase = "初始平衡阶段（Initial Balance）"
        description = "市场在寻找价值，价格在区间内震荡"
    
    return {
        'phase': phase,
        'description': description,
        'avg_price_change': avg_price_change,
        'avg_volume': avg_volume
    }

def get_range_width_judgment(width_percent, timeframe='15m'):
    """根据百分比判断区间宽度是否合理"""
    # De.系统：BTC区间通常几百点，对于$88,000的BTC，几百点约0.1-0.6%
    # 换算到不同价格币种，应该用百分比而不是绝对点数
    
    if timeframe == '15m':
        # 15分钟级别：合理区间宽度约0.2%-1.5%
        if width_percent < 0.2:
            return "不足", "区间宽度不足0.2%，不适合区间交易"
        elif width_percent > 1.5:
            return "过大", "区间宽度超过1.5%，需要确认是否为单边行情"
        else:
            return "合理", "区间宽度合理，适合区间交易"
    elif timeframe == '1h':
        # 1小时级别：合理区间宽度约0.5%-2%
        if width_percent < 0.5:
            return "不足", "区间宽度不足0.5%，不适合区间交易"
        elif width_percent > 2:
            return "过大", "区间宽度超过2%，需要确认是否为单边行情"
        else:
            return "合理", "区间宽度合理，适合区间交易"
    else:
        # 默认判断
        if width_percent < 0.2:
            return "不足", "区间宽度不足，不适合区间交易"
        elif width_percent > 2:
            return "过大", "区间宽度过大，需要确认是否为单边行情"
        else:
            return "合理", "区间宽度合理，适合区间交易"

def generate_trading_plan():
    """生成交易计划"""
    print("=" * 80)
    print("BCH 15分钟交易计划生成（基于De.交易系统 + 拍卖理论）")
    print("=" * 80)
    print()
    
    # 获取数据
    print("正在获取市场数据...")
    current_price = get_current_bch_price()
    klines_15m = get_bch_kline_data('15m', 200)
    klines_1h = get_bch_kline_data('1h', 100)
    klines_4h = get_bch_kline_data('4h', 50)
    
    if not current_price or not klines_15m:
        print("获取数据失败，请检查网络连接")
        return
    
    print(f"当前BCH价格: ${current_price:,.2f}")
    print()
    
    # 计算指标
    print("正在计算技术指标...")
    closes_15m = [k['close'] for k in klines_15m]
    ema144_15m = calculate_ema(closes_15m, 144) if len(closes_15m) >= 144 else None
    ema169_15m = calculate_ema(closes_15m, 169) if len(closes_15m) >= 169 else None
    vwap_15m = calculate_vwap(klines_15m[-24:])
    
    # 分析趋势
    trends = analyze_trend(klines_15m, klines_1h, klines_4h)
    
    # 识别价值区域
    value_area = identify_value_area(klines_15m)
    
    # 识别交易区间（使用百分比判断）
    trading_range = identify_trading_range(klines_15m, ema144_15m, ema169_15m, current_price)
    
    # 分析拍卖阶段
    auction_phase = analyze_auction_phase(klines_15m)
    
    # 生成交易计划
    plan = []
    plan.append("=" * 80)
    plan.append("BCH 15分钟交易计划（修正版）")
    plan.append("=" * 80)
    plan.append("")
    plan.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    plan.append(f"当前价格: ${current_price:,.2f}")
    plan.append("")
    plan.append("**重要说明**: 区间宽度判断已根据币种价格调整，使用百分比而非绝对点数")
    plan.append("")
    
    # 一、区间宽度判断标准说明
    plan.append("## 一、区间宽度判断标准说明")
    plan.append("")
    plan.append("**De.系统的区间宽度标准**：")
    plan.append("- BTC价格约$88,000，\"几百点\"区间 = 约0.1%-0.6%")
    plan.append("- BCH价格约$600，对应区间宽度应换算为百分比")
    plan.append("")
    plan.append("**15分钟级别合理区间宽度**：")
    plan.append("- 最小：0.2%（约$1.2，对于$600的BCH）")
    plan.append("- 最大：1.5%（约$9，对于$600的BCH）")
    plan.append("- 理想：0.5%-1%（约$3-$6，对于$600的BCH）")
    plan.append("")
    plan.append("**1小时级别合理区间宽度**：")
    plan.append("- 最小：0.5%（约$3，对于$600的BCH）")
    plan.append("- 最大：2%（约$12，对于$600的BCH）")
    plan.append("- 理想：1%-1.5%（约$6-$9，对于$600的BCH）")
    plan.append("")
    
    # 二、15分钟级别交易特点
    plan.append("## 二、15分钟级别交易特点")
    plan.append("")
    plan.append("**优势**:")
    plan.append("- 区间相对稳定，波动适中")
    plan.append("- 适合频繁看盘的交易者")
    plan.append("- 持仓时间：30分钟-2小时")
    plan.append("- 止损距离：0.1%-0.2%（约$0.6-$1.2，对于$600的BCH）")
    plan.append("")
    plan.append("**劣势**:")
    plan.append("- 需要经常看盘")
    plan.append("- 信号较多，需要筛选")
    plan.append("- 持仓时间较短，需要快速决策")
    plan.append("")
    
    # 三、多时间框架趋势分析
    plan.append("## 三、多时间框架趋势分析")
    plan.append("")
    if trends.get('4h'):
        plan.append(f"**4小时趋势**: {trends['4h']}（大趋势）")
    if trends.get('1h'):
        plan.append(f"**1小时趋势**: {trends['1h']}（中期趋势）")
    if trends.get('15m'):
        plan.append(f"**15分钟趋势**: {trends['15m']}（短期趋势）")
    plan.append("")
    
    if trends.get('4h') and trends.get('1h') and trends.get('15m'):
        if trends['4h'] == trends['1h'] == trends['15m']:
            plan.append("**[OK] 多时间框架趋势一致** - 交易信号强烈")
        else:
            plan.append("**[WARN] 多时间框架趋势不一致** - 需要谨慎")
    plan.append("")
    
    # 四、技术指标分析
    plan.append("## 四、技术指标分析（15分钟图）")
    plan.append("")
    if ema144_15m and ema169_15m:
        plan.append(f"**Vegas通道（EMA144/169）**:")
        plan.append(f"  - EMA144: ${ema144_15m:,.2f}")
        plan.append(f"  - EMA169: ${ema169_15m:,.2f}")
        plan.append(f"  - 通道宽度: ${abs(ema169_15m - ema144_15m):,.2f} ({abs(ema169_15m - ema144_15m)/current_price*100:.2f}%)")
        if current_price > max(ema144_15m, ema169_15m):
            plan.append("  - 当前价格在通道上方 - 偏多")
        elif current_price < min(ema144_15m, ema169_15m):
            plan.append("  - 当前价格在通道下方 - 偏空")
        else:
            plan.append("  - 当前价格在通道内 - 震荡")
        plan.append("")
    
    if vwap_15m:
        plan.append(f"**VWAP（6小时）**: ${vwap_15m:,.2f}")
        if current_price > vwap_15m:
            plan.append("  - 当前价格在VWAP上方 - 偏多")
        else:
            plan.append("  - 当前价格在VWAP下方 - 偏空")
        plan.append("")
    
    # 五、拍卖机制分析
    plan.append("## 五、拍卖机制分析")
    plan.append("")
    if auction_phase:
        plan.append(f"**当前拍卖阶段**: {auction_phase['phase']}")
        plan.append(f"  - {auction_phase['description']}")
        plan.append(f"  - 平均价格变化: {auction_phase['avg_price_change']*100:.2f}%")
        plan.append("")
    
    if value_area:
        plan.append("**价值区域分析**:")
        plan.append(f"  - POC（成交量最大点）: ${value_area['poc']:,.2f}")
        plan.append(f"  - 价值区域: ${value_area['value_area_low']:,.2f} - ${value_area['value_area_high']:,.2f}")
        plan.append(f"  - 价格范围: ${value_area['range_low']:,.2f} - ${value_area['range_high']:,.2f}")
        
        if value_area['value_area_low'] <= current_price <= value_area['value_area_high']:
            plan.append("  - [OK] 当前价格在价值区域内 - 价格被接受")
        elif current_price < value_area['value_area_low']:
            plan.append("  - [WARN] 当前价格低于价值区域 - 可能回归")
        else:
            plan.append("  - [WARN] 当前价格高于价值区域 - 可能回归")
        plan.append("")
    
    # 六、交易区间识别（使用百分比判断）
    plan.append("## 六、交易区间识别（使用百分比判断）")
    plan.append("")
    if trading_range:
        plan.append(f"**识别区间**:")
        plan.append(f"  - 区间上沿: ${trading_range['range_high']:,.2f}")
        plan.append(f"  - 区间下沿: ${trading_range['range_low']:,.2f}")
        plan.append(f"  - 区间宽度: ${trading_range['width']:,.2f} ({trading_range['width_percent']:.2f}%)")
        
        # 使用百分比判断
        judgment, description = get_range_width_judgment(trading_range['width_percent'], '15m')
        if judgment == "合理":
            plan.append(f"  - [OK] {description}")
        else:
            plan.append(f"  - [WARN] {description}")
        
        plan.append("")
        plan.append(f"**Vegas通道确认**:")
        plan.append(f"  - 通道上沿: ${trading_range['vegas_high']:,.2f}")
        plan.append(f"  - 通道下沿: ${trading_range['vegas_low']:,.2f}")
        plan.append("")
        
        if trading_range['range_low'] <= current_price <= trading_range['range_high']:
            plan.append("  - [OK] 当前价格在区间内")
            distance_to_top = trading_range['range_high'] - current_price
            distance_to_bottom = current_price - trading_range['range_low']
            if distance_to_top < distance_to_bottom:
                plan.append(f"  - 更接近区间上沿（距离: ${distance_to_top:,.2f}，{distance_to_top/current_price*100:.2f}%）")
            else:
                plan.append(f"  - 更接近区间下沿（距离: ${distance_to_bottom:,.2f}，{distance_to_bottom/current_price*100:.2f}%）")
        else:
            plan.append("  - [WARN] 当前价格在区间外")
        plan.append("")
    
    # 七、多情景规划
    plan.append("## 七、多情景规划（必须执行）")
    plan.append("")
    plan.append("**情景A：区间震荡交易**")
    plan.append("  - 条件：价格在区间内震荡，价值区域确认")
    plan.append("  - 策略：在区间上下沿挂单")
    if trading_range:
        plan.append(f"  - 多单挂单：${trading_range['range_low']*1.001:,.2f}（区间下沿+0.1%）")
        plan.append(f"  - 空单挂单：${trading_range['range_high']*0.999:,.2f}（区间上沿-0.1%）")
    plan.append("")
    plan.append("**情景B：价格发现阶段（突破）**")
    plan.append("  - 条件：价格突破区间，成交量增加")
    plan.append("  - 策略：等待确认方向，跟随趋势")
    plan.append("")
    plan.append("**情景C：价格回归价值区域**")
    plan.append("  - 条件：价格偏离价值区域")
    plan.append("  - 策略：等待价格回归，在价值区域边界挂单")
    if value_area:
        plan.append(f"  - 多单挂单：${value_area['value_area_low']*1.001:,.2f}")
        plan.append(f"  - 空单挂单：${value_area['value_area_high']*0.999:,.2f}")
    plan.append("")
    
    # 八、交易建议
    plan.append("## 八、交易建议")
    plan.append("")
    
    can_trade = True
    reasons = []
    
    if trends.get('4h') == '偏多' and trends.get('15m') == '偏多':
        reasons.append("[OK] 4小时和15分钟趋势一致偏多")
    elif trends.get('4h') == '偏空' and trends.get('15m') == '偏空':
        reasons.append("[OK] 4小时和15分钟趋势一致偏空")
    else:
        reasons.append("[WARN] 趋势不一致，需要谨慎")
    
    # 使用百分比判断区间宽度
    if trading_range:
        judgment, _ = get_range_width_judgment(trading_range['width_percent'], '15m')
        if judgment == "合理":
            reasons.append(f"[OK] 区间宽度合理（{trading_range['width_percent']:.2f}%）")
        else:
            reasons.append(f"[WARN] 区间宽度不合理（{trading_range['width_percent']:.2f}%）")
            can_trade = False
    
    if value_area and value_area['value_area_low'] <= current_price <= value_area['value_area_high']:
        reasons.append("[OK] 价格在价值区域内")
    else:
        reasons.append("[WARN] 价格偏离价值区域")
    
    if auction_phase:
        if "价格接受" in auction_phase['phase']:
            reasons.append("[OK] 处于价格接受阶段，适合区间交易")
        elif "价格发现" in auction_phase['phase']:
            reasons.append("[WARN] 处于价格发现阶段，需要确认方向")
        else:
            reasons.append("[WARN] 处于初始平衡阶段，等待明确信号")
    
    for reason in reasons:
        plan.append(f"  {reason}")
    plan.append("")
    
    if can_trade:
        plan.append("**交易建议**: 可以交易，但需要严格按照检查清单执行")
    else:
        plan.append("**交易建议**: 暂不建议交易，等待更好的机会")
    plan.append("")
    
    # 九、风险管理（使用百分比）
    plan.append("## 九、风险管理（使用百分比）")
    plan.append("")
    plan.append("**止损设置**:")
    plan.append("  - 位置：假突破不能打到的位置")
    plan.append("  - 距离：0.1%-0.2%（15分钟级别）")
    if trading_range:
        stop_loss_percent = max(0.1, trading_range['width_percent'] * 0.1)
        stop_loss_amount = current_price * stop_loss_percent / 100
        plan.append(f"  - 建议止损距离：约{stop_loss_percent:.2f}%（约${stop_loss_amount:,.2f}）")
    plan.append("")
    plan.append("**止盈设置**:")
    plan.append("  - 位置：区间上下沿或中间位置")
    plan.append("  - 盈亏比：至少2倍")
    if trading_range:
        take_profit_percent = trading_range['width_percent'] * 0.5
        take_profit_amount = current_price * take_profit_percent / 100
        plan.append(f"  - 建议止盈距离：约{take_profit_percent:.2f}%（约${take_profit_amount:,.2f}）")
    plan.append("")
    plan.append("**仓位管理**:")
    plan.append("  - 风险不超过账户的5%")
    plan.append("  - 使用逐仓模式")
    plan.append("  - 持仓时间：30分钟-2小时")
    plan.append("")
    
    # 十、检查清单提醒
    plan.append("## 十、交易前检查清单提醒")
    plan.append("")
    plan.append("**必须完成以下检查（共62项）**:")
    plan.append("")
    plan.append("1. 拍卖机制分析（9项）")
    plan.append("2. 市场分析检查（24项）")
    plan.append("3. 交易区间检查（7项）")
    plan.append("4. 入场条件检查（8项）")
    plan.append("5. 风险管理检查（8项）")
    plan.append("6. 特殊情况检查（5项）")
    plan.append("")
    plan.append("**只有完成所有检查后，才能执行交易！**")
    plan.append("")
    plan.append("=" * 80)
    
    # 保存计划
    plan_text = "\n".join(plan)
    output_file = f"BCH_15m_trading_plan_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(plan_text)
    
    import sys
    sys.stdout.buffer.write(f"\n交易计划已保存到: {output_file}\n".encode('utf-8'))
    sys.stdout.buffer.write(f"文件包含 {len(plan)} 行内容\n".encode('utf-8'))

if __name__ == "__main__":
    generate_trading_plan()




