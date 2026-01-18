#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import sys, json
from datetime import datetime
from typing import List, Dict, Any

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager

app = FastAPI(title='Qingniao BE API', version='0.2')


# --- Sherlock endpoints ---
class Hit(BaseModel):
    computed_at: str
    symbol: str
    tf: str | None = None
    exchange: str | None = None
    score: float | None = None
    tags: str | None = None
    details: Dict[str, Any] | None = None


def _fetch_hits(min_score: float = 0, limit: int = 100) -> List[Dict[str, Any]]:
    db = TraderDBManager('sherlock')
    con = db._get_connection()
    rows = con.execute(
        """
        SELECT computed_at, symbol, tf, exchange, score, tags, details_json
        FROM sherlock_hits
        WHERE score >= ?
        ORDER BY computed_at DESC, score DESC
        LIMIT ?
        """ , [float(min_score), int(limit)]).fetchall()
    db.close()
    out = []
    for r in rows:
        try:
            details = json.loads(r[6]) if r[6] else {}
        except Exception:
            details = {}
        out.append({
            'computed_at': r[0], 'symbol': r[1], 'tf': r[2], 'exchange': r[3], 'score': r[4], 'tags': r[5], 'details': details
        })
    return out


@app.get('/api/hits')
def list_hits(min_score: float = Query(0), limit: int = Query(100), aux_filter: str = Query('none')):
    return JSONResponse(_fetch_hits(min_score=min_score, limit=limit))


@app.get('/api/hit/{symbol}')
def get_symbol(symbol: str):
    db = TraderDBManager('sherlock')
    con = db._get_connection()
    row = con.execute(
        """
        SELECT computed_at, symbol, tf, exchange, score, tags, details_json
        FROM sherlock_hits
        WHERE symbol = ?
        ORDER BY computed_at DESC, score DESC
        LIMIT 1
        """, [symbol]).fetchone()
    db.close()
    if not row:
        return JSONResponse({'error':'not found'}, status_code=404)
    try:
        details = json.loads(row[6]) if row[6] else {}
    except Exception:
        details = {}
    return JSONResponse({
        'computed_at': row[0], 'symbol': row[1], 'tf': row[2], 'exchange': row[3], 'score': row[4], 'tags': row[5], 'details': details
    })


@app.get('/api/config')
def get_config():
    db = TraderDBManager('sherlock')
    con = db._get_connection()
    row = con.execute("SELECT config_json FROM system_configs WHERE name='sherlock_scan' AND enabled=1 ORDER BY id DESC LIMIT 1").fetchone()
    db.close()
    cfg = {'interval':3600, 'exchange':'gate', 'limit':1000, 'topn':100}
    if row and row[0]:
        try:
            cfg.update(json.loads(row[0]) or {})
        except Exception:
            pass
    return JSONResponse(cfg)


@app.post('/api/config')
def set_config(cfg: Dict[str, Any]):
    db = TraderDBManager('sherlock')
    con = db._get_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    con.execute("INSERT INTO system_configs(name, version, config_json, enabled, created_at) VALUES(?,?,?,?,?)",
                ['sherlock_scan', 'v1', json.dumps(cfg, ensure_ascii=False), 1, now])
    db.close()
    return JSONResponse({'ok':True})


# --- De endpoints ---
def _fetch_de_latest_signals(limit_group: int = 1, system_name: str | None = None):
    db = TraderDBManager('de')
    con = db._get_connection()
    where = ''
    params = []
    if system_name:
        where = 'WHERE system_name=?'
        params.append(system_name)
    last = con.execute(f"SELECT MAX(signal_time) FROM trading_signals {where}", params).fetchone()[0]
    if not last:
        db.close(); return {'latest': None, 'items': []}
    rows = con.execute(
        f"""
        SELECT timeframe, signal_type, entry_price, stop_loss, take_profit_1, take_profit_2, entry_model, strength,
               entry_lower, entry_upper, risk_reward_ratio, system_name
        FROM trading_signals WHERE signal_time=? {'AND system_name=?' if system_name else ''} ORDER BY timeframe
        """, [last] + ([system_name] if system_name else [])).fetchall()
    db.close()
    items = []
    for r in rows:
        items.append({
            'timeframe': r[0], 'type': r[1], 'entry': r[2], 'stop': r[3], 'tp1': r[4], 'tp2': r[5],
            'model': r[6], 'strength': r[7], 'entry_lower': r[8], 'entry_upper': r[9], 'rr': r[10], 'system': r[11]
        })
    return {'latest': last, 'items': items}


@app.get('/api/de/status')
def de_status(system: str = Query('de', description='system_name in trading_signals (e.g., de, de_watcher)')):
    snap = _fetch_de_latest_signals(system_name=system)
    return JSONResponse(snap)


# --- Abu endpoints ---
def _fetch_abu_latest(topn: int = 10):
    db = TraderDBManager('abu')
    con = db._get_connection()
    last = con.execute("SELECT MAX(signal_time) FROM trading_signals").fetchone()[0]
    if not last:
        db.close(); return {'latest': None, 'items': []}
    rows = con.execute(
        """
        SELECT symbol, signal_type, entry_price, stop_loss, take_profit_1, take_profit_2,
               entry_model, strength, risk_reward_ratio, COALESCE(score,0), COALESCE(notes,'')
        FROM trading_signals
        WHERE signal_time=?
        ORDER BY COALESCE(score,0) DESC, id DESC
        LIMIT ?
        """, [last, int(topn)]).fetchall()
    db.close()
    items = []
    for r in rows:
        items.append({
            'symbol': r[0], 'type': r[1], 'entry': r[2], 'stop': r[3], 'tp1': r[4], 'tp2': r[5],
            'model': r[6], 'strength': r[7], 'rr': r[8], 'score': r[9], 'reason': r[10]
        })
    return {'latest': last, 'items': items}


@app.get('/api/abu/status')
def abu_status(top: int = Query(10)):
    return JSONResponse(_fetch_abu_latest(topn=top))


# Static mounts
try:
    ROOT = Path(__file__).resolve().parent.parent
    app.mount('/de', StaticFiles(directory=str(ROOT/'web'/'de'), html=True), name='de')
except Exception:
    pass

try:
    ROOT = Path(__file__).resolve().parent.parent
    app.mount('/abu', StaticFiles(directory=str(ROOT/'web'/'abu'), html=True), name='abu')
except Exception:
    pass


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8090)
