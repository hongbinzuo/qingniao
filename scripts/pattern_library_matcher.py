#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
模式库匹配器
将 PDF 中识别的模式库与实时价格图表匹配
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加 src 到路径
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from chart_patterns_detector import ChartPatternsDetector

class PatternLibraryMatcher:
    """模式库匹配器 - 将 PDF 识别模式与实时价格匹配"""
    
    def __init__(self):
        self.db = TraderDBManager('abu')
        self.detector = ChartPatternsDetector()
        
    def load_pattern_library(self, pattern_type: Optional[str] = None) -> List[Dict]:
        """从数据库加载模式库"""
        conn = self.db._get_connection()
        
        if pattern_type:
            query = '''
                SELECT id, pattern_name, pattern_type, key_features, 
                       timeframe_hint, direction, confidence, image_path
                FROM pattern_library 
                WHERE pattern_type = ?
                ORDER BY confidence DESC
            '''
            patterns = conn.execute(query, (pattern_type,)).fetchall()
        else:
            query = '''
                SELECT id, pattern_name, pattern_type, key_features, 
                       timeframe_hint, direction, confidence, image_path
                FROM pattern_library 
                WHERE pattern_type IS NOT NULL 
                  AND pattern_type != 'other'
                  AND pattern_type != ''
                ORDER BY pattern_type, confidence DESC
            '''
            patterns = conn.execute(query).fetchall()
        
        result = []
        for p in patterns:
            try:
                features = json.loads(p[3]) if p[3] else {}
            except:
                features = {}
            
            result.append({
                'id': p[0],
                'name': p[1],
                'type': p[2],
                'features': features,
                'timeframe': p[4],
                'direction': p[5],
                'confidence': p[6],
                'image_path': p[7]
            })
        
        return result
    
    def extract_pattern_features(self, pattern: Dict) -> Dict:
        """从模式记录中提取特征参数"""
        features = pattern.get('features', {})
        pattern_type = pattern.get('type', '')
        
        extracted = {
            'type': pattern_type,
            'direction': pattern.get('direction'),
            'timeframe': pattern.get('timeframe'),
            'confidence': pattern.get('confidence', 0),
        }
        
        # 根据不同模式类型提取特征
        if pattern_type == 'HeadAndShoulders':
            # 头肩顶特征
            extracted['shape'] = 'head_shoulders'
            extracted['key_points'] = ['left_shoulder', 'head', 'right_shoulder', 'neckline']
        elif pattern_type == 'Triangle':
            # 三角形特征
            extracted['shape'] = 'triangle'
            extracted['key_points'] = ['upper_bound', 'lower_bound', 'apex']
            # 可以从 features 中提取更多信息
            if isinstance(features, dict):
                concepts = features.get('concepts', [])
                if 'ascending' in str(concepts).lower():
                    extracted['triangle_type'] = 'ascending'
                elif 'descending' in str(concepts).lower():
                    extracted['triangle_type'] = 'descending'
                else:
                    extracted['triangle_type'] = 'symmetrical'
        elif pattern_type == 'InsideBar':
            # 内包线特征
            extracted['shape'] = 'inside_bar'
            extracted['key_points'] = ['mother_bar', 'inside_bar']
        else:
            extracted['shape'] = pattern_type.lower()
        
        return extracted
    
    def match_pattern_in_klines(self, pattern_features: Dict, klines: List[Dict]) -> Optional[Dict]:
        """在 K 线数据中匹配模式"""
        shape = pattern_features.get('shape', '')
        
        # 使用现有的检测器
        if shape == 'head_shoulders':
            if pattern_features.get('direction') == 'long':
                result = self.detector.detect_head_shoulders_bottom(klines)
            else:
                result = self.detector.detect_head_shoulders_top(klines)
            
            if result.get('detected'):
                return {
                    'matched': True,
                    'pattern_type': pattern_features['type'],
                    'confidence': result['confidence'],
                    'entry': result.get('entry'),
                    'stop_loss': result.get('stop_loss'),
                    'take_profit': result.get('take_profit'),
                    'details': result
                }
        
        elif shape == 'triangle':
            triangle_type = pattern_features.get('triangle_type', 'symmetrical')
            all_patterns = self.detector.detect_all_patterns(klines)
            
            # 检查三角形形态
            for pattern in all_patterns.get('continuation_patterns', []):
                if 'triangle' in pattern.get('name', '').lower():
                    if triangle_type == 'ascending' and '上升' in pattern.get('name', ''):
                        return {
                            'matched': True,
                            'pattern_type': pattern_features['type'],
                            'confidence': pattern.get('confidence', 0),
                            'entry': pattern.get('entry'),
                            'stop_loss': pattern.get('stop_loss'),
                            'take_profit': pattern.get('take_profit'),
                            'details': pattern
                        }
                    elif triangle_type == 'descending' and '下降' in pattern.get('name', ''):
                        return {
                            'matched': True,
                            'pattern_type': pattern_features['type'],
                            'confidence': pattern.get('confidence', 0),
                            'entry': pattern.get('entry'),
                            'stop_loss': pattern.get('stop_loss'),
                            'take_profit': pattern.get('take_profit'),
                            'details': pattern
                        }
                    elif triangle_type == 'symmetrical':
                        return {
                            'matched': True,
                            'pattern_type': pattern_features['type'],
                            'confidence': pattern.get('confidence', 0),
                            'entry': pattern.get('entry'),
                            'stop_loss': pattern.get('stop_loss'),
                            'take_profit': pattern.get('take_profit'),
                            'details': pattern
                        }
        
        elif shape == 'inside_bar':
            # 内包线检测（简化版）
            if len(klines) >= 2:
                current = klines[-1]
                previous = klines[-2]
                
                # 检查是否形成内包线
                if (current['high'] < previous['high'] and 
                    current['low'] > previous['low']):
                    direction = pattern_features.get('direction', 'long')
                    
                    return {
                        'matched': True,
                        'pattern_type': 'InsideBar',
                        'confidence': 60.0,
                        'entry': current['close'],
                        'stop_loss': current['low'] * 0.995 if direction == 'long' else current['high'] * 1.005,
                        'take_profit': current['high'] * 1.02 if direction == 'long' else current['low'] * 0.98,
                        'details': {
                            'mother_bar': previous,
                            'inside_bar': current
                        }
                    }
        
        return None
    
    def scan_real_time_patterns(self, symbol: str = 'BTC_USDT', 
                                timeframe: str = '5m',
                                limit: int = 200) -> List[Dict]:
        """扫描实时价格图表，匹配模式库中的模式"""
        # 获取实时K线数据
        try:
            from gate_scanner_bottom_formation import TechnicalPatternScanner
            scanner = TechnicalPatternScanner()
            df = scanner.get_daily_klines(symbol)
            
            if df is None or len(df) < 50:
                return []
            
            # 转换为K线格式
            klines = []
            for _, row in df.tail(limit).iterrows():
                klines.append({
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume']),
                    'timestamp': row.name.isoformat() if hasattr(row.name, 'isoformat') else str(row.name)
                })
        except Exception as e:
            print(f"获取K线数据失败: {e}", file=sys.stderr)
            return []
        
        # 加载模式库（按置信度排序）
        pattern_library = self.load_pattern_library()
        
        # 按类型分组
        by_type = {}
        for pattern in pattern_library:
            ptype = pattern['type']
            if ptype not in by_type:
                by_type[ptype] = []
            by_type[ptype].append(pattern)
        
        matched_patterns = []
        
        # 对每种类型的模式进行匹配
        for pattern_type, patterns in by_type.items():
            # 取每种类型置信度最高的前3个作为模板
            templates = sorted(patterns, key=lambda x: x.get('confidence', 0), reverse=True)[:3]
            
            for template in templates:
                features = self.extract_pattern_features(template)
                match_result = self.match_pattern_in_klines(features, klines)
                
                if match_result and match_result.get('matched'):
                    matched_patterns.append({
                        'template_id': template['id'],
                        'template_name': template['name'],
                        'template_type': template['type'],
                        'template_confidence': template.get('confidence', 0),
                        'matched_result': match_result,
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    break  # 每种类型只匹配第一个成功的
        
        return matched_patterns


def main():
    import argparse
    
    ap = argparse.ArgumentParser(description='模式库实时匹配器')
    ap.add_argument('--symbol', type=str, default='BTC_USDT', help='交易对符号')
    ap.add_argument('--timeframe', type=str, default='5m', help='时间框架')
    ap.add_argument('--pattern-type', type=str, help='特定模式类型（如 HeadAndShoulders, Triangle）')
    ap.add_argument('--list-library', action='store_true', help='列出模式库内容')
    args = ap.parse_args()
    
    matcher = PatternLibraryMatcher()
    
    if args.list_library:
        print("\n模式库内容:")
        print("=" * 80)
        patterns = matcher.load_pattern_library(args.pattern_type)
        
        by_type = {}
        for p in patterns:
            if p['type'] not in by_type:
                by_type[p['type']] = []
            by_type[p['type']].append(p)
        
        for ptype, plist in sorted(by_type.items()):
            print(f"\n【{ptype}】- {len(plist)} 个模式")
            for p in plist[:5]:  # 每种类型显示前5个
                conf = p.get('confidence') or 0
                conf_str = f"{conf:.2f}" if conf else "N/A"
                print(f"  ID={p['id']}, 置信度={conf_str}, "
                      f"方向={p.get('direction') or 'N/A'}, "
                      f"时间周期={p.get('timeframe') or 'N/A'}")
        
        print(f"\n总计: {len(patterns)} 个模式")
        return 0
    
    # 执行实时匹配
    print(f"\n扫描 {args.symbol} ({args.timeframe}) 实时图表...")
    print("=" * 80)
    
    matched = matcher.scan_real_time_patterns(
        symbol=args.symbol,
        timeframe=args.timeframe
    )
    
    if matched:
        print(f"\n找到 {len(matched)} 个匹配的模式:\n")
        for i, match in enumerate(matched, 1):
            result = match['matched_result']
            print(f"{i}. {match['template_type']} (模板ID: {match['template_id']})")
            print(f"   模板名称: {match['template_name']}")
            print(f"   匹配置信度: {result['confidence']:.1f}%")
            if result.get('entry'):
                print(f"   入场价: ${result['entry']:,.2f}")
            if result.get('stop_loss'):
                print(f"   止损价: ${result['stop_loss']:,.2f}")
            if result.get('take_profit'):
                print(f"   止盈价: ${result['take_profit']:,.2f}")
            print()
    else:
        print("\n未找到匹配的模式")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

