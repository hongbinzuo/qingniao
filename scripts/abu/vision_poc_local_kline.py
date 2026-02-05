#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地K线 + Brooks图表的视觉匹配POC（Option 2）

功能：
1) 从 DuckDB 读取本地K线数据
2) 渲染K线为图表图片
3) 随机抽取 Brooks 图表进行视觉相似度比较（OpenRouter + Gemini）
4) 输出JSONL结果与简要汇总

注意：
- 仅使用本地K线数据（不访问交易所）
- 视觉匹配会产生API费用，请自行控制 cases 与 candidates
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

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"

import sys
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from abu.chart_renderer import ChartRenderer
    from abu.ai_vision_matcher import AIVisionMatcher
    from abu.vision_utils import resolve_pattern_image_path
except Exception as exc:
    print(f"❌ 依赖导入失败: {exc}")
    raise


DEFAULT_SYMBOLS = [
    "BTC", "ETH", "BNB", "SOL", "XRP",
    "ADA", "DOGE", "AVAX", "DOT", "LINK"
]


def _parse_table_name(table_name: str) -> Optional[Tuple[str, str]]:
    """解析 DuckDB 表名: {symbol}_price_{timeframe}"""
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
) -> List[Tuple[str, str, str]]:
    """筛选符合条件的表 -> (table_name, symbol, timeframe)"""
    symbols_set = {s.upper() for s in symbols}
    timeframes_set = {tf.lower() for tf in timeframes}
    selected: List[Tuple[str, str, str]] = []
    for name in tables:
        parsed = _parse_table_name(name)
        if not parsed:
            continue
        symbol, timeframe = parsed[0], parsed[1].lower()
        if symbol in symbols_set and timeframe in timeframes_set:
            selected.append((name, symbol, timeframe))
    return selected


def _fetch_window(
    con: duckdb.DuckDBPyConnection,
    table_name: str,
    window: int,
    offset: int,
) -> List[Dict]:
    """获取一段K线窗口"""
    query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM {table_name}
        ORDER BY timestamp
        LIMIT {window} OFFSET {offset}
    """
    rows = con.execute(query).fetchall()
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


def _count_rows(con: duckdb.DuckDBPyConnection, table_name: str) -> int:
    return int(con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])


def _sample_cases(
    con: duckdb.DuckDBPyConnection,
    tables: List[Tuple[str, str, str]],
    cases: int,
    window: int,
    seed: int,
) -> List[Dict]:
    """从表中抽样case"""
    rnd = random.Random(seed)
    sampled: List[Dict] = []
    if not tables:
        return sampled

    # 预计算每张表的行数
    counts = {}
    for table_name, _, _ in tables:
        counts[table_name] = _count_rows(con, table_name)

    valid_tables = [t for t in tables if counts[t[0]] >= window]
    if not valid_tables:
        return sampled

    for case_id in range(1, cases + 1):
        table_name, symbol, timeframe = rnd.choice(valid_tables)
        max_offset = counts[table_name] - window
        offset = rnd.randint(0, max_offset) if max_offset > 0 else 0
        klines = _fetch_window(con, table_name, window, offset)
        if not klines:
            continue
        sampled.append({
            "case_id": case_id,
            "table_name": table_name,
            "symbol": symbol,
            "timeframe": timeframe,
            "offset": offset,
            "window": window,
            "start_ts": klines[0]["timestamp"],
            "end_ts": klines[-1]["timestamp"],
            "klines": klines,
        })
    return sampled


def _list_images(image_dir: Path) -> List[Path]:
    return sorted(list(image_dir.glob("*.png")) + list(image_dir.glob("*.jpg")))


def _resolve_image_path(image_path: str, image_dir: Path, source_page: Optional[int]) -> Optional[Path]:
    return resolve_pattern_image_path(image_path, source_page, image_dir=image_dir)


def _load_pattern_images_from_db(
    db_path: Path,
    image_dir: Path,
    exclude_types: List[str],
    min_confidence: float,
) -> List[Dict]:
    con = duckdb.connect(str(db_path))
    rows = con.execute(
        """
        SELECT id, pattern_name, pattern_type, image_path, confidence, source_page
        FROM pattern_library
        WHERE (image_path IS NOT NULL AND image_path != '')
           OR source_page IS NOT NULL
        """
    ).fetchall()
    con.close()

    exclude_set = {t.strip().lower() for t in exclude_types if t.strip()}
    results: List[Dict] = []
    for row in rows:
        pid, name, ptype, image_path, conf, source_page = row
        ptype_norm = (ptype or "").strip().lower()
        if ptype_norm in exclude_set:
            continue
        if conf is None:
            if min_confidence > 0:
                continue
        elif conf < min_confidence:
            continue
        resolved = _resolve_image_path(image_path, image_dir, source_page)
        if not resolved:
            continue
        results.append({
            "id": pid,
            "pattern_name": name or "",
            "pattern_type": ptype or "",
            "image_path": str(resolved),
            "confidence": float(conf) if conf is not None else None,
        })
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="本地K线视觉匹配POC（DuckDB）")
    parser.add_argument("--db-path", type=str, default="data/btc_price_timeseries.duckdb")
    parser.add_argument("--pattern-db", type=str, default="src/data/qingniao_abu.duckdb")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_SYMBOLS))
    parser.add_argument("--timeframes", type=str, default="15m")
    parser.add_argument("--cases", type=int, default=30)
    parser.add_argument("--window", type=int, default=120)
    parser.add_argument("--candidates", type=int, default=5, help="每个case比较的Brooks图片数")
    parser.add_argument("--pattern-type-exclude", type=str, default="other,unknown,null",
                        help="排除的pattern_type（逗号分隔）")
    parser.add_argument("--min-confidence", type=float, default=0.6, help="最小置信度阈值")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--vision-model", type=str, default="google/gemini-3-flash-preview")
    parser.add_argument("--style", type=str, default="dark_background")
    parser.add_argument("--include-volume", action="store_true")
    parser.add_argument("--include-ema", action="store_true")
    parser.add_argument("--pure-klines", action="store_true", help="纯K线图（无标题/网格/坐标轴/图例）")
    parser.add_argument("--sleep", type=float, default=0.5, help="每次视觉请求间隔秒数")
    parser.add_argument("--image-dir", type=str, default="data/abu/images")
    args = parser.parse_args()

    db_path = ROOT / args.db_path
    image_dir = ROOT / args.image_dir
    if not db_path.exists():
        print(f"❌ DuckDB 文件不存在: {db_path}")
        return 1
    if not image_dir.exists():
        print(f"❌ Brooks 图片目录不存在: {image_dir}")
        return 1

    # 初始化视觉匹配器
    try:
        vision = AIVisionMatcher(model=args.vision_model)
    except Exception as exc:
        print(f"❌ 视觉匹配器初始化失败: {exc}")
        return 1

    # 初始化图表渲染器
    try:
        renderer = ChartRenderer(style=args.style)
    except Exception as exc:
        print(f"❌ 图表渲染器初始化失败: {exc}")
        return 1

    out_dir = ROOT / "outputs" / "vision_poc_local"
    chart_dir = out_dir / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)
    chart_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_path = out_dir / f"vision_poc_results_{timestamp}.jsonl"
    summary_path = out_dir / f"vision_poc_summary_{timestamp}.md"

    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    timeframes = [t.strip().lower() for t in args.timeframes.split(",") if t.strip()]

    con = duckdb.connect(str(db_path))
    tables = _list_tables(con)
    selected_tables = _select_tables(tables, symbols, timeframes)

    if not selected_tables:
        print("❌ 未找到匹配的K线表，请检查 symbols/timeframes")
        return 1

    cases = _sample_cases(
        con=con,
        tables=selected_tables,
        cases=args.cases,
        window=args.window,
        seed=args.seed,
    )
    if not cases:
        print("❌ 无可用case（可能窗口过大或表为空）")
        return 1

    # 准备Brooks图片池（优先使用pattern_library）
    pattern_db_path = ROOT / args.pattern_db
    if not pattern_db_path.exists():
        print(f"❌ pattern_library 数据库不存在: {pattern_db_path}")
        return 1
    exclude_types = [t.strip() for t in args.pattern_type_exclude.split(",") if t.strip()]
    images_all = _load_pattern_images_from_db(
        db_path=pattern_db_path,
        image_dir=image_dir,
        exclude_types=exclude_types,
        min_confidence=args.min_confidence,
    )
    if not images_all:
        print("❌ Brooks 图片池为空（过滤后无可用图片）")
        return 1

    summary_lines = [
        "# 本地K线视觉匹配POC结果",
        "",
        f"- DB: {db_path}",
        f"- Symbols: {', '.join(symbols)}",
        f"- Timeframes: {', '.join(timeframes)}",
        f"- Cases: {len(cases)}",
        f"- Window: {args.window}",
        f"- Candidates per case: {args.candidates}",
        f"- Pattern DB: {pattern_db_path}",
        f"- Pattern filters: exclude={exclude_types}, min_conf={args.min_confidence}",
        f"- Model: {args.vision_model}",
        f"- Pure klines: {args.pure_klines}",
        "",
        "## Top Matches",
        "",
    ]

    show_grid = not args.pure_klines
    show_axes = not args.pure_klines
    show_title = not args.pure_klines
    show_legend = not args.pure_klines
    include_volume = args.include_volume and not args.pure_klines
    include_ema = args.include_ema and not args.pure_klines

    with results_path.open("w", encoding="utf-8") as f:
        for case in cases:
            case_id = case["case_id"]
            chart_path = chart_dir / f"case_{case_id:03d}.png"
            renderer.render_klines_to_image(
                case["klines"],
                output_path=chart_path,
                title=f"{case['symbol']} {case['timeframe']}",
                include_volume=include_volume,
                include_ema=include_ema,
                show_grid=show_grid,
                show_axes=show_axes,
                show_title=show_title,
                show_legend=show_legend,
            )
            if not chart_path.exists():
                print(f"⚠️  Case {case_id:03d} 渲染失败，跳过")
                continue

            rnd_case = random.Random(args.seed + case_id)
            if args.candidates >= len(images_all):
                images_pool = images_all
            else:
                images_pool = rnd_case.sample(images_all, args.candidates)

            matches = []
            for img_item in images_pool:
                img_path = Path(img_item["image_path"])
                result = vision.compare_two_images(
                    image1_path=img_path,
                    image2_path=chart_path,
                    context=f"Case {case_id} {case['symbol']} {case['timeframe']}",
                )
                matches.append({
                    "pattern_image": str(img_path),
                    "pattern_name": img_item.get("pattern_name", ""),
                    "pattern_type": img_item.get("pattern_type", ""),
                    "vision_result": asdict(result),
                })
                time.sleep(max(args.sleep, 0))

            # 选出最佳匹配
            best = None
            for item in matches:
                score = item["vision_result"].get("similarity_score", 0)
                if best is None or score > best["vision_result"].get("similarity_score", 0):
                    best = item

            record = {
                "case_id": case_id,
                "symbol": case["symbol"],
                "timeframe": case["timeframe"],
                "table_name": case["table_name"],
                "offset": case["offset"],
                "window": case["window"],
                "start_ts": case["start_ts"],
                "end_ts": case["end_ts"],
                "chart_image": str(chart_path),
                "matches": matches,
                "best_match": best,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()

            if best:
                best_score = best["vision_result"].get("similarity_score", 0)
                summary_lines.append(
                    f"- Case {case_id:03d} | {case['symbol']} {case['timeframe']} | "
                    f"Best: {Path(best['pattern_image']).name} | Score: {best_score}"
                )

            print(f"✓ 完成 Case {case_id:03d} / {len(cases)}")

    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"✅ 结果已保存: {results_path}")
    print(f"✅ 汇总已保存: {summary_path}")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
