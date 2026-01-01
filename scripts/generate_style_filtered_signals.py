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
    """获取多源 BTCUSDT 实时价格（Gate.io / Bitget / Binance）。"""
    gate = {"exchange": "Gate.io", "price": None, "error": None}
    bitget = {"exchange": "Bitget", "price": None, "error": None}
    binance = {"exchange": "Binance", "price": None, "error": None}

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
    # Binance
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "BTCUSDT"},
            timeout=12,
        )
        d = r.json()
        if d and d.get("price"):
            binance["price"] = float(d["price"]) 
            binance["raw"] = d
    except Exception as e:
        binance["error"] = str(e)

    return gate, bitget, binance


def main():
    ap = argparse.ArgumentParser(description="生成风格筛选版BTC信号")
    # RR 改为软参考：默认0，不作硬过滤，仅用于展示与轻微排序
    ap.add_argument("--min-rr", type=float, default=0.0, help="盈亏比软阈值（仅参考），默认0不过滤")
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
    gate, bitget, binance = get_tickers()
    prices = [p for p in (gate.get("price"), bitget.get("price"), binance.get("price")) if p]
    if prices:
        # 使用多源中位数更稳健
        current_price = sorted(prices)[len(prices)//2]
        if gate.get("price") == current_price:
            price_src = "Gate.io ticker"
        elif bitget.get("price") == current_price:
            price_src = "Bitget ticker"
        else:
            price_src = "Binance ticker"
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
    # 改善SR：用 swing+聚类 + 多周期合并
    try:
        from sr_detector import detect_levels, merge_multi_tf
        lv_15 = detect_levels(k15, window=5, grid=50, topk=6)
        lv_1h = detect_levels(k1h or [], window=5, grid=50, topk=6)
        merged = merge_multi_tf([lv_15, lv_1h], grid=50, topk=8)
        if analyses['15m'] is not None:
            analyses['15m']['support_resistance']={'support': merged['supports'], 'resistance': merged['resistances']}
        if analyses['1h'] is not None:
            analyses['1h']['support_resistance']={'support': merged['supports'], 'resistance': merged['resistances']}
    except Exception:
        pass

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
            # 不再硬过滤RR，全部纳入候选，由后续评分选优
            filtered.append(sig)

        if filtered:
            def score_good(s):
                # 轻微考虑RR，主要由后续“信心标记”给出可靠性说明
                strength = 3 if s["strength"] == "strong" else 2 if s["strength"] == "medium" else 1
                return (s["_rr"].get("avg_rr_ratio", 0.0) * 0.2 + strength)
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
    # 展示多源与价差
    srcs = []
    for src in (gate, bitget, binance):
        if src.get('price'):
            srcs.append(f"{src['exchange']}: ${src['price']:,.2f}")
    if len(prices) >= 2:
        mi, ma = min(prices), max(prices)
        spread = (abs(ma - mi) / ((ma + mi) / 2)) * 100
        cp_line += " | " + " / ".join(srcs) + f" (跨源最大价差 {spread:.3f}%)"
    lines.append(cp_line + "  ")
    lines.append("**筛选条件**: RR≥{}, 排除关键词: {}  ".format(args.min_rr, ", ".join(exclude_keywords)))
    lines.append("")
    # 执行建议（统一出现在简要版顶部，便于快速决策）
    try:
        lines.append("## 执行建议")
        # 4小时趋势过滤
        bias_line = None
        if analysis_4h and analysis_4h.get("ema_144") and analysis_4h.get("ema_169"):
            lo = min(analysis_4h["ema_144"], analysis_4h["ema_169"]) 
            hi = max(analysis_4h["ema_144"], analysis_4h["ema_169"]) 
            vwap_4h = analysis_4h.get("vwap")
            if current_price > hi and (vwap_4h is None or current_price > vwap_4h):
                bias_line = "- 趋势过滤: 4h 偏多，仅做多；逆势空直接过滤"
            elif current_price < lo and (vwap_4h is None or current_price < vwap_4h):
                bias_line = "- 趋势过滤: 4h 偏空，仅做空；逆势多直接过滤"
            else:
                bias_line = "- 趋势过滤: 4h 震荡，优先边界回踩/反抽，谨慎逆势"
        if bias_line:
            lines.append(bias_line)
        # 入场纪律（只接回踩 + 5m确认）
        ote_line = "- 入场纪律: 只接回踩至 OTE 0.618–0.786/关键位，出现5m反转确认（针/吞没+放量）后入场"
        try:
            oa = (analysis_4h or {}).get("ote_analysis") or {}
            f618 = oa.get("fib_618"); f786 = oa.get("fib_786")
            if f618 and f786:
                ote_line += f"（参考: 0.618=${f618:,.0f} / 0.786=${f786:,.0f}）"
        except Exception:
            pass
        lines.append(ote_line)
        # 风险/目标与RR
        lines.append(f"- 风险/目标: 止损设最近摆动点；分级止盈（RR≥1.0、RR≥{args.min_rr:.2f}）；加权RR≥{args.min_rr:.2f} 方可入场")
        # 失效条件
        lines.append("- 失效条件: N根K线未成交作废；若先破坏入场方向的关键结构/均线/VWAP，信号作废")
        lines.append("")
    except Exception:
        # 建议生成失败时不影响主流程
        pass
    # 情绪/流向
    sent = {}
    try:
        from sentiment_aggregator import aggregate_sentiment
        sent = aggregate_sentiment()
        parts=[]
        if isinstance(sent.get('sentiment_score'), (int,float)):
            parts.append(f"情绪分: {sent['sentiment_score']:+.1f}")
        if isinstance(sent.get('coinbase_premium_pct'), (int,float)):
            parts.append(f"CB溢价: {sent['coinbase_premium_pct']:+.2f}%")
        if isinstance(sent.get('binance_ls_ratio'), (int,float)):
            parts.append(f"LS比: {sent['binance_ls_ratio']:.2f}")
        if isinstance(sent.get('funding_rate_pct'), (int,float)):
            parts.append(f"资金费: {sent['funding_rate_pct']:+.3f}%")
        if parts:
            lines.append("**情绪/流向**: "+" | ".join(parts))
            lines.append("")
    except Exception:
        pass
    # 战术指引（De.）：883 与 0.618-0.786
    try:
        fibs = []
        for tfk in ("15m", "1h"):
            a = analyses.get(tfk)
            if a and a.get("ote_analysis"):
                oa = a["ote_analysis"]
                f618 = oa.get("fib_618"); f786 = oa.get("fib_786")
                if f618 and f786:
                    fibs.append((tfk, f618, f786))
        if fibs:
            tfk, f618, f786 = fibs[0]
            lines.append("战术指引（De.）：")
            lines.append(f"- {tfk} 回撤区间: 0.618=${f618:,.0f} / 0.786=${f786:,.0f}")
            lines.append("- 未破883且价格回到0.618-0.786附近 → 优先空，止损放0.786上方；")
            lines.append("- 强穿883并回踩不破 → 翻多，目标90k，失效为跌回883下方。")
            lines.append("")
    except Exception:
        pass

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
        def calc_confidence(tf, sig):
            # 评分要素：OTE命中、883一致性、SR接近、多周期偏向、形态确认
            score = 0
            clues = []
            a = analyses.get(tf)
            # OTE
            try:
                oa = a.get('ote_analysis') if a else None
                if oa:
                    f618 = oa.get('fib_618'); f786 = oa.get('fib_786')
                    if f618 and f786:
                        if sig['entry']>=min(f618,f786) and sig['entry']<=max(f618,f786):
                            score += 25; clues.append('OTE')
                        else:
                            # 距离边界<0.2%
                            dist = min(abs(sig['entry']-f618), abs(sig['entry']-f786))/sig['entry']*100
                            if dist < 0.2:
                                score += 15; clues.append('OTE邻近')
            except Exception:
                pass
            # 883 规则一致性
            try:
                if sig['type']=='short':
                    if sig['entry'] < 88300: score += 10; clues.append('883下空')
                    if abs(sig['entry']-88300)/sig['entry']*100 < 0.2: score += 5
                else:
                    if sig['entry'] > 88300: score += 10; clues.append('883上多')
                    if abs(sig['entry']-88300)/sig['entry']*100 < 0.2: score += 5
            except Exception:
                pass
            # SR 接近
            try:
                sr = a.get('support_resistance') if a else {}
                arr = (sr.get('resistance') or []) if sig['type']=='short' else (sr.get('support') or [])
                if arr:
                    d = min(abs(sig['entry']-x)/sig['entry']*100 for x in arr)
                    if d < 0.2: score += 10; clues.append('SR邻近')
            except Exception:
                pass
            # 多周期偏向（EMA144/169同向）
            try:
                bias_score = 0
                for tfk in ('15m','1h'):
                    aa = analyses.get(tfk)
                    if aa and aa.get('ema_144') and aa.get('ema_169'):
                        lo = min(aa['ema_144'], aa['ema_169']); hi = max(aa['ema_144'], aa['ema_169'])
                        if sig['type']=='short' and current_price<lo: bias_score += 1
                        if sig['type']=='long' and current_price>hi: bias_score += 1
                if bias_score==2: score += 20; clues.append('多周期一致')
                elif bias_score==1: score += 10; clues.append('部分一致')
            except Exception:
                pass
            # 形态确认
            try:
                em = (sig.get('entry_model') or '').lower()
                if 'pinbar' in em or '形态' in em: score += 10; clues.append('形态确认')
            except Exception:
                pass
            # 情绪加权（逆向倾向）：FG/CB溢价/LS比/资金费
            try:
                emo = sent if isinstance(sent, dict) else {}
                ls = emo.get('binance_ls_ratio'); prem = emo.get('coinbase_premium_pct')
                fg = emo.get('sentiment_score'); fr = emo.get('funding_rate_pct')
                adj = 0
                if sig['type']=='short':
                    if isinstance(ls,(int,float)) and ls>1.15: adj += 6; clues.append('LS偏多逆向+')
                    if isinstance(prem,(int,float)) and prem>0.1: adj += 4
                    if isinstance(fg,(int,float)) and fg>+20: adj += 4
                    if isinstance(fr,(int,float)) and fr>0.02: adj += 3
                else:
                    if isinstance(ls,(int,float)) and ls<0.85: adj += 6; clues.append('LS偏空逆向+')
                    if isinstance(prem,(int,float)) and prem<-0.1: adj += 4
                    if isinstance(fg,(int,float)) and fg<-20: adj += 4
                    if isinstance(fr,(int,float)) and fr<-0.01: adj += 3
                # 轻微惩罚：与逆向倾向相反时扣分
                if adj==0:
                    if isinstance(fg,(int,float)):
                        if sig['type']=='short' and fg<-15: adj -= 3
                        if sig['type']=='long' and fg>+15: adj -= 3
                score += adj
                if adj>0: clues.append('情绪加权+')
                if adj<0: clues.append('情绪加权-')
            except Exception:
                pass
            # 映射为等级
            if score>=60: label,prob='A',0.68
            elif score>=45: label,prob='B',0.58
            elif score>=30: label,prob='C',0.50
            else: label,prob='D',0.45
            return label,prob,score,clues

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
            label,prob,score,clues = calc_confidence(tf, sig)
            if clues:
                lines.append(f"- 信心: {label} (≈{int(prob*100)}%) | 得分 {score}/100 | 线索: {', '.join(clues)}")
            lines.append("")

    # 技术组合胜率快照
    try:
        from label_de_trades_techniques import format_combo_snapshot
        snap_lines = format_combo_snapshot([20,50])
        if snap_lines:
            lines.append('---')
            lines.append('')
            lines.append('## 技术组合胜率快照（最近20/50笔）')
            lines.extend(snap_lines)
            lines.append('')
    except Exception:
        pass

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
    srcs = []
    for src in (gate, bitget, binance):
        if src.get('price'):
            srcs.append(f"{src['exchange']}: ${src['price']:,.2f}")
    if len(prices) >= 2:
        mi, ma = min(prices), max(prices)
        spread = (abs(ma - mi) / ((ma + mi) / 2)) * 100
        cp_line_f += " | " + " / ".join(srcs) + f" (跨源最大价差 {spread:.3f}%)"
    full.append(cp_line_f + "  ")
    full.append("**筛选条件**: RR≥{}, 排除关键词: {}  ".format(args.min_rr, ", ".join(exclude_keywords)))
    full.append("")
    # 同步执行建议到详细版
    try:
        full.append("### 执行建议")
        bias_line = None
        if analysis_4h and analysis_4h.get("ema_144") and analysis_4h.get("ema_169"):
            lo = min(analysis_4h["ema_144"], analysis_4h["ema_169"]) 
            hi = max(analysis_4h["ema_144"], analysis_4h["ema_169"]) 
            vwap_4h = analysis_4h.get("vwap")
            if current_price > hi and (vwap_4h is None or current_price > vwap_4h):
                bias_line = "- 趋势过滤: 4h 偏多，仅做多；逆势空直接过滤"
            elif current_price < lo and (vwap_4h is None or current_price < vwap_4h):
                bias_line = "- 趋势过滤: 4h 偏空，仅做空；逆势多直接过滤"
            else:
                bias_line = "- 趋势过滤: 4h 震荡，优先边界回踩/反抽，谨慎逆势"
        if bias_line:
            full.append(bias_line)
        ote_line = "- 入场纪律: 只接回踩至 OTE 0.618–0.786/关键位，出现5m反转确认（针/吞没+放量）后入场"
        try:
            oa = (analysis_4h or {}).get("ote_analysis") or {}
            f618 = oa.get("fib_618"); f786 = oa.get("fib_786")
            if f618 and f786:
                ote_line += f"（参考: 0.618=${f618:,.0f} / 0.786=${f786:,.0f}）"
        except Exception:
            pass
        full.append(ote_line)
        full.append(f"- 风险/目标: 止损设最近摆动点；分级止盈（RR≥1.0、RR≥{args.min_rr:.2f}）；加权RR≥{args.min_rr:.2f} 方可入场")
        full.append("- 失效条件: N根K线未成交作废；若先破坏入场方向的关键结构/均线/VWAP，信号作废")
        full.append("")
    except Exception:
        pass
    # 同步战术指引到详细版
    try:
        fibs = []
        for tfk in ("15m", "1h"):
            a = analyses.get(tfk)
            if a and a.get("ote_analysis"):
                oa = a["ote_analysis"]
                f618 = oa.get("fib_618"); f786 = oa.get("fib_786")
                if f618 and f786:
                    fibs.append((tfk, f618, f786))
        if fibs:
            tfk, f618, f786 = fibs[0]
            full.append("### 战术指引（De.）")
            full.append("")
            full.append(f"- {tfk} 回撤区间: 0.618=${f618:,.0f} / 0.786=${f786:,.0f}")
            full.append("- 未破883且价格回到0.618-0.786附近 → 优先空，止损放0.786上方；")
            full.append("- 强穿883并回踩不破 → 翻多，目标90k，失效为跌回883下方。")
            full.append("")
    except Exception:
        pass

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

    # 技术组合胜率快照（详细版同样附上）
    try:
        from label_de_trades_techniques import format_combo_snapshot
        snap_lines = format_combo_snapshot([20,50])
        if snap_lines:
            full.append('---')
            full.append('')
            full.append('## 技术组合胜率快照（最近20/50笔）')
            full.extend(snap_lines)
            full.append('')
    except Exception:
        pass

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
