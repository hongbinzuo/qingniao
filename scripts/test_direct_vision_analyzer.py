#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试直接视觉分析器（方案1）
只测试1-2个币种，验证功能
"""

import sys
import asyncio
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from abu.unified_pattern_library import UnifiedPatternLibrary
    from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
    from abu.common_pattern_extractor import CommonPatternExtractor
    from abu.brooks_parameter_extractor import BrooksParameterExtractor, DEFAULT_PARAMETERS
    from abu.chart_renderer import ChartRenderer
    from abu.direct_vision_analyzer import DirectVisionAnalyzer
    
    # 特征提取函数
    try:
        from abu.feature_extractor import extract_features_from_klines
    except ImportError:
        try:
            from src.abu.feature_extractor import extract_features_from_klines
        except ImportError:
            # 如果找不到，使用简化版本
            def extract_features_from_klines(klines, timeframe):
                """简化的特征提取"""
                if not klines or len(klines) < 50:
                    return None
                
                closes = [k['close'] for k in klines]
                highs = [k['high'] for k in klines]
                lows = [k['low'] for k in klines]
                volumes = [k.get('volume', 0) for k in klines]
                
                return {
                    'timeframe': timeframe,
                    'price_features': {
                        'current_price': closes[-1],
                        'price_change_24h': (closes[-1] - closes[0]) / closes[0] if len(closes) > 0 else 0,
                        'high_24h': max(highs) if highs else closes[-1],
                        'low_24h': min(lows) if lows else closes[-1],
                    },
                    'kline_features': {
                        'recent_trend': 'up' if closes[-1] > closes[-20] else 'down' if closes[-1] < closes[-20] else 'sideways',
                        'volatility': (max(highs[-20:]) - min(lows[-20:])) / closes[-1] if len(highs) >= 20 else 0,
                    },
                    'volume_features': {
                        'avg_volume': sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0,
                    }
                }
    
    # 获取K线数据的函数
    try:
        from gateio_api import get_kline_gateio
    except ImportError:
        try:
            from src.gateio_api import get_kline_gateio
        except ImportError:
            # 如果找不到，使用requests直接调用
            import requests
            def get_kline_gateio(symbol, timeframe, limit=200):
                """获取Gate.io K线数据"""
                url = "https://api.gateio.ws/api/v4/spot/candlesticks"
                params = {
                    'currency_pair': f'{symbol}_USDT',
                    'interval': timeframe,
                    'limit': limit
                }
                try:
                    response = requests.get(url, params=params, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        klines = []
                        for item in data:
                            klines.append({
                                'timestamp': int(item[0]),
                                'open': float(item[2]),
                                'high': float(item[3]),
                                'low': float(item[4]),
                                'close': float(item[5]),
                                'volume': float(item[6])
                            })
                        return klines
                except Exception:
                    pass
                return None
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)


async def test_single_coin(symbol: str, timeframe: str):
    """测试单个币种"""
    print(f"\n{'='*80}")
    print(f"测试: {symbol} {timeframe}")
    print(f"{'='*80}\n")
    
    # 1. 初始化组件
    print("1. 初始化组件...")
    lib = UnifiedPatternLibrary('abu')
    lib.load_all_patterns()
    print(f"   [OK] 模式库: {len(lib.patterns)} 个模式")
    
    matcher = EnhancedHybridMatcher(
        pattern_library=lib,
        top_k=10,
        min_confidence=0.3
    )
    print("   [OK] 匹配器初始化完成")
    
    chart_renderer = ChartRenderer()
    print("   [OK] 图表渲染器初始化完成")
    
    try:
        direct_vision_analyzer = DirectVisionAnalyzer()
        print("   [OK] 直接视觉分析器初始化完成")
    except Exception as e:
        print(f"   [ERROR] 直接视觉分析器初始化失败: {e}")
        return None
    
    # 2. 获取K线数据
    print(f"\n2. 获取K线数据 ({symbol} {timeframe})...")
    klines = get_kline_gateio(symbol, timeframe, limit=200)
    if not klines or len(klines) < 50:
        print(f"   [ERROR] K线数据不足")
        return None
    
    current_price = klines[-1]['close']
    print(f"   [OK] 获取到 {len(klines)} 根K线，当前价格: ${current_price:,.2f}")
    
    # 3. 提取特征并匹配
    print(f"\n3. 算法匹配...")
    query_features = extract_features_from_klines(klines, timeframe)
    if not query_features:
        print(f"   [ERROR] 特征提取失败")
        return None
    
    klines_dict = {timeframe: klines}
    matches = await matcher.async_match(
        query_features=query_features,
        klines_dict=klines_dict,
        symbol=f"{symbol}_USDT"
    )
    
    if not matches:
        print(f"   [WARN] 未找到匹配模式")
        return None
    
    print(f"   [OK] 找到 {len(matches)} 个匹配")
    print(f"   最佳匹配: {matches[0].pattern_name} (置信度: {matches[0].combined_confidence:.2%})")
    
    # 4. 渲染图表
    print(f"\n4. 渲染图表...")
    output_dir = ROOT / 'outputs' / 'charts'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    chart_image_path = output_dir / f"{symbol}_{timeframe}_{int(time.time())}.png"
    
    chart_renderer.render_klines_to_image(
        klines,
        output_path=chart_image_path,
        title=f"{symbol} {timeframe} Chart"
    )
    
    if not chart_image_path.exists():
        print(f"   [ERROR] 图表渲染失败")
        return None
    
    print(f"   [OK] 图表已保存: {chart_image_path}")
    
    # 5. 视觉分析（方案1）
    print(f"\n5. 视觉分析（方案1：直接分析）...")
    
    # 准备Top 3候选
    pattern_candidates = []
    for match in matches[:3]:
        pattern_candidates.append({
            'pattern_name': match.pattern_name,
            'pattern_type': match.pattern_type,
            'source': match.source,
            'confidence': match.combined_confidence
        })
    
    print(f"   准备分析 {len(pattern_candidates)} 个候选模式...")
    
    try:
        vision_result = direct_vision_analyzer.analyze_chart_directly(
            chart_image_path,
            pattern_candidates=pattern_candidates,
            symbol=symbol,
            timeframe=timeframe
        )
        
        print(f"\n   [OK] 视觉分析完成")
        print(f"   识别模式: {vision_result.pattern_name} ({vision_result.pattern_type})")
        print(f"   方向: {vision_result.direction}")
        print(f"   置信度: {vision_result.confidence:.2%}")
        print(f"   关键特征: {', '.join(vision_result.key_features[:3])}")
        print(f"   估算成本: ${vision_result.estimated_cost:.4f}")
        
        # 6. 成本统计
        print(f"\n6. 成本统计...")
        cost_summary = direct_vision_analyzer.get_cost_summary()
        print(f"   总调用次数: {cost_summary['total_calls']}")
        print(f"   总成本: ${cost_summary['total_cost_usd']:.4f}")
        print(f"   平均成本/次: ${cost_summary['avg_cost_per_call']:.4f}")
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'algorithm_match': matches[0].pattern_name,
            'algorithm_confidence': matches[0].combined_confidence,
            'vision_match': vision_result.pattern_name,
            'vision_confidence': vision_result.confidence,
            'direction': vision_result.direction,
            'cost': vision_result.estimated_cost
        }
        
    except Exception as e:
        print(f"   [ERROR] 视觉分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主函数"""
    print("="*80)
    print("直接视觉分析器测试（方案1）")
    print("="*80)
    print("\n注意: 此测试会产生API调用费用（约$0.005/次）")
    print("测试范围: 2个币种 × 1个时间框架 = 2次调用")
    print("预计成本: ~$0.01")
    print()
    
    # 测试BTC和ETH
    test_cases = [
        ('BTC', '15m'),
        ('ETH', '15m')
    ]
    
    results = []
    
    for symbol, timeframe in test_cases:
        result = await test_single_coin(symbol, timeframe)
        if result:
            results.append(result)
    
    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}\n")
    
    if results:
        print(f"成功: {len(results)}/{len(test_cases)}")
        print()
        
        total_cost = sum(r['cost'] for r in results)
        print(f"总成本: ${total_cost:.4f}")
        print()
        
        print("结果对比:")
        for r in results:
            print(f"\n{r['symbol']} {r['timeframe']}:")
            print(f"  算法匹配: {r['algorithm_match']} ({r['algorithm_confidence']:.2%})")
            print(f"  视觉分析: {r['vision_match']} ({r['vision_confidence']:.2%})")
            print(f"  方向: {r['direction']}")
            print(f"  成本: ${r['cost']:.4f}")
    else:
        print("❌ 所有测试失败")
    
    print()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
