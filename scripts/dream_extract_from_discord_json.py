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
    'TP','SL','MA','EMA','SMA','MACD','RSI','VWAP','TVEM','DCA','AVG','PRICE','USDT','USDC','USD',
    'FVG','GAP','POC','VALUE','AREA','HIGH','LOW','OPEN','CLOSE','VOLUME','VOL','BUY','SELL',
    'ENTRY','EXIT','STOP','LOSS','TAKE','PROFIT','TARGET','LIMIT','MARKET','ORDER'])

def _is_valid_base(base: str) -> bool:
    b = (base or '').upper()
    if not b:
        return False
    # Length check: valid crypto symbols are typically 2-15 chars
    if len(b) < 2 or len(b) > 15:
        return False
    # Must contain at least one letter (not pure numbers)
    if not re.search(r'[A-Z]', b):
        return False
    if b in EXCLUDE_TOKENS:
        return False
    # pure number or number with trailing dot
    if re.fullmatch(r'\d+(?:\.\d+)?', b) or b.endswith('.'):
        return False
    # timeframe-like tokens: 15MIN, 1H, 1W, 1D, 5M, 1HRS
    if re.fullmatch(r'\d+(MIN|MINS?|H|HR|HRS?|D|DAY|DAYS?|W|WK|WEEK|WEEKS?)', b):
        return False
    # units or leverage-like: 10U, 20X, 100USDT, 50USD
    if re.fullmatch(r'\d+(U|USDT|USD|X|倍)', b):
        return False
    # indicators: MA89, EMA12, SMA50, RSI, MACD, EMA200, EMA144, EMA169
    if re.fullmatch(r'(MA|EMA|SMA)\d+', b) or re.fullmatch(r'(RSI|MACD)\d*', b):
        return False
    # TP/SL with numbers: TP1, TP2, TP3, SL1, SL2
    if re.fullmatch(r'(TP|SL)\d+', b):
        return False
    # ranges or mixed numeric-hyphen (but allow valid symbols with hyphen like USDC-BTC)
    if '-' in b and not re.fullmatch(r'[A-Z]+-[A-Z]+', b):
        return False
    # weird patterns like 9W5, 1D2, 5H3 (number + letter + number)
    if re.fullmatch(r'\d+[WDHM]\d+', b):
        return False
    # patterns starting with number and ending with letter (like 10X, but already caught above)
    # Additional: single letter + number (like M1, H1) - likely timeframe
    if re.fullmatch(r'[A-Z]\d+', b) and len(b) <= 3:
        return False
    # patterns ending with common suffixes that are not coins
    if b.endswith(('MIN', 'HRS', 'DAYS', 'WKS', 'WEEKS')):
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


def pick_first(label_kws: Tuple[str,...], t: str, base_price: Optional[float] = None) -> Optional[float]:
    """提取价格：支持绝对价格、百分比价格（如+5%）、价格范围（如100-105取平均值）"""
    for kw in label_kws:
        # 1. 尝试百分比价格（如 "入场+5%" 或 "止损-2%"）
        pct_pattern = re.escape(kw) + r'.{0,20}?([+-]?\d+\.?\d*)\s*%'
        m_pct = re.search(pct_pattern, t, re.IGNORECASE)
        if m_pct and base_price:
            try:
                pct = float(m_pct.group(1))
                return base_price * (1 + pct / 100.0)
            except Exception:
                pass
        
        # 2. 尝试价格范围（如 "入场 100-105" 或 "止损 50-55"）
        range_pattern = re.escape(kw) + r'.{0,20}?(\d+\.?\d*)\s*[-~]\s*(\d+\.?\d*)'
        m_range = re.search(range_pattern, t, re.IGNORECASE)
        if m_range:
            try:
                low = float(m_range.group(1))
                high = float(m_range.group(2))
                # 返回范围的平均值
                return (low + high) / 2.0
            except Exception:
                pass
        
        # 3. 标准绝对价格提取
        m = re.search(re.escape(kw) + r'.{0,16}?(\d+\.\d+|\d+)', t, re.IGNORECASE)
        if m:
            num = m.group(1)
            # 如果附近有%，且不是百分比模式（已处理），则跳过
            span_s, span_e = m.span(1)
            window = t[max(0, span_s-3):min(len(t), span_e+3)]
            # 只有在不是百分比计算的情况下才跳过
            if '%' in window and not (base_price and re.search(r'[+-]\s*\d+\.?\d*\s*%', window)):
                continue
            try:
                return float(num)
            except Exception:
                continue
    return None


def extract_from_messages(msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # context: remember last symbol and side within 60 minutes (统一时间窗口)
    CONTEXT_WINDOW_SECS = 3600  # 60 minutes
    last_sym: Optional[str] = None
    last_sym_ts: Optional[datetime] = None
    last_side: Optional[str] = None
    last_side_ts: Optional[datetime] = None
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
        # context symbol borrowing (60分钟窗口)
        symbol = syms[0] if syms else None
        if not symbol and last_sym and last_sym_ts:
            time_diff = abs((dt - last_sym_ts).total_seconds())
            if time_diff <= CONTEXT_WINDOW_SECS:
                # message references direction or prices but no symbol
                if side or entry or sl or tp:
                    symbol = last_sym
        # context side borrowing (如果当前消息有价格信息但无方向，尝试借用上下文方向)
        if not side and (entry or sl or tp) and last_side and last_side_ts:
            time_diff = abs((dt - last_side_ts).total_seconds())
            if time_diff <= CONTEXT_WINDOW_SECS:
                side = last_side
        # update context if current has explicit symbol
        if syms:
            last_sym = syms[0]
            last_sym_ts = dt
        # update context if current has explicit side
        if side:
            last_side = side
            last_side_ts = dt
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
