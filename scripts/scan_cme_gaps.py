#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
扫描最近N周的“CME周末缺口”（近似法：以现货1小时K线模拟）并写入数据库与报告。

近似规则：
- 以UTC时间：周一00:00附近为开盘，周五22:00附近为收盘（容错±1h，取最接近者）。
- 缺口：周一开盘价 mon_open 与周五收盘价 fri_close 之间的价差区间。
- 回补：
  - 上跳缺口（mon_open > fri_close）：后续K线最低价 <= fri_close 视为回补；
  - 下跳缺口（mon_open < fri_close）：后续K线最高价 >= fri_close 视为回补。

输出：
- DuckDB 表 cme_gaps（若不存在则创建）
- outputs/cme_gaps_report.md
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from generate_btc_de_signals import get_btc_kline_gateio, get_btc_kline_bitget


def get_kl(tf='1h', hours=24*90):
    return get_btc_kline_gateio(tf, hours) or get_btc_kline_bitget(tf, hours)


def nearest_bar(kl, target_dt: datetime):
    # kl: list of dicts with 'timestamp'
    ts = int(target_dt.replace(tzinfo=timezone.utc).timestamp())
    best = None
    bestdiff = 10**9
    for k in kl:
        d = abs(int(k['timestamp']) - ts)
        if d < bestdiff:
            best = k
            bestdiff = d
    return best


def ensure_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cme_gaps (
          id INTEGER,
          gap_date VARCHAR,
          fri_close FLOAT,
          mon_open FLOAT,
          gap_dir VARCHAR,
          gap_low FLOAT,
          gap_high FLOAT,
          filled INTEGER,
          filled_time VARCHAR,
          days_to_fill FLOAT,
          created_at VARCHAR
        )
        """
    )


def upsert_gap(conn, rec):
    # naive upsert by gap_date
    row = conn.execute("SELECT id FROM cme_gaps WHERE gap_date=?", [rec['gap_date']]).fetchone()
    if row:
        gid = row[0]
        conn.execute(
            """
            UPDATE cme_gaps SET fri_close=?, mon_open=?, gap_dir=?, gap_low=?, gap_high=?,
                   filled=?, filled_time=?, days_to_fill=?, created_at=?
            WHERE id=?
            """,
            [rec['fri_close'], rec['mon_open'], rec['gap_dir'], rec['gap_low'], rec['gap_high'],
             rec['filled'], rec['filled_time'], rec['days_to_fill'], rec['created_at'], gid]
        )
    else:
        r = conn.execute("SELECT COALESCE(MAX(id),0)+1 FROM cme_gaps").fetchone()
        gid = int(r[0])
        conn.execute(
            """
            INSERT INTO cme_gaps (id,gap_date,fri_close,mon_open,gap_dir,gap_low,gap_high,filled,filled_time,days_to_fill,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            [gid, rec['gap_date'], rec['fri_close'], rec['mon_open'], rec['gap_dir'], rec['gap_low'], rec['gap_high'],
             rec['filled'], rec['filled_time'], rec['days_to_fill'], rec['created_at']]
        )


def scan_and_write(days_back=120):
    kl = get_kl('1h', 24*days_back)
    if not kl:
        print('no kline')
        return None
    db = TraderDBManager('de')
    con = db._get_connection()
    ensure_table(con)

    # 枚举每周：找到周五22:00与周一00:00附近bar
    utcnow = datetime.now(timezone.utc)
    start = utcnow - timedelta(days=days_back)
    # 对每个周一
    week = start
    out = []
    while week < utcnow:
        # 当周周一00:00与周五22:00（上一工作日）
        monday = (week - timedelta(days=week.weekday())).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
        friday = monday + timedelta(days=4)
        fri_close_dt = friday.replace(hour=22)
        mon_open_dt = monday + timedelta(days=7)  # 下周一
        # 只处理过去的完整周
        if mon_open_dt > utcnow:
            break
        k_fri = nearest_bar(kl, fri_close_dt)
        k_mon = nearest_bar(kl, mon_open_dt)
        if not k_fri or not k_mon:
            week += timedelta(days=7)
            continue
        fri_close = float(k_fri['close'])
        mon_open = float(k_mon['open'] if 'open' in k_mon else k_mon['close'])
        gap_dir = 'up' if mon_open > fri_close else 'down'
        low, high = (min(fri_close, mon_open), max(fri_close, mon_open))
        # 回补判定
        filled = 0
        filled_time = None
        # 后续所有bar
        mon_ts = int(k_mon['timestamp'])
        after = [k for k in kl if int(k['timestamp']) >= mon_ts]
        if gap_dir == 'up':
            for k in after:
                if float(k['low']) <= fri_close:
                    filled = 1
                    filled_time = datetime.fromtimestamp(int(k['timestamp']), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    break
        else:
            for k in after:
                if float(k['high']) >= fri_close:
                    filled = 1
                    filled_time = datetime.fromtimestamp(int(k['timestamp']), tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    break
        gap_date = datetime.fromtimestamp(int(k_mon['timestamp']), tz=timezone.utc).strftime('%Y-%m-%d')
        days_to_fill = None
        if filled and filled_time:
            t0 = datetime.fromtimestamp(int(k_mon['timestamp']), tz=timezone.utc)
            t1 = datetime.strptime(filled_time, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            days_to_fill = (t1 - t0).total_seconds() / 86400.0
        rec = {
            'gap_date': gap_date,
            'fri_close': fri_close,
            'mon_open': mon_open,
            'gap_dir': gap_dir,
            'gap_low': low,
            'gap_high': high,
            'filled': int(filled),
            'filled_time': filled_time,
            'days_to_fill': days_to_fill,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        upsert_gap(con, rec)
        out.append(rec)
        week += timedelta(days=7)
    con.commit()
    # 写报告
    lines = ['# CME 缺口追踪（近似）', '']
    lines.append(f'*生成时间*: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    lines.append('')
    for r in out[-12:][::-1]:
        status = '✅ 已回补' if r['filled'] else '⌛ 未回补'
        extra = f"，用时 {r['days_to_fill']:.1f} 天" if r['filled'] and r['days_to_fill'] is not None else ''
        lines.append(f"- 周期 {r['gap_date']} | {r['gap_dir']} gap | {r['gap_low']:,.0f}-{r['gap_high']:,.0f} | {status}{extra}")
    outdir = Path('outputs'); outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'cme_gaps_report.md').write_text('\n'.join(lines), encoding='utf-8')
    db.close()
    print('✓ CME缺口扫描完成，报告: outputs/cme_gaps_report.md')


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    scan_and_write()

