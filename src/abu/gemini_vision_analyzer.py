#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini Vision 图形识别模块（独立模块）

功能：使用Gemini Vision API分析图表图片，提取模式组合、K线行为、交易参数

设计原则：
1. 独立模块：只用于图形识别，不做其他用途
2. 成本控制：使用Gemini 1.5 Flash（不用Pro）
3. 断点续传：支持中断后继续，不浪费API调用
4. 去重机制：确保每张图片只分析一次
5. 健壮性：完整的错误处理和重试机制
6. 日志完整：详细记录处理状态，便于排查问题

输入：
- data/abu/images/*.png (1000张图片)
- pattern_library表（已有记录，通过image_path匹配）

输出：
- outputs/abu_gemini_annotations_enhanced.jsonl (主输出)
- outputs/.cache/abu_gemini/{sha1}.json (单图缓存)
- outputs/abu_gemini_analysis_state.json (处理状态，支持断点续传)
- outputs/abu_gemini_analysis.log (详细日志)

使用：
    from abu.gemini_vision_analyzer import GeminiVisionAnalyzer
    
    analyzer = GeminiVisionAnalyzer(
        api_key=os.getenv('GEMINI_API_KEY'),
        model='gemini-1.5-flash',  # 只使用Flash，不用Pro
        images_dir='data/abu/images',
        output_file='outputs/abu_gemini_annotations_enhanced.jsonl',
        state_file='outputs/abu_gemini_analysis_state.json'
    )
    
    # 执行分析（自动断点续传）
    analyzer.analyze_all(resume=True)
"""

from __future__ import annotations
import os
import sys
import json
import time
import hashlib
import logging
import base64
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / 'src'

# 设置日志
LOG_DIR = ROOT / 'outputs' / 'abu_gemini'
LOG_DIR.mkdir(parents=True, exist_ok=True)

class ProcessingStatus(Enum):
    """处理状态枚举"""
    PENDING = 'pending'      # 待处理
    PROCESSING = 'processing'  # 处理中
    COMPLETED = 'completed'   # 已完成
    FAILED = 'failed'        # 失败
    SKIPPED = 'skipped'      # 跳过（已存在）

@dataclass
class ImageAnalysisState:
    """单张图片的分析状态"""
    image_path: str
    image_sha1: str
    status: str  # ProcessingStatus值
    processed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    gemini_result: Optional[Dict] = None

@dataclass
class AnalysisState:
    """整体分析状态（支持断点续传）"""
    start_time: str
    last_update: str
    total_images: int
    completed_count: int
    failed_count: int
    skipped_count: int
    images: List[Dict]  # List[ImageAnalysisState as dict]
    settings: Dict  # 分析设置（model, prompt_version等）
    
    def get_pending_images(self) -> List[str]:
        """获取待处理的图片列表"""
        return [
            img['image_path'] for img in self.images
            if img['status'] in ['pending', 'failed'] and img['retry_count'] < 3
        ]

ENHANCED_PROMPT = """You are an expert price-action trading analyst specializing in Al Brooks trading methodology. Analyze this chart image COMPREHENSIVELY and extract ALL information - not just text and patterns, but the COMPLETE picture of what's happening in the entire chart.

CRITICAL: You must DESCRIBE THE ENTIRE CHART comprehensively. Think of yourself as explaining this chart to another trader - describe the complete price journey, all visual elements, relationships between patterns, and the full context. Extract maximum knowledge from the entire chart.

EXTRACTION PRIORITIES (in order of importance):

0. **COMPLETE CHART DESCRIPTION** (CRITICAL - MUST DESCRIBE ENTIRE CHART):
   - Describe the ENTIRE chart as a complete picture - what does the chart show from start to finish?
   - Complete price journey: Describe the price movement path from chart left (start) to right (end) step by step
   - Chart structure: What's the overall structure? (e.g., "strong uptrend in left section, pullback in middle, continuation in right section")
   - Visual layout: Where are patterns located relative to each other? Spatial relationships?
   - All visual elements: Describe ALL lines, arrows, labels, annotations, colors, shapes, and how they relate
   - Price range: Extract highest and lowest prices visible
   - Timeframe context: What timeframe and time period? (if visible)

1. **TRADING SIGNALS** - The MOST IMPORTANT. Extract EVERY trading signal mentioned or shown:
   - Look for text annotations like "20-Gap bar buy", "75% chance", "test of high of day"
   - Extract entry conditions, entry prices, stop-loss levels, take-profit levels
   - Extract probability percentages (e.g., "75%", "80% chance")
   - Extract direction (long/short), timeframe hints (e.g., "15m", "5m")
   - Even if prices are approximate, extract them (e.g., "around 87,500" or "near 2,080")
   - Extract multiple signals if chart shows different setups at different times
   - Signal relationships: How do different signals relate to each other? Sequence? Hierarchy?

2. **PATTERNS** - Identify ALL chart patterns visible:
   - Common patterns: Head and Shoulders, Double Top/Bottom, Triple Top/Bottom, Wedges, Triangles, Flags, Pennants
   - Price action patterns: Small Pullback (PB), Measured Move (MM), Bear Trap, Bull Trap
   - Trend patterns: Higher Highs/Higher Lows, Lower Highs/Lower Lows, Trend Channels
   - Pattern combinations MUST be identified (e.g., "W底 + Triangle + Breakout")
   - Pattern locations: Describe WHERE each pattern appears (left side, middle, right side, top, bottom)
   - Pattern relationships: How do patterns relate? (e.g., "Triangle forms after W-bottom", "MM follows breakout")
   - Pattern timeline: When does each pattern occur relative to chart start/end?
   - Location: top, bottom, mid_trend, start_of_trend, end_of_trend
   - Type: reversal, continuation, consolidation

3. **K-LINE FEATURES** - Extract specific candlestick patterns:
   - Engulfing patterns (bullish/bearish) - WHERE they appear
   - Pin bars / Rejection bars - location and significance
   - Inside bars - how many, where
   - Gap bars - size, location, direction
   - Specific bar patterns mentioned (e.g., "20-Gap bar", "Minor Bar 38") - exact bar number if visible
   - Bar sequences: Describe sequences of bars (e.g., "series of small pullback bars", "consecutive bullish bars")
   - Bar relationships: How bars relate to patterns and key levels

4. **PRICE ACTION BEHAVIOR** - Analyze overall structure COMPREHENSIVELY:
   - COMPLETE PRICE PATH: Describe the ENTIRE price journey from chart start to end (e.g., "starts at 4930, gaps up to 4940, strong uptrend to 4970, small pullback to 4955, continuation to 4990, midday reversal to 4970")
   - Trend evolution: How does trend develop over time? (e.g., "starts neutral at open, becomes bullish after gap at bar 5, strengthens during uptrend, weakens at midday reversal around bar 120")
   - Trend: bullish, bearish, neutral, choppy - and describe HOW it changes over time
   - Structure: higher_highs_and_higher_lows, lower_highs_and_lower_lows, etc. - describe the COMPLETE structure with all swings
   - All swings: Identify ALL price swings (up swings, down swings) with approximate price levels and locations
   - All pullbacks: Describe ALL pullbacks - depth, location, significance, when they occur
   - All breakouts: Describe ALL breakout points - from what pattern/level, to where, when
   - Volume behavior if visible: increasing, decreasing, constant - and WHEN it changes

5. **MARKET CONDITIONS** - Extract COMPLETE context:
   - Market context descriptions (e.g., "Small PB bull trend", "Bear trend from the open")
   - Time-based context: Morning session? Afternoon? Pre-market? Intraday evolution?
   - Trend strength: strong, moderate, weak - and HOW it changes
   - Volatility: high, low, moderate - and WHEN it changes
   - Market phases: Identify distinct market phases (e.g., "accumulation phase", "trend phase", "distribution phase")
   - Key price levels (support/resistance levels marked on chart) - describe ALL levels and their significance
   - EMA/SMA lines if visible: Values, relationship to price, crossovers
   - Market structure: Trend lines, channels, consolidation zones

REQUIRED JSON STRUCTURE (COMPREHENSIVE):
{
  "chart_overview": {
    "timeframe": "5m E-mini",
    "time_period": "morning session 9:30-12:00 or entire day",
    "price_range": {"high": 4990, "low": 4930},
    "total_bars": "approximately 200-300 bars if visible",
    "chart_structure": "Left side shows opening, middle shows trend development, right side shows reversal or continuation",
    "layout_description": "Complete description of chart layout, regions, visual organization"
  },
  "complete_price_path": {
    "start_price": "4930 (chart left)",
    "end_price": "4985 (chart right)",
    "price_journey": "Detailed step-by-step description: starts at 4930, gaps up to 4940, strong uptrend to 4970, small pullback to 4955, continuation to 4990, midday reversal to 4970",
    "major_swings": [
      {"type": "up", "from": 4930, "to": 4970, "location": "left third"},
      {"type": "down", "from": 4970, "to": 4955, "location": "middle"},
      {"type": "up", "from": 4955, "to": 4990, "location": "middle-right"}
    ],
    "key_price_points": [
      {"point": "opening", "price": 4930, "significance": "gap up from previous close"},
      {"point": "first high", "price": 4970, "significance": "first measured move target"},
      {"point": "pullback low", "price": 4955, "significance": "small PB in bull trend"},
      {"point": "high of day", "price": 4990, "significance": "test of high"},
      {"point": "reversal", "price": 4970, "significance": "Minor Bar 38 midday reversal"}
    ]
  },
  "patterns": [
    {
      "name": "Small Pullback Bull Trend",
      "type": "continuation",
      "location": "left to middle third",
      "chart_position": {"start_bar": "approximately bar 10", "end_bar": "approximately bar 150"},
      "price_range": {"high": 4970, "low": 4930},
      "confidence": 0.95,
      "relationship_to_others": "Forms foundation for measured move pattern"
    },
    {
      "name": "Bear Trap",
      "type": "reversal",
      "location": "bottom of pullback around bar 80-90",
      "chart_position": {"bar_range": "bars 80-90"},
      "price_range": {"trap_low": 4955, "reversal_high": 4970},
      "confidence": 0.9,
      "relationship_to_others": "Precedes measured move continuation"
    },
    {
      "name": "Measured Move",
      "type": "continuation",
      "location": "middle to right third",
      "chart_position": {"start_bar": "approximately bar 90", "target_bar": "approximately bar 180"},
      "price_range": {"measured_from": 4930, "measured_to": 4990},
      "confidence": 0.85
    }
  ],
  "pattern_combination": "Small Pullback Bull Trend (foundation) + Bear Trap (reversal at pullback) + Measured Move (continuation target)",
  "pattern_relationships": "Complete description of how patterns relate: W-bottom forms first, then triangle consolidation, then breakout triggers measured move",
  "price_action_behavior": {
    "trend": "bullish",
    "trend_evolution": "starts neutral at open, becomes bullish after gap, strengthens during uptrend, weakens at midday reversal",
    "structure": "higher_highs_and_higher_lows",
    "structure_details": "Complete description: HH at 4970, HL at 4955, HH at 4990, then potential HL forming",
    "kline_features": [
      {"feature": "20-Gap bar", "location": "bar 20", "significance": "buy signal"},
      {"feature": "engulfing", "location": "bar 85", "significance": "reversal confirmation"},
      {"feature": "Minor Bar 38", "location": "bar 38", "significance": "midday reversal point"}
    ],
    "volume_behavior": "increasing during uptrend, decreasing at reversal",
    "swings": [
      {"type": "up_swing", "start": 4930, "end": 4970, "bars": "bars 1-60"},
      {"type": "down_swing", "start": 4970, "end": 4955, "bars": "bars 60-80"},
      {"type": "up_swing", "start": 4955, "end": 4990, "bars": "bars 80-120"},
      {"type": "down_swing", "start": 4990, "end": 4970, "bars": "bars 120-140"}
    ],
    "pullbacks": [
      {"depth": "15 points", "location": "middle", "significance": "small PB in bull trend"}
    ],
    "breakouts": [
      {"from": "triangle consolidation", "to": "measured move target", "price": 4965, "bar": "approximately bar 90"}
    ]
  },
  "trading_signals": [
    {
      "direction": "long",
      "entry_condition": "20-Gap bar buy in small PB bull trend",
      "entry_price_hint": "around 4960.00",
      "stop_loss_hint": "below 20-Gap bar or 4950",
      "take_profit_1_hint": "test of high of day or 4990",
      "take_profit_2_hint": "measured move extension",
      "probability": 75,
      "target": "test_of_high_of_day",
      "risk_reward_ratio": 2.5,
      "timeframe_hint": "5m",
      "chart_location": "left to middle section, around bar 20"
    }
  ],
  "market_conditions": {
    "context": "Small PB bull trend from the open",
    "session_context": "Morning session with strong opening gap",
    "trend_strength": "strong",
    "volatility": "low to moderate",
    "market_phases": "opening gap phase, trend phase, reversal phase (if any)",
    "key_levels": ["4930.00", "4955.00", "4970.00", "4990.00"],
    "level_significance": "Describe what each key level represents: support, resistance, target, etc."
  },
  "visual_elements": {
    "annotations": [
      {"label": "Minor Bar 38", "description": "Midday reversal point", "price": 4985, "position": "middle-right"},
      {"label": "MM", "description": "Measured move target", "price": "around 4985"}
    ],
    "lines_and_shapes": "Describe all visible lines, arrows, shapes, zones, highlighting if any",
    "colors_and_markers": "Describe significant colors, markers, highlighting if visible"
  },
  "text_notes": [
    "20-Gap bar buy in small PB bull trend so 75% chance of test of high of day",
    "All text annotations, labels, descriptions visible on chart"
  ],
  "complete_narrative": "Complete narrative description of the ENTIRE chart from start to finish, as if explaining to another trader. Describe the complete price journey, all patterns, signals, relationships, and visual elements. This should be a comprehensive story of what happened in this chart.",
  "confidence": 0.90
}

MANDATORY REQUIREMENTS (COMPREHENSIVE EXTRACTION - MAXIMUM KNOWLEDGE):

0. **COMPLETE CHART DESCRIPTION IS MANDATORY** (HIGHEST PRIORITY - NEW):
   - You MUST describe the ENTIRE chart as a complete, holistic picture - not just isolated elements
   - Start with overall chart structure: What does the chart show as a whole from start to finish?
   - Describe the complete price movement path: step-by-step journey from chart left (start) to right (end)
   - Identify ALL chart regions and phases: opening phase, development phase, climax phase, reversal phase (if any)
   - Describe visual layout: How are elements arranged spatially? What's in left third? Middle third? Right third?
   - Extract timeframe and time period: What timeframe? What time period shown? (if visible on chart)
   - Describe price range: highest, lowest, typical range, and price scale
   - Describe chart organization: Multiple panels? Overlays? Insets? Any secondary charts?
   - Visual elements: Describe ALL visible elements - lines, arrows, labels, shapes, colors, highlighting
   - Element relationships: How do all visual elements relate to each other? Connections? Dependencies?

1. **TRADING SIGNALS ARE CRITICAL**: Extract EVERY trading signal - primary and secondary:
   - If ANY text mentions trading setups, signals, or probabilities, extract them ALL
   - Do NOT leave trading_signals empty if chart shows ANY trading information
   - Extract signal sequence: Which signals come first, second, third? (temporal order)
   - Signal timing: When do signals occur? (relative to chart start, bar numbers if visible)
   - Signal hierarchy: Primary signals vs secondary signals vs tertiary signals
   - Signal relationships: How do different signals relate? (e.g., "Signal 2 confirms Signal 1")
   - Multiple setups: If chart shows different setups at different times, extract ALL of them

2. **PATTERNS ARE MANDATORY** - Identify ALL patterns comprehensively:
   - If chart shows ANY recognizable pattern (even simple ones), add to patterns array
   - Patterns can be simple (e.g., "Bull Trend", "Small PB") or complex (e.g., "Head and Shoulders")
   - MUST include chart_position: Where exactly does each pattern appear? (left/middle/right third, approximate bar numbers if visible)
   - MUST include pattern relationships: How do patterns connect and relate? (e.g., "Pattern A leads to Pattern B")
   - MUST include pattern timeline: When does each pattern form relative to chart start?
   - Pattern combinations: If multiple patterns form a combination, describe the complete combination
   - Pattern significance: What's the significance of each pattern? (reversal, continuation, etc.)

3. **COMPLETE PRICE PATH** (CRITICAL - DESCRIBE ENTIRE JOURNEY):
   - Describe the ENTIRE price journey: Start → Middle → End (complete narrative)
   - Identify ALL major swings: every up swing and down swing with price levels and approximate locations
   - Identify ALL pullbacks: every pullback with depth, location, and significance
   - Identify ALL breakouts: every breakout - from what, to where, when
   - Price evolution: How does price evolve over time? (e.g., "starts at X, gaps to Y, trends to Z, pulls back to W, breaks out to V")
   - Trend evolution: How does trend change over time? (e.g., "starts neutral, becomes bullish, strengthens, then weakens")
   - Describe price evolution: How does price behavior change over time?
   - Extract swing relationships: How do swings connect? (e.g., "up swing from 4930 to 4970, followed by down swing to 4955, then up swing to 4990")

4. **EXTRACT FROM TEXT**: Read ALL text annotations, labels, and descriptions. Extract trading signals, probabilities, and price levels from text.
   - Extract from ALL text: Titles, labels, annotations, notes, descriptions
   - Extract implicit information: What does the text imply about the chart?

5. **PATTERN COMBINATIONS**: If multiple patterns exist, list them individually AND describe the combination in pattern_combination field.
   - Describe pattern sequence: In what order do patterns appear?
   - Describe pattern relationships: How do patterns interact?

6. **PRICE LEVELS**: Extract price levels from chart axes, annotations, or text.
   - Extract ALL price levels: support, resistance, targets, entries, stops
   - Use approximate values if exact values are unclear (e.g., "around 87,500")
   - Describe level significance: Why is each level important?

7. **PROBABILITY EXTRACTION**: Look for any mention of probability: "75%", "80% chance", "likely", "probably". Convert to numeric if possible.
   - Extract probabilities for all signals and setups
   - If multiple probabilities mentioned, extract all

8. **K-LINE FEATURES**: Identify specific candlestick patterns mentioned in text or visible in chart.
   - Include location: Where does each K-line feature appear?
   - Include sequence: Describe sequences of K-line patterns
   - Include relationships: How do K-line features relate to patterns?

9. **VISUAL ELEMENTS** (NEW):
   - Describe ALL visual elements: lines, arrows, shapes, colors, highlights
   - Describe spatial relationships: How are elements positioned relative to each other?
   - Extract colors and markers: What colors/shapes indicate what?

10. **TEMPORAL INFORMATION** (NEW):
    - Extract time information: What time period does the chart cover?
    - Identify time markers: Are there time labels? Session markers?
    - Describe temporal evolution: How does the market evolve over time?

11. **RELATIONSHIPS** (NEW):
    - Describe relationships between ALL elements: patterns, signals, price movements, annotations
    - Extract causal relationships: "Bear trap causes measured move", "gap triggers trend"
    - Describe spatial relationships: "Triangle appears above W-bottom", "reversal occurs at midday"

12. **COMPLETE NARRATIVE** (NEW):
    - Provide a complete narrative description: Tell the story of the entire chart
    - Like explaining the chart to another trader: What happened from start to finish?

13. **BE COMPREHENSIVE**: Extract MAXIMUM information. It's better to extract too much than too little.
    - If unsure, include it with lower confidence
    - Don't leave fields empty if information is visible or inferable
    - Describe what you see, even if not explicitly labeled

IMPORTANT NOTES:
- **COMPREHENSIVE DESCRIPTION REQUIRED**: You must describe the ENTIRE chart, not just isolated features. Think of yourself as a trader explaining this chart to another trader.
- **MAXIMUM INFORMATION**: Extract as much information as possible. Include:
  - Complete price path from start to end
  - All visual elements and their relationships
  - All patterns and how they relate
  - All signals and their sequence
  - Complete narrative of what happened
- **SPATIAL AND TEMPORAL CONTEXT**: Always include WHERE and WHEN things happen on the chart
- If chart is just a cover page or title page, provide minimal description but still note what's visible
- If chart shows unmarked/blank chart, describe the complete price action and structure you can see
- Always extract what IS visible, even if incomplete. Use "not_specified" or null only if truly not available
- **VISUAL DETAILS MATTER**: Describe colors, shapes, arrows, lines, annotations - everything visible
- **RELATIONSHIPS MATTER**: Describe how all elements relate to each other spatially and temporally

OUTPUT FORMAT - CRITICAL JSON REQUIREMENTS:

**YOU MUST RESPOND WITH VALID JSON ONLY - NO MARKDOWN, NO EXPLANATIONS, NO ADDITIONAL TEXT**

- Start your response directly with `{` (opening brace)
- End your response directly with `}` (closing brace)
- Do NOT wrap your response in ```json``` or ``` or any markdown formatting
- Do NOT add any text before or after the JSON
- Do NOT include explanations, notes, or additional text
- Ensure all strings are properly quoted with double quotes
- Ensure all special characters in strings are properly escaped
- Ensure all brackets `[]` and braces `{}` are properly closed
- Ensure no trailing commas in arrays or objects
- Ensure all numeric values are valid (no NaN or Infinity)

REQUIRED FIELDS (all must be present in JSON response, even if empty):
- "complete_narrative": String - Complete story of the entire chart (REQUIRED, cannot be null or empty)
- "chart_overview": Object - Complete layout description with timeframe, price_range, chart_structure, layout_description (REQUIRED)
- "complete_price_path": Object - Full price journey from start to end with price_journey, major_swings, key_price_points (REQUIRED)
- "patterns": Array - All patterns (can be empty [] if no patterns, but field must exist)
- "trading_signals": Array - All trading signals (can be empty [] if no signals, but field must exist)
- "price_action_behavior": Object - Complete price action analysis (REQUIRED)
- "market_conditions": Object - Market context and conditions (REQUIRED)
- "visual_elements": Object - All visible chart elements (REQUIRED)
- "pattern_relationships": String - How patterns relate to each other (REQUIRED, can be empty string if no patterns)
- "text_notes": Array - All text annotations visible on chart (REQUIRED, can be empty [])

**CRITICAL: RESPOND WITH ONLY VALID JSON. NO MARKDOWN. NO EXPLANATIONS. NO ADDITIONAL TEXT. JUST THE JSON OBJECT STARTING WITH { AND ENDING WITH }.**"""


class GeminiVisionAnalyzer:
    """Gemini Vision 图形识别分析器（独立模块）"""
    
    def __init__(
        self,
        api_key: str = None,  # OpenRouter API Key（从环境变量或参数获取）
        model: str = 'google/gemini-2.5-flash-image',  # OpenRouter模型名称
        images_dir: Path = None,
        output_file: Path = None,
        state_file: Path = None,
        cache_dir: Path = None,
        log_file: Path = None,
        sleep_ms: int = 1000,  # API限流，默认1秒
        max_retries: int = 3,
        context_window: int = 2,
        use_openrouter: bool = True  # 默认使用OpenRouter
    ):
        """
        初始化分析器（使用OpenRouter API）
        
        Args:
            api_key: OpenRouter API Key（可选，默认从环境变量获取）
            model: OpenRouter模型名称
                - 'google/gemini-2.5-flash-image' (默认，支持图像)
                - 'google/gemini-2.5-flash' (文本+图像)
                - 'google/gemini-3.0-flash-image-exp' (如果可用，实验性3.0)
            images_dir: 图片目录
            output_file: 输出JSONL文件
            state_file: 状态文件（用于断点续传）
            cache_dir: 缓存目录
            log_file: 日志文件
            sleep_ms: API调用间隔（毫秒）
            max_retries: 最大重试次数
            context_window: 上下文窗口（读取前后N页的文本）
            use_openrouter: 是否使用OpenRouter（默认True）
        """
        # 加载OpenRouter配置
        if use_openrouter:
            try:
                # 尝试多种导入方式
                try:
                    from openrouter_config import get_openrouter_api_key, get_openrouter_api_url, is_openrouter_configured
                except ImportError:
                    try:
                        from src.openrouter_config import get_openrouter_api_key, get_openrouter_api_url, is_openrouter_configured
                    except ImportError:
                        # 添加到sys.path
                        if str(SRC) not in sys.path:
                            sys.path.insert(0, str(SRC))
                        from openrouter_config import get_openrouter_api_key, get_openrouter_api_url, is_openrouter_configured
                
                if not api_key:
                    if not is_openrouter_configured():
                        raise ValueError("OpenRouter API Key 未配置！请设置环境变量 OPENROUTER_API_KEY 或在 .env 文件中配置")
                    api_key = get_openrouter_api_key()
                
                self.api_url = get_openrouter_api_url()
            except ImportError as e:
                raise ImportError(f"无法导入openrouter_config: {e}，请确保 src/openrouter_config.py 存在")
        else:
            # 直接使用Google API（不推荐，成本更高）
            if not api_key:
                api_key = os.getenv('GEMINI_API_KEY')
                if not api_key:
                    raise ValueError("Gemini API Key 未配置！请设置环境变量 GEMINI_API_KEY")
            self.api_url = None
        
        # 验证模型（禁止使用Pro，除非明确指定）
        model_lower = model.lower()
        if 'pro' in model_lower and '3.0' not in model_lower and 'exp' not in model_lower:
            raise ValueError(f"禁止使用Pro模型以控制成本！建议使用: google/gemini-2.5-flash-image")
        
        # 尝试使用3.0-preview（如果可用且用户未明确指定）
        if '3.0' in model_lower or 'flash' not in model_lower:
            # 用户明确指定了3.0或非flash，使用用户指定
            pass
        else:
            # 默认尝试3.0-flash，如果不可用则回退到2.5-flash
            if model == 'google/gemini-2.5-flash-image':
                # 先尝试3.0（需要在运行时检查）
                pass
        
        self.api_key = api_key
        self.model = model
        self.use_openrouter = use_openrouter
        self.sleep_ms = sleep_ms
        self.max_retries = max_retries
        self.context_window = context_window
        
        # 路径设置
        self.images_dir = images_dir or ROOT / 'data' / 'abu' / 'images'
        self.output_file = output_file or ROOT / 'outputs' / 'abu_gemini_annotations_enhanced.jsonl'
        self.state_file = state_file or ROOT / 'outputs' / 'abu_gemini_analysis_state.json'
        self.cache_dir = cache_dir or ROOT / 'outputs' / '.cache' / 'abu_gemini'
        self.log_file = log_file or LOG_DIR / 'gemini_analysis.log'
        
        # 确保目录存在
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 设置日志
        self._setup_logging()
        
        # 加载上下文文本（用于增强分析）
        self.pages_context = self._load_pages_context()
        
        self.logger.info(f"Gemini Vision Analyzer初始化完成")
        self.logger.info(f"  API: {'OpenRouter' if self.use_openrouter else 'Google Direct'}")
        self.logger.info(f"  模型: {self.model}")
        if self.use_openrouter and self.api_url:
            self.logger.info(f"  API URL: {self.api_url}")
        self.logger.info(f"  图片目录: {self.images_dir}")
        self.logger.info(f"  输出文件: {self.output_file}")
        self.logger.info(f"  状态文件: {self.state_file}")
        self.logger.info(f"  缓存目录: {self.cache_dir}")
    
    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger('gemini_vision_analyzer')
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(file_format)
        
        # 避免重复添加处理器
        if not self.logger.handlers:
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
    
    def _load_pages_context(self) -> Dict[int, Dict[str, Any]]:
        """加载页面上下文文本（用于增强分析）"""
        pages_jsonl = ROOT / 'data' / 'abu' / 'raw_pages.jsonl'
        if not pages_jsonl.exists():
            self.logger.warning(f"上下文文件不存在: {pages_jsonl}")
            return {}
        
        pages = {}
        try:
            with pages_jsonl.open('r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        page_num = int(record.get('page', 0))
                        if page_num > 0:
                            pages[page_num] = record
                    except Exception:
                        continue
            self.logger.info(f"加载了 {len(pages)} 页上下文文本")
        except Exception as e:
            self.logger.error(f"加载上下文失败: {e}")
        
        return pages
    
    def _sha1_of_file(self, file_path: Path, nbytes: int = 65536) -> str:
        """计算文件SHA1（用于去重和缓存）"""
        h = hashlib.sha1()
        with file_path.open('rb') as f:
            while True:
                chunk = f.read(nbytes)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    
    def _get_image_page_number(self, image_path: Path) -> Optional[int]:
        """从文件名提取页面号（如 page_0450_img_01_xxx.png -> 450）"""
        import re
        stem = image_path.stem
        match = re.search(r'page_(\d+)_', stem)
        return int(match.group(1)) if match else None
    
    def _get_context_text(self, page_num: int) -> Optional[str]:
        """获取页面上下文文本"""
        if not self.context_window:
            return None
        
        buf = []
        for offset in range(-self.context_window, self.context_window + 1):
            page = self.pages_context.get(page_num + offset)
            if page:
                text = page.get('text', '') or page.get('content', '')
                if text:
                    buf.append(text)
        
        return '\n'.join(buf) if buf else None
    
    def _load_analysis_state(self) -> Optional[AnalysisState]:
        """加载分析状态（用于断点续传）"""
        if not self.state_file.exists():
            return None
        
        try:
            with self.state_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
                return AnalysisState(**data)
        except Exception as e:
            self.logger.error(f"加载状态文件失败: {e}")
            return None
    
    def _save_analysis_state(self, state: AnalysisState):
        """保存分析状态"""
        state.last_update = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            with self.state_file.open('w', encoding='utf-8') as f:
                json.dump(asdict(state), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存状态文件失败: {e}")
    
    def _check_cache(self, image_sha1: str) -> Optional[Dict]:
        """检查缓存（避免重复分析）"""
        cache_file = self.cache_dir / f'{image_sha1}.json'
        if cache_file.exists():
            try:
                cached = json.loads(cache_file.read_text(encoding='utf-8'))
                if cached.get('error'):
                    return None  # 缓存的错误结果，重新分析
                return cached
            except Exception:
                return None
        return None
    
    def _save_cache(self, image_sha1: str, result: Dict):
        """保存缓存"""
        cache_file = self.cache_dir / f'{image_sha1}.json'
        try:
            cache_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            self.logger.warning(f"保存缓存失败: {e}")
    
    def _check_output_file(self, image_sha1: str) -> bool:
        """检查输出文件是否已包含该图片的分析（去重）"""
        if not self.output_file.exists():
            return False
        
        try:
            with self.output_file.open('r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        if record.get('sha1') == image_sha1:
                            return True
                    except Exception:
                        continue
        except Exception:
            pass
        
        return False
    
    def _encode_image_to_base64(self, image_path: Path) -> Optional[str]:
        """将图片编码为base64字符串（用于OpenRouter API）"""
        try:
            with open(image_path, 'rb') as f:
                image_data = f.read()
                base64_str = base64.b64encode(image_data).decode('utf-8')
                # 检测图片格式
                if image_path.suffix.lower() == '.png':
                    mime_type = 'image/png'
                elif image_path.suffix.lower() in ['.jpg', '.jpeg']:
                    mime_type = 'image/jpeg'
                else:
                    mime_type = 'image/png'  # 默认PNG
                return f"data:{mime_type};base64,{base64_str}"
        except Exception as e:
            self.logger.error(f"图片编码失败: {e}")
            return None
    
    def _call_gemini_api(self, image_path: Path, context_text: Optional[str] = None) -> Dict[str, Any]:
        """
        调用Gemini Vision API（核心方法，使用OpenRouter）
        
        注意：这是唯一调用Gemini API的地方，确保成本可控
        """
        if self.use_openrouter:
            # 使用OpenRouter API
            return self._call_openrouter_api(image_path, context_text)
        else:
            # 使用Google直接API（不推荐，成本更高）
            return self._call_google_api(image_path, context_text)
    
    def _call_openrouter_api(self, image_path: Path, context_text: Optional[str] = None) -> Dict[str, Any]:
        """使用OpenRouter API调用Gemini Vision"""
        # 编码图片
        image_data_url = self._encode_image_to_base64(image_path)
        if not image_data_url:
            return {"error": "图片编码失败"}
        
        # 构建请求体
        prompt = ENHANCED_PROMPT
        if context_text:
            prompt += f"\n\n上下文信息:\n{context_text[:4000]}"
        
        # OpenRouter使用OpenAI兼容格式
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,  # 降低温度以获得更稳定的结果
            "max_tokens": 1500  # 减少token限制以降低成本（从2000降到1500）
        }
        
        # 构建请求头
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/qingniao",
            "X-Title": "QingNiao ABU Pattern Analyzer"
        }
        
        # 调用API
        api_url = f"{self.api_url}/chat/completions"
        start_time = time.time()
        
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=60  # 60秒超时
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    # 解析JSON响应
                    return self._parse_api_response(content, elapsed)
                else:
                    self.logger.error(f"API响应格式异常: {result}")
                    return {"error": f"API响应格式异常: {result}"}
            else:
                error_text = response.text
                self.logger.error(f"API请求失败 (状态码 {response.status_code}): {error_text}")
                return {"error": f"API请求失败 (状态码 {response.status_code}): {error_text}"}
                
        except requests.exceptions.Timeout:
            self.logger.error(f"API请求超时")
            return {"error": "API请求超时"}
        except Exception as e:
            self.logger.error(f"API请求异常: {e}")
            return {"error": f"API请求异常: {str(e)}"}
    
    def _call_google_api(self, image_path: Path, context_text: Optional[str] = None) -> Dict[str, Any]:
        """使用Google直接API调用Gemini Vision（不推荐，保留兼容性）"""
        try:
            import google.generativeai as genai
            from PIL import Image
        except ImportError:
            raise ImportError("请安装依赖: pip install google-generativeai pillow")
        
        # 配置API
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        
        # 读取图片
        try:
            img = Image.open(str(image_path))
        except Exception as e:
            return {"error": f"图片读取失败: {e}"}
        
        # 构建请求
        parts = [
            {"text": ENHANCED_PROMPT},
            img,
        ]
        
        # 添加上下文文本（如果有）
        if context_text:
            parts.append({"text": f"context_text:\n{context_text[:4000]}"})
        
        # 调用API
        try:
            response = model.generate_content(parts)
            response_text = response.text or '{}'
        except Exception as e:
            return {"error": f"API调用失败: {str(e)}"}
        
        # 解析JSON响应
        return self._parse_api_response(response_text, 0)
    
    def _parse_api_response(self, response_text: str, elapsed_time: float = 0) -> Dict[str, Any]:
        """解析API响应（提取JSON，使用更健壮的方法）"""
        import re
        
        # 方法1: 尝试直接解析（如果已经是纯JSON）
        try:
            result = json.loads(response_text.strip())
            if elapsed_time > 0:
                result['_api_elapsed'] = elapsed_time
            return result
        except json.JSONDecodeError:
            pass
        
        # 方法2: 尝试提取markdown代码块中的JSON
        try:
            # 匹配 ```json ... ``` 或 ``` ... ```
            json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_block_match:
                json_text = json_block_match.group(1)
                result = json.loads(json_text)
                if elapsed_time > 0:
                    result['_api_elapsed'] = elapsed_time
                return result
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # 方法3: 尝试找到第一个 { 到最后一个 } 之间的内容（更健壮）
        try:
            first_brace = response_text.find('{')
            last_brace = response_text.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_text = response_text[first_brace:last_brace + 1]
                # 尝试修复常见的JSON格式问题
                json_text = self._fix_json_issues(json_text)
                result = json.loads(json_text)
                if elapsed_time > 0:
                    result['_api_elapsed'] = elapsed_time
                return result
        except json.JSONDecodeError as e:
            # 记录错误位置以便调试
            self.logger.warning(f"JSON解析失败（方法3）: {e}")
            # 尝试更激进的修复
            try:
                json_text = self._aggressively_fix_json(json_text)
                result = json.loads(json_text)
                if elapsed_time > 0:
                    result['_api_elapsed'] = elapsed_time
                return result
            except:
                pass
        
        # 所有方法都失败，返回错误信息
        self.logger.warning(f"JSON解析完全失败，返回原始文本")
        return {
            "raw": response_text[:5000],  # 限制长度避免太大
            "parse_error": "JSON解析失败",
            "parse_error_detail": "无法从响应中提取有效JSON",
            "confidence": 0.0,
            "_api_elapsed": elapsed_time
        }
    
    def _fix_json_issues(self, json_text: str) -> str:
        """修复常见的JSON格式问题"""
        import re
        # 移除尾随逗号（在对象和数组的最后一项）
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        # 修复未转义的控制字符
        json_text = json_text.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return json_text
    
    def _aggressively_fix_json(self, json_text: str) -> str:
        """更激进的JSON修复（尝试修复更多问题）"""
        import re
        # 修复尾随逗号
        json_text = self._fix_json_issues(json_text)
        # 修复未闭合的引号（简单情况）
        # 注意：这个方法可能不够完善，但对于大部分情况有效
        return json_text
    
    def analyze_single_image(
        self,
        image_path: Path,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """
        分析单张图片（带缓存和去重）
        
        Args:
            image_path: 图片路径
            force_reanalyze: 是否强制重新分析（忽略缓存）
        
        Returns:
            分析结果字典
        """
        # 1. 计算SHA1（用于去重和缓存）
        image_sha1 = self._sha1_of_file(image_path)
        
        # 2. 检查是否已处理（去重）
        if not force_reanalyze and self._check_output_file(image_sha1):
            self.logger.info(f"跳过已处理图片: {image_path.name} (SHA1: {image_sha1[:8]}...)")
            return {
                "image": str(image_path),
                "sha1": image_sha1,
                "status": "skipped",
                "reason": "已在输出文件中存在"
            }
        
        # 3. 检查缓存
        if not force_reanalyze:
            cached = self._check_cache(image_sha1)
            if cached:
                self.logger.info(f"使用缓存: {image_path.name} (SHA1: {image_sha1[:8]}...)")
                return {
                    "image": str(image_path),
                    "sha1": image_sha1,
                    "result": cached,
                    "cached": True
                }
        
        # 4. 获取上下文文本
        page_num = self._get_image_page_number(image_path)
        context_text = self._get_context_text(page_num) if page_num else None
        
        # 5. 调用Gemini API（唯一调用点）
        self.logger.info(f"开始分析: {image_path.name} (SHA1: {image_sha1[:8]}...)")
        start_time = time.time()
        
        result = self._call_gemini_api(image_path, context_text)
        
        elapsed = time.time() - start_time
        api_cost = self._estimate_cost(1)  # 估算成本
        
        # 6. 保存缓存
        if 'error' not in result:
            self._save_cache(image_sha1, result)
            self.logger.info(f"分析完成: {image_path.name} (耗时: {elapsed:.2f}s, 成本: ${api_cost:.6f})")
        else:
            self.logger.error(f"分析失败: {image_path.name} - {result.get('error')}")
        
        # 7. 返回结果
        return {
            "image": str(image_path),
            "sha1": image_sha1,
            "page": page_num,
            "result": result,
            "cached": False,
            "elapsed_seconds": elapsed,
            "estimated_cost_usd": api_cost
        }
    
    def _estimate_cost(self, image_count: int) -> float:
        """估算API成本（基于实际使用数据，修正版）"""
        # 实际成本计算（修正）：
        # - 总花费：$2.4（自开始调用Gemini以来）
        # - 之前测试轮次：$1.8（简单Prompt）
        # - 本次运行花费：$2.4 - $1.8 = $0.6
        # - 本次已处理：68张
        # - 实际单张成本：$0.6 / 68 = $0.0088/张
        # 
        # 注意：虽然比最初估算的$0.000125高70倍，但比之前的$0.0414合理得多
        # 可能原因：
        # 1. OpenRouter可能有额外费用或更高定价
        # 2. 图片base64编码后token数很多
        # 3. Prompt较长（400+行），输入token数多
        # 4. max_tokens=1500，输出token数较多
        return image_count * 0.0088
    
    def _initialize_analysis_state(self, image_paths: List[Path]) -> AnalysisState:
        """初始化分析状态"""
        images = []
        for img_path in image_paths:
            sha1 = self._sha1_of_file(img_path)
            # 检查是否已处理
            status = ProcessingStatus.SKIPPED if self._check_output_file(sha1) else ProcessingStatus.PENDING
            
            images.append({
                "image_path": str(img_path),
                "image_sha1": sha1,
                "status": status.value,
                "processed_at": None,
                "error_message": None,
                "retry_count": 0,
                "gemini_result": None
            })
        
        return AnalysisState(
            start_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            last_update=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_images=len(image_paths),
            completed_count=sum(1 for img in images if img['status'] == ProcessingStatus.SKIPPED.value),
            failed_count=0,
            skipped_count=sum(1 for img in images if img['status'] == ProcessingStatus.SKIPPED.value),
            images=images,
            settings={
                "model": self.model,
                "prompt_version": "enhanced_v1",
                "sleep_ms": self.sleep_ms,
                "max_retries": self.max_retries,
                "context_window": self.context_window
            }
        )
    
    def analyze_all(
        self,
        resume: bool = True,
        limit: Optional[int] = None,
        start_idx: int = 0,
        end_idx: Optional[int] = None,
        force_reanalyze: bool = False
    ) -> Dict[str, Any]:
        """
        批量分析所有图片（支持断点续传）
        
        Args:
            resume: 是否从上次中断处继续
            limit: 限制处理数量（None=全部）
            start_idx: 开始索引
            end_idx: 结束索引（None=到末尾）
            force_reanalyze: 是否强制重新分析（忽略缓存和已处理记录）
        
        Returns:
            处理结果统计
        """
        # 1. 收集图片
        image_paths = sorted(list(self.images_dir.glob('*.png')) + list(self.images_dir.glob('*.jpg')))
        image_paths = [p for p in image_paths if p.is_file()]
        
        if not image_paths:
            self.logger.error(f"未找到图片: {self.images_dir}")
            return {"error": "未找到图片"}
        
        # 2. 切片处理
        if end_idx:
            image_paths = image_paths[start_idx:end_idx]
        elif start_idx > 0:
            image_paths = image_paths[start_idx:]
        
        if limit:
            image_paths = image_paths[:limit]
        
        self.logger.info(f"找到 {len(image_paths)} 张图片待处理")
        
        # 3. 加载或初始化状态
        state = None
        if resume:
            state = self._load_analysis_state()
            if state:
                self.logger.info(f"恢复分析状态: 已完成 {state.completed_count}/{state.total_images}")
        
        if not state:
            state = self._initialize_analysis_state(image_paths)
            self._save_analysis_state(state)
        
        # 4. 获取待处理图片（断点续传）
        if resume:
            pending_paths = [Path(img['image_path']) for img in state.images 
                           if img['status'] in ['pending', 'failed'] and img['retry_count'] < self.max_retries]
            # 确保图片路径存在
            pending_paths = [p for p in pending_paths if p.exists()]
            self.logger.info(f"从断点继续: {len(pending_paths)} 张图片待处理")
        else:
            pending_paths = image_paths
        
        if not pending_paths:
            self.logger.info("所有图片已处理完成")
            return {
                "total": state.total_images,
                "completed": state.completed_count,
                "failed": state.failed_count,
                "skipped": state.skipped_count
            }
        
        # 5. 处理每张图片
        total_cost = 0.0
        processed_count = 0
        
        # 运行/休息机制：运行3小时，休息1小时
        WORK_DURATION_HOURS = 3.0  # 运行3小时
        REST_DURATION_HOURS = 1.0  # 休息1小时
        session_start_time = datetime.now()  # 当前运行周期的开始时间
        
        # 打开输出文件（追加模式）
        with self.output_file.open('a', encoding='utf-8') as output_f:
            for i, img_path in enumerate(pending_paths, 1):
                try:
                    # 检查是否达到运行时间限制（运行3小时后休息1小时）
                    current_time = datetime.now()
                    elapsed_hours = (current_time - session_start_time).total_seconds() / 3600.0
                    
                    if elapsed_hours >= WORK_DURATION_HOURS:
                        self.logger.info(f"⏸️  已运行 {elapsed_hours:.2f} 小时，达到运行时间限制，开始休息 {REST_DURATION_HOURS} 小时...")
                        self.logger.info(f"   当前进度: {i-1}/{len(pending_paths)} (已完成: {state.completed_count}, 失败: {state.failed_count})")
                        
                        # 保存状态
                        self._save_analysis_state(state)
                        
                        # 休息1小时
                        rest_seconds = REST_DURATION_HOURS * 3600
                        self.logger.info(f"   💤 休息中... ({REST_DURATION_HOURS} 小时，{rest_seconds//60} 分钟)")
                        self.logger.info(f"   预计恢复时间: {(current_time + timedelta(hours=REST_DURATION_HOURS)).strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        # 倒计时休息（每5分钟输出一次状态）
                        rest_countdown = int(rest_seconds)
                        while rest_countdown > 0:
                            if rest_countdown % 300 == 0 or rest_countdown <= 60:  # 每5分钟或最后1分钟
                                remaining_minutes = rest_countdown // 60
                                self.logger.info(f"   💤 休息中... 剩余 {remaining_minutes} 分钟 ({rest_countdown} 秒)")
                            time.sleep(min(60, rest_countdown))  # 每次最多睡60秒，方便响应中断
                            rest_countdown -= 60
                        
                        # 休息结束，开始新的运行周期
                        session_start_time = datetime.now()
                        self.logger.info(f"✅ 休息结束，恢复处理...")
                        self.logger.info(f"   新的运行周期开始时间: {session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # 更新状态为处理中
                    img_state = next((img for img in state.images if img['image_path'] == str(img_path)), None)
                    if img_state:
                        img_state['status'] = ProcessingStatus.PROCESSING.value
                    else:
                        # 新图片，添加到状态
                        sha1 = self._sha1_of_file(img_path)
                        img_state = {
                            "image_path": str(img_path),
                            "image_sha1": sha1,
                            "status": ProcessingStatus.PROCESSING.value,
                            "processed_at": None,
                            "error_message": None,
                            "retry_count": 0,
                            "gemini_result": None
                        }
                        state.images.append(img_state)
                        state.total_images += 1
                    
                    # 分析图片
                    result = self.analyze_single_image(img_path, force_reanalyze=force_reanalyze)
                    
                    # 更新状态
                    if result.get('status') == 'skipped':
                        img_state['status'] = ProcessingStatus.SKIPPED.value
                        state.skipped_count += 1
                    elif 'error' in result.get('result', {}):
                        img_state['status'] = ProcessingStatus.FAILED.value
                        img_state['error_message'] = result['result']['error']
                        img_state['retry_count'] += 1
                        state.failed_count += 1
                    else:
                        img_state['status'] = ProcessingStatus.COMPLETED.value
                        img_state['processed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        img_state['gemini_result'] = result.get('result')
                        state.completed_count += 1
                        processed_count += 1
                    
                    # 写入输出文件（立即写入，避免丢失）
                    output_f.write(json.dumps(result, ensure_ascii=False) + '\n')
                    output_f.flush()
                    
                    # 更新总成本
                    total_cost += result.get('estimated_cost_usd', 0)
                    
                    # 保存状态（每10张保存一次）
                    if i % 10 == 0:
                        self._save_analysis_state(state)
                        elapsed_since_start = (datetime.now() - session_start_time).total_seconds() / 3600.0
                        self.logger.info(f"进度: {i}/{len(pending_paths)} (已完成: {state.completed_count}, 失败: {state.failed_count}, 跳过: {state.skipped_count}, 本周期运行: {elapsed_since_start:.2f}小时)")
                    
                    # API限流
                    if self.sleep_ms > 0 and i < len(pending_paths):
                        time.sleep(self.sleep_ms / 1000.0)
                
                except KeyboardInterrupt:
                    self.logger.warning("用户中断，保存状态...")
                    self._save_analysis_state(state)
                    raise
                except Exception as e:
                    self.logger.error(f"处理图片失败 {img_path.name}: {e}", exc_info=True)
                    if img_state:
                        img_state['status'] = ProcessingStatus.FAILED.value
                        img_state['error_message'] = str(e)
                        img_state['retry_count'] += 1
                        state.failed_count += 1
        
        # 6. 最终保存状态
        self._save_analysis_state(state)
        
        # 7. 生成报告
        summary = {
            "total_images": state.total_images,
            "completed": state.completed_count,
            "failed": state.failed_count,
            "skipped": state.skipped_count,
            "newly_processed": processed_count,
            "total_cost_usd": total_cost,
            "estimated_remaining_cost": self._estimate_cost(state.total_images - state.completed_count - state.skipped_count),
            "output_file": str(self.output_file),
            "state_file": str(self.state_file),
            "log_file": str(self.log_file)
        }
        
        self.logger.info("=" * 80)
        self.logger.info("分析完成")
        self.logger.info(f"  总图片数: {summary['total_images']}")
        self.logger.info(f"  已完成: {summary['completed']}")
        self.logger.info(f"  失败: {summary['failed']}")
        self.logger.info(f"  跳过: {summary['skipped']}")
        self.logger.info(f"  本次处理: {summary['newly_processed']}")
        self.logger.info(f"  本次成本: ${summary['total_cost_usd']:.6f}")
        self.logger.info(f"  预计剩余成本: ${summary['estimated_remaining_cost']:.6f}")
        self.logger.info("=" * 80)
        
        return summary
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前分析状态"""
        state = self._load_analysis_state()
        if not state:
            # 检查是否有图片待处理
            image_paths = sorted(list(self.images_dir.glob('*.png')) + list(self.images_dir.glob('*.jpg')))
            image_paths = [p for p in image_paths if p.is_file()]
            return {
                "status": "not_started",
                "total_images": len(image_paths),
                "output_file": str(self.output_file),
                "state_file": str(self.state_file)
            }
        
        # 计算待处理图片数
        pending_count = sum(1 for img in state.images 
                          if img.get('status') in ['pending', 'failed', 'processing'] 
                          and img.get('retry_count', 0) < self.max_retries)
        
        return {
            "status": "in_progress" if pending_count > 0 else "completed",
            "start_time": state.start_time,
            "last_update": state.last_update,
            "total_images": state.total_images,
            "completed": state.completed_count,
            "failed": state.failed_count,
            "skipped": state.skipped_count,
            "pending": pending_count,
            "progress_pct": (state.completed_count + state.skipped_count) / state.total_images * 100 if state.total_images > 0 else 0,
            "estimated_remaining_cost": self._estimate_cost(pending_count),
            "output_file": str(self.output_file),
            "state_file": str(self.state_file),
            "log_file": str(self.log_file),
            "model": self.model
        }
    
    def reset_state(self, confirm: bool = False):
        """重置分析状态（谨慎使用）"""
        if not confirm:
            raise ValueError("必须设置confirm=True才能重置状态")
        
        if self.state_file.exists():
            self.state_file.unlink()
            self.logger.info("状态文件已删除")
        
        self.logger.warning("状态已重置，下次运行将重新开始")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ABU Gemini Vision 图形识别分析器')
    parser.add_argument('--api-key', type=str, help='OpenRouter API Key（或使用OPENROUTER_API_KEY环境变量，默认从.env读取）')
    parser.add_argument('--model', type=str, default='google/gemini-2.5-flash-image', 
                       help='OpenRouter模型名称（默认: google/gemini-2.5-flash-image，可选: google/gemini-3.0-flash-image-exp）')
    parser.add_argument('--images-dir', type=str, help='图片目录')
    parser.add_argument('--output', type=str, help='输出JSONL文件')
    parser.add_argument('--state', type=str, help='状态文件路径')
    parser.add_argument('--resume', action='store_true', default=True, help='断点续传（默认开启）')
    parser.add_argument('--no-resume', dest='resume', action='store_false', help='不续传，重新开始')
    parser.add_argument('--limit', type=int, help='限制处理数量')
    parser.add_argument('--start-idx', type=int, default=0, help='开始索引')
    parser.add_argument('--end-idx', type=int, help='结束索引')
    parser.add_argument('--force', action='store_true', help='强制重新分析（忽略缓存）')
    parser.add_argument('--sleep-ms', type=int, default=1000, help='API调用间隔（毫秒）')
    parser.add_argument('--status', action='store_true', help='只查看状态，不执行分析')
    parser.add_argument('--reset', action='store_true', help='重置状态文件（需谨慎）')
    
    args = parser.parse_args()
    
    # 设置UTF-8编码
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
    
    # 获取API Key（默认使用OpenRouter）
    api_key = args.api_key
    use_openrouter = True  # 默认使用OpenRouter
    
    # 创建分析器
    try:
        analyzer = GeminiVisionAnalyzer(
            api_key=api_key,  # 如果为None，将从环境变量或openrouter_config获取
            model=args.model,
            images_dir=Path(args.images_dir) if args.images_dir else None,
            output_file=Path(args.output) if args.output else None,
            state_file=Path(args.state) if args.state else None,
            sleep_ms=args.sleep_ms,
            use_openrouter=use_openrouter
        )
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        print("提示: 请确保 .env 文件中包含 OPENROUTER_API_KEY", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"初始化失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
    
    # 只查看状态
    if args.status:
        status = analyzer.get_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0
    
    # 重置状态
    if args.reset:
        analyzer.reset_state(confirm=True)
        return 0
    
    # 执行分析
    try:
        result = analyzer.analyze_all(
            resume=args.resume,
            limit=args.limit,
            start_idx=args.start_idx,
            end_idx=args.end_idx,
            force_reanalyze=args.force
        )
        
        print("\n分析结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return 0
    except KeyboardInterrupt:
        print("\n分析被用户中断，状态已保存")
        return 130
    except Exception as e:
        print(f"\n分析失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

