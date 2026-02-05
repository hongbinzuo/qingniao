#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视觉匹配工具集

提供图像路径解析、图表渲染与缓存键生成等通用能力。
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent

try:
    from abu.chart_renderer import ChartRenderer
except Exception:
    ChartRenderer = None


def resolve_pattern_image_path(
    raw_path: Optional[str],
    source_page: Optional[int],
    image_dir: Optional[Path] = None,
) -> Optional[Path]:
    """解析模式库图片路径，兼容Windows/WSL/相对路径与页码回退"""
    image_dir = image_dir or (ROOT / "data" / "abu" / "images")
    candidates: List[Path] = []

    if raw_path:
        raw = str(raw_path)
        # 1) 原始路径
        try:
            candidates.append(Path(raw))
        except Exception:
            pass

        # 2) Windows 路径 -> WSL 路径
        if os.name != "nt" and ":" in raw[:3]:
            drive, rest = raw.split(":", 1)
            rest = rest.replace("\\", "/").lstrip("/")
            candidates.append(Path("/mnt") / drive.lower() / rest)

        # 3) 相对路径 -> 项目根目录
        if not os.path.isabs(raw):
            candidates.append(ROOT / raw)

        # 4) WSL 路径 -> Windows 路径
        if os.name == "nt" and raw.startswith("/mnt/"):
            parts = raw.split("/")
            if len(parts) > 3:
                drive = parts[2].upper()
                win_path = drive + ":\\" + "\\".join(parts[3:])
                candidates.append(Path(win_path))

        # 5) 仅文件名 -> 默认图片目录
        candidates.append(image_dir / Path(raw).name)

    # 6) 通过页码回退到 ebook 图片
    if isinstance(source_page, int):
        candidates.extend(sorted(image_dir.glob(f"page_{source_page:04d}_img_*.png")))

    for p in candidates:
        try:
            if p.exists():
                return p
        except Exception:
            continue
    return None


def render_chart_image(
    renderer: "ChartRenderer",
    klines: List[Dict],
    out_path: Path,
    include_volume: bool = False,
    include_ema: bool = True,
    ema_periods: Optional[List[int]] = None,
    show_grid: bool = False,
    show_axes: bool = False,
    show_title: bool = False,
    show_legend: bool = False,
) -> Optional[Path]:
    """渲染K线到图片文件"""
    if renderer is None or not klines:
        return None
    renderer.render_klines_to_image(
        klines,
        output_path=out_path,
        title="",
        include_volume=include_volume,
        include_ema=include_ema,
        ema_periods=ema_periods or [20],
        show_grid=show_grid,
        show_axes=show_axes,
        show_title=show_title,
        show_legend=show_legend,
    )
    return out_path if out_path.exists() else None


def make_cache_key(
    symbol: str,
    timeframe: str,
    klines: List[Dict],
    window: int = 5,
    suffix: Optional[str] = None,
) -> str:
    """基于最近K线生成缓存键"""
    if not klines or len(klines) < window:
        base = f"{symbol}_{timeframe}_{int(time.time() / 60)}"
    else:
        recent_closes = [k.get("close") for k in klines[-window:]]
        price_hash = hash(tuple(recent_closes))
        base = f"{symbol}_{timeframe}_{price_hash}"
    if suffix:
        return f"{base}_{suffix}"
    return base
