#!/usr/bin/env python3
"""
生成“风格筛选版”BTC信号（基于青鸟系统现有模块）

规则（可通过参数调整）：
- 仅 5m / 15m
- 只接回踩：排除包含“突破/breakout/区间突破”的信号
- 严格校验入场相对现价偏差（默认≤0.3%）
- 盈亏比阈值（默认 RR≥1.5）

价格来源：优先 Gate.io ticker，其次 Bitget；若均失败，回退到K线收盘价。
输出：在当前目录写入 `BTC_de_signals_简要_<时间>_style_filtered.md`
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# 允许从 src/ 导入现有功能
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import requests  # 仅用于获取 Gate/Bitget ticker

# 复用青鸟系统的已实现能力
from generate_btc_de_signals import (
    get_btc_kline_gateio,
    get_btc_kline_bitget,
    analyze_timeframe,
    validate_signal,
)
from volatility_analyzer import calculate_risk_reward_ratio


def get_tickers():
    """获取 Gate.io 与 Bitget 的 BTCUSDT 实时价格。"""
    gate = {"exchange": "Gate.io", "price": None, "error": None}
    bitget = {"exchange": "Bitget", "price": None, "error": None}

    # Gate.io
    try:
        r = requests.get(
            "https://api.gateio.ws/api/v4/spot/tickers",
            params={"currency_pair": "BTC_USDT"},
            timeout=12,
        )
        d = r.json()
        if isinstance(d, list) and d:
            gate["price"] = float(d[0]["last"])
            gate["raw"] = d[0]
    except Exception as e:
        gate["error"] = str(e)

    # Bitget
    try:
        r = requests.get(
            "https://api.bitget.com/api/spot/v1/market/ticker",
            params={"symbol": "BTCUSDT"},
            timeout=12,
        )
        d = r.json()
        if d.get("code") == "00000" and d.get("data"):
            bitget["price"] = float(d["data"]["last"])
            bitget["raw"] = d["data"]
    except Exception as e:
        bitget["error"] = str(e)

    return gate, bitget


def main():
    ap = argparse.ArgumentParser(description="生成风格筛选版BTC信号")
    ap.add_argument("--min-rr", type=float, default=2.0, help="盈亏比阈值，默认2.0")
    ap.add_argument(
        "--timeframes",
        default="5m,15m,1h",
        help="时间框架，逗号分隔，默认5m,15m,1h",
    )
    ap.add_argument(
        "--exclude",
        default="突破,breakout,区间突破",
        help="排除关键词，逗号分隔，默认排除突破相关",
    )
    ap.add_argument(
        "--tolerance",
        type=float,
        default=0.003,
        help="入场相对现价的最大偏差(比例)，默认0.003=0.3%%",
    )
    ap.add_argument(
        "--outdir",
        default=".",
        help="输出目录（默认当前目录）",
    )
    args = ap.parse_args()

    timeframes = [tf.strip() for tf in args.timeframes.split(",") if tf.strip()]
    exclude_keywords = [w.strip() for w in args.exclude.split(",") if w.strip()]

    # 1) 获取实时ticker（Gate优先，其次Bitget）
    gate, bitget = get_tickers()
    prices = [p for p in (gate.get("price"), bitget.get("price")) if p]
    if prices:
        current_price = prices[0]
        price_src = "Gate.io ticker" if gate.get("price") else "Bitget ticker"
    else:
        current_price = None
        price_src = "N/A"

    # 2) 获取K线（Gate优先；失败回退Bitget）
    k5 = get_btc_kline_gateio("5m", 200)
    k15 = get_btc_kline_gateio("15m", 200)
    k1h = get_btc_kline_gateio("1h", 200)
    k4h = get_btc_kline_gateio("4h", 200)
    if k5 is None:
        k5 = get_btc_kline_bitget("5m", 200)
    if k15 is None:
        k15 = get_btc_kline_bitget("15m", 200)
    if k1h is None:
        k1h = get_btc_kline_bitget("1h", 200)
    if k4h is None:
        k4h = get_btc_kline_bitget("4h", 200)

    # 3) 双ticker均失败才回退到K线收盘价
    if current_price is None:
        for ks in (k15, k5):
            if ks:
                current_price = ks[-1]["close"]
                price_src = "K线收盘价回退"
                break

    if not current_price or not k5 or not k15:
        print("❌ 无法获取足够的数据（ticker 或 K线）。")
        sys.exit(2)

    # 4) 运行青鸟分析
    tf_map_cn = {"5m": "5分钟", "15m": "15分钟", "1h": "1小时"}
    analyses = {
        "5m": analyze_timeframe(k5, tf_map_cn.get("5m", "5分钟"), current_price),
        "15m": analyze_timeframe(k15, tf_map_cn.get("15m", "15分钟"), current_price),
        "1h": analyze_timeframe(k1h, tf_map_cn.get("1h", "1小时"), current_price) if k1h else None,
    }
    analysis_4h = analyze_timeframe(k4h, "4小时", current_price) if k4h else None

    results = []
    for tf in timeframes:
        analysis = analyses.get(tf)
        if not analysis or not analysis.get("signals"):
            continue
        filtered = []
        for sig in analysis["signals"]:
            # 排除突破类
            text = (sig.get("entry_model", "") or "") + " " + (sig.get("reason", "") or "")
            if any(kw in text for kw in exclude_keywords):
                continue
            ok, _ = validate_signal(sig, current_price, tolerance_pct=args.tolerance)
            if not ok:
                continue
            rr = calculate_risk_reward_ratio(
                sig["entry"], sig["stop_loss"], sig["take_profit_1"], sig["take_profit_2"], sig["type"]
            )
            sig["_rr"] = rr
            if rr["avg_rr_ratio"] >= args.min_rr:
                filtered.append(sig)

        if filtered:
            def score_good(s):
                strength = 3 if s["strength"] == "strong" else 2 if s["strength"] == "medium" else 1
                return (s["_rr"]["avg_rr_ratio"], strength)
            best = sorted(filtered, key=score_good, reverse=True)[0]
            results.append((tf, best, True))
        else:
            # 若无达标RR信号，选一个参考（RR最高且通过校验）
            candidates = []
            for sig in analysis["signals"]:
                text = (sig.get("entry_model", "") or "") + " " + (sig.get("reason", "") or "")
                if any(kw in text for kw in exclude_keywords):
                    continue
                ok, _ = validate_signal(sig, current_price, tolerance_pct=args.tolerance)
                if not ok:
                    continue
                rr = calculate_risk_reward_ratio(
                    sig["entry"], sig["stop_loss"], sig["take_profit_1"], sig["take_profit_2"], sig["type"]
                )
                sig["_rr"] = rr
                candidates.append(sig)
            if candidates:
                def score_ref(s):
                    strength = 3 if s["strength"] == "strong" else 2 if s["strength"] == "medium" else 1
                    return (s["_rr"]["avg_rr_ratio"], strength)
                best = sorted(candidates, key=score_ref, reverse=True)[0]
                results.append((tf, best, False))

    # 5) 生成输出（简要版）
    now = datetime.now()
    lines = []
    lines.append("# BTC 交易信号（风格筛选版 · 仅5m/15m · RR≥{:.2f} · 只接回踩）".format(args.min_rr))
    lines.append("")
    lines.append("**生成时间**: {}  ".format(now.strftime("%Y-%m-%d %H:%M:%S")))
    cp_line = "**当前价格**: ${:,.2f}  (来源: {})".format(current_price, price_src)
    if gate.get("price") and bitget.get("price"):
        spread = (abs(gate["price"] - bitget["price"]) / ((gate["price"] + bitget["price"]) / 2)) * 100
        cp_line += " | Gate: ${:,.2f} / Bitget: ${:,.2f} (价差 {:.3f}%)".format(
            gate["price"], bitget["price"], spread
        )
    lines.append(cp_line + "  ")
    lines.append("**筛选条件**: RR≥{}, 排除关键词: {}  ".format(args.min_rr, ", ".join(exclude_keywords)))
    lines.append("")

    if not results:
        lines.append("本轮无符合筛选条件的 5m/15m/1h 信号。建议：等待回踩至近支撑再看多，或至近阻力反抽再看空。")
        for tf in ("5m", "15m", "1h"):
            a = analyses.get(tf)
            if a and a.get("support_resistance"):
                sr = a["support_resistance"]
                sup = sr.get("support") or []
                res = sr.get("resistance") or []
                if sup or res:
                    if sup:
                        lines.append("- {} 支撑: {}".format(tf, ", ".join("${:,.0f}".format(x) for x in sup[:3])))
                    if res:
                        lines.append("- {} 阻力: {}".format(tf, ", ".join("${:,.0f}".format(x) for x in res[:3])))
    else:
        for tf, sig, passed in results:
            direction = "做多" if sig["type"] == "long" else "做空"
            lines.append("## {} 最优信号（{} — {}）".format(tf, direction, "已通过筛选" if passed else "RR未达标，供参考"))
            lines.append("- 入场: ${:,.0f}".format(sig["entry"]))
            lines.append("- 止损: ${:,.0f}".format(sig["stop_loss"]))
            lines.append("- 止盈: ${:,.0f} / ${:,.0f}".format(sig["take_profit_1"], sig["take_profit_2"]))
            rr = sig["_rr"]
            lines.append("- 盈亏比: {:.2f}:1 ({})".format(rr["avg_rr_ratio"], rr["quality"]))
            lines.append("- 模型: {}".format(sig.get("entry_model", "未知")))
            ok, err = validate_signal(sig, current_price, tolerance_pct=args.tolerance)
            lines.append("- 合理性验证: {}{}".format("通过" if ok else "失败", " — " + err if not ok else ""))
            lines.append("")

    # 追加：4小时趋势背景（不生成4小时信号）
    lines.append("---")
    lines.append("")
    lines.append("## 4小时趋势背景（仅供参考，不生成4小时入场/止损/止盈信号）")
    lines.append("")
    if analysis_4h:
        ema144 = analysis_4h.get("ema_144")
        ema169 = analysis_4h.get("ema_169")
        vwap = analysis_4h.get("vwap")
        rsi = analysis_4h.get("rsi")
        sr = analysis_4h.get("support_resistance") or {}
        sup = sr.get("support") or []
        res = sr.get("resistance") or []

        if ema144 and ema169:
            lo = min(ema144, ema169)
            hi = max(ema144, ema169)
            if current_price > hi:
                pos = "价格在4小时Vegas通道上方（大趋势偏多）"
            elif current_price < lo:
                pos = "价格在4小时Vegas通道下方（大趋势偏空）"
            else:
                pos = "价格在4小时Vegas通道内（震荡）"
            lines.append("- 4小时EMA144: ${:,.2f}".format(ema144))
            lines.append("- 4小时EMA169: ${:,.2f}".format(ema169))
            lines.append("- 趋势位置: {}".format(pos))

        if vwap:
            rel = "上方" if current_price > vwap else "下方"
            lines.append("- 4小时VWAP: ${:,.2f}（价格在其{}）".format(vwap, rel))
        if rsi is not None:
            lines.append("- 4小时RSI: {:.1f}".format(rsi))

        if sup:
            lines.append("- 4小时支撑: {}".format(", ".join("${:,.0f}".format(x) for x in sup[:3])))
        if res:
            lines.append("- 4小时阻力: {}".format(", ".join("${:,.0f}".format(x) for x in res[:3])))
        lines.append("")
        ote = analysis_4h.get("ote_analysis")
        if ote:
            if ote.get("in_ote_zone"):
                lines.append("- OTE: 价格位于618-786区间内（关注回踩/反抽机会）")
            elif ote.get("above_786"):
                lines.append("- OTE: 价格已突破786（强势，回踩OTE区间可关注）")
            elif ote.get("below_618"):
                lines.append("- OTE: 价格低于618（弱势，关注是否跌破786反向区间）")
            lines.append("")
    else:
        lines.append("- 暂无法获取4小时K线或分析数据")

    # 写入文件
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    out_path = outdir / f"BTC_de_signals_简要_{timestamp}_style_filtered.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"已保存: {out_path}")

    # 6) 生成输出（详细版）
    def fmt_sr(sr_list, maxn=5):
        return ", ".join("${:,.0f}".format(x) for x in (sr_list or [])[:maxn]) if sr_list else "无"

    full = []
    full.append("# BTC 交易信号（风格筛选版 · 详细）")
    full.append("")
    full.append("**生成时间**: {}  ".format(now.strftime("%Y-%m-%d %H:%M:%S")))
    cp_line_f = "**当前价格**: ${:,.2f}  (来源: {})".format(current_price, price_src)
    if gate.get("price") and bitget.get("price"):
        spread = (abs(gate["price"] - bitget["price"]) / ((gate["price"] + bitget["price"]) / 2)) * 100
        cp_line_f += " | Gate: ${:,.2f} / Bitget: ${:,.2f} (价差 {:.3f}%)".format(
            gate["price"], bitget["price"], spread
        )
    full.append(cp_line_f + "  ")
    full.append("**筛选条件**: RR≥{}, 排除关键词: {}  ".format(args.min_rr, ", ".join(exclude_keywords)))
    full.append("")

    # 为每个时间框架输出：信号 + 技术分析详情
    order = [tf for tf in ("5m", "15m", "1h") if tf in timeframes]
    # 建立每个tf对应的最佳信号记录（若存在）
    best_map = {}
    for tf, sig, passed in results:
        best_map[tf] = (sig, passed)

    for tf in order:
        a = analyses.get(tf)
        tf_title = {"5m": "5分钟", "15m": "15分钟", "1h": "1小时"}.get(tf, tf)
        full.append("## {} 时间框架".format(tf_title))
        full.append("")
        # 信号（若有）
        if tf in best_map:
            sig, passed = best_map[tf]
            direction = "做多" if sig["type"] == "long" else "做空"
            full.append("### 信号")
            full.append("- 方向: {}（{}）".format(direction, "已通过筛选" if passed else "RR未达标，供参考"))
            full.append("- 入场: ${:,.0f}".format(sig["entry"]))
            full.append("- 止损: ${:,.0f}".format(sig["stop_loss"]))
            full.append("- 止盈: ${:,.0f} / ${:,.0f}".format(sig["take_profit_1"], sig["take_profit_2"]))
            rr = sig["_rr"]
            full.append("- 盈亏比: {:.2f}:1 ({})".format(rr["avg_rr_ratio"], rr["quality"]))
            full.append("- 模型: {}".format(sig.get("entry_model", "未知")))
            ok, err = validate_signal(sig, current_price, tolerance_pct=args.tolerance)
            full.append("- 合理性验证: {}{}".format("通过" if ok else "失败", " — " + err if not ok else ""))
            full.append("")
        else:
            full.append("（本轮无符合筛选条件的信号）")
            full.append("")

        # 技术分析详情
        if a:
            full.append("### 技术分析")
            ema144 = a.get("ema_144")
            ema169 = a.get("ema_169")
            vwap = a.get("vwap")
            rsi = a.get("rsi")
            sr = a.get("support_resistance") or {}
            sup = sr.get("support") or []
            res = sr.get("resistance") or []
            fvgs = a.get("fvgs") or []
            ote = a.get("ote_analysis")
            ob = a.get("order_blocks") or []

            if ema144 and ema169:
                lo = min(ema144, ema169)
                hi = max(ema144, ema169)
                pos = "上方" if current_price > hi else ("下方" if current_price < lo else "通道内")
                full.append("- Vegas通道: EMA144=${:,.2f}, EMA169=${:,.2f}（价格在{}）".format(ema144, ema169, pos))
            if vwap:
                rel = "上方" if current_price > vwap else "下方"
                full.append("- VWAP: ${:,.2f}（价格在其{}）".format(vwap, rel))
            if rsi is not None:
                full.append("- RSI: {:.1f}".format(rsi))
            if sup or res:
                full.append("- 支撑: {}".format(fmt_sr(sup)))
                full.append("- 阻力: {}".format(fmt_sr(res)))
            if ote:
                if ote.get("in_ote_zone"):
                    full.append("- OTE: 价格位于618-786区间内（关注回踩/反抽）")
                elif ote.get("above_786"):
                    full.append("- OTE: 价格已突破786（强势，回踩关注）")
                elif ote.get("below_618"):
                    full.append("- OTE: 价格低于618（弱势）")
                f618 = ote.get("fib_618"); f786 = ote.get("fib_786")
                if f618 and f786:
                    full.append("  - 618: ${:,.0f} / 786: ${:,.0f}".format(f618, f786))
            if fvgs:
                full.append("- FVG: 近{}处（最多列3个）".format(len(fvgs)))
                for f in fvgs[-3:]:
                    full.append("  - {}: ${:,.0f}-${:,.0f}".format("看涨" if f.get("type")=="bullish" else "看跌", f.get("low",0), f.get("high",0)))
            if ob:
                full.append("- 订单块: 检测到 {} 个（显示最近3个）".format(len(ob)))
                for b in ob[:3]:
                    full.append("  - {} OB: ${:,.0f}-${:,.0f} ({})".format("看涨" if b.get("type")=="bullish" else "看跌", b.get("low",0), b.get("high",0), b.get("strength","")))
            full.append("")

    # 末尾：4小时趋势背景（沿用简要版逻辑）
    full.append("---")
    full.append("")
    full.append("## 4小时趋势背景（仅供参考，不生成4小时入场/止损/止盈信号）")
    full.append("")
    if analysis_4h:
        ema144 = analysis_4h.get("ema_144"); ema169 = analysis_4h.get("ema_169")
        vwap = analysis_4h.get("vwap"); rsi = analysis_4h.get("rsi")
        sr = analysis_4h.get("support_resistance") or {}
        sup = sr.get("support") or []
        res = sr.get("resistance") or []
        if ema144 and ema169:
            lo = min(ema144, ema169); hi = max(ema144, ema169)
            pos = "上方" if current_price > hi else ("下方" if current_price < lo else "通道内")
            full.append("- 4小时EMA144: ${:,.2f}".format(ema144))
            full.append("- 4小时EMA169: ${:,.2f}".format(ema169))
            full.append("- 趋势位置: 价格在4小时Vegas通道{}".format(pos))
        if vwap:
            rel = "上方" if current_price > vwap else "下方"
            full.append("- 4小时VWAP: ${:,.2f}（价格在其{}）".format(vwap, rel))
        if rsi is not None:
            full.append("- 4小时RSI: {:.1f}".format(rsi))
        if sup:
            full.append("- 4小时支撑: {}".format(fmt_sr(sup)))
        if res:
            full.append("- 4小时阻力: {}".format(fmt_sr(res)))
    else:
        full.append("- 暂无法获取4小时K线或分析数据")

    out_full = outdir / f"BTC_de_signals_{timestamp}_style_filtered_full.md"
    out_full.write_text("\n".join(full), encoding="utf-8")
    print(f"已保存: {out_full}")


if __name__ == "__main__":
    main()
