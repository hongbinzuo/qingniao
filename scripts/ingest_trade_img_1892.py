#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
录入 IMG_1892.jpg 截图对应的最新交易，并进行技术归类（稳健版）。

数据来源：截图文本（手动录入数值），技术归类：在线获取15m/1h K线。

注意：
- 在 Windows 下执行，便于访问 DuckDB 与图片路径。
- 需要外网以从 Gate.io/Bitget 获取K线。
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime

# import from src/
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from generate_btc_de_signals import (
    get_btc_kline_gateio,
    get_btc_kline_bitget,
    analyze_timeframe,
)


def near(x: float, y: float, pct: float = 0.2) -> bool:
    """x 是否在 y 附近，容差为 pct%（默认0.2%）。"""
    try:
        return abs(x - y) / y * 100 < pct
    except Exception:
        return False


def label_trade(entry: float, direction: str, current_price: float) -> list[str]:
    """基于 15m/1h 做轻量技术归类。"""
    labels: list[str] = []
    # 拉取K线（优先 Gate，兜底 Bitget）
    k15 = get_btc_kline_gateio('15m', 200) or get_btc_kline_bitget('15m', 200)
    k1h = get_btc_kline_gateio('1h', 200) or get_btc_kline_bitget('1h', 200)
    for kl, tf in ((k15, '15m'), (k1h, '1h')):
        if not kl:
            continue
        a = analyze_timeframe(kl, '15分钟' if tf == '15m' else '1小时', current_price)
        if not a:
            continue
        # OTE（618-786）
        oa = a.get('ote_analysis') or {}
        f618 = oa.get('fib_618')
        f786 = oa.get('fib_786')
        if f618 and f786:
            lo, hi = (min(f618, f786), max(f618, f786))
            if entry >= lo and entry <= hi:
                if 'OTE' not in labels:
                    labels.append('OTE')
            elif near(entry, f618) or near(entry, f786):
                if 'OTE邻近' not in labels:
                    labels.append('OTE邻近')
        # Vegas
        e144, e169 = a.get('ema_144'), a.get('ema_169')
        if e144 and near(entry, e144) or e169 and near(entry, e169):
            if 'Vegas邻近' not in labels:
                labels.append('Vegas邻近')
        # VWAP
        vwap = a.get('vwap')
        if vwap and near(entry, vwap):
            if 'VWAP邻近' not in labels:
                labels.append('VWAP邻近')
        # SR（支持/阻力邻近）
        sr = a.get('support_resistance') or {}
        if direction == 'long':
            arr = sr.get('support') or []
        else:
            arr = sr.get('resistance') or []
        for p in arr[:5]:
            try:
                if abs(entry - float(p)) / entry * 100 < 0.2:
                    if 'SR邻近' not in labels:
                        labels.append('SR邻近')
                    break
            except Exception:
                pass
    return labels


def main():
    # 从截图读取到的数值（IMG_1892）
    ts = '2026-01-02 11:30:00'  # 截图显示 UTC+8 11:30
    symbol = 'BTC/USDT'
    direction = 'long'
    leverage = 15
    entry_price = 88193.9
    current_price = 88832.0
    profit_pct = 10.94
    shot = r"C:\\Users\\zuoho\\Pictures\\IMG_1892.jpg"

    db = TraderDBManager('de')
    tid = db.add_trade_record(
        timestamp=ts,
        symbol=symbol,
        direction=direction,
        leverage=leverage,
        entry_price=entry_price,
        exit_price=None,
        profit_pct=profit_pct,
        profit_usdt=None,
        strategy='real_trade',
        screenshot_path=shot,
        text_content=f'截图录入 IMG_1892；当前价 {current_price:.1f}；显示收益 {profit_pct:.2f}%（{leverage}x）。',
        source='screenshot'
    )

    # 技术归类
    try:
        labels = label_trade(entry_price, direction, current_price)
    except Exception:
        labels = []

    # 写 viewpoint & 回填标签
    if labels:
        db.add_viewpoint(
            content=(
                f"De.交易技术归因 | trade#{tid} | {direction.upper()} | entry ${entry_price:,.1f} | "
                f"技术: {', '.join(labels)}"
            ),
            timestamp=ts,
            source='tech-label',
            category='label',
            tags=['tech','label'],
            related_trade_id=tid,
            btc_price=current_price,
        )
        try:
            con = db._get_connection()
            import json as _j
            con.execute("UPDATE trade_records SET tech_labels=? WHERE id=?", [_j.dumps(labels, ensure_ascii=False), tid])
            con.commit()
        except Exception:
            pass

    db.close()
    print(f"✓ 已录入 trade#{tid}，labels={labels}")


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

