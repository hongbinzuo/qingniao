#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini模式匹配器（TA-Lib增强版）

在原有EnhancedGeminiPatternMatcher基础上，集成TA-Lib：
1. 使用TA-Lib检测K线形态（替代手动检测，更准确）
2. 使用TA-Lib技术指标验证信号可靠性
3. 使用TA-Lib增强相似度计算
4. 添加TA-Lib验证层过滤低质量信号

功能：
- 从pattern_library表读取Gemini分析的价格行为特征
- 使用TA-Lib检测K线形态（100+种）
- 使用TA-Lib计算技术指标（RSI、MACD、布林带等）
- 将实时K线数据与模式库特征进行匹配
- 使用TA-Lib验证匹配结果
- 生成可靠的交易信号
"""

from __future__ import annotations
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 导入原有的增强版匹配器
from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher

# 尝试导入TA-Lib增强版检测器
try:
    from chart_patterns_detector_enhanced import EnhancedChartPatternsDetector
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    EnhancedChartPatternsDetector = None
    print("警告: TA-Lib增强版检测器不可用，将使用基础功能", file=sys.stderr)

# 尝试直接导入TA-Lib
try:
    import talib
    TALIB_DIRECT_AVAILABLE = True
except ImportError:
    TALIB_DIRECT_AVAILABLE = False
    talib = None


class TalibEnhancedGeminiPatternMatcher(EnhancedGeminiPatternMatcher):
    """TA-Lib增强版Gemini模式匹配器"""
    
    def __init__(self, use_dl: bool = False, min_confidence: float = 0.0, 
                 exclude_other: bool = True, use_ml: bool = True,
                 require_trading_signals: bool = False, exclude_unmarked: bool = True,
                 signal_completeness: str = 'basic',
                 use_talib: bool = True, talib_validation: bool = True):
        """
        初始化TA-Lib增强版匹配器
        
        Args:
            use_dl: 是否使用深度学习特征
            min_confidence: 最小置信度阈值
            exclude_other: 是否排除pattern_type='other'的模式
            use_ml: 是否使用ML模型增强
            require_trading_signals: 是否要求Gemini标注包含交易信号
            exclude_unmarked: 是否排除无标注/教学页
            signal_completeness: 交易信号完整性等级
            use_talib: 是否使用TA-Lib（如果可用）
            talib_validation: 是否使用TA-Lib验证信号（默认True）
        """
        super().__init__(use_dl=use_dl, min_confidence=min_confidence, 
                        exclude_other=exclude_other, use_ml=use_ml,
                        require_trading_signals=require_trading_signals,
                        exclude_unmarked=exclude_unmarked,
                        signal_completeness=signal_completeness)
        
        self.use_talib = use_talib and (TALIB_AVAILABLE or TALIB_DIRECT_AVAILABLE)
        self.talib_validation = talib_validation and self.use_talib
        
        # 创建TA-Lib检测器（如果可用）
        if self.use_talib and TALIB_AVAILABLE:
            self.talib_detector = EnhancedChartPatternsDetector(use_talib=True)
        else:
            self.talib_detector = None
        
        if self.use_talib:
            print("✓ TA-Lib已启用，将用于K线形态识别和技术指标验证", file=sys.stderr)
        else:
            print("⚠ TA-Lib未启用，将使用基础功能", file=sys.stderr)
    
    def extract_realtime_features(self, klines_dict: Dict[str, List[Dict]]) -> Dict:
        """
        从实时K线数据提取特征（TA-Lib增强版）
        
        使用TA-Lib检测K线形态，补充手动检测
        """
        # 先调用父类方法获取基础特征
        features = super().extract_realtime_features(klines_dict)
        
        if not features or not self.use_talib:
            return features
        
        # 获取15m K线数据（主要时间框架）
        klines_15m = klines_dict.get('15m', [])
        if not klines_15m or len(klines_15m) < 2:
            return features
        
        # ========== 使用TA-Lib检测K线形态 ==========
        try:
            if self.talib_detector:
                # 使用增强版检测器
                candlestick_result = self.talib_detector.detect_candlestick_patterns(klines_15m)
                talib_patterns = candlestick_result.get('patterns', [])
            elif TALIB_DIRECT_AVAILABLE:
                # 直接使用TA-Lib
                talib_patterns = self._detect_talib_patterns_direct(klines_15m)
            else:
                talib_patterns = []
            
            # 将TA-Lib检测的形态添加到特征中
            if talib_patterns:
                # 获取现有的K线特征
                existing_features = set(features.get('price_action_behavior', {}).get('kline_features', []))
                
                # 映射TA-Lib形态到标准特征名称
                talib_feature_map = {
                    '吞没形态': 'engulfing',
                    '十字星': 'doji',
                    '锤子线': 'hammer',
                    '上吊线': 'hanging_man',
                    '流星线': 'shooting_star',
                    '倒锤子': 'inverted_hammer',
                    '孕线': 'harami',
                    '三只乌鸦': 'three_black_crows',
                    '三白兵': 'three_white_soldiers',
                    '晨星': 'morning_star',
                    '暮星': 'evening_star',
                    '刺透形态': 'piercing',
                    '乌云盖顶': 'dark_cloud_cover',
                }
                
                # 添加TA-Lib检测的形态
                for pattern in talib_patterns:
                    pattern_name = pattern.get('name', '')
                    direction = pattern.get('direction', '')
                    
                    # 映射到标准特征名称
                    if pattern_name in talib_feature_map:
                        base_feature = talib_feature_map[pattern_name]
                        if direction == 'bullish':
                            feature_name = f'bullish_{base_feature}' if not base_feature.startswith('bullish_') else base_feature
                        elif direction == 'bearish':
                            feature_name = f'bearish_{base_feature}' if not base_feature.startswith('bearish_') else base_feature
                        else:
                            feature_name = base_feature
                        
                        existing_features.add(feature_name)
                
                # 更新特征
                if 'price_action_behavior' not in features:
                    features['price_action_behavior'] = {}
                features['price_action_behavior']['kline_features'] = list(existing_features)
                features['price_action_behavior']['talib_patterns'] = talib_patterns
                
        except Exception as e:
            print(f"  TA-Lib形态检测失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        # ========== 使用TA-Lib计算技术指标 ==========
        try:
            if self.talib_detector:
                indicators = self.talib_detector.calculate_technical_indicators(klines_15m)
            elif TALIB_DIRECT_AVAILABLE:
                indicators = self._calculate_talib_indicators_direct(klines_15m)
            else:
                indicators = {}
            
            # 添加技术指标到特征中
            if indicators:
                if 'market_conditions' not in features:
                    features['market_conditions'] = {}
                features['market_conditions']['technical_indicators'] = indicators
                
        except Exception as e:
            print(f"  TA-Lib技术指标计算失败: {e}", file=sys.stderr)
        
        return features
    
    def _detect_talib_patterns_direct(self, klines: List[Dict]) -> List[Dict]:
        """直接使用TA-Lib检测K线形态"""
        if not TALIB_DIRECT_AVAILABLE or len(klines) < 2:
            return []
        
        try:
            opens = np.array([k['open'] for k in klines], dtype=np.float64)
            highs = np.array([k['high'] for k in klines], dtype=np.float64)
            lows = np.array([k['low'] for k in klines], dtype=np.float64)
            closes = np.array([k['close'] for k in klines], dtype=np.float64)
            
            patterns = []
            
            # 检测常用形态
            pattern_functions = {
                'CDLENGULFING': '吞没形态',
                'CDLDOJI': '十字星',
                'CDLHAMMER': '锤子线',
                'CDLHANGINGMAN': '上吊线',
                'CDLSHOOTINGSTAR': '流星线',
                'CDLINVERTEDHAMMER': '倒锤子',
                'CDLHARAMI': '孕线',
                'CDL3BLACKCROWS': '三只乌鸦',
                'CDL3WHITESOLDIERS': '三白兵',
                'CDLMORNINGSTAR': '晨星',
                'CDLEVENINGSTAR': '暮星',
                'CDLPIERCING': '刺透形态',
                'CDLDARKCLOUDCOVER': '乌云盖顶',
            }
            
            for func_name, pattern_name in pattern_functions.items():
                try:
                    func = getattr(talib, func_name)
                    result = func(opens, highs, lows, closes)
                    detected_indices = np.where(result != 0)[0]
                    
                    if len(detected_indices) > 0:
                        latest_index = detected_indices[-1]
                        signal_value = result[latest_index]
                        direction = 'bullish' if signal_value > 0 else 'bearish'
                        
                        patterns.append({
                            'name': pattern_name,
                            'direction': direction,
                            'index': int(latest_index),
                            'signal_strength': abs(signal_value),
                            'price': float(closes[latest_index])
                        })
                except AttributeError:
                    continue
                except Exception:
                    continue
            
            return patterns
            
        except Exception as e:
            print(f"  直接TA-Lib检测失败: {e}", file=sys.stderr)
            return []
    
    def _calculate_talib_indicators_direct(self, klines: List[Dict]) -> Dict:
        """直接使用TA-Lib计算技术指标"""
        if not TALIB_DIRECT_AVAILABLE or len(klines) < 14:
            return {}
        
        try:
            opens = np.array([k['open'] for k in klines], dtype=np.float64)
            highs = np.array([k['high'] for k in klines], dtype=np.float64)
            lows = np.array([k['low'] for k in klines], dtype=np.float64)
            closes = np.array([k['close'] for k in klines], dtype=np.float64)
            volumes = np.array([k.get('volume', 0) for k in klines], dtype=np.float64)
            
            indicators = {}
            
            # RSI
            rsi = talib.RSI(closes, timeperiod=14)
            if len(rsi) > 0 and not np.isnan(rsi[-1]):
                indicators['rsi'] = {
                    'value': float(rsi[-1]),
                    'overbought': 70,
                    'oversold': 30
                }
            
            # MACD
            macd, signal, hist = talib.MACD(closes, fastperiod=12, slowperiod=26, signalperiod=9)
            if len(macd) > 0 and not np.isnan(macd[-1]):
                indicators['macd'] = {
                    'macd': float(macd[-1]) if not np.isnan(macd[-1]) else None,
                    'signal': float(signal[-1]) if not np.isnan(signal[-1]) else None,
                    'histogram': float(hist[-1]) if not np.isnan(hist[-1]) else None
                }
            
            # 布林带
            upper, middle, lower = talib.BBANDS(closes, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
            if len(upper) > 0 and not np.isnan(upper[-1]):
                indicators['bollinger_bands'] = {
                    'upper': float(upper[-1]),
                    'middle': float(middle[-1]),
                    'lower': float(lower[-1])
                }
            
            # ATR
            atr = talib.ATR(highs, lows, closes, timeperiod=14)
            if len(atr) > 0 and not np.isnan(atr[-1]):
                indicators['atr'] = {
                    'value': float(atr[-1])
                }
            
            # ADX（趋势强度）
            adx = talib.ADX(highs, lows, closes, timeperiod=14)
            if len(adx) > 0 and not np.isnan(adx[-1]):
                indicators['adx'] = {
                    'value': float(adx[-1]),
                    'strong_trend': 25  # ADX > 25 表示强趋势
                }
            
            return indicators
            
        except Exception as e:
            print(f"  直接TA-Lib指标计算失败: {e}", file=sys.stderr)
            return {}
    
    def calculate_similarity(self, realtime_features: Dict, pattern_annotation: Dict) -> float:
        """
        计算实时特征与模式库特征的相似度（TA-Lib增强版）
        
        在原有相似度计算基础上，添加TA-Lib验证
        """
        # 先计算基础相似度
        base_similarity = super().calculate_similarity(realtime_features, pattern_annotation)
        
        if not self.talib_validation or base_similarity < 0.3:
            return base_similarity
        
        # ========== TA-Lib验证增强 ==========
        try:
            # 获取TA-Lib检测的形态
            talib_patterns = realtime_features.get('price_action_behavior', {}).get('talib_patterns', [])
            talib_indicators = realtime_features.get('market_conditions', {}).get('technical_indicators', {})
            
            # 验证因子（0.0 - 1.0）
            validation_score = 1.0
            
            # 1. K线形态验证
            if talib_patterns:
                # 如果TA-Lib检测到形态，增加相似度
                # 每个TA-Lib形态增加5%的相似度（最多增加20%）
                pattern_bonus = min(len(talib_patterns) * 0.05, 0.20)
                validation_score += pattern_bonus
            
            # 2. 技术指标验证
            if talib_indicators:
                indicator_validation = self._validate_with_indicators(
                    talib_indicators, 
                    pattern_annotation
                )
                # 指标验证影响相似度（最多±10%）
                validation_score += indicator_validation * 0.10
            
            # 应用验证调整（限制在合理范围内）
            validation_score = max(0.5, min(1.5, validation_score))
            enhanced_similarity = base_similarity * validation_score
            
            return min(1.0, max(0.0, enhanced_similarity))
            
        except Exception as e:
            print(f"  TA-Lib验证失败: {e}", file=sys.stderr)
            return base_similarity
    
    def _validate_with_indicators(self, indicators: Dict, pattern_annotation: Dict) -> float:
        """
        使用技术指标验证模式匹配
        
        Returns:
            验证分数 (-1.0 到 1.0)
            - 正数：指标支持匹配
            - 负数：指标不支持匹配
        """
        if not indicators:
            return 0.0
        
        validation_score = 0.0
        factors = 0.0
        
        # 解析模式标注
        pattern_parsed = pattern_annotation.get('parsed', pattern_annotation) if isinstance(pattern_annotation, dict) else {}
        trading_signals = pattern_parsed.get('trading_signals', [])
        
        if not trading_signals:
            return 0.0
        
        signal = trading_signals[0] if isinstance(trading_signals[0], dict) else {}
        direction = signal.get('direction', '').lower()
        
        # 1. RSI验证
        if 'rsi' in indicators:
            rsi_value = indicators['rsi'].get('value')
            if rsi_value:
                if direction in ['long', 'buy']:
                    # 看涨信号：RSI应该不是超买状态
                    if rsi_value < 70:
                        validation_score += 0.3
                    elif rsi_value > 80:
                        validation_score -= 0.5  # 超买，不支持看涨
                elif direction in ['short', 'sell']:
                    # 看跌信号：RSI应该不是超卖状态
                    if rsi_value > 30:
                        validation_score += 0.3
                    elif rsi_value < 20:
                        validation_score -= 0.5  # 超卖，不支持看跌
                factors += 1.0
        
        # 2. MACD验证
        if 'macd' in indicators:
            macd_data = indicators['macd']
            macd_value = macd_data.get('macd')
            signal_value = macd_data.get('signal')
            histogram = macd_data.get('histogram')
            
            if macd_value is not None and signal_value is not None:
                if direction in ['long', 'buy']:
                    # 看涨信号：MACD应该在信号线上方，或正在上升
                    if macd_value > signal_value:
                        validation_score += 0.3
                    if histogram and histogram > 0:
                        validation_score += 0.2
                elif direction in ['short', 'sell']:
                    # 看跌信号：MACD应该在信号线下方，或正在下降
                    if macd_value < signal_value:
                        validation_score += 0.3
                    if histogram and histogram < 0:
                        validation_score += 0.2
                factors += 1.0
        
        # 3. 布林带验证
        if 'bollinger_bands' in indicators:
            bb = indicators['bollinger_bands']
            upper = bb.get('upper')
            lower = bb.get('lower')
            middle = bb.get('middle')
            
            # 需要当前价格（从特征中获取，或使用middle作为近似）
            current_price = middle if middle else None
            
            if current_price and upper and lower:
                if direction in ['long', 'buy']:
                    # 看涨信号：价格不应该在上轨附近（可能超买）
                    if current_price < upper * 0.98:
                        validation_score += 0.2
                    else:
                        validation_score -= 0.3
                elif direction in ['short', 'sell']:
                    # 看跌信号：价格不应该在下轨附近（可能超卖）
                    if current_price > lower * 1.02:
                        validation_score += 0.2
                    else:
                        validation_score -= 0.3
                factors += 1.0
        
        # 4. ADX验证（趋势强度）
        if 'adx' in indicators:
            adx_value = indicators['adx'].get('value')
            if adx_value:
                # ADX > 25 表示强趋势，支持交易信号
                if adx_value > 25:
                    validation_score += 0.2
                elif adx_value < 20:
                    validation_score -= 0.2  # 趋势弱，信号可靠性低
                factors += 1.0
        
        # 归一化
        if factors > 0:
            validation_score = validation_score / factors
        
        return max(-1.0, min(1.0, validation_score))
    
    def validate_signal_with_talib(self, signal: Dict, klines_15m: List[Dict]) -> Dict:
        """
        使用TA-Lib验证交易信号
        
        Args:
            signal: 交易信号字典
            klines_15m: 15分钟K线数据
        
        Returns:
            验证结果字典，包含：
            - validated: 是否通过验证
            - confidence: 验证置信度
            - talib_indicators: TA-Lib技术指标
            - validation_reasons: 验证原因列表
        """
        if not self.use_talib or not klines_15m or len(klines_15m) < 14:
            return {
                'validated': True,  # 如果TA-Lib不可用，不拒绝信号
                'confidence': 0.5,
                'talib_indicators': {},
                'validation_reasons': ['TA-Lib不可用，跳过验证']
            }
        
        try:
            # 计算技术指标
            if self.talib_detector:
                indicators = self.talib_detector.calculate_technical_indicators(klines_15m)
            elif TALIB_DIRECT_AVAILABLE:
                indicators = self._calculate_talib_indicators_direct(klines_15m)
            else:
                indicators = {}
            
            direction = signal.get('direction', '').lower()
            entry_price = signal.get('entry_price', 0)
            current_price = klines_15m[-1]['close'] if klines_15m else entry_price
            
            validation_reasons = []
            confidence = 0.5
            validated = True
            
            # 1. RSI验证
            if 'rsi' in indicators:
                rsi_value = indicators['rsi'].get('value')
                if rsi_value:
                    if direction in ['long', 'buy']:
                        if rsi_value < 70:
                            validation_reasons.append(f"✓ RSI({rsi_value:.1f})未超买，支持看涨")
                            confidence += 0.1
                        elif rsi_value > 80:
                            validation_reasons.append(f"⚠ RSI({rsi_value:.1f})超买，看涨信号风险高")
                            confidence -= 0.2
                            validated = False
                    elif direction in ['short', 'sell']:
                        if rsi_value > 30:
                            validation_reasons.append(f"✓ RSI({rsi_value:.1f})未超卖，支持看跌")
                            confidence += 0.1
                        elif rsi_value < 20:
                            validation_reasons.append(f"⚠ RSI({rsi_value:.1f})超卖，看跌信号风险高")
                            confidence -= 0.2
                            validated = False
            
            # 2. MACD验证
            if 'macd' in indicators:
                macd_data = indicators['macd']
                macd_value = macd_data.get('macd')
                signal_value = macd_data.get('signal')
                histogram = macd_data.get('histogram')
                
                if macd_value is not None and signal_value is not None:
                    if direction in ['long', 'buy']:
                        if macd_value > signal_value:
                            validation_reasons.append(f"✓ MACD({macd_value:.2f}) > Signal({signal_value:.2f})，支持看涨")
                            confidence += 0.15
                        else:
                            validation_reasons.append(f"⚠ MACD({macd_value:.2f}) < Signal({signal_value:.2f})，看涨信号较弱")
                            confidence -= 0.1
                        
                        if histogram and histogram > 0:
                            validation_reasons.append(f"✓ MACD柱状图上升({histogram:.2f})，动量支持")
                            confidence += 0.1
                    elif direction in ['short', 'sell']:
                        if macd_value < signal_value:
                            validation_reasons.append(f"✓ MACD({macd_value:.2f}) < Signal({signal_value:.2f})，支持看跌")
                            confidence += 0.15
                        else:
                            validation_reasons.append(f"⚠ MACD({macd_value:.2f}) > Signal({signal_value:.2f})，看跌信号较弱")
                            confidence -= 0.1
                        
                        if histogram and histogram < 0:
                            validation_reasons.append(f"✓ MACD柱状图下降({histogram:.2f})，动量支持")
                            confidence += 0.1
            
            # 3. 布林带验证
            if 'bollinger_bands' in indicators:
                bb = indicators['bollinger_bands']
                upper = bb.get('upper')
                lower = bb.get('lower')
                middle = bb.get('middle')
                
                if current_price and upper and lower and middle:
                    price_position = (current_price - lower) / (upper - lower) if (upper - lower) > 0 else 0.5
                    
                    if direction in ['long', 'buy']:
                        if price_position < 0.8:  # 价格不在上轨附近
                            validation_reasons.append(f"✓ 价格位置({price_position*100:.1f}%)，未超买")
                            confidence += 0.1
                        else:
                            validation_reasons.append(f"⚠ 价格接近上轨({price_position*100:.1f}%)，可能超买")
                            confidence -= 0.15
                    elif direction in ['short', 'sell']:
                        if price_position > 0.2:  # 价格不在下轨附近
                            validation_reasons.append(f"✓ 价格位置({price_position*100:.1f}%)，未超卖")
                            confidence += 0.1
                        else:
                            validation_reasons.append(f"⚠ 价格接近下轨({price_position*100:.1f}%)，可能超卖")
                            confidence -= 0.15
            
            # 4. ADX验证（趋势强度）
            if 'adx' in indicators:
                adx_value = indicators['adx'].get('value')
                if adx_value:
                    if adx_value > 25:
                        validation_reasons.append(f"✓ ADX({adx_value:.1f}) > 25，趋势强劲")
                        confidence += 0.15
                    elif adx_value < 20:
                        validation_reasons.append(f"⚠ ADX({adx_value:.1f}) < 20，趋势较弱")
                        confidence -= 0.1
            
            # 5. ATR验证（波动率）
            if 'atr' in indicators:
                atr_value = indicators['atr'].get('value')
                if atr_value and current_price:
                    atr_pct = (atr_value / current_price) * 100
                    if 0.5 < atr_pct < 5.0:  # 合理的波动率范围
                        validation_reasons.append(f"✓ ATR({atr_pct:.2f}%)，波动率正常")
                        confidence += 0.05
                    elif atr_pct > 10:
                        validation_reasons.append(f"⚠ ATR({atr_pct:.2f}%)，波动率过高，风险大")
                        confidence -= 0.15
            
            # 限制置信度范围
            confidence = max(0.0, min(1.0, confidence))
            
            return {
                'validated': validated,
                'confidence': confidence,
                'talib_indicators': indicators,
                'validation_reasons': validation_reasons
            }
            
        except Exception as e:
            print(f"  TA-Lib信号验证失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return {
                'validated': True,  # 验证失败时不拒绝信号
                'confidence': 0.5,
                'talib_indicators': {},
                'validation_reasons': [f'验证过程出错: {e}']
            }
    
    def generate_signal_from_match(self, match: Dict, current_price: float, 
                                   klines_15m: List[Dict]) -> Optional[Dict]:
        """
        从匹配结果生成交易信号（TA-Lib增强版）
        
        在生成信号后，使用TA-Lib验证信号可靠性
        """
        # 先调用父类方法生成基础信号
        signal = super().generate_signal_from_match(match, current_price, klines_15m)
        
        if not signal:
            return None
        
        # ========== TA-Lib验证信号 ==========
        if self.talib_validation:
            validation_result = self.validate_signal_with_talib(signal, klines_15m)
            
            # 添加验证结果到信号
            signal['talib_validation'] = validation_result
            
            # 如果验证失败，可以选择拒绝信号或降低置信度
            if not validation_result.get('validated', True):
                # 选项1: 拒绝信号（严格模式）
                # return None
                
                # 选项2: 降低置信度但保留信号（宽松模式，推荐）
                original_confidence = signal.get('confidence', 0.5)
                validation_confidence = validation_result.get('confidence', 0.5)
                # 综合置信度：取平均值
                signal['confidence'] = (original_confidence + validation_confidence) / 2
                signal['confidence_reduced'] = True
                signal['validation_warning'] = 'TA-Lib验证未完全通过，但信号保留'
            
            # 添加技术指标信息到信号
            if validation_result.get('talib_indicators'):
                signal['talib_indicators'] = validation_result['talib_indicators']
            
            # 添加验证原因
            if validation_result.get('validation_reasons'):
                signal['validation_reasons'] = validation_result['validation_reasons']
        
        return signal



