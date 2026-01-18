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
from detailed_logger import get_detailed_logger


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
    """增强抽取：
    - 支持结构化卡片：【币种】/【方向】/【杠杆】/【开仓价】/【止盈价】/【止损价】
    - 中文/英文关键词：开空/做空/开多/做多/short/long；入场/进场/成本/止损/止盈/目标
    - 仅返回本条消息解析出的 0~1 笔（避免重复），上下文关联由上层事件处理
    """
    import re
    t = (text or '').strip()
    if not t:
        return []

    def pick_num(kws: List[str], window: int = 24) -> Optional[float]:
        for kw in kws:
            m = re.search(fr'{re.escape(kw)}[ ：:=]?\s{{0,{window}}}?(\d+\.\d+|\d+)', t, flags=re.IGNORECASE)
            if m:
                try:
                    return float(m.group(1))
                except Exception:
                    continue
        return None

    # 1) 结构化卡片优先
    m_sym = re.search(r'【\s*币种\s*】[ ：:]\s*([A-Za-z0-9._\-]{2,15})', t)
    m_dir = re.search(r'【\s*方向\s*】[ ：:]\s*([^\n]+)', t)
    m_lev = re.search(r'【\s*杠杆\s*】[ ：:]\s*(\d+)\s*(x|X|倍)', t)
    sym = None; side = None; lev = None
    if m_sym:
        base = m_sym.group(1).upper()
        if 2 <= len(base) <= 15 and not base.isdigit():
            sym = base + '/USDT'
    if m_dir:
        dir_txt = m_dir.group(1)
        if any(k in dir_txt for k in ['开空','做空','空','short','SHORT','反手空']):
            side = 'short'
        elif any(k in dir_txt for k in ['开多','做多','多','long','LONG','反手多']):
            side = 'long'
    if m_lev:
        try: lev = int(m_lev.group(1))
        except: lev = None
    entry = pick_num(['【开仓价】','【开仓】','入场','进场','成本','entry','avg'])
    sl    = pick_num(['【止损价】','止损','SL','sl'])
    tp    = pick_num(['【止盈价】','止盈','TP','tp','目标'])
    if sym or side or entry or sl or tp or lev:
        return [{'symbol': sym or None, 'side': side, 'entry': entry, 'sl': sl, 'tp': tp, 'leverage': lev}]

    # 2) 非结构化回退（英文/中文关键词 + 显式 ABC/USDT 或裸大写符号）
    syms = []
    for m in re.finditer(r'\b([A-Za-z0-9][A-Za-z0-9._\-]{1,14})\s*/\s*(USDT|USDC|USD)\b', t, flags=re.IGNORECASE):
        syms.append(m.group(1).upper())
    if not syms:
        for m in re.finditer(r'\b([A-Z0-9]{2,10})\b', t):
            base = m.group(1).upper()
            if base in ('USDT','USDC','USD','TP','SL','MA','EMA','MACD','RSI','VWAP','TVEM'):
                continue
            if base.isdigit():
                continue
            syms.append(base)
    side = None
    if any(k in t for k in ['开空','做空','空','short','SHORT','反手空']):
        side = 'short'
    elif any(k in t for k in ['开多','做多','多','long','LONG','反手多']):
        side = 'long'
    entry = pick_num(['入场','进场','成本','entry','avg'])
    sl    = pick_num(['止损','SL','sl'])
    tp    = pick_num(['止盈','TP','tp','目标'])
    if syms:
        return [{'symbol': f'{syms[0]}/USDT', 'side': side, 'entry': entry, 'sl': sl, 'tp': tp}]
    return []


def _is_valid_symbol_base(b: str) -> bool:
    """验证币种基础符号是否有效（避免EMA200, 10X, 1H, TP1等误识别）"""
    import re
    B = (b or '').upper()
    if not B:
        return False
    # Length check: valid crypto symbols are typically 2-15 chars
    if len(B) < 2 or len(B) > 15:
        return False
    # Must contain at least one letter (not pure numbers)
    if not re.search(r'[A-Z]', B):
        return False
    if B in {'USDT','USDC','USD','TP','SL','MA','EMA','SMA','MACD','RSI','VWAP','TVEM','DCA','AVG','PRICE',
             'FVG','GAP','POC','VALUE','AREA','HIGH','LOW','OPEN','CLOSE','VOLUME','VOL','BUY','SELL',
             'ENTRY','EXIT','STOP','LOSS','TAKE','PROFIT','TARGET','LIMIT','MARKET','ORDER'}:
        return False
    if B.isdigit():  # pure number
        return False
    # timeframe-like tokens: 15MIN, 1H, 1W, 1D, 5M, 1HRS
    if re.fullmatch(r'\d+(MIN|MINS?|H|HR|HRS?|D|DAY|DAYS?|W|WK|WEEK|WEEKS?)', B):
        return False
    # leverage/units-like: 10U, 20X, 100USDT, 50USD
    if re.fullmatch(r'\d+(U|USDT|USD|X|倍)', B):
        return False
    # indicators: MA89, EMA12, SMA50, RSI, MACD, EMA200, EMA144, EMA169
    if re.fullmatch(r'(MA|EMA|SMA)\d+', B) or re.fullmatch(r'(RSI|MACD)\d*', B):
        return False
    # TP/SL with numbers: TP1, TP2, TP3, SL1, SL2
    if re.fullmatch(r'(TP|SL)\d+', B):
        return False
    # hyphenated ranges, weird forms (but allow valid symbols with hyphen)
    if '-' in B and not re.fullmatch(r'[A-Z]+-[A-Z]+', B):
        return False
    # mix letter-number ending with W/D etc. like 9W5, 1D2
    if re.fullmatch(r'\d+[WDHM]\d+', B):
        return False
    # patterns starting with single letter + number (like M1, H1) - likely timeframe
    if re.fullmatch(r'[A-Z]\d+', B) and len(B) <= 3:
        return False
    # patterns ending with common suffixes that are not coins
    if B.endswith(('MIN', 'HRS', 'DAYS', 'WKS', 'WEEKS')):
        return False
    return True


def _find_symbols_lean(text: str) -> List[str]:
    import re, json as _j
    t = (text or '')
    out = []
    # explicit pair like ABC/USDT
    for m in re.finditer(r'\b([A-Za-z0-9][A-Za-z0-9._\-]{1,14})\s*/\s*(USDT|USDC|USD)\b', t, flags=re.IGNORECASE):
        base = m.group(1).upper()
        if _is_valid_symbol_base(base):
            out.append(base + '/USDT')
    # bare symbol fallback (strict - uppercase letters/digits 2-10 len)
    if not out:
        for m in re.finditer(r'\b([A-Z0-9]{2,10})\b', t):
            base = m.group(1).upper()
            if not _is_valid_symbol_base(base):
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

def contextual_extract_trades(all_msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """在全量消息上进行上下文增强抽取：
    - 支持结构化卡片（【币种】【方向】【开仓价】【止盈价】【止损价】【杠杆】）
    - 非结构化关键词（开空/做空/开多/做多/short/long + 入场/止损/止盈/目标）
    - 若本条缺失标的，但前 60 分钟内最近一条含标的/或含方向的消息存在，则借用（优先同时找到标的和方向）
    - 若本条仅出现止盈/止损事件，尝试向上回溯 60 分钟寻找最近的方向信息填充
    - 1 分钟去重（symbol+side 同桶保留信息更全的一条）
    """
    import re
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
    out: List[Dict[str, Any]] = []

    def pick_num(text: str, kws: List[str], window: int = 24) -> Optional[float]:
        for kw in kws:
            m = re.search(fr'{re.escape(kw)}[ ：:=]?\s{{0,{window}}}?(\d+\.\d+|\d+)', text, flags=re.IGNORECASE)
            if m:
                try: return float(m.group(1))
                except Exception: continue
        return None

    for i, m in enumerate(msgs):
        t = (m.get('text') or '').strip()
        if not t:
            continue
        ts = m.get('timestamp',''); dt = to_dt_iso(ts)
        syms = _find_symbols_lean(t)
        # direction detection (wide keywords)
        side = None
        if any(k in t for k in ['开空','做空','空单','空仓','空 ','short','SHORT','反手空']):
            side = 'short'
        elif any(k in t for k in ['开多','做多','多单','多仓','多 ','long','LONG','反手多']):
            side = 'long'
        # structured cards
        m_sym = re.search(r'【\s*币种\s*】[ ：:]\s*([A-Za-z0-9._\-]{2,15})', t)
        if m_sym and not syms:
            base = m_sym.group(1).upper()
            if 2 <= len(base) <= 15 and not base.isdigit():
                syms = [base + '/USDT']
        # numbers
        entry = pick_num(t, ['【开仓价】','【开仓】','入场','进场','成本','entry','avg'])
        sl    = pick_num(t, ['【止损价】','止损','SL','sl'])
        tp    = pick_num(t, ['【止盈价】','止盈','TP','tp','目标'])
        # leverage
        lev = None
        mlev = re.search(r'(\d+)\s*(x|X|倍)', t)
        if mlev:
            try: lev = int(mlev.group(1))
            except: lev = None

        symbol = syms[0] if syms else None
        # if missing symbol or side, look back up to 30 msgs / 60 min
        if not (symbol and side):
            for j in range(i-1, max(-1, i-30), -1):
                mj = msgs[j]
                tj = (mj.get('text') or '')
                if not tj: continue
                dtj = to_dt_iso(mj.get('timestamp',''))
                if abs((dt - dtj).total_seconds()) > 3600:
                    break
                if not symbol:
                    sj = _find_symbols_lean(tj)
                    if sj: symbol = sj[0]
                if not side:
                    if any(k in tj for k in ['开空','做空','空单','空仓','short','SHORT','反手空']):
                        side = 'short'
                    elif any(k in tj for k in ['开多','做多','多单','多仓','long','LONG','反手多']):
                        side = 'long'
                if symbol and side:
                    break

        # If message contains only tp/sl words, try infer side from context
        if not side and any(k in t for k in ['止盈','TP','tp','目标','止损','SL','sl']):
            for j in range(i-1, max(-1, i-30), -1):
                mj = msgs[j]
                tj = (mj.get('text') or '')
                if not tj: continue
                dtj = to_dt_iso(mj.get('timestamp',''))
                if abs((dt - dtj).total_seconds()) > 3600:
                    break
                if any(k in tj for k in ['开空','做空','空单','空仓','short','SHORT','反手空']):
                    side = 'short'; break
                if any(k in tj for k in ['开多','做多','多单','多仓','long','LONG','反手多']):
                    side = 'long'; break

        # 过滤无效/噪声标的（如 EMA200/10X/TP1/9W5 等）- 使用统一的验证函数
        if symbol:
            base = symbol.split('/')[0]
            if not _is_valid_symbol_base(base):
                symbol = None
        # Only record trades that at least have a side or carry strong price intent AND valid symbol when present
        if not (side or entry or sl or tp):
            continue
        rec = {'timestamp': norm_ts(ts), 'symbol': symbol, 'side': side, 'entry': entry, 'sl': sl, 'tp': tp, 'leverage': lev, 'raw': t}
        out.append(rec)

    # dedup within minute bucket per (symbol, side)
    def score(x: Dict[str, Any]) -> int:
        s = 0
        for k in ('symbol','side','entry','sl','tp','leverage'):
            if x.get(k) not in (None, ''):
                s += 1
        return s
    buckets = {}
    for r in out:
        sym = r.get('symbol'); side = r.get('side'); tss = r.get('timestamp')
        try:
            dt = datetime.strptime(tss, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except Exception:
            dt = to_dt_iso(tss)
        key = (sym, side, dt.replace(second=0, microsecond=0))
        prev = buckets.get(key)
        if prev is None or score(r) > score(prev):
            buckets[key] = r
    return list(buckets.values())


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
    
    # 初始化详细日志
    logger = get_detailed_logger('dream_run_pipeline')
    
    ap = argparse.ArgumentParser(description='Dream 预处理流水线')
    ap.add_argument('--files', required=True, help='逗号分隔的 JSON 文件列表')
    ap.add_argument('--exchange', default='bitget', choices=['bitget','gate','binance'])
    ap.add_argument('--tf', default='15m', choices=['5m','15m','1h'])
    ap.add_argument('--horizon', default='288h', help='评估窗口，示例：288h')
    ap.add_argument('--tz', default='Asia/Shanghai')
    ap.add_argument('--conflict', default='conservative', choices=['conservative','optimistic'])
    args = ap.parse_args()
    
    # 记录启动
    logger.log_startup({
        'files': args.files,
        'exchange': args.exchange,
        'timeframe': args.tf,
        'horizon': args.horizon,
        'conflict_strategy': args.conflict
    })

    # 解析 horizon
    try:
        if args.horizon.endswith('h'):
            horizon_hours = int(args.horizon[:-1])
        else:
            horizon_hours = int(args.horizon)
    except Exception:
        horizon_hours = 288
    horizon_secs = horizon_hours * 3600

    # 兼容 Windows 传入路径中偶发多空格（例如文件名中有多个空格）
    raw_files = [x for x in args.files.split(',')]
    files = [Path(x.strip()) for x in raw_files if x and x.strip()]
    all_msgs = []
    for f in files:
        if not f.exists():
            print(f"! 文件不存在: {f}", file=sys.stderr); continue
        all_msgs.extend(load_json_any(f))

    # 1) 导入对话（去重：基于timestamp+内容哈希）
    db = TraderDBManager('dream')
    conn = db._get_connection()
    
    # 检查已存在的对话（用于去重）
    existing_conv_hashes = set()
    try:
        existing = conn.execute('SELECT timestamp, trader_message FROM conversations WHERE source = ?', ('dream',)).fetchall()
        for row in existing:
            ts, msg = row[0] if len(row) > 0 else '', row[1] if len(row) > 1 else ''
            if ts and msg:
                import hashlib
                hash_val = hashlib.md5(f"{ts}|{msg}".encode('utf-8')).hexdigest()
                existing_conv_hashes.add(hash_val)
    except Exception as e:
        print(f"⚠️ 检查已存在对话时出错: {e}", file=sys.stderr)
    
    conv_ids = []
    new_conv_count = 0
    for m in all_msgs:
        ts = norm_ts(m.get('timestamp',''))
        txt = m.get('text','')
        if not txt:
            continue
        # 检查是否已存在
        import hashlib
        hash_val = hashlib.md5(f"{ts}|{txt}".encode('utf-8')).hexdigest()
        if hash_val in existing_conv_hashes:
            continue  # 跳过已存在的对话
        cid = db.add_conversation(timestamp=ts, user_message=None, trader_message=txt, source='dream', btc_price=None, extracted_content=None)
        conv_ids.append(cid)
        new_conv_count += 1
        existing_conv_hashes.add(hash_val)  # 避免同批次重复
    
    logger.info(f"导入对话完成: 新增 {new_conv_count} 条，跳过 {len(all_msgs) - new_conv_count} 条重复", {
        'new_count': new_conv_count,
        'skipped_count': len(all_msgs) - new_conv_count,
        'total_count': len(all_msgs)
    })
    print(f"✓ 导入对话: 新增 {new_conv_count} 条，跳过 {len(all_msgs) - new_conv_count} 条重复")

    # 2) 抽取交易（上下文增强 NLP 规则）
    trade_rows = contextual_extract_trades(all_msgs)

    # 写入交易记录并记住生成的ID，便于后续评估留痕（去重：基于timestamp+symbol+direction+entry）
    inserted: List[Dict[str, Any]] = []
    existing_trade_keys = set()
    try:
        existing_trades = conn.execute('''
            SELECT timestamp, symbol, direction, entry_price FROM trade_records 
            WHERE source = ? AND timestamp IS NOT NULL
        ''', ('dream',)).fetchall()
        for row in existing_trades:
            ts, sym, dir, entry = row[0] if len(row) > 0 else '', row[1] if len(row) > 1 else None, row[2] if len(row) > 2 else None, row[3] if len(row) > 3 else None
            key = f"{ts}|{sym}|{dir}|{entry}"
            existing_trade_keys.add(key)
    except Exception as e:
        print(f"⚠️ 检查已存在交易时出错: {e}", file=sys.stderr)
    
    new_trade_count = 0
    for tr in trade_rows:
        # 检查是否已存在
        key = f"{tr['timestamp']}|{tr.get('symbol')}|{tr.get('side')}|{tr.get('entry')}"
        if key in existing_trade_keys:
            continue  # 跳过已存在的交易
        rid = db.add_trade_record(
            timestamp=tr['timestamp'], symbol=tr['symbol'], direction=tr.get('side'),
            entry_price=tr.get('entry'), exit_price=None, profit_pct=None, profit_usdt=None,
            strategy='dream_extract', screenshot_path=None, text_content=tr.get('raw'), source='dream')
        tr2 = dict(tr)
        tr2['id'] = rid
        inserted.append(tr2)
        existing_trade_keys.add(key)
        new_trade_count += 1
    
    logger.info(f"抽取交易完成: 新增 {new_trade_count} 条，跳过 {len(trade_rows) - new_trade_count} 条重复", {
        'new_trade_count': new_trade_count,
        'skipped_count': len(trade_rows) - new_trade_count,
        'total_extracted': len(trade_rows)
    })
    print(f"✓ 抽取交易: 新增 {new_trade_count} 条，跳过 {len(trade_rows) - new_trade_count} 条重复")

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
        sym = tr.get('symbol')
        side = tr.get('side') or ''
        entry = tr.get('entry')
        sl = tr.get('sl')
        tp = tr.get('tp')
        # 尝试从原文回退解析标的；若仍缺失则跳过该条，避免评估崩溃
        if not sym:
            raw = tr.get('raw') or ''
            syms = _find_symbols_lean(raw)
            if syms:
                sym = syms[0]
                tr['symbol'] = sym
            else:
                # 无标的无法评估，略过但不中断
                continue
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
    
    logger.info(f"评估完成，报告已生成", {
        'report_path': str(rpt),
        'evaluated_count': len(inserted),
        'report_lines': len(lines)
    })
    logger.log_shutdown(exit_code=0)
    print('✓ 评估完成，报告已生成:', rpt)


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
