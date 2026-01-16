#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini模式匹配器（Al Brooks特殊模式增强版）

在TA-Lib增强版基础上，添加Al Brooks特殊模式检测：
1. 前18根K线范围突破
2. 日内反转/End of Day Reversal
3. 竭尽式抛售高潮
4. 失败突破
5. 下降楔形
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 导入TA-Lib增强版匹配器
try:
    from abu.gemini_pattern_matcher_talib_enhanced import TalibEnhancedGeminiPatternMatcher
    BASE_MATCHER_AVAILABLE = True
except ImportError:
    try:
        from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher as TalibEnhancedGeminiPatternMatcher
        BASE_MATCHER_AVAILABLE = True
    except ImportError:
        BASE_MATCHER_AVAILABLE = False
        TalibEnhancedGeminiPatternMatcher = None

# 导入Al Brooks特殊模式检测器
try:
    from abu.al_brooks_special_patterns_detector import AlBrooksSpecialPatternsDetector
    AL_BROOKS_DETECTOR_AVAILABLE = True
except ImportError:
    AL_BROOKS_DETECTOR_AVAILABLE = False
    AlBrooksSpecialPatternsDetector = None


class AlBrooksEnhancedGeminiPatternMatcher(TalibEnhancedGeminiPatternMatcher):
    """Al Brooks特殊模式增强版匹配器"""
    
    def __init__(self, use_dl: bool = False, min_confidence: float = 0.0, 
                 exclude_other: bool = True, use_ml: bool = True,
                 use_talib: bool = True, talib_validation: bool = True,
                 use_al_brooks_patterns: bool = True):
        """
        初始化Al Brooks增强版匹配器
        
        Args:
            use_al_brooks_patterns: 是否使用Al Brooks特殊模式检测（默认True）
        """
        if not BASE_MATCHER_AVAILABLE:
            raise ImportError("基础匹配器不可用")
        
        try:
            super().__init__(
                use_dl=use_dl,
                min_confidence=min_confidence,
                exclude_other=exclude_other,
                use_ml=use_ml,
                use_talib=use_talib,
                talib_validation=talib_validation
            )
        except TypeError:
            # 兼容基础匹配器不支持TA-Lib参数的情况
            super().__init__(
                use_dl=use_dl,
                min_confidence=min_confidence,
                exclude_other=exclude_other,
                use_ml=use_ml
            )
        
        self.use_al_brooks_patterns = use_al_brooks_patterns and AL_BROOKS_DETECTOR_AVAILABLE
        
        if self.use_al_brooks_patterns:
            self.al_brooks_detector = AlBrooksSpecialPatternsDetector(initial_bars_count=18)
            print("✓ Al Brooks特殊模式检测已启用", file=sys.stderr)
        else:
            self.al_brooks_detector = None
            if not AL_BROOKS_DETECTOR_AVAILABLE:
                print("⚠ Al Brooks特殊模式检测器不可用", file=sys.stderr)
    
    def extract_realtime_features(self, klines_dict: Dict[str, List[Dict]]) -> Dict:
        """
        从实时K线数据提取特征（Al Brooks增强版）
        """
        # 先调用父类方法获取基础特征
        features = super().extract_realtime_features(klines_dict)
        
        if not features or not self.use_al_brooks_patterns:
            return features
        
        # 获取15m K线数据（主要时间框架）
        klines_15m = klines_dict.get('15m', [])
        if not klines_15m or len(klines_15m) < 20:
            return features
        
        # ========== 检测Al Brooks特殊模式 ==========
        try:
            al_brooks_results = self.al_brooks_detector.detect_all_special_patterns(klines_15m) or {}
            
            # 将检测结果添加到特征中
            if 'price_action_behavior' not in features:
                features['price_action_behavior'] = {}
            
            # 添加Al Brooks特殊模式
            features['price_action_behavior']['al_brooks_patterns'] = al_brooks_results
            
            # 如果检测到前18根K线突破，添加到K线特征
            first_18 = al_brooks_results.get('first_18_bars_breakout') or {}
            if first_18.get('detected'):
                breakout = first_18
                if 'kline_features' not in features['price_action_behavior']:
                    features['price_action_behavior']['kline_features'] = []
                
                if breakout.get('breakouts'):
                    first_bo = breakout['first_breakout']
                    if first_bo['type'] == 'bullish_breakout':
                        features['price_action_behavior']['kline_features'].append('first_18_bars_bullish_breakout')
                    else:
                        features['price_action_behavior']['kline_features'].append('first_18_bars_bearish_breakout')
            
            # 如果检测到日内反转，添加到特征
            reversal = al_brooks_results.get('end_of_day_reversal') or {}
            if reversal.get('detected'):
                if 'kline_features' not in features['price_action_behavior']:
                    features['price_action_behavior']['kline_features'] = []
                features['price_action_behavior']['kline_features'].append('end_of_day_reversal')

                if (reversal.get('exhaustive_sell_climax') or {}).get('detected'):
                    features['price_action_behavior']['kline_features'].append('exhaustive_sell_climax')
                if (reversal.get('failed_breakout_below') or {}).get('detected'):
                    features['price_action_behavior']['kline_features'].append('failed_breakout_below')
                if (reversal.get('wedge') or {}).get('detected'):
                    features['price_action_behavior']['kline_features'].append('descending_wedge')
                    
        except Exception as e:
            print(f"  Al Brooks模式检测失败: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        
        return features
    
    def calculate_similarity(self, realtime_features: Dict, pattern_annotation: Dict) -> float:
        """
        计算相似度（Al Brooks增强版）
        
        如果检测到Al Brooks特殊模式，增加相似度
        """
        # 先计算基础相似度
        base_similarity = super().calculate_similarity(realtime_features, pattern_annotation)
        
        if not self.use_al_brooks_patterns or base_similarity < 0.3:
            return base_similarity
        
        # ========== Al Brooks模式增强 ==========
        try:
            al_brooks_patterns = realtime_features.get('price_action_behavior', {}).get('al_brooks_patterns') or {}
            
            if not al_brooks_patterns:
                return base_similarity
            
            enhancement = 0.0
            
            # 检查前18根K线突破
            first_18 = al_brooks_patterns.get('first_18_bars_breakout') or {}
            if first_18.get('detected'):
                # 检查模式标注中是否提到breakout或range
                pattern_str = json.dumps(pattern_annotation, ensure_ascii=False).lower()
                if any(kw in pattern_str for kw in ['breakout', 'range', 'initial', 'first']):
                    enhancement += 0.1
            
            # 检查日内反转
            reversal = al_brooks_patterns.get('end_of_day_reversal') or {}
            if reversal.get('detected'):
                confidence = reversal.get('confidence', 0.0)
                
                # 检查模式标注中是否提到reversal
                pattern_str = json.dumps(pattern_annotation, ensure_ascii=False).lower()
                if any(kw in pattern_str for kw in ['reversal', 'climax', 'exhaustive', 'wedge']):
                    enhancement += confidence * 0.15
            
            # 应用增强
            enhanced_similarity = base_similarity + enhancement
            return min(1.0, max(0.0, enhanced_similarity))
            
        except Exception as e:
            print(f"  Al Brooks相似度增强失败: {e}", file=sys.stderr)
            return base_similarity
    
    def generate_signal_from_match(self, match: Dict, current_price: float, 
                                   klines_15m: List[Dict]) -> Optional[Dict]:
        """
        生成信号（Al Brooks增强版）
        
        在信号中添加Al Brooks特殊模式信息
        """
        # 先调用父类方法生成基础信号
        signal = super().generate_signal_from_match(match, current_price, klines_15m)
        
        if not signal or not self.use_al_brooks_patterns:
            return signal
        
        # ========== 添加Al Brooks特殊模式信息 ==========
        try:
            # 检测Al Brooks模式
            al_brooks_results = self.al_brooks_detector.detect_all_special_patterns(klines_15m) or {}
            
            # 添加到信号
            signal['al_brooks_patterns'] = al_brooks_results
            
            # 如果检测到特殊模式，在reason中说明
            detected_patterns = []
            first_18 = al_brooks_results.get('first_18_bars_breakout') or {}
            if first_18.get('detected'):
                detected_patterns.append('前18根K线范围突破')
            reversal = al_brooks_results.get('end_of_day_reversal') or {}
            if reversal.get('detected'):
                detected_patterns.append('日内反转')
            
            if detected_patterns:
                original_reason = signal.get('reason', '')
                signal['reason'] = f"{original_reason} [Al Brooks模式: {', '.join(detected_patterns)}]"
                
        except Exception as e:
            print(f"  Al Brooks信号增强失败: {e}", file=sys.stderr)
        
        return signal
