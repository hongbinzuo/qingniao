#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dream 预处理流水线（批量对话 → 交易抽取 → 价格评估 → 报告）
默认：bitget，15m，窗口288h，冲突策略 conservative
"""
from __future__ import annotations
import sys, json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

SRC = Path(__file__).resolve().parent.parent / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from db_manager_trader import TraderDBManager


def load_json_any(p: Path) -> List[Dict[str, Any]]:
    """加载对话：支持两类
    1) Discord 导出结构：{..., "messages": [ {author:{name}, timestamp, content}, ... ]}
    2) 自定义简易结构：
       - 列表 [{timestamp, text}]
       - 或键值式 {timestamp: text}
    仅保留 Dream 本人消息（author.name='qimeng0104_49398'）
    """
    DREAM_AUTHOR = 'qimeng0104_49398'
    data = json.loads(p.read_text(encoding='utf-8'))
    # Discord 导出
    if isinstance(data, dict) and isinstance(data.get('messages'), list):
        out = []
        for m in data['messages']:
            name = (m.get('author') or {}).get('name', '')
            if name != DREAM_AUTHOR:
                continue
            ts = m.get('timestamp') or m.get('timestampEdited') or ''
            content = m.get('content')
            if isinstance(content, str):
                txt = content
            elif content is None:
                txt = ''
            else:
                # 非字符串内容序列化为文本
                try:
                    txt = json.dumps(content, ensure_ascii=False)
                except Exception:
                    txt = str(content)
            out.append({'timestamp': ts, 'text': txt})
        return out
    # 键值式 {ts: text}
    if isinstance(data, dict):
        out = []
        for k, v in data.items():
            txt = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            out.append({'timestamp': k, 'text': txt})
        return out
    # 列表 [{timestamp, text, ...}]
    if isinstance(data, list):
        return data
    return []


def norm_ts(ts: str) -> str:
    s = (ts or '').strip()
    if not s:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # ISO 格式（可能带Z或时区偏移），统一转为 UTC 文本
    try:
        if 'T' in s:
            iso = s.replace('Z', '+00:00') if s.endswith('Z') else s
            dt = datetime.fromisoformat(iso)
            dt_utc = dt.astimezone(timezone.utc)
            return dt_utc.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        pass
    # 仅 HH:MM 或 HH:MM:SS
    try:
        if len(s) == 5:
            return f"{datetime.now().strftime('%Y-%m-%d')} {s}:00"
        if len(s) == 8 and s.count(':') == 2:
            return f"{datetime.now().strftime('%Y-%m-%d')} {s}"
    except Exception:
        pass
    # 常见格式
    for fmt in ('%Y-%m-%d %H:%M:%S','%Y-%m-%d %H:%M','%Y/%m/%d %H:%M:%S','%Y/%m/%d %H:%M'):
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            continue
    return s


def extract_trades_from_text(text: str) -> List[Dict[str, Any]]:
    """极简抽取：symbol/side/entry/sl/tp，后续可替换更强解析器"""
    import re
    t = text or ''
    trades = []
    # 标的：大写字母 2-10 位；方向：多/空/long/short
    syms = re.findall(r'\b[A-Z]{2,10}\b', t)
    side = None
    if any(k in t for k in ['开空','做空','空','short','SHORT']):
        side = 'short'
    elif any(k in t for k in ['开多','做多','多','long','LONG']):
        side = 'long'
    # 价格提取（小数/整数）
    nums = re.findall(r'(?:\d+\.\d+|\d+)', t)
    # 粗略映射：出现顺序 entry, dca?, sl, tp（若包含关键词则优先）
    def pick(label_kw: List[str]) -> Optional[float]:
        for kw in label_kw:
            m = re.search(kw + r'.{0,8}?(\d+\.\d+|\d+)', t, re.IGNORECASE)
            if m:
                try:
                    return float(m.group(1))
                except Exception:
                    pass
        return None
    entry = pick(['入场','进场','成本','entry','avg'])
    sl    = pick(['止损','SL','sl'])
    tp    = pick(['止盈','TP','tp'])
    # 构造（若 price 缺失，后续评估再补）
    for s in syms[:1]:  # 每条只取第一个标的，后续可扩
        trades.append({'symbol': f'{s}/USDT', 'side': side, 'entry': entry, 'sl': sl, 'tp': tp})
    return trades


def _find_symbols_lean(text: str) -> List[str]:
    import re
    t = (text or '')
    out = []
    # explicit pair like ABC/USDT
    for m in re.finditer(r'\b([A-Za-z0-9][A-Za-z0-9._\-]{1,14})\s*/\s*(USDT|USDC|USD)\b', t, flags=re.IGNORECASE):
        out.append(m.group(1).upper() + '/USDT')
    # bare symbol fallback (strict - uppercase letters/digits 2-10 len)
    if not out:
        for m in re.finditer(r'\b([A-Z0-9]{2,10})\b', t):
            base = m.group(1)
            if base in ('USDT','USDC','USD','TP','SL','MA','EMA','MACD','RSI'):
                continue
            if base.isdigit():
                continue
            out.append(base + '/USDT')
    # dedup keep order
    seen=set(); res=[]
    for s in out:
        if s not in seen:
            seen.add(s); res.append(s)
    return res


def _pick_num_after_keywords(text: str, kws: List[str], window: int = 24) -> Optional[float]:
    import re
    t = text or ''
    for kw in kws:
        # accept ascii ':' and chinese '：', optional spaces/equal
        m = re.search(fr'{re.escape(kw)}[ ：:=]?\s{{0,{window}}}?(\d+\.\d+|\d+)', t, flags=re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except Exception:
                continue
    return None


def build_events(all_msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """从对话构建结果事件（止盈/止损），若消息未显式标的，则向上回溯寻找最近标的"""
    # Pre-order messages by time
    def to_dt_iso(ts: str) -> datetime:
        try:
            iso = ts.replace('Z','+00:00') if ts and ts.endswith('Z') else ts
            return datetime.fromisoformat(iso).astimezone(timezone.utc)
        except Exception:
            try:
                return datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            except Exception:
                return datetime.now(timezone.utc)
    msgs = sorted(all_msgs, key=lambda x: to_dt_iso(x.get('timestamp','')))
    events: List[Dict[str, Any]] = []
    ctx_symbol: Optional[str] = None
    ctx_time: Optional[datetime] = None
    for i, m in enumerate(msgs):
        txt = m.get('text','')
        ts = m.get('timestamp','')
        syms = _find_symbols_lean(txt)
        if syms:
            ctx_symbol = syms[0]
            ctx_time = to_dt_iso(ts)
        # detect event words
        has_tp = any(k in txt for k in ['止盈','tp','TP','到目标','清仓','平仓','止盈了'])
        has_sl = any(k in txt for k in ['止损','sl','SL','打止损','爆仓','止损了'])
        if not (has_tp or has_sl):
            continue
        # try price near keywords
        ev_price = None
        if has_tp:
            ev_price = _pick_num_after_keywords(txt, ['止盈','TP','tp','目标'])
        if ev_price is None and has_sl:
            ev_price = _pick_num_after_keywords(txt, ['止损','SL','sl'])
        # resolve symbol: prefer this line, else look back up to 60min
        symbol = syms[0] if syms else None
        if symbol is None:
            # search back up to 30 messages or 60min
            base_dt = to_dt_iso(ts)
            for j in range(i-1, max(-1, i-30), -1):
                mj = msgs[j]
                sj = _find_symbols_lean(mj.get('text',''))
                if not sj:
                    continue
                dtj = to_dt_iso(mj.get('timestamp',''))
                if abs((base_dt - dtj).total_seconds()) <= 3600:
                    symbol = sj[0]
                    break
        if symbol is None:
            continue
        events.append({'timestamp': norm_ts(ts), 'symbol': symbol, 'kind': 'tp' if has_tp else 'sl', 'price': ev_price, 'text': txt})
    return events


def fetch_klines(symbol: str, tf: str, limit: int, exchange: str) -> List[Dict[str, Any]]:
    # 复用 generate_comprehensive_trading_plans 的 get_kline_*
    try:
        from generate_comprehensive_trading_plans import get_kline_bitget as _get_k_bitget
        from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
        from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
    except Exception:
        _get_k_bitget = _get_k_gate = _get_k_bin = None
    providers = []
    if exchange == 'bitget':
        providers = [_get_k_bitget, _get_k_gate, _get_k_bin]
    elif exchange == 'gate':
        providers = [_get_k_gate, _get_k_bitget, _get_k_bin]
    else:
        providers = [_get_k_bitget, _get_k_gate, _get_k_bin]
    for fn in providers:
        if not fn:
            continue
        try:
            kl = fn(symbol=symbol.replace('/USDT',''), timeframe=tf, limit=limit)
            if kl:
                return kl
        except Exception:
            continue
    return []


def first_hit(side: str, tp: Optional[float], sl: Optional[float], kl: List[Dict[str, Any]], start_ts: int,
              horizon_secs: int, conflict: str = 'conservative') -> Dict[str, Any]:
    """返回 {'result': 'tp'|'sl'|'none', 'hit_time':ts or None} """
    res = {'result': 'none', 'hit_time': None, 'hit_price': None}
    if not kl:
        return res
    # 只看 start_ts 之后 horizon 窗内
    end_ts = start_ts + horizon_secs * 1000
    for k in kl:
        ts = int(k['timestamp'])
        if ts < start_ts or ts > end_ts:
            continue
        hi = float(k['high']); lo = float(k['low'])
        # 同根冲突：conservative 优先视为止损
        if side == 'long':
            tp_hit = (tp is not None and hi >= tp)
            sl_hit = (sl is not None and lo <= sl)
        else:
            tp_hit = (tp is not None and lo <= tp)
            sl_hit = (sl is not None and hi >= sl)
        if tp_hit and sl_hit:
            res['result'] = 'sl' if conflict=='conservative' else 'tp'
            res['hit_time'] = ts
            res['hit_price'] = sl if conflict=='conservative' else tp
            return res
        if tp_hit:
            res['result'] = 'tp'; res['hit_time'] = ts; res['hit_price'] = tp; return res
        if sl_hit:
            res['result'] = 'sl'; res['hit_time'] = ts; res['hit_price'] = sl; return res
    return res


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Dream 预处理流水线')
    ap.add_argument('--files', required=True, help='逗号分隔的 JSON 文件列表')
    ap.add_argument('--exchange', default='bitget', choices=['bitget','gate','binance'])
    ap.add_argument('--tf', default='15m', choices=['5m','15m','1h'])
    ap.add_argument('--horizon', default='288h', help='评估窗口，示例：288h')
    ap.add_argument('--tz', default='Asia/Shanghai')
    ap.add_argument('--conflict', default='conservative', choices=['conservative','optimistic'])
    args = ap.parse_args()

    # 解析 horizon
    try:
        if args.horizon.endswith('h'):
            horizon_hours = int(args.horizon[:-1])
        else:
            horizon_hours = int(args.horizon)
    except Exception:
        horizon_hours = 288
    horizon_secs = horizon_hours * 3600

    files = [Path(x.strip()) for x in args.files.split(',') if x.strip()]
    all_msgs = []
    for f in files:
        if not f.exists():
            print(f"! 文件不存在: {f}", file=sys.stderr); continue
        all_msgs.extend(load_json_any(f))

    # 1) 导入对话
    db = TraderDBManager('dream')
    conv_ids = []
    for m in all_msgs:
        ts = norm_ts(m.get('timestamp',''))
        txt = m.get('text','')
        cid = db.add_conversation(timestamp=ts, user_message=None, trader_message=txt, source='dream', btc_price=None, extracted_content=None)
        conv_ids.append(cid)

    # 2) 抽取交易（简单规则，按需后续增强）
    trade_rows = []
    for m in all_msgs:
        ts = norm_ts(m.get('timestamp',''))
        txt = m.get('text','')
        for t in extract_trades_from_text(txt):
            trade_rows.append({**t, 'timestamp': ts, 'raw': txt})

    # 写入交易记录并记住生成的ID，便于后续评估留痕
    inserted: List[Dict[str, Any]] = []
    for tr in trade_rows:
        rid = db.add_trade_record(
            timestamp=tr['timestamp'], symbol=tr['symbol'], direction=tr.get('side'),
            entry_price=tr.get('entry'), exit_price=None, profit_pct=None, profit_usdt=None,
            strategy='dream_extract', screenshot_path=None, text_content=tr.get('raw'), source='dream')
        tr2 = dict(tr)
        tr2['id'] = rid
        inserted.append(tr2)

    # 事件索引（止盈/止损）
    events = build_events(all_msgs)
    events_by_symbol: Dict[str, List[Dict[str, Any]]] = {}
    for ev in events:
        events_by_symbol.setdefault(ev['symbol'], []).append(ev)
    for lst in events_by_symbol.values():
        lst.sort(key=lambda x: x['timestamp'])

    # 3) 评估（逐笔，使用刚抽取的 inserted 列表）
    out_dir = Path('outputs') / 'dream'
    out_dir.mkdir(parents=True, exist_ok=True)
    ts_now = datetime.now().strftime('%Y%m%d_%H%M')
    rpt = out_dir / f'eval_{ts_now}.md'
    lines = [f"# Dream 交易评估报告 ({ts_now})", '', f"默认交易所: {args.exchange} | TF={args.tf} | 窗口={horizon_hours}h | 策略={args.conflict}", '', '| 时间 | 标的 | 方向 | 入场 | SL | TP | 结果 | 触发时间 |', '|---|---|---|---:|---:|---:|---|---|']

    def to_ms_utc(s: str) -> int:
        try:
            dt = datetime.strptime(s, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except Exception:
            return 0

    def fetch_klines_binance_range(sym: str, tf: str, start_ms: int, end_ms: int) -> List[Dict[str, Any]]:
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

    def price_eval(sym: str, side: str, entry: Optional[float], sl: Optional[float], tp: Optional[float], tss: str) -> Dict[str, Any]:
        start_ms = to_ms_utc(tss)
        end_ms = start_ms + horizon_secs * 1000
        kl = fetch_klines_binance_range(sym, args.tf, start_ms, end_ms) or fetch_klines(sym.replace('/USDT',''), args.tf, 1200, args.exchange)
        if not kl:
            return {'result':'none','hit_time':None,'mfe':None,'mae':None,'entry':entry}
        e = entry
        if e is None:
            # use first close at/after start
            cand = next((x for x in kl if int(x['timestamp']) >= start_ms), None)
            if cand:
                e = float(cand['close'])
        # compute hits
        if tp is not None or sl is not None:
            hit = first_hit('long' if side=='long' else 'short', tp, sl, kl, start_ms, horizon_secs, conflict=args.conflict)
            return {'result': hit['result'], 'hit_time': hit['hit_time'], 'entry': e}
        # else compute mfe/mae
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

    for tr in inserted:
        rid = tr['id']
        tss = tr['timestamp']
        sym = tr['symbol']
        side = tr.get('side') or ''
        entry = tr.get('entry')
        sl = tr.get('sl')
        tp = tr.get('tp')
        # 先用对话事件判定
        ev_hit_time = ''
        ev_result = None
        evs = events_by_symbol.get(sym, [])
        for ev in evs:
            # 事件时间在交易之后
            if ev['timestamp'] >= tss:
                ev_result = ev['kind']
                ev_hit_time = ev['timestamp']
                break

        hit_time_str = ''
        if ev_result:
            result = ev_result
            hit_time_str = ev_hit_time
            pe = {'entry': entry}
        else:
            pe = price_eval(sym, side, entry, sl, tp, tss)
            result = pe.get('result')
            h_ms = pe.get('hit_time')
            hit_time_str = datetime.fromtimestamp(h_ms/1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M') if h_ms else ''
        e = pe.get('entry') if isinstance(pe, dict) else entry
        # 只输出含方向的记录，减少噪声
        if not side:
            continue
        lines.append(f"| {tss} | {sym} | {side or ''} | {e or ''} | {sl or ''} | {tp or ''} | {result or 'none'} | {hit_time_str} |")

        # 评估观点入库（hit_time 使用字符串，统一展示友好）
        summary = {'trade_id': rid, 'symbol': sym, 'side': side, 'entry': e, 'sl': sl, 'tp': tp, 'result': result, 'hit_time': hit_time_str}
        db.add_viewpoint(content=json.dumps(summary, ensure_ascii=False), timestamp=tss, source='dream', category='eval', tags=['dream','eval'])

    db.close()
    rpt.write_text('\n'.join(lines), encoding='utf-8')
    print('✓ 评估完成，报告已生成:', rpt)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
