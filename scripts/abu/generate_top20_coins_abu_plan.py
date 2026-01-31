#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU系统v3.0 - Top 20币种交易计划生成器

为Top 20币种生成交易计划，每个币种5分钟和15分钟各1个信号。
使用Gemini Flash模式库进行匹配。
"""

import sys
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def get_top_coins(limit=20):
    """获取Top N币种（按24h交易量）"""
    try:
        # 使用Gate.io API
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 筛选USDT交易对，按24h交易量排序
            usdt_pairs = [t for t in data if t.get('currency_pair', '').endswith('_USDT')]
            usdt_pairs.sort(key=lambda x: float(x.get('quote_volume', 0)), reverse=True)
            
            coins = []
            for pair in usdt_pairs[:limit]:
                symbol = pair['currency_pair'].replace('_USDT', '')
                coins.append({
                    'symbol': symbol,
                    'pair': pair['currency_pair'],
                    'volume_24h': float(pair.get('quote_volume', 0)),
                    'price': float(pair.get('last', 0))
                })
            return coins
    except Exception as e:
        print(f"[WARN] Gate.io获取失败: {e}", file=sys.stderr)
    
    return []


def get_kline_gateio(symbol: str, timeframe='5m', limit=200):
    """从Gate.io获取K线数据"""
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h'}
        interval = tf_map.get(timeframe, '5m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': f'{symbol}_USDT',
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


def extract_features_from_klines(klines: List[Dict], timeframe: str) -> Dict:
    """从K线数据提取特征"""
    if not klines or len(klines) < 20:
        return {}
    
    recent = klines[-50:] if len(klines) >= 50 else klines
    
    closes = [k['close'] for k in recent]
    highs = [k['high'] for k in recent]
    lows = [k['low'] for k in recent]
    
    # 趋势特征
    if len(closes) >= 10:
        price_trend = 'bullish' if closes[-1] > closes[0] else 'bearish'
        trend_strength = abs(closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
    else:
        price_trend = 'neutral'
        trend_strength = 0
    
    # K线特征
    kline_features = []
    if len(recent) >= 2:
        for i in range(max(1, len(recent) - 5), len(recent)):
            if i < 1:
                continue
            last = recent[i]
            prev = recent[i-1]
            
            if last['close'] > last['open'] and prev['close'] < prev['open']:
                if last['open'] < prev['close'] and last['close'] > prev['open']:
                    kline_features.append('bullish_engulfing')
            elif last['close'] < last['open'] and prev['close'] > prev['open']:
                if last['open'] > prev['close'] and last['close'] < prev['open']:
                    kline_features.append('bearish_engulfing')
            
            if last['high'] < prev['high'] and last['low'] > prev['low']:
                kline_features.append('inside_bar')
    
    # 波动率
    price_ranges = [(h - l) for h, l in zip(highs, lows)]
    avg_range = sum(price_ranges) / len(price_ranges) if price_ranges else 0
    volatility = avg_range / closes[-1] if closes and closes[-1] > 0 else 0
    
    features = {
        'pattern_type': 'unknown',
        'direction': 'long' if price_trend == 'bullish' else 'short' if price_trend == 'bearish' else 'neutral',
        'trend': price_trend,
        'trend_strength': trend_strength,
        'kline_features': list(set(kline_features)),
        'volatility': volatility,
        'market_conditions': {
            'trend_strength': 'strong' if trend_strength > 0.02 else 'weak',
            'volatility': 'high' if volatility > 0.01 else 'low',
            'trend_direction': price_trend
        }
    }
    
    return features


def generate_signal_from_match(match_result, current_price: float, klines: List[Dict]) -> Optional[Dict]:
    """从匹配结果生成交易信号"""
    pattern_name = match_result.pattern_name
    pattern_type = match_result.pattern_type
    source = match_result.source
    
    # 从模式类型推断方向
    direction = 'neutral'
    pattern_type_lower = pattern_type.lower() if pattern_type else ''
    
    if any(kw in pattern_type_lower for kw in ['bull', 'long', 'buy', 'up', 'ascending']):
        direction = 'long'
    elif any(kw in pattern_type_lower for kw in ['bear', 'short', 'sell', 'down', 'descending']):
        direction = 'short'
    else:
        pattern_name_lower = pattern_name.lower() if pattern_name else ''
        if any(kw in pattern_name_lower for kw in ['bull', 'long', 'buy', 'up', 'ascending']):
            direction = 'long'
        elif any(kw in pattern_name_lower for kw in ['bear', 'short', 'sell', 'down', 'descending']):
            direction = 'short'
        else:
            direction = 'long'  # 默认
    
    # 计算止损和止盈
    entry_price = current_price
    recent_lows = [k['low'] for k in klines[-10:]]
    recent_highs = [k['high'] for k in klines[-10:]]
    
    if direction == 'long':
        # 做多：止损在入场价下方
        stop_loss = min(recent_lows) if recent_lows else entry_price * 0.98
        # 确保止损不高于入场价
        stop_loss = min(stop_loss, entry_price * 0.99)
        stop_loss_pct = abs(entry_price - stop_loss) / entry_price
        take_profit_1 = entry_price * (1 + stop_loss_pct * 1.5)
        take_profit_2 = entry_price * (1 + stop_loss_pct * 2.5)
    else:
        # 做空：止损在入场价上方（重要！）
        # 使用最近高点，但必须确保止损价高于入场价
        candidate_stop = max(recent_highs) if recent_highs else entry_price * 1.02
        # 确保止损价至少比入场价高1%（防止使用历史低点）
        stop_loss = max(candidate_stop, entry_price * 1.01)
        stop_loss_pct = abs(stop_loss - entry_price) / entry_price
        take_profit_1 = entry_price * (1 - stop_loss_pct * 1.5)
        take_profit_2 = entry_price * (1 - stop_loss_pct * 2.5)
    
    return {
        'pattern_id': match_result.pattern_id,
        'pattern_name': pattern_name,
        'pattern_type': pattern_type,
        'source': source,
        'direction': direction,
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'confidence': match_result.combined_confidence,
        'final_score': match_result.final_score,
        'all_sources': match_result.all_sources or [source]
    }


async def generate_coin_plan(symbol: str, timeframe: str, matcher: EnhancedHybridMatcher) -> Optional[Dict]:
    """为单个币种生成交易计划"""
    # 获取K线数据
    klines = get_kline_gateio(symbol, timeframe, limit=200)
    if not klines or len(klines) < 50:
        return None
    
    current_price = klines[-1]['close']
    
    # 提取特征
    query_features = extract_features_from_klines(klines, timeframe)
    if not query_features:
        return None
    
    # 匹配模式（只取Top 1）
    try:
        klines_dict = {timeframe: klines}
        results = await matcher.async_match(
            query_features=query_features,
            klines_dict=klines_dict,
            symbol=f"{symbol}_USDT"
        )
        
        if not results:
            return None
        
        # 取最佳匹配
        best_match = results[0]
        signal = generate_signal_from_match(best_match, current_price, klines)
        
        if signal:
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_price': current_price,
                'signal': signal
            }
    except Exception as e:
        print(f"[WARN] {symbol} {timeframe} 匹配失败: {e}", file=sys.stderr)
    
    return None


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("ABU系统v3.0 - Top 20币种交易计划生成器")
    print("=" * 80)
    print()
    
    # 1. 获取Top 20币种
    print("1. 获取Top 20币种...")
    coins = get_top_coins(20)
    if not coins:
        print("[ERROR] 无法获取币种列表")
        return 1
    
    print(f"   找到 {len(coins)} 个币种")
    for i, coin in enumerate(coins[:10], 1):
        print(f"   {i}. {coin['symbol']} (24h交易量: ${coin['volume_24h']:,.0f})")
    print()
    
    # 2. 初始化匹配器（使用Gemini Flash）
    print("2. 初始化ABU系统v3.0匹配器...")
    print("   数据源: Gemini Flash (主要)")
    matcher = EnhancedHybridMatcher(
        strategy='comprehensive',
        use_async=True,
        use_vision=False,  # 不使用视觉验证以加快速度
        top_k=5,  # 每个币种只需要1个信号，但获取Top 5候选
        min_confidence=0.2,
        min_similarity=0.3
    )
    print("   [OK] 匹配器初始化完成")
    print()
    
    # 3. 为每个币种生成5分钟和15分钟信号
    print("3. 生成交易计划...")
    all_plans = []
    
    for i, coin in enumerate(coins, 1):
        symbol = coin['symbol']
        print(f"   [{i}/{len(coins)}] {symbol}...", end=' ', flush=True)
        
        # 5分钟信号
        plan_5m = await generate_coin_plan(symbol, '5m', matcher)
        
        # 15分钟信号
        plan_15m = await generate_coin_plan(symbol, '15m', matcher)
        
        if plan_5m or plan_15m:
            all_plans.append({
                'coin': coin,
                'plan_5m': plan_5m,
                'plan_15m': plan_15m
            })
            print(f"✓ (5m: {'✓' if plan_5m else '✗'}, 15m: {'✓' if plan_15m else '✗'})")
        else:
            print("✗ (无信号)")
    
    print()
    
    # 4. 生成报告
    print("4. 生成报告...")
    output = []
    output.append("# ABU系统v3.0 - Top 20币种交易计划")
    output.append("")
    output.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"**数据源**: Gemini Flash模式库（主要）")
    output.append(f"**币种数量**: {len(coins)}")
    output.append(f"**有信号的币种**: {len(all_plans)}")
    output.append("")
    output.append("---")
    output.append("")
    
    for plan_data in all_plans:
        coin = plan_data['coin']
        plan_5m = plan_data['plan_5m']
        plan_15m = plan_data['plan_15m']
        
        output.append(f"## {coin['symbol']}")
        output.append("")
        output.append(f"- **当前价格**: ${coin['price']:,.4f}")
        output.append(f"- **24h交易量**: ${coin['volume_24h']:,.0f}")
        output.append("")
        
        if plan_5m:
            signal = plan_5m['signal']
            output.append("### 5分钟信号")
            output.append("")
            output.append(f"- **模式**: {signal['pattern_name']} ({signal['pattern_type']})")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${signal['entry_price']:,.4f}")
            output.append(f"- **止损价**: ${signal['stop_loss']:,.4f}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:,.4f}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:,.4f}")
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            output.append(f"- **数据源**: {', '.join(signal['all_sources'])}")
            output.append("")
        
        if plan_15m:
            signal = plan_15m['signal']
            output.append("### 15分钟信号")
            output.append("")
            output.append(f"- **模式**: {signal['pattern_name']} ({signal['pattern_type']})")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${signal['entry_price']:,.4f}")
            output.append(f"- **止损价**: ${signal['stop_loss']:,.4f}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:,.4f}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:,.4f}")
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            output.append(f"- **数据源**: {', '.join(signal['all_sources'])}")
            output.append("")
        
        output.append("---")
        output.append("")
    
    # 保存文件
    output_file = ROOT / 'trading_signals' / f'ABU_v3_top20_coins_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with output_file.open('w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print(f"   [OK] 报告已保存: {output_file}")
    print()
    
    # 统计
    total_signals = sum(1 for p in all_plans if p['plan_5m']) + sum(1 for p in all_plans if p['plan_15m'])
    print("=" * 80)
    print("生成完成！")
    print("=" * 80)
    print(f"币种数量: {len(coins)}")
    print(f"有信号的币种: {len(all_plans)}")
    print(f"总信号数: {total_signals} (5分钟: {sum(1 for p in all_plans if p['plan_5m'])}, 15分钟: {sum(1 for p in all_plans if p['plan_15m'])})")
    print()
    
    # 清理
    matcher.close()
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
