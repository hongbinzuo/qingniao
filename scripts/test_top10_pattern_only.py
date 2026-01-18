#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Top 10币种的纯模式匹配交易计划生成（不使用视觉分析）
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
    from abu.timeframe_risk_calculator import TimeframeRiskCalculator
    from abu.chart_renderer import ChartRenderer
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


async def generate_coin_plan_pattern_only(
    symbol: str,
    timeframe: str,
    matcher: EnhancedHybridMatcher,
    common_extractor: CommonPatternExtractor,
    brooks_extractor: BrooksParameterExtractor,
    risk_calculator: TimeframeRiskCalculator
) -> Optional[Dict]:
    """为单个币种生成纯模式匹配交易计划（不使用视觉分析）"""
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
        
        # 生成信号（仅使用算法匹配结果）
        # 根据模式类型确定方向（符合Brooks顺势原则）
        pattern_name_lower = best_match.pattern_name.lower()
        pattern_type_lower = best_match.pattern_type.lower()
        
        # 检查是否为上升趋势模式
        is_bull_pattern = any(kw in pattern_name_lower or kw in pattern_type_lower 
                            for kw in ['bull', 'ascending', '上升', '多头', 'small pullback bull'])
        
        # 检查是否为下降趋势模式
        is_bear_pattern = any(kw in pattern_name_lower or kw in pattern_type_lower 
                            for kw in ['bear', 'descending', '下降', '空头'])
        
        # 确定方向（优先考虑模式类型）
        if is_bull_pattern:
            direction = 'long'  # 上升趋势必须做多
        elif is_bear_pattern:
            direction = 'short'  # 下降趋势必须做空
        else:
            # 如果没有明确模式，根据pattern_type推断
            if any(kw in pattern_type_lower for kw in ['bear', 'short', 'sell', 'down']):
                direction = 'short'
            elif any(kw in pattern_type_lower for kw in ['bull', 'long', 'buy', 'up']):
                direction = 'long'
            else:
                direction = 'long'  # 默认做多
        
        pattern_name = best_match.pattern_name
        pattern_type = best_match.pattern_type
        
        # 获取完整的模式描述（用于显示和匹配）
        # 优先使用pattern_type，因为它通常包含更详细的描述（如"Small Pullback Bull Trend"）
        full_pattern_description = pattern_name
        if pattern_type and pattern_type != pattern_name:
            full_pattern_description = f"{pattern_name} ({pattern_type})"
        
        pattern = matcher.pattern_library.patterns.get(best_match.pattern_id)
        if pattern and pattern.raw_data:
            # 尝试从raw_data获取更完整的描述
            raw_name = pattern.raw_data.get('pattern_name') or pattern.raw_data.get('name')
            if raw_name:
                # 如果raw_name包含更多信息（比如括号内容），使用它
                if '(' in raw_name or len(raw_name) > len(pattern_name):
                    full_pattern_description = raw_name
        
        # 使用时间周期风险计算器（专业交易员方法）
        # 入场价：使用当前价格（5分钟信号不能等太久）
        entry_price = current_price
        
        # 获取时间框架参数
        timeframe_params = risk_calculator.get_params(timeframe)
        
        # 计算止损（基于时间框架和波动）
        recent_lows = [k['low'] for k in klines[-10:]]
        recent_highs = [k['high'] for k in klines[-10:]]
        is_small_price = entry_price < 1.0
        
        stop_loss, stop_loss_distance_pct = risk_calculator.calculate_stop_loss(
            entry_price=entry_price,
            direction=direction,
            timeframe=timeframe,
            recent_lows=recent_lows if direction == 'long' else None,
            recent_highs=recent_highs if direction == 'short' else None,
            is_small_price=is_small_price
        )
        
        # 计算止盈
        take_profit_1, take_profit_2 = risk_calculator.calculate_take_profit(
            entry_price=entry_price,
            stop_loss=stop_loss,
            direction=direction,
            timeframe=timeframe
        )
        
        # 估算入场概率（如果目标入场价与当前价差异较大）
        entry_probability_info = risk_calculator.estimate_entry_probability(
            current_price=current_price,
            target_entry_price=entry_price,  # 当前价格就是入场价
            timeframe=timeframe
        )
        
        # 计算仓位（基于风险）
        account_equity = 10000.0  # 默认账户权益
        position_info = risk_calculator.calculate_position_size(
            account_equity=account_equity,
            entry_price=entry_price,
            stop_loss=stop_loss,
            risk_per_trade_pct=1.0,  # 单笔交易风险1%
            timeframe=timeframe
        )
        
        
        # 使用算法匹配置信度
        combined_confidence = best_match.combined_confidence
        
        # 获取概率信息（改进匹配逻辑）
        probability_score = None
        import re
        
        # 方法1: 从模式对象获取
        if pattern and pattern.probability_score:
            probability_score = pattern.probability_score
            print(f"      [DEBUG] {symbol} {timeframe}: 从模式对象获取概率 {probability_score}%", file=sys.stderr)
        # 方法2: 直接匹配模式名称
        elif pattern_name in matcher.pattern_library.probability_rules:
            probability_score = matcher.pattern_library.probability_rules[pattern_name].get('probability')
            print(f"      [DEBUG] {symbol} {timeframe}: 直接匹配模式名称'{pattern_name}'，概率 {probability_score}%", file=sys.stderr)
        # 方法3: 从模式名称中提取关键词匹配（处理"Pattern from page 12 (Small Pullback Bull Trend)"这种情况）
        else:
            # 调试：检查概率规则是否加载
            if not matcher.pattern_library.probability_rules:
                print(f"      [WARN] {symbol} {timeframe}: 概率规则未加载", file=sys.stderr)
            else:
                # 常见模式关键词（按优先级排序，更具体的先匹配）
                keywords = [
                    'bull trend', 'bear trend',  # 先匹配两个词的组合
                    'pullback', 'breakout', 'reversal',
                    'wedge', 'channel', 'flag', 'triangle', 
                    'double top', 'double bottom',
                    'head and shoulders', 'cup and handle', 
                    'ascending triangle', 'descending triangle'
                ]
                
                # 先尝试从模式名称中提取括号内容
                pattern_text_lower = full_pattern_description.lower()
                bracket_match = re.search(r'\(([^)]+)\)', full_pattern_description)
                if bracket_match:
                    bracket_content = bracket_match.group(1).lower()
                    pattern_text_lower = bracket_content
                # 如果没有括号，直接使用pattern_type（通常包含更详细的描述）
                elif pattern_type and pattern_type != pattern_name:
                    pattern_text_lower = pattern_type.lower()
                
                # 尝试匹配关键词（按优先级）
                for keyword in keywords:
                    if keyword in pattern_text_lower:
                        if keyword in matcher.pattern_library.probability_rules:
                            probability_score = matcher.pattern_library.probability_rules[keyword].get('probability')
                            print(f"      [DEBUG] {symbol} {timeframe}: 通过关键词'{keyword}'匹配到概率 {probability_score}%", file=sys.stderr)
                            break
                
                # 如果还没找到，尝试从完整描述中匹配
                if probability_score is None and 'full_pattern_description' in locals():
                    full_text_lower = full_pattern_description.lower() if full_pattern_description else ''
                    for keyword in keywords:
                        if keyword in full_text_lower:
                            if keyword in matcher.pattern_library.probability_rules:
                                probability_score = matcher.pattern_library.probability_rules[keyword].get('probability')
                                print(f"      [DEBUG] {symbol} {timeframe}: 从完整描述中通过关键词'{keyword}'匹配到概率 {probability_score}%", file=sys.stderr)
                                break
        
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
            'probability_score': probability_score,  # 新增：概率分数
            'vision_score': None,  # 不使用视觉分析
            'vision_result': None,
            'final_score': best_match.final_score,
            'is_common_pattern': best_match.pattern_id in common_extractor.get_common_pattern_ids(),
            'trading_params': trading_params,
            'all_sources': best_match.all_sources or [best_match.source],
            # 新增：时间周期风险信息
            'stop_loss_distance_pct': stop_loss_distance_pct,
            'entry_probability': entry_probability_info.get('probability', 1.0),
            'position_size_pct': position_info.get('position_size_pct', 0.1),
            'risk_amount': position_info.get('risk_amount', 0.0),
            'timeframe_params': {
                'min_stop': timeframe_params.min_stop_distance_pct,
                'max_stop': timeframe_params.max_stop_distance_pct,
                'max_delay_hours': timeframe_params.max_acceptable_delay_hours
            }
        }
        
        # 调试：打印概率匹配结果
        print(f"      [DEBUG] {symbol} {timeframe}: pattern_name='{pattern_name}', full_desc='{full_pattern_description}', probability_score={probability_score}", file=sys.stderr)
        if probability_score is not None:
            print(f"      [DEBUG] {symbol} {timeframe}: ✓ 匹配到概率 {probability_score}%", file=sys.stderr)
        else:
            print(f"      [DEBUG] {symbol} {timeframe}: ✗ 未匹配到概率", file=sys.stderr)
        
        # 概率过滤：如果概率太低，添加警告
        if probability_score is not None and probability_score < 50:
            if 'validation_warnings' not in signal:
                signal['validation_warnings'] = []
            signal['validation_warnings'].append(
                f"低概率信号：概率仅{probability_score}%，建议谨慎"
            )
        
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
    print("纯模式匹配交易计划生成器 - Top 10币种测试")
    print("=" * 80)
    print()
    print("注意: 此版本不使用视觉分析，仅使用算法模式匹配")
    print("测试范围: 10个币种 × 2个时间框架 = 20个信号")
    print("预计成本: $0.00 (无API调用)")
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
    risk_calculator = TimeframeRiskCalculator()
    
    print("   [OK] 所有组件初始化完成（无视觉分析器）")
    print()
    
    # 3. 生成交易计划
    print("3. 生成交易计划...")
    all_plans = []
    
    for i, coin in enumerate(coins, 1):
        symbol = coin['symbol']
        print(f"   [{i}/{len(coins)}] {symbol}...", end=' ', flush=True)
        
        # 5分钟信号
        plan_5m = await generate_coin_plan_pattern_only(
            symbol, '5m', matcher, common_extractor, brooks_extractor, risk_calculator
        )
        
        # 15分钟信号
        plan_15m = await generate_coin_plan_pattern_only(
            symbol, '15m', matcher, common_extractor, brooks_extractor, risk_calculator
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
    output_file = output_dir / f"top10_pattern_only_{timestamp}.md"
    
    output = []
    output.append("# Top 10币种纯模式匹配交易计划")
    output.append("")
    output.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"**数据源**: Gemini Flash + Cursor AI + Brooks规则")
    output.append(f"**匹配方式**: 纯算法模式匹配（无视觉分析）")
    output.append(f"**共同模式**: {len(common_patterns)}个")
    output.append(f"**成本**: $0.00 (无API调用)")
    output.append("")
    
    # 交易计划
    for plan_data in all_plans:
        coin = plan_data['coin']
        plan_5m = plan_data['plan_5m']
        plan_15m = plan_data['plan_15m']
        
        # 对于小价格币种，使用更多小数位显示
        coin_price = coin['price']
        is_small_coin = coin_price < 1.0
        price_format = ",.4f" if is_small_coin else ",.2f"
        
        output.append(f"## {coin['symbol']} (${coin_price:{price_format}})")
        output.append("")
        
        if plan_5m:
            signal = plan_5m['signal']
            entry_price = signal['entry_price']
            # 根据价格范围动态调整小数位
            if entry_price < 0.01:
                signal_price_format = ",.6f"  # PEPE等极低价格币种
            elif entry_price < 0.1:
                signal_price_format = ",.5f"
            elif entry_price < 1.0:
                signal_price_format = ",.4f"  # DOGE等小价格币种
            else:
                signal_price_format = ",.2f"  # 正常价格币种
            
            output.append("### 5分钟信号")
            output.append("")
            output.append(f"- **模式**: {signal['pattern_name']} ({signal['pattern_type']})")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${entry_price:{signal_price_format}}")
            output.append(f"- **止损**: ${signal['stop_loss']:{signal_price_format}}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:{signal_price_format}}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:{signal_price_format}}")
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            output.append(f"- **算法匹配**: {signal['algorithm_confidence']:.2%}")
            if signal.get('probability_score') is not None:
                prob = signal['probability_score']
                prob_level = "高" if prob >= 70 else "中" if prob >= 50 else "低"
                output.append(f"- **Brooks概率**: {prob}% ({prob_level}概率)")
            
            # 显示风险信息
            if signal.get('stop_loss_distance_pct'):
                output.append(f"- **止损距离**: {signal['stop_loss_distance_pct']*100:.2f}%")
            if signal.get('position_size_pct'):
                output.append(f"- **建议仓位**: {signal['position_size_pct']*100:.1f}% (风险: ${signal.get('risk_amount', 0):.2f})")
            if signal.get('entry_probability') and signal.get('entry_probability') < 0.8:
                output.append(f"- ⚠️ **入场概率**: {signal['entry_probability']*100:.0f}% (可能需等待)")
            
            if not signal.get('is_valid', True):
                output.append(f"- ⚠️ **验证错误**: {', '.join(signal.get('validation_errors', []))}")
            
            output.append("")
        
        if plan_15m:
            signal = plan_15m['signal']
            entry_price = signal['entry_price']
            # 根据价格范围动态调整小数位
            if entry_price < 0.01:
                signal_price_format = ",.6f"  # PEPE等极低价格币种
            elif entry_price < 0.1:
                signal_price_format = ",.5f"
            elif entry_price < 1.0:
                signal_price_format = ",.4f"  # DOGE等小价格币种
            else:
                signal_price_format = ",.2f"  # 正常价格币种
            
            output.append("### 15分钟信号")
            output.append("")
            output.append(f"- **模式**: {signal['pattern_name']} ({signal['pattern_type']})")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${entry_price:{signal_price_format}}")
            output.append(f"- **止损**: ${signal['stop_loss']:{signal_price_format}}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:{signal_price_format}}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:{signal_price_format}}")
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            output.append(f"- **算法匹配**: {signal['algorithm_confidence']:.2%}")
            if signal.get('probability_score') is not None:
                prob = signal['probability_score']
                prob_level = "高" if prob >= 70 else "中" if prob >= 50 else "低"
                output.append(f"- **Brooks概率**: {prob}% ({prob_level}概率)")
            
            # 显示风险信息
            if signal.get('stop_loss_distance_pct'):
                output.append(f"- **止损距离**: {signal['stop_loss_distance_pct']*100:.2f}%")
            if signal.get('position_size_pct'):
                output.append(f"- **建议仓位**: {signal['position_size_pct']*100:.1f}% (风险: ${signal.get('risk_amount', 0):.2f})")
            if signal.get('entry_probability') and signal.get('entry_probability') < 0.8:
                output.append(f"- ⚠️ **入场概率**: {signal['entry_probability']*100:.0f}% (可能需等待)")
            
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
    print(f"总成本: $0.00 (无API调用)")
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
