#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import sys, json
from datetime import datetime

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

def main():
    cfg = {
        'interval': 3600,
        'exchange': 'gate',
        'limit': 1000,
        'topn': 100,
        'min_score': 45,
        'fresh_bars': 1,   # 新鲜度阈值：1根1h bar以内视为最新
        'tvem_n': 200,     # TVEM EMA窗口
        'tvem_k': 0.2      # TVEM σ倍数
    }
    db = TraderDBManager('sherlock')
    con = db._get_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # 计算下一个ID
    try:
        row = con.execute('SELECT COALESCE(MAX(id),0)+1 FROM system_configs').fetchone()
        next_id = int(row[0]) if row and row[0] else 1
    except Exception:
        next_id = 1
    con.execute("INSERT INTO system_configs(id, name, version, config_json, enabled, created_at) VALUES(?,?,?,?,?,?)",
                [next_id, 'sherlock_scan', 'v1', json.dumps(cfg, ensure_ascii=False), 1, now])
    db.close()
    print('✓ sherlock_scan 配置已写入:', cfg)

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass
    main()
