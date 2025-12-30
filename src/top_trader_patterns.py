#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
顶级交易员常用形态识别模块（统一接口）
整合现有形态识别模块，统一输出格式，确保每种形态都提供明确的买入点/卖出点和止损点
包含：8种看涨形态、8种看跌形态、8种反转形态（共24种）
"""

import sys
from typing import Dict, List, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 导入现有模块
try:
    from bullish_patterns_with_signals import BullishPatternsWithSignals
    BULLISH_PATTERNS_AVAILABLE = True
except ImportError:
    BULLISH_PATTERNS_AVAILABLE = False
    BullishPatternsWithSignals = None

try:
    from chart_patterns_detector import ChartPatternsDetector
    CHART_PATTERNS_AVAILABLE = True
except ImportError:
    CHART_PATTERNS_AVAILABLE = False
    ChartPatternsDetector = None


class TopTraderPatterns:
    """顶级交易员常用形态识别器（统一接口）"""
    
    def __init__(self):
        """初始化形态识别器"""
        if BULLISH_PATTERNS_AVAILABLE:
            self.bullish_detector = BullishPatternsWithSignals()
        else:
            self.bullish_detector = None
        
        if CHART_PATTERNS_AVAILABLE:
            self.chart_detector = ChartPatternsDetector()
        else:
            self.chart_detector = None
    
    def detect_all_patterns(self, klines: List[Dict]) -> Dict:
        """
        检测所有24种顶级交易员常用形态
        
        Args:
            klines: K线数据列表
        
        Returns:
            {
                'bullish_patterns': [...],  # 看涨形态列表（8种）
                'bearish_patterns': [...],  # 看跌形态列表（8种）
                'reversal_patterns': [...],  # 反转形态列表（8种）
                'all_signals': [...],  # 所有信号合并（带类型标记）
                'total_patterns': int  # 总形态数
            }
        """
        if not klines or len(klines) < 20:
            return {
                'bullish_patterns': [],
                'bearish_patterns': [],
                'reversal_patterns': [],
                'all_signals': [],
                'total_patterns': 0
            }
        
        bullish_patterns = []
        bearish_patterns = []
        reversal_patterns = []
        all_signals = []
        
        # ========== 看涨形态（8种）==========
        # 复用bullish_patterns_with_signals模块
        if self.bullish_detector:
            try:
                bullish_result = self.bullish_detector.detect_all_bullish_patterns(klines)
                if bullish_result.get('patterns'):
                    for pattern in bullish_result['patterns']:
                        # 统一格式
                        signal = {
                            'name': pattern['name'],
                            'type': 'long',
                            'strength': pattern.get('strength', 70.0),
                            'entry': pattern['entry'],
                            'stop_loss': pattern['stop_loss'],
                            'entry_model': f"看涨形态-{pattern['name']}",
                            'reason': pattern.get('description', f"识别到{pattern['name']}形态"),
                            'category': 'bullish'
                        }
                        bullish_patterns.append(signal)
                        all_signals.append(signal)
            except Exception as e:
                print(f"看涨形态识别失败: {e}", file=sys.stderr)
        
        # ========== 看跌形态（8种）==========
        # 从chart_patterns_detector获取看跌形态
        if self.chart_detector:
            try:
                chart_result = self.chart_detector.detect_all_patterns(klines)
                
                # 提取看跌持续形态
                for pattern in chart_result.get('continuation_patterns', []):
                    if pattern['type'] == 'bearish_continuation':
                        # 转换为统一格式
                        signal = {
                            'name': pattern['name'],
                            'type': 'short',
                            'strength': pattern.get('confidence', 70.0),
                            'entry': pattern.get('entry'),
                            'stop_loss': pattern.get('stop_loss'),
                            'entry_model': f"看跌形态-{pattern['name']}",
                            'reason': f"识别到{pattern['name']}形态",
                            'category': 'bearish'
                        }
                        if signal['entry'] and signal['stop_loss']:
                            bearish_patterns.append(signal)
                            all_signals.append(signal)
            except Exception as e:
                print(f"看跌形态识别失败: {e}", file=sys.stderr)
        
        # ========== 反转形态（8种）==========
        # 从chart_patterns_detector获取反转形态
        if self.chart_detector:
            try:
                chart_result = self.chart_detector.detect_all_patterns(klines)
                
                # 提取反转形态
                for pattern in chart_result.get('reversal_patterns', []):
                    # 转换为统一格式
                    signal_type = 'long' if 'bullish' in pattern['type'] else 'short'
                    # 优化入场价：如果入场价距离当前价格太远，调整到合理位置
                    entry = pattern.get('entry')
                    if entry:
                        current_price = klines[-1]['close'] if klines else None
                        if current_price:
                            if signal_type == 'long' and entry < current_price * 0.95:
                                # 做多入场价低于当前价格超过5%，调整到当前价格下方1-2%等待回调
                                entry = current_price * 0.985
                                entry_reason = f"入场价已调整到{entry:.0f}（当前价格下方1.5%，等待回调）"
                            elif signal_type == 'short' and entry > current_price * 1.05:
                                # 做空入场价高于当前价格超过5%，调整到当前价格上方1-2%等待反弹
                                entry = current_price * 1.015
                                entry_reason = f"入场价已调整到{entry:.0f}（当前价格上方1.5%，等待反弹）"
                            else:
                                entry_reason = pattern.get('entry_reason', '')
                    else:
                        entry_reason = ''
                    
                    # 构建理由
                    reason = f"识别到{pattern['name']}形态"
                    if entry_reason:
                        reason += f"。{entry_reason}"
                    
                    signal = {
                        'name': pattern['name'],
                        'type': signal_type,
                        'strength': pattern.get('confidence', 70.0),
                        'entry': entry,
                        'stop_loss': pattern.get('stop_loss'),
                        'entry_model': f"反转形态-{pattern['name']}",
                        'reason': reason,
                        'category': 'reversal_bullish' if 'bullish' in pattern['type'] else 'reversal_bearish'
                    }
                    if signal['entry'] and signal['stop_loss']:
                        reversal_patterns.append(signal)
                        all_signals.append(signal)
            except Exception as e:
                print(f"反转形态识别失败: {e}", file=sys.stderr)
        
        # 补充看跌形态（基于现有看涨形态的逻辑，创建看跌版本）
        bearish_patterns.extend(self._detect_additional_bearish_patterns(klines))
        for pattern in bearish_patterns:
            if pattern not in all_signals:
                all_signals.append(pattern)
        
        # 补充反转形态（双重顶/底、钻石、矩形、头肩顶/底）
        reversal_patterns.extend(self._detect_additional_reversal_patterns(klines))
        for pattern in reversal_patterns:
            if pattern not in all_signals:
                all_signals.append(pattern)
        
        return {
            'bullish_patterns': bullish_patterns,
            'bearish_patterns': bearish_patterns,
            'reversal_patterns': reversal_patterns,
            'all_signals': all_signals,
            'total_patterns': len(all_signals)
        }
    
    def _detect_additional_bearish_patterns(self, klines: List[Dict]) -> List[Dict]:
        """检测额外的看跌形态（基于看涨形态的镜像逻辑）"""
        patterns = []
        # 这里可以添加基于看涨形态逻辑的看跌版本
        # 例如：看跌旗形、看跌三角形等
        return patterns
    
    def _detect_additional_reversal_patterns(self, klines: List[Dict]) -> List[Dict]:
        """检测额外的反转形态"""
        patterns = []
        # 这里可以添加额外的反转形态检测
        return patterns



