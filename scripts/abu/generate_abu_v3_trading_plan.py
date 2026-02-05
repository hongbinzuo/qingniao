#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU系统v3.0交易计划生成器

使用增强版混合匹配器生成Top 20的5分钟和15分钟交易计划。
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from abu.enhanced_hybrid_matcher import EnhancedHybridMatcher
    from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
    from abu.unified_pattern_library import UnifiedPatternLibrary
    from abu.gemini_trade_plan import (
        generate_trade_plan,
        load_plan_context,
        plan_budget_ok,
        get_ebook_rules,
    )

    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    print(f"[ERROR] 导入失败: {e}", file=sys.stderr)
    sys.exit(1)


def get_btc_kline_gateio(timeframe="5m", limit=200):
    """从Gate.io获取BTC K线数据"""
    try:
        tf_map = {"5m": "5m", "15m": "15m", "1h": "1h"}
        interval = tf_map.get(timeframe, "5m")

        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {"currency_pair": "BTC_USDT", "interval": interval, "limit": limit}
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data:
                data.reverse()
                klines = []
                for k in data:
                    klines.append(
                        {
                            "timestamp": int(k[0]),
                            "open": float(k[5]),
                            "high": float(k[3]),
                            "low": float(k[4]),
                            "close": float(k[2]),
                            "volume": float(k[1]),
                        }
                    )
                # Sort by timestamp to ensure newest is last
                klines.sort(key=lambda x: x["timestamp"])
                return klines
    except Exception as e:
        print(f"[WARN] Gate.io获取失败: {e}", file=sys.stderr)
    return None


def get_btc_kline_bitget(timeframe="5m", limit=200):
    """从Bitget获取BTC K线数据"""
    try:
        tf_map = {"5m": "5min", "15m": "15min", "1h": "1hour"}
        interval = tf_map.get(timeframe, "5min")

        url = "https://api.bitget.com/api/spot/v1/market/candles"
        params = {"symbol": "BTCUSDT", "granularity": interval, "limit": limit}
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "00000" and data.get("data"):
                klines_data = data["data"]
                klines_data.reverse()
                klines = []
                for k in klines_data:
                    klines.append(
                        {
                            "timestamp": int(k[0]) // 1000,
                            "open": float(k[1]),
                            "high": float(k[3]),
                            "low": float(k[4]),
                            "close": float(k[2]),
                            "volume": float(k[5]),
                        }
                    )
                # Sort by timestamp to ensure newest is last
                klines.sort(key=lambda x: x["timestamp"])
                return klines
    except Exception as e:
        print(f"[WARN] Bitget获取失败: {e}", file=sys.stderr)
    return None


def get_btc_current_price():
    """获取BTC当前价格"""
    try:
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {"currency_pair": "BTC_USDT"}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]["last"])
    except:
        pass

    try:
        url = "https://api.bitget.com/api/spot/v1/market/ticker"
        params = {"symbol": "BTCUSDT"}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == "00000" and data.get("data"):
                return float(data["data"]["last"])
    except:
        pass

    return None


def extract_features_from_klines(klines: List[Dict], timeframe: str) -> Dict:
    """
    从K线数据提取特征（用于匹配）

    Args:
        klines: K线数据列表
        timeframe: 时间框架

    Returns:
        特征字典
    """
    if not klines or len(klines) < 20:
        return {}

    recent = klines[-50:] if len(klines) >= 50 else klines

    # 价格数据
    closes = [k["close"] for k in recent]
    highs = [k["high"] for k in recent]
    lows = [k["low"] for k in recent]
    volumes = [k.get("volume", 0) for k in recent]

    # 趋势特征
    if len(closes) >= 10:
        price_trend = "bullish" if closes[-1] > closes[0] else "bearish"
        trend_strength = abs(closes[-1] - closes[0]) / closes[0] if closes[0] > 0 else 0
    else:
        price_trend = "neutral"
        trend_strength = 0

    # K线特征
    kline_features = []
    if len(recent) >= 2:
        for i in range(max(1, len(recent) - 5), len(recent)):
            if i < 1:
                continue
            last = recent[i]
            prev = recent[i - 1]

            # 吞没形态
            if last["close"] > last["open"] and prev["close"] < prev["open"]:
                if last["open"] < prev["close"] and last["close"] > prev["open"]:
                    kline_features.append("bullish_engulfing")
            elif last["close"] < last["open"] and prev["close"] > prev["open"]:
                if last["open"] > prev["close"] and last["close"] < prev["open"]:
                    kline_features.append("bearish_engulfing")

            # Inside Bar
            if last["high"] < prev["high"] and last["low"] > prev["low"]:
                kline_features.append("inside_bar")

    # 波动率
    price_ranges = [(h - l) for h, l in zip(highs, lows)]
    avg_range = sum(price_ranges) / len(price_ranges) if price_ranges else 0
    volatility = avg_range / closes[-1] if closes and closes[-1] > 0 else 0

    # 构建特征
    features = {
        "pattern_type": "unknown",  # 由匹配器确定
        "direction": "long"
        if price_trend == "bullish"
        else "short"
        if price_trend == "bearish"
        else "neutral",
        "trend": price_trend,
        "trend_strength": trend_strength,
        "kline_features": list(set(kline_features)),
        "volatility": volatility,
        "market_conditions": {
            "trend_strength": "strong" if trend_strength > 0.02 else "weak",
            "volatility": "high" if volatility > 0.01 else "low",
            "trend_direction": price_trend,
        },
    }

    return features

def generate_signal_from_match(
    match_result, current_price: float, klines: List[Dict]
) -> Optional[Dict]:
    """
    从匹配结果生成交易信号

    Args:
        match_result: 匹配结果（EnhancedMatchResult）
        current_price: 当前价格
        klines: K线数据

    Returns:
        交易信号字典
    """
    # 从EnhancedMatchResult提取信息
    pattern_name = match_result.pattern_name
    pattern_type = match_result.pattern_type
    source = match_result.source

    # 需要从统一模式库获取完整模式信息以获取direction
    # 这里先使用模式类型推断方向
    direction = "neutral"
    pattern_type_lower = pattern_type.lower() if pattern_type else ""

    if any(
        kw in pattern_type_lower for kw in ["bull", "long", "buy", "up", "ascending"]
    ):
        direction = "long"
    elif any(
        kw in pattern_type_lower
        for kw in ["bear", "short", "sell", "down", "descending"]
    ):
        direction = "short"
    else:
        # 如果无法推断，尝试从模式名称推断
        pattern_name_lower = pattern_name.lower() if pattern_name else ""
        if any(
            kw in pattern_name_lower
            for kw in ["bull", "long", "buy", "up", "ascending"]
        ):
            direction = "long"
        elif any(
            kw in pattern_name_lower
            for kw in ["bear", "short", "sell", "down", "descending"]
        ):
            direction = "short"
        else:
            # 默认使用long（可以根据实际情况调整）
            direction = "long"

    # direction已经确定，继续处理

    # 计算止损和止盈
    entry_price = current_price

    # 从K线数据计算止损
    recent_lows = [k["low"] for k in klines[-10:]]
    recent_highs = [k["high"] for k in klines[-10:]]

    if direction == "long":
        # 做多：止损在入场价下方
        stop_loss = min(recent_lows) if recent_lows else entry_price * 0.98
        # 确保止损不高于入场价
        stop_loss = min(stop_loss, entry_price * 0.99)
        stop_loss_pct = abs(entry_price - stop_loss) / entry_price
        take_profit_1 = entry_price * (1 + stop_loss_pct * 1.5)  # 1.5:1 RR
        take_profit_2 = entry_price * (1 + stop_loss_pct * 2.5)  # 2.5:1 RR
    else:  # short
        # 做空：止损在入场价上方（重要！）
        # 使用最近高点，但必须确保止损价高于入场价
        candidate_stop = max(recent_highs) if recent_highs else entry_price * 1.02
        # 确保止损价至少比入场价高1%（防止使用历史低点）
        stop_loss = max(candidate_stop, entry_price * 1.01)
        stop_loss_pct = abs(stop_loss - entry_price) / entry_price
        take_profit_1 = entry_price * (1 - stop_loss_pct * 1.5)
        take_profit_2 = entry_price * (1 - stop_loss_pct * 2.5)

    # 计算盈亏比（基于TP1）
    if direction == "long":
        risk = entry_price - stop_loss
        reward = take_profit_1 - entry_price
    else:
        risk = stop_loss - entry_price
        reward = entry_price - take_profit_1
    risk_reward_ratio = reward / risk if risk > 0 else None

    return {
        "pattern_id": match_result.pattern_id,
        "pattern_name": match_result.pattern_name,
        "pattern_type": match_result.pattern_type,
        "source": match_result.source,
        "direction": direction,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit_1": take_profit_1,
        "take_profit_2": take_profit_2,
        "confidence": match_result.combined_confidence,
        "final_score": match_result.final_score,
        "risk_reward_ratio": risk_reward_ratio,
        "all_sources": match_result.all_sources or [match_result.source],
    }


async def generate_trading_plan(
    timeframe: str = "15m",
    top_k: int = 20,
    plan_ctx: Optional[Dict[str, Any]] = None,
):
    """
    生成交易计划

    Args:
        timeframe: 时间框架 ('5m' 或 '15m')
        top_k: 返回Top K结果
        plan_ctx: Gemini交易计划配置
    """
    print("=" * 80)
    print(f"ABU系统v3.0 - {timeframe}交易计划生成")
    print("=" * 80)
    print()

    # 1. 获取市场数据
    print(f"1. 获取BTC {timeframe}市场数据...")
    current_price = get_btc_current_price()
    klines = get_btc_kline_gateio(timeframe, limit=200)

    if not klines:
        print("   尝试从Bitget获取...")
        klines = get_btc_kline_bitget(timeframe, limit=200)

    if not current_price or not klines:
        print("[ERROR] 无法获取市场数据")
        return None

    if len(klines) < 50:
        print(f"[ERROR] K线数据不足: {len(klines)}根")
        return None

    # 验证价格新鲜度和一致性
    import time as _time

    now_ts = int(_time.time())
    kline_ts = klines[-1].get("timestamp", 0)
    kline_age = now_ts - kline_ts

    # K线数据不应超过30分钟
    if kline_age > 1800:
        print(f"[WARN] K线数据过旧 ({kline_age}秒), 重新获取...")
        klines = get_btc_kline_gateio(timeframe, limit=200)
        if not klines:
            klines = get_btc_kline_bitget(timeframe, limit=200)
        if not klines:
            print("[ERROR] 无法获取新鲜K线数据")
            return None

    # 价格偏差超过3%时使用K线收盘价
    kline_close = klines[-1]["close"]
    price_diff = (
        abs(kline_close - current_price) / current_price if current_price > 0 else 1
    )
    if price_diff > 0.03:
        print(f"[WARN] 价格偏差{price_diff * 100:.1f}%, 使用K线收盘价")
        current_price = kline_close

    print(f"   当前价格: ${current_price:,.2f}")
    print(f"   K线数量: {len(klines)}根")
    print()

    # 2. 提取特征
    print("2. 提取K线特征...")
    query_features = extract_features_from_klines(klines, timeframe)
    if not query_features:
        print("[ERROR] 特征提取失败")
        return None

    print(f"   趋势: {query_features.get('trend')}")
    print(f"   方向: {query_features.get('direction')}")
    print(f"   K线特征: {len(query_features.get('kline_features', []))}个")
    print()

    # 3. 使用增强版混合匹配器匹配
    print("3. 使用ABU系统v3.0匹配模式...")
    matcher = EnhancedHybridMatcher(
        strategy="comprehensive",
        use_async=True,
        use_vision=False,  # 不使用视觉验证以加快速度
        top_k=top_k * 4,  # 获取更多候选（确保有足够的结果）
        min_confidence=0.15,  # 进一步降低阈值以获取更多结果
        min_similarity=0.25,  # 进一步降低相似度阈值
    )

    try:
        klines_dict = {timeframe: klines}
        results = await matcher.async_match(
            query_features=query_features, klines_dict=klines_dict, symbol="BTC_USDT"
        )

        print(f"   找到 {len(results)} 个匹配")
        print()

        # 4. 生成交易信号
        print("4. 生成交易信号...")
        signals = []
        for result in results[:top_k]:
            signal = generate_signal_from_match(result, current_price, klines)
            if signal:
                if plan_budget_ok(plan_ctx):
                    match_payload = {
                        "pattern_name": result.pattern_name,
                        "pattern_type": result.pattern_type,
                        "source": result.source,
                        "similarity": result.algorithm_score,
                        "confidence": result.combined_confidence,
                        "final_score": result.final_score,
                    }
                    extra_context = {}
                    ebook_rules = get_ebook_rules(
                        plan_ctx, result.pattern_name, result.pattern_type
                    )
                    if ebook_rules:
                        extra_context["ebook_rules"] = ebook_rules
                    plan_result = generate_trade_plan(
                        symbol="BTC",
                        timeframe=timeframe,
                        match=match_payload,
                        signal=signal,
                        klines=klines,
                        extra_context=extra_context,
                        model=plan_ctx.get("model"),
                    )
                    signal["gemini_plan"] = plan_result
                    plan_ctx["calls"] = plan_ctx.get("calls", 0) + 1
                signals.append(signal)

        print(f"   生成了 {len(signals)} 个交易信号")
        print()

        return {
            "timeframe": timeframe,
            "current_price": current_price,
            "signals": signals,
            "generated_at": datetime.now(),
        }

    finally:
        matcher.close()

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


def format_trading_plan(plan_5m: Dict, plan_15m: Dict) -> str:
    """格式化交易计划为Markdown"""
    output = []

    output.append("# ABU系统v3.0交易计划")
    output.append("")
    output.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"**当前BTC价格**: ${plan_15m['current_price']:,.2f}")
    output.append("")
    output.append("---")
    output.append("")

    # 5分钟交易计划
    output.append("## 5分钟交易计划")
    output.append("")
    if plan_5m["signals"]:
        output.append(f"**找到 {len(plan_5m['signals'])} 个交易信号**")
        output.append("")

        for i, signal in enumerate(plan_5m["signals"], 1):
            output.append(f"### {i}. {signal['pattern_name']}")
            output.append("")
            output.append(f"- **模式类型**: {signal['pattern_type']}")
            output.append(f"- **数据源**: {', '.join(signal['all_sources'])}")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${signal['entry_price']:,.2f}")
            output.append(f"- **止损价**: ${signal['stop_loss']:,.2f}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:,.2f}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:,.2f}")

            # 计算盈亏比
            if signal["direction"] == "long":
                risk = signal["entry_price"] - signal["stop_loss"]
                reward_1 = signal["take_profit_1"] - signal["entry_price"]
                rr_1 = reward_1 / risk if risk > 0 else 0
            else:
                risk = signal["stop_loss"] - signal["entry_price"]
                reward_1 = signal["entry_price"] - signal["take_profit_1"]
                rr_1 = reward_1 / risk if risk > 0 else 0

            output.append(f"- **盈亏比**: {rr_1:.2f}:1")
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            output.append(f"- **综合分数**: {signal['final_score']:.3f}")
            if signal.get("gemini_plan"):
                output.append(_format_gemini_plan(signal.get("gemini_plan")))
            output.append("")
    else:
        output.append("未找到匹配的交易信号")
        output.append("")

    output.append("---")
    output.append("")

    # 15分钟交易计划
    output.append("## 15分钟交易计划")
    output.append("")
    if plan_15m["signals"]:
        output.append(f"**找到 {len(plan_15m['signals'])} 个交易信号**")
        output.append("")

        for i, signal in enumerate(plan_15m["signals"], 1):
            output.append(f"### {i}. {signal['pattern_name']}")
            output.append("")
            output.append(f"- **模式类型**: {signal['pattern_type']}")
            output.append(f"- **数据源**: {', '.join(signal['all_sources'])}")
            output.append(f"- **方向**: {signal['direction'].upper()}")
            output.append(f"- **入场价**: ${signal['entry_price']:,.2f}")
            output.append(f"- **止损价**: ${signal['stop_loss']:,.2f}")
            output.append(f"- **止盈1**: ${signal['take_profit_1']:,.2f}")
            output.append(f"- **止盈2**: ${signal['take_profit_2']:,.2f}")

            # 计算盈亏比
            if signal["direction"] == "long":
                risk = signal["entry_price"] - signal["stop_loss"]
                reward_1 = signal["take_profit_1"] - signal["entry_price"]
                rr_1 = reward_1 / risk if risk > 0 else 0
            else:
                risk = signal["stop_loss"] - signal["entry_price"]
                reward_1 = signal["entry_price"] - signal["take_profit_1"]
                rr_1 = reward_1 / risk if risk > 0 else 0

            output.append(f"- **盈亏比**: {rr_1:.2f}:1")
            output.append(f"- **置信度**: {signal['confidence']:.2%}")
            output.append(f"- **综合分数**: {signal['final_score']:.3f}")
            if signal.get("gemini_plan"):
                output.append(_format_gemini_plan(signal.get("gemini_plan")))
            output.append("")
    else:
        output.append("未找到匹配的交易信号")
        output.append("")

    return "\n".join(output)


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("ABU系统v3.0交易计划生成器")
    print("=" * 80)
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

    # 生成5分钟和15分钟交易计划
    print("生成5分钟交易计划...")
    plan_5m = await generate_trading_plan("5m", top_k=20, plan_ctx=plan_ctx)
    print()

    print("生成15分钟交易计划...")
    plan_15m = await generate_trading_plan("15m", top_k=20, plan_ctx=plan_ctx)
    print()

    if not plan_5m or not plan_15m:
        print("[ERROR] 交易计划生成失败")
        return 1

    # 格式化输出
    output = format_trading_plan(plan_5m, plan_15m)

    # 保存到文件
    output_file = (
        ROOT
        / "trading_signals"
        / f"ABU_v3_trading_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        f.write(output)

    print("=" * 80)
    print("交易计划生成完成！")
    print("=" * 80)
    print()
    print(f"输出文件: {output_file}")
    print()

    # 显示摘要
    print("摘要:")
    print(f"  5分钟: {len(plan_5m['signals'])} 个信号")
    print(f"  15分钟: {len(plan_15m['signals'])} 个信号")
    print()

    # 打印到控制台
    print(output)

    return 0


if __name__ == "__main__":
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
