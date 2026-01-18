#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TA-Lib集成测试脚本
测试增强版图表形态识别器的功能
"""

import sys
from pathlib import Path

# 添加src目录到路径
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def test_talib_installation():
    """测试TA-Lib是否已正确安装"""
    print("=" * 80)
    print("测试TA-Lib安装")
    print("=" * 80)
    print()
    
    try:
        import talib
        print("✓ TA-Lib已成功导入")
        print(f"  版本信息: {talib.__version__ if hasattr(talib, '__version__') else '未知'}")
        print()
        
        # 测试基本功能
        import numpy as np
        closes = np.array([100, 102, 101, 103, 105, 104, 106], dtype=np.float64)
        rsi = talib.RSI(closes, timeperiod=5)
        print(f"✓ RSI计算测试成功: {rsi[-1]:.2f}")
        print()
        
        return True
    except ImportError as e:
        print("✗ TA-Lib未安装或安装失败")
        print(f"  错误: {e}")
        print()
        print("安装说明:")
        print("  Windows: 下载TA-Lib C库后 pip install TA-Lib")
        print("  macOS: brew install ta-lib && pip install TA-Lib")
        print("  Linux: sudo apt-get install libta-lib0-dev && pip install TA-Lib")
        print()
        return False
    except Exception as e:
        print(f"✗ TA-Lib测试失败: {e}")
        print()
        return False


def test_enhanced_detector():
    """测试增强版检测器"""
    print("=" * 80)
    print("测试增强版图表形态识别器")
    print("=" * 80)
    print()
    
    try:
        from chart_patterns_detector_enhanced import EnhancedChartPatternsDetector
        import numpy as np
        
        # 创建检测器
        detector = EnhancedChartPatternsDetector(use_talib=True)
        print("✓ 检测器创建成功")
        print()
        
        # 生成测试数据（模拟一个看涨吞没形态）
        print("生成测试K线数据...")
        klines = []
        base_price = 50000.0
        
        # 前几根K线：下跌趋势
        for i in range(5):
            price_change = -100 * (i + 1)
            klines.append({
                'open': base_price + price_change,
                'high': base_price + price_change + 50,
                'low': base_price + price_change - 50,
                'close': base_price + price_change - 30,
                'volume': 1000 + i * 100,
                'timestamp': i
            })
            base_price = klines[-1]['close']
        
        # 吞没形态：大阳线吞没前一根阴线
        prev_close = klines[-1]['close']
        klines.append({
            'open': prev_close - 20,  # 低开
            'high': prev_close + 100,  # 大幅上涨
            'low': prev_close - 30,
            'close': prev_close + 80,  # 收盘高于前一根的开盘
            'volume': 5000,
            'timestamp': 5
        })
        
        # 继续生成一些K线
        base_price = klines[-1]['close']
        for i in range(10):
            price_change = np.random.randn() * 50
            klines.append({
                'open': base_price + price_change,
                'high': base_price + price_change + abs(np.random.randn() * 30),
                'low': base_price + price_change - abs(np.random.randn() * 30),
                'close': base_price + price_change + np.random.randn() * 20,
                'volume': 2000 + np.random.uniform(-500, 500),
                'timestamp': 6 + i
            })
            base_price = klines[-1]['close']
        
        print(f"✓ 生成了 {len(klines)} 根K线")
        print()
        
        # 检测形态
        print("检测形态...")
        result = detector.detect_all_patterns_enhanced(klines)
        print("✓ 检测完成")
        print()
        
        # 显示结果
        print("=" * 80)
        print("检测结果")
        print("=" * 80)
        print()
        
        # K线形态
        candlestick = result.get('candlestick_patterns', {})
        total_candlestick = candlestick.get('total_detected', 0)
        print(f"K线形态: {total_candlestick} 个")
        if total_candlestick > 0:
            patterns = candlestick.get('patterns', [])
            for pattern in patterns[-5:]:  # 显示最后5个
                print(f"  - {pattern['name']} ({pattern['direction']}) at index {pattern['index']}")
        else:
            print("  (未检测到K线形态)")
        print()
        
        # 图表形态
        chart = result.get('chart_patterns', {})
        chart_patterns = chart.get('patterns', [])
        print(f"图表形态: {len(chart_patterns)} 个")
        if chart_patterns:
            for pattern in chart_patterns[:5]:  # 显示前5个
                print(f"  - {pattern}")
        else:
            print("  (未检测到图表形态)")
        print()
        
        # 技术指标
        indicators = result.get('technical_indicators', {})
        if indicators:
            print("技术指标:")
            if 'rsi' in indicators and indicators['rsi'].get('value'):
                rsi_val = indicators['rsi']['value']
                status = "超买" if rsi_val > 70 else "超卖" if rsi_val < 30 else "正常"
                print(f"  RSI(14): {rsi_val:.2f} ({status})")
            
            if 'macd' in indicators:
                macd = indicators['macd']
                if macd.get('macd'):
                    print(f"  MACD: {macd['macd']:.2f}, Signal: {macd['signal']:.2f}, Hist: {macd['histogram']:.2f}")
            
            if 'bollinger_bands' in indicators:
                bb = indicators['bollinger_bands']
                if bb.get('upper'):
                    print(f"  布林带: Upper={bb['upper']:.2f}, Middle={bb['middle']:.2f}, Lower={bb['lower']:.2f}")
            
            if 'atr' in indicators and indicators['atr'].get('value'):
                print(f"  ATR(14): {indicators['atr']['value']:.2f}")
        else:
            print("  (未计算技术指标)")
        print()
        
        # 摘要
        summary = result.get('summary', {})
        print(f"综合置信度: {summary.get('confidence', 0):.1f}%")
        print()
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        print("  请确保 chart_patterns_detector_enhanced.py 在 src/ 目录下")
        print()
        return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        print()
        return False


def main():
    """主函数"""
    print()
    print("TA-Lib集成测试")
    print()
    
    # 测试1: TA-Lib安装
    talib_ok = test_talib_installation()
    
    if not talib_ok:
        print("⚠ TA-Lib未安装，跳过功能测试")
        print()
        return
    
    # 测试2: 增强版检测器
    detector_ok = test_enhanced_detector()
    
    # 总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print()
    print(f"TA-Lib安装: {'✓ 通过' if talib_ok else '✗ 失败'}")
    print(f"检测器功能: {'✓ 通过' if detector_ok else '✗ 失败'}")
    print()
    
    if talib_ok and detector_ok:
        print("✓ 所有测试通过！TA-Lib已成功集成。")
    else:
        print("⚠ 部分测试失败，请检查错误信息。")
    print()


if __name__ == '__main__':
    main()



