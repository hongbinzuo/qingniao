#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多时间框架支撑阻力识别（无第三方依赖）

方法概述：
- 基于 swing high/low（Fractal，窗口 w）提取候选价位
- 使用价格网格聚类（grid=价格步长，如 50 美元）合并相近价位
- 以触发次数和新近权重评分，输出最强的 supports/resistances

接口：
  detect_levels(klines, window=5, grid=50, topk=6) -> dict
  merge_multi_tf(list_of_levels) -> dict
"""
from __future__ import annotations
from typing import List, Dict, Tuple


def _swings(klines: List[Dict], window: int = 5) -> Tuple[List[float], List[float]]:
    highs, lows = [], []
    n = len(klines)
    if n < window * 2 + 1:
        return highs, lows
    for i in range(window, n - window):
        h = klines[i]['high']; l = klines[i]['low']
        if all(h >= klines[j]['high'] for j in range(i - window, i + window + 1)):
            highs.append((i, h))
        if all(l <= klines[j]['low'] for j in range(i - window, i + window + 1)):
            lows.append((i, l))
    return highs, lows


def _cluster(levels: List[Tuple[int, float]], grid: float = 50.0, n: int = 0) -> List[Tuple[float, float]]:
    # 价格四舍五入到网格，累积计数并加新近权重（越近权重越高）
    buckets: Dict[float, float] = {}
    for idx, price in levels:
        key = round(price / grid) * grid
        # 新近权重：越靠近末尾 idx 越大
        recency = 1.0 + (idx / max(n, 1))
        buckets[key] = buckets.get(key, 0.0) + recency
    # 转为列表 (price, score)
    items = [(k, v) for k, v in buckets.items()]
    items.sort(key=lambda x: x[1], reverse=True)
    return items


def detect_levels(klines: List[Dict], window: int = 5, grid: float = 50.0, topk: int = 6) -> Dict[str, List[float]]:
    if not klines:
        return {'supports': [], 'resistances': []}
    swings_h, swings_l = _swings(klines, window=window)
    n = len(klines)
    res_items = _cluster(swings_h, grid=grid, n=n)
    sup_items = _cluster(swings_l, grid=grid, n=n)
    resistances = [p for p, s in res_items[:topk]]
    supports = [p for p, s in sup_items[:topk]]
    return {'supports': supports, 'resistances': resistances}


def merge_multi_tf(levels_list: List[Dict[str, List[float]]], grid: float = 50.0, topk: int = 8) -> Dict[str, List[float]]:
    from collections import defaultdict
    sup_bucket = defaultdict(float); res_bucket = defaultdict(float)
    for lv in levels_list:
        for p in lv.get('supports', []):
            key = round(p / grid) * grid
            sup_bucket[key] += 1.0
        for p in lv.get('resistances', []):
            key = round(p / grid) * grid
            res_bucket[key] += 1.0
    supports = [k for k, v in sorted(sup_bucket.items(), key=lambda x: x[1], reverse=True)[:topk]]
    resistances = [k for k, v in sorted(res_bucket.items(), key=lambda x: x[1], reverse=True)[:topk]]
    return {'supports': supports, 'resistances': resistances}

