#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉确认信号试跑（JSON输出，可选写入PostgreSQL）

流程：
1) 从 DuckDB 读取本地K线（15m）
2) 从 pattern_library 读取可交易模式（gemini_annotation_json）
3) 算法匹配筛选候选
4) 视觉匹配确认（Gemini）
5) 通过阈值后生成信号并输出JSON
"""

from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import duckdb
import shutil
import re
import requests

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

import sys
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from abu.chart_renderer import ChartRenderer
from abu.ai_vision_matcher import AIVisionMatcher
from abu.vision_utils import resolve_pattern_image_path
from abu.vision_storage import VisionMatchRecorder
import abu.gemini_pattern_matcher_enhanced as gpm
from openrouter_config import get_openrouter_api_key, get_openrouter_api_url
try:
    from abu.ebook_knowledge_retriever import EbookKnowledgeRetriever
    EBOOK_AVAILABLE = True
except Exception:
    EbookKnowledgeRetriever = None
    EBOOK_AVAILABLE = False
try:
    from db_manager_trader import TraderDBManager
    PG_AVAILABLE = True
except Exception:
    TraderDBManager = None
    PG_AVAILABLE = False


DEFAULT_SYMBOLS = ["BTC", "ETH", "SOL", "BNB", "XRP"]


def _parse_table_name(table_name: str) -> Optional[Tuple[str, str]]:
    parts = table_name.split("_price_")
    if len(parts) != 2:
        return None
    symbol, timeframe = parts[0], parts[1]
    if not symbol or not timeframe:
        return None
    return symbol.upper(), timeframe


def _list_tables(con: duckdb.DuckDBPyConnection) -> List[str]:
    return [row[0] for row in con.execute("SHOW TABLES").fetchall()]


def _select_tables(
    tables: List[str],
    symbols: List[str],
    timeframes: List[str],
) -> Dict[Tuple[str, str], str]:
    """返回 {(symbol, timeframe): table_name}"""
    symbols_set = {s.upper() for s in symbols}
    timeframes_set = {tf.lower() for tf in timeframes}
    mapping: Dict[Tuple[str, str], str] = {}
    for name in tables:
        parsed = _parse_table_name(name)
        if not parsed:
            continue
        symbol, timeframe = parsed[0], parsed[1].lower()
        if symbol in symbols_set and timeframe in timeframes_set:
            mapping[(symbol, timeframe)] = name
    return mapping


def _fetch_latest_window(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    window: int,
) -> List[Dict]:
    query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM {table_name}
        ORDER BY timestamp DESC
        LIMIT {window}
    """
    rows = con.execute(query).fetchall()
    rows.reverse()
    klines: List[Dict] = []
    for row in rows:
        klines.append({
            "timestamp": int(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]) if row[5] is not None else 0.0,
        })
    return klines


def _resolve_image_path(image_path: str, image_dir: Path, source_page: Optional[int]) -> Optional[Path]:
    return resolve_pattern_image_path(image_path, source_page, image_dir=image_dir)


def _load_patterns_from_db(
    db_path: Path,
    image_dir: Path,
    exclude_types: List[str],
    min_confidence: float,
    matcher: "gpm.EnhancedGeminiPatternMatcher",
) -> Tuple[List[Dict], Dict[int, Dict], str]:
    rows = []
    source = "postgres"
    # 优先使用PostgreSQL
    if PG_AVAILABLE:
        try:
            db = TraderDBManager('abu')
            conn = db._get_connection(read_only=True)
            rows = conn.execute(
                """
                SELECT id, gemini_annotation_json, pattern_type, pattern_name,
                       source_page, image_path, confidence
                FROM pattern_library
                WHERE gemini_annotation_json IS NOT NULL AND gemini_annotation_json != ''
                """
            ).fetchall()
            db.close()
        except Exception:
            rows = []

    # PostgreSQL不可用则回退DuckDB
    if not rows:
        source = "duckdb"
        con = duckdb.connect(str(db_path))
        rows = con.execute(
            """
            SELECT id, gemini_annotation_json, pattern_type, pattern_name,
                   source_page, image_path, confidence
            FROM pattern_library
            WHERE gemini_annotation_json IS NOT NULL AND gemini_annotation_json != ''
            """
        ).fetchall()
        con.close()

    exclude_set = {t.strip().lower() for t in exclude_types if t.strip()}
    patterns: List[Dict] = []
    by_id: Dict[int, Dict] = {}
    for row in rows:
        # 兼容dict与tuple
        if isinstance(row, dict):
            pid = row.get("id")
            gemini_json = row.get("gemini_annotation_json")
            ptype = row.get("pattern_type")
            pname = row.get("pattern_name")
            source_page = row.get("source_page")
            image_path = row.get("image_path")
            conf = row.get("confidence")
        else:
            pid, gemini_json, ptype, pname, source_page, image_path, conf = row
        ptype_norm = (ptype or "").strip().lower()
        if ptype_norm in exclude_set:
            continue
        if conf is None:
            if min_confidence > 0:
                continue
        elif conf < min_confidence:
            continue
        try:
            gemini_annotation = json.loads(gemini_json)
        except Exception:
            continue
        if not matcher._is_actionable_pattern(gemini_annotation, gemini_json):
            continue
        resolved = _resolve_image_path(image_path, image_dir, source_page)
        if not resolved:
            continue
        entry = {
            "id": pid,
            "pattern_name": pname or "",
            "pattern_type": ptype or "",
            "gemini_annotation": gemini_annotation,
            "image_path": str(resolved),
            "source_page": source_page,
            "confidence": float(conf) if conf is not None else None,
        }
        patterns.append(entry)
        by_id[pid] = entry
    return patterns, by_id, source


def _safe_truncate(text: str, max_len: int = 800) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len] + ("..." if len(text) > max_len else "")


def _fetch_web_context(urls: List[str], timeout: int = 20, max_chars: int = 1200) -> List[Dict]:
    if not urls:
        return []
    context_items: List[Dict] = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code != 200:
                context_items.append({"url": url, "error": f"HTTP {resp.status_code}"})
                continue
            text = resp.text
            # 粗略去标签
            text = re.sub(r"<script.*?>.*?</script>", " ", text, flags=re.S)
            text = re.sub(r"<style.*?>.*?</style>", " ", text, flags=re.S)
            text = re.sub(r"<[^>]+>", " ", text)
            text = _safe_truncate(text, max_chars)
            context_items.append({"url": url, "content": text})
        except Exception as e:
            context_items.append({"url": url, "error": str(e)})
    return context_items


def _load_web_context_file(path: Optional[str]) -> List[Dict]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    text = p.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return [{"content": _safe_truncate(text)}]
    except Exception:
        return [{"content": _safe_truncate(text)}]


def _build_plan_prompt(
    symbol: str,
    timeframe: str,
    pattern: Dict,
    vision_result: Dict,
    klines: List[Dict],
    ebook_rules: List[Dict],
    web_context: List[Dict],
) -> str:
    closes = [k["close"] for k in klines[-20:]] if klines else []
    highs = [k["high"] for k in klines[-20:]] if klines else []
    lows = [k["low"] for k in klines[-20:]] if klines else []
    current_price = closes[-1] if closes else None
    recent_high = max(highs) if highs else None
    recent_low = min(lows) if lows else None
    atr = None
    if highs and lows:
        atr = sum(h - l for h, l in zip(highs, lows)) / len(highs)
    atr_pct = (atr / current_price) if atr and current_price else None

    rules_snippets = []
    for item in ebook_rules[:3]:
        rule = item.get("rules", {})
        context = item.get("context", "")
        rules_snippets.append({
            "book": item.get("book"),
            "chapter": item.get("chapter"),
            "section": item.get("section"),
            "rules": rule,
            "context": _safe_truncate(context, 400),
        })

    annotation = pattern.get("gemini_annotation") or {}
    parsed = annotation.get("parsed", annotation) if isinstance(annotation, dict) else {}
    pattern_list = parsed.get("patterns") or []
    pattern_names = []
    for p in pattern_list:
        if isinstance(p, dict) and p.get("name"):
            pattern_names.append(p.get("name"))
        elif isinstance(p, str):
            pattern_names.append(p)
    pattern_names = pattern_names[:6]
    price_behavior = parsed.get("price_action_behavior") or {}

    prompt = {
        "task": "Generate a Brooks-style trading plan (educational) with entry, stop, targets.",
        "instrument": symbol,
        "timeframe": timeframe,
        "pattern": {
            "name": pattern.get("pattern_name"),
            "type": pattern.get("pattern_type"),
            "annotation_patterns": pattern_names,
            "price_action": {
                "trend": price_behavior.get("trend"),
                "structure": price_behavior.get("structure"),
            },
        },
        "vision_summary": {
            "similarity_score": vision_result.get("similarity_score"),
            "confidence": vision_result.get("confidence"),
            "key_matches": vision_result.get("key_matches", []),
            "differences": vision_result.get("differences", []),
        },
        "market_context": {
            "current_price": current_price,
            "recent_high": recent_high,
            "recent_low": recent_low,
            "atr": atr,
            "atr_pct": atr_pct,
        },
        "ebook_rules": rules_snippets,
        "web_context": web_context[:3],
        "output_schema": {
            "direction": "long/short/neutral",
            "entry": "price or range",
            "stop_loss": "price",
            "take_profit_1": "price",
            "take_profit_2": "price",
            "invalidation": "condition",
            "risk_reward": "number",
            "confidence": "0-1",
            "notes": "short reasoning"
        },
        "constraints": [
            "Keep it concise.",
            "If data is insufficient, state assumptions.",
            "Do not fabricate ebook quotes.",
        ],
    }
    return json.dumps(prompt, ensure_ascii=False)


def _call_openrouter_text(prompt: str, model: str, max_tokens: int = 800) -> Dict:
    api_key = get_openrouter_api_key()
    api_url = get_openrouter_api_url()
    if not api_key:
        return {"error": "OpenRouter API Key not configured"}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/qingniao",
        "X-Title": "QingNiao Vision Trial Plan",
    }
    try:
        resp = requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}", "response": resp.text}
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"content": content}
    except Exception as e:
        return {"error": str(e)}


def _extract_json_from_text(text: str) -> Optional[Dict]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    # 尝试提取首个JSON对象
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _write_html_report(
    records: List[Dict],
    out_dir: Path,
    timestamp: str,
    top_n: int = 5,
) -> Optional[Path]:
    if not records:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / f"spotcheck_assets_{timestamp}"
    assets_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"spotcheck_{timestamp}.html"

    sorted_records = sorted(records, key=lambda r: r.get("final_score") or 0, reverse=True)
    top_records = sorted_records[:top_n]
    accepted_records = [r for r in sorted_records if r.get("signal")]

    parts = [
        "<!doctype html>",
        "<html lang=\"en\">",
        "<head><meta charset=\"utf-8\"><title>Vision Trial Report</title>",
        "<style>body{font-family:Arial, sans-serif} .case{margin:24px 0} "
        ".imgs{display:flex; gap:16px} img{max-width:48%; height:auto; "
        "border:1px solid #ccc} pre{white-space:pre-wrap}</style>",
        "</head><body>",
        "<h1>Vision Trial Report</h1>",
        f"<p>Top {len(top_records)} by final_score</p>",
    ]

    def render_record(rec: Dict):
        symbol = rec.get("symbol")
        timeframe = rec.get("timeframe")
        pattern_name = rec.get("pattern_name")
        final_score = rec.get("final_score") or 0
        vision_score = rec.get("vision_score") or 0
        chart = Path(rec.get("chart_image", ""))
        pattern = Path(rec.get("pattern_image", ""))

        chart_copy = assets_dir / f"{symbol}_{timeframe}_chart{chart.suffix or '.png'}"
        pattern_copy = assets_dir / f"{symbol}_{timeframe}_pattern{pattern.suffix or '.png'}"
        if chart.exists() and not chart_copy.exists():
            shutil.copy2(chart, chart_copy)
        if pattern.exists() and not pattern_copy.exists():
            shutil.copy2(pattern, pattern_copy)

        vr = rec.get("vision_result", {})
        plan = rec.get("gemini_plan") or {}
        key_matches = vr.get("key_matches") or []
        differences = vr.get("differences") or []
        reasoning = (vr.get("reasoning") or "").strip()

        parts.extend(
            [
                "<div class=\"case\">",
                f"<h2>{symbol} {timeframe} | {pattern_name} | final={final_score:.3f} vision={vision_score:.3f}</h2>",
                "<div class=\"imgs\">",
                f"<div><h3>Pattern Image</h3><img src=\"{assets_dir.name}/{pattern_copy.name}\" alt=\"pattern\"></div>",
                f"<div><h3>Chart Image</h3><img src=\"{assets_dir.name}/{chart_copy.name}\" alt=\"chart\"></div>",
                "</div>",
                "<h3>Key Matches</h3>",
                "<pre>" + "\n".join([f"- {k}" for k in key_matches]) + "</pre>",
                "<h3>Differences</h3>",
                "<pre>" + "\n".join([f"- {d}" for d in differences]) + "</pre>",
                "<h3>Reasoning (truncated)</h3>",
                "<pre>" + (reasoning[:900] + ("..." if len(reasoning) > 900 else "")) + "</pre>",
                "<h3>Gemini Plan</h3>",
                "<pre>" + _safe_truncate(json.dumps(plan, ensure_ascii=False), 1200) + "</pre>",
                "</div>",
            ]
        )

    for rec in top_records:
        render_record(rec)

    if accepted_records:
        parts.append("<h1>Accepted Signals</h1>")
        for rec in accepted_records:
            render_record(rec)

    parts.append("</body></html>")
    html_path.write_text("\n".join(parts), encoding="utf-8")
    return html_path


def main() -> int:
    parser = argparse.ArgumentParser(description="视觉确认信号试跑（JSON输出）")
    parser.add_argument("--kline-db", type=str, default="data/btc_price_timeseries.duckdb")
    parser.add_argument("--pattern-db", type=str, default="src/data/qingniao_abu.duckdb")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--timeframe", type=str, default="15m")
    parser.add_argument("--window", type=int, default=120)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--min-similarity", type=float, default=0.3)
    parser.add_argument("--vision-top-n", type=int, default=5)
    parser.add_argument("--vision-score", type=float, default=0.75)
    parser.add_argument("--final-score", type=float, default=0.70)
    parser.add_argument("--pattern-type-exclude", type=str, default="other,unknown,null")
    parser.add_argument("--min-confidence", type=float, default=0.6)
    parser.add_argument("--signal-completeness", type=str, default="none",
                        help="交易信号完整性要求(none/basic/trade_ready)")
    parser.add_argument("--vision-model", type=str, default="google/gemini-3-flash-preview")
    parser.add_argument("--plan-model", type=str, default="google/gemini-3-flash-preview")
    parser.add_argument("--web-urls", type=str, default="", help="逗号分隔的URL列表")
    parser.add_argument("--web-context-file", type=str, default="", help="预先整理的web摘要JSON/文本")
    parser.add_argument("--style", type=str, default="light")
    parser.add_argument("--sleep", type=float, default=0.5)
    parser.add_argument("--write-db", type=int, default=1, help="写入PostgreSQL(1/0)")
    args = parser.parse_args()

    kline_db = ROOT / args.kline_db
    pattern_db = ROOT / args.pattern_db
    image_dir = ROOT / "data" / "abu" / "images"
    if not kline_db.exists():
        print(f"❌ K线数据库不存在: {kline_db}")
        return 1
    if not pattern_db.exists():
        print(f"❌ pattern_library 数据库不存在: {pattern_db}")
        return 1
    if not image_dir.exists():
        print(f"❌ Brooks 图片目录不存在: {image_dir}")
        return 1

    # 禁用DB加载（使用本地duckdb）
    gpm.DB_AVAILABLE = False
    matcher = gpm.EnhancedGeminiPatternMatcher(
        use_dl=False,
        use_ml=False,
        use_ebook=False,
        min_confidence=0.0,
        exclude_other=True,
        require_trading_signals=True,
        exclude_unmarked=True,
        signal_completeness=args.signal_completeness,
    )

    exclude_types = [t.strip() for t in args.pattern_type_exclude.split(",") if t.strip()]
    patterns, patterns_by_id, pattern_source = _load_patterns_from_db(
        db_path=pattern_db,
        image_dir=image_dir,
        exclude_types=exclude_types,
        min_confidence=args.min_confidence,
        matcher=matcher,
    )
    if not patterns:
        print("❌ 可用模式为空（过滤后无候选）")
        return 1
    matcher.pattern_library = patterns

    chart_renderer = ChartRenderer(style=args.style)
    vision = AIVisionMatcher(model=args.vision_model)
    web_urls = [u.strip() for u in args.web_urls.split(",") if u.strip()]
    web_context = _fetch_web_context(web_urls) if web_urls else []
    web_context.extend(_load_web_context_file(args.web_context_file))
    ebook_retriever = None
    if EBOOK_AVAILABLE:
        try:
            ebook_retriever = EbookKnowledgeRetriever('abu')
        except Exception:
            ebook_retriever = None

    out_dir = ROOT / "outputs" / "vision_trial"
    charts_dir = out_dir / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)
    charts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    recorder = VisionMatchRecorder(enabled=bool(args.write_db))
    results_path = out_dir / f"vision_trial_results_{timestamp}.jsonl"
    summary_path = out_dir / f"vision_trial_summary_{timestamp}.md"

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    timeframe = args.timeframe.strip().lower()

    con = duckdb.connect(str(kline_db))
    tables = _list_tables(con)
    table_map = _select_tables(tables, symbols, [timeframe])

    summary_lines = [
        "# 视觉确认信号试跑",
        "",
        f"- Kline DB: {kline_db}",
        f"- Pattern DB: {pattern_db}",
        f"- Pattern source: {pattern_source}",
        f"- Symbols: {', '.join(symbols)}",
        f"- Timeframe: {timeframe}",
        f"- Window: {args.window}",
        f"- Candidates (algo): {args.max_candidates}",
        f"- Vision top N: {args.vision_top_n}",
        f"- Thresholds: vision>={args.vision_score}, final>={args.final_score}",
        f"- Pattern filters: exclude={exclude_types}, min_conf={args.min_confidence}",
        f"- Model: {args.vision_model}",
        f"- Plan model: {args.plan_model}",
        f"- Ebook rules: {'enabled' if ebook_retriever else 'disabled'}",
        f"- Web context: {len(web_context)} item(s)",
        "",
        "## Accepted Signals",
        "",
    ]

    accepted_count = 0
    records: List[Dict] = []
    with results_path.open("w", encoding="utf-8") as f:
        for symbol in symbols:
            table_name = table_map.get((symbol, timeframe))
            if not table_name:
                continue
            klines = _fetch_latest_window(con, table_name, args.window)
            if not klines or len(klines) < 20:
                continue
            klines_dict = {timeframe: klines}

            # 算法匹配
            algo_matches = matcher.match_patterns(
                klines_dict=klines_dict,
                min_similarity=args.min_similarity,
                max_matches=args.max_candidates,
            )
            if not algo_matches:
                continue

            # 渲染纯K线图（无噪声）
            chart_path = charts_dir / f"{symbol}_{timeframe}_{timestamp}.png"
            chart_renderer.render_klines_to_image(
                klines,
                output_path=chart_path,
                title="",
                include_volume=False,
                include_ema=True,
                ema_periods=[20],
                show_grid=False,
                show_axes=False,
                show_title=False,
                show_legend=False,
            )
            if not chart_path.exists():
                continue

            # 视觉匹配（Top N）
            top_candidates = algo_matches[: max(1, args.vision_top_n)]
            for match in top_candidates:
                pid = match["pattern_id"]
                pattern = patterns_by_id.get(pid)
                if not pattern:
                    continue
                pattern_image = Path(pattern["image_path"])
                vision_result = vision.compare_two_images(
                    image1_path=pattern_image,
                    image2_path=chart_path,
                    context=f"{symbol} {timeframe} trial",
                )
                vision_score = vision_result.similarity_score / 100.0
                final_score = (match["similarity"] * 0.4) + (vision_score * 0.6)

                signal = None
                gemini_plan = None
                if vision_score >= args.vision_score and final_score >= args.final_score:
                    current_price = klines[-1]["close"]
                    signal = matcher.generate_signal_from_match(
                        match=match,
                        current_price=current_price,
                        klines_15m=klines,
                    )
                    # 读取电子书规则（PostgreSQL）
                    ebook_rules = []
                    if ebook_retriever:
                        query_key = pattern.get("pattern_type") or pattern.get("pattern_name")
                        if query_key:
                            try:
                                ebook_rules = ebook_retriever.get_trading_rules(query_key)
                            except Exception:
                                ebook_rules = []
                    plan_prompt = _build_plan_prompt(
                        symbol=symbol,
                        timeframe=timeframe,
                        pattern=pattern,
                        vision_result=asdict(vision_result),
                        klines=klines,
                        ebook_rules=ebook_rules,
                        web_context=web_context,
                    )
                    plan_resp = _call_openrouter_text(plan_prompt, model=args.plan_model)
                    if isinstance(plan_resp, dict) and "content" in plan_resp:
                        parsed = _extract_json_from_text(plan_resp.get("content"))
                        gemini_plan = parsed if parsed else plan_resp
                    else:
                        gemini_plan = plan_resp
                    if signal:
                        accepted_count += 1
                        summary_lines.append(
                            f"- {symbol} {timeframe} | {pattern['pattern_name']} | "
                            f"vision={vision_score:.3f} final={final_score:.3f}"
                        )

                record = {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "pattern_id": pid,
                    "pattern_name": pattern.get("pattern_name"),
                    "pattern_type": pattern.get("pattern_type"),
                    "algorithm_score": match["similarity"],
                    "vision_score": vision_score,
                    "final_score": final_score,
                    "vision_result": asdict(vision_result),
                    "signal": signal,
                    "gemini_plan": gemini_plan,
                    "ebook_rules": ebook_rules if ebook_rules else [],
                    "web_context_count": len(web_context),
                    "chart_image": str(chart_path),
                    "pattern_image": str(pattern_image),
                }
                if recorder:
                    recorder.record_match({
                        "source": "vision_confirmed_trial",
                        "batch_id": timestamp,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "pattern_id": str(pid),
                        "pattern_name": pattern.get("pattern_name"),
                        "pattern_type": pattern.get("pattern_type"),
                        "algorithm_score": match["similarity"],
                        "vision_score": vision_score,
                        "final_score": final_score,
                        "accepted": bool(signal),
                        "model": args.vision_model,
                        "pattern_image": str(pattern_image),
                        "chart_image": str(chart_path),
                        "vision_result": record.get("vision_result"),
                        "extra": {
                            "signal": signal is not None,
                            "web_context_count": len(web_context),
                        },
                    })
                records.append(record)
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                f.flush()
                time.sleep(max(args.sleep, 0))

    con.close()
    summary_lines.append("")
    summary_lines.append(f"Total accepted: {accepted_count}")
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    html_path = _write_html_report(records, out_dir, timestamp, top_n=5)
    if html_path:
        print(f"✅ 详情HTML已保存: {html_path}")
    print(f"✅ 结果已保存: {results_path}")
    print(f"✅ 汇总已保存: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
