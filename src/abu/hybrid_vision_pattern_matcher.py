#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合视觉模式匹配器 - 结合算法筛选和AI视觉验证
"""
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
    from abu.chart_renderer import ChartRenderer
    from abu.ai_vision_matcher import AIVisionMatcher, VisionMatchResult
    from abu.vision_utils import resolve_pattern_image_path, render_chart_image
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"⚠️  导入失败: {e}")


@dataclass
class HybridMatchResult:
    """混合匹配结果"""
    pattern_id: int
    pattern_name: str
    pattern_type: str
    algorithm_score: float  # 算法匹配分数
    final_score: float  # 最终综合分数
    vision_score: Optional[float] = None  # AI视觉匹配分数（如果有）
    vision_result: Optional[VisionMatchResult] = None
    klines_rendered: bool = False  # 是否已渲染K线图


class HybridVisionPatternMatcher:
    """
    混合视觉模式匹配器（v3.0）
    
    工作流程：
    1. 使用算法快速筛选Top N候选（免费，快速）
    2. 对所有候选使用AI视觉匹配（v3.0特性，付费，精确）
    3. 综合评分，返回最终结果
    """
    
    def __init__(
        self,
        # 算法匹配器配置
        min_similarity: float = 0.5,
        max_candidates: int = 20,  # 算法筛选的候选数
        
        # 视觉匹配配置
        use_vision: bool = True,
        use_all_candidates: bool = True,  # 对所有候选使用视觉匹配（v3.0）
        vision_top_n: int = None,  # 如果use_all_candidates=False，对Top N使用视觉匹配
        vision_min_score: float = 0.6,  # 视觉匹配的最小分数阈值
        
        # 缓存配置
        enable_cache: bool = True,
        cache_ttl: int = 300,  # 缓存有效期（秒，5分钟）
        
        # 成本控制（仅当use_all_candidates=False时有效）
        max_vision_calls_per_scan: int = 20,  # 每次扫描最大视觉匹配次数
        
        # API配置
        vision_api_key: Optional[str] = None,
        vision_model: str = "google/gemini-2.5-flash-image",  # 或 "google/gemini-3-flash-preview"
        signal_completeness: str = "trade_ready"
    ):
        """
        初始化混合匹配器
        
        Args:
            min_similarity: 算法匹配的最小相似度
            max_candidates: 算法筛选的最大候选数
            use_vision: 是否使用AI视觉匹配
            use_all_candidates: 是否对所有候选使用视觉匹配（v3.0特性，默认True）
            vision_top_n: 如果use_all_candidates=False，对Top N候选使用视觉匹配
            vision_min_score: 视觉匹配的最小分数
            enable_cache: 是否启用缓存
            cache_ttl: 缓存有效期（秒）
            max_vision_calls_per_scan: 如果use_all_candidates=False，每次扫描最大视觉匹配次数
        """
        if not IMPORTS_AVAILABLE:
            raise ImportError("需要安装相关依赖")
        
        # 初始化算法匹配器
        self.algorithm_matcher = EnhancedGeminiPatternMatcher(
            min_confidence=0.0,
            exclude_other=False,
            require_trading_signals=True,
            exclude_unmarked=True,
            signal_completeness=signal_completeness
        )
        
        # 初始化图表渲染器（支持环境变量覆盖）
        chart_width = int(os.getenv("ABU_VISION_CHART_WIDTH", "2560") or 2560)
        chart_height = int(os.getenv("ABU_VISION_CHART_HEIGHT", "1440") or 1440)
        self.chart_renderer = ChartRenderer(
            width=chart_width,
            height=chart_height,
            style='dark_background'
        )
        
        # 初始化视觉匹配器（可选）
        self.vision_matcher = None
        if use_vision:
            try:
                self.vision_matcher = AIVisionMatcher(
                    api_key=vision_api_key,
                    model=vision_model
                )
                print("✓ AI视觉匹配器已启用")
            except Exception as e:
                print(f"⚠️  AI视觉匹配器初始化失败: {e}")
                print("   将只使用算法匹配")
                use_vision = False
        
        # 配置参数
        self.min_similarity = min_similarity
        self.max_candidates = max_candidates
        self.use_vision = use_vision and self.vision_matcher is not None
        self.use_all_candidates = use_all_candidates
        if use_all_candidates:
            self.vision_top_n = None  # 全部使用视觉匹配
        else:
            self.vision_top_n = min(vision_top_n or 5, max_vision_calls_per_scan)
        self.vision_min_score = vision_min_score
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.max_vision_calls_per_scan = max_vision_calls_per_scan
        
        # 缓存（简单的内存缓存）
        self.cache: Dict[str, Tuple[float, float]] = {}  # {cache_key: (score, timestamp)}
        
        # 临时目录
        self.temp_dir = Path("/tmp") / "qingniao_charts"
        if sys.platform == 'win32':
            # Windows使用用户临时目录
            self.temp_dir = Path(os.getenv('TEMP', os.getenv('TMP', '/tmp'))) / "qingniao_charts"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def match_patterns(
        self,
        klines_dict: Dict[str, List[Dict]],
        symbol: str = "BTC_USDT",
        timeframe: str = "15m"
    ) -> List[HybridMatchResult]:
        """
        混合模式匹配
        
        Args:
            klines_dict: K线数据字典，格式: {'5m': [...], '15m': [...]}
            symbol: 交易对符号
            timeframe: 主要时间框架
        
        Returns:
            匹配结果列表（按最终分数排序）
        """
        results = []
        
        # 步骤1: 算法快速筛选（免费，快速）
        print(f"[{symbol}] 步骤1: 算法快速筛选...", end=' ', flush=True)
        algorithm_matches = self.algorithm_matcher.match_patterns(
            klines_dict=klines_dict,
            min_similarity=self.min_similarity,
            max_matches=self.max_candidates
        )
        print(f"找到 {len(algorithm_matches)} 个候选")
        
        if not algorithm_matches:
            return results
        
        # 步骤2: AI视觉匹配（付费，精确）
        vision_matches = []
        if self.use_vision and len(algorithm_matches) > 0:
            # v3.0: 对所有候选使用视觉匹配，或对Top N使用
            if self.use_all_candidates:
                top_candidates = algorithm_matches  # 全部候选
                print(f"[{symbol}] 步骤2: AI视觉验证（全部 {len(top_candidates)} 个候选）...", end=' ', flush=True)
            else:
                top_candidates = algorithm_matches[:self.vision_top_n]  # Top N
                print(f"[{symbol}] 步骤2: AI视觉验证（Top {len(top_candidates)}）...", end=' ', flush=True)
            
            # 渲染实时K线图（只渲染一次）
            realtime_klines = klines_dict.get(timeframe, klines_dict.get('15m', []))
            if realtime_klines:
                cache_key = self._get_cache_key(symbol, timeframe, realtime_klines[-50:])
                
                # 检查缓存
                if self.enable_cache and cache_key in self.cache:
                    cached_score, cached_time = self.cache[cache_key]
                    if time.time() - cached_time < self.cache_ttl:
                        print("使用缓存")
                        # 使用缓存的视觉分数（简化处理）
                        for match in top_candidates:
                            vision_matches.append({
                                'pattern_id': match['pattern_id'],
                                'vision_score': cached_score
                            })
                    else:
                        # 缓存过期，删除
                        del self.cache[cache_key]
                
                if not vision_matches:
                    # 渲染K线图
                    chart_image_bytes = self.chart_renderer.render_klines_to_image(
                        realtime_klines,
                        title=f"{symbol} {timeframe} Chart"
                    )
                    
                    if chart_image_bytes:
                        # 保存临时图片
                        temp_chart_path = self._save_temp_chart(symbol, chart_image_bytes)
                        
                        # 对每个候选进行视觉匹配
                        for i, match in enumerate(top_candidates):
                            # 如果使用全部候选，不限制数量；否则限制为max_vision_calls_per_scan
                            if not self.use_all_candidates and i >= self.max_vision_calls_per_scan:
                                break
                            
                            try:
                                pattern = self._get_pattern_by_id(match['pattern_id'])
                                if not pattern:
                                    continue
                                pattern_image_path = self._resolve_pattern_image_path(pattern)
                                if not pattern_image_path:
                                    continue
                                
                                # AI视觉匹配
                                vision_result = self.vision_matcher.compare_two_images(
                                    image1_path=pattern_image_path,
                                    image2_path=temp_chart_path,
                                    context=f"Pattern: {pattern.get('pattern_name', '')}"
                                )
                                
                                vision_score = vision_result.similarity_score / 100.0
                                
                                vision_matches.append({
                                    'pattern_id': match['pattern_id'],
                                    'vision_score': vision_score,
                                    'vision_result': vision_result
                                })
                                
                                # 缓存结果（使用第一个匹配的分数作为缓存参考）
                                if i == 0 and self.enable_cache:
                                    self.cache[cache_key] = (vision_score, time.time())
                                
                            except Exception as e:
                                print(f"\n⚠️  视觉匹配失败 pattern_id={match['pattern_id']}: {e}")
                                continue
                        
                        # 清理临时文件
                        if temp_chart_path.exists():
                            try:
                                temp_chart_path.unlink()
                            except Exception:
                                pass
                    
                    print(f"完成 {len(vision_matches)} 个视觉匹配")
        
        # 步骤3: 综合评分
        print(f"[{symbol}] 步骤3: 综合评分...")
        vision_dict = {m['pattern_id']: m for m in vision_matches}
        
        for match in algorithm_matches:
            pattern_id = match['pattern_id']
            algorithm_score = match.get('similarity', 0)
            
            # 获取视觉分数（如果有）
            vision_data = vision_dict.get(pattern_id, {})
            vision_score = vision_data.get('vision_score')
            vision_result = vision_data.get('vision_result')
            
            # 综合评分
            if vision_score is not None:
                # 有视觉匹配：算法40% + 视觉60%
                final_score = (algorithm_score * 0.4) + (vision_score * 0.6)
            else:
                # 只有算法匹配：直接使用算法分数
                final_score = algorithm_score
            
            # 创建结果
            result = HybridMatchResult(
                pattern_id=pattern_id,
                pattern_name=match.get('pattern_name', ''),
                pattern_type=match.get('pattern_type', ''),
                algorithm_score=algorithm_score,
                vision_score=vision_score,
                final_score=final_score,
                vision_result=vision_result,
                klines_rendered=vision_score is not None
            )
            
            results.append(result)
        
        # 按最终分数排序
        results.sort(key=lambda x: x.final_score, reverse=True)
        
        return results
    
    def _get_pattern_by_id(self, pattern_id: int) -> Optional[Dict]:
        """根据ID获取模式信息"""
        for pattern in self.algorithm_matcher.pattern_library:
            if pattern.get('id') == pattern_id:
                return pattern
        return None

    def _resolve_pattern_image_path(self, pattern: Dict) -> Optional[Path]:
        """解析模式库图片路径（统一解析逻辑）"""
        return resolve_pattern_image_path(
            pattern.get('image_path'),
            pattern.get('source_page')
        )
    
    def _get_cache_key(self, symbol: str, timeframe: str, klines: List[Dict]) -> str:
        """生成缓存键"""
        # 基于最近几根K线的价格特征生成缓存键
        if not klines or len(klines) < 5:
            return f"{symbol}_{timeframe}_{int(time.time() / 60)}"  # 按分钟缓存
        
        recent_closes = [k['close'] for k in klines[-5:]]
        # 使用价格的哈希值（简化为字符串）
        price_hash = hash(tuple(recent_closes))
        return f"{symbol}_{timeframe}_{price_hash}"

    def match_candidates(
        self,
        matches: List[Dict],
        klines_dict: Dict[str, List[Dict]],
        symbol: str,
        timeframe: str = "15m",
    ) -> List[Optional[VisionMatchResult]]:
        """
        对指定候选执行视觉匹配（保证与候选顺序一致）
        """
        if not self.use_vision or not self.vision_matcher:
            return [None] * len(matches)

        realtime_klines = klines_dict.get(timeframe) or klines_dict.get("15m") or []
        if not realtime_klines:
            return [None] * len(matches)

        chart_path = self.temp_dir / f"{symbol}_{int(time.time())}_cand.png"
        chart_image = render_chart_image(
            self.chart_renderer,
            realtime_klines,
            chart_path,
            include_volume=False,
            include_ema=True,
            ema_periods=[20],
            show_grid=False,
            show_axes=False,
            show_title=False,
            show_legend=False,
        )
        if not chart_image:
            return [None] * len(matches)

        results: List[Optional[VisionMatchResult]] = []
        try:
            for match in matches:
                pattern = match.get("pattern") or {}
                pattern_image_path = resolve_pattern_image_path(
                    pattern.get("image_path"),
                    pattern.get("page_number") or pattern.get("source_page"),
                )
                if not pattern_image_path:
                    results.append(None)
                    continue
                try:
                    vision_result = self.vision_matcher.compare_two_images(
                        image1_path=pattern_image_path,
                        image2_path=chart_path,
                        context=f"{symbol} {timeframe}",
                    )
                    results.append(vision_result)
                except Exception:
                    results.append(None)
        finally:
            try:
                if chart_path.exists():
                    chart_path.unlink()
            except Exception:
                pass

        return results
    
    def _save_temp_chart(self, symbol: str, chart_bytes: bytes) -> Path:
        """保存临时图表文件"""
        temp_path = self.temp_dir / f"{symbol}_{int(time.time())}.png"
        temp_path.write_bytes(chart_bytes)
        return temp_path
    
    def get_match_statistics(self) -> Dict:
        """获取匹配统计信息"""
        return {
            'algorithm_matcher': {
                'pattern_count': len(self.algorithm_matcher.pattern_library)
            },
            'vision_enabled': self.use_vision,
            'use_all_candidates': self.use_all_candidates,
            'vision_top_n': self.vision_top_n,
            'cache_enabled': self.enable_cache,
            'cache_size': len(self.cache),
            'version': '3.0'
        }
