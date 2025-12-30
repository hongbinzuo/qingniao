#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Freelemon交易系统 - 斐波那契高空策略
基于JellyJelly案例分析，结合量价分析寻找做空机会
"""

import requests
import sys
import time
from datetime import datetime
from pathlib import Path

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def get_kline_gateio(symbol='JELLY', timeframe='4h', limit=500):
    """从Gate.io获取K线数据"""
    try:
        tf_map = {
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        interval = tf_map.get(timeframe, '4h')
        
        pair = f'{symbol}_USDT'
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': pair,
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
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
                return klines
    except Exception as e:
        pass
    return None

def get_kline_binance(symbol='JELLY', timeframe='4h', limit=500):
    """从Binance获取K线数据（备用）"""
    try:
        tf_map = {
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        interval = tf_map.get(timeframe, '4h')
        
        symbol_str = f'{symbol}USDT'
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol_str,
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                klines = []
                for k in data:
                    klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    })
                return klines
    except Exception as e:
        pass
    return None

def calculate_fibonacci_levels(low, high):
    """计算斐波那契回撤和扩展位"""
    diff = high - low
    
    # 回撤位（0-1区间）
    retracement = {
        '0': low,
        '0.236': low + diff * 0.236,
        '0.382': low + diff * 0.382,
        '0.5': low + diff * 0.5,
        '0.618': low + diff * 0.618,
        '0.786': low + diff * 0.786,
        '1': high
    }
    
    # 扩展位（1以上）
    extension = {
        '1.272': high + diff * 0.272,
        '1.414': high + diff * 0.414,
        '1.618': high + diff * 0.618,
        '2': high + diff * 1.0,
        '2.618': high + diff * 1.618,
        '3': high + diff * 2.0,
        '3.618': high + diff * 2.618,
        '4.236': high + diff * 3.236,
        '5': high + diff * 4.0,
        '8': high + diff * 7.0,
        '13': high + diff * 12.0
    }
    
    return retracement, extension

def find_swing_points(klines, lookback=20):
    """寻找关键的高低点"""
    if len(klines) < lookback * 2:
        return None, None
    
    # 寻找最近的低点（支撑）
    recent_lows = []
    for i in range(lookback, len(klines) - lookback):
        is_low = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and klines[j]['low'] < klines[i]['low']:
                is_low = False
                break
        if is_low:
            recent_lows.append((i, klines[i]['low']))
    
    # 寻找最近的高点（阻力）
    recent_highs = []
    for i in range(lookback, len(klines) - lookback):
        is_high = True
        for j in range(i - lookback, i + lookback + 1):
            if j != i and klines[j]['high'] > klines[i]['high']:
                is_high = False
                break
        if is_high:
            recent_highs.append((i, klines[i]['high']))
    
    # 选择最显著的低点和高点
    if recent_lows:
        significant_low = min(recent_lows, key=lambda x: x[1])
    else:
        significant_low = None
    
    if recent_highs:
        significant_high = max(recent_highs, key=lambda x: x[1])
    else:
        significant_high = None
    
    return significant_low, significant_high

def analyze_volume_price(klines, recent_period=20):
    """分析量价关系"""
    if len(klines) < recent_period:
        return None
    
    recent = klines[-recent_period:]
    older = klines[-recent_period*2:-recent_period] if len(klines) >= recent_period*2 else klines[:-recent_period]
    
    # 计算平均成交量
    recent_avg_volume = sum(k['volume'] for k in recent) / len(recent)
    older_avg_volume = sum(k['volume'] for k in older) / len(older) if older else recent_avg_volume
    
    # 分析最近K线
    recent_closes = [k['close'] for k in recent]
    price_trend = 'up' if recent_closes[-1] > recent_closes[0] else 'down'
    
    # 检查是否有大量换手（高成交量）
    high_volume_ratio = recent_avg_volume / older_avg_volume if older_avg_volume > 0 else 1.0
    
    # 检查最近是否有大阴线/大阳线
    last_candle = recent[-1]
    candle_body = abs(last_candle['close'] - last_candle['open'])
    candle_range = last_candle['high'] - last_candle['low']
    body_ratio = candle_body / candle_range if candle_range > 0 else 0
    
    is_big_candle = body_ratio > 0.7
    is_bearish = last_candle['close'] < last_candle['open']
    is_bullish = last_candle['close'] > last_candle['open']
    
    return {
        'price_trend': price_trend,
        'volume_ratio': high_volume_ratio,
        'has_high_volume': high_volume_ratio > 1.5,
        'is_big_candle': is_big_candle,
        'is_bearish_candle': is_bearish and is_big_candle,
        'is_bullish_candle': is_bullish and is_big_candle,
        'recent_avg_volume': recent_avg_volume
    }

def check_breakout_pattern(klines, fib_levels):
    """检查突破模式"""
    if len(klines) < 50:
        return None
    
    current_price = klines[-1]['close']
    fib_1 = fib_levels['1']  # 原高点
    
    # 检查是否突破
    is_breakout = current_price > fib_1
    
    # 检查突破前的回踩
    recent_lows = [k['low'] for k in klines[-20:]]
    min_recent_low = min(recent_lows)
    
    fib_0786 = fib_levels.get('0.786', fib_1 * 0.786)
    fib_0618 = fib_levels.get('0.618', fib_1 * 0.618)
    fib_0382 = fib_levels.get('0.382', fib_1 * 0.382)
    
    retracement_level = None
    if min_recent_low <= fib_0786 * 1.02 and min_recent_low >= fib_0786 * 0.98:
        retracement_level = '0.786'
    elif min_recent_low <= fib_0618 * 1.02 and min_recent_low >= fib_0618 * 0.98:
        retracement_level = '0.618'
    elif min_recent_low <= fib_0382 * 1.02 and min_recent_low >= fib_0382 * 0.98:
        retracement_level = '0.382'
    
    return {
        'is_breakout': is_breakout,
        'retracement_level': retracement_level,
        'current_price': current_price
    }

def identify_short_opportunities(klines):
    """识别做空机会"""
    if not klines or len(klines) < 100:
        return None
    
    # 寻找关键高低点
    swing_low, swing_high = find_swing_points(klines, lookback=20)
    
    if not swing_low or not swing_high:
        return None
    
    low_idx, low_price = swing_low
    high_idx, high_price = swing_high
    
    # 确保高点在低点之后
    if high_idx <= low_idx:
        return None
    
    # 计算斐波那契位
    retracement, extension = calculate_fibonacci_levels(low_price, high_price)
    
    current_price = klines[-1]['close']
    
    # 分析量价
    volume_analysis = analyze_volume_price(klines)
    if not volume_analysis:
        return None
    
    # 检查突破模式
    breakout_info = check_breakout_pattern(klines, {**retracement, **extension})
    
    opportunities = []
    
    # 机会1：突破后的斐波扩展高空（最稳的交易）
    # 挂单在1.618/2，止盈1，中间止盈1.272/1.414
    if breakout_info and breakout_info['is_breakout']:
        fib_1618 = extension['1.618']
        fib_2 = extension['2']
        fib_1 = retracement['1']
        fib_1272 = extension['1.272']
        fib_1414 = extension['1.414']
        
        # 检查当前价格是否在1.618-2区间
        if fib_1618 * 0.98 <= current_price <= fib_2 * 1.02:
            # 检查量价：如果有大阴线爆量，是好的做空信号
            if volume_analysis['is_bearish_candle'] and volume_analysis['has_high_volume']:
                opportunities.append({
                    'type': 'fib_extension_short_primary',
                    'entry_zone': f"{fib_1618:.4f} - {fib_2:.4f}",
                    'entry_1': fib_1618,
                    'entry_2': fib_2,
                    'take_profit_1': fib_1272,
                    'take_profit_2': fib_1414,
                    'take_profit_3': fib_1,
                    'stop_loss': fib_2 * 1.05,  # 2上方5%
                    'risk_reward': (fib_2 - fib_1) / (fib_2 * 0.05),
                    'confidence': 'high',
                    'reason': '突破后斐波扩展高空，最稳的交易机会',
                    'volume_signal': '大阴线爆量确认'
                })
            elif current_price >= fib_1618:
                # 即使没有大阴线，如果价格在扩展位，也可以关注
                opportunities.append({
                    'type': 'fib_extension_short_primary',
                    'entry_zone': f"{fib_1618:.4f} - {fib_2:.4f}",
                    'entry_1': fib_1618,
                    'entry_2': fib_2,
                    'take_profit_1': fib_1272,
                    'take_profit_2': fib_1414,
                    'take_profit_3': fib_1,
                    'stop_loss': fib_2 * 1.05,
                    'risk_reward': (fib_2 - fib_1) / (fib_2 * 0.05),
                    'confidence': 'medium',
                    'reason': '突破后斐波扩展高空，等待确认信号',
                    'volume_signal': '需等待大阴线或量价确认'
                })
    
    # 机会2：第二波扩展高空（2.618-3.618区间）
    if breakout_info and breakout_info['is_breakout']:
        fib_2618 = extension['2.618']
        fib_3 = extension['3']
        fib_3618 = extension['3.618']
        fib_1 = retracement['1']
        
        if fib_2618 * 0.98 <= current_price <= fib_3618 * 1.02:
            # 在2.618-4.236区间需要关注量价行为和K线形态
            if volume_analysis['is_bearish_candle'] and volume_analysis['has_high_volume']:
                opportunities.append({
                    'type': 'fib_extension_short_secondary',
                    'entry_zone': f"{fib_2618:.4f} - {fib_3618:.4f}",
                    'entry_1': fib_2618,
                    'entry_2': fib_3,
                    'entry_3': fib_3618,
                    'take_profit_1': extension.get('2', fib_1 * 2),
                    'take_profit_2': extension.get('1.618', fib_1 * 1.618),
                    'take_profit_3': fib_1,
                    'stop_loss': fib_3618 * 1.05,
                    'risk_reward': (fib_3618 - fib_1) / (fib_3618 * 0.05),
                    'confidence': 'medium',
                    'reason': '第二波扩展高空，需要量价确认',
                    'volume_signal': '大阴线爆量确认',
                    'warning': '此位置风险较高，需轻仓'
                })
    
    # 机会3：盘整后突破的第二次机会
    # 检查是否有盘整后再次突破
    if len(klines) >= 100:
        # 检查最近是否有盘整
        recent_50 = klines[-50:]
        recent_highs = [k['high'] for k in recent_50]
        recent_lows = [k['low'] for k in recent_50]
        
        price_range_ratio = (max(recent_highs) - min(recent_lows)) / min(recent_lows)
        
        # 如果价格波动较小，可能是盘整
        if price_range_ratio < 0.2:
            # 检查是否有大阳线突破
            if volume_analysis['is_bullish_candle'] and volume_analysis['has_high_volume']:
                # 重新计算斐波位（基于盘整区间）
                consolidation_low = min(recent_lows)
                consolidation_high = max(recent_highs)
                new_ret, new_ext = calculate_fibonacci_levels(consolidation_low, consolidation_high)
                
                if current_price >= new_ext['1.618']:
                    opportunities.append({
                        'type': 'consolidation_breakout_short',
                        'entry_zone': f"{new_ext['1.618']:.4f} - {new_ext['2']:.4f}",
                        'entry_1': new_ext['1.618'],
                        'entry_2': new_ext['2'],
                        'take_profit_1': new_ext['1.272'],
                        'take_profit_2': new_ext['1.414'],
                        'take_profit_3': new_ret['1'],
                        'stop_loss': new_ext['2'] * 1.05,
                        'risk_reward': (new_ext['2'] - new_ret['1']) / (new_ext['2'] * 0.05),
                        'confidence': 'high',
                        'reason': '盘整后突破，第二次最稳的交易机会',
                        'volume_signal': '大阳线突破确认'
                    })
    
    return {
        'symbol': None,  # 将在调用时设置
        'current_price': current_price,
        'swing_low': low_price,
        'swing_high': high_price,
        'fibonacci_levels': {**retracement, **extension},
        'volume_analysis': volume_analysis,
        'breakout_info': breakout_info,
        'opportunities': opportunities
    }

def scan_top_coins(limit=500):
    """扫描前N个币种"""
    print(f"正在扫描前{limit}个币种...")
    
    # 获取币种列表
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 筛选USDT交易对，按24h交易量排序
            usdt_pairs = [t for t in data if t.get('currency_pair', '').endswith('_USDT')]
            usdt_pairs.sort(key=lambda x: float(x.get('quote_volume', 0)), reverse=True)
            return [pair['currency_pair'].replace('_USDT', '') for pair in usdt_pairs[:limit]]
    except:
        pass
    
    return []

def scan_fibonacci_short_opportunities(limit=500):
    """扫描斐波那契做空机会"""
    print("="*70)
    print("Freelemon交易系统 - 斐波那契高空策略扫描")
    print("="*70)
    print()
    
    coins = scan_top_coins(limit)
    if not coins:
        print("无法获取币种列表")
        return []
    
    print(f"开始扫描 {len(coins)} 个币种...")
    print()
    
    opportunities_found = []
    
    for i, symbol in enumerate(coins):
        try:
            print(f"分析 {symbol} ({i+1}/{len(coins)})...", end=' ')
            
            # 获取4小时K线
            klines = get_kline_gateio(symbol, '4h', 500)
            if not klines:
                klines = get_kline_binance(symbol, '4h', 500)
            
            if not klines or len(klines) < 100:
                print("数据不足")
                time.sleep(0.2)
                continue
            
            # 分析做空机会
            analysis = identify_short_opportunities(klines)
            
            if analysis and analysis['opportunities']:
                analysis['symbol'] = symbol
                opportunities_found.append(analysis)
                print(f"✓ 发现 {len(analysis['opportunities'])} 个机会")
            else:
                print("-")
            
            time.sleep(0.2)  # 避免请求过快
            
        except Exception as e:
            print(f"错误: {e}")
            continue
    
    print()
    print("="*70)
    print(f"扫描完成！发现 {len(opportunities_found)} 个币种有做空机会")
    print("="*70)
    print()
    
    return opportunities_found

def format_opportunities_report(opportunities):
    """格式化机会报告"""
    now = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
    
    md = f"""# Freelemon交易系统 - 斐波那契高空策略扫描报告

**生成时间**: {now}

---

## 策略说明

基于JellyJelly案例分析，本策略寻找以下做空机会：

### 1. 突破后斐波扩展高空（最稳交易）
- **入场**: 1.618/2 区间挂单
- **止盈**: 1.272/1.414（中间），1/0.786（主要）
- **止损**: 2上方5%
- **特点**: 突破后最稳的交易机会

### 2. 第二波扩展高空
- **入场**: 2.618-3.618 区间挂单
- **止盈**: 2/1.618/1
- **止损**: 3.618上方5%
- **特点**: 需要量价确认，风险较高，需轻仓

### 3. 盘整后突破的第二次机会
- **入场**: 盘整后突破的1.618/2
- **止盈**: 1.272/1.414/1
- **止损**: 2上方5%
- **特点**: 盘整后的第二次最稳交易机会

---

## 扫描结果

**共发现 {len(opportunities)} 个币种有做空机会**

"""
    
    for opp in opportunities:
        symbol = opp['symbol']
        current_price = opp['current_price']
        swing_low = opp['swing_low']
        swing_high = opp['swing_high']
        volume_analysis = opp['volume_analysis']
        opps = opp['opportunities']
        
        md += f"""### {symbol}

**当前价格**: ${current_price:.6f}
**关键低点**: ${swing_low:.6f}
**关键高点**: ${swing_high:.6f}
**价格趋势**: {volume_analysis['price_trend']}
**成交量比**: {volume_analysis['volume_ratio']:.2f}x
**量价信号**: {'大阴线爆量' if volume_analysis['is_bearish_candle'] and volume_analysis['has_high_volume'] else '需等待确认'}

"""
        
        for i, opp_detail in enumerate(opps, 1):
            entry_2_str = f"${opp_detail['entry_2']:.6f}" if 'entry_2' in opp_detail else 'N/A'
            entry_3_str = f"${opp_detail['entry_3']:.6f}" if 'entry_3' in opp_detail else 'N/A'
            tp_2_str = f"${opp_detail['take_profit_2']:.6f}" if 'take_profit_2' in opp_detail else 'N/A'
            tp_3_str = f"${opp_detail['take_profit_3']:.6f}" if 'take_profit_3' in opp_detail else 'N/A'
            
            md += f"""#### 机会 {i}: {opp_detail['type']}

**置信度**: {opp_detail['confidence']}
**入场区间**: {opp_detail['entry_zone']}
**入场点位**:
- 第一笔: ${opp_detail['entry_1']:.6f}
- 第二笔: {entry_2_str}
- 第三笔: {entry_3_str}

**止盈点位**:
- 第一目标: ${opp_detail['take_profit_1']:.6f}
- 第二目标: {tp_2_str}
- 第三目标: {tp_3_str}

**止损**: ${opp_detail['stop_loss']:.6f}
**盈亏比**: {opp_detail['risk_reward']:.2f}
**理由**: {opp_detail['reason']}
**量价信号**: {opp_detail.get('volume_signal', 'N/A')}

"""
            
            if 'warning' in opp_detail:
                md += f"**⚠️ 警告**: {opp_detail['warning']}\n\n"
        
        md += "---\n\n"
    
    md += """---

## 交易建议

1. **仓位管理**: 
   - 第一笔（1.618/2）: 可以给正常仓位
   - 第二笔（2.618-3.618）: 需轻仓，风险较高

2. **止损设置**: 
   - 必须设置止损
   - 建议使用柔性止损（4h级别）

3. **量价确认**: 
   - 优先选择有大阴线爆量确认的机会
   - 如果K线没有空头供应，大盘健康，需谨慎

4. **分批止盈**: 
   - 建议分3-4笔止盈
   - 不要贪心，及时止盈

---

*本报告仅供参考，交易有风险，入市需谨慎。*

"""
    
    return md

def main():
    """主函数"""
    # 扫描做空机会
    opportunities = scan_fibonacci_short_opportunities(limit=500)
    
    if opportunities:
        # 生成报告
        report = format_opportunities_report(opportunities)
        
        # 保存报告
        filename = f"outputs/Freelemon_斐波高空策略_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        Path('outputs').mkdir(exist_ok=True)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✓ 报告已保存: {filename}")
    else:
        print("未发现符合条件的做空机会")

if __name__ == '__main__':
    main()

