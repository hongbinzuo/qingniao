#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量将 C:\\Users\\zuoho\\Pictures 下的 IMG_190*.* 截图占位入库（De. 交易员库）。

目的：
- 自动发现多种扩展名（jpg/jpeg/png/webp）的 190x 截图；
- 若数据库尚未记录该 screenshot_path，则按文件修改时间作为时间戳写入 trade_records；
- 暂不解析方向/杠杆/入场价等（避免误填），以占位形式入库，便于后续补全；
- 同步写入一条 viewpoint 便于检索。

运行：
  python scripts/ingest_screenshots_190x.py

说明：
- 仅写入缺失项，已存在的不会重复写入；
- 不访问网络，不做K线/标签分析（避免外网依赖）。
"""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
import sys

# 允许从 src/ 导入 TraderDBManager
SRC_DIR = Path(__file__).resolve().parent.parent / 'src'
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from db_manager_trader import TraderDBManager  # type: ignore


def list_target_images(pictures_dir: Path) -> list[Path]:
    patterns = [
        'IMG_190*.jpg', 'IMG_190*.jpeg', 'IMG_190*.png', 'IMG_190*.webp'
    ]
    files: list[Path] = []
    for pat in patterns:
        files.extend(sorted(pictures_dir.glob(pat)))
    # 去重并按名称排序
    seen = set()
    unique: list[Path] = []
    for f in files:
        if f.exists():
            key = f.resolve().as_posix().lower()
            if key not in seen:
                seen.add(key)
                unique.append(f)
    unique.sort(key=lambda p: p.name)
    return unique


def already_in_db(db: TraderDBManager, fullpath: str) -> bool:
    con = db._get_connection()
    try:
        row = con.execute(
            "SELECT COUNT(*) FROM trade_records WHERE screenshot_path = ?",
            [fullpath]
        ).fetchone()
        return bool(row and row[0] and int(row[0]) > 0)
    except Exception:
        return False


def main():
    # 目标目录（Windows 用户图片目录）
    pictures = Path(r"C:\Users\zuoho\Pictures")
    images = list_target_images(pictures)
    if not images:
        print('未找到 IMG_190*.* 图片')
        return

    db = TraderDBManager('de')
    inserted = []
    skipped = []

    for img in images:
        fullpath = str(img)
        if already_in_db(db, fullpath):
            skipped.append(img.name)
            continue
        # 时间戳采用文件修改时间
        try:
            ts = datetime.fromtimestamp(os.path.getmtime(fullpath))
        except Exception:
            ts = datetime.now()
        timestamp = ts.strftime('%Y-%m-%d %H:%M:%S')

        # 占位写入：仅基础字段 + 路径 + 备注（待补全）
        db.add_trade_record(
            timestamp=timestamp,
            symbol='BTC/USDT',
            direction=None,
            leverage=None,
            entry_price=None,
            exit_price=None,
            profit_pct=None,
            profit_usdt=None,
            strategy='screenshot_placeholder',
            screenshot_path=fullpath,
            text_content=f'截图占位：{img.name}（待补全方向/杠杆/入场等）',
            source='screenshot'
        )
        try:
            db.add_viewpoint(
                content=f'截图占位已入库：{img.name}（待补全）',
                timestamp=timestamp,
                source='screenshot',
                category='snapshot',
                tags=['trade','placeholder','image'],
                btc_price=None,
            )
        except Exception:
            pass
        inserted.append(img.name)

    db.close()

    print('已处理 IMG_190*.*')
    if inserted:
        print('新增入库:', ', '.join(inserted))
    if skipped:
        print('已存在跳过:', ', '.join(skipped))


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()

