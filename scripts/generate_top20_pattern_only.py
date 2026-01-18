#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Top 20币种交易计划生成器（纯模式匹配）

使用模式匹配生成Top 20市值币种的交易计划，不使用视觉分析。
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
from abu.unified_pattern_library import UnifiedPatternLibrary
from abu.common_pattern_extractor import CommonPatternExtractor
from abu.brooks_parameter_extractor import BrooksParameterExtractor, DEFAULT_PARAMETERS
import requests

# 定义必要的函数
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
    
    volatility = (max(highs) - min(lows)) / closes[-1] if closes else 0
    
    return {
        'trend': price_trend,
        'trend_strength': trend_strength,
        'volatility': volatility,
        'market_conditions': {
            'trend_strength': 'strong' if trend_strength > 0.02 else 'weak',
            'volatility': 'high' if volatility > 0.01 else 'low',
        }
    }

def validate_trading_plan(signal: Dict) -> tuple:
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

# 默认参数
DEFAULT_PARAMETERS = type('obj', (object,), {
    'stop_loss_pct': None,
    'take_profit_pct': None,
    'risk_reward_ratio': None,
    'position_size_pct': None
})()


async def get_top_coins(limit: int = 20) -> List[tuple]:
    """获取Top N币种"""
    try:
        import requests
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': False
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [(coin['symbol'].upper(), coin['current_price']) for coin in data]
    except Exception as e:
        print(f"[WARN] 获取Top币种失败: {e}", file=sys.stderr)
        # 返回默认列表
        return [
            ('BTC', 95000), ('ETH', 3500), ('SOL', 150), ('XRP', 0.6),
            ('DOGE', 0.15), ('BNB', 600), ('ADA', 0.5), ('AVAX', 40),
            ('TRX', 0.1), ('LINK', 20), ('DOT', 7), ('MATIC', 1),
            ('SHIB', 0.00001), ('DAI', 1), ('UNI', 10), ('LTC', 100),
            ('BCH', 300), ('ATOM', 12), ('ETC', 25), ('XLM', 0.12)
        ][:limit]
    return []


async def generate_coin_plan_pattern_only(
    symbol: str,
    timeframe: str,
    matcher: EnhancedHybridMatcher,
    common_extractor: CommonPatternExtractor,
    brooks_extractor: BrooksParameterExtractor
) -> Optional[Dict]:
    """生成单个币种的交易计划（纯模式匹配）"""
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
        trading_params = type('obj', (object,), {
            'stop_loss_pct': None,
            'take_profit_pct': None,
            'risk_reward_ratio': None,
            'position_size_pct': None
        })()
        if best_match.source == 'brooks_rule' and best_match.pattern:
            raw_data = best_match.pattern.raw_data if hasattr(best_match.pattern, 'raw_data') else {}
            if raw_data:
                trading_params = brooks_extractor.extract_parameters(
                    raw_data.get('trading_rules', {}),
                    raw_data.get('content_text', ''),
                    raw_data.get('key_concepts', [])
                )
        
        # 生成信号（仅使用算法匹配结果，符合Brooks顺势原则）
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
        
        # 计算止损和止盈（符合Brooks规则）
        entry_price = current_price
        stop_loss_pct = trading_params.stop_loss_pct if trading_params.stop_loss_pct else 0.02
        take_profit_pct = trading_params.take_profit_pct if trading_params.take_profit_pct else (stop_loss_pct * 2.0)
        
        # 根据时间框架确定最小止损距离
        if '5m' in timeframe:
            min_stop_distance_pct = 0.015  # 5分钟至少1.5%
        elif '15m' in timeframe:
            min_stop_distance_pct = 0.02  # 15分钟至少2%
        else:
            min_stop_distance_pct = 0.01  # 其他至少1%
        
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
                # 至少0.5%的绝对距离，但不超过最小距离要求
                min_absolute_distance = entry_price * 0.005  # 0.5%
                min_stop_absolute = entry_price - min_absolute_distance
                stop_loss = min(stop_loss, min_stop_absolute)
            
            # 再次确保止损低于入场价（至少1%或最小距离）
            final_min_stop = entry_price * (1 - max(min_stop_distance_pct, 0.01))
            stop_loss = min(stop_loss, final_min_stop)
            
            # 最终验证：止损必须明显低于入场价
            if stop_loss >= entry_price * 0.999:  # 如果止损太接近入场价（误差<0.1%）
                # 强制设置止损为入场价的(1 - min_stop_distance_pct)
                stop_loss = entry_price * (1 - min_stop_distance_pct)
            
            # 计算盈亏比，确保至少2:1
            risk = entry_price - stop_loss
            if risk <= 0 or risk < entry_price * 0.001:  # 风险太小（<0.1%）
                # 如果风险计算失败，使用最小距离重新计算
                stop_loss = entry_price * (1 - min_stop_distance_pct)
                risk = entry_price - stop_loss
            
            if risk > 0:
                min_reward = risk * 2.0  # 至少2:1
                take_profit_1 = entry_price + min_reward
                take_profit_2 = entry_price + risk * 3.0  # 理想3:1
            else:
                # 如果风险计算仍然失败，使用默认百分比
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
                # 至少0.5%的绝对距离
                min_absolute_distance = entry_price * 0.005  # 0.5%
                max_stop_absolute = entry_price + min_absolute_distance
                stop_loss = max(stop_loss, max_stop_absolute)
            
            # 再次确保止损高于入场价（至少1%或最小距离）
            final_max_stop = entry_price * (1 + max(min_stop_distance_pct, 0.01))
            stop_loss = max(stop_loss, final_max_stop)
            
            # 最终验证：止损必须明显高于入场价
            if stop_loss <= entry_price * 1.001:  # 如果止损太接近入场价（误差<0.1%）
                # 强制设置止损为入场价的(1 + min_stop_distance_pct)
                stop_loss = entry_price * (1 + min_stop_distance_pct)
            
            # 计算盈亏比，确保至少2:1
            risk = stop_loss - entry_price
            if risk <= 0 or risk < entry_price * 0.001:  # 风险太小（<0.1%）
                # 如果风险计算失败，使用最小距离重新计算
                stop_loss = entry_price * (1 + min_stop_distance_pct)
                risk = stop_loss - entry_price
            
            if risk > 0:
                min_reward = risk * 2.0  # 至少2:1
                take_profit_1 = entry_price - min_reward
                take_profit_2 = entry_price - risk * 3.0  # 理想3:1
            else:
                # 如果风险计算仍然失败，使用默认百分比
                take_profit_1 = entry_price * (1 - take_profit_pct)
                take_profit_2 = entry_price * (1 - take_profit_pct * 1.5)
        
        # 使用算法匹配置信度
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
            'vision_score': None,  # 不使用视觉分析
            'vision_result': None,
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
    print("Top 20币种交易计划生成器 - 纯模式匹配")
    print("=" * 80)
    print()
    print("注意: 此版本不使用视觉分析，仅使用算法模式匹配")
    print("测试范围: 20个币种 × 2个时间框架 = 40个信号")
    print("预计成本: $0.00 (无API调用)")
    print()
    
    # 1. 获取Top 20币种
    print("1. 获取Top 20币种...")
    coins = await get_top_coins(20)
    print(f"   找到 {len(coins)} 个币种: {', '.join([c[0] for c in coins])}")
    print()
    
    # 2. 初始化组件
    print("2. 初始化组件...")
    pattern_library = UnifiedPatternLibrary()
    pattern_library.load_all_patterns()
    
    matcher = EnhancedHybridMatcher(pattern_library)
    common_extractor = CommonPatternExtractor(pattern_library)
    brooks_extractor = BrooksParameterExtractor()
    
    print("   [OK] 所有组件初始化完成（无视觉分析器）")
    print()
    
    # 3. 生成交易计划
    print("3. 生成交易计划...")
    all_plans = []
    timeframes = ['5m', '15m']
    
    for i, (symbol, price) in enumerate(coins, 1):
        print(f"   [{i}/{len(coins)}] {symbol}...", end=' ', flush=True)
        coin_plans = {}
        
        for timeframe in timeframes:
            plan = await generate_coin_plan_pattern_only(
                symbol, timeframe, matcher, common_extractor, brooks_extractor
            )
            if plan:
                coin_plans[timeframe] = plan
        
        if coin_plans:
            all_plans.append({
                'symbol': symbol,
                'price': price,
                'plans': coin_plans
            })
            print(f"✓ ({len(coin_plans)}/{len(timeframes)} 信号)")
        else:
            print("✗")
    
    print()
    
    # 4. 生成报告
    print("4. 生成报告...")
    output_dir = ROOT / 'outputs' / 'trading_plans'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"top20_pattern_only_{timestamp}.md"
    
    output = []
    output.append("# Top 20币种交易计划（纯模式匹配）")
    output.append("")
    output.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"**币种数量**: {len(all_plans)}")
    output.append(f"**总信号数**: {sum(len(p['plans']) for p in all_plans)}")
    output.append("")
    output.append("---")
    output.append("")
    
    for coin_data in all_plans:
        symbol = coin_data['symbol']
        price = coin_data['price']
        plans = coin_data['plans']
        
        output.append(f"## {symbol} (${price:,.2f})")
        output.append("")
        
        plan_5m = plans.get('5m')
        plan_15m = plans.get('15m')
        
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
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            output.append(f"- **算法匹配**: {signal['algorithm_confidence']:.2%}")
            
            # Brooks验证结果
            if signal.get('brooks_validation'):
                bv = signal['brooks_validation']
                if not bv['is_valid']:
                    output.append(f"- 🚨 **Brooks验证失败** (分数: {bv['score']:.1f}/100)")
                    if bv['issues']:
                        output.append(f"  - 问题: {'; '.join(bv['issues'][:3])}")
                    if bv['warnings']:
                        output.append(f"  - 警告: {'; '.join(bv['warnings'][:2])}")
                elif bv['warnings']:
                    output.append(f"- ⚠️ **Brooks警告**: {'; '.join(bv['warnings'][:2])}")
                else:
                    output.append(f"- ✅ **Brooks验证通过** (分数: {bv['score']:.1f}/100)")
            
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
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            output.append(f"- **算法匹配**: {signal['algorithm_confidence']:.2%}")
            
            # Brooks验证结果
            if signal.get('brooks_validation'):
                bv = signal['brooks_validation']
                if not bv['is_valid']:
                    output.append(f"- 🚨 **Brooks验证失败** (分数: {bv['score']:.1f}/100)")
                    if bv['issues']:
                        output.append(f"  - 问题: {'; '.join(bv['issues'][:3])}")
                    if bv['warnings']:
                        output.append(f"  - 警告: {'; '.join(bv['warnings'][:2])}")
                elif bv['warnings']:
                    output.append(f"- ⚠️ **Brooks警告**: {'; '.join(bv['warnings'][:2])}")
                else:
                    output.append(f"- ✅ **Brooks验证通过** (分数: {bv['score']:.1f}/100)")
            
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
    print(f"总信号数: {sum(len(p['plans']) for p in all_plans)}")
    print(f"总成本: $0.00 (无API调用)")
    print()
    print(f"报告文件: {output_file}")
    print()
    
    return output_file


if __name__ == '__main__':
    from typing import List, Dict, Optional
    result = asyncio.run(main())
