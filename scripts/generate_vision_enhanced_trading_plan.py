#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉增强交易计划生成器

使用Gemini Vision API识别Top 20币种的5分钟和15分钟图表，
结合模式匹配生成高概率交易计划。
"""

import sys
import asyncio
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# 导入必要的模块
try:
    from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
    from abu.common_pattern_extractor import CommonPatternExtractor
    from abu.brooks_parameter_extractor import BrooksParameterExtractor, DEFAULT_PARAMETERS
    from abu.chart_renderer import ChartRenderer
    from abu.ai_vision_matcher import AIVisionMatcher
    from abu.direct_vision_analyzer import DirectVisionAnalyzer
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def get_top_coins(limit=20):
    """获取Top N币种（按24h交易量）"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
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
    
    if len(closes) >= 10:
        price_trend = 'bullish' if closes[-1] > closes[0] else 'bearish'
        trend_strength = abs(closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
    else:
        price_trend = 'neutral'
        trend_strength = 0
    
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
    
    price_ranges = [(h - l) for h, l in zip(highs, lows)]
    avg_range = sum(price_ranges) / len(price_ranges) if price_ranges else 0
    volatility = avg_range / closes[-1] if closes and closes[-1] > 0 else 0
    
    return {
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


def validate_trading_plan(signal: Dict) -> tuple:
    """
    验证交易计划，检查低级错误
    
    Returns:
        (is_valid, errors)
    """
    errors = []
    
    direction = signal.get('direction', '').lower()
    entry_price = signal.get('entry_price', 0)
    stop_loss = signal.get('stop_loss', 0)
    take_profit_1 = signal.get('take_profit_1', 0)
    
    if not entry_price or entry_price <= 0:
        errors.append("入场价无效")
        return False, errors
    
    # 检查止损方向
    if direction == 'long':
        if stop_loss >= entry_price:
            errors.append(f"做多止损错误：止损价({stop_loss})应该低于入场价({entry_price})")
        if take_profit_1 <= entry_price:
            errors.append(f"做多止盈错误：止盈价({take_profit_1})应该高于入场价({entry_price})")
    elif direction == 'short':
        if stop_loss <= entry_price:
            errors.append(f"做空止损错误：止损价({stop_loss})应该高于入场价({entry_price})")
        if take_profit_1 >= entry_price:
            errors.append(f"做空止盈错误：止盈价({take_profit_1})应该低于入场价({entry_price})")
    
    # 检查盈亏比
    if direction == 'long':
        risk = entry_price - stop_loss
        reward = take_profit_1 - entry_price
    else:
        risk = stop_loss - entry_price
        reward = entry_price - take_profit_1
    
    if risk <= 0:
        errors.append(f"风险计算错误：风险({risk})应该大于0")
    else:
        rr_ratio = reward / risk if risk > 0 else 0
        if rr_ratio < 1.0:
            errors.append(f"盈亏比过低：{rr_ratio:.2f}:1，建议至少1.5:1")
    
    return len(errors) == 0, errors


async def generate_coin_plan_with_vision(
    symbol: str,
    timeframe: str,
    matcher: EnhancedHybridMatcher,
    vision_matcher: Optional[AIVisionMatcher],
    direct_vision_analyzer: Optional[DirectVisionAnalyzer],
    chart_renderer: ChartRenderer,
    common_extractor: CommonPatternExtractor,
    brooks_extractor: BrooksParameterExtractor,
    use_direct_vision: bool = True  # 使用方案1：直接分析
) -> Optional[Dict]:
    """为单个币种生成带视觉验证的交易计划"""
    # 获取K线数据
    klines = get_kline_gateio(symbol, timeframe, limit=200)
    if not klines or len(klines) < 50:
        return None
    
    current_price = klines[-1]['close']
    
    # 提取特征
    query_features = extract_features_from_klines(klines, timeframe)
    if not query_features:
        return None
    
    # 模式匹配
    try:
        klines_dict = {timeframe: klines}
        matches = await matcher.async_match(
            query_features=query_features,
            klines_dict=klines_dict,
            symbol=f"{symbol}_USDT"
        )
        
        if not matches:
            return None
        
        # 优先使用共同模式
        matches_dict = [{'pattern_id': m.pattern_id, 'confidence': m.combined_confidence, 
                        'pattern': m} for m in matches]
        prioritized_matches = common_extractor.prioritize_common_patterns(matches_dict)
        
        # 取最佳匹配
        best_match = matches[0]  # 已经按分数排序
        
        # 渲染图表
        chart_image_path = chart_renderer.render_chart(
            klines, 
            symbol=symbol,
            timeframe=timeframe,
            output_dir=ROOT / 'outputs' / 'charts'
        )
        
        # 视觉分析（方案1：直接分析实时图表）
        vision_result = None
        vision_score = None
        direct_vision_pattern = None
        
        if use_direct_vision and direct_vision_analyzer and chart_image_path and chart_image_path.exists():
            # 准备模式候选（Top 3）
            pattern_candidates = []
            for match in matches[:3]:
                pattern_candidates.append({
                    'pattern_name': match.pattern_name,
                    'pattern_type': match.pattern_type,
                    'source': match.source,
                    'confidence': match.combined_confidence
                })
            
            # 直接分析实时图表
            try:
                vision_result = direct_vision_analyzer.analyze_chart_directly(
                    chart_image_path,
                    pattern_candidates=pattern_candidates,
                    symbol=symbol,
                    timeframe=timeframe
                )
                vision_score = vision_result.confidence
                direct_vision_pattern = {
                    'pattern_name': vision_result.pattern_name,
                    'pattern_type': vision_result.pattern_type,
                    'direction': vision_result.direction,
                    'key_features': vision_result.key_features
                }
            except Exception as e:
                print(f"  [WARN] 视觉分析失败: {e}", file=sys.stderr)
        
        # 备用：图片对比（如果模式有图片且未使用直接分析）
        elif vision_matcher and best_match.pattern and hasattr(best_match.pattern, 'image_path') and best_match.pattern.image_path:
            pattern_image_path = Path(best_match.pattern.image_path)
            if pattern_image_path.exists():
                try:
                    vision_result_compare = vision_matcher.compare_two_images(
                        pattern_image_path,
                        chart_image_path,
                        context=f"{symbol} {timeframe} chart"
                    )
                    vision_score = vision_result_compare.similarity_score / 100.0
                except Exception as e:
                    print(f"  [WARN] 视觉对比失败: {e}", file=sys.stderr)
        
        # 从Brooks规则提取参数（如果匹配到Brooks规则）
        trading_params = DEFAULT_PARAMETERS
        if best_match.source == 'brooks_rule' and best_match.pattern:
            raw_data = best_match.pattern.raw_data if hasattr(best_match.pattern, 'raw_data') else {}
            if raw_data:
                trading_params = brooks_extractor.extract_parameters(
                    raw_data.get('trading_rules', {}),
                    raw_data.get('content_text', ''),
                    raw_data.get('key_concepts', [])
                )
        
        # 生成信号（优先使用视觉分析结果）
        pattern_name = best_match.pattern_name
        pattern_type = best_match.pattern_type
        
        if direct_vision_pattern and direct_vision_pattern['direction'] != 'neutral':
            direction = direct_vision_pattern['direction']
            # 如果视觉分析识别出模式，使用视觉分析的结果
            if direct_vision_pattern['pattern_name'] != 'Unknown':
                pattern_name = direct_vision_pattern['pattern_name']
                pattern_type = direct_vision_pattern['pattern_type']
        else:
            # 从算法匹配结果推断
            direction = 'long'  # 默认
            pattern_type_lower = best_match.pattern_type.lower()
            if any(kw in pattern_type_lower for kw in ['bear', 'short', 'sell', 'down']):
                direction = 'short'
            elif any(kw in pattern_type_lower for kw in ['bull', 'long', 'buy', 'up']):
                direction = 'long'
        
        # 计算止损和止盈（使用Brooks参数或默认值）
        entry_price = current_price
        stop_loss_pct = trading_params.stop_loss_pct if trading_params.stop_loss_pct else 0.02
        take_profit_pct = trading_params.take_profit_pct if trading_params.take_profit_pct else (stop_loss_pct * 2.0)
        
        # 从K线数据计算止损（确保止损在正确方向）
        recent_lows = [k['low'] for k in klines[-10:]]
        recent_highs = [k['high'] for k in klines[-10:]]
        
        if direction == 'long':
            # 做多：止损在入场价下方
            candidate_stop = min(recent_lows) if recent_lows else entry_price * (1 - stop_loss_pct)
            stop_loss = min(candidate_stop, entry_price * 0.99)  # 确保止损低于入场价
            take_profit_1 = entry_price * (1 + take_profit_pct)
            take_profit_2 = entry_price * (1 + take_profit_pct * 1.5)
        else:
            # 做空：止损在入场价上方
            candidate_stop = max(recent_highs) if recent_highs else entry_price * (1 + stop_loss_pct)
            stop_loss = max(candidate_stop, entry_price * 1.01)  # 确保止损高于入场价
            take_profit_1 = entry_price * (1 - take_profit_pct)
            take_profit_2 = entry_price * (1 - take_profit_pct * 1.5)
        
        # 计算综合置信度（结合算法匹配和视觉分析）
        if vision_score and vision_score > 0:
            # 如果视觉分析可用，综合算法匹配和视觉分析
            combined_confidence = (best_match.combined_confidence * 0.6 + vision_score * 0.4)
        else:
            combined_confidence = best_match.combined_confidence
        
        signal = {
            'pattern_id': best_match.pattern_id,
            'pattern_name': pattern_name,
            'pattern_type': pattern_type,
            'source': best_match.source,
            'direction': direction,
            'entry_price': current_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'confidence': combined_confidence,
            'algorithm_confidence': best_match.combined_confidence,
            'vision_score': vision_score,
            'vision_result': direct_vision_pattern,
            'final_score': best_match.final_score,
            'is_common_pattern': best_match.pattern_id in common_extractor.get_common_pattern_ids(),
            'trading_params': trading_params,
            'all_sources': best_match.all_sources or [best_match.source]
        }
        
        # 验证交易计划
        is_valid, errors = validate_trading_plan(signal)
        signal['validation_errors'] = errors
        signal['is_valid'] = is_valid
        
        if not is_valid:
            print(f"  [WARN] {symbol} {timeframe} 交易计划验证失败: {', '.join(errors)}")
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'current_price': current_price,
            'signal': signal
        }
    except Exception as e:
        print(f"[WARN] {symbol} {timeframe} 生成失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    
    return None


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("视觉增强交易计划生成器 - Top 20币种")
    print("=" * 80)
    print()
    
    # 1. 获取Top 20币种
    print("1. 获取Top 20币种...")
    coins = get_top_coins(20)
    if not coins:
        print("[ERROR] 无法获取币种列表")
        return 1
    
    print(f"   找到 {len(coins)} 个币种")
    print()
    
    # 2. 初始化组件
    print("2. 初始化组件...")
    
    # 匹配器
    matcher = EnhancedHybridMatcher(
        strategy='comprehensive',
        use_async=True,
        use_vision=False,  # 我们手动使用视觉匹配
        top_k=10,
        min_confidence=0.2,
        min_similarity=0.25
    )
    
    # 共同模式提取器
    common_extractor = CommonPatternExtractor(matcher.pattern_library)
    common_patterns = common_extractor.extract_common_patterns(min_sources=2)
    print(f"   找到 {len(common_patterns)} 个共同模式")
    
    # Brooks参数提取器
    brooks_extractor = BrooksParameterExtractor()
    
    # 图表渲染器
    chart_renderer = ChartRenderer()
    
    # 视觉匹配器（备用：图片对比）
    try:
        vision_matcher = AIVisionMatcher()
        print("   [OK] 视觉匹配器初始化完成（备用）")
    except Exception as e:
        print(f"   [WARN] 视觉匹配器初始化失败: {e}")
        vision_matcher = None
    
    # 直接视觉分析器（方案1：推荐）
    try:
        direct_vision_analyzer = DirectVisionAnalyzer()
        print("   [OK] 直接视觉分析器初始化完成（方案1）")
    except Exception as e:
        print(f"   [WARN] 直接视觉分析器初始化失败: {e}")
        direct_vision_analyzer = None
    
    print("   [OK] 所有组件初始化完成")
    print()
    
    # 3. 生成交易计划
    print("3. 生成交易计划...")
    all_plans = []
    
    for i, coin in enumerate(coins, 1):
        symbol = coin['symbol']
        print(f"   [{i}/{len(coins)}] {symbol}...", end=' ', flush=True)
        
        # 5分钟信号
        plan_5m = await generate_coin_plan_with_vision(
            symbol, '5m', matcher, vision_matcher, direct_vision_analyzer,
            chart_renderer, common_extractor, brooks_extractor,
            use_direct_vision=True
        )
        
        # 15分钟信号
        plan_15m = await generate_coin_plan_with_vision(
            symbol, '15m', matcher, vision_matcher, direct_vision_analyzer,
            chart_renderer, common_extractor, brooks_extractor,
            use_direct_vision=True
        )
        
        if plan_5m or plan_15m:
            all_plans.append({
                'coin': coin,
                'plan_5m': plan_5m,
                'plan_15m': plan_15m
            })
            valid_5m = plan_5m['signal']['is_valid'] if plan_5m else False
            valid_15m = plan_15m['signal']['is_valid'] if plan_15m else False
            print(f"✓ (5m: {'✓' if plan_5m and valid_5m else '✗' if plan_5m else '-'}, "
                  f"15m: {'✓' if plan_15m and valid_15m else '✗' if plan_15m else '-'})")
        else:
            print("✗ (无信号)")
    
    print()
    
    # 4. 生成报告
    print("4. 生成报告...")
    output = []
    output.append("# 视觉增强交易计划 - Top 20币种")
    output.append("")
    output.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"**数据源**: Gemini Flash + Cursor AI + Brooks规则")
    output.append(f"**视觉验证**: Gemini Vision API（直接分析实时图表）")
    output.append(f"**共同模式**: {len(common_patterns)}个")
    
    # 成本统计
    if direct_vision_analyzer:
        cost_summary = direct_vision_analyzer.get_cost_summary()
        output.append(f"**视觉分析成本**: ${cost_summary['total_cost_usd']:.4f} ({cost_summary['total_calls']}次调用)")
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
        
        for plan, tf_name in [(plan_5m, '5分钟'), (plan_15m, '15分钟')]:
            if not plan:
                continue
            
            signal = plan['signal']
            output.append(f"### {tf_name}信号")
            output.append("")
            
            if not signal.get('is_valid', True):
                output.append("⚠️ **验证失败**: " + ", ".join(signal.get('validation_errors', [])))
                output.append("")
            
            output.append(f"- **模式**: {signal['pattern_name']} ({signal['pattern_type']})")
            output.append(f"- **数据源**: {', '.join(signal['all_sources'])}")
            if signal.get('is_common_pattern'):
                output.append(f"- **共同模式**: ✓ (多个数据源匹配)")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${signal['entry_price']:,.4f}")
            output.append(f"- **止损价**: ${signal['stop_loss']:,.4f}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:,.4f}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:,.4f}")
            
            # 计算盈亏比
            if signal['direction'] == 'long':
                risk = signal['entry_price'] - signal['stop_loss']
                reward = signal['take_profit_1'] - signal['entry_price']
            else:
                risk = signal['stop_loss'] - signal['entry_price']
                reward = signal['entry_price'] - signal['take_profit_1']
            
            rr_ratio = reward / risk if risk > 0 else 0
            output.append(f"- **盈亏比**: {rr_ratio:.2f}:1")
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            
            if signal.get('vision_score'):
                output.append(f"- **视觉分析**: {signal['vision_score']:.2%}")
                if signal.get('vision_result'):
                    vr = signal['vision_result']
                    output.append(f"  - 识别模式: {vr.get('pattern_name', 'Unknown')} ({vr.get('pattern_type', 'unknown')})")
                    output.append(f"  - 关键特征: {', '.join(vr.get('key_features', [])[:3])}")
            
            if signal.get('algorithm_confidence'):
                output.append(f"- **算法匹配**: {signal['algorithm_confidence']:.2%}")
            
            # Brooks参数
            if signal.get('trading_params'):
                params = signal['trading_params']
                if params.notes:
                    output.append(f"- **Brooks参数**: {', '.join(params.notes)}")
            
            output.append("")
        
        output.append("---")
        output.append("")
    
    # 保存文件
    output_file = ROOT / 'trading_signals' / f'vision_enhanced_plan_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with output_file.open('w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print(f"   [OK] 报告已保存: {output_file}")
    print()
    
    # 统计
    total_signals = sum(1 for p in all_plans if p['plan_5m']) + sum(1 for p in all_plans if p['plan_15m'])
    valid_signals = sum(1 for p in all_plans 
                       if (p['plan_5m'] and p['plan_5m']['signal'].get('is_valid', False)) or
                          (p['plan_15m'] and p['plan_15m']['signal'].get('is_valid', False)))
    
    print("=" * 80)
    print("生成完成！")
    print("=" * 80)
    print(f"币种数量: {len(coins)}")
    print(f"有信号的币种: {len(all_plans)}")
    print(f"总信号数: {total_signals}")
    print(f"有效信号数: {valid_signals}")
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
