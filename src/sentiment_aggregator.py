#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场情绪聚合（开放接口）
数据源（免密钥/公开）：
- Fear & Greed Index: https://api.alternative.me/fng/
- Coinbase Premium（近似）：Coinbase BTC-USD vs Binance BTCUSDT 现价差
- Binance 合约全网多空账户比（可能随接口变动）
  https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=5m&limit=12
- Funding Rate（近一笔）：https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=1

输出：情绪分数 -100~+100，及各项子指标
"""
from __future__ import annotations
import requests
from typing import Dict, Any


def _safe_get(url, params=None, timeout=10):
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def fear_greed() -> Dict[str, Any]:
    data = _safe_get('https://api.alternative.me/fng/', {'limit': 2})
    if data and data.get('data'):
        v = int(data['data'][0]['value'])  # 0-100
        return {'fear_greed': v}
    return {'fear_greed': None}


def coinbase_premium() -> Dict[str, Any]:
    cb = _safe_get('https://api.exchange.coinbase.com/products/BTC-USD/ticker')
    bn = _safe_get('https://api.binance.com/api/v3/ticker/price', {'symbol': 'BTCUSDT'})
    try:
        cbp = float(cb['price']) if 'price' in cb else float(cb['last'])
        bnp = float(bn['price'])
        prem = (cbp - bnp) / bnp * 100
        return {'coinbase_premium_pct': prem}
    except Exception:
        return {'coinbase_premium_pct': None}


def binance_long_short_ratio() -> Dict[str, Any]:
    # 近一小时（12*5m）平均
    js = _safe_get('https://fapi.binance.com/futures/data/globalLongShortAccountRatio',
                   {'symbol': 'BTCUSDT', 'period': '5m', 'limit': 12})
    if isinstance(js, list) and js:
        try:
            vals = [float(x['longShortRatio']) for x in js]
            avg = sum(vals) / len(vals)
            return {'binance_ls_ratio': avg}
        except Exception:
            pass
    return {'binance_ls_ratio': None}


def funding_rate() -> Dict[str, Any]:
    js = _safe_get('https://fapi.binance.com/fapi/v1/fundingRate', {'symbol': 'BTCUSDT', 'limit': 1})
    try:
        if isinstance(js, list) and js:
            fr = float(js[0]['fundingRate']) * 100
            return {'funding_rate_pct': fr}
    except Exception:
        pass
    return {'funding_rate_pct': None}


def aggregate_sentiment() -> Dict[str, Any]:
    d = {}
    d.update(fear_greed())
    d.update(coinbase_premium())
    d.update(binance_long_short_ratio())
    d.update(funding_rate())
    # 评分：简单线性映射
    score = 0; cnt = 0
    v = d.get('fear_greed');
    if isinstance(v, (int, float)):
        score += (v - 50)  # 0-100 -> -50~+50
        cnt += 1
    p = d.get('coinbase_premium_pct')
    if isinstance(p, (int, float)):
        score += p  # 正溢价偏多；负溢价偏空
        cnt += 1
    ls = d.get('binance_ls_ratio')
    if isinstance(ls, (int, float)):
        score += (ls - 1.0) * 50  # 1为中性
        cnt += 1
    fr = d.get('funding_rate_pct')
    if isinstance(fr, (int, float)):
        score += -fr * 5  # 高正资金费偏拥挤
        cnt += 1
    if cnt:
        score = max(-100, min(100, score))
    d['sentiment_score'] = score
    return d

