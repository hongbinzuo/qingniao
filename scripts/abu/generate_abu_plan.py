#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU系统v3.0 - 30币种交易计划生成器

为30币种生成交易计划，每个币种5分钟和15分钟各1个信号。
使用Gemini Flash模式库进行匹配。
"""

import sys
import os
import json
import asyncio
import shutil
import time
import requests
import argparse
from dataclasses import asdict
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
    from abu.gemini_trade_plan import (
        generate_trade_plan,
        load_plan_context,
        plan_budget_ok,
        get_ebook_rules,
    )
    from abu.chart_renderer import ChartRenderer
    from abu.ai_vision_matcher import AIVisionMatcher
    from abu.vision_storage import VisionMatchRecorder
    from abu.vision_utils import resolve_pattern_image_path, render_chart_image, make_cache_key
    from abu.brooks_trading_validator import BrooksTradingValidator
    from abu.kline_feature_extractor import extract_basic_kline_features
    from abu.market_context import classify_market_context
    from db_manager_trader import TraderDBManager
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


STABLE_SYMBOLS = {
    "USDT", "USDC", "BUSD", "TUSD", "USDP", "USDD", "DAI", "FRAX",
    "FDUSD", "USDE", "USDN", "UST", "USTC", "EURT", "EURC", "PYUSD",
    "GUSD", "LUSD", "SUSD", "STABLE",
}

TIMEFRAMES = ["15m", "1h", "4h"]


def _is_stable(symbol: str) -> bool:
    if not symbol:
        return False
    sym = symbol.upper()
    if sym in STABLE_SYMBOLS:
        return True
    # 覆盖常见 USD* 稳定币（如 USD1/USDK/USDX 等）
    if sym.startswith("USD") or sym.endswith("USD"):
        return True
    return False


def _is_leveraged_token(symbol: str) -> bool:
    if not symbol:
        return False
    sym = symbol.upper()
    # Common leveraged suffixes like 3L/3S/5L/5S/2L/2S/10L/10S
    for suffix in ("2L", "2S", "3L", "3S", "5L", "5S", "10L", "10S"):
        if sym.endswith(suffix):
            return True
    # Common leveraged naming patterns
    if sym.endswith("BULL") or sym.endswith("BEAR") or sym.endswith("UP") or sym.endswith("DOWN"):
        return True
    if sym.endswith("LONG") or sym.endswith("SHORT"):
        return True
    return False


def _build_rank_list() -> List[int]:
    # 1-based ranks: top5 + 20-24 + 60-64 + 140-144 + 300-304 + 620-624
    ranks = []
    for start, end in [(1, 5), (20, 24), (60, 64), (140, 144), (300, 304), (620, 624)]:
        ranks.extend(list(range(start, end + 1)))
    return ranks


def _coin_cache_path(root: Path) -> Path:
    return root / "data" / "coin_lists" / "abu_ranked_coins.json"


def _load_cached_coins(path: Path) -> Optional[List[Dict]]:
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("coins"), list):
            return data["coins"]
        if isinstance(data, list):
            return data
    except Exception:
        return None
    return None


def _save_cached_coins(path: Path, coins: List[Dict], ranks: List[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ranks": ranks,
        "coins": coins,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _run_dry_checks(root: Path, ranks: List[int]) -> int:
    """干跑校验（不调用外部API）"""
    print("[DRY RUN] 校验开始（不会请求外部API）")

    cache_path = _coin_cache_path(root)
    coins = _load_cached_coins(cache_path)
    if not coins:
        print(f"[DRY RUN] ❌ 缓存币种列表不存在或为空: {cache_path}")
        print("[DRY RUN]     请先运行一次真实模式或设置 ABU_COIN_LIST_REFRESH=1")
        return 2

    print(f"[DRY RUN] ✅ 缓存币种列表: {cache_path} (数量: {len(coins)})")
    if len(coins) != len(ranks):
        print(f"[DRY RUN] ⚠️  期望 {len(ranks)} 个币种，实际 {len(coins)} 个")

    # Gemini 计划 + Ebook 校验
    plan_ctx = load_plan_context()
    if plan_ctx.get("enabled"):
        print(f"[DRY RUN] ✅ Gemini计划已启用 (model={plan_ctx.get('model')})")
        if plan_ctx.get("ebook_enabled"):
            print("[DRY RUN] ✅ Ebook规则已启用")
        else:
            print("[DRY RUN] ⚠️  Ebook规则未启用或不可用")
    else:
        print("[DRY RUN] ⚠️  Gemini计划未启用（可设置 ABU_GEMINI_PLAN=1）")

    # 视觉过滤校验
    vision_ctx = _load_vision_context(root)
    if vision_ctx.get("enabled"):
        print(f"[DRY RUN] ✅ 视觉过滤已启用 (model={vision_ctx.get('model')})")
        print(f"[DRY RUN]    视觉日志: {'verbose' if vision_ctx.get('verbose') else 'quiet'}")
    else:
        print("[DRY RUN] ⚠️  视觉过滤未启用（可设置 ABU_VISION_FILTER=1）")

    print("[DRY RUN] 校验完成")
    return 0


def get_ranked_coins(ranks: List[int]) -> List[Dict]:
    """按24h交易量排名选择币种（排除稳定币）"""
    try:
        # 使用Gate.io API
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # 筛选USDT交易对，按24h交易量排序
            usdt_pairs = [t for t in data if t.get('currency_pair', '').endswith('_USDT')]
            filtered = []
            for pair in usdt_pairs:
                symbol = pair.get('currency_pair', '').replace('_USDT', '')
                if _is_stable(symbol) or _is_leveraged_token(symbol):
                    continue
                filtered.append(pair)
            filtered.sort(key=lambda x: float(x.get('quote_volume', 0)), reverse=True)

            coins = []
            for rank in ranks:
                idx = rank - 1
                if idx < 0 or idx >= len(filtered):
                    continue
                pair = filtered[idx]
                symbol = pair['currency_pair'].replace('_USDT', '')
                coins.append({
                    'symbol': symbol,
                    'pair': pair['currency_pair'],
                    'volume_24h': float(pair.get('quote_volume', 0)),
                    'price': float(pair.get('last', 0)),
                    'rank': rank,
                })
            return coins
    except Exception as e:
        print(f"[WARN] Gate.io获取失败: {e}", file=sys.stderr)
    
    return []


def get_kline_gateio(symbol: str, timeframe='5m', limit=200):
    """从Gate.io获取K线数据"""
    try:
        tf_map = {'5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h'}
        interval = tf_map.get(timeframe, '5m')
        
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            'currency_pair': f'{symbol}_USDT',
            'interval': interval,
            'limit': limit
        }
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                klines = []
                for k in data:
                    klines.append({
                        'timestamp': int(k[0]),
                        'open': float(k[5]),
                        'high': float(k[3]),
                        'low': float(k[4]),
                        'close': float(k[2]),
                        'volume': float(k[1])
                    })
                klines.sort(key=lambda x: x.get('timestamp', 0))
                return klines
    except Exception as e:
        pass
    return None


def extract_features_from_klines(klines: List[Dict], timeframe: str) -> Dict:
    """从K线数据提取特征"""
    if not klines or len(klines) < 20:
        return {}
    
    recent = klines[-50:] if len(klines) >= 50 else klines
    
    closes = [k['close'] for k in recent]
    highs = [k['high'] for k in recent]
    lows = [k['low'] for k in recent]
    
    # 趋势特征
    if len(closes) >= 10:
        price_trend = 'bullish' if closes[-1] > closes[0] else 'bearish'
        trend_strength = abs(closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
    else:
        price_trend = 'neutral'
        trend_strength = 0
    
    # K线特征
    kline_features = []
    if len(recent) >= 2:
        for i in range(max(1, len(recent) - 5), len(recent)):
            if i < 1:
                continue
            last = recent[i]
            prev = recent[i-1]
            
            if last['close'] > last['open'] and prev['close'] < prev['open']:
                if last['open'] < prev['close'] and last['close'] > prev['open']:
                    kline_features.append('bullish_engulfing')
            elif last['close'] < last['open'] and prev['close'] > prev['open']:
                if last['open'] > prev['close'] and last['close'] < prev['open']:
                    kline_features.append('bearish_engulfing')
            
            if last['high'] < prev['high'] and last['low'] > prev['low']:
                kline_features.append('inside_bar')
    
    # 波动率
    price_ranges = [(h - l) for h, l in zip(highs, lows)]
    avg_range = sum(price_ranges) / len(price_ranges) if price_ranges else 0
    volatility = avg_range / closes[-1] if closes and closes[-1] > 0 else 0
    
    features = {
        'pattern_type': 'unknown',
        'direction': 'long' if price_trend == 'bullish' else 'short' if price_trend == 'bearish' else 'neutral',
        'trend': price_trend,
        'trend_direction': price_trend,
        'trend_strength': trend_strength,
        'kline_features': list(set(kline_features)),
        'volatility': volatility,
        'market_conditions': {
            'trend_strength': 'strong' if trend_strength > 0.02 else 'weak',
            'volatility': 'high' if volatility > 0.01 else 'low',
            'trend_direction': price_trend
        }
    }
    
    return features


def _normalize_direction(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    val = str(raw).strip().lower()
    if val in {"long", "buy", "bull", "bullish", "up"}:
        return "long"
    if val in {"short", "sell", "bear", "bearish", "down"}:
        return "short"
    if val in {"neutral", "sideways"}:
        return "neutral"
    return None


def generate_signal_from_match(
    match_result,
    current_price: float,
    klines: List[Dict],
    direction_hint: Optional[str] = None,
    timeframe: Optional[str] = None,
) -> Tuple[Optional[Dict], Optional[str]]:
    """从匹配结果生成交易信号"""
    def _reject(reason: str) -> Tuple[Optional[Dict], Optional[str]]:
        return None, reason

    pattern_name = match_result.pattern_name
    pattern_type = match_result.pattern_type
    source = match_result.source
    
    # 从模式类型推断方向
    direction = _normalize_direction(direction_hint) or 'neutral'
    pattern_type_lower = pattern_type.lower() if pattern_type else ''
    
    if any(kw in pattern_type_lower for kw in ['bull', 'long', 'buy', 'up', 'ascending']):
        direction = 'long'
    elif any(kw in pattern_type_lower for kw in ['bear', 'short', 'sell', 'down', 'descending']):
        direction = 'short'
    else:
        pattern_name_lower = pattern_name.lower() if pattern_name else ''
        if any(kw in pattern_name_lower for kw in ['bull', 'long', 'buy', 'up', 'ascending']):
            direction = 'long'
        elif any(kw in pattern_name_lower for kw in ['bear', 'short', 'sell', 'down', 'descending']):
            direction = 'short'
        else:
            direction = 'neutral'

    if direction == 'neutral':
        allow_neutral = os.getenv("ABU_ALLOW_NEUTRAL_DIRECTION", "").strip().lower() in {"1", "true", "yes", "y", "on"}
        if allow_neutral:
            direction = 'long'
        else:
            return _reject("neutral_direction")
    
    # 计算市场结构与入场方式（Brooks）
    features = extract_basic_kline_features(klines, lookback=50)
    context_info = classify_market_context(klines, features) if features else {}

    entry_price, entry_type, entry_reason, entry_meta = _decide_entry_by_context(
        direction=direction,
        current_price=current_price,
        klines=klines,
        context_info=context_info,
    )
    if entry_price <= 0:
        return _reject("invalid_entry_price")

    # 计算止损和止盈（Brooks规则：RR>=2:1，5m止损>=1.5%，15m>=2%）
    recent_lows = [k['low'] for k in klines[-10:]]
    recent_highs = [k['high'] for k in klines[-10:]]

    min_stop_pct = 0.01
    if timeframe:
        tf = timeframe.lower()
        if "5m" in tf:
            min_stop_pct = 0.015
        elif "15m" in tf:
            min_stop_pct = 0.02
        elif "1h" in tf:
            min_stop_pct = 0.02
        elif "4h" in tf:
            min_stop_pct = 0.03
    max_stop_pct = 0.05

    rr1 = float(os.getenv("ABU_RR_TP1", "2.0") or 2.0)
    rr2 = float(os.getenv("ABU_RR_TP2", "3.0") or 3.0)

    if direction == 'long':
        candidate_stop = min(recent_lows) if recent_lows else entry_price * (1 - min_stop_pct)
        distance_pct = (entry_price - candidate_stop) / entry_price if entry_price else 0.0
        if distance_pct > max_stop_pct:
            return _reject(f"stop_distance_too_wide({distance_pct:.4f})")
        if distance_pct < min_stop_pct:
            stop_loss = entry_price * (1 - min_stop_pct)
            distance_pct = min_stop_pct
        else:
            stop_loss = candidate_stop
        risk = entry_price - stop_loss
        if risk <= 0:
            return _reject("risk_non_positive")
        take_profit_1 = entry_price + risk * rr1
        take_profit_2 = entry_price + risk * rr2
    else:
        candidate_stop = max(recent_highs) if recent_highs else entry_price * (1 + min_stop_pct)
        distance_pct = (candidate_stop - entry_price) / entry_price if entry_price else 0.0
        if distance_pct > max_stop_pct:
            return _reject(f"stop_distance_too_wide({distance_pct:.4f})")
        if distance_pct < min_stop_pct:
            stop_loss = entry_price * (1 + min_stop_pct)
            distance_pct = min_stop_pct
        else:
            stop_loss = candidate_stop
        risk = stop_loss - entry_price
        if risk <= 0:
            return _reject("risk_non_positive")
        take_profit_1 = entry_price - risk * rr1
        take_profit_2 = entry_price - risk * rr2
    
    all_sources = match_result.all_sources or [source]
    dedup_sources = list(dict.fromkeys([s for s in all_sources if s]))

    # 安全性校验：止损/止盈方向必须正确
    if direction == 'long':
        if stop_loss >= entry_price or take_profit_1 <= entry_price:
            return _reject("invalid_risk_geometry")
    else:
        if stop_loss <= entry_price or take_profit_1 >= entry_price:
            return _reject("invalid_risk_geometry")

    return {
        'pattern_id': match_result.pattern_id,
        'pattern_name': pattern_name,
        'pattern_type': pattern_type,
        'source': source,
        'direction': direction,
        'entry_price': entry_price,
        'entry_type': entry_type,
        'entry_reason': entry_reason,
        'entry_meta': entry_meta,
        'market_context': context_info,
        'stop_loss': stop_loss,
        'take_profit_1': take_profit_1,
        'take_profit_2': take_profit_2,
        'confidence': match_result.combined_confidence,
        'final_score': match_result.final_score,
        'all_sources': dedup_sources
    }, None


def _calc_range_bounds(klines: List[Dict], lookback: int = 40) -> Tuple[float, float]:
    if not klines:
        return 0.0, 0.0
    window = klines[-lookback:] if len(klines) > lookback else klines
    highs = [float(k.get("high") or 0.0) for k in window]
    lows = [float(k.get("low") or 0.0) for k in window]
    return (max(highs) if highs else 0.0), (min(lows) if lows else 0.0)


def _decide_entry_by_context(
    direction: str,
    current_price: float,
    klines: List[Dict],
    context_info: Dict[str, Any],
) -> Tuple[float, str, str, Dict[str, Any]]:
    """Brooks风格入场：区间用限价，趋势用市价。"""
    ctx = str(context_info.get("context") or "").lower()
    entry_type = "market"
    entry_reason = "trend_market"
    entry_meta: Dict[str, Any] = {}
    entry_price = float(current_price or 0.0)

    if ctx == "trading_range":
        entry_type = "limit"
        entry_reason = "trading_range_limit"
        range_high, range_low = _calc_range_bounds(klines, lookback=40)
        span = max(range_high - range_low, 0.0)
        buffer_pct = float(os.getenv("ABU_RANGE_ENTRY_BUFFER_PCT", "0.20") or 0.20)
        buffer_val = span * buffer_pct if span > 0 else 0.0
        if direction == "long":
            target = range_low + buffer_val
            if entry_price > 0:
                entry_price = min(target, entry_price) if target > 0 else entry_price
            else:
                entry_price = target
        else:
            target = range_high - buffer_val
            if entry_price > 0:
                entry_price = max(target, entry_price) if target > 0 else entry_price
            else:
                entry_price = target
        entry_meta = {
            "range_high": range_high,
            "range_low": range_low,
            "range_span": span,
            "range_buffer_pct": buffer_pct,
        }
    elif ctx == "strong_trend":
        entry_type = "market"
        entry_reason = "strong_trend_market"

    return entry_price, entry_type, entry_reason, entry_meta


def _load_vision_context(root: Path) -> Dict[str, Any]:
    """加载视觉过滤配置（图像匹配作为首要过滤）"""
    enabled_env = os.getenv("ABU_VISION_FILTER")
    if enabled_env is None:
        enabled = True  # 默认启用
    else:
        enabled = enabled_env.strip().lower() in {"1", "true", "yes", "y", "on"}
    model = os.getenv("ABU_VISION_MODEL", "google/gemini-2.5-flash-image")
    top_n = int(os.getenv("ABU_VISION_TOP_N", "5") or 5)
    min_score = float(os.getenv("ABU_VISION_SCORE", "0.75") or 0.75)
    min_final = float(os.getenv("ABU_VISION_FINAL_SCORE", "0.70") or 0.70)
    style = os.getenv("ABU_VISION_STYLE", "light")
    cache_ttl = int(os.getenv("ABU_VISION_CACHE_TTL", "300") or 300)
    chart_width = int(os.getenv("ABU_VISION_CHART_WIDTH", "2560") or 2560)
    chart_height = int(os.getenv("ABU_VISION_CHART_HEIGHT", "1440") or 1440)
    skip_prefixes_env = os.getenv("ABU_VISION_SKIP_PATTERN_PREFIXES", "pattern from page")
    skip_prefixes = [
        p.strip().lower()
        for p in skip_prefixes_env.split(",")
        if p.strip()
    ]
    verbose_env = os.getenv("ABU_VISION_VERBOSE")
    if verbose_env is None:
        verbose = True
    else:
        verbose = verbose_env.strip().lower() in {"1", "true", "yes", "y", "on"}

    out_dir = root / "outputs" / "vision_plan"
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    charts_dir = out_dir / f"charts_{timestamp}"
    charts_dir.mkdir(parents=True, exist_ok=True)

    vision = None
    renderer = None
    recorder = None
    if enabled:
        try:
            vision = AIVisionMatcher(model=model)
            renderer = ChartRenderer(width=chart_width, height=chart_height, style=style)
            recorder = VisionMatchRecorder(enabled=True)
        except Exception as e:
            print(f"[WARN] 视觉匹配初始化失败: {e}")
            enabled = False

    return {
        "enabled": enabled,
        "model": model,
        "top_n": top_n,
        "min_score": min_score,
        "min_final": min_final,
        "style": style,
        "chart_width": chart_width,
        "chart_height": chart_height,
        "skip_pattern_prefixes": skip_prefixes,
        "out_dir": out_dir,
        "charts_dir": charts_dir,
        "timestamp": timestamp,
        "vision": vision,
        "renderer": renderer,
        "recorder": recorder,
        "records": [],
        "calls": 0,
        "accepted": 0,
        "skipped_no_image": 0,
        "skipped_placeholder": 0,
        "algo_no_match": 0,
        "no_vision_match": 0,
        "cache": {},
        "cache_ttl": cache_ttl,
        "verbose": verbose,
    }


async def _vision_inc(vision_ctx: Dict[str, Any], key: str, amount: int = 1) -> None:
    if not vision_ctx:
        return
    lock = vision_ctx.get("lock")
    if lock is None:
        vision_ctx[key] = vision_ctx.get(key, 0) + amount
        return
    async with lock:
        vision_ctx[key] = vision_ctx.get(key, 0) + amount


def _is_placeholder_pattern(match: Any, pattern: Any, vision_ctx: Dict[str, Any]) -> bool:
    name = ""
    if pattern is not None:
        name = str(getattr(pattern, "pattern_name", "") or "").strip().lower()
    if not name and match is not None:
        name = str(getattr(match, "pattern_name", "") or "").strip().lower()
    if not name:
        return False
    prefixes = vision_ctx.get("skip_pattern_prefixes") or []
    if not any(name.startswith(p) for p in prefixes):
        return False
    # 规则1：命名为“Pattern from page ...”的条目视为占位/标题页，直接跳过
    if any(name.startswith(p) for p in prefixes):
        return True
    raw = getattr(pattern, "raw_data", {}) or {} if pattern is not None else {}
    orig = raw.get("original_fields") or {}
    gemini_annotation = raw.get("gemini_annotation")
    if gemini_annotation is None:
        gemini_annotation = raw.get("gemini_annotation_json")
    if gemini_annotation in (None, "", {}, []):
        return True
    if isinstance(gemini_annotation, str):
        if not gemini_annotation.strip():
            return True
        try:
            parsed = json.loads(gemini_annotation)
        except Exception:
            return False
        return parsed in (None, "", {}, [])
    return False


async def _select_match_by_vision(
    matches: List[Any],
    matcher: EnhancedHybridMatcher,
    klines: List[Dict],
    symbol: str,
    timeframe: str,
    vision_ctx: Dict[str, Any],
) -> Optional[Any]:
    if not vision_ctx.get("enabled"):
        return matches[0] if matches else None

    vision = vision_ctx.get("vision")
    renderer = vision_ctx.get("renderer")
    if not vision or not renderer:
        return None

    chart_path = vision_ctx["charts_dir"] / f"{symbol}_{timeframe}_{vision_ctx['timestamp']}.png"
    chart_image = render_chart_image(
        renderer,
        klines,
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
        return None

    accepted = []
    processed = 0
    cache = vision_ctx.get("cache", {})
    cache_ttl = int(vision_ctx.get("cache_ttl") or 0)
    cache_key_base = make_cache_key(symbol, timeframe, klines[-50:] if len(klines) >= 50 else klines)
    verbose = bool(vision_ctx.get("verbose"))

    for match in matches:
        if processed >= vision_ctx["top_n"]:
            break
        pattern = matcher.pattern_library.patterns.get(match.pattern_id)
        if _is_placeholder_pattern(match, pattern, vision_ctx):
            await _vision_inc(vision_ctx, "skipped_placeholder", 1)
            continue
        pattern_image = resolve_pattern_image_path(
            pattern.image_path if pattern else None,
            pattern.page_number if pattern else None,
        )
        if not pattern_image:
            await _vision_inc(vision_ctx, "skipped_no_image", 1)
            continue

        processed += 1
        cache_key = f"{cache_key_base}_{match.pattern_id}"
        vision_result = None
        from_cache = False
        if cache_ttl > 0 and cache_key in cache:
            cached = cache.get(cache_key) or {}
            if time.time() - cached.get("ts", 0) < cache_ttl:
                vision_result = cached.get("result")
                from_cache = True
            else:
                cache.pop(cache_key, None)
        recorder = vision_ctx.get("recorder")
        if vision_result is None and recorder:
            cached_db = recorder.fetch_cached(cache_key_base, match.pattern_id)
            if cached_db:
                vision_result = cached_db.get("vision_result") or {}
                from_cache = True
        if vision_result is None:
            await _vision_inc(vision_ctx, "calls", 1)
            vision_result = await asyncio.to_thread(
                vision.compare_two_images,
                image1_path=pattern_image,
                image2_path=chart_image,
                context=f"{symbol} {timeframe}",
            )
            if cache_ttl > 0:
                cache[cache_key] = {"result": vision_result, "ts": time.time()}
        if vision_result and isinstance(vision_result, dict):
            raw_score = vision_result.get("similarity_score", 0.0)
            vision_score = raw_score / 100.0 if isinstance(raw_score, (int, float)) else 0.0
        elif vision_result:
            vision_score = vision_result.similarity_score / 100.0
        else:
            vision_score = 0.0
        final_score = (match.algorithm_score * 0.4) + (vision_score * 0.6)
        accepted_flag = vision_score >= vision_ctx["min_score"] and final_score >= vision_ctx["min_final"]

        record = {
            "symbol": symbol,
            "timeframe": timeframe,
            "pattern_name": match.pattern_name,
            "pattern_type": match.pattern_type,
            "pattern_id": match.pattern_id,
            "pattern_image": str(pattern_image),
            "chart_image": str(chart_image),
            "algorithm_score": match.algorithm_score,
            "vision_score": vision_score,
            "final_score": final_score,
            "accepted": accepted_flag,
            "vision_result": asdict(vision_result) if vision_result and not isinstance(vision_result, dict) else (vision_result or {}),
            "from_cache": from_cache,
        }
        if verbose:
            cache_tag = "cache" if from_cache else "live"
            print(
                f"[VISION] {symbol} {timeframe} | {match.pattern_name} "
                f"algo={match.algorithm_score:.3f} vision={vision_score:.3f} final={final_score:.3f} "
                f"{'✅' if accepted_flag else '❌'} ({cache_tag})",
                file=sys.stderr,
            )
        vision_ctx["records"].append(record)
        if recorder:
            recorder.record_match({
                "source": "abu_generate_plan",
                "batch_id": vision_ctx.get("timestamp"),
                "symbol": symbol,
                "timeframe": timeframe,
                "pattern_id": match.pattern_id,
                "pattern_name": match.pattern_name,
                "pattern_type": match.pattern_type,
                "algorithm_score": match.algorithm_score,
                "vision_score": vision_score,
                "final_score": final_score,
                "accepted": record["accepted"],
                "model": vision_ctx.get("model"),
                "pattern_image": str(pattern_image),
                "chart_image": str(chart_image),
                "vision_result": record.get("vision_result"),
                "extra": {
                    "from_cache": from_cache,
                    "cache_key": cache_key_base,
                },
            })

        if record["accepted"]:
            await _vision_inc(vision_ctx, "accepted", 1)
            accepted.append((final_score, match, record))

    if not accepted:
        return None

    accepted.sort(key=lambda x: x[0], reverse=True)
    best_final, best_match, best_record = accepted[0]
    best_match._vision_score = best_record.get("vision_score")
    best_match._vision_final = best_record.get("final_score")
    best_match._vision_result = best_record.get("vision_result")
    return best_match


def _write_html_report(records: List[Dict], out_dir: Path, timestamp: str) -> Optional[Path]:
    if not records:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / f"assets_{timestamp}"
    assets_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"vision_plan_summary_{timestamp}.html"

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Vision Plan Summary</title>",
        "<style>body{font-family:Arial,sans-serif} .case{margin:24px 0} .imgs{display:flex;gap:16px} img{max-width:48%;height:auto;border:1px solid #ccc} pre{white-space:pre-wrap}</style>",
        "</head><body>",
        "<h1>Vision Filter Summary</h1>",
    ]

    for rec in records:
        chart = Path(rec.get("chart_image", ""))
        pattern = Path(rec.get("pattern_image", ""))
        chart_copy = assets_dir / f"{Path(rec['symbol']).stem}_{rec['timeframe']}_chart{chart.suffix or '.png'}"
        pattern_copy = assets_dir / f"{Path(rec['symbol']).stem}_{rec['timeframe']}_pattern{pattern.suffix or '.png'}"
        if chart.exists() and not chart_copy.exists():
            shutil.copy2(chart, chart_copy)
        if pattern.exists() and not pattern_copy.exists():
            shutil.copy2(pattern, pattern_copy)

        vr = rec.get("vision_result", {})
        key_matches = vr.get("key_matches") or []
        differences = vr.get("differences") or []
        reasoning = (vr.get("reasoning") or "").strip()

        parts.extend(
            [
                "<div class='case'>",
                f"<h2>{rec['symbol']} {rec['timeframe']} | {rec['pattern_name']} | "
                f"algo={rec.get('algorithm_score', 0):.3f} vision={rec.get('vision_score', 0):.3f} "
                f"final={rec.get('final_score', 0):.3f} "
                f"{'✅' if rec.get('accepted') else '❌'}</h2>",
                "<div class='imgs'>",
                f"<div><h3>Pattern</h3><img src='{assets_dir.name}/{pattern_copy.name}'></div>",
                f"<div><h3>Chart</h3><img src='{assets_dir.name}/{chart_copy.name}'></div>",
                "</div>",
                "<h3>Key Matches</h3>",
                "<pre>" + "\n".join([f"- {k}" for k in key_matches]) + "</pre>",
                "<h3>Differences</h3>",
                "<pre>" + "\n".join([f"- {d}" for d in differences]) + "</pre>",
                "<h3>Reasoning (truncated)</h3>",
                "<pre>" + (reasoning[:900] + ("..." if len(reasoning) > 900 else "")) + "</pre>",
                "</div>",
            ]
        )

    parts.append("</body></html>")
    html_path.write_text("\n".join(parts), encoding="utf-8")
    return html_path


def _write_top_matches_html(
    records: List[Dict],
    out_dir: Path,
    timestamp: str,
    top_n: int = 5,
) -> Optional[Path]:
    if not records:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / f"top_matches_assets_{timestamp}"
    assets_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"vision_top_matches_{timestamp}.html"

    grouped: Dict[Tuple[str, str], List[Dict]] = {}
    for rec in records:
        key = (rec.get("symbol", ""), rec.get("timeframe", ""))
        grouped.setdefault(key, []).append(rec)

    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'><title>Vision Top Matches</title>",
        "<style>body{font-family:Arial,sans-serif} .case{margin:24px 0} .imgs{display:flex;gap:16px} "
        "img{max-width:48%;height:auto;border:1px solid #ccc} pre{white-space:pre-wrap}</style>",
        "</head><body>",
        f"<h1>Vision Top {top_n} Matches</h1>",
        "<p>Each symbol/timeframe lists its top matches by final score, with key matches and differences.</p>",
    ]

    for (symbol, timeframe), recs in grouped.items():
        if not symbol or not timeframe:
            continue
        sorted_recs = sorted(recs, key=lambda r: r.get("final_score", 0.0), reverse=True)[: max(1, top_n)]
        parts.append(f"<h2>{symbol} {timeframe}</h2>")
        for idx, rec in enumerate(sorted_recs, 1):
            pattern = Path(rec.get("pattern_image", ""))
            chart = Path(rec.get("chart_image", ""))
            pattern_copy = assets_dir / f"{symbol}_{timeframe}_{idx}_pattern{pattern.suffix or '.png'}"
            chart_copy = assets_dir / f"{symbol}_{timeframe}_{idx}_chart{chart.suffix or '.png'}"
            try:
                if pattern.exists() and not pattern_copy.exists():
                    shutil.copy2(pattern, pattern_copy)
                if chart.exists() and not chart_copy.exists():
                    shutil.copy2(chart, chart_copy)
            except Exception:
                pass

            vr = rec.get("vision_result", {})
            key_matches = vr.get("key_matches") or []
            differences = vr.get("differences") or []
            reasoning = (vr.get("reasoning") or "").strip()

            parts.extend(
                [
                    "<div class='case'>",
                    f"<h3>{idx}. {rec.get('pattern_name')} | "
                    f"algo={rec.get('algorithm_score', 0):.3f} "
                    f"vision={rec.get('vision_score', 0):.3f} "
                    f"final={rec.get('final_score', 0):.3f} "
                    f"{'✅' if rec.get('accepted') else '❌'}</h3>",
                    "<div class='imgs'>",
                    f"<div><h4>Pattern</h4><img src='{assets_dir.name}/{pattern_copy.name}'></div>",
                    f"<div><h4>Chart</h4><img src='{assets_dir.name}/{chart_copy.name}'></div>",
                    "</div>",
                    "<h4>Key Matches</h4>",
                    "<pre>" + "\n".join([f"- {k}" for k in key_matches]) + "</pre>",
                    "<h4>Differences</h4>",
                    "<pre>" + "\n".join([f"- {d}" for d in differences]) + "</pre>",
                    "<h4>Reasoning (truncated)</h4>",
                    "<pre>" + (reasoning[:900] + ("..." if len(reasoning) > 900 else "")) + "</pre>",
                    "</div>",
                ]
            )

    parts.append("</body></html>")
    html_path.write_text("\n".join(parts), encoding="utf-8")
    return html_path


def _summarize_vision_result(vision_result: Optional[Dict[str, Any]], max_reason: int = 400) -> Optional[Dict[str, Any]]:
    if not vision_result or not isinstance(vision_result, dict):
        return None
    summary = {
        "similarity_score": vision_result.get("similarity_score"),
        "confidence": vision_result.get("confidence"),
        "key_matches": vision_result.get("key_matches") or [],
        "differences": vision_result.get("differences") or [],
    }
    reasoning = vision_result.get("reasoning") or ""
    if isinstance(reasoning, str) and reasoning:
        summary["reasoning"] = reasoning[:max_reason] + ("..." if len(reasoning) > max_reason else "")
    return summary


def _format_gemini_plan(plan_result: Dict) -> str:
    """格式化Gemini交易计划（摘要）"""
    if not plan_result:
        return "- **Gemini计划**: 无"
    if not plan_result.get("ok"):
        err = plan_result.get("error") or "生成失败"
        return f"- **Gemini计划**: 失败（{err}）"

    plan = plan_result.get("plan") or {}
    entry = plan.get("entry") or {}
    stop = plan.get("stop_loss") or {}
    tps = plan.get("take_profits") or []
    tp1 = tps[0].get("price") if tps and isinstance(tps[0], dict) else None
    rr = None
    risk = plan.get("risk") or {}
    if isinstance(risk, dict):
        rr = risk.get("risk_reward")
    if rr is None:
        rr = plan.get("risk_reward")
    invalidation = plan.get("invalidation")

    entry_price = entry.get("price")
    entry_zone = entry.get("zone")
    entry_text = entry_price if entry_price is not None else entry_zone

    parts = [
        f"入场={entry_text}",
        f"止损={stop.get('price')}",
        f"TP1={tp1}",
    ]
    if rr is not None:
        parts.append(f"RR={rr}")
    if invalidation:
        parts.append(f"失效={invalidation}")
    return "- **Gemini计划**: " + " / ".join(parts)


def _calc_rr(entry: Optional[float], stop_loss: Optional[float], take_profit_1: Optional[float], direction: str) -> Optional[float]:
    if entry is None or stop_loss is None or take_profit_1 is None:
        return None
    try:
        entry = float(entry)
        stop_loss = float(stop_loss)
        take_profit_1 = float(take_profit_1)
    except Exception:
        return None
    if direction.lower() == "long":
        risk = entry - stop_loss
        reward = take_profit_1 - entry
    else:
        risk = stop_loss - entry
        reward = entry - take_profit_1
    if risk <= 0:
        return None
    return reward / risk


def _safe_json_payload(value: Any) -> Optional[Any]:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {"text": value}
    try:
        return json.loads(json.dumps(value, default=str, ensure_ascii=False))
    except Exception:
        return {"text": str(value)}


def _save_signal_to_db(signal: Dict[str, Any], db_ctx: Optional[Dict[str, Any]]) -> Optional[int]:
    if not db_ctx or not db_ctx.get("enabled"):
        return None
    db = db_ctx.get("db")
    if db is None:
        return None
    try:
        ts = signal.get("kline_timestamp")
        signal_time = datetime.fromtimestamp(float(ts)) if ts else datetime.now()
    except Exception:
        signal_time = datetime.now()

    direction = (signal.get("direction") or "").lower()
    rr = signal.get("risk_reward_ratio")
    if rr is None:
        rr = _calc_rr(
            signal.get("entry_price"),
            signal.get("stop_loss"),
            signal.get("take_profit_1"),
            direction or "long",
        )

    notes_payload = {
        "pattern_name": signal.get("pattern_name"),
        "pattern_type": signal.get("pattern_type"),
        "source": signal.get("source"),
        "vision_score": signal.get("vision_score"),
        "final_score": signal.get("final_score"),
        "brooks_validation": signal.get("brooks_validation"),
        "entry_type": signal.get("entry_type"),
        "entry_reason": signal.get("entry_reason"),
        "entry_meta": _safe_json_payload(signal.get("entry_meta")),
        "market_context": _safe_json_payload(signal.get("market_context")),
    }
    if signal.get("gemini_plan"):
        try:
            notes_payload["gemini_plan_summary"] = _format_gemini_plan(signal.get("gemini_plan"))
        except Exception:
            notes_payload["gemini_plan_summary"] = None
        notes_payload["gemini_plan"] = _safe_json_payload(signal.get("gemini_plan"))

    payload = {
        "signal_time": signal_time,
        "timeframe": signal.get("timeframe"),
        "symbol": signal.get("symbol"),
        "signal_type": direction or None,
        "entry_price": signal.get("entry_price"),
        "stop_loss": signal.get("stop_loss"),
        "take_profit_1": signal.get("take_profit_1"),
        "take_profit_2": signal.get("take_profit_2"),
        "entry_model": signal.get("pattern_name"),
        "strength": None,
        "risk_reward_ratio": rr,
        "volatility_level": None,
        "system_name": "abu",
        "score": signal.get("final_score") or signal.get("confidence"),
        "notes": json.dumps(notes_payload, ensure_ascii=False),
        "status": "pending",
        "created_at": datetime.now(),
    }
    try:
        return db.add_trading_signal(payload)
    except Exception as exc:
        print(f"[WARN] 写入交易信号失败: {exc}", file=sys.stderr)
        return None


def _build_live_signal_lines(coin: Dict[str, Any], plan: Dict[str, Any]) -> List[str]:
    signal = plan.get("signal", {})
    timeframe = plan.get("timeframe", "")
    symbol = coin.get("symbol", "")
    current_price = plan.get("current_price") if plan else None
    if current_price is None:
        current_price = coin.get("price")
    lines: List[str] = []
    lines.append(f"## {symbol} ({timeframe})")
    lines.append("")
    if coin.get("rank"):
        lines.append(f"- **排名**: #{coin['rank']}")
    if current_price is not None:
        lines.append(f"- **当前价格**: ${float(current_price):,.4f}")
    lines.append(f"- **24h交易量**: ${coin['volume_24h']:,.0f}")
    lines.append("")
    lines.append(f"- **模式**: {signal.get('pattern_name')} ({signal.get('pattern_type')})")
    lines.append(f"- **方向**: {signal.get('direction', '').upper()}")
    entry_type = signal.get("entry_type") or ""
    entry_label = f"{entry_type}".upper() if entry_type else "MARKET"
    lines.append(f"- **入场价**: ${signal.get('entry_price', 0):,.4f} ({entry_label})")
    lines.append(f"- **止损价**: ${signal.get('stop_loss', 0):,.4f}")
    lines.append(f"- **止盈1**: ${signal.get('take_profit_1', 0):,.4f}")
    lines.append(f"- **止盈2**: ${signal.get('take_profit_2', 0):,.4f}")
    if signal.get("confidence") is not None:
        lines.append(f"- **置信度**: {signal['confidence']:.2%}")
    if signal.get("all_sources"):
        lines.append(f"- **数据源**: {', '.join(signal['all_sources'])}")
    if signal.get("vision_score") is not None:
        lines.append(f"- **视觉分数**: {signal['vision_score']:.3f}")
    ts = signal.get("kline_timestamp")
    if ts:
        try:
            ts_str = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"- **K线时间**: {ts_str}")
        except Exception:
            pass
    brooks = signal.get("brooks_validation")
    if isinstance(brooks, dict):
        status = brooks.get("status")
        score = brooks.get("score")
        if status:
            if score is not None:
                lines.append(f"- **Brooks验证**: {status.upper()} (score={score:.1f})")
            else:
                lines.append(f"- **Brooks验证**: {status.upper()}")
        issues = brooks.get("issues") or []
        warnings = brooks.get("warnings") or []
        if issues:
            lines.append(f"- **Brooks问题**: {'; '.join(issues[:3])}")
        if warnings:
            lines.append(f"- **Brooks警告**: {'; '.join(warnings[:3])}")
    market_ctx = signal.get("market_context") or {}
    if isinstance(market_ctx, dict):
        ctx_label = market_ctx.get("label") or market_ctx.get("context")
        if ctx_label:
            lines.append(f"- **市场结构**: {ctx_label}")
    if signal.get("gemini_plan"):
        lines.append(_format_gemini_plan(signal.get("gemini_plan")))
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


class LiveReportWriter:
    def __init__(self, path: Path, header_lines: List[str], lock: Optional[asyncio.Lock] = None):
        self.path = path
        self.lock = lock or asyncio.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(header_lines) + "\n", encoding="utf-8")

    async def append_lines(self, lines: List[str]) -> None:
        if not lines:
            return
        async with self.lock:
            await asyncio.to_thread(self._append_sync, lines)

    def _append_sync(self, lines: List[str]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
            f.flush()


async def _debug_pause_if_needed(debug_ctx: Optional[Dict[str, Any]]) -> None:
    if not debug_ctx or not debug_ctx.get("enabled"):
        return
    limit = int(debug_ctx.get("limit", 0) or 0)
    if limit <= 0:
        return
    lock = debug_ctx.get("lock")
    should_pause = False
    count = 0
    if lock is None:
        debug_ctx["count"] = debug_ctx.get("count", 0) + 1
        count = debug_ctx["count"]
        should_pause = count == limit and not debug_ctx.get("paused")
        if should_pause:
            debug_ctx["paused"] = True
    else:
        async with lock:
            debug_ctx["count"] = debug_ctx.get("count", 0) + 1
            count = debug_ctx["count"]
            should_pause = count == limit and not debug_ctx.get("paused")
            if should_pause:
                debug_ctx["paused"] = True
    if should_pause:
        prompt = f"[DEBUG] 已生成 {count} 个信号，已暂停。请检查后按回车继续..."
        print(prompt)
        await asyncio.to_thread(input, "")


async def generate_coin_plan(
    symbol: str,
    timeframe: str,
    matcher: EnhancedHybridMatcher,
    plan_ctx: Optional[Dict[str, Any]] = None,
    vision_ctx: Optional[Dict[str, Any]] = None,
    brooks_ctx: Optional[Dict[str, Any]] = None,
    db_ctx: Optional[Dict[str, Any]] = None,
) -> Optional[Dict]:
    """为单个币种生成交易计划"""
    # 获取K线数据
    klines = await asyncio.to_thread(get_kline_gateio, symbol, timeframe, limit=200)
    if not klines or len(klines) < 50:
        _log_reject(symbol, timeframe, "kline_insufficient", extra={"count": len(klines or [])})
        return None
    klines = sorted(klines, key=lambda x: x.get("timestamp", 0))
    current_price = klines[-1]['close']
    
    # 提取特征
    query_features = extract_features_from_klines(klines, timeframe)
    if not query_features:
        _log_reject(symbol, timeframe, "feature_empty")
        return None
    
    # 匹配模式（只取Top 1）
    try:
        klines_dict = {timeframe: klines}
        results = await matcher.async_match(
            query_features=query_features,
            klines_dict=klines_dict,
            symbol=f"{symbol}_USDT"
        )
        
        if not results:
            if vision_ctx is not None:
                await _vision_inc(vision_ctx, "algo_no_match", 1)
            _log_reject(symbol, timeframe, "algo_no_match")
            return None
        
        # 先进行视觉过滤（首要过滤）
        best_match = await _select_match_by_vision(
            results,
            matcher,
            klines,
            symbol,
            timeframe,
            vision_ctx or {},
        )
        if not best_match:
            if vision_ctx is not None:
                await _vision_inc(vision_ctx, "no_vision_match", 1)
            extra = {}
            if vision_ctx:
                extra = {
                    "min_score": vision_ctx.get("min_score"),
                    "min_final": vision_ctx.get("min_final"),
                }
            top_match = results[0] if results else None
            _log_reject(symbol, timeframe, "vision_reject", match=top_match, extra=extra)
            return None

        direction_hint = None
        try:
            pattern_meta = matcher.pattern_library.patterns.get(best_match.pattern_id)
        except Exception:
            pattern_meta = None
        if pattern_meta is not None:
            direction_hint = getattr(pattern_meta, "direction", None)
            if not direction_hint and isinstance(getattr(pattern_meta, "structured_features", None), dict):
                direction_hint = pattern_meta.structured_features.get("direction")

        signal, reject_reason = generate_signal_from_match(
            best_match,
            current_price,
            klines,
            direction_hint=direction_hint,
            timeframe=timeframe,
        )
        
        if signal:
            signal["symbol"] = symbol
            signal["timeframe"] = timeframe
            signal["kline_timestamp"] = klines[-1].get("timestamp")
            if hasattr(best_match, "_vision_score"):
                signal["vision_score"] = best_match._vision_score
                signal["final_score"] = best_match._vision_final
                signal["vision_result"] = best_match._vision_result
            if brooks_ctx and brooks_ctx.get("enabled"):
                validator = brooks_ctx.get("validator")
                if validator:
                    result = validator.validate_signal(signal)
                    signal["brooks_validation"] = {
                        "valid": result.is_valid,
                        "status": result.level.value,
                        "score": result.score,
                        "issues": result.issues,
                        "warnings": result.warnings,
                    }
                    if not result.is_valid and brooks_ctx.get("strict"):
                        issue = result.issues[0] if result.issues else None
                        extra = {"issue": issue} if issue else None
                        _log_reject(symbol, timeframe, "brooks_strict", match=best_match, extra=extra)
                        return None
            should_call_plan = False
            plan_lock = plan_ctx.get("lock") if plan_ctx else None
            if plan_lock is None:
                if plan_budget_ok(plan_ctx):
                    plan_ctx["calls"] = plan_ctx.get("calls", 0) + 1
                    should_call_plan = True
            else:
                async with plan_lock:
                    if plan_budget_ok(plan_ctx):
                        plan_ctx["calls"] = plan_ctx.get("calls", 0) + 1
                        should_call_plan = True
            if should_call_plan:
                match_payload = {
                    "pattern_name": best_match.pattern_name,
                    "pattern_type": best_match.pattern_type,
                    "source": best_match.source,
                    "similarity": best_match.algorithm_score,
                    "confidence": best_match.combined_confidence,
                    "final_score": best_match.final_score,
                }
                extra_context = {}
                ebook_rules = get_ebook_rules(
                    plan_ctx, best_match.pattern_name, best_match.pattern_type
                )
                if ebook_rules:
                    extra_context["ebook_rules"] = ebook_rules
                if hasattr(best_match, "_vision_result"):
                    vision_summary = _summarize_vision_result(best_match._vision_result)
                    if vision_summary:
                        extra_context["vision_match"] = vision_summary
                plan_result = await asyncio.to_thread(
                    generate_trade_plan,
                    symbol=symbol,
                    timeframe=timeframe,
                    match=match_payload,
                    signal=signal,
                    klines=klines,
                    extra_context=extra_context,
                    model=plan_ctx.get("model"),
                )
                signal["gemini_plan"] = plan_result
            db_id = _save_signal_to_db(signal, db_ctx)
            if db_id:
                signal["db_id"] = db_id
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'current_price': current_price,
                'signal': signal
            }
        _log_reject(
            symbol,
            timeframe,
            reject_reason or "signal_build_failed",
            match=best_match,
        )
    except Exception as e:
        print(f"[WARN] {symbol} {timeframe} 匹配失败: {e}", file=sys.stderr)
    
    return None


async def _process_coin(
    index: int,
    total: int,
    coin: Dict[str, Any],
    timeframe: str,
    matcher: EnhancedHybridMatcher,
    plan_ctx: Optional[Dict[str, Any]],
    vision_ctx: Optional[Dict[str, Any]],
    brooks_ctx: Optional[Dict[str, Any]],
    db_ctx: Optional[Dict[str, Any]],
    writer: LiveReportWriter,
    sem: asyncio.Semaphore,
    debug_ctx: Optional[Dict[str, Any]],
) -> int:
    symbol = coin["symbol"]
    print(f"   [{index}/{total}] {symbol} {timeframe}...", end=" ", flush=True)

    try:
        async with sem:
            plan = await generate_coin_plan(symbol, timeframe, matcher, plan_ctx, vision_ctx, brooks_ctx, db_ctx)
            if plan:
                await writer.append_lines(_build_live_signal_lines(coin, plan))
                await _debug_pause_if_needed(debug_ctx)
    except Exception as e:
        print(f"[WARN] {symbol} {timeframe} 处理失败: {e}", file=sys.stderr)
        return 0

    if plan:
        print("✓")
    else:
        print("✗ (无信号)")
    return 1 if plan else 0


def _resolve_timeframes() -> List[str]:
    parser = argparse.ArgumentParser(description="ABU计划生成参数", add_help=False)
    parser.add_argument("--only-timeframe", choices=TIMEFRAMES)
    parser.add_argument("--from-timeframe", choices=TIMEFRAMES)
    args, _ = parser.parse_known_args()

    only_tf = args.only_timeframe or os.getenv("ABU_ONLY_TIMEFRAME", "").strip().lower()
    from_tf = args.from_timeframe or os.getenv("ABU_FROM_TIMEFRAME", "").strip().lower()

    if only_tf:
        return [only_tf]
    if from_tf and from_tf in TIMEFRAMES:
        start_idx = TIMEFRAMES.index(from_tf)
        return TIMEFRAMES[start_idx:]
    return list(TIMEFRAMES)


def _reject_log_enabled() -> bool:
    val = os.getenv("ABU_LOG_REJECTS")
    if val is None:
        return True
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


def _log_reject(
    symbol: str,
    timeframe: str,
    reason: str,
    match: Optional[Any] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if not _reject_log_enabled():
        return
    parts = [f"[REJECT] {symbol} {timeframe} {reason}"]
    if match is not None:
        name = getattr(match, "pattern_name", None)
        ptype = getattr(match, "pattern_type", None)
        src = getattr(match, "source", None)
        algo = getattr(match, "algorithm_score", None)
        vision = getattr(match, "_vision_score", None)
        final = getattr(match, "_vision_final", None)
        if name:
            parts.append(f"pattern={name}")
        if ptype:
            parts.append(f"type={ptype}")
        if src:
            parts.append(f"source={src}")
        if algo is not None:
            parts.append(f"algo={algo:.3f}")
        if vision is not None:
            parts.append(f"vision={vision:.3f}")
        if final is not None:
            parts.append(f"final={final:.3f}")
    if extra:
        detail = "; ".join([f"{k}={v}" for k, v in extra.items()])
        if detail:
            parts.append(detail)
    print(" | ".join(parts))


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("ABU系统v3.0 - 30币种交易计划生成器")
    print("=" * 80)
    print()

    run_timeframes = _resolve_timeframes()
    if not run_timeframes:
        print("[ERROR] 未指定有效时间框架", file=sys.stderr)
        return 1

    ranks = _build_rank_list()
    if os.getenv("ABU_DRY_RUN", "").strip().lower() in {"1", "true", "yes", "y", "on"}:
        return _run_dry_checks(ROOT, ranks)
    
    # 1. 获取指定排名币种（排除稳定币）
    print("1. 获取指定排名币种（排除稳定币）...")
    print("   规则: top5 + 20-24 + 60-64 + 140-144 + 300-304 + 620-624")
    cache_path = _coin_cache_path(ROOT)
    refresh = os.getenv("ABU_COIN_LIST_REFRESH", "").strip().lower() in {"1", "true", "yes", "y", "on"}
    coins = None
    if not refresh:
        coins = _load_cached_coins(cache_path)
        if coins:
            print(f"   使用缓存币种列表: {cache_path}")
    if not coins:
        coins = get_ranked_coins(ranks)
        if coins:
            _save_cached_coins(cache_path, coins, ranks)
            print(f"   已保存币种列表: {cache_path}")
    if not coins:
        print("[ERROR] 无法获取币种列表")
        return 1

    limit_env = os.getenv("ABU_COIN_LIMIT", "").strip()
    if limit_env:
        try:
            limit_n = int(limit_env)
        except Exception:
            limit_n = 0
        if limit_n > 0 and len(coins) > limit_n:
            coins = coins[:limit_n]
            print(f"[INFO] 已限制币种数量: {limit_n}")
    
    expected = len(ranks)
    if len(coins) < expected:
        print(f"[WARN] 仅获取到 {len(coins)}/{expected} 个币种（交易对数量不足或被过滤）")
        found_ranks = {c.get("rank") for c in coins if c.get("rank")}
        missing = [r for r in ranks if r not in found_ranks]
        if missing:
            print(f"[WARN] 缺失排名: {missing}")
    else:
        print(f"   找到 {len(coins)} 个币种")
    for i, coin in enumerate(coins, 1):
        print(f"   {i}. #{coin.get('rank', '?')} {coin['symbol']} (24h交易量: ${coin['volume_24h']:,.0f})")
    print()
    
    # 2. 初始化匹配器（使用Gemini Flash）
    print("2. 初始化ABU系统v3.0匹配器...")
    print("   数据源: Gemini Flash (主要)")
    matcher = EnhancedHybridMatcher(
        strategy='comprehensive',
        use_async=True,
        use_vision=False,  # 不使用视觉验证以加快速度
        top_k=5,  # 每个币种只需要1个信号，但获取Top 5候选
        min_confidence=0.2,
        min_similarity=0.3
    )
    print("   [OK] 匹配器初始化完成")
    print()

    plan_ctx = load_plan_context()
    if plan_ctx.get("enabled"):
        print(f"[INFO] Gemini交易计划已启用 (model={plan_ctx.get('model')})")
        if plan_ctx.get("ebook_enabled"):
            print("[INFO] Ebook规则: 已启用")
        else:
            print("[WARN] Ebook规则: 未启用或不可用")
    else:
        print("[INFO] Gemini交易计划未启用（可设置 ABU_GEMINI_PLAN=1）")

    vision_ctx = _load_vision_context(ROOT)
    if vision_ctx.get("enabled"):
        print(f"[INFO] 视觉过滤已启用 (model={vision_ctx.get('model')})")
        print(f"[INFO] 视觉阈值: score>={vision_ctx['min_score']}, final>={vision_ctx['min_final']}")
        print(f"[INFO] 视觉日志: {'verbose' if vision_ctx.get('verbose') else 'quiet'}")
    else:
        print("[INFO] 视觉过滤未启用（可设置 ABU_VISION_FILTER=1）")

    brooks_enabled = os.getenv("ABU_BROOKS_VALIDATE", "").strip().lower() not in {"0", "false", "no", "off"}
    brooks_strict = os.getenv("ABU_BROOKS_STRICT", "").strip().lower() not in {"0", "false", "no", "off"}
    brooks_ctx = {
        "enabled": brooks_enabled,
        "strict": brooks_strict,
        "validator": BrooksTradingValidator() if brooks_enabled else None,
    }
    if brooks_enabled:
        print(f"[INFO] Brooks验证已启用 (strict={'on' if brooks_strict else 'off'})")
    else:
        print("[INFO] Brooks验证未启用（可设置 ABU_BROOKS_VALIDATE=1）")

    save_db_env = os.getenv("ABU_SAVE_DB")
    if save_db_env is None or not save_db_env.strip():
        save_db_enabled = True
    else:
        save_db_enabled = save_db_env.strip().lower() in {"1", "true", "yes", "y", "on"}
    db_ctx = {"enabled": False, "db": None}
    if save_db_enabled:
        try:
            db_ctx["db"] = TraderDBManager("abu")
            db_ctx["enabled"] = True
            print("[INFO] 交易计划写入PostgreSQL: 已启用")
        except Exception as e:
            print(f"[WARN] 交易计划写入PostgreSQL初始化失败: {e}")
            db_ctx["enabled"] = False
    else:
        print("[INFO] 交易计划写入PostgreSQL: 未启用（可设置 ABU_SAVE_DB=1）")

    plan_ctx["lock"] = asyncio.Lock()
    if vision_ctx.get("enabled"):
        vision_ctx["lock"] = asyncio.Lock()

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 3. 按时间框架依次生成信号（15m -> 1h -> 4h）
    concurrency = int(os.getenv("ABU_CONCURRENCY", "4") or 4)
    concurrency = max(1, concurrency)
    debug_limit = int(os.getenv("ABU_DEBUG_STOP_AFTER", "0") or 0)
    debug_ctx = None
    if debug_limit > 0:
        debug_ctx = {
            "enabled": True,
            "limit": debug_limit,
            "count": 0,
            "paused": False,
            "lock": asyncio.Lock(),
        }
        if concurrency != 1:
            print(f"[DEBUG] ABU_DEBUG_STOP_AFTER={debug_limit} 启用，强制并发度=1")
            concurrency = 1
    print("3. 生成交易计划（按时间框架分文件）...")
    print(f"   [INFO] 并发度: {concurrency}")
    print(f"   [INFO] 时间框架: {', '.join(run_timeframes)}")

    sem = asyncio.Semaphore(concurrency)
    overall_counts = {}

    for timeframe in run_timeframes:
        report_path = ROOT / "trading_signals" / f"ABU_v3_ranked_30_coins_{timeframe}_{run_ts}.md"
        header_lines = [
            f"# ABU系统v3.0 - 30币种交易计划（{timeframe}，实时追加）",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "**数据源**: Gemini Flash模式库（主要）",
            f"**币种数量**: {len(coins)}",
            "**选择规则**: top5 + 20-24 + 60-64 + 140-144 + 300-304 + 620-624（排除稳定币）",
            f"**时间框架**: {timeframe}",
            "**实时写入**: 已启用（信号生成即写入）",
            f"**Brooks验证**: {'开启' if brooks_enabled else '关闭'}{'(严格)' if brooks_enabled and brooks_strict else ''}",
            "",
            "---",
            "",
        ]
        writer = LiveReportWriter(report_path, header_lines)
        print(f"   [INFO] {timeframe} 报告: {report_path}")

        tasks = [
            asyncio.create_task(
                _process_coin(
                    i,
                    len(coins),
                    coin,
                    timeframe,
                    matcher,
                    plan_ctx,
                    vision_ctx,
                    brooks_ctx,
                    db_ctx,
                    writer,
                    sem,
                    debug_ctx,
                )
            )
            for i, coin in enumerate(coins, 1)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        signals_count = 0
        for r in results:
            if isinstance(r, Exception):
                print(f"[WARN] {timeframe} 并发任务失败: {r}", file=sys.stderr)
                continue
            signals_count += int(r)
        overall_counts[timeframe] = signals_count

        print()
        summary_lines = [
            "## 汇总",
            "",
            f"- **有信号的币种**: {signals_count}",
            f"- **总信号数**: {signals_count}",
            f"- **完成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        await writer.append_lines(summary_lines)
        print(f"   [OK] {timeframe} 报告已保存: {report_path}")

    print()
    print("4. 全局汇总...")
    total_signals = sum(overall_counts.values())
    detail = ", ".join([f"{tf}: {overall_counts.get(tf, 0)}" for tf in run_timeframes])
    print(f"   [OK] 总信号数: {total_signals} ({detail})")

    if vision_ctx.get("enabled") and vision_ctx.get("records"):
        html_path = _write_html_report(vision_ctx["records"], vision_ctx["out_dir"], vision_ctx["timestamp"])
        if html_path:
            print(f"   [OK] 视觉摘要HTML: {html_path}")
        top_n = int(os.getenv("ABU_VISION_TOP_MATCHES", "5") or 5)
        top_path = _write_top_matches_html(
            vision_ctx["records"],
            vision_ctx["out_dir"],
            vision_ctx["timestamp"],
            top_n=top_n,
        )
        if top_path:
            print(f"   [OK] 视觉Top匹配HTML: {top_path}")
        print(f"   [INFO] 视觉调用次数: {vision_ctx.get('calls', 0)}")
        print(f"   [INFO] 视觉通过次数: {vision_ctx.get('accepted', 0)}")
        print(f"   [INFO] 视觉跳过（缺少图片）: {vision_ctx.get('skipped_no_image', 0)}")
        print(f"   [INFO] 算法无匹配: {vision_ctx.get('algo_no_match', 0)}")
        print(f"   [INFO] 视觉未通过: {vision_ctx.get('no_vision_match', 0)}")
    elif vision_ctx.get("enabled"):
        print(f"   [INFO] 视觉调用次数: {vision_ctx.get('calls', 0)}")
        print(f"   [INFO] 视觉通过次数: {vision_ctx.get('accepted', 0)}")
        print(f"   [INFO] 视觉跳过（缺少图片）: {vision_ctx.get('skipped_no_image', 0)}")
        print(f"   [INFO] 算法无匹配: {vision_ctx.get('algo_no_match', 0)}")
        print(f"   [INFO] 视觉未通过: {vision_ctx.get('no_vision_match', 0)}")
    print()
    
    # 统计
    print("=" * 80)
    print("生成完成！")
    print("=" * 80)
    print(f"币种数量: {len(coins)}")
    detail = ", ".join([f"{tf}: {overall_counts.get(tf, 0)}" for tf in run_timeframes])
    print(f"有信号的币种(按时间框架): {detail}")
    print(f"总信号数: {total_signals} ({detail})")
    print()
    
    # 清理
    matcher.close()
    
    return 0


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 执行失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
