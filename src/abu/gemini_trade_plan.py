#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini 交易计划生成器（文本模型）

用途：
- 基于模式匹配结果 + 最新K线信息，生成结构化交易计划
- 仅在需要时调用（依赖OpenRouter API）
"""

from __future__ import annotations

import json
import os
import time
import re
from typing import Dict, List, Optional, Any

import requests

try:
    from openrouter_config import (
        get_openrouter_api_key,
        get_openrouter_api_url,
        is_openrouter_configured,
    )
except ImportError:
    from src.openrouter_config import (
        get_openrouter_api_key,
        get_openrouter_api_url,
        is_openrouter_configured,
    )


def _safe_truncate(text: str, max_chars: int = 800) -> str:
    if not text:
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _init_ebook_retriever(trader_id: str = "abu"):
    try:
        from abu.ebook_knowledge_retriever import EbookKnowledgeRetriever
    except Exception:
        try:
            from src.abu.ebook_knowledge_retriever import EbookKnowledgeRetriever
        except Exception:
            return None
    try:
        return EbookKnowledgeRetriever(trader_id)
    except Exception:
        return None


def get_ebook_rules(
    plan_ctx: Optional[Dict[str, Any]],
    pattern_name: Optional[str],
    pattern_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if not plan_ctx or not plan_ctx.get("ebook_enabled"):
        return []
    retriever = plan_ctx.get("ebook_retriever")
    if not retriever:
        return []

    max_items = int(plan_ctx.get("ebook_max_rules") or 3)
    max_chars = int(plan_ctx.get("ebook_context_chars") or 400)
    cache: Dict[str, List[Dict[str, Any]]] = plan_ctx.get("ebook_cache", {})

    keys = []
    if pattern_name:
        keys.append(pattern_name)
    if pattern_type and pattern_type not in keys:
        keys.append(pattern_type)
    if not keys:
        return []

    for key in keys:
        if key in cache:
            return cache[key]

    for key in keys:
        try:
            rules = retriever.get_trading_rules(key)
        except Exception:
            rules = []
        if rules:
            cleaned = []
            for item in rules[:max_items]:
                cleaned.append(
                    {
                        "book": item.get("book"),
                        "chapter": item.get("chapter"),
                        "section": item.get("section"),
                        "rules": item.get("rules", {}),
                        "context": _safe_truncate(item.get("context", ""), max_chars),
                    }
                )
            cache[key] = cleaned
            plan_ctx["ebook_cache"] = cache
            return cleaned

    return []


def load_plan_context() -> Dict[str, Any]:
    """加载Gemini交易计划配置（通过环境变量控制）"""
    enabled_env = os.getenv("ABU_GEMINI_PLAN")
    if enabled_env is None:
        enabled = is_openrouter_configured()
    else:
        enabled = enabled_env.strip().lower() in {"1", "true", "yes", "y", "on"}

    model = os.getenv("ABU_GEMINI_PLAN_MODEL", "google/gemini-3-flash-preview")
    max_calls_raw = os.getenv("ABU_GEMINI_PLAN_MAX", "0").strip()
    try:
        max_calls = int(max_calls_raw)
    except ValueError:
        max_calls = 0

    # Ebook设置
    ebook_env = os.getenv("ABU_GEMINI_PLAN_EBOOK")
    if ebook_env is None:
        ebook_enabled = True
    else:
        ebook_enabled = ebook_env.strip().lower() in {"1", "true", "yes", "y", "on"}
    ebook_max_rules = int(os.getenv("ABU_GEMINI_PLAN_EBOOK_MAX", "3") or 3)
    ebook_context_chars = int(os.getenv("ABU_GEMINI_PLAN_EBOOK_CHARS", "400") or 400)
    ebook_trader = os.getenv("ABU_GEMINI_PLAN_EBOOK_TRADER", "abu")
    ebook_retriever = _init_ebook_retriever(ebook_trader) if ebook_enabled else None
    if ebook_retriever is None:
        ebook_enabled = False

    return {
        "enabled": enabled,
        "model": model,
        "max_calls": max_calls,  # 0 表示不限制
        "calls": 0,
        "ebook_enabled": ebook_enabled,
        "ebook_retriever": ebook_retriever,
        "ebook_cache": {},
        "ebook_max_rules": ebook_max_rules,
        "ebook_context_chars": ebook_context_chars,
    }


def plan_budget_ok(plan_ctx: Optional[Dict[str, Any]]) -> bool:
    if not plan_ctx or not plan_ctx.get("enabled"):
        return False
    max_calls = int(plan_ctx.get("max_calls") or 0)
    if max_calls > 0 and plan_ctx.get("calls", 0) >= max_calls:
        return False
    return True


def _summarize_klines(klines: List[Dict[str, Any]], window: int = 50) -> Dict[str, Any]:
    if not klines:
        return {}
    recent = klines[-window:] if len(klines) > window else klines
    closes = [k.get("close") for k in recent if k.get("close") is not None]
    highs = [k.get("high") for k in recent if k.get("high") is not None]
    lows = [k.get("low") for k in recent if k.get("low") is not None]
    if not closes or not highs or not lows:
        return {}

    start = closes[0]
    end = closes[-1]
    direction = "neutral"
    if end > start:
        direction = "bullish"
    elif end < start:
        direction = "bearish"

    price_range = max(highs) - min(lows)
    atr = sum(h - l for h, l in zip(highs, lows)) / len(highs) if highs and lows else 0.0
    atr_pct = atr / end if end else None

    return {
        "current_price": end,
        "recent_high": max(highs),
        "recent_low": min(lows),
        "trend_direction": direction,
        "trend_strength": (end - start) / start if start else 0.0,
        "range_pct": price_range / end if end else 0.0,
        "atr": atr,
        "atr_pct": atr_pct,
        "bars": len(recent),
    }


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def build_trade_plan_prompt(
    symbol: str,
    timeframe: str,
    match: Optional[Dict[str, Any]] = None,
    signal: Optional[Dict[str, Any]] = None,
    klines: Optional[List[Dict[str, Any]]] = None,
    extra_context: Optional[Dict[str, Any]] = None,
) -> str:
    """构造交易计划提示词（JSON-only输出）。"""
    match = match or {}
    signal = signal or {}
    extra_context = extra_context or {}

    kline_summary = _summarize_klines(klines or [])

    ebook_rules = extra_context.get("ebook_rules") if isinstance(extra_context, dict) else None

    prompt = {
        "task": "Generate a concise but detailed trading plan for the given setup.",
        "instrument": symbol,
        "timeframe": timeframe,
        "match": {
            "pattern_name": match.get("pattern_name"),
            "pattern_type": match.get("pattern_type"),
            "source": match.get("source"),
            "similarity": match.get("similarity"),
            "confidence": match.get("confidence"),
            "final_score": match.get("final_score"),
        },
        "signal_hint": {
            "direction": signal.get("direction"),
            "entry_price": signal.get("entry_price"),
            "stop_loss": signal.get("stop_loss"),
            "take_profit_1": signal.get("take_profit_1"),
            "take_profit_2": signal.get("take_profit_2"),
            "risk_reward": signal.get("risk_reward_ratio"),
        },
        "market_context": kline_summary,
        "ebook_rules": ebook_rules,
        "extra_context": extra_context,
        "output_schema": {
            "direction": "long/short/neutral",
            "setup": "short description",
            "entry": {
                "type": "market/limit/stop",
                "price": "number or null",
                "zone": "[low, high] or null",
                "condition": "string"
            },
            "stop_loss": {
                "price": "number or null",
                "reason": "string"
            },
            "take_profits": [
                {"price": "number or null", "portion_pct": "number or null", "reason": "string"}
            ],
            "invalidation": "string",
            "time_stop": {"bars": "number or null", "condition": "string"},
            "risk": {
                "risk_reward": "number or null",
                "position_size_pct": "number or null",
                "max_loss_pct": "number or null"
            },
            "management": {
                "move_sl_to_be": "string",
                "trail": "string",
                "partial_exit": "string"
            },
            "confidence": "0-1",
            "assumptions": ["string"],
            "notes": "short reasoning"
        },
        "constraints": [
            "Return JSON only. No markdown.",
            "If data is insufficient, set fields to null and list assumptions.",
            "Do not fabricate quotes or external facts.",
            "Summarize ebook/web context; avoid long verbatim quotes.",
            "Keep numeric fields as numbers, not strings."
        ]
    }
    return json.dumps(prompt, ensure_ascii=False)


def generate_trade_plan(
    symbol: str,
    timeframe: str,
    match: Optional[Dict[str, Any]] = None,
    signal: Optional[Dict[str, Any]] = None,
    klines: Optional[List[Dict[str, Any]]] = None,
    extra_context: Optional[Dict[str, Any]] = None,
    model: str = "google/gemini-3-flash-preview",
    max_tokens: int = 800,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    调用Gemini文本模型生成交易计划。

    Returns:
        {"ok": bool, "plan": dict|None, "error": str|None, "raw": str|None}
    """
    api_key = get_openrouter_api_key()
    api_url = get_openrouter_api_url()
    if not api_key:
        return {"ok": False, "plan": None, "error": "OpenRouter API Key 未配置", "raw": None}

    prompt = build_trade_plan_prompt(
        symbol=symbol,
        timeframe=timeframe,
        match=match,
        signal=signal,
        klines=klines,
        extra_context=extra_context,
    )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/qingniao",
        "X-Title": "QingNiao Trade Plan",
    }

    start = time.time()
    try:
        resp = requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=60)
        elapsed_ms = int((time.time() - start) * 1000)
        if resp.status_code != 200:
            return {
                "ok": False,
                "plan": None,
                "error": f"HTTP {resp.status_code}",
                "raw": resp.text,
                "elapsed_ms": elapsed_ms,
            }
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        plan = _extract_json_from_text(content)
        return {
            "ok": plan is not None,
            "plan": plan,
            "error": None if plan is not None else "JSON解析失败",
            "raw": content,
            "elapsed_ms": elapsed_ms,
            "model": model,
        }
    except Exception as e:
        return {"ok": False, "plan": None, "error": str(e), "raw": None}
