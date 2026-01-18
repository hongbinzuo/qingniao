#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini模式匹配器

功能：
- 从pattern_library表读取Gemini分析的价格行为特征
- 将实时K线数据与模式库特征进行匹配
- 计算匹配度和置信度
- 生成交易信号

设计思路：
1. 从数据库加载所有有Gemini标注的模式
2. 从实时K线数据提取特征
3. 使用价格行为学习模型和特征相似度进行匹配
4. 计算匹配度和置信度
5. 生成高质量的交易信号
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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


class GeminiPatternMatcher:
    """Gemini模式匹配器"""
    
    def __init__(self):
        self.pattern_library: List[Dict] = []
        self.learner = PriceActionLearner() if ML_AVAILABLE else None
        self._load_pattern_library()
    
    def _load_pattern_library(self):
        """从数据库加载所有有Gemini标注的模式"""
        if not DB_AVAILABLE:
            return
        
        try:
            db = TraderDBManager('abu')
            # 使用只读连接，允许多进程同时读取
            conn = db._get_connection(read_only=True)
            
            query = '''
                SELECT id, gemini_annotation_json, pattern_type, pattern_name
                FROM pattern_library
                WHERE gemini_annotation_json IS NOT NULL 
                  AND gemini_annotation_json != ''
                ORDER BY id
            '''
            
            results = conn.execute(query).fetchall()
            db.close()
            
            for pattern_id, gemini_json, pattern_type, pattern_name in results:
                try:
                    gemini_annotation = json.loads(gemini_json)
                    self.pattern_library.append({
                        'id': pattern_id,
                        'pattern_type': pattern_type,
                        'pattern_name': pattern_name,
                        'gemini_annotation': gemini_annotation
                    })
                except Exception as e:
                    print(f"⚠️  解析模式 {pattern_id} 失败: {e}", file=sys.stderr)
            
            print(f"✓ 加载了 {len(self.pattern_library)} 个Gemini模式")
        
        except Exception as e:
            print(f"⚠️  加载模式库失败: {e}", file=sys.stderr)
    
    def extract_realtime_features(self, klines_15m: List[Dict], klines_1h: List[Dict]) -> Dict:
        """
        从实时K线数据提取特征，用于匹配模式库
        
        Args:
            klines_15m: 15分钟K线数据（最近7天，约672根）
            klines_1h: 1小时K线数据（最近7天，约168根）
        
        Returns:
            特征字典，结构类似Gemini分析结果
        """
        if not klines_15m or len(klines_15m) < 20:
            return {}
        
        # 提取最近K线的特征（用于模式匹配）
        recent_15m = klines_15m[-50:]  # 最近50根15m K线（约12.5小时）
        recent_1h = klines_1h[-50:] if klines_1h else []  # 最近50根1h K线（约2天）
        
        # 价格数据
        closes_15m = [k['close'] for k in recent_15m]
        highs_15m = [k['high'] for k in recent_15m]
        lows_15m = [k['low'] for k in recent_15m]
        opens_15m = [k['open'] for k in recent_15m]
        volumes_15m = [k.get('volume', 0) for k in recent_15m]
        
        # 趋势特征
        if len(closes_15m) >= 10:
            price_trend_15m = 'bullish' if closes_15m[-1] > closes_15m[0] else 'bearish'
            trend_strength_15m = abs(closes_15m[-1] - closes_15m[0]) / closes_15m[0] if closes_15m[0] > 0 else 0
        else:
            price_trend_15m = 'neutral'
            trend_strength_15m = 0
        
        if recent_1h and len(recent_1h) >= 20:
            closes_1h = [k['close'] for k in recent_1h]
            price_trend_1h = 'bullish' if closes_1h[-1] > closes_1h[0] else 'bearish'
            # 计算EMA200（简化版，使用50根K线）
            if len(closes_1h) >= 50:
                ema_values = []
                k = 2 / (50 + 1)
                ema = closes_1h[0]
                for price in closes_1h[1:]:
                    ema = price * k + ema * (1 - k)
                    ema_values.append(ema)
                current_ema = ema_values[-1] if ema_values else closes_1h[-1]
                trend_strength_1h = abs(closes_1h[-1] - current_ema) / current_ema if current_ema > 0 else 0
            else:
                trend_strength_1h = 0
        else:
            price_trend_1h = 'neutral'
            trend_strength_1h = 0
        
        # 波动率特征
        price_ranges = [(h - l) for h, l in zip(highs_15m, lows_15m)]
        avg_range = sum(price_ranges) / len(price_ranges) if price_ranges else 0
        volatility = avg_range / closes_15m[-1] if closes_15m and closes_15m[-1] > 0 else 0
        
        # K线行为特征（检测最近几根K线）
        kline_features = []
        if len(recent_15m) >= 2:
            for i in range(max(1, len(recent_15m) - 5), len(recent_15m)):
                if i < 1:
                    continue
                last = recent_15m[i]
                prev = recent_15m[i-1]
                
                # 吞没形态
                if last['close'] > last['open'] and prev['close'] < prev['open']:
                    if last['open'] < prev['close'] and last['close'] > prev['open']:
                        kline_features.append('bullish_engulfing')
                elif last['close'] < last['open'] and prev['close'] > prev['open']:
                    if last['open'] > prev['close'] and last['close'] < prev['open']:
                        kline_features.append('bearish_engulfing')
                
                # Pin Bar
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
        
        # 成交量特征
        avg_volume = sum(volumes_15m) / len(volumes_15m) if volumes_15m else 0
        recent_volume = sum(volumes_15m[-5:]) / 5 if len(volumes_15m) >= 5 else 0
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1.0
        
        # 构建特征字典（类似Gemini分析结果的结构）
        features = {
            'price_action_behavior': {
                'kline_features': list(set(kline_features)),  # 去重
                'trend': price_trend_15m,
                'structure': 'higher_highs' if trend_strength_15m > 0.02 else 'lower_highs' if trend_strength_15m < -0.02 else 'neutral'
            },
            'market_conditions': {
                'trend_strength': 'strong' if trend_strength_15m > 0.02 or trend_strength_1h > 0.02 else 'weak',
                'volatility': 'high' if volatility > 0.01 else 'low',
                'trend_direction': price_trend_15m,
                'volume_ratio': volume_ratio,
                'timeframe_trend_1h': price_trend_1h
            },
            'patterns': [],  # 实时数据中不预先识别模式
            'trading_signals': []  # 稍后由匹配生成
        }
        
        return features
    
    def calculate_similarity(self, realtime_features: Dict, pattern_annotation: Dict) -> float:
        """
        计算实时特征与模式库特征的相似度
        
        Returns:
            相似度分数 (0.0 - 1.0)
        """
        if not realtime_features or not pattern_annotation:
            return 0.0
        
        # 确保是parsed格式
        pattern_parsed = pattern_annotation.get('parsed', pattern_annotation) if isinstance(pattern_annotation, dict) else {}
        
        score = 0.0
        factors = 0
        
        # 1. K线特征匹配 (权重: 0.8)
        realtime_kline_features = set(realtime_features.get('price_action_behavior', {}).get('kline_features', []))
        pattern_kline_features = set()
        pattern_kline_raw = pattern_parsed.get('price_action_behavior', {}).get('kline_features', [])
        for feat in pattern_kline_raw:
            if isinstance(feat, dict):
                pattern_kline_features.add(feat.get('feature', ''))
            elif isinstance(feat, str):
                pattern_kline_features.add(feat)
        
        if pattern_kline_features:
            kline_match = len(realtime_kline_features & pattern_kline_features) / len(pattern_kline_features | realtime_kline_features) if (pattern_kline_features | realtime_kline_features) else 0
            score += kline_match * 0.8
            factors += 0.8
        
        # 2. ML模型预测匹配 (权重: 0.2，如果可用)
        if self.learner and ML_AVAILABLE:
            try:
                # 使用ML模型预测实时K线的价格行为
                ml_prediction = self.learner.predict(realtime_features)
                if ml_prediction.get('success'):
                    price_action = ml_prediction.get('price_action', '')
                    pattern_patterns = pattern_parsed.get('patterns', [])
                    if pattern_patterns:
                        pattern_types = [p.get('type', '') for p in pattern_patterns if isinstance(p, dict)]
                        # 简化的匹配逻辑
                        ml_match = 0.5  # 基础分数
                        if price_action in ['reversal', 'continuation']:
                            ml_match = 0.8
                        score += ml_match * 0.2
                        factors += 0.2
            except Exception:
                pass
        
        # 归一化分数
        if factors > 0:
            score = score / factors
        
        return min(1.0, max(0.0, score))
    
    def match_patterns(self, klines_15m: List[Dict], klines_1h: List[Dict], 
                      min_similarity: float = 0.5, max_matches: int = 10) -> List[Dict]:
        """
        匹配模式库中的模式
        
        Args:
            klines_15m: 15分钟K线数据
            klines_1h: 1小时K线数据
            min_similarity: 最小相似度阈值
            max_matches: 最大匹配数量
        
        Returns:
            匹配结果列表，每个包含模式信息和匹配度
        """
        # 提取实时特征
        realtime_features = self.extract_realtime_features(klines_15m, klines_1h)
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
            交易信号字典，如果无法生成则返回None
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
        
        # 计算止损和止盈（从信号参数或K线数据推断）
        entry_price = current_price
        
        # 尝试从信号中获取止损止盈
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
                    take_profit_1_pct = stop_loss_pct * 1.5  # 默认1.5:1 RR
            else:  # short
                if not stop_loss_pct:
                    stop_loss = max(recent_highs) if recent_highs else entry_price * 1.02
                    stop_loss_pct = abs(stop_loss - entry_price) / entry_price
                if not take_profit_1_pct:
                    take_profit_1_pct = stop_loss_pct * 1.5
        
        # 计算实际价格
        if direction == 'long':
            stop_loss = entry_price * (1 - stop_loss_pct)
            take_profit_1 = entry_price * (1 + take_profit_1_pct)
            take_profit_2 = entry_price * (1 + (take_profit_2_pct or take_profit_1_pct * 2))
        else:  # short
            stop_loss = entry_price * (1 + stop_loss_pct)
            take_profit_1 = entry_price * (1 - take_profit_1_pct)
            take_profit_2 = entry_price * (1 - (take_profit_2_pct or take_profit_1_pct * 2))
        
        # 提取概率（如果有）
        probability = signal.get('probability', match.get('similarity', 0.5))
        
        return {
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
            'reason': f"Gemini模式匹配: {match['pattern_name']} (相似度: {match['similarity']:.2%})",
            'gemini_annotation': pattern_annotation
        }

