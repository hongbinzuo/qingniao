#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
根据图片 IMG_1900.jpg 录入 De. 的一笔实盘（OKX 合约截图）。
图片时间作为分享时间；入场/标记价来自截图文本。
"""
from pathlib import Path
from datetime import datetime
import os, sys

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager


def main():
    img = Path(r"C:\Users\zuoho\Pictures\IMG_1900.jpg")
    # 来自截图识别
    symbol = 'BTC/USDT'
    direction = 'long'
    leverage = 15
    entry_price = 87854.3
    mark_price = 90056.5
    # 以文件修改时间作为分享时间
    try:
        ts = datetime.fromtimestamp(os.path.getmtime(img))
    except Exception:
        ts = datetime.now()
    timestamp = ts.strftime('%Y-%m-%d %H:%M:%S')

    # 近似收益（按杠杆）：(mark-entry)/entry * 100 * leverage
    pnl_pct_lev = (mark_price - entry_price) / entry_price * 100 * leverage

    db = TraderDBManager('de')
    trade_id = db.add_trade_record(
        timestamp=timestamp,
        symbol=symbol,
        direction=direction,
        leverage=leverage,
        entry_price=entry_price,
        exit_price=None,
        profit_pct=round(pnl_pct_lev, 2),
        profit_usdt=None,
        strategy='image_okx_screenshot',
        screenshot_path=str(img),
        text_content=f'OKX截图录入；标记价 {mark_price:.1f}；杠杆 {leverage}x；理论收益≈{pnl_pct_lev:.2f}%（仅作为分享时点估算）',
        source='screenshot'
    )
    db.add_viewpoint(
        content=f'De.实盘（截图） | BTCUSDT 合约 LONG {leverage}x | 开仓均价 {entry_price:.1f} | 标记价 {mark_price:.1f} | 理论收益 {pnl_pct_lev:.2f}%\n截图: {img}',
        timestamp=timestamp,
        source='screenshot',
        category='learning',
        tags=['trade','snapshot','de'],
        related_trade_id=trade_id
    )
    db.close()
    print(f'✓ 已录入 trade#{trade_id} 来自 {img.name}')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

