#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图表形态识别模块（TA-Lib增强版）
集成TA-Lib的100+ K线形态识别，补充现有的图表形态检测

功能：
1. 使用TA-Lib识别K线形态（吞没、十字星、锤子等）
2. 保留现有的图表形态识别（头肩顶、双顶等）
3. 提供技术指标计算（RSI、MACD、布林带等）
4. 综合分析和信号生成
"""

import sys
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 尝试导入TA-Lib
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("警告: TA-Lib未安装，将使用基础功能。安装命令: pip install TA-Lib", file=sys.stderr)

# 导入原有的图表形态识别器
try:
    from chart_patterns_detector import ChartPatternsDetector
except ImportError:
    # 如果无法导入，尝试从src目录导入
    import sys
    from pathlib import Path
    src_path = Path(__file__).parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from chart_patterns_detector import ChartPatternsDetector


class EnhancedChartPatternsDetector(ChartPatternsDetector):
    """增强版图表形态识别器（集成TA-Lib）"""
    
    def __init__(self, min_pattern_length: int = 20, max_pattern_length: int = 200, use_talib: bool = True):
        """
        初始化增强版形态识别器
        
        Args:
            min_pattern_length: 最小形态长度（K线数）
            max_pattern_length: 最大形态长度（K线数）
            use_talib: 是否使用TA-Lib（如果可用）
        """
        super().__init__(min_pattern_length, max_pattern_length)
        self.use_talib = use_talib and TALIB_AVAILABLE
        
        if self.use_talib:
            print("✓ TA-Lib已启用，支持100+ K线形态识别", file=sys.stderr)
        else:
            print("⚠ TA-Lib未启用，仅使用基础形态识别", file=sys.stderr)
    
    def detect_candlestick_patterns(self, klines: List[Dict]) -> Dict:
        """
        使用TA-Lib识别K线形态
        
        Args:
            klines: K线数据列表
            
        Returns:
            {
                'patterns': [...],  # 检测到的K线形态列表
                'pattern_details': {...}  # 形态详细信息
            }
        """
        if not self.use_talib or not klines or len(klines) < 2:
            return {
                'patterns': [],
                'pattern_details': {}
            }
        
        # 转换为numpy数组
        opens = np.array([k['open'] for k in klines], dtype=np.float64)
        highs = np.array([k['high'] for k in klines], dtype=np.float64)
        lows = np.array([k['low'] for k in klines], dtype=np.float64)
        closes = np.array([k['close'] for k in klines], dtype=np.float64)
        
        patterns = []
        pattern_details = {}
        
        # TA-Lib的K线形态识别函数列表（常用形态）
        candlestick_patterns = {
            # 反转形态
            'CDLENGULFING': ('吞没形态', 'reversal'),
            'CDLDOJI': ('十字星', 'reversal'),
            'CDLHAMMER': ('锤子线', 'bullish_reversal'),
            'CDLHANGINGMAN': ('上吊线', 'bearish_reversal'),
            'CDLSHOOTINGSTAR': ('流星线', 'bearish_reversal'),
            'CDLINVERTEDHAMMER': ('倒锤子', 'bullish_reversal'),
            'CDLHARAMI': ('孕线', 'reversal'),
            'CDL3BLACKCROWS': ('三只乌鸦', 'bearish_reversal'),
            'CDL3WHITESOLDIERS': ('三白兵', 'bullish_reversal'),
            'CDLMORNINGSTAR': ('晨星', 'bullish_reversal'),
            'CDLEVENINGSTAR': ('暮星', 'bearish_reversal'),
            'CDL3LINESTRIKE': ('三线打击', 'reversal'),
            'CDLSPINNINGTOP': ('纺锤线', 'indecision'),
            'CDLDRAGONFLYDOJI': ('蜻蜓十字', 'bullish_reversal'),
            'CDLGRAVESTONEDOJI': ('墓碑十字', 'bearish_reversal'),
            'CDLMARUBOZU': ('光头光脚', 'continuation'),
            'CDLPIERCING': ('刺透形态', 'bullish_reversal'),
            'CDLDARKCLOUDCOVER': ('乌云盖顶', 'bearish_reversal'),
            'CDLADVANCEBLOCK': ('上升三法', 'bearish_reversal'),
            'CDLBELTHOLD': ('捉腰带线', 'reversal'),
            'CDLBREAKAWAY': ('脱离形态', 'reversal'),
            'CDLCLOSINGMARUBOZU': ('收盘光头光脚', 'continuation'),
            'CDLCONCEALBABYSWALL': ('藏婴吞没', 'reversal'),
            'CDLCOUNTERATTACK': ('反击线', 'reversal'),
            'CDLDOJISTAR': ('十字星', 'reversal'),
            'CDLGAPSIDESIDEWHITE': ('跳空并列白线', 'continuation'),
            'CDLHIGHWAVE': ('高浪线', 'indecision'),
            'CDLHOMINGPIGEON': ('家鸽', 'bullish_reversal'),
            'CDLIDENTICAL3CROWS': ('相同三乌鸦', 'bearish_reversal'),
            'CDLINNECK': ('颈内线', 'bearish_reversal'),
            'CDLKICKING': ('反冲形态', 'reversal'),
            'CDLKICKINGBYLENGTH': ('长反冲', 'reversal'),
            'CDLLADDERBOTTOM': ('梯底', 'bullish_reversal'),
            'CDLLONGLEGGEDDOJI': ('长腿十字', 'indecision'),
            'CDLLONGLINE': ('长线', 'continuation'),
            'CDLMATHOLD': ('铺垫', 'bullish_reversal'),
            'CDLMORNINGDOJISTAR': ('晨星十字', 'bullish_reversal'),
            'CDLONNECK': ('颈上线', 'bearish_reversal'),
            'CDLRICKSHAWMAN': ('黄包车夫', 'indecision'),
            'CDLRISEFALL3METHODS': ('上升三法', 'bullish_continuation'),
            'CDLSEPARATINGLINES': ('分离线', 'reversal'),
            'CDLSHORTLINE': ('短线', 'indecision'),
            'CDLSTALLEDPATTERN': ('停滞形态', 'bearish_reversal'),
            'CDLSTICKSANDWICH': ('三明治', 'reversal'),
            'CDLTAKURI': ('探水竿', 'bullish_reversal'),
            'CDLTASUKIGAP': ('跳空并列', 'continuation'),
            'CDLTHRUSTING': ('插入', 'bearish_reversal'),
            'CDLTRISTAR': ('三星', 'reversal'),
            'CDLUNIQUE3RIVER': ('独特三河', 'bullish_reversal'),
            'CDLUPSIDEGAP2CROWS': ('向上跳空二乌鸦', 'bearish_reversal'),
            'CDLXSIDEGAP3METHODS': ('跳空三法', 'continuation'),
        }
        
        # 检测每个形态
        for func_name, (pattern_name, pattern_type) in candlestick_patterns.items():
            try:
                func = getattr(talib, func_name)
                result = func(opens, highs, lows, closes)
                
                # 查找非零值（表示检测到形态）
                detected_indices = np.where(result != 0)[0]
                
                if len(detected_indices) > 0:
                    # 获取最新的检测结果
                    latest_index = detected_indices[-1]
                    signal_value = result[latest_index]
                    
                    # signal_value > 0 表示看涨，< 0 表示看跌
                    direction = 'bullish' if signal_value > 0 else 'bearish'
                    
                    pattern_info = {
                        'name': pattern_name,
                        'type': pattern_type,
                        'direction': direction,
                        'index': int(latest_index),
                        'signal_strength': abs(signal_value),
                        'price': float(closes[latest_index]),
                        'timestamp': klines[latest_index].get('timestamp') if 'timestamp' in klines[latest_index] else None
                    }
                    
                    patterns.append(pattern_info)
                    pattern_details[func_name] = pattern_info
                    
            except AttributeError:
                # 如果函数不存在，跳过
                continue
            except Exception as e:
                # 其他错误，记录但继续
                print(f"  检测{pattern_name}时出错: {e}", file=sys.stderr)
                continue
        
        return {
            'patterns': patterns,
            'pattern_details': pattern_details,
            'total_detected': len(patterns)
        }
    
    def calculate_technical_indicators(self, klines: List[Dict]) -> Dict:
        """
        使用TA-Lib计算技术指标
        
        Args:
            klines: K线数据列表
            
        Returns:
            {
                'rsi': {...},
                'macd': {...},
                'bollinger_bands': {...},
                'indicators': {...}  # 所有指标
            }
        """
        if not self.use_talib or not klines or len(klines) < 14:
            return {}
        
        # 转换为numpy数组
        opens = np.array([k['open'] for k in klines], dtype=np.float64)
        highs = np.array([k['high'] for k in klines], dtype=np.float64)
        lows = np.array([k['low'] for k in klines], dtype=np.float64)
        closes = np.array([k['close'] for k in klines], dtype=np.float64)
        volumes = np.array([k.get('volume', 0) for k in klines], dtype=np.float64)
        
        indicators = {}
        
        try:
            # RSI (相对强弱指标)
            rsi = talib.RSI(closes, timeperiod=14)
            indicators['rsi'] = {
                'value': float(rsi[-1]) if not np.isnan(rsi[-1]) else None,
                'values': rsi.tolist(),
                'overbought': 70,
                'oversold': 30
            }
            
            # MACD (指数平滑异同移动平均线)
            macd, signal, hist = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
            indicators['macd'] = {
                'macd': float(macd[-1]) if not np.isnan(macd[-1]) else None,
                'signal': float(signal[-1]) if not np.isnan(signal[-1]) else None,
                'histogram': float(hist[-1]) if not np.isnan(hist[-1]) else None,
                'values': {
                    'macd': macd.tolist(),
                    'signal': signal.tolist(),
                    'histogram': hist.tolist()
                }
            }
            
            # 布林带 (Bollinger Bands)
            upper, middle, lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
            indicators['bollinger_bands'] = {
                'upper': float(upper[-1]) if not np.isnan(upper[-1]) else None,
                'middle': float(middle[-1]) if not np.isnan(middle[-1]) else None,
                'lower': float(lower[-1]) if not np.isnan(lower[-1]) else None,
                'values': {
                    'upper': upper.tolist(),
                    'middle': middle.tolist(),
                    'lower': lower.tolist()
                }
            }
            
            # 移动平均线
            indicators['sma_20'] = {
                'value': float(talib.SMA(closes, timeperiod=20)[-1]) if len(closes) >= 20 else None
            }
            indicators['sma_50'] = {
                'value': float(talib.SMA(closes, timeperiod=50)[-1]) if len(closes) >= 50 else None
            }
            indicators['ema_12'] = {
                'value': float(talib.EMA(closes, timeperiod=12)[-1]) if len(closes) >= 12 else None
            }
            indicators['ema_26'] = {
                'value': float(talib.EMA(closes, timeperiod=26)[-1]) if len(closes) >= 26 else None
            }
            
            # ATR (平均真实波幅)
            atr = talib.ATR(highs, lows, closes, timeperiod=14)
            indicators['atr'] = {
                'value': float(atr[-1]) if not np.isnan(atr[-1]) else None,
                'values': atr.tolist()
            }
            
            # ADX (平均趋向指标)
            adx = talib.ADX(highs, lows, closes, timeperiod=14)
            indicators['adx'] = {
                'value': float(adx[-1]) if not np.isnan(adx[-1]) else None,
                'values': adx.tolist(),
                'strong_trend': 25  # ADX > 25 表示强趋势
            }
            
            # OBV (能量潮)
            if len(volumes) > 0 and np.sum(volumes) > 0:
                obv = talib.OBV(closes, volumes)
                indicators['obv'] = {
                    'value': float(obv[-1]),
                    'values': obv.tolist()
                }
            
            # Stochastic (随机指标)
            slowk, slowd = talib.STOCH(highs, lows, closes, 
                                      fastk_period=14, slowk_period=3, 
                                      slowk_matype=0, slowd_period=3, slowd_matype=0)
            indicators['stochastic'] = {
                'k': float(slowk[-1]) if not np.isnan(slowk[-1]) else None,
                'd': float(slowd[-1]) if not np.isnan(slowd[-1]) else None,
                'values': {
                    'k': slowk.tolist(),
                    'd': slowd.tolist()
                },
                'overbought': 80,
                'oversold': 20
            }
            
        except Exception as e:
            print(f"  计算技术指标时出错: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        return indicators
    
    def detect_all_patterns_enhanced(self, klines: List[Dict]) -> Dict:
        """
        增强版：检测所有形态（包括TA-Lib的K线形态和原有的图表形态）
        
        Args:
            klines: K线数据列表
            
        Returns:
            {
                'candlestick_patterns': {...},  # TA-Lib识别的K线形态
                'chart_patterns': {...},         # 原有的图表形态
                'technical_indicators': {...},    # 技术指标
                'summary': {...}                 # 综合分析
            }
        """
        result = {
            'candlestick_patterns': {},
            'chart_patterns': {},
            'technical_indicators': {},
            'summary': {}
        }
        
        # 1. 使用TA-Lib识别K线形态
        if self.use_talib:
            result['candlestick_patterns'] = self.detect_candlestick_patterns(klines)
        
        # 2. 使用原有方法识别图表形态
        result['chart_patterns'] = super().detect_all_patterns(klines)
        
        # 3. 计算技术指标
        if self.use_talib:
            result['technical_indicators'] = self.calculate_technical_indicators(klines)
        
        # 4. 生成综合分析
        result['summary'] = self._generate_summary(result, klines)
        
        return result
    
    def _generate_summary(self, analysis_result: Dict, klines: List[Dict]) -> Dict:
        """生成综合分析摘要"""
        summary = {
            'total_candlestick_patterns': len(analysis_result.get('candlestick_patterns', {}).get('patterns', [])),
            'total_chart_patterns': len(analysis_result.get('chart_patterns', {}).get('patterns', [])),
            'signals': [],
            'confidence': 0.0
        }
        
        # 分析K线形态信号
        candlestick_patterns = analysis_result.get('candlestick_patterns', {}).get('patterns', [])
        if candlestick_patterns:
            latest_pattern = candlestick_patterns[-1]
            summary['signals'].append({
                'type': 'candlestick',
                'name': latest_pattern['name'],
                'direction': latest_pattern['direction'],
                'confidence': min(latest_pattern.get('signal_strength', 100), 100)
            })
        
        # 分析图表形态信号
        chart_patterns = analysis_result.get('chart_patterns', {}).get('patterns', [])
        if chart_patterns:
            summary['signals'].append({
                'type': 'chart_pattern',
                'patterns': chart_patterns,
                'count': len(chart_patterns)
            })
        
        # 计算综合置信度
        if summary['signals']:
            confidences = [s.get('confidence', 50) for s in summary['signals'] if 'confidence' in s]
            if confidences:
                summary['confidence'] = sum(confidences) / len(confidences)
        
        return summary


def main():
    """测试函数"""
    print("=" * 80)
    print("增强版图表形态识别器测试")
    print("=" * 80)
    print()
    
    # 创建检测器
    detector = EnhancedChartPatternsDetector(use_talib=True)
    
    # 模拟K线数据
    print("生成模拟K线数据...")
    klines = []
    base_price = 50000.0
    for i in range(100):
        price_change = np.random.randn() * 100
        open_price = base_price + price_change
        high_price = open_price + abs(np.random.randn() * 50)
        low_price = open_price - abs(np.random.randn() * 50)
        close_price = open_price + np.random.randn() * 50
        base_price = close_price
        
        klines.append({
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': np.random.uniform(1000, 10000),
            'timestamp': i
        })
    
    print(f"✓ 生成了 {len(klines)} 根K线")
    print()
    
    # 检测所有形态
    print("检测形态...")
    result = detector.detect_all_patterns_enhanced(klines)
    
    # 显示结果
    print("=" * 80)
    print("检测结果")
    print("=" * 80)
    print()
    
    # K线形态
    candlestick = result.get('candlestick_patterns', {})
    print(f"K线形态: {candlestick.get('total_detected', 0)} 个")
    for pattern in candlestick.get('patterns', [])[-5:]:  # 显示最后5个
        print(f"  - {pattern['name']} ({pattern['direction']}) at index {pattern['index']}")
    print()
    
    # 图表形态
    chart = result.get('chart_patterns', {})
    print(f"图表形态: {len(chart.get('patterns', []))} 个")
    for pattern in chart.get('patterns', [])[:5]:  # 显示前5个
        print(f"  - {pattern}")
    print()
    
    # 技术指标
    indicators = result.get('technical_indicators', {})
    if indicators:
        print("技术指标:")
        if 'rsi' in indicators and indicators['rsi']['value']:
            print(f"  RSI: {indicators['rsi']['value']:.2f}")
        if 'macd' in indicators:
            macd = indicators['macd']
            if macd['macd']:
                print(f"  MACD: {macd['macd']:.2f}, Signal: {macd['signal']:.2f}")
        if 'bollinger_bands' in indicators:
            bb = indicators['bollinger_bands']
            print(f"  布林带: Upper={bb['upper']:.2f}, Middle={bb['middle']:.2f}, Lower={bb['lower']:.2f}")
    print()
    
    # 摘要
    summary = result.get('summary', {})
    print(f"综合置信度: {summary.get('confidence', 0):.1f}%")
    print()


if __name__ == '__main__':
    main()

