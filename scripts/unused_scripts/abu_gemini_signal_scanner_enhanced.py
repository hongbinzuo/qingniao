#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini信号扫描器（扩展版）

新策略：
- 5分钟：Top 300币种，1天跨度
- 15分钟：Top 200币种，2天跨度
- 1h/4h：Top 50币种，7天跨度
- 每个级别输出一个文件
"""
from __future__ import annotations
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Optional

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 使用K线数据库
try:
    from kline_db import load_klines as _load_klines_db
    from fetch_incremental_klines import ensure_fresh_klines
    KLINE_DB_AVAILABLE = True
except ImportError:
    KLINE_DB_AVAILABLE = False
    _load_klines_db = None
    ensure_fresh_klines = None

# 备用：如果数据库不可用，使用API
try:
    from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
    from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
    API_FALLBACK_AVAILABLE = True
except ImportError:
    API_FALLBACK_AVAILABLE = False
    _get_k_gate = None
    _get_k_bin = None

try:
    from get_extended_gateio_klines import get_kline_gateio_extended
    EXTENDED_GATEIO_AVAILABLE = True
except ImportError:
    EXTENDED_GATEIO_AVAILABLE = False
    get_kline_gateio_extended = None

# 优先使用Al Brooks增强版匹配器（包含TA-Lib）
try:
    from abu.gemini_pattern_matcher_al_brooks_enhanced import AlBrooksEnhancedGeminiPatternMatcher
    MATCHER_AVAILABLE = True
    USE_AL_BROOKS = True
    print("✓ 使用Al Brooks增强版匹配器（包含TA-Lib）", file=sys.stderr)
except ImportError:
    USE_AL_BROOKS = False
    # 备用：使用TA-Lib增强版匹配器
    try:
        from abu.gemini_pattern_matcher_talib_enhanced import TalibEnhancedGeminiPatternMatcher
        MATCHER_AVAILABLE = True
        USE_TALIB = True
        print("✓ 使用TA-Lib增强版匹配器", file=sys.stderr)
    except ImportError:
        USE_TALIB = False
        try:
            from abu.gemini_pattern_matcher_enhanced import EnhancedGeminiPatternMatcher
            MATCHER_AVAILABLE = True
            print("⚠ 使用标准增强版匹配器（TA-Lib不可用）", file=sys.stderr)
        except ImportError:
            MATCHER_AVAILABLE = False
            EnhancedGeminiPatternMatcher = None
            try:
                from abu.gemini_pattern_matcher import GeminiPatternMatcher
                # 兼容旧版本
                class EnhancedGeminiPatternMatcher:
                    def __init__(self, use_dl=False, **kwargs):
                        self.matcher = GeminiPatternMatcher()
                        self.pattern_library = self.matcher.pattern_library
                    
                    def match_patterns(self, klines_dict, min_similarity=0.5, max_matches=10):
                        # 兼容旧接口
                        klines_15m = klines_dict.get('15m', [])
                        klines_1h = klines_dict.get('1h', [])
                        return self.matcher.match_patterns(klines_15m, klines_1h, min_similarity, max_matches)
                    
                    def generate_signal_from_match(self, match, current_price, klines_15m):
                        return self.matcher.generate_signal_from_match(match, current_price, klines_15m)
            except ImportError:
                pass

# 选择匹配器（优先级：Al Brooks > TA-Lib > 标准版）
if USE_AL_BROOKS and MATCHER_AVAILABLE:
    EnhancedGeminiPatternMatcher = AlBrooksEnhancedGeminiPatternMatcher
elif USE_TALIB and MATCHER_AVAILABLE:
    EnhancedGeminiPatternMatcher = TalibEnhancedGeminiPatternMatcher

from db_manager_trader import TraderDBManager

# TOP 50 加密货币（按市值，扩展版）
# 注意：目前只使用真实的50个币种，如需扩展到300个，请添加真实币种代码
TOP_50_SYMBOLS = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'LINK', 'DOT',
    'MATIC', 'TON', 'TRX', 'ATOM', 'SUI', 'APT', 'ARB', 'OP', 'NEAR', 'PEPE',
    'SEI', 'TIA', 'INJ', 'AAVE', 'UNI', 'RUNE', 'ETC', 'FIL', 'ICP', 'XLM',
    'LDO', 'STX', 'HBAR', 'VET', 'ALGO', 'SAND', 'MANA', 'AXS', 'THETA',
    'FLOW', 'EGLD', 'ZIL', 'ENJ', 'CHZ', 'BAT', 'ZEC', 'XMR', 'DASH', 'WAVES'
]

# 排除稳定币
EXCL = set(['USDT', 'USDC', 'DAI', 'BUSD', 'FDUSD', 'TUSD', 'PYUSD', 'USDE', 'GUSD', 'EURT'])

# 排除的教学页面（仓位管理、理论教学等，不是实际的交易模式）
EXCLUDED_PAGES = {222}  # 第222页是仓位管理教学，不应作为交易模式
# 第273页：概念教学（H1/H2/H3讲解），太复杂细腻，不适合当前直接用于信号生成
# 保留作为后期高级识别的候选，但暂时降低优先级
CONCEPT_TEACHING_PAGES = {273}  # 概念教学页面，降低权重但不排除

# 时间框架配置
TIMEFRAME_CONFIGS = {
    '5m': {'limit_per_day': 288, 'description': '5分钟'},
    '15m': {'limit_per_day': 96, 'description': '15分钟'},
    '1h': {'limit_per_day': 24, 'description': '1小时'},
    '4h': {'limit_per_day': 6, 'description': '4小时'}
}

# 默认扫描配置
DEFAULT_TIMEFRAME_COINS = {'5m': 300, '15m': 200, '1h': 50, '4h': 50}
DEFAULT_TIMEFRAME_DAYS = {'5m': 1, '15m': 2, '1h': 7, '4h': 7}


def get_klines(symbol: str, timeframe: str, limit: int, exchange: str = 'gate', days: int = None) -> List[Dict]:
    """
    获取K线数据（优先使用K线数据库，支持增量获取）
    
    Args:
        symbol: 交易对
        timeframe: 时间框架
        limit: K线数量限制（如果days不为None，此参数会被忽略）
        exchange: 交易所（'gate'或'binance'，默认'gate'）
        days: 需要的天数（如果提供，会使用扩展API获取）
    
    Returns:
        K线数据列表
    """
    try:
        # 优先使用K线数据库
        if KLINE_DB_AVAILABLE and _load_klines_db and ensure_fresh_klines:
            # 计算需要的K线数量
            if days is not None:
                # 根据days计算limit
                klines_per_day_map = {
                    '5m': 288,
                    '15m': 96,
                    '1h': 24,
                    '4h': 6,
                    '1d': 1
                }
                klines_per_day = klines_per_day_map.get(timeframe, 96)
                required_limit = days * klines_per_day
            else:
                required_limit = limit
            
            # 确保数据足够新（增量获取）
            ensure_fresh_klines(symbol, timeframe, days=days or 90, exchange=exchange)
            
            # 从数据库加载
            klines = _load_klines_db(symbol, timeframe, limit=required_limit, exchange=exchange)
            if klines:
                return klines
        
        # 备用：如果数据库不可用，使用API
        if API_FALLBACK_AVAILABLE:
            # 如果提供了days参数，使用扩展API（仅Gate.io支持）
            if days is not None and exchange in ['gate', 'auto'] and EXTENDED_GATEIO_AVAILABLE and get_kline_gateio_extended:
                try:
                    kl = get_kline_gateio_extended(symbol=symbol, timeframe=timeframe, days=days)
                    if kl:
                        return kl
                except Exception:
                    pass
            
            # 标准API获取
            if exchange == 'gate' or exchange == 'auto':
                # 优先Gate.io
                if _get_k_gate:
                    kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
                    if kl:
                        return kl
                # Gate.io失败，尝试Binance
                if _get_k_bin:
                    kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
                    return kl or []
            elif exchange == 'binance':
                if _get_k_bin:
                    kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
                    if kl:
                        return kl
                if _get_k_gate:
                    kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
                    return kl or []
    except Exception as e:
        print(f"Error getting klines for {symbol} {timeframe}: {e}", file=sys.stderr)
        return []
    
    return []


def calculate_klines_limit(timeframe: str, days: Optional[int] = None, fallback_limit: int = 200) -> int:
    """根据时间框架和天数计算K线数量"""
    if days is None:
        return fallback_limit
    per_day = TIMEFRAME_CONFIGS.get(timeframe, {}).get('limit_per_day', 96)
    return max(1, int(days) * int(per_day))


def get_top_coins(limit: int, exchange: str = 'gate') -> List[str]:
    """获取Top N币种（按24h成交量），失败则回退到内置列表"""
    symbols: List[str] = []
    if limit <= 0:
        return symbols
    try:
        import requests
        if exchange in ('gate', 'auto'):
            url = "https://api.gateio.ws/api/v4/spot/tickers"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                data.sort(key=lambda x: float(x.get('quote_volume', 0)), reverse=True)
                for item in data:
                    pair = item.get('currency_pair', '')
                    if not pair.endswith('_USDT'):
                        continue
                    symbol = pair.replace('_USDT', '')
                    if not symbol or symbol in EXCL:
                        continue
                    if '_' in symbol or '-' in symbol or len(symbol) > 10:
                        continue
                    if symbol not in symbols:
                        symbols.append(symbol)
                    if len(symbols) >= limit:
                        break
    except Exception as e:
        print(f"⚠️  获取Top币种失败，使用默认列表: {e}", file=sys.stderr)
    if len(symbols) < limit:
        for symbol in TOP_50_SYMBOLS:
            if symbol in EXCL or symbol in symbols:
                continue
            symbols.append(symbol)
            if len(symbols) >= limit:
                break
    if not symbols:
        symbols = TOP_50_SYMBOLS[:limit]
    return symbols


def _extract_page_number(pattern_name: str) -> Optional[int]:
    if not pattern_name:
        return None
    match = re.search(r'page\s*(\d+)', pattern_name, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _normalize_direction(direction: str) -> str:
    direction = (direction or '').lower()
    if direction in ('buy', 'long'):
        return 'long'
    if direction in ('sell', 'short'):
        return 'short'
    return ''


def _is_valid_signal(signal: Dict) -> bool:
    entry = signal.get('entry_price', 0)
    stop_loss = signal.get('stop_loss', 0)
    tp1 = signal.get('take_profit_1', 0)
    direction = _normalize_direction(signal.get('direction', ''))
    if entry <= 0 or stop_loss <= 0 or tp1 <= 0:
        return False
    if abs(entry - stop_loss) < 0.0001 or abs(entry - tp1) < 0.0001 or abs(stop_loss - tp1) < 0.0001:
        return False
    if direction == 'long' and (stop_loss >= entry or tp1 <= entry):
        return False
    if direction == 'short' and (stop_loss <= entry or tp1 >= entry):
        return False
    return direction in ('long', 'short')


def scan_timeframe(
    timeframe: str,
    symbols: List[str],
    days: int,
    top_n: int,
    exchange: str,
    min_similarity: float,
    max_matches_per_symbol: int,
    write_db: bool,
    matcher
) -> List[Dict]:
    """扫描单个时间框架并生成信号"""
    if not symbols:
        return []
    desc = TIMEFRAME_CONFIGS.get(timeframe, {}).get('description', timeframe)
    print("=" * 80)
    print(f"扫描{desc}时间框架 (Top {len(symbols)}币种, {days}天跨度, Top {top_n}信号)")
    print("=" * 80)
    print()

    all_signals: List[Dict] = []
    processed = 0

    # 15m是主特征时间框架，确保至少2天
    days_15m = max(days, DEFAULT_TIMEFRAME_DAYS['15m'])
    limit_15m = calculate_klines_limit('15m', days_15m)
    limit_tf = calculate_klines_limit(timeframe, days)

    for symbol in symbols:
        if symbol.upper() in EXCL:
            continue
        processed += 1
        if processed % 10 == 0:
            print(f"[{processed}/{len(symbols)}] 扫描 {symbol}...", end=' ', flush=True)

        klines_15m = get_klines(symbol, '15m', limit=limit_15m, exchange=exchange, days=days_15m)
        if not klines_15m or len(klines_15m) < 20:
            if processed % 10 == 0:
                print("跳过（15m数据不足）")
            continue

        if timeframe == '15m':
            klines_tf = klines_15m
        else:
            klines_tf = get_klines(symbol, timeframe, limit=limit_tf, exchange=exchange, days=days)
            if not klines_tf or len(klines_tf) < 20:
                if processed % 10 == 0:
                    print("跳过（K线数据不足）")
                continue

        klines_dict = {'15m': klines_15m}
        if timeframe != '15m':
            klines_dict[timeframe] = klines_tf

        try:
            matches = matcher.match_patterns(
                klines_dict,
                min_similarity=min_similarity,
                max_matches=max_matches_per_symbol
            )
        except Exception as e:
            if processed % 10 == 0:
                print(f"匹配失败: {e}")
            continue

        if not matches:
            if processed % 10 == 0:
                print("无匹配")
            continue

        current_price = klines_tf[-1]['close']
        signals_count = 0
        for match in matches:
            pattern_name = match.get('pattern_name', '')
            page_num = _extract_page_number(pattern_name)
            if page_num in EXCLUDED_PAGES:
                continue
            signal = matcher.generate_signal_from_match(match, current_price, klines_15m)
            if not signal:
                continue
            signal['direction'] = _normalize_direction(signal.get('direction', ''))
            if not _is_valid_signal(signal):
                continue

            similarity = float(match.get('similarity', 0.0))
            probability = float(signal.get('probability', 0.5))
            score = (similarity * 0.7 + probability * 0.3) * 100
            if page_num in CONCEPT_TEACHING_PAGES:
                score *= 0.7

            signal.update({
                'symbol': symbol,
                'timeframe': timeframe,
                'pattern_name': pattern_name,
                'pattern_type': match.get('pattern_type', ''),
                'similarity': similarity,
                'score': score
            })
            all_signals.append(signal)
            signals_count += 1

        if processed % 10 == 0:
            print(f"信号: {signals_count}")

    print()
    print(f"总计: {len(all_signals)} 个信号")

    all_signals.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_signals = all_signals[:top_n]

    if write_db and top_signals:
        db = TraderDBManager('abu')
        signal_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for sig in top_signals:
            try:
                direction_cn = '做多' if sig.get('direction') == 'long' else '做空'
                entry_model = sig.get('pattern_name') or sig.get('reason', 'Abu/Gemini')
                db.add_trading_signal({
                    'signal_time': signal_time,
                    'timeframe': sig.get('timeframe', timeframe),
                    'symbol': sig.get('symbol'),
                    'signal_type': direction_cn,
                    'entry_price': sig.get('entry_price'),
                    'stop_loss': sig.get('stop_loss'),
                    'take_profit_1': sig.get('take_profit_1'),
                    'take_profit_2': sig.get('take_profit_2'),
                    'entry_model': f"Abu/Gemini/{entry_model}",
                    'strength': 'high' if sig.get('similarity', 0) >= 0.7 else 'medium',
                    'risk_reward_ratio': None,
                    'volatility_level': None,
                    'system_name': 'abu',
                    'score': sig.get('score', 0),
                    'notes': sig.get('reason', '')
                })
            except Exception as e:
                print(f"⚠️  写入信号失败: {e}", file=sys.stderr)
        db.close_all_connections()

    return top_signals


def save_signals_to_file(signals: List[Dict], timeframe: str, days: int, exchange: str) -> Optional[Path]:
    """保存信号到Markdown文件"""
    if not signals:
        return None
    output_dir = ROOT / 'outputs' / 'trading_signals'
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_file = output_dir / f'ABU_Gemini_{timeframe}_top{len(signals)}_{timestamp}.md'

    lines = []
    lines.append(f"# ABU Gemini {timeframe} 信号 (Top {len(signals)})")
    lines.append("")
    lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"数据跨度: {days}天")
    lines.append(f"交易所: {exchange}")
    lines.append("")
    lines.append("| 序号 | 币种 | 方向 | 入场 | 止损 | 止盈1 | 止盈2 | 相似度 | 评分 | 模式 |")
    lines.append("|------|------|------|------|------|-------|-------|--------|------|------|")

    for i, sig in enumerate(signals, 1):
        direction = sig.get('direction', '').lower()
        direction_cn = '做多' if direction == 'long' else '做空'
        tp2 = sig.get('take_profit_2')
        tp2_str = f"{tp2:.4f}" if isinstance(tp2, (int, float)) else 'N/A'
        similarity = sig.get('similarity')
        similarity_str = f"{similarity:.2%}" if isinstance(similarity, (int, float)) else 'N/A'
        lines.append(
            f"| {i} | {sig.get('symbol', 'N/A')} | {direction_cn} | "
            f"{sig.get('entry_price', 0):.4f} | {sig.get('stop_loss', 0):.4f} | "
            f"{sig.get('take_profit_1', 0):.4f} | {tp2_str} | "
            f"{similarity_str} | {sig.get('score', 0):.2f} | {sig.get('pattern_name', 'N/A')} |"
        )

    out_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n✓ 已生成报告: {out_file}")
    return out_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description='ABU Gemini信号扫描器（扩展版）')
    parser.add_argument('--top', type=int, default=20, help='每个时间框架输出Top N信号')
    parser.add_argument('--timeframes', type=str, default='5m,15m,1h,4h', help='时间框架（逗号分隔）')
    parser.add_argument('--exchange', type=str, default='gate', help='交易所（gate/binance/auto）')
    parser.add_argument('--min-similarity', type=float, default=0.5, help='最小相似度阈值（0.0-1.0）')
    parser.add_argument('--max-matches-per-symbol', type=int, default=5, help='每个币种最大匹配数')
    parser.add_argument('--write-db', type=int, default=1, help='是否写入数据库（0/1）')
    parser.add_argument('--coins', type=int, default=0, help='覆盖所有时间框架的币种数量（0=默认）')
    parser.add_argument('--days', type=int, default=0, help='覆盖所有时间框架的数据跨度天数（0=默认）')
    parser.add_argument('--signal-level', type=str, default='trade_ready',
                        choices=['none', 'basic', 'trade_ready'],
                        help='交易信号完整性等级（none/basic/trade_ready）')

    args = parser.parse_args()

    if not MATCHER_AVAILABLE or not EnhancedGeminiPatternMatcher:
        print("✗ 错误: 无法导入模式匹配器模块", file=sys.stderr)
        return 1

    matcher = EnhancedGeminiPatternMatcher(
        use_dl=False,
        require_trading_signals=True,
        exclude_unmarked=True,
        signal_completeness=args.signal_level
    )
    pattern_count = len(matcher.pattern_library) if hasattr(matcher, 'pattern_library') else 0
    if pattern_count == 0:
        print("✗ 错误: 模式库为空，请先运行Gemini分析流程", file=sys.stderr)
        return 1
    print(f"✓ 模式库已加载: {pattern_count} 个模式")

    timeframes = [t.strip() for t in args.timeframes.split(',') if t.strip()]
    timeframes = [t for t in timeframes if t in TIMEFRAME_CONFIGS]
    if not timeframes:
        print("✗ 错误: 未指定有效的时间框架", file=sys.stderr)
        return 1

    max_coins = max(DEFAULT_TIMEFRAME_COINS.get(tf, 50) for tf in timeframes)
    if args.coins and args.coins > 0:
        max_coins = args.coins
    all_symbols = get_top_coins(max_coins, exchange=args.exchange)

    for timeframe in timeframes:
        coins_limit = args.coins if args.coins > 0 else DEFAULT_TIMEFRAME_COINS.get(timeframe, 50)
        days = args.days if args.days > 0 else DEFAULT_TIMEFRAME_DAYS.get(timeframe, 2)
        symbols = all_symbols[:coins_limit]
        top_signals = scan_timeframe(
            timeframe=timeframe,
            symbols=symbols,
            days=days,
            top_n=args.top,
            exchange=args.exchange,
            min_similarity=args.min_similarity,
            max_matches_per_symbol=args.max_matches_per_symbol,
            write_db=bool(args.write_db),
            matcher=matcher
        )
        save_signals_to_file(top_signals, timeframe, days, args.exchange)

    return 0


if __name__ == '__main__':
    sys.exit(main())
