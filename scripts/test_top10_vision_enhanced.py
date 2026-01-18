#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Top 10币种的视觉增强交易计划生成（方案1）
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
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# 导入必要的模块
try:
    from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
    from abu.common_pattern_extractor import CommonPatternExtractor
    from abu.brooks_parameter_extractor import BrooksParameterExtractor, DEFAULT_PARAMETERS
    from abu.chart_renderer import ChartRenderer
    from abu.direct_vision_analyzer import DirectVisionAnalyzer
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def get_top_coins(limit=10):
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
                        'volume': float(k[6])
                    })
                return klines
    except Exception as e:
        print(f"[WARN] K线获取失败 {symbol}: {e}", file=sys.stderr)
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
        }
    }


def validate_trading_plan(signal: Dict) -> tuple[bool, List[str]]:
    """验证交易计划"""
    errors = []
    
    if signal['direction'] == 'long':
        if signal['stop_loss'] >= signal['entry_price']:
            errors.append("做多止损应该在入场价下方")
        if signal['take_profit_1'] <= signal['entry_price']:
            errors.append("做多止盈应该在入场价上方")
    else:  # short
        if signal['stop_loss'] <= signal['entry_price']:
            errors.append("做空止损应该在入场价上方")
        if signal['take_profit_1'] >= signal['entry_price']:
            errors.append("做空止盈应该在入场价下方")
    
    return len(errors) == 0, errors


async def generate_coin_plan_with_vision(
    symbol: str,
    timeframe: str,
    matcher: EnhancedHybridMatcher,
    direct_vision_analyzer: DirectVisionAnalyzer,
    chart_renderer: ChartRenderer,
    common_extractor: CommonPatternExtractor,
    brooks_extractor: BrooksParameterExtractor
) -> Optional[Dict]:
    """为单个币种生成带视觉验证的交易计划"""
    try:
        # 过滤稳定币（Brooks规则：稳定币不生成交易信号）
        if symbol.upper() in {'USDC', 'USDT', 'BUSD', 'DAI', 'TUSD', 'PAXG'}:
            return None
        
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
        best_match = matches[0]
        
        # 渲染图表
        output_dir = ROOT / 'outputs' / 'charts'
        output_dir.mkdir(parents=True, exist_ok=True)
        chart_image_path = output_dir / f"{symbol}_{timeframe}_{int(datetime.now().timestamp())}.png"
        
        chart_renderer.render_klines_to_image(
            klines,
            output_path=chart_image_path,
            title=f"{symbol} {timeframe} Chart"
        )
        
        if not chart_image_path.exists():
            return None
        
        # 视觉分析（方案1：直接分析实时图表）
        vision_result = None
        vision_score = None
        direct_vision_pattern = None
        
        if direct_vision_analyzer and chart_image_path.exists():
            # 准备Top 3候选
            pattern_candidates = []
            for match in matches[:3]:
                pattern_candidates.append({
                    'pattern_name': match.pattern_name,
                    'pattern_type': match.pattern_type,
                    'source': match.source,
                    'confidence': match.combined_confidence
                })
            
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
        
        # 从Brooks规则提取参数
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
            if direct_vision_pattern['pattern_name'] != 'Unknown':
                pattern_name = direct_vision_pattern['pattern_name']
                pattern_type = direct_vision_pattern['pattern_type']
        else:
            direction = 'long'
            pattern_type_lower = best_match.pattern_type.lower()
            if any(kw in pattern_type_lower for kw in ['bear', 'short', 'sell', 'down']):
                direction = 'short'
            elif any(kw in pattern_type_lower for kw in ['bull', 'long', 'buy', 'up']):
                direction = 'long'
        
        # 计算止损和止盈
        entry_price = current_price
        stop_loss_pct = trading_params.stop_loss_pct if trading_params.stop_loss_pct else 0.02
        take_profit_pct = trading_params.take_profit_pct if trading_params.take_profit_pct else (stop_loss_pct * 2.0)
        
        recent_lows = [k['low'] for k in klines[-10:]]
        recent_highs = [k['high'] for k in klines[-10:]]
        
        # 对于价格极小的币种（< $1），需要特殊处理精度问题
        is_small_price = entry_price < 1.0
        
        if direction == 'long':
            # 做多：止损在入场价下方
            candidate_stop = min(recent_lows) if recent_lows else entry_price * (1 - stop_loss_pct)
            # 确保止损在入场价下方，且距离至少满足最小要求
            min_stop_price = entry_price * (1 - min_stop_distance_pct)
            stop_loss = min(candidate_stop, min_stop_price)
            
            # 对于小价格币种，确保止损有足够的绝对距离
            if is_small_price:
                min_absolute_distance = entry_price * 0.005  # 0.5%
                min_stop_absolute = entry_price - min_absolute_distance
                stop_loss = min(stop_loss, min_stop_absolute)
            
            # 再次确保止损低于入场价（至少1%或最小距离）
            final_min_stop = entry_price * (1 - max(min_stop_distance_pct, 0.01))
            stop_loss = min(stop_loss, final_min_stop)
            
            # 最终验证：止损必须明显低于入场价
            if stop_loss >= entry_price * 0.999:  # 如果止损太接近入场价（误差<0.1%）
                stop_loss = entry_price * (1 - min_stop_distance_pct)
            
            # 计算盈亏比，确保至少2:1
            risk = entry_price - stop_loss
            if risk <= 0 or risk < entry_price * 0.001:  # 风险太小（<0.1%）
                stop_loss = entry_price * (1 - min_stop_distance_pct)
                risk = entry_price - stop_loss
            
            if risk > 0:
                min_reward = risk * 2.0  # 至少2:1
                take_profit_1 = entry_price + min_reward
                take_profit_2 = entry_price + risk * 3.0  # 理想3:1
            else:
                take_profit_1 = entry_price * (1 + take_profit_pct)
                take_profit_2 = entry_price * (1 + take_profit_pct * 1.5)
        else:
            # 做空：止损在入场价上方
            candidate_stop = max(recent_highs) if recent_highs else entry_price * (1 + stop_loss_pct)
            # 确保止损在入场价上方，且距离至少满足最小要求
            max_stop_price = entry_price * (1 + min_stop_distance_pct)
            stop_loss = max(candidate_stop, max_stop_price)
            
            # 对于小价格币种，确保止损有足够的绝对距离
            if is_small_price:
                min_absolute_distance = entry_price * 0.005  # 0.5%
                max_stop_absolute = entry_price + min_absolute_distance
                stop_loss = max(stop_loss, max_stop_absolute)
            
            # 再次确保止损高于入场价（至少1%或最小距离）
            final_max_stop = entry_price * (1 + max(min_stop_distance_pct, 0.01))
            stop_loss = max(stop_loss, final_max_stop)
            
            # 最终验证：止损必须明显高于入场价
            if stop_loss <= entry_price * 1.001:  # 如果止损太接近入场价（误差<0.1%）
                stop_loss = entry_price * (1 + min_stop_distance_pct)
            
            # 计算盈亏比，确保至少2:1
            risk = stop_loss - entry_price
            if risk <= 0 or risk < entry_price * 0.001:  # 风险太小（<0.1%）
                stop_loss = entry_price * (1 + min_stop_distance_pct)
                risk = stop_loss - entry_price
            
            if risk > 0:
                min_reward = risk * 2.0  # 至少2:1
                take_profit_1 = entry_price - min_reward
                take_profit_2 = entry_price - risk * 3.0  # 理想3:1
            else:
                take_profit_1 = entry_price * (1 - take_profit_pct)
                take_profit_2 = entry_price * (1 - take_profit_pct * 1.5)
        
        # 计算综合置信度
        if vision_score and vision_score > 0:
            combined_confidence = (best_match.combined_confidence * 0.6 + vision_score * 0.4)
        else:
            combined_confidence = best_match.combined_confidence
        
        signal = {
            'pattern_id': best_match.pattern_id,
            'pattern_name': pattern_name,
            'pattern_type': pattern_type,
            'source': best_match.source,
            'direction': direction,
            'entry_price': entry_price,
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
        
        # 验证交易计划（基础验证）
        is_valid, errors = validate_trading_plan(signal)
        signal['validation_errors'] = errors
        signal['is_valid'] = is_valid
        
        # Brooks规则验证
        try:
            from abu.brooks_trading_validator import BrooksTradingValidator
            validator = BrooksTradingValidator()
            validation_result = validator.validate_signal(signal)
            
            signal['brooks_validation'] = {
                'is_valid': validation_result.is_valid,
                'level': validation_result.level.value,
                'score': validation_result.score,
                'issues': validation_result.issues,
                'warnings': validation_result.warnings
            }
            
            # 如果Brooks验证失败，标记为无效
            if not validation_result.is_valid:
                signal['is_valid'] = False
                signal['validation_errors'].extend(validation_result.issues)
        except ImportError:
            pass
        
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
    print("视觉增强交易计划生成器 - Top 10币种测试")
    print("=" * 80)
    print()
    print("注意: 此测试会产生API调用费用")
    print("测试范围: 10个币种 × 2个时间框架 = 20次视觉分析")
    print("预计成本: ~$0.10")
    print()
    
    # 1. 获取Top 10币种
    print("1. 获取Top 10币种...")
    coins = get_top_coins(10)
    if not coins:
        print("[ERROR] 无法获取币种列表")
        return 1
    
    print(f"   找到 {len(coins)} 个币种: {', '.join([c['symbol'] for c in coins])}")
    print()
    
    # 2. 初始化组件
    print("2. 初始化组件...")
    
    matcher = EnhancedHybridMatcher(
        strategy='comprehensive',
        use_async=True,
        use_vision=False,
        top_k=10,
        min_confidence=0.2,
        min_similarity=0.25
    )
    
    common_extractor = CommonPatternExtractor(matcher.pattern_library)
    common_patterns = common_extractor.extract_common_patterns(min_sources=2)
    print(f"   找到 {len(common_patterns)} 个共同模式")
    
    brooks_extractor = BrooksParameterExtractor()
    chart_renderer = ChartRenderer()
    
    try:
        direct_vision_analyzer = DirectVisionAnalyzer()
        print("   [OK] 直接视觉分析器初始化完成（方案1）")
    except Exception as e:
        print(f"   [ERROR] 直接视觉分析器初始化失败: {e}")
        return 1
    
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
            symbol, '5m', matcher, direct_vision_analyzer,
            chart_renderer, common_extractor, brooks_extractor
        )
        
        # 15分钟信号
        plan_15m = await generate_coin_plan_with_vision(
            symbol, '15m', matcher, direct_vision_analyzer,
            chart_renderer, common_extractor, brooks_extractor
        )
        
        if plan_5m or plan_15m:
            all_plans.append({
                'coin': coin,
                'plan_5m': plan_5m,
                'plan_15m': plan_15m
            })
            print("✓")
        else:
            print("✗")
    
    print()
    
    # 4. 生成报告
    print("4. 生成报告...")
    
    output_dir = ROOT / 'outputs' / 'trading_plans'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"top10_vision_enhanced_{timestamp}.md"
    
    output = []
    output.append("# Top 10币种视觉增强交易计划")
    output.append("")
    output.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"**数据源**: Gemini Flash + Cursor AI + Brooks规则")
    output.append(f"**视觉验证**: Gemini Vision API（直接分析实时图表）")
    output.append(f"**共同模式**: {len(common_patterns)}个")
    
    # 成本统计
    cost_summary = direct_vision_analyzer.get_cost_summary()
    output.append(f"**视觉分析成本**: ${cost_summary['total_cost_usd']:.4f} ({cost_summary['total_calls']}次调用)")
    output.append("")
    
    # 交易计划
    for plan_data in all_plans:
        coin = plan_data['coin']
        plan_5m = plan_data['plan_5m']
        plan_15m = plan_data['plan_15m']
        
        output.append(f"## {coin['symbol']} (${coin['price']:,.2f})")
        output.append("")
        
        if plan_5m:
            signal = plan_5m['signal']
            output.append("### 5分钟信号")
            output.append("")
            output.append(f"- **模式**: {signal['pattern_name']} ({signal['pattern_type']})")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${signal['entry_price']:,.2f}")
            output.append(f"- **止损**: ${signal['stop_loss']:,.2f}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:,.2f}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:,.2f}")
            output.append(f"- **综合置信度**: {signal['confidence']:.2%}")
            
            if signal.get('vision_score'):
                output.append(f"- **视觉分析**: {signal['vision_score']:.2%}")
                if signal.get('vision_result'):
                    vr = signal['vision_result']
                    output.append(f"  - 识别模式: {vr.get('pattern_name', 'Unknown')} ({vr.get('pattern_type', 'unknown')})")
                    output.append(f"  - 关键特征: {', '.join(vr.get('key_features', [])[:3])}")
            
            if signal.get('algorithm_confidence'):
                output.append(f"- **算法匹配**: {signal['algorithm_confidence']:.2%}")
            
            if not signal.get('is_valid', True):
                output.append(f"- ⚠️ **验证错误**: {', '.join(signal.get('validation_errors', []))}")
            
            output.append("")
        
        if plan_15m:
            signal = plan_15m['signal']
            output.append("### 15分钟信号")
            output.append("")
            output.append(f"- **模式**: {signal['pattern_name']} ({signal['pattern_type']})")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${signal['entry_price']:,.2f}")
            output.append(f"- **止损**: ${signal['stop_loss']:,.2f}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:,.2f}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:,.2f}")
            output.append(f"- **综合置信度**: {signal['confidence']:.2%}")
            
            if signal.get('vision_score'):
                output.append(f"- **视觉分析**: {signal['vision_score']:.2%}")
                if signal.get('vision_result'):
                    vr = signal['vision_result']
                    output.append(f"  - 识别模式: {vr.get('pattern_name', 'Unknown')} ({vr.get('pattern_type', 'unknown')})")
                    output.append(f"  - 关键特征: {', '.join(vr.get('key_features', [])[:3])}")
            
            if signal.get('algorithm_confidence'):
                output.append(f"- **算法匹配**: {signal['algorithm_confidence']:.2%}")
            
            if not signal.get('is_valid', True):
                output.append(f"- ⚠️ **验证错误**: {', '.join(signal.get('validation_errors', []))}")
            
            output.append("")
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))
    
    print(f"   [OK] 报告已保存: {output_file}")
    print()
    
    # 5. 总结
    print("=" * 80)
    print("生成完成")
    print("=" * 80)
    print()
    print(f"成功生成: {len(all_plans)}/{len(coins)} 个币种")
    print(f"总成本: ${cost_summary['total_cost_usd']:.4f}")
    print(f"平均成本/次: ${cost_summary['avg_cost_per_call']:.4f}")
    print()
    print(f"报告文件: {output_file}")
    print()
    
    # 6. 自动回测
    print("5. 自动回测交易计划...")
    try:
        from abu.auto_backtest_integration import AutoBacktestIntegration
        
        backtest_integration = AutoBacktestIntegration()
        backtest_result, error = backtest_integration.run_backtest(output_file)
        
        if error:
            print(f"   [WARN] 回测失败: {error}")
        else:
            # 保存回测结果
            backtest_output_dir = ROOT / 'outputs' / 'backtest_results'
            backtest_report_file = backtest_integration.save_backtest_result(
                backtest_result,
                backtest_output_dir
            )
            print(f"   [OK] 回测完成，报告已保存: {backtest_report_file}")
            
            # 打印反馈
            backtest_integration.print_feedback(backtest_result)
    except Exception as e:
        print(f"   [WARN] 自动回测失败: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
