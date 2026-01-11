#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini模式匹配器（优化版）

优化内容：
1. 深入了解Gemini标注数据结构，改进特征提取
2. 优化匹配算法和权重分配
3. 支持深度学习集成（CNN图像特征、LSTM/Transformer时序特征）
4. 支持多时间框架（5m/15m/1h/4h）

功能：
- 从pattern_library表读取Gemini分析的价格行为特征
- 将实时K线数据与模式库特征进行匹配
- 使用优化的多维度匹配算法计算相似度
- 支持深度学习增强匹配
- 生成交易信号
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from db_manager_trader import TraderDBManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    TraderDBManager = None

try:
    from ml_dl.abu_price_action_learner import PriceActionLearner
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    PriceActionLearner = None

# 尝试导入深度学习模块
try:
    from abu.dl_features import DLFeatureExtractor
    DL_AVAILABLE = True
except ImportError:
    DL_AVAILABLE = False

# 尝试导入信号质量增强器
try:
    from abu.signal_quality_enhancer import enhance_signal_prices
    SIGNAL_ENHANCER_AVAILABLE = True
except ImportError:
    SIGNAL_ENHANCER_AVAILABLE = False
    enhance_signal_prices = None
    DLFeatureExtractor = None


class EnhancedGeminiPatternMatcher:
    """优化的Gemini模式匹配器"""
    
    # 特征名称映射表（Gemini自然语言 -> 标准化特征名称）
    FEATURE_NAME_MAPPING = {
        # Doji相关
        'doji': 'doji',
        'small body bars/dojis': 'doji',
        'dojis': 'doji',
        'small body bars': 'doji',
        
        # Pin Bar相关
        'pin bar': 'bullish_pin_bar',  # 默认看涨，实际需要上下文判断
        'bullish pin bar': 'bullish_pin_bar',
        'bearish pin bar': 'bearish_pin_bar',
        
        # Engulfing相关
        'bullish engulfing': 'bullish_engulfing',
        'bearish engulfing': 'bearish_engulfing',
        'engulfing': 'bullish_engulfing',  # 默认看涨
        'large bearish bars': 'bearish_engulfing',
        'large bullish bars': 'bullish_engulfing',
        'strong bullish bars': 'bullish_engulfing',
        'strong bearish bars': 'bearish_engulfing',
        
        # Inside/Outside Bar相关
        'inside bar': 'inside_bar',
        'inside bars': 'inside_bar',
        'outside bar': 'outside_bar',
        'outside bars': 'outside_bar',
    }
    
    def __init__(self, use_dl: bool = False, min_confidence: float = 0.0, 
                 exclude_other: bool = True, use_ml: bool = True):
        """
        初始化匹配器
        
        Args:
            use_dl: 是否使用深度学习特征（CNN/LSTM）
            min_confidence: 最小置信度阈值（默认0.0，建议0.5）
            exclude_other: 是否排除pattern_type='other'的模式（默认True，排除教学页面）
            use_ml: 是否使用ML模型增强（默认True）
        """
        self.pattern_library: List[Dict] = []
        self.learner = PriceActionLearner() if (ML_AVAILABLE and use_ml) else None
        self.dl_extractor = DLFeatureExtractor() if (DL_AVAILABLE and use_dl) else None
        self.use_dl = use_dl and DL_AVAILABLE
        self.use_ml = use_ml and ML_AVAILABLE
        
        # 优化的权重配置（基于原始算法，优化ML和DL权重）
        ml_weight = 0.3 if self.use_ml else 0.0
        dl_weight = 0.2 if self.use_dl else 0.0
        kline_weight = 1.0 - ml_weight - dl_weight
        
        self.weights = {
            'kline_features': kline_weight,  # K线特征匹配
            'ml_prediction': ml_weight,      # ML模型预测（增强）
            'dl_features': dl_weight         # 深度学习特征（增强）
        }
        
        self._load_pattern_library(min_confidence=min_confidence, exclude_other=exclude_other)
    
    def _normalize_feature_name(self, feature_name: str) -> str:
        """
        将Gemini的自然语言特征名称标准化为代码中的特征名称
        
        Args:
            feature_name: Gemini返回的特征名称（可能是自然语言描述）
        
        Returns:
            标准化后的特征名称
        """
        if not feature_name:
            return ''
        
        feature_name_lower = feature_name.lower().strip()
        
        # 直接匹配
        if feature_name_lower in self.FEATURE_NAME_MAPPING:
            return self.FEATURE_NAME_MAPPING[feature_name_lower]
        
        # 关键词匹配
        for gemini_name, std_name in self.FEATURE_NAME_MAPPING.items():
            if gemini_name in feature_name_lower:
                return std_name
        
        # 如果无法映射，返回原始名称（小写）
        return feature_name_lower
    
    def _load_pattern_library(self, min_confidence: float = 0.0, exclude_other: bool = True):
        """
        从数据库加载所有有Gemini标注的模式
        
        Args:
            min_confidence: 最小置信度阈值（默认0.0，建议0.5）
            exclude_other: 是否排除pattern_type='other'的模式（默认True）
        """
        if not DB_AVAILABLE:
            return
        
        try:
            db = TraderDBManager('abu')
            conn = db._get_connection()
            
            # 构建查询条件
            conditions = [
                "gemini_annotation_json IS NOT NULL",
                "gemini_annotation_json != ''"
            ]
            params = []
            
            # 排除pattern_type='other'（教学页面通常被标记为other）
            if exclude_other:
                conditions.append("(pattern_type IS NULL OR pattern_type != 'other' OR pattern_type = '')")
            
            # 置信度过滤（如果有confidence字段）
            # 注意：当前数据库可能没有confidence字段，先注释
            # if min_confidence > 0:
            #     conditions.append("COALESCE(confidence, 0.0) >= ?")
            #     params.append(min_confidence)
            
            query = f'''
                SELECT id, gemini_annotation_json, pattern_type, pattern_name, 
                       source_page, COALESCE(confidence, 0.0) as confidence
                FROM pattern_library
                WHERE {' AND '.join(conditions)}
                ORDER BY id
            '''
            
            results = conn.execute(query, params).fetchall()
            db.close()
            
            excluded_count = 0
            for pattern_id, gemini_json, pattern_type, pattern_name, source_page, confidence in results:
                try:
                    # 额外检查：排除已知的教学页面（如第222页）
                    if source_page and source_page in [222]:  # 可以扩展这个列表
                        excluded_count += 1
                        continue
                    
                    gemini_annotation = json.loads(gemini_json)
                    
                    # 检查置信度（如果数据库有confidence字段）
                    conf_value = confidence if confidence is not None else 0.0
                    if min_confidence > 0 and conf_value < min_confidence:
                        excluded_count += 1
                        continue
                    
                    self.pattern_library.append({
                        'id': pattern_id,
                        'pattern_type': pattern_type,
                        'pattern_name': pattern_name,
                        'source_page': source_page,
                        'confidence': conf_value,
                        'gemini_annotation': gemini_annotation
                    })
                except Exception as e:
                    print(f"⚠️  解析模式 {pattern_id} 失败: {e}", file=sys.stderr)
            
            print(f"✓ 加载了 {len(self.pattern_library)} 个Gemini模式")
            if excluded_count > 0:
                print(f"  (已排除 {excluded_count} 个低质量/教学页面模式)", file=sys.stderr)
        
        except Exception as e:
            print(f"⚠️  加载模式库失败: {e}", file=sys.stderr)
    
    def extract_realtime_features(self, klines_dict: Dict[str, List[Dict]]) -> Dict:
        """
        从实时K线数据提取特征（支持多时间框架）
        
        Args:
            klines_dict: 不同时间框架的K线数据字典
                格式: {'5m': [...], '15m': [...], '1h': [...], '4h': [...]}
        
        Returns:
            特征字典，结构类似Gemini分析结果
        """
        # 默认使用15m作为主要时间框架（向后兼容）
        klines_15m = klines_dict.get('15m', [])
        klines_1h = klines_dict.get('1h', [])
        klines_5m = klines_dict.get('5m', [])
        klines_4h = klines_dict.get('4h', [])
        
        if not klines_15m or len(klines_15m) < 20:
            return {}
        
        # 使用15m作为主要特征提取时间框架
        recent_15m = klines_15m[-100:] if len(klines_15m) >= 100 else klines_15m  # 扩展窗口
        recent_1h = klines_1h[-50:] if klines_1h else []
        recent_5m = klines_5m[-50:] if klines_5m else []
        recent_4h = klines_4h[-50:] if klines_4h else []
        
        # 价格数据
        closes_15m = [k['close'] for k in recent_15m]
        highs_15m = [k['high'] for k in recent_15m]
        lows_15m = [k['low'] for k in recent_15m]
        opens_15m = [k['open'] for k in recent_15m]
        volumes_15m = [k.get('volume', 0) for k in recent_15m]
        
        # ========== 1. K线行为特征（增强版） ==========
        kline_features = []
        if len(recent_15m) >= 2:
            # 检测最近10根K线的特征（扩展范围）
            for i in range(max(1, len(recent_15m) - 10), len(recent_15m)):
                if i < 1:
                    continue
                last = recent_15m[i]
                prev = recent_15m[i-1]
                
                # 吞没形态（增强检测逻辑）
                if last['close'] > last['open'] and prev['close'] < prev['open']:
                    if last['open'] < prev['close'] and last['close'] > prev['open']:
                        kline_features.append('bullish_engulfing')
                elif last['close'] < last['open'] and prev['close'] > prev['open']:
                    if last['open'] > prev['close'] and last['close'] < prev['open']:
                        kline_features.append('bearish_engulfing')
                
                # Pin Bar（增强检测）
                body = abs(last['close'] - last['open'])
                total_range = last['high'] - last['low']
                if total_range > 0:
                    body_ratio = body / total_range
                    upper_wick = last['high'] - max(last['open'], last['close'])
                    lower_wick = min(last['open'], last['close']) - last['low']
                    
                    if body_ratio < 0.3:
                        if upper_wick > lower_wick * 2:
                            kline_features.append('bearish_pin_bar')
                        elif lower_wick > upper_wick * 2:
                            kline_features.append('bullish_pin_bar')
                
                # Inside Bar
                if last['high'] < prev['high'] and last['low'] > prev['low']:
                    kline_features.append('inside_bar')
                
                # Outside Bar（新增）
                if last['high'] > prev['high'] and last['low'] < prev['low']:
                    kline_features.append('outside_bar')
                
                # Doji（新增）
                if body_ratio < 0.1:
                    kline_features.append('doji')
        
        # ========== 2. 趋势特征（多时间框架） ==========
        trend_features = {}
        
        # 15m趋势
        if len(closes_15m) >= 20:
            price_trend_15m = 'bullish' if closes_15m[-1] > closes_15m[0] else 'bearish'
            trend_strength_15m = abs(closes_15m[-1] - closes_15m[0]) / closes_15m[0] if closes_15m[0] > 0 else 0
            trend_features['15m'] = {
                'direction': price_trend_15m,
                'strength': trend_strength_15m
            }
        else:
            trend_features['15m'] = {'direction': 'neutral', 'strength': 0}
        
        # 1h趋势
        if recent_1h and len(recent_1h) >= 20:
            closes_1h = [k['close'] for k in recent_1h]
            price_trend_1h = 'bullish' if closes_1h[-1] > closes_1h[0] else 'bearish'
            # 计算EMA50（简化版）
            if len(closes_1h) >= 50:
                ema = closes_1h[0]
                k = 2 / (50 + 1)
                for price in closes_1h[1:]:
                    ema = price * k + ema * (1 - k)
                trend_strength_1h = abs(closes_1h[-1] - ema) / ema if ema > 0 else 0
            else:
                trend_strength_1h = abs(closes_1h[-1] - closes_1h[0]) / closes_1h[0] if closes_1h[0] > 0 else 0
            trend_features['1h'] = {
                'direction': price_trend_1h,
                'strength': trend_strength_1h
            }
        else:
            trend_features['1h'] = {'direction': 'neutral', 'strength': 0}
        
        # 4h趋势（新增）
        if recent_4h and len(recent_4h) >= 20:
            closes_4h = [k['close'] for k in recent_4h]
            price_trend_4h = 'bullish' if closes_4h[-1] > closes_4h[0] else 'bearish'
            trend_strength_4h = abs(closes_4h[-1] - closes_4h[0]) / closes_4h[0] if closes_4h[0] > 0 else 0
            trend_features['4h'] = {
                'direction': price_trend_4h,
                'strength': trend_strength_4h
            }
        else:
            trend_features['4h'] = {'direction': 'neutral', 'strength': 0}
        
        # ========== 3. 市场结构特征（新增） ==========
        structure = 'neutral'
        if len(closes_15m) >= 50:
            # 检测higher highs / lower lows
            recent_closes = closes_15m[-50:]
            highs_50 = highs_15m[-50:]
            lows_50 = lows_15m[-50:]
            
            # 检测higher highs
            peak_count = 0
            for i in range(10, len(highs_50) - 5):
                if highs_50[i] > max(highs_50[i-10:i]) and highs_50[i] > max(highs_50[i+1:i+6]):
                    peak_count += 1
            
            # 检测lower lows
            valley_count = 0
            for i in range(10, len(lows_50) - 5):
                if lows_50[i] < min(lows_50[i-10:i]) and lows_50[i] < min(lows_50[i+1:i+6]):
                    valley_count += 1
            
            if peak_count >= 2 and recent_closes[-1] > recent_closes[0]:
                structure = 'higher_highs'
            elif valley_count >= 2 and recent_closes[-1] < recent_closes[0]:
                structure = 'lower_lows'
            else:
                structure = 'neutral'
        
        # ========== 4. 波动率特征 ==========
        price_ranges = [(h - l) for h, l in zip(highs_15m, lows_15m)]
        avg_range = sum(price_ranges) / len(price_ranges) if price_ranges else 0
        volatility = avg_range / closes_15m[-1] if closes_15m and closes_15m[-1] > 0 else 0
        
        # 波动率分级
        if volatility > 0.02:
            volatility_level = 'high'
        elif volatility > 0.01:
            volatility_level = 'medium'
        else:
            volatility_level = 'low'
        
        # ========== 5. 成交量特征 ==========
        avg_volume = sum(volumes_15m) / len(volumes_15m) if volumes_15m else 0
        recent_volume = sum(volumes_15m[-5:]) / 5 if len(volumes_15m) >= 5 else 0
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        
        # 构建特征字典
        features = {
            'price_action_behavior': {
                'kline_features': list(set(kline_features)),  # 去重
                'trend': trend_features['15m']['direction'],
                'structure': structure,
                'trend_strength': trend_features['15m']['strength']
            },
            'market_conditions': {
                'trend_strength': 'strong' if trend_features['15m']['strength'] > 0.02 else 'weak',
                'volatility': volatility_level,
                'volatility_value': volatility,
                'trend_direction': trend_features['15m']['direction'],
                'volume_ratio': volume_ratio,
                'timeframe_trends': {
                    '15m': trend_features['15m'],
                    '1h': trend_features.get('1h', {'direction': 'neutral', 'strength': 0}),
                    '4h': trend_features.get('4h', {'direction': 'neutral', 'strength': 0})
                }
            },
            'patterns': [],
            'trading_signals': []
        }
        
        return features
    
    def calculate_similarity(self, realtime_features: Dict, pattern_annotation: Dict) -> float:
        """
        计算实时特征与模式库特征的相似度（优化版）
        
        Returns:
            相似度分数 (0.0 - 1.0)
        """
        if not realtime_features or not pattern_annotation:
            return 0.0
        
        # 确保是parsed格式
        pattern_parsed = pattern_annotation.get('parsed', pattern_annotation) if isinstance(pattern_annotation, dict) else {}
        
        score = 0.0
        factors = 0.0
        
        # ========== 1. K线特征匹配 ==========
        realtime_kline_features = set(realtime_features.get('price_action_behavior', {}).get('kline_features', []))
        pattern_kline_features = set()
        pattern_kline_raw = pattern_parsed.get('price_action_behavior', {}).get('kline_features', [])
        
        # 提取并标准化模式库中的特征名称
        for feat in pattern_kline_raw:
            if isinstance(feat, dict):
                feat_name = feat.get('feature', '')
            elif isinstance(feat, str):
                feat_name = feat
            else:
                continue
            
            # 标准化特征名称（将Gemini自然语言映射到标准化名称）
            normalized_name = self._normalize_feature_name(feat_name)
            if normalized_name:
                pattern_kline_features.add(normalized_name)
        
        kline_match = 0.0  # 初始化为0
        if pattern_kline_features:
            intersection = realtime_kline_features & pattern_kline_features
            union = pattern_kline_features | realtime_kline_features
            kline_match = len(intersection) / len(union) if union else 0.0
            score += kline_match * self.weights['kline_features']
            factors += self.weights['kline_features']
        
        # ========== 1.5. 趋势方向匹配（基于Gemini标注） ==========
        # 只匹配趋势方向一致的，提高匹配质量（但不完全拒绝方向相反的模式，因为可能是反转信号）
        realtime_trend = realtime_features.get('price_action_behavior', {}).get('trend', 'neutral')
        pattern_trend = pattern_parsed.get('price_action_behavior', {}).get('trend', 'neutral')
        
        # 标准化趋势方向（只考虑主要的bullish/bearish/neutral）
        def normalize_trend(trend_str):
            if not trend_str:
                return 'neutral'
            trend_lower = str(trend_str).lower()
            if 'bullish' in trend_lower and 'bearish' not in trend_lower:
                return 'bullish'
            elif 'bearish' in trend_lower and 'bullish' not in trend_lower:
                return 'bearish'
            else:
                return 'neutral'
        
        realtime_trend_norm = normalize_trend(realtime_trend)
        pattern_trend_norm = normalize_trend(pattern_trend)
        
        # 趋势匹配：完全匹配=1.0，一方为neutral=0.8，不匹配=0.5（不完全拒绝，但降低权重）
        if realtime_trend_norm == pattern_trend_norm:
            trend_match = 1.0
        elif realtime_trend_norm == 'neutral' or pattern_trend_norm == 'neutral':
            trend_match = 0.8  # neutral可以与任何趋势匹配，但权重稍低
        else:
            trend_match = 0.5  # 方向相反，但不完全拒绝（可能用于反转模式）
        
        # 趋势匹配作为K线匹配的调节因子（如果K线匹配存在）
        if kline_match > 0:
            # 趋势匹配调整：趋势方向一致时，K线匹配权重提高10%
            trend_adjustment = trend_match * 0.1
            score += kline_match * trend_adjustment * self.weights['kline_features']
        
        # ========== 2. ML模型预测匹配 ==========
        pattern_patterns = pattern_parsed.get('patterns', [])
        if self.learner and ML_AVAILABLE:
            try:
                # 使用ML模型预测实时K线的价格行为
                ml_prediction = self.learner.predict(realtime_features)
                if ml_prediction.get('success'):
                    price_action = ml_prediction.get('price_action', '')
                    if pattern_patterns:
                        pattern_types = [p.get('type', '') for p in pattern_patterns if isinstance(p, dict)]
                        # 简化的匹配逻辑
                        ml_match = 0.5  # 基础分数
                        if price_action in pattern_types:
                            ml_match = 0.9
                        elif price_action in ['reversal', 'continuation'] and any(t in pattern_types for t in ['reversal', 'continuation']):
                            ml_match = 0.8
                        score += ml_match * self.weights['ml_prediction']
                        factors += self.weights['ml_prediction']
            except Exception:
                pass
        
        # ========== 3. 深度学习特征匹配（可选） ==========
        if self.use_dl and self.dl_extractor and self.weights['dl_features'] > 0:
            try:
                # 提取深度学习特征（需要K线数据，这里简化处理）
                dl_match = 0.5  # 占位符，实际需要K线数据
                score += dl_match * self.weights['dl_features']
                factors += self.weights['dl_features']
            except Exception:
                pass
        
        # 归一化分数
        if factors > 0:
            score = score / factors
        
        return min(1.0, max(0.0, score))
    
    def match_patterns(self, klines_dict: Dict[str, List[Dict]], 
                      min_similarity: float = 0.5, max_matches: int = 10) -> List[Dict]:
        """
        匹配模式库中的模式（支持多时间框架）
        
        Args:
            klines_dict: 不同时间框架的K线数据字典
                {'5m': [...], '15m': [...], '1h': [...], '4h': [...]}
            min_similarity: 最小相似度阈值
            max_matches: 最大匹配数量
        
        Returns:
            匹配结果列表
        """
        # 提取实时特征
        realtime_features = self.extract_realtime_features(klines_dict)
        if not realtime_features:
            return []
        
        # 匹配所有模式
        matches = []
        for pattern in self.pattern_library:
            similarity = self.calculate_similarity(realtime_features, pattern['gemini_annotation'])
            
            if similarity >= min_similarity:
                matches.append({
                    'pattern_id': pattern['id'],
                    'pattern_name': pattern['pattern_name'],
                    'pattern_type': pattern['pattern_type'],
                    'gemini_annotation': pattern['gemini_annotation'],
                    'similarity': similarity,
                    'realtime_features': realtime_features
                })
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        # 返回Top N
        return matches[:max_matches]
    
    def generate_signal_from_match(self, match: Dict, current_price: float, 
                                   klines_15m: List[Dict]) -> Optional[Dict]:
        """
        从匹配结果生成交易信号
        
        Args:
            match: 匹配结果
            current_price: 当前价格
            klines_15m: 15分钟K线数据（用于计算止损止盈）
        
        Returns:
            交易信号字典
        """
        if not match or not klines_15m:
            return None
        
        pattern_annotation = match['gemini_annotation']
        pattern_parsed = pattern_annotation.get('parsed', pattern_annotation) if isinstance(pattern_annotation, dict) else {}
        
        # 提取交易信号
        trading_signals = pattern_parsed.get('trading_signals', [])
        if not trading_signals or not isinstance(trading_signals, list):
            return None
        
        # 使用第一个交易信号
        signal = trading_signals[0] if isinstance(trading_signals[0], dict) else {}
        
        direction = signal.get('direction', '').lower()
        if direction not in ['long', 'short', 'buy', 'sell']:
            # 尝试从模式类型推断
            pattern_type = match.get('pattern_type', '').lower()
            if any(kw in pattern_type for kw in ['bull', 'long', 'buy', 'up']):
                direction = 'long'
            elif any(kw in pattern_type for kw in ['bear', 'short', 'sell', 'down']):
                direction = 'short'
            else:
                return None
        
        # 标准化方向
        if direction in ['buy']:
            direction = 'long'
        elif direction in ['sell']:
            direction = 'short'
        
        # 计算止损和止盈
        entry_price = current_price
        
        stop_loss_pct = signal.get('stop_loss_pct') or signal.get('stop_loss_distance_pct')
        take_profit_1_pct = signal.get('take_profit_1_pct') or signal.get('take_profit_distance_pct')
        take_profit_2_pct = signal.get('take_profit_2_pct')
        
        # 如果信号中没有，从K线数据计算
        if stop_loss_pct is None or take_profit_1_pct is None:
            recent_lows = [k['low'] for k in klines_15m[-10:]]
            recent_highs = [k['high'] for k in klines_15m[-10:]]
            
            if direction == 'long':
                if not stop_loss_pct:
                    stop_loss = min(recent_lows) if recent_lows else entry_price * 0.98
                    stop_loss_pct = abs(entry_price - stop_loss) / entry_price
                if not take_profit_1_pct:
                    take_profit_1_pct = stop_loss_pct * 1.5
            else:  # short
                if not stop_loss_pct:
                    stop_loss = max(recent_highs) if recent_highs else entry_price * 1.02
                    stop_loss_pct = abs(stop_loss - entry_price) / entry_price
                if not take_profit_1_pct:
                    take_profit_1_pct = stop_loss_pct * 1.5
        
        # 确保所有百分比都有值
        if stop_loss_pct is None:
            stop_loss_pct = 0.02  # 默认2%
        if take_profit_1_pct is None:
            take_profit_1_pct = stop_loss_pct * 1.5
        if take_profit_2_pct is None:
            take_profit_2_pct = take_profit_1_pct * 2
        
        # 计算实际价格
        if direction == 'long':
            stop_loss = entry_price * (1 - stop_loss_pct)
            take_profit_1 = entry_price * (1 + take_profit_1_pct)
            take_profit_2 = entry_price * (1 + take_profit_2_pct)
        else:  # short
            stop_loss = entry_price * (1 + stop_loss_pct)
            take_profit_1 = entry_price * (1 - take_profit_1_pct)
            take_profit_2 = entry_price * (1 - take_profit_2_pct)
        
        # 提取概率（标准化：如果是百分比值则除以100）
        probability_raw = signal.get('probability', match.get('similarity', 0.5))
        if probability_raw is not None:
            # 如果probability > 1，说明是百分比值（如70表示70%），需要除以100转换为0-1之间的值
            probability = probability_raw / 100.0 if probability_raw > 1 else probability_raw
        else:
            probability = match.get('similarity', 0.5)
        
        # 构建基础信号
        base_signal = {
            'pattern_id': match['pattern_id'],
            'pattern_name': match['pattern_name'],
            'pattern_type': match['pattern_type'],
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit_1': take_profit_1,
            'take_profit_2': take_profit_2,
            'similarity': match['similarity'],
            'probability': probability,
            'reason': f"Gemini模式匹配(优化): {match['pattern_name']} (相似度: {match['similarity']:.2%})",
            'gemini_annotation': pattern_annotation
        }
        
        # 尝试使用信号质量增强器（如果可用）
        if SIGNAL_ENHANCER_AVAILABLE and enhance_signal_prices:
            try:
                enhanced_signal = enhance_signal_prices(
                    base_signal, klines_15m,
                    use_swing_points=True,
                    use_resistance=True
                )
                # 只在增强成功时使用增强后的信号
                if enhanced_signal.get('price_enhanced'):
                    enhanced_signal['reason'] = base_signal['reason'] + " [价格已增强]"
                    return enhanced_signal
            except Exception:
                # 如果增强失败，使用基础信号
                pass
        
        return base_signal

