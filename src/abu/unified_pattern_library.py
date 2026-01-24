#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一模式库 - ABU系统v3.0

整合三个数据源：
1. Gemini Flash模式（1000个）- 从pattern_library表加载
2. Cursor AI模式（300个）- 从识别结果文件加载
3. Brooks规则 - 从ebook_knowledge_base表加载

功能：
- 统一模式索引结构
- 特征标准化
- 多源模式搜索
- 向量索引（可选）
"""

from __future__ import annotations
import sys
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
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

# 权重配置（根据文档决策）
SOURCE_WEIGHTS = {
    'cursor_ai': 0.5,
    'brooks_rule': 0.3,
    'gemini_flash': 0.2,
    'gemini_pro': 0.2,
    'gemini_pro3': 0.2,
}


@dataclass
class UnifiedPattern:
    """统一模式数据结构"""
    pattern_id: str  # 统一ID：{source}_{original_id}
    source: str  # 'gemini_flash' | 'gemini_pro' | 'gemini_pro3' | 'cursor_ai' | 'brooks_rule'
    original_id: Any  # 原始ID（可能是int或str）
    
    # 基本信息
    pattern_name: str
    pattern_type: str
    direction: str  # 'long' | 'short' | 'neutral'
    confidence: float  # 0.0-1.0
    
    # 标准化特征
    structured_features: Dict[str, Any]
    
    # 原始数据（保留用于调试和详细分析）
    raw_data: Dict[str, Any]
    
    # 元数据
    image_path: Optional[str] = None
    page_number: Optional[int] = None
    created_at: Optional[str] = None
    probability_score: Optional[int] = None  # 概率分数（0-100），来自Brooks概率分类
    probability_source: Optional[str] = None  # 概率来源（如'brooks_probability'）
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UnifiedPattern':
        """从字典创建"""
        return cls(**data)


class UnifiedPatternLibrary:
    """统一模式库"""
    
    def __init__(self, trader_id: str = 'abu'):
        """
        初始化统一模式库
        
        Args:
            trader_id: 交易员ID，用于数据库连接
        """
        if not DB_AVAILABLE:
            raise RuntimeError("数据库模块不可用")
        
        self.trader_id = trader_id
        self.db = TraderDBManager(trader_id)
        
        # 模式存储
        self.patterns: Dict[str, UnifiedPattern] = {}  # {pattern_id: UnifiedPattern}
        self.source_map: Dict[str, List[str]] = {  # {source: [pattern_ids]}
            'gemini_flash': [],
            'gemini_pro': [],
            'gemini_pro3': [],
            'cursor_ai': [],
            'brooks_rule': []
        }
        
        # 向量索引（可选，需要安装annoy）
        self.vector_index = None
        self.vector_index_manager = None
        self.use_vector_index = False
        
        # 概率规则映射 {pattern_name: {probability, source, ...}}
        self.probability_rules: Dict[str, Dict] = {}
        self._load_probability_rules()
        self._check_vector_index_available()
        
        # 统计信息
        self.stats = {
            'total': 0,
            'gemini_flash': 0,
            'gemini_pro': 0,
            'gemini_pro3': 0,
            'cursor_ai': 0,
            'brooks_rule': 0,
            'loaded_at': None
        }
    
    def _check_vector_index_available(self):
        """检查向量索引是否可用"""
        try:
            from abu.vector_index_manager import VectorIndexManager
            from abu.feature_vectorizer import FeatureVectorizer
            self.vector_index_available = True
        except ImportError:
            self.vector_index_available = False
    
    def load_all_patterns(self, 
                         load_gemini: bool = True,
                         load_cursor_ai: bool = True,
                         load_brooks: bool = True) -> Dict[str, int]:
        """
        加载所有模式库
        
        Args:
            load_gemini: 是否加载Gemini Flash模式
            load_cursor_ai: 是否加载Cursor AI模式
            load_brooks: 是否加载Brooks规则
        
        Returns:
            加载统计信息
        """
        print("=" * 80)
        print("加载统一模式库")
        print("=" * 80)
        print()
        
        if load_gemini:
            print("1. 加载Gemini模式...")
            self._load_gemini_flash_patterns()
            gemini_total = (
                self.stats.get('gemini_flash', 0)
                + self.stats.get('gemini_pro', 0)
                + self.stats.get('gemini_pro3', 0)
            )
            print(f"   [OK] 加载了 {gemini_total} 个Gemini模式")
            if self.stats.get('gemini_pro3'):
                print(f"      - Gemini Pro3: {self.stats.get('gemini_pro3')}")
            if self.stats.get('gemini_pro'):
                print(f"      - Gemini Pro: {self.stats.get('gemini_pro')}")
            if self.stats.get('gemini_flash'):
                print(f"      - Gemini Flash: {self.stats.get('gemini_flash')}")
            print()
        
        if load_cursor_ai:
            print("2. 加载Cursor AI模式...")
            count = self._load_cursor_ai_patterns()
            self.stats['cursor_ai'] = count
            print(f"   [OK] 加载了 {count} 个Cursor AI模式")
            print()
        
        if load_brooks:
            print("3. 加载Brooks规则...")
            count = self._load_brooks_rules()
            self.stats['brooks_rule'] = count
            print(f"   [OK] 加载了 {count} 个Brooks规则")
            print()
        
        self.stats['total'] = len(self.patterns)
        self.stats['loaded_at'] = datetime.now().isoformat()
        
        print("=" * 80)
        print(f"加载完成: 总计 {self.stats['total']} 个模式")
        print(f"  - Gemini Flash: {self.stats.get('gemini_flash', 0)}")
        print(f"  - Gemini Pro: {self.stats.get('gemini_pro', 0)}")
        print(f"  - Gemini Pro3: {self.stats.get('gemini_pro3', 0)}")
        print(f"  - Cursor AI: {self.stats['cursor_ai']}")
        print(f"  - Brooks规则: {self.stats['brooks_rule']}")
        print("=" * 80)
        
        # （可选）建立向量索引
        if self.vector_index_available and self.use_vector_index:
            self._build_vector_index()
        
        return self.stats
    
    def _build_vector_index(self):
        """建立向量索引（可选）"""
        try:
            from abu.vector_index_manager import VectorIndexManager
            from abu.feature_vectorizer import FeatureVectorizer
            
            print("\n建立向量索引...")
            self.vector_index_manager = VectorIndexManager(n_trees=10)
            
            # 准备模式数据
            pattern_data = []
            for pattern_id, pattern in self.patterns.items():
                pattern_data.append({
                    'pattern_id': pattern_id,
                    'structured_features': pattern.structured_features
                })
            
            # 建立索引
            self.vector_index_manager.build_index(pattern_data)
            self.use_vector_index = True
            print("向量索引建立完成")
        except Exception as e:
            print(f"[WARN] 向量索引建立失败: {e}，将使用线性搜索")
            self.use_vector_index = False
    
    def _load_gemini_flash_patterns(self) -> int:
        """从数据库加载Gemini Flash模式（只读操作）"""
        # 使用只读连接，允许多进程同时读取
        conn = self.db._get_connection(read_only=True)
        
        query = '''
            SELECT id, pattern_name, pattern_type, gemini_annotation_json,
                   direction, confidence, image_path, source_page
            FROM pattern_library
            WHERE gemini_annotation_json IS NOT NULL 
              AND gemini_annotation_json != ''
            ORDER BY id
        '''
        
        results = conn.execute(query).fetchall()
        count = 0
        self.stats['gemini_flash'] = 0
        self.stats['gemini_pro'] = 0
        self.stats['gemini_pro3'] = 0
        
        for row in results:
            pattern_id, pattern_name, pattern_type, gemini_json, \
            direction, confidence, image_path, source_page = row
            
            try:
                gemini_annotation = json.loads(gemini_json) if gemini_json else {}
                meta = gemini_annotation.get('_meta') or gemini_annotation.get('meta')
                model = None
                if isinstance(meta, dict):
                    model = meta.get('gemini_model') or meta.get('model')
                if not model:
                    model = gemini_annotation.get('gemini_model') or gemini_annotation.get('model')
                source = 'gemini_flash'
                if model:
                    model_lower = str(model).lower()
                    if 'pro' in model_lower and ('3.0' in model_lower or '3' in model_lower):
                        source = 'gemini_pro3'
                    elif 'pro' in model_lower:
                        source = 'gemini_pro'
                    elif 'flash' in model_lower:
                        source = 'gemini_flash'
                
                # 生成统一ID
                unified_id = f"{source}_{pattern_id}"
                
                # 标准化特征
                structured_features = self._standardize_gemini_features(
                    gemini_annotation, pattern_type, direction, pattern_name
                )
                
                # 创建统一模式
                norm_type = structured_features.get('pattern_type', pattern_type) or 'unknown'
                pattern = UnifiedPattern(
                    pattern_id=unified_id,
                    source=source,
                    original_id=pattern_id,
                    pattern_name=pattern_name or f"Pattern_{pattern_id}",
                    pattern_type=norm_type,
                    direction=direction or 'neutral',
                    confidence=float(confidence) if confidence else 0.5,
                    structured_features=structured_features,
                    raw_data={
                        'gemini_annotation': gemini_annotation,
                        'original_fields': {
                            'pattern_name': pattern_name,
                            'pattern_type': pattern_type,
                            'direction': direction,
                            'confidence': confidence
                        }
                    },
                    image_path=image_path,
                    page_number=source_page
                )
                
                # 添加到索引
                self.patterns[unified_id] = pattern
                self.source_map.setdefault(source, []).append(unified_id)
                count += 1
                self.stats[source] = self.stats.get(source, 0) + 1
                
            except Exception as e:
                print(f"   [WARN] 解析模式 {pattern_id} 失败: {e}", file=sys.stderr)
                continue
        
        return count
    
    def _load_probability_rules(self):
        """加载Brooks概率分类规则"""
        try:
            prob_file = ROOT / 'data' / 'brooks_probability_rules.json'
            if prob_file.exists():
                with open(prob_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 处理不同格式的数据
                    if isinstance(data, dict) and 'rules' in data:
                        rules = data['rules']
                    elif isinstance(data, list):
                        rules = data
                    else:
                        rules = []
                    
                    # 建立pattern_name -> probability映射
                    for rule in rules:
                        pattern_name = rule.get('pattern_name', '')
                        if pattern_name:
                            self.probability_rules[pattern_name] = {
                                'probability': rule.get('probability'),
                                'source': 'brooks_probability',
                                'page': rule.get('page'),
                                'text': rule.get('text', '')[:200]
                            }
        except Exception:
            # 静默失败，不影响主流程
            pass
    
    def _load_cursor_ai_patterns(self) -> int:
        """从识别结果文件加载Cursor AI模式"""
        # Cursor AI识别结果目录
        results_dir = ROOT / 'outputs' / 'cursor_ai_recognition' / 'results'
        features_dir = ROOT / 'outputs' / 'cursor_ai_recognition' / 'structured_features'
        
        if not results_dir.exists() and not features_dir.exists():
            print(f"   [WARN] Cursor AI结果目录不存在: {results_dir}")
            return 0
        
        count = 0
        
        # 优先从结构化特征目录加载（如果已提取）
        if features_dir.exists():
            feature_files = list(features_dir.glob('*.json'))
            for feature_file in feature_files:
                try:
                    with feature_file.open('r', encoding='utf-8') as f:
                        features = json.load(f)
                    
                    # 生成统一ID（基于文件名）
                    file_stem = feature_file.stem
                    unified_id = f"cursor_ai_{file_stem}"
                    
                    # 标准化特征
                    structured_features = self._standardize_cursor_ai_features(features)
                    
                    # 提取基本信息
                    pattern_name = features.get('pattern_name') or features.get('pattern_type') or 'Unknown'
                    pattern_type = self._normalize_pattern_type(
                        features.get('pattern_type') or features.get('pattern_subtype'),
                        pattern_name=pattern_name
                    )
                    direction = (features.get('direction') or 'neutral').lower()
                    confidence = float(features.get('confidence', 0.5))
                    
                    # 创建统一模式
                    pattern = UnifiedPattern(
                        pattern_id=unified_id,
                        source='cursor_ai',
                        original_id=file_stem,
                        pattern_name=pattern_name,
                        pattern_type=pattern_type,
                        direction=direction,
                        confidence=confidence,
                        structured_features=structured_features,
                        raw_data={
                            'cursor_ai_features': features,
                            'source_file': feature_file.name
                        }
                    )
                    
                    # 添加到索引
                    self.patterns[unified_id] = pattern
                    self.source_map['cursor_ai'].append(unified_id)
                    count += 1
                    
                except Exception as e:
                    print(f"   [WARN] 加载Cursor AI模式 {feature_file.name} 失败: {e}", file=sys.stderr)
                    continue
        
        # 如果结构化特征不存在，尝试从原始结果文件提取
        elif results_dir.exists():
            # 这里可以调用extract_structured_features的逻辑
            # 为了简化，先跳过，建议先运行extract_structured_features.py
            print(f"   [WARN] 未找到结构化特征，请先运行 scripts/extract_structured_features.py")
        
        return count
    
    def _load_brooks_rules(self) -> int:
        """从电子书知识库加载Brooks规则（只读操作）"""
        # 使用只读连接，允许多进程同时读取
        conn = self.db._get_connection(read_only=True)
        
        # 查询有交易规则的电子书条目
        query = '''
            SELECT id, book_title, chapter_title, section_title,
                   trading_rules_json, content_text, extracted_patterns,
                   key_concepts, related_image_path, page_number
            FROM ebook_knowledge_base
            WHERE trading_rules_json IS NOT NULL 
              AND trading_rules_json != ''
            ORDER BY id
        '''
        
        results = conn.execute(query).fetchall()
        count = 0
        
        for row in results:
            item_id, book_title, chapter_title, section_title, \
            rules_json, content_text, extracted_patterns, \
            key_concepts, image_path, page_number = row
            
            try:
                trading_rules = json.loads(rules_json) if rules_json else {}
                
                # 解析提取的模式
                patterns_list = []
                if extracted_patterns:
                    try:
                        patterns_list = json.loads(extracted_patterns)
                    except:
                        pass
                
                # 为每个模式创建规则条目
                if not patterns_list:
                    patterns_list = ['Brooks_Rule']  # 默认名称
                
                for pattern_name in patterns_list:
                    # 生成统一ID
                    unified_id = f"brooks_rule_{item_id}_{hashlib.md5(pattern_name.encode()).hexdigest()[:8]}"
                    
                    # 标准化特征
                    structured_features = self._standardize_brooks_features(
                        trading_rules, content_text, key_concepts, pattern_name
                    )
                    
                    # 尝试从概率规则中获取概率分数
                    probability_score = None
                    probability_source = None
                    if pattern_name in self.probability_rules:
                        prob_rule = self.probability_rules[pattern_name]
                        probability_score = prob_rule.get('probability')
                        probability_source = 'brooks_probability'
                    
                    # 创建统一模式
                    pattern = UnifiedPattern(
                        pattern_id=unified_id,
                        source='brooks_rule',
                        original_id=item_id,
                        pattern_name=pattern_name,
                        pattern_type='brooks_rule',
                        direction=self._infer_direction_from_rules(trading_rules),
                        confidence=0.7,  # Brooks规则默认置信度
                        structured_features=structured_features,
                        raw_data={
                            'trading_rules': trading_rules,
                            'content_text': content_text[:500] if content_text else '',
                            'book_title': book_title,
                            'chapter_title': chapter_title,
                            'section_title': section_title,
                            'key_concepts': json.loads(key_concepts) if key_concepts else []
                        },
                        image_path=image_path,
                        page_number=page_number,
                        probability_score=probability_score,
                        probability_source=probability_source
                    )
                    
                    # 添加到索引
                    self.patterns[unified_id] = pattern
                    self.source_map['brooks_rule'].append(unified_id)
                    count += 1
                
            except Exception as e:
                print(f"   [WARN] 加载Brooks规则 {item_id} 失败: {e}", file=sys.stderr)
                continue
        
        return count
    
    def _normalize_kline_features(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(v) for v in value if v]
        if isinstance(value, dict):
            return [str(k) for k in value.keys()]
        if isinstance(value, str):
            return [value]
        return []

    def _normalize_pattern_type(self, value: Any, pattern_name: Optional[str] = None) -> str:
        raw = ''
        if isinstance(value, list):
            raw = ' '.join(str(v) for v in value if v)
        elif isinstance(value, dict):
            raw = value.get('pattern_type') or value.get('type') or ''
        elif value is not None:
            raw = str(value)

        raw = raw.strip().lower()
        raw = raw.replace('-', ' ').replace('/', ' ')
        raw = ' '.join(raw.split())

        if not raw and pattern_name:
            raw = str(pattern_name).strip().lower()
            raw = raw.replace('-', ' ').replace('/', ' ')
            raw = ' '.join(raw.split())

        if 'major trend reversal' in raw or 'major_trend_reversal' in raw:
            return 'major_trend_reversal'
        if 'double top' in raw or 'double_top' in raw:
            return 'double_top'
        if 'double bottom' in raw or 'double_bottom' in raw:
            return 'double_bottom'
        if 'wedge' in raw:
            return 'wedge'
        if 'triangle' in raw:
            return 'triangle'
        if 'inside bar' in raw or 'inside_bar' in raw:
            return 'breakout'
        if 'engulf' in raw or 'pin bar' in raw or 'pinbar' in raw or 'reversal' in raw:
            return 'reversal'
        if 'bull' in raw and 'breakout' in raw:
            return 'bull_breakout'
        if 'bear' in raw and 'breakout' in raw:
            return 'bear_breakout'
        if 'breakout' in raw:
            return 'breakout'
        if 'trading range' in raw or 'trading_range' in raw or 'range' in raw:
            return 'trading_range'
        if 'bull trend' in raw or 'bear trend' in raw or 'trend' in raw:
            return 'trend'
        if 'continuation' in raw:
            return 'continuation'
        if raw in ('informational', 'analysis_chart', 'educational', 'other'):
            return 'informational'
        if raw:
            return raw.replace(' ', '_')
        return 'unknown'

    def _standardize_gemini_features(self, gemini_annotation: Dict, 
                                   pattern_type: Optional[str],
                                   direction: Optional[str],
                                   pattern_name: Optional[str] = None) -> Dict:
        """标准化Gemini特征"""
        parsed = gemini_annotation.get('parsed', gemini_annotation)
        raw_type = pattern_type or parsed.get('pattern_type')
        if not raw_type:
            patterns = parsed.get('patterns') or []
            if patterns:
                first = patterns[0]
                if isinstance(first, dict):
                    raw_type = first.get('pattern_type') or first.get('pattern_name') or first.get('type')
                elif isinstance(first, str):
                    raw_type = first
        norm_type = self._normalize_pattern_type(raw_type, pattern_name=pattern_name)
        kline_features = self._normalize_kline_features(parsed.get('price_action_behavior', {}).get('kline_features', []))
        norm_direction = (direction or parsed.get('direction') or 'neutral').lower()
        
        return {
            'kline_features': kline_features,
            'trend': parsed.get('price_action_behavior', {}).get('trend', 'neutral'),
            'structure': parsed.get('price_action_behavior', {}).get('structure', 'neutral'),
            'market_conditions': parsed.get('market_conditions', {}),
            'patterns': parsed.get('patterns', []),
            'trading_signals': parsed.get('trading_signals', []),
            'pattern_type': norm_type,
            'direction': norm_direction
        }
    
    def _standardize_cursor_ai_features(self, features: Dict) -> Dict:
        """标准化Cursor AI特征"""
        pattern_name = features.get('pattern_name') or ''
        raw_type = features.get('pattern_type') or features.get('pattern_subtype')
        norm_type = self._normalize_pattern_type(raw_type, pattern_name=pattern_name)
        kline_features = self._normalize_kline_features(features.get('kline_features', {}))
        return {
            'kline_features': kline_features,
            'price_levels': features.get('price_levels', {}),
            'pattern_structure': features.get('pattern_structure', {}),
            'trading_signals': features.get('trading_signals', []),
            'quantified_indicators': features.get('quantified_indicators', {}),
            'market_conditions': features.get('market_conditions', {}),
            'pattern_type': norm_type,
            'direction': (features.get('direction') or 'neutral').lower()
        }
    
    def _standardize_brooks_features(self, trading_rules: Dict, 
                                    content_text: Optional[str],
                                    key_concepts: Optional[str],
                                    pattern_name: str) -> Dict:
        """标准化Brooks规则特征"""
        concepts_list = []
        if key_concepts:
            try:
                concepts_list = json.loads(key_concepts)
            except:
                pass
        
        return {
            'trading_rules': trading_rules,
            'key_concepts': concepts_list,
            'pattern_name': pattern_name,
            'pattern_type': 'brooks_rule',
            'content_summary': content_text[:200] if content_text else ''
        }
    
    def _infer_direction_from_rules(self, trading_rules: Dict) -> str:
        """从交易规则推断方向"""
        rules_str = json.dumps(trading_rules).lower()
        
        if any(kw in rules_str for kw in ['long', 'buy', 'bull', 'up']):
            return 'long'
        elif any(kw in rules_str for kw in ['short', 'sell', 'bear', 'down']):
            return 'short'
        else:
            return 'neutral'
    
    def search_patterns(self, 
                       query_features: Dict,
                       sources: Optional[List[str]] = None,
                       top_k: int = 10,
                       min_confidence: float = 0.0,
                       use_vector_index: Optional[bool] = None) -> List[Dict]:
        """
        搜索相似模式
        
        Args:
            query_features: 查询特征（标准化格式）
            sources: 数据源列表，None表示所有源
            top_k: 返回Top K结果
            min_confidence: 最小置信度阈值
            use_vector_index: 是否使用向量索引（None表示自动选择）
        
        Returns:
            匹配结果列表，每个包含模式信息和相似度分数
        """
        # 决定是否使用向量索引
        if use_vector_index is None:
            use_vector_index = self.use_vector_index and self.vector_index_available
        
        # 如果使用向量索引且可用
        if use_vector_index and self.vector_index_manager and self.vector_index_manager.built:
            return self._search_with_vector_index(query_features, sources, top_k, min_confidence)
        
        # 否则使用线性搜索
        if sources is None:
            sources = ['gemini_flash', 'gemini_pro', 'gemini_pro3', 'cursor_ai', 'brooks_rule']
        
        matches = []
        
        # 遍历指定数据源的模式
        for source in sources:
            if source not in self.source_map:
                continue
            
            for pattern_id in self.source_map[source]:
                pattern = self.patterns[pattern_id]
                
                # 跳过低置信度模式
                if pattern.confidence < min_confidence:
                    continue
                
                # 计算相似度（简化版，后续可以优化）
                similarity = self._calculate_similarity(query_features, pattern.structured_features)
                
                if similarity > 0:
                    matches.append({
                        'pattern_id': pattern_id,
                        'pattern': pattern.to_dict(),
                        'similarity': similarity,
                        'source': source,
                        'weight': SOURCE_WEIGHTS.get(source, 0.1)
                    })
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return matches[:top_k]
    
    def _calculate_similarity(self, query_features: Dict, pattern_features: Dict) -> float:
        """
        计算相似度（增强版，支持Brooks规则）
        
        支持：
        1. 标准特征匹配（Gemini Flash, Cursor AI）
        2. Brooks规则特征匹配（文本相似度）
        3. 向量相似度（如果可用）
        """
        score = 0.0
        factors = 0
        
        # 检测是否为Brooks规则特征
        is_brooks = pattern_features.get('pattern_type', '').lower() == 'brooks_rule' or \
                   'trading_rules' in pattern_features or \
                   'key_concepts' in pattern_features
        
        if is_brooks:
            # Brooks规则专用匹配逻辑
            return self._calculate_brooks_similarity(query_features, pattern_features)
        
        # 标准特征匹配（Gemini Flash, Cursor AI）
        # 1. 模式类型匹配
        query_type = query_features.get('pattern_type', '').lower()
        pattern_type = pattern_features.get('pattern_type', '').lower()
        if query_type and pattern_type:
            if query_type == pattern_type:
                score += 1.0
                factors += 1.0
            elif query_type in pattern_type or pattern_type in query_type:
                score += 0.5
                factors += 1.0
        
        # 2. 方向匹配
        query_dir = query_features.get('direction', 'neutral').lower()
        pattern_dir = pattern_features.get('direction', 'neutral').lower()
        if query_dir == pattern_dir:
            score += 0.5
            factors += 0.5
        
        # 3. K线特征匹配（简化）
        query_kline = query_features.get('kline_features', [])
        pattern_kline = pattern_features.get('kline_features', [])
        if query_kline and pattern_kline:
            # 处理列表类型
            if isinstance(query_kline, list) and isinstance(pattern_kline, list):
                # 转换为字符串集合以便比较
                query_set = set(str(f) for f in query_kline if isinstance(f, (str, int, float)))
                pattern_set = set(str(f) for f in pattern_kline if isinstance(f, (str, int, float)))
                if query_set and pattern_set:
                    common = query_set & pattern_set
                    if common:
                        score += 0.3 * (len(common) / max(len(query_set), len(pattern_set)))
                        factors += 0.3
            # 处理字典类型
            elif isinstance(query_kline, dict) and isinstance(pattern_kline, dict):
                # 比较字典键
                query_keys = set(query_kline.keys())
                pattern_keys = set(pattern_kline.keys())
                if query_keys and pattern_keys:
                    common = query_keys & pattern_keys
                    if common:
                        score += 0.3 * (len(common) / max(len(query_keys), len(pattern_keys)))
                        factors += 0.3
        
        # 4. 趋势匹配
        query_trend = query_features.get('trend', '').lower()
        pattern_trend = pattern_features.get('trend', '').lower()
        if query_trend and pattern_trend:
            if query_trend == pattern_trend:
                score += 0.2
                factors += 0.2
        
        # 归一化
        if factors > 0:
            score = score / factors
        
        return min(1.0, max(0.0, score))
    
    def _calculate_brooks_similarity(self, query_features: Dict, pattern_features: Dict) -> float:
        """
        计算Brooks规则的相似度（基于文本和概念匹配）
        """
        score = 0.0
        factors = 0
        
        # 1. 方向匹配（从Brooks规则推断方向）
        query_dir = query_features.get('direction', 'neutral').lower()
        pattern_name = pattern_features.get('pattern_name', '').lower()
        content_summary = pattern_features.get('content_summary', '').lower()
        key_concepts = pattern_features.get('key_concepts', [])
        
        # 从Brooks规则推断方向
        brooks_text = f"{pattern_name} {content_summary} {' '.join(str(kc).lower() for kc in key_concepts)}"
        brooks_dir = 'neutral'
        if any(kw in brooks_text for kw in ['long', 'buy', 'bull', 'up', '做多', '买入']):
            brooks_dir = 'long'
        elif any(kw in brooks_text for kw in ['short', 'sell', 'bear', 'down', '做空', '卖出']):
            brooks_dir = 'short'
        
        if query_dir == brooks_dir and query_dir != 'neutral':
            score += 0.4
            factors += 0.4
        
        # 2. 趋势匹配（从查询特征推断）
        query_trend = query_features.get('trend', '').lower()
        if query_trend:
            if query_trend == 'bullish' and ('bull' in brooks_text or 'up' in brooks_text or 'long' in brooks_text):
                score += 0.3
                factors += 0.3
            elif query_trend == 'bearish' and ('bear' in brooks_text or 'down' in brooks_text or 'short' in brooks_text):
                score += 0.3
                factors += 0.3
        
        # 3. 模式名称关键词匹配
        query_type = query_features.get('pattern_type', '').lower()
        if query_type and query_type != 'unknown':
            # 检查Brooks规则的模式名称是否包含查询类型的关键词
            pattern_keywords = ['wedge', 'triangle', 'channel', 'trend', 'range', 'breakout', 'pullback']
            for keyword in pattern_keywords:
                if keyword in query_type and keyword in pattern_name:
                    score += 0.2
                    factors += 0.2
                    break
        
        # 4. K线特征关键词匹配（如果Brooks规则提到了相关概念）
        query_kline = query_features.get('kline_features', [])
        if query_kline:
            kline_keywords = ['engulfing', 'inside', 'bar', 'candle']
            for kline_feat in query_kline:
                if isinstance(kline_feat, str):
                    for keyword in kline_keywords:
                        if keyword in kline_feat.lower() and keyword in brooks_text:
                            score += 0.1
                            factors += 0.1
                            break
        
        # 5. 市场条件匹配
        query_volatility = query_features.get('volatility', 0)
        market_conditions = query_features.get('market_conditions', {})
        volatility_level = market_conditions.get('volatility', '').lower()
        
        if volatility_level:
            if volatility_level == 'high' and ('volatile' in brooks_text or 'high' in brooks_text):
                score += 0.1
                factors += 0.1
            elif volatility_level == 'low' and ('low' in brooks_text or 'quiet' in brooks_text):
                score += 0.1
                factors += 0.1
        
        # 归一化（如果factors为0，返回基础分数）
        if factors > 0:
            score = score / factors
        else:
            # 如果没有匹配，给一个基础分数（基于方向匹配）
            if query_dir != 'neutral':
                score = 0.2  # 基础分数
        
        return min(1.0, max(0.0, score))
    
    def _search_with_vector_index(
        self,
        query_features: Dict,
        sources: Optional[List[str]],
        top_k: int,
        min_confidence: float
    ) -> List[Dict]:
        """
        使用向量索引搜索（快速）
        
        Args:
            query_features: 查询特征
            sources: 数据源列表
            top_k: 返回Top K结果
            min_confidence: 最小置信度阈值
        
        Returns:
            匹配结果列表
        """
        # 使用向量索引搜索
        vector_results = self.vector_index_manager.search(query_features, top_k=top_k * 2)
        
        matches = []
        for pattern_id, similarity in vector_results:
            pattern = self.patterns.get(pattern_id)
            if not pattern:
                continue
            
            # 过滤数据源
            if sources and pattern.source not in sources:
                continue
            
            # 过滤置信度
            if pattern.confidence < min_confidence:
                continue
            
            matches.append({
                'pattern_id': pattern_id,
                'pattern': pattern.to_dict(),
                'similarity': similarity,
                'source': pattern.source,
                'weight': 0.5 if pattern.source == 'cursor_ai' else 0.3 if pattern.source == 'brooks_rule' else 0.2
            })
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return matches[:top_k]
    
    def get_pattern(self, pattern_id: str) -> Optional[UnifiedPattern]:
        """根据ID获取模式"""
        return self.patterns.get(pattern_id)
    
    def get_patterns_by_source(self, source: str) -> List[UnifiedPattern]:
        """获取指定数据源的所有模式"""
        if source not in self.source_map:
            return []
        
        return [self.patterns[pid] for pid in self.source_map[source]]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            **self.stats,
            'source_distribution': {
                source: len(pattern_ids) 
                for source, pattern_ids in self.source_map.items()
            }
        }
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """测试函数"""
    import sys
    
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    
    # 创建统一模式库
    library = UnifiedPatternLibrary('abu')
    
    # 加载所有模式
    stats = library.load_all_patterns()
    
    # 显示统计信息
    print("\n统计信息:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    
    # 测试搜索
    print("\n测试搜索...")
    query_features = {
        'pattern_type': 'triangle',
        'direction': 'long',
        'kline_features': ['ascending_triangle']
    }
    
    results = library.search_patterns(query_features, top_k=5)
    print(f"\n找到 {len(results)} 个匹配:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['pattern']['pattern_name']} "
              f"(来源: {result['source']}, 相似度: {result['similarity']:.2f})")
    
    library.close()


if __name__ == '__main__':
    main()
