#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dream 交易抽取（从 Discord JSON 导出文件）
- 仅解析作者为 Dream 本人（默认: qimeng0104_49398）的消息
- 抽取: symbol(含大小写/数字/连字符/显式 /USDT)、direction(空/多/short/long)、entry/SL/TP/杠杆
- 关联上下文: 若本条无symbol，但近10分钟内最近一条含symbol的消息存在，则借用其symbol
- 去重: 同symbol+direction 在同一分钟窗口内只保留信息更完整的一条
输出: outputs/dream/dream_extracted_<ts>.json/.md
"""
from __future__ import annotations
import sys, json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

DREAM_AUTHOR = 'qimeng0104_49398'
PAIR_QUOTE = ('USDT','USDC','USD','BTC')
# token id: letters+numbers+.-_ between 2 and 15 chars
SYM_CORE_RE = r'[A-Za-z0-9][A-Za-z0-9._\-]{1,14}'
PAIR_RE = re.compile(rf'\b({SYM_CORE_RE})\s*/\s*(?:{"|".join(PAIR_QUOTE)})\b', re.IGNORECASE)
# Bare symbol: stricter（只接受大写字母数字，长度2-10，不含点/连字符）
BARE_SYM_RE = re.compile(r'\b([A-Z0-9]{2,10})\b')
# Keywords
KW_SHORT = ('开空','做空','空单','空仓','空','short','SHORT','s空','反手空')
KW_LONG  = ('开多','做多','多单','多仓','多','long','LONG','反手多')
KW_ENTRY = ('入场','进场','限价','开仓','开在','挂在','成本','均价','entry','avg','average','价格','price')
KW_SL    = ('止损','SL','sl','风控','防守','不破','破位')
KW_TP    = ('止盈','TP','tp','目标','第一目标','第二目标','tp1','tp2')

PCT_NEAR_RE = re.compile(r'(\d+\.?\d*)\s*%')
NUM_RE = re.compile(r'(\d+\.\d+|\d+)')
LEV_RE = re.compile(r'(\d+)\s*(x|X|倍)')
TIME_PARSE_FORMATS = ('%Y-%m-%dT%H:%M:%S.%f','%Y-%m-%dT%H:%M:%S')

# Optional alias map
ALIAS_PATH = Path('config/dream_symbol_alias.json')
ALIAS = {}
if ALIAS_PATH.exists():
    try:
        ALIAS = json.loads(ALIAS_PATH.read_text(encoding='utf-8'))
    except Exception:
        ALIAS = {}

# Optional Bitget supported bases for strict matching
BASES_PATH = Path('config/dream_bitget_bases.json')
BITGET_BASES: set[str] = set()
if BASES_PATH.exists():
    try:
        BITGET_BASES = set(json.loads(BASES_PATH.read_text(encoding='utf-8')))
    except Exception:
        BITGET_BASES = set()

def to_dt(ts: str) -> datetime:
    s = (ts or '').rstrip('Z')
    for fmt in TIME_PARSE_FORMATS:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return datetime.now(timezone.utc)


def norm_symbol(s: str) -> Optional[str]:
    if not s:
        return None
    up = s.upper()
    up = ALIAS.get(up, up)
    # If Bitget base list present, enforce membership
    if BITGET_BASES and up not in BITGET_BASES:
        return None
    return f'{up}/USDT'


EXCLUDE_TOKENS = set(['MIN','MINS','M','H','HR','HRS','D','DAY','W','WK','WEEK',
    'TP','SL','MA','EMA','SMA','MACD','RSI','VWAP','TVEM','DCA','AVG','PRICE','USDT','USDC','USD'])

def _is_valid_base(base: str) -> bool:
    b = (base or '').upper()
    if not b:
        return False
    if b in EXCLUDE_TOKENS:
        return False
    # pure number or number with trailing dot
    if re.fullmatch(r'\d+(?:\.\d+)?', b) or b.endswith('.'):
        return False
    # timeframe-like tokens: 15MIN, 1H, 1W, 1D
    if re.fullmatch(r'\d+(MIN|M|H|HR|HRS|D|DAY|W|WK|WEEK)', b):
        return False
    # units or leverage-like: 10U, 20X
    if re.fullmatch(r'\d+(U|USDT|USD|X)', b):
        return False
    # indicators: MA89, EMA12, SMA50, RSI, MACD
    if re.fullmatch(r'(MA|EMA|SMA)\d+', b) or re.fullmatch(r'(RSI|MACD)\d*', b):
        return False
    # ranges or mixed numeric-hyphen
    if '-' in b:
        return False
    return True


def find_symbols(text: str) -> List[str]:
    t = text or ''
    out = []
    # explicit pairs
    for m in PAIR_RE.finditer(t):
        base = m.group(1)
        if _is_valid_base(base):
            ns = norm_symbol(base)
            if ns:
                out.append(ns)
    # bare symbols (avoid capturing quote tokens and common words)
    if not out:
        for m in BARE_SYM_RE.finditer(t.upper()):
            core = m.group(1)
            if not _is_valid_base(core):
                continue
            ns = norm_symbol(core)
            if ns:
                out.append(ns)
    # dedup preserve order
    seen = set(); res = []
    for s in out:
        if s and s not in seen:
            seen.add(s); res.append(s)
    return res


def has_kw(text: str, kws: Tuple[str,...]) -> bool:
    return any(kw in text for kw in kws)


def pick_first(label_kws: Tuple[str,...], t: str) -> Optional[float]:
    # prioritize numbers near keywords; ignore percent
    for kw in label_kws:
        m = re.search(re.escape(kw) + r'.{0,16}?(\d+\.\d+|\d+)', t, re.IGNORECASE)
        if m:
            num = m.group(1)
            # discard if explicitly percent nearby
            span_s, span_e = m.span(1)
            window = t[max(0, span_s-3):min(len(t), span_e+3)]
            if '%' in window:
                continue
            try:
                return float(num)
            except Exception:
                continue
    return None


def extract_from_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # context: remember last symbol within 10 minutes
    last_sym: Optional[str] = None
    last_sym_ts: Optional[datetime] = None
    results: List[Dict[str, Any]] = []

    for m in msgs:
        t = (m.get('text') or '').strip()
        if not t:
            continue
        dt = to_dt(m.get('timestamp'))
        syms = find_symbols(t)
        side = None
        if has_kw(t, KW_SHORT):
            side = 'short'
        elif has_kw(t, KW_LONG):
            side = 'long'
        # numbers
        entry = pick_first(KW_ENTRY, t)
        sl    = pick_first(KW_SL, t)
        tp    = pick_first(KW_TP, t)
        # leverage
        lev = None
        mlev = LEV_RE.search(t)
        if mlev:
            try: lev = int(mlev.group(1))
            except: lev = None
        # context symbol borrowing
        symbol = syms[0] if syms else None
        if not symbol and last_sym and last_sym_ts and abs((dt - last_sym_ts).total_seconds()) <= 600:
            # message references direction or prices but no symbol
            if side or entry or sl or tp:
                symbol = last_sym
        # update context if current has explicit symbol
        if syms:
            last_sym = syms[0]
            last_sym_ts = dt
        # 只在存在方向或价格要素时才输出，避免纯提及symbol导致噪音
        if not (side or entry or sl or tp or lev):
            continue
        results.append({
            'timestamp': m.get('timestamp'),
            'symbol': symbol,
            'side': side,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'leverage': lev,
            'text': t[:500]
        })
    # dedup within 1-minute bucket for same symbol+side: keep one with more fields
    def score(x):
        s = 0
        for k in ('symbol','side','entry','sl','tp','leverage'):
            if x.get(k) not in (None, ''):
                s += 1
        return s
    buckets = {}
    out = []
    for r in results:
        sym = r.get('symbol'); side = r.get('side')
        dt = to_dt(r.get('timestamp'))
        key = (sym, side, dt.replace(second=0, microsecond=0))
        prev = buckets.get(key)
        if prev is None or score(r) > score(prev):
            buckets[key] = r
    out = list(buckets.values())
    # sort by time
    out.sort(key=lambda x: to_dt(x.get('timestamp')))
    return out


def load_messages_from_files(files: List[Path]) -> List[Dict[str, Any]]:
    all_msgs = []
    for p in files:
        d = json.loads(p.read_text(encoding='utf-8'))
        msgs = d.get('messages') or []
        for m in msgs:
            if (m.get('author') or {}).get('name') != DREAM_AUTHOR:
                continue
            txt = (m.get('content') or '').strip()
            if not txt:
                continue
            all_msgs.append({'timestamp': m.get('timestamp') or m.get('timestampEdited'), 'text': txt, 'id': m.get('id')})
    # sort
    all_msgs.sort(key=lambda x: to_dt(x['timestamp']))
    return all_msgs


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Dream 交易抽取（Discord JSON）')
    ap.add_argument('--files', required=True, help='逗号分隔的 JSON 文件列表')
    args = ap.parse_args()
    files = [Path(x.strip()) for x in args.files.split(',') if x.strip()]

    msgs = load_messages_from_files(files)
    trades = extract_from_messages(msgs)

    outdir = Path('outputs') / 'dream'
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    jpath = outdir / f'dream_extracted_trades_v2_{ts}.json'
    mpath = outdir / f'dream_extracted_trades_v2_{ts}.md'

    with jpath.open('w', encoding='utf-8') as f:
        json.dump(trades, f, ensure_ascii=False, indent=2)

    # preview markdown
    lines = [f"# Dream 交易抽取 v2 ({ts})", '', f"共抽取 {len(trades)} 条（去重后）", '', '| 时间 | 标的 | 方向 | 入场 | SL | TP | 杠杆 | 原文摘录 |', '|---|---|---|---:|---:|---:|---:|---|']
    for x in trades[:300]:
        lines.append(f"| {x.get('timestamp','')} | {x.get('symbol','') or ''} | {x.get('side','') or ''} | {x.get('entry','') or ''} | {x.get('sl','') or ''} | {x.get('tp','') or ''} | {x.get('leverage','') or ''} | {x.get('text','').replace('|','/')} |")
    mpath.write_text('\n'.join(lines), encoding='utf-8')

    print('✓ Extracted:', len(trades))
    print('JSON:', jpath)
    print('MD  :', mpath)

if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    main()
