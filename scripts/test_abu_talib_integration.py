#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试ABU TA-Lib集成功能

验证TA-Lib增强版匹配器是否正常工作
"""
from __future__ import annotations
import sys
from pathlib import Path

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

print("=" * 80)
print("ABU TA-Lib集成测试")
print("=" * 80)
print()

# 1. 测试TA-Lib增强版匹配器导入
print("1. 测试TA-Lib增强版匹配器导入...")
try:
    from abu.gemini_pattern_matcher_talib_enhanced import TalibEnhancedGeminiPatternMatcher
    print("   ✓ TalibEnhancedGeminiPatternMatcher 导入成功")
except ImportError as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

# 2. 测试TA-Lib可用性
print("\n2. 测试TA-Lib可用性...")
try:
    import talib
    print(f"   ✓ TA-Lib已安装，版本: {talib.__version__ if hasattr(talib, '__version__') else '未知'}")
except ImportError:
    print("   ⚠ TA-Lib未安装，将使用基础功能")

# 3. 测试创建匹配器
print("\n3. 测试创建TA-Lib增强版匹配器...")
try:
    matcher = TalibEnhancedGeminiPatternMatcher(
        use_talib=True,
        talib_validation=True,
        use_ml=False,
        use_dl=False
    )
    print(f"   ✓ 匹配器创建成功")
    print(f"   ✓ TA-Lib启用状态: {matcher.use_talib}")
    print(f"   ✓ TA-Lib验证启用: {matcher.talib_validation}")
    print(f"   ✓ 模式库数量: {len(matcher.pattern_library)}")
except Exception as e:
    print(f"   ✗ 创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 测试特征提取（使用模拟数据）
print("\n4. 测试特征提取（使用模拟K线数据）...")
try:
    import random
    from datetime import datetime, timedelta
    
    # 生成模拟K线数据
    base_price = 100.0
    klines_15m = []
    for i in range(100):
        price_change = random.uniform(-0.02, 0.02)
        open_price = base_price * (1 + price_change)
        close_price = open_price * (1 + random.uniform(-0.01, 0.01))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        
        klines_15m.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': random.uniform(1000, 10000),
            'timestamp': int((datetime.now() - timedelta(minutes=100-i)).timestamp() * 1000)
        })
        base_price = close_price
    
    klines_dict = {'15m': klines_15m}
    
    # 提取特征
    features = matcher.extract_realtime_features(klines_dict)
    
    if features:
        print("   ✓ 特征提取成功")
        
        # 检查TA-Lib特征
        kline_features = features.get('price_action_behavior', {}).get('kline_features', [])
        talib_patterns = features.get('price_action_behavior', {}).get('talib_patterns', [])
        indicators = features.get('market_conditions', {}).get('technical_indicators', {})
        
        print(f"   ✓ K线特征数量: {len(kline_features)}")
        if talib_patterns:
            print(f"   ✓ TA-Lib检测到的形态: {len(talib_patterns)}")
        if indicators:
            print(f"   ✓ 技术指标: {list(indicators.keys())}")
    else:
        print("   ⚠ 特征提取返回空结果")
        
except Exception as e:
    print(f"   ✗ 特征提取失败: {e}")
    import traceback
    traceback.print_exc()

# 5. 测试信号验证（如果有模式库）
print("\n5. 测试信号验证...")
if matcher.pattern_library:
    try:
        # 生成一个测试信号
        test_signal = {
            'direction': 'long',
            'entry_price': klines_15m[-1]['close'],
            'stop_loss': klines_15m[-1]['close'] * 0.98,
            'take_profit_1': klines_15m[-1]['close'] * 1.02
        }
        
        # 验证信号
        validation_result = matcher.validate_signal_with_talib(test_signal, klines_15m)
        
        print(f"   ✓ 信号验证完成")
        print(f"   ✓ 验证结果: {'通过' if validation_result.get('validated') else '未通过'}")
        print(f"   ✓ 置信度: {validation_result.get('confidence', 0.5):.2%}")
        
        reasons = validation_result.get('validation_reasons', [])
        if reasons:
            print(f"   ✓ 验证原因:")
            for reason in reasons[:3]:  # 只显示前3个
                print(f"      - {reason}")
    except Exception as e:
        print(f"   ✗ 信号验证失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("   ⚠ 模式库为空，跳过信号验证测试")

print("\n" + "=" * 80)
print("测试完成！")
print("=" * 80)
print("\n如果所有测试通过，说明TA-Lib集成成功。")
print("现在可以在ABU信号扫描器中使用TA-Lib增强功能。")



