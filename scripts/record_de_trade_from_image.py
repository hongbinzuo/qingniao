#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从一张已知截图信息录入 De. 的最近一笔交易，并生成学习/归档摘要。

用法：直接运行（脚本内置本次解析结果），或改参数后再运行。
注意：Windows 下若 Falcon 正在占用 DuckDB 文件，可能需要先停止再录入。
"""
import sys
from pathlib import Path
from datetime import datetime

SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_manager_trader import TraderDBManager


def main():
    # 解析自图片 C:\\Users\\zuoho\\Pictures\\IMG_1889.jpg
    timestamp = '2026-01-01 00:49:00'  # UTC+8（截图标注）
    symbol = 'BTC/USDT'
    direction = 'short'
    leverage = 10
    entry_price = 88781.6
    current_price = 87492.1
    # 近似收益（做空）：(entry - current)/entry * 100 * leverage
    pnl_pct_lev = (entry_price - current_price) / entry_price * 100 * leverage
    display_pct = 14.73  # 截图显示
    screenshot = r"C:\\Users\\zuoho\\Pictures\\IMG_1889.jpg"

    db = TraderDBManager('de')
    trade_id = db.add_trade_record(
        timestamp=timestamp,
        symbol=symbol,
        direction=direction,
        leverage=leverage,
        entry_price=entry_price,
        exit_price=None,
        profit_pct=display_pct,
        profit_usdt=None,
        strategy='real_trade',
        screenshot_path=screenshot,
        text_content=f'来自截图录入；当前价 {current_price:.1f}，杠杆 {leverage}x；显示收益 {display_pct:.2f}%；理论收益≈{pnl_pct_lev:.2f}%。',
        source='screenshot'
    )

    # 归档到观点（便于检索）
    vp = (
        f"De.实盘快照 | {symbol} {direction.upper()} {leverage}x | 开仓 {entry_price:.1f} | "
        f"当前 {current_price:.1f} | 收益 {display_pct:.2f}% (理:{pnl_pct_lev:.2f}%) | 截图: {screenshot}"
    )
    db.add_viewpoint(
        content=vp,
        timestamp=timestamp,
        source='screenshot',
        category='learning',
        tags=['trade','snapshot','de'],
        btc_price=current_price,
        related_trade_id=trade_id,
    )

    # 生成轻量学习摘要文件（供后续 ML 使用）
    outdir = Path('trading_signals') / '.learning_reports'
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / f'learn_trade_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
    out.write_text(
        "\n".join([
            '# 学习条目 - 实盘快照',
            '',
            f'**时间**: {timestamp}',
            f'**标的**: {symbol}',
            f'**方向**: {direction.upper()}  **杠杆**: {leverage}x',
            f'**开仓均价**: ${entry_price:,.1f}',
            f'**当前价格**: ${current_price:,.1f}',
            f'**收益率(显示)**: {display_pct:.2f}%',
            f'**收益率(理论)**: {pnl_pct_lev:.2f}%',
            f'**截图**: {screenshot}',
            '',
            '建议: 作为“实盘样本”纳入后续训练集，关注做空回撤期的止盈分配与移动止损策略。'
        ]),
        encoding='utf-8'
    )

    db.close()
    print(f'✓ 已录入交易(ID={trade_id})，并写入学习摘要: {out}')


if __name__ == '__main__':
    # Windows 控制台 UTF-8
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

