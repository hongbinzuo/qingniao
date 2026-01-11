#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能解析Gemini Vision API输出（独立模块的一部分）

功能：
- 解析Gemini返回的JSON（可能不完整或格式不一致）
- 从text_notes提取交易参数（概率、价格等）
- 补全缺失字段
- 标准化格式

输入：
- outputs/abu_gemini_annotations_enhanced.jsonl（Gemini分析结果）

输出：
- outputs/abu_gemini_parsed.jsonl（解析后的标准化结果）

使用：
    python scripts/abu_parse_gemini_output.py \
        --input outputs/abu_gemini_annotations_enhanced.jsonl \
        --output outputs/abu_gemini_parsed.jsonl
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

ROOT = Path(__file__).resolve().parent.parent

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


@dataclass
class ParsedAnnotation:
    """解析后的标准化标注"""
    patterns: List[Dict]
    pattern_combination: str
    price_action_behavior: Dict
    trading_signals: List[Dict]
    market_conditions: Dict
    annotations: List[Dict]
    text_notes: List[str]
    confidence: float
    parse_errors: List[str]  # 解析过程中的错误


class GeminiOutputParser:
    """Gemini输出智能解析器"""
    
    def __init__(self):
        self.parse_errors = []
    
    def parse(self, gemini_output: Dict) -> ParsedAnnotation:
        """
        解析Gemini输出，补全缺失字段
        
        Args:
            gemini_output: Gemini API返回的原始结果
        
        Returns:
            标准化的ParsedAnnotation对象
        """
        result = ParsedAnnotation(
            patterns=[],
            pattern_combination='',
            price_action_behavior={},
            trading_signals=[],
            market_conditions={},
            annotations=[],
            text_notes=[],
            confidence=0.0,
            parse_errors=[]
        )
        
        # 如果输出包含错误，直接返回
        if gemini_output.get('error'):
            result.parse_errors.append(f"Gemini API错误: {gemini_output['error']}")
            return result
        
        # 提取原始JSON（可能嵌套在result中）
        raw_result = gemini_output.get('result', gemini_output)
        if isinstance(raw_result, str):
            try:
                raw_result = json.loads(raw_result)
            except:
                # 尝试从raw字段提取
                raw_result = gemini_output.get('raw', {})
        
        # 1. 解析patterns（支持多模式）
        result.patterns = self._parse_patterns(raw_result)
        
        # 2. 提取pattern_combination
        result.pattern_combination = self._extract_pattern_combination(raw_result, result.patterns)
        
        # 3. 解析price_action_behavior
        result.price_action_behavior = self._parse_price_action_behavior(raw_result)
        
        # 4. 解析trading_signals（提取交易参数）
        result.trading_signals = self._parse_trading_signals(raw_result)
        
        # 5. 从text_notes提取额外交易信号
        text_notes = self._extract_text_notes(raw_result)
        result.text_notes = text_notes
        
        # 从text_notes中提取交易参数（补充到trading_signals）
        for note in text_notes:
            signal_from_note = self._parse_trading_note(note)
            if signal_from_note:
                result.trading_signals.append(signal_from_note)
        
        # 6. 解析market_conditions
        result.market_conditions = self._parse_market_conditions(raw_result)
        
        # 7. 解析annotations
        result.annotations = self._parse_annotations(raw_result)
        
        # 8. 提取confidence
        result.confidence = float(raw_result.get('confidence', 0.0))
        if not result.confidence and result.patterns:
            # 从patterns计算平均置信度
            confidences = [p.get('confidence', 0.0) for p in result.patterns if isinstance(p.get('confidence'), (int, float))]
            result.confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return result
    
    def _parse_patterns(self, data: Dict) -> List[Dict]:
        """解析模式列表"""
        patterns = []
        
        # 方式1: patterns字段是列表
        if isinstance(data.get('patterns'), list):
            for p in data['patterns']:
                if isinstance(p, dict):
                    patterns.append({
                        'name': p.get('name', 'Unknown'),
                        'type': p.get('type', 'unknown'),
                        'location': p.get('location', 'unknown'),
                        'confidence': float(p.get('confidence', 0.5))
                    })
        
        # 方式2: 单一pattern字段
        elif data.get('pattern'):
            patterns.append({
                'name': data['pattern'],
                'type': self._infer_pattern_type(data['pattern']),
                'location': self._infer_location(data),
                'confidence': float(data.get('confidence', 0.5))
            })
        
        # 方式3: 从pattern_combination推断
        elif data.get('pattern_combination'):
            combo = data['pattern_combination']
            # 分割组合（如 "W底 + 三角形 + 突破"）
            pattern_names = [p.strip() for p in combo.split('+') if p.strip()]
            for name in pattern_names:
                patterns.append({
                    'name': name,
                    'type': self._infer_pattern_type(name),
                    'location': 'unknown',
                    'confidence': 0.7  # 默认置信度
                })
        
        return patterns if patterns else [{'name': 'Unknown', 'type': 'unknown', 'location': 'unknown', 'confidence': 0.0}]
    
    def _infer_pattern_type(self, pattern_name: str) -> str:
        """从模式名称推断类型"""
        name_lower = pattern_name.lower()
        
        # 反转模式
        if any(x in name_lower for x in ['w底', 'w bottom', 'double bottom', '头肩底', 'head and shoulder bottom']):
            return 'reversal'
        if any(x in name_lower for x in ['m顶', 'm top', 'double top', '头肩顶', 'head and shoulder top']):
            return 'reversal'
        
        # 持续模式
        if any(x in name_lower for x in ['triangle', '三角形', 'flag', '旗形', 'wedge', '楔形']):
            return 'continuation'
        
        # 价格行为
        if any(x in name_lower for x in ['engulfing', '吞没', 'pin bar', '影线', 'inside bar', '内包']):
            return 'price_action'
        
        return 'unknown'
    
    def _infer_location(self, data: Dict) -> str:
        """推断模式位置"""
        direction = data.get('direction', '').lower()
        if 'long' in direction or 'bottom' in str(data).lower() or 'buy' in str(data).lower():
            return 'bottom'
        elif 'short' in direction or 'top' in str(data).lower() or 'sell' in str(data).lower():
            return 'top'
        return 'middle'
    
    def _extract_pattern_combination(self, data: Dict, patterns: List[Dict]) -> str:
        """提取模式组合"""
        if data.get('pattern_combination'):
            return data['pattern_combination']
        
        # 从patterns列表生成组合
        if len(patterns) > 1:
            pattern_names = [p['name'] for p in patterns]
            return ' + '.join(pattern_names)
        elif len(patterns) == 1:
            return patterns[0]['name']
        
        return ''
    
    def _parse_price_action_behavior(self, data: Dict) -> Dict:
        """解析价格行为特征"""
        behavior = data.get('price_action_behavior', {})
        
        if not behavior:
            # 从其他字段推断
            behavior = {
                'trend': data.get('trend', 'neutral'),
                'structure': 'unknown',
                'kline_features': [],
                'volume_behavior': 'unknown'
            }
            
            # 从key_features提取
            key_features = data.get('key_features', [])
            if isinstance(key_features, list):
                behavior['kline_features'] = key_features
            elif isinstance(key_features, str):
                # 尝试解析字符串
                behavior['kline_features'] = [f.strip() for f in key_features.split(',')]
        
        # 确保kline_features是列表
        if isinstance(behavior.get('kline_features'), str):
            behavior['kline_features'] = [behavior['kline_features']]
        
        # 标准化
        return {
            'trend': behavior.get('trend', 'neutral'),
            'structure': behavior.get('structure', 'unknown'),
            'kline_features': behavior.get('kline_features', []),
            'volume_behavior': behavior.get('volume_behavior', 'unknown')
        }
    
    def _parse_trading_signals(self, data: Dict) -> List[Dict]:
        """解析交易信号"""
        signals = []
        
        # 方式1: trading_signals字段是列表
        if isinstance(data.get('trading_signals'), list):
            for sig in data['trading_signals']:
                if isinstance(sig, dict):
                    signals.append(self._normalize_signal(sig))
        
        # 方式2: 从单一字段推断
        elif data.get('direction') or data.get('entry_price_hint'):
            signal = self._normalize_signal(data)
            if signal:
                signals.append(signal)
        
        return signals
    
    def _normalize_signal(self, sig: Dict) -> Dict:
        """标准化交易信号"""
        return {
            'direction': self._extract_direction(sig),
            'entry_condition': sig.get('entry_condition', ''),
            'entry_price_hint': self._parse_price(sig.get('entry_price_hint')),
            'stop_loss_hint': self._parse_price(sig.get('stop_loss_hint')),
            'take_profit_1_hint': self._parse_price(sig.get('take_profit_1_hint')),
            'take_profit_2_hint': self._parse_price(sig.get('take_profit_2_hint')),
            'probability': self._parse_probability(sig),
            'target': sig.get('target', ''),
            'risk_reward_ratio': self._parse_float(sig.get('risk_reward_ratio')),
            'timeframe_hint': sig.get('timeframe_hint', '')
        }
    
    def _extract_direction(self, data: Dict) -> str:
        """提取交易方向"""
        direction = (data.get('direction') or '').lower()
        if 'long' in direction or 'buy' in direction or '做多' in direction or '买入' in direction:
            return 'long'
        elif 'short' in direction or 'sell' in direction or '做空' in direction or '卖出' in direction:
            return 'short'
        return 'neutral'
    
    def _parse_price(self, price_str: Any) -> Optional[float]:
        """解析价格字符串（如 "87,500" -> 87500.0）"""
        if price_str is None:
            return None
        if isinstance(price_str, (int, float)):
            return float(price_str)
        
        # 移除逗号和货币符号
        price_clean = re.sub(r'[,\$¥€]', '', str(price_str)).strip()
        try:
            return float(price_clean)
        except:
            return None
    
    def _parse_probability(self, data: Dict) -> Optional[int]:
        """解析概率（如 "75% chance" -> 75）"""
        # 从probability字段
        prob = data.get('probability')
        if isinstance(prob, (int, float)):
            return int(prob)
        
        # 从文本中提取
        text = str(data)
        prob_match = re.search(r'(\d+)%', text)
        if prob_match:
            return int(prob_match.group(1))
        
        return None
    
    def _parse_float(self, value: Any) -> Optional[float]:
        """安全解析浮点数"""
        if value is None:
            return None
        try:
            return float(value)
        except:
            return None
    
    def _parse_trading_note(self, text: str) -> Optional[Dict]:
        """从文本提取交易信息（如 "75% chance of test of high"）"""
        if not text:
            return None
        
        signal = {}
        
        # 提取概率
        prob_match = re.search(r'(\d+)%', text)
        if prob_match:
            signal['probability'] = int(prob_match.group(1))
        
        # 提取方向
        if re.search(r'\b(buy|long|做多|买入)\b', text, re.I):
            signal['direction'] = 'long'
        elif re.search(r'\b(sell|short|做空|卖出)\b', text, re.I):
            signal['direction'] = 'short'
        
        # 提取目标
        if 'test of high' in text.lower() or 'test of high of day' in text.lower():
            signal['target'] = 'test_of_high_of_day'
        elif 'test of low' in text.lower() or 'test of low of day' in text.lower():
            signal['target'] = 'test_of_low_of_day'
        
        # 提取价格（如果提到）
        price_matches = re.findall(r'\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\b', text)
        if price_matches:
            prices = [self._parse_price(p) for p in price_matches if self._parse_price(p) and 40000 < self._parse_price(p) < 150000]
            if prices:
                signal['entry_price_hint'] = prices[0]  # 使用第一个合理的价格
        
        # 如果有概率或方向，返回信号
        if signal.get('probability') or signal.get('direction'):
            signal['entry_condition'] = text[:200]  # 保留原始文本
            return signal
        
        return None
    
    def _extract_text_notes(self, data: Dict) -> List[str]:
        """提取文本注释"""
        notes = data.get('text_notes', [])
        if isinstance(notes, str):
            return [notes]
        elif isinstance(notes, list):
            return [str(n) for n in notes]
        
        # 从raw字段提取
        if data.get('raw'):
            # 尝试从原始文本中提取关键句子
            raw_text = str(data['raw'])
            sentences = re.split(r'[.!?]\s+', raw_text)
            return [s.strip() for s in sentences if len(s.strip()) > 10][:5]  # 最多5句
        
        return []
    
    def _parse_market_conditions(self, data: Dict) -> Dict:
        """解析市场条件"""
        conditions = data.get('market_conditions', {})
        
        if not conditions:
            # 从其他字段推断
            conditions = {
                'context': data.get('context_text', '')[:200],
                'trend_strength': 'unknown',
                'volatility': 'unknown',
                'key_levels': []
            }
        
        # 确保key_levels是列表
        if isinstance(conditions.get('key_levels'), str):
            conditions['key_levels'] = [conditions['key_levels']]
        
        return {
            'context': conditions.get('context', ''),
            'trend_strength': conditions.get('trend_strength', 'unknown'),
            'volatility': conditions.get('volatility', 'unknown'),
            'key_levels': conditions.get('key_levels', [])
        }
    
    def _parse_annotations(self, data: Dict) -> List[Dict]:
        """解析图表标注"""
        annotations = data.get('annotations', [])
        
        if isinstance(annotations, list):
            return [
                {
                    'label': str(ann.get('label', '')),
                    'description': str(ann.get('description', ann.get('text', ''))),
                    'price': self._parse_price(ann.get('price'))
                }
                for ann in annotations if isinstance(ann, dict)
            ]
        
        return []


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='智能解析Gemini Vision API输出')
    parser.add_argument('--input', type=str, required=True, help='输入JSONL文件（Gemini分析结果）')
    parser.add_argument('--output', type=str, help='输出JSONL文件（解析后的标准化结果）')
    parser.add_argument('--verify', action='store_true', help='验证解析结果')
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"错误: 输入文件不存在: {input_file}", file=sys.stderr)
        return 1
    
    output_file = Path(args.output) if args.output else input_file.parent / f"{input_file.stem}_parsed.jsonl"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    parser_obj = GeminiOutputParser()
    
    total = 0
    parsed = 0
    errors = 0
    
    print(f"开始解析: {input_file}")
    print(f"输出文件: {output_file}\n")
    
    with output_file.open('w', encoding='utf-8') as out_f:
        with input_file.open('r', encoding='utf-8') as in_f:
            for line_num, line in enumerate(in_f, 1):
                try:
                    record = json.loads(line)
                    total += 1
                    
                    # 解析Gemini结果
                    gemini_result = record.get('result', {})
                    parsed_ann = parser_obj.parse(gemini_result)
                    
                    # 构建输出记录
                    output_record = {
                        'image': record.get('image'),
                        'sha1': record.get('sha1'),
                        'page': record.get('page'),
                        'parsed': {
                            'patterns': [asdict(p) if hasattr(p, '__dict__') else p for p in parsed_ann.patterns],
                            'pattern_combination': parsed_ann.pattern_combination,
                            'price_action_behavior': parsed_ann.price_action_behavior,
                            'trading_signals': parsed_ann.trading_signals,
                            'market_conditions': parsed_ann.market_conditions,
                            'annotations': parsed_ann.annotations,
                            'text_notes': parsed_ann.text_notes,
                            'confidence': parsed_ann.confidence
                        },
                        'parse_errors': parsed_ann.parse_errors,
                        'original': gemini_result  # 保留原始结果
                    }
                    
                    # 验证（可选）
                    if args.verify:
                        if parsed_ann.parse_errors:
                            errors += 1
                            print(f"  行 {line_num}: 解析错误 - {parsed_ann.parse_errors}")
                    
                    out_f.write(json.dumps(output_record, ensure_ascii=False) + '\n')
                    parsed += 1
                    
                    if line_num % 100 == 0:
                        print(f"  已解析: {parsed}/{total} (错误: {errors})")
                
                except Exception as e:
                    print(f"  行 {line_num}: 处理失败 - {e}", file=sys.stderr)
                    errors += 1
                    continue
    
    print(f"\n解析完成:")
    print(f"  总计: {total}")
    print(f"  成功: {parsed}")
    print(f"  错误: {errors}")
    print(f"  输出: {output_file}")
    
    return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

