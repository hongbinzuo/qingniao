#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行Dream交易评估（对数据库中的交易进行价格评估）"""
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加src目录到路径
SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager
from dream_run_pipeline import (
    fetch_klines, first_hit, _find_symbols_lean, norm_ts
)
import json

def to_ms_utc(s: str) -> int:
    try:
        dt = datetime.strptime(s, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0

def fetch_klines_binance_range(sym: Optional[str], tf: str, start_ms: int, end_ms: int) -> List[Dict[str, Any]]:
    if not sym or not isinstance(sym, str):
        return []
    import requests
    tf_map = {'5m':'5m','15m':'15m','1h':'1h'}
    interval = tf_map.get(tf, '15m')
    symbol = sym.replace('/USDT','') + 'USDT'
    url = 'https://api.binance.com/api/v3/klines'
    params = {'symbol': symbol, 'interval': interval, 'startTime': start_ms, 'endTime': end_ms, 'limit': 1500}
    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code == 200:
            data = r.json()
            out=[]
            for k in data:
                out.append({'timestamp': int(k[0]), 'open': float(k[1]), 'high': float(k[2]), 'low': float(k[3]), 'close': float(k[4]), 'volume': float(k[5])})
            return out
    except Exception:
        return []
    return []

def price_eval(sym: str, side: str, entry: Optional[float], sl: Optional[float], tp: Optional[float], tss: str, tf: str = '15m', horizon_hours: int = 288) -> Dict[str, Any]:
    start_ms = to_ms_utc(tss)
    horizon_secs = horizon_hours * 3600
    end_ms = start_ms + horizon_secs * 1000
    kl = fetch_klines_binance_range(sym, tf, start_ms, end_ms) or fetch_klines(sym.replace('/USDT',''), tf, 1200, 'bitget')
    if not kl:
        return {'result':'none','hit_time':None,'mfe':None,'mae':None,'entry':entry}
    e = entry
    if e is None:
        cand = next((x for x in kl if int(x['timestamp']) >= start_ms), None)
        if cand:
            e = float(cand['close'])
    if tp is not None or sl is not None:
        hit = first_hit('long' if side=='long' else 'short', tp, sl, kl, start_ms, horizon_secs, conflict='conservative')
        return {'result': hit['result'], 'hit_time': hit['hit_time'], 'entry': e}
    highs = [float(x['high']) for x in kl]
    lows = [float(x['low']) for x in kl]
    if e is None:
        return {'result':'none','hit_time':None,'mfe':None,'mae':None,'entry':None}
    if side=='long':
        mfe = (max(highs) - e) / e
        mae = (e - min(lows)) / e
    else:
        mfe = (e - min(lows)) / e
        mae = (max(highs) - e) / e
    return {'result':'none','hit_time':None,'mfe':mfe,'mae':mae,'entry':e}

def main():
    print("📈 开始评估Dream交易记录...\n")
    
    db = TraderDBManager('dream')
    conn = db._get_connection()
    
    # 获取所有未评估或需要重新评估的交易
    trades = conn.execute('''
        SELECT id, timestamp, symbol, direction, entry_price, stop_loss, take_profit, text_content
        FROM trade_records 
        WHERE source = ? AND direction IS NOT NULL AND direction != ''
        ORDER BY timestamp
    ''', ('dream',)).fetchall()
    
    print(f"📊 找到 {len(trades)} 条交易记录需要评估\n")
    
    if not trades:
        print("✅ 没有需要评估的交易")
        db.close()
        return
    
    # 生成评估报告
    out_dir = Path('outputs') / 'dream'
    out_dir.mkdir(parents=True, exist_ok=True)
    ts_now = datetime.now().strftime('%Y%m%d_%H%M')
    rpt = out_dir / f'eval_{ts_now}.md'
    
    lines = [
        f"# Dream 交易评估报告 ({ts_now})",
        '',
        f"默认交易所: bitget | TF=15m | 窗口=288h | 策略=conservative",
        '',
        '| 时间 | 标的 | 方向 | 入场 | SL | TP | 结果 | 触发时间 |',
        '|---|---|---|---:|---:|---:|---|---|'
    ]
    
    evaluated = 0
    for row in trades:
        rid, tss, sym, side, entry, sl, tp, raw = row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7]
        
        if not sym:
            # 尝试从原文提取
            if raw:
                syms = _find_symbols_lean(raw)
                if syms:
                    sym = syms[0]
                    # 更新数据库
                    conn.execute('UPDATE trade_records SET symbol = ? WHERE id = ?', (sym, rid))
                    conn.commit()
        
        if not sym or not side:
            continue
        
        # 评估
        pe = price_eval(sym, side, entry, sl, tp, tss, tf='15m', horizon_hours=288)
        result = pe.get('result', 'none')
        h_ms = pe.get('hit_time')
        hit_time_str = datetime.fromtimestamp(h_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M') if h_ms else ''
        e = pe.get('entry') if isinstance(pe, dict) else entry
        
        lines.append(f"| {tss} | {sym} | {side or ''} | {e or ''} | {sl or ''} | {tp or ''} | {result or 'none'} | {hit_time_str} |")
        
        # 更新观点
        summary = {'trade_id': rid, 'symbol': sym, 'side': side, 'entry': e, 'sl': sl, 'tp': tp, 'result': result, 'hit_time': hit_time_str}
        db.add_viewpoint(content=json.dumps(summary, ensure_ascii=False), timestamp=tss, source='dream', category='eval', tags=['dream','eval'])
        
        evaluated += 1
        if evaluated % 100 == 0:
            print(f"   已评估 {evaluated}/{len(trades)} 条...")
    
    rpt.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n✅ 评估完成！")
    print(f"   - 评估交易数: {evaluated}")
    print(f"   - 报告路径: {rpt}")
    
    db.close()

if __name__ == '__main__':
    main()



