#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sherlock 扫描守护进程
- 周期性运行 sherlock_scan_strong_coins.py --limit 1000 --topn 100 --write-db --exchange <cfg>
- 间隔、交易所、TopN 从 system_configs('sherlock_scan') 读取，缺省：interval=3600, exchange='gate', limit=1000, topn=100
- 透传可选参数：min_score、fresh_bars、tvem_n、tvem_k（若配置中存在）
- 状态写入 outputs/sherlock/.state.json；记录 last_success_at、fail_count、next_run_eta
- 醒来补跑：根据 last_success_at 与 interval 判断是否应立即执行一次，避免睡眠空窗
"""
from __future__ import annotations
import sys, json, time, subprocess
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

STATE = Path('outputs') / 'sherlock' / '.state.json'


def load_cfg():
    cfg = {'interval': 3600, 'exchange': 'gate', 'limit': 1000, 'topn': 100}
    try:
        db = TraderDBManager('sherlock')
        con = db._get_connection()
        row = con.execute("SELECT config_json FROM system_configs WHERE name='sherlock_scan' AND enabled=1 ORDER BY id DESC LIMIT 1").fetchone()
        if row and row[0]:
            import json as _j
            c = _j.loads(row[0])
            cfg.update(c or {})
        db.close()
    except Exception:
        pass
    return cfg


def read_state() -> dict:
    try:
        if STATE.exists():
            return json.loads(STATE.read_text(encoding='utf-8') or '{}')
    except Exception:
        pass
    return {}


def write_state(d: dict):
    try:
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass


def run_once(cfg, prev_state: dict | None = None, next_eta: str | None = None):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cmd = [sys.executable or 'python', str(ROOT / 'scripts' / 'sherlock_scan_strong_coins.py'),
           '--limit', str(cfg.get('limit',1000)),
           '--topn', str(cfg.get('topn',100)),
           '--exchange', str(cfg.get('exchange','gate')),
           '--write-db']
    # 透传 min_score 与 fresh_bars（如配置中存在）
    if 'min_score' in cfg:
        cmd.extend(['--min-score', str(cfg.get('min_score'))])
    if 'fresh_bars' in cfg and cfg.get('fresh_bars') is not None:
        cmd.extend(['--fresh-bars', str(cfg.get('fresh_bars'))])
    if 'tvem_n' in cfg:
        cmd.extend(['--tvem-n', str(cfg.get('tvem_n'))])
    if 'tvem_k' in cfg:
        cmd.extend(['--tvem-k', str(cfg.get('tvem_k'))])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800, cwd=str(ROOT))
        ok = (r.returncode == 0)
        out = (r.stdout or '')
        err = (r.stderr or '')
        ps = prev_state or {}
        last_success_at = ts if ok else ps.get('last_success_at')
        fail_count = 0 if ok else int(ps.get('fail_count', 0)) + 1
        st = {'last_run': ts, 'ok': ok, 'stdout': out[-400:], 'stderr': err[-400:], 'cmd': ' '.join(cmd),
              'last_success_at': last_success_at, 'fail_count': fail_count}
        if next_eta:
            st['next_run_eta'] = next_eta
        write_state(st)
    except Exception as e:
        ps = prev_state or {}
        fail_count = int(ps.get('fail_count', 0)) + 1
        st = {'last_run': ts, 'ok': False, 'error': str(e), 'fail_count': fail_count, 'last_success_at': ps.get('last_success_at')}
        if next_eta:
            st['next_run_eta'] = next_eta
        write_state(st)


def main():
    while True:
        cfg = load_cfg()  # 每轮重载配置
        interval = max(30, int(cfg.get('interval', 3600)))
        ps = read_state()
        now = datetime.now()
        # 计算下一次计划运行时间（用于写入状态展示）
        next_eta = (now + timedelta(seconds=interval)).strftime('%Y-%m-%d %H:%M:%S')

        # 醒来补跑：若上次成功时间缺失或已超过间隔，则立即跑一轮
        should_run = True
        try:
            lss = ps.get('last_success_at')
            if lss:
                last_ok = datetime.strptime(lss, '%Y-%m-%d %H:%M:%S')
                delta = (now - last_ok).total_seconds()
                if delta < interval:
                    # 未到窗口，短睡眠
                    time.sleep(max(5, int(interval - delta)))
                    should_run = False
        except Exception:
            pass

        if should_run:
            run_once(cfg, prev_state=ps, next_eta=next_eta)
            # 正常节拍休眠
            time.sleep(interval)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
