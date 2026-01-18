#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合交易计划生成器
1. BTC多时间框架交易计划（15m, 1h, 4h, 1D）
2. 扫描前200个币种，识别趋势币种
3. 分析24小时涨幅榜，生成做空计划
"""

import requests
import sys
import time
from datetime import datetime
import json

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def get_kline_gateio(symbol='BTC', timeframe='15m', limit=200):
    """从Gate.io获取K线数据"""
    try:
        tf_map = {
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        interval = tf_map.get(timeframe, '15m')
        
        # 构建交易对
        if symbol == 'BTC':
            pair = 'BTC_USDT'
        else:
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
        print(f"[DEBUG] get_kline_gateio 异常 ({symbol}): {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
    return None

def get_kline_binance(symbol='BTC', timeframe='15m', limit=200):
    """从Binance合约获取K线数据（使用fapi.binance.com）"""
    try:
        tf_map = {
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }
        interval = tf_map.get(timeframe, '15m')
        
        symbol_map = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT'
        }
        symbol_str = symbol_map.get(symbol, f'{symbol}USDT')
        
        # 使用币安合约API（fapi.binance.com）
        url = "https://fapi.binance.com/fapi/v1/klines"
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
                        'timestamp': int(k[0]) // 1000,  # 合约API返回毫秒，转换为秒
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

def calculate_ema(prices, period):
    """计算EMA"""
    if len(prices) < period:
        return None
    ema = [prices[0]]
    multiplier = 2 / (period + 1)
    for price in prices[1:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema[-1]

def calculate_ma(prices, period):
    """计算MA"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def analyze_trend(klines):
    """分析趋势"""
    if not klines or len(klines) < 50:
        return None
    
    closes = [k['close'] for k in klines]
    highs = [k['high'] for k in klines]
    lows = [k['low'] for k in klines]
    volumes = [k['volume'] for k in klines]
    
    current_price = closes[-1]
    
    # 计算均线
    ma20 = calculate_ma(closes, 20)
    ma50 = calculate_ma(closes, 50)
    ema12 = calculate_ema(closes, 12)
    ema26 = calculate_ema(closes, 26)
    
    # 计算RSI
    rsi = calculate_rsi(closes, 14)
    
    # 趋势判断
    trend = '震荡'
    if ma20 and ma50:
        if ma20 > ma50 and current_price > ma20:
            trend = '上涨'
        elif ma20 < ma50 and current_price < ma20:
            trend = '下跌'
    
    # 支撑阻力
    recent_highs = sorted(highs[-20:], reverse=True)
    recent_lows = sorted(lows[-20:])
    resistance = recent_highs[0] if recent_highs else current_price * 1.05
    support = recent_lows[0] if recent_lows else current_price * 0.95
    
    return {
        'current_price': current_price,
        'trend': trend,
        'ma20': ma20,
        'ma50': ma50,
        'ema12': ema12,
        'ema26': ema26,
        'rsi': rsi,
        'support': support,
        'resistance': resistance,
        'volume_avg': sum(volumes[-20:]) / 20 if len(volumes) >= 20 else volumes[-1]
    }

def calculate_rsi(prices, period=14):
    """计算RSI"""
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    if len(gains) < period:
        return None
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_btc_plan(timeframe):
    """生成BTC指定时间框架的交易计划"""
    print(f"正在分析BTC {timeframe}...")
    
    klines = get_kline_gateio('BTC', timeframe, 200)
    if not klines:
        klines = get_kline_binance('BTC', timeframe, 200)
    
    if not klines:
        return None
    
    analysis = analyze_trend(klines)
    if not analysis:
        return None
    
    current_price = analysis['current_price']
    trend = analysis['trend']
    
    # 生成交易计划
    plan = {
        'timeframe': timeframe,
        'current_price': current_price,
        'trend': trend,
        'ma20': analysis['ma20'],
        'ma50': analysis['ma50'],
        'rsi': analysis['rsi'],
        'support': analysis['support'],
        'resistance': analysis['resistance'],
        'signals': []
    }
    
    # 做多信号
    if trend == '上涨' or (analysis['ma20'] and current_price > analysis['ma20']):
        entry = current_price * 0.998  # 略低于当前价
        stop_loss = analysis['support'] * 0.995
        take_profit = analysis['resistance'] * 0.998
        
        plan['signals'].append({
            'direction': '做多',
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': (take_profit - entry) / (entry - stop_loss) if entry > stop_loss else 0
        })
    
    # 做空信号
    if trend == '下跌' or (analysis['ma20'] and current_price < analysis['ma20']):
        entry = current_price * 1.002  # 略高于当前价
        stop_loss = analysis['resistance'] * 1.005
        take_profit = analysis['support'] * 1.002
        
        plan['signals'].append({
            'direction': '做空',
            'entry': entry,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk_reward': (entry - take_profit) / (stop_loss - entry) if stop_loss > entry else 0
        })
    
    return plan

def get_top200_coins():
    """获取前200个币种"""
    try:
        # 使用CoinGecko API
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': 200,
            'page': 1
        }
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data
    except:
        pass
    
    # 备用：使用Gate.io
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 按24h交易量排序
            data.sort(key=lambda x: float(x.get('quote_volume', 0)), reverse=True)
            return data[:200]
    except:
        pass
    
    return []

def get_top_gainers():
    """获取24小时涨幅榜"""
    try:
        # 使用Gate.io
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 筛选USDT交易对
            usdt_pairs = [t for t in data if t.get('currency_pair', '').endswith('_USDT')]
            # 按24h涨跌幅排序
            usdt_pairs.sort(key=lambda x: float(x.get('change_percentage', 0)), reverse=True)
            return usdt_pairs[:50]  # 前50个涨幅最大的
    except:
        pass
    
    return []

def scan_trend_coins():
    """扫描趋势币种"""
    print("正在扫描前200个币种...")
    coins = get_top200_coins()
    
    trend_coins = []
    
    for i, coin in enumerate(coins[:200]):
        try:
            symbol = coin.get('symbol', '').upper()
            if not symbol:
                continue
            
            print(f"分析 {symbol} ({i+1}/200)...")
            
            # 获取1小时K线
            klines = get_kline_gateio(symbol, '1h', 100)
            if not klines:
                time.sleep(0.2)
                continue
            
            analysis = analyze_trend(klines)
            if not analysis:
                time.sleep(0.2)
                continue
            
            # 判断是否为趋势币种
            is_trend = False
            reason = []
            
            if analysis['trend'] == '上涨' and analysis['ma20'] and analysis['ma50']:
                if analysis['current_price'] > analysis['ma20'] > analysis['ma50']:
                    is_trend = True
                    reason.append('上涨趋势，价格在均线上方')
            
            if analysis['trend'] == '下跌' and analysis['ma20'] and analysis['ma50']:
                if analysis['current_price'] < analysis['ma20'] < analysis['ma50']:
                    is_trend = True
                    reason.append('下跌趋势，价格在均线下方')
            
            if is_trend:
                trend_coins.append({
                    'symbol': symbol,
                    'current_price': analysis['current_price'],
                    'trend': analysis['trend'],
                    'ma20': analysis['ma20'],
                    'ma50': analysis['ma50'],
                    'rsi': analysis['rsi'],
                    'support': analysis['support'],
                    'resistance': analysis['resistance'],
                    'reason': '; '.join(reason)
                })
            
            time.sleep(0.2)  # 避免请求过快
            
        except Exception as e:
            continue
    
    return trend_coins

def analyze_short_opportunities():
    """分析做空机会（涨幅榜币种）"""
    print("正在分析24小时涨幅榜做空机会...")
    gainers = get_top_gainers()
    
    short_opportunities = []
    
    for coin in gainers[:30]:  # 分析前30个
        try:
            pair = coin.get('currency_pair', '')
            symbol = pair.replace('_USDT', '').upper()
            
            if not symbol:
                continue
            
            print(f"分析 {symbol} 做空机会...")
            
            # 获取4小时K线
            klines = get_kline_gateio(symbol, '4h', 100)
            if not klines:
                time.sleep(0.2)
                continue
            
            analysis = analyze_trend(klines)
            if not analysis:
                time.sleep(0.2)
                continue
            
            current_price = analysis['current_price']
            change_24h = float(coin.get('change_percentage', 0))
            
            # 判断做空条件
            should_short = False
            reason = []
            
            # 涨幅过大
            if change_24h > 20:
                should_short = True
                reason.append(f'24小时涨幅{change_24h:.2f}%，涨幅过大')
            
            # RSI超买
            if analysis['rsi'] and analysis['rsi'] > 70:
                should_short = True
                reason.append(f'RSI={analysis["rsi"]:.2f}，超买')
            
            # 接近阻力位
            if analysis['resistance'] and current_price >= analysis['resistance'] * 0.98:
                should_short = True
                reason.append(f'接近阻力位${analysis["resistance"]:,.2f}')
            
            if should_short:
                entry = current_price * 1.002
                stop_loss = analysis['resistance'] * 1.01 if analysis['resistance'] else current_price * 1.05
                take_profit = analysis['support'] * 1.01 if analysis['support'] else current_price * 0.95
                
                short_opportunities.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'change_24h': change_24h,
                    'rsi': analysis['rsi'],
                    'resistance': analysis['resistance'],
                    'support': analysis['support'],
                    'entry': entry,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'risk_reward': (entry - take_profit) / (stop_loss - entry) if stop_loss > entry else 0,
                    'reason': '; '.join(reason)
                })
            
            time.sleep(0.2)
            
        except Exception as e:
            continue
    
    return short_opportunities

def format_plan_markdown(btc_plans, trend_coins, short_opportunities):
    """格式化计划为Markdown"""
    now = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
    
    md = f"""# 综合交易计划

**生成时间**: {now}

---

## 一、BTC多时间框架交易计划

"""
    
    # BTC计划
    for tf in ['15m', '1h', '4h', '1d']:
        plan = btc_plans.get(tf)
        if plan:
            ma20_str = f"${plan['ma20']:,.2f}" if plan['ma20'] is not None else 'N/A'
            ma50_str = f"${plan['ma50']:,.2f}" if plan['ma50'] is not None else 'N/A'
            rsi_str = f"{plan['rsi']:.2f}" if plan['rsi'] is not None else 'N/A'
            
            md += f"""### BTC {tf.upper()} 交易计划

**当前价格**: ${plan['current_price']:,.2f}
**趋势**: {plan['trend']}
**MA20**: {ma20_str}
**MA50**: {ma50_str}
**RSI**: {rsi_str}
**支撑位**: ${plan['support']:,.2f}
**阻力位**: ${plan['resistance']:,.2f}

"""
            
            for signal in plan['signals']:
                md += f"""#### {signal['direction']}信号

- **入场价**: ${signal['entry']:,.2f}
- **止损价**: ${signal['stop_loss']:,.2f}
- **止盈价**: ${signal['take_profit']:,.2f}
- **盈亏比**: {signal['risk_reward']:.2f}

"""
    
    # 趋势币种
    md += """---

## 二、趋势币种交易计划

"""
    
    if trend_coins:
        md += f"**发现 {len(trend_coins)} 个趋势币种**\n\n"
        for coin in trend_coins:
            ma20_str = f"${coin['ma20']:,.4f}" if coin['ma20'] is not None else 'N/A'
            ma50_str = f"${coin['ma50']:,.4f}" if coin['ma50'] is not None else 'N/A'
            rsi_str = f"{coin['rsi']:.2f}" if coin['rsi'] is not None else 'N/A'
            
            md += f"""### {coin['symbol']}

**当前价格**: ${coin['current_price']:,.4f}
**趋势**: {coin['trend']}
**MA20**: {ma20_str}
**MA50**: {ma50_str}
**RSI**: {rsi_str}
**支撑位**: ${coin['support']:,.4f}
**阻力位**: ${coin['resistance']:,.4f}
**判断理由**: {coin['reason']}

"""
    else:
        md += "**未发现明显趋势币种**\n\n"
    
    # 做空机会
    md += """---

## 三、24小时涨幅榜做空计划

"""
    
    if short_opportunities:
        md += f"**发现 {len(short_opportunities)} 个做空机会**\n\n"
        for opp in short_opportunities:
            rsi_str = f"{opp['rsi']:.2f}" if opp['rsi'] is not None else 'N/A'
            resistance_str = f"${opp['resistance']:,.4f}" if opp['resistance'] is not None else 'N/A'
            support_str = f"${opp['support']:,.4f}" if opp['support'] is not None else 'N/A'
            
            md += f"""### {opp['symbol']} 做空计划

**当前价格**: ${opp['current_price']:,.4f}
**24小时涨幅**: {opp['change_24h']:.2f}%
**RSI**: {rsi_str}
**阻力位**: {resistance_str}
**支撑位**: {support_str}

**交易计划**:
- **入场价**: ${opp['entry']:,.4f}
- **止损价**: ${opp['stop_loss']:,.4f}
- **止盈价**: ${opp['take_profit']:,.4f}
- **盈亏比**: {opp['risk_reward']:.2f}
- **做空理由**: {opp['reason']}

"""
    else:
        md += "**未发现明显做空机会**\n\n"
    
    md += """---

*本计划仅供参考，交易有风险，入市需谨慎。*

"""
    
    return md

def main():
    print("="*70)
    print("综合交易计划生成器")
    print("="*70)
    print()
    
    # 1. 生成BTC多时间框架计划
    print("【任务1】生成BTC多时间框架交易计划...")
    btc_plans = {}
    for tf in ['15m', '1h', '4h', '1d']:
        plan = generate_btc_plan(tf)
        if plan:
            btc_plans[tf] = plan
        time.sleep(1)
    
    print(f"✓ 完成BTC计划生成（{len(btc_plans)}个时间框架）\n")
    
    # 2. 扫描趋势币种
    print("【任务2】扫描前200个币种...")
    trend_coins = scan_trend_coins()
    print(f"✓ 发现 {len(trend_coins)} 个趋势币种\n")
    
    # 3. 分析做空机会
    print("【任务3】分析24小时涨幅榜做空机会...")
    short_opportunities = analyze_short_opportunities()
    print(f"✓ 发现 {len(short_opportunities)} 个做空机会\n")
    
    # 4. 生成Markdown文件
    print("【任务4】生成交易计划文件...")
    md_content = format_plan_markdown(btc_plans, trend_coins, short_opportunities)
    
    filename = f"综合交易计划_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✓ 计划已保存到: {filename}")
    print()
    print("="*70)
    print("所有任务完成！")
    print("="*70)

if __name__ == '__main__':
    main()

