#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini信号扫描器（基于Gemini特征库）

功能：
- 获取TOP 20加密货币的实时K线数据（15分钟、1小时级别，7天范围）
- 与pattern_library中的Gemini特征进行匹配
- 生成高质量的交易信号

使用：
    python scripts/abu/abu_gemini_signal_scanner.py --top 10 --exchange binance --write-db 1
"""
from __future__ import annotations
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

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

from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
try:
    from generate_btc_de_signals import get_btc_kline_bitget as _get_k_bitget_btc
    def _get_k_bitget(symbol='BTC', timeframe='15m', limit=200):
        return _get_k_bitget_btc(timeframe=timeframe, limit=limit) if symbol == 'BTC' else None
except Exception:
    _get_k_bitget = None

try:
    from abu.gemini_pattern_matcher import GeminiPatternMatcher
    MATCHER_AVAILABLE = True
except ImportError:
    MATCHER_AVAILABLE = False
    GeminiPatternMatcher = None

from db_manager_trader import TraderDBManager

# TOP 20 加密货币（按市值）
TOP_20_SYMBOLS = [
    'BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'AVAX', 'DOGE', 'LINK', 'DOT',
    'MATIC', 'TON', 'TRX', 'ATOM', 'SUI', 'APT', 'ARB', 'OP', 'NEAR', 'PEPE'
]

# 排除稳定币
EXCL = set(['USDT', 'USDC', 'DAI', 'BUSD', 'FDUSD', 'TUSD', 'PYUSD', 'USDE', 'GUSD', 'EURT'])


def get_klines(symbol: str, timeframe: str, limit: int, exchange: str = 'binance') -> List[Dict]:
    """获取K线数据（多数据源支持）"""
    try:
        if exchange == 'binance':
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        elif exchange == 'gate':
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        else:
            # default: binance -> gate
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
    except Exception:
        return []
    return []


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ABU Gemini信号扫描器（基于特征库匹配）')
    parser.add_argument('--top', type=int, default=10, help='生成Top N个信号')
    parser.add_argument('--exchange', type=str, default='binance', help='交易所（binance/gate）')
    parser.add_argument('--write-db', type=int, default=1, help='是否写入数据库（0/1）')
    parser.add_argument('--min-similarity', type=float, default=0.5, help='最小相似度阈值（0.0-1.0）')
    parser.add_argument('--max-matches-per-symbol', type=int, default=3, help='每个币种最大匹配数')
    
    args = parser.parse_args()
    
    if not MATCHER_AVAILABLE:
        print("✗ 错误: 无法导入GeminiPatternMatcher模块", file=sys.stderr)
        return 1
    
    print("=" * 80)
    print("ABU Gemini信号扫描器（基于特征库匹配）")
    print("=" * 80)
    print(f"币种数量: {len(TOP_20_SYMBOLS)}")
    print(f"最小相似度: {args.min_similarity}")
    print(f"每个币种最大匹配数: {args.max_matches_per_symbol}")
    print()
    
    # 初始化匹配器
    print("加载模式库...")
    matcher = GeminiPatternMatcher()
    
    if len(matcher.pattern_library) == 0:
        print("✗ 错误: 模式库为空，请先运行Gemini分析流程", file=sys.stderr)
        return 1
    
    print(f"✓ 模式库已加载: {len(matcher.pattern_library)} 个模式")
    print()
    
    # 扫描币种
    all_signals: List[Dict] = []
    
    for symbol in TOP_20_SYMBOLS:
        if symbol.upper() in EXCL:
            continue
        
        print(f"扫描 {symbol}...", end=' ', flush=True)
        
        # 获取K线数据
        # 7天范围：15m约672根，1h约168根
        kl15m = get_klines(symbol, '15m', 672, args.exchange)  # 7天
        kl1h = get_klines(symbol, '1h', 168, args.exchange)  # 7天
        
        if not kl15m or len(kl15m) < 50:
            print("跳过（K线数据不足）")
            continue
        
        # 匹配模式
        matches = matcher.match_patterns(
            kl15m, kl1h,
            min_similarity=args.min_similarity,
            max_matches=args.max_matches_per_symbol
        )
        
        if not matches:
            print("无匹配")
            continue
        
        # 生成信号
        current_price = kl15m[-1]['close']
        signals_count = 0
        
        for match in matches:
            signal = matcher.generate_signal_from_match(match, current_price, kl15m)
            if signal:
                signal['symbol'] = symbol
                signal['timeframe'] = '15m'
                # 计算综合评分（基于相似度和概率）
                signal['score'] = (match['similarity'] * 0.7 + signal.get('probability', 0.5) * 0.3) * 100
                all_signals.append(signal)
                signals_count += 1
        
        print(f"匹配 {signals_count} 个信号")
    
    print()
    print(f"总共匹配到 {len(all_signals)} 个信号")
    
    # 按评分排序，选择Top N
    all_signals.sort(key=lambda x: x.get('score', 0), reverse=True)
    top_signals = all_signals[:args.top]
    
    if not top_signals:
        print("未生成任何信号")
        return 0
    
    print(f"\n选择Top {len(top_signals)} 个信号:")
    print("-" * 80)
    for i, sig in enumerate(top_signals, 1):
        print(f"{i}. {sig['symbol']} {sig['direction'].upper():5s} | "
              f"Entry: {sig['entry_price']:.4f} | "
              f"SL: {sig['stop_loss']:.4f} | "
              f"TP1: {sig['take_profit_1']:.4f} | "
              f"相似度: {sig['similarity']:.2%} | "
              f"评分: {sig['score']:.2f}")
    print("-" * 80)
    
    # 写入数据库
    if args.write_db and top_signals:
        print("\n写入数据库...")
        db = TraderDBManager('abu')
        written_count = 0
        
        for sig in top_signals:
            try:
                db.add_trading_signal(
                    signal_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    timeframe=sig['timeframe'],
                    signal_type=sig['direction'],
                    symbol=sig['symbol'],
                    entry_price=sig['entry_price'],
                    stop_loss=sig['stop_loss'],
                    take_profit_1=sig['take_profit_1'],
                    take_profit_2=sig.get('take_profit_2'),
                    entry_model=f"Abu/Gemini/{sig['pattern_name']}",
                    strength='high' if sig['similarity'] > 0.7 else 'medium',
                    risk_reward_ratio=None,
                    volatility_level=None,
                    system_name='abu',
                    score=float(sig.get('score', 0.0)),
                    notes=sig.get('reason', '')
                )
                written_count += 1
            except Exception as e:
                print(f"⚠️  写入信号失败: {e}", file=sys.stderr)
        
        db.close()
        print(f"✓ 已写入 {written_count} 个信号到数据库")
    
    # 生成Markdown文件
    out_file = ROOT / 'outputs' / 'trading_signals' / f"ABU_Gemini_top{args.top}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    lines = [
        f"# ABU Gemini信号 Top{args.top}",
        f"",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**模式库规模**: {len(matcher.pattern_library)} 个模式",
        f"**匹配阈值**: {args.min_similarity:.0%}",
        f"",
        "| # | Symbol | Direction | Entry | SL | TP1 | TP2 | Similarity | Score | Pattern |",
        "|---|---|:---:|---:|---:|---:|---:|---:|:---:|---|"
    ]
    
    for i, sig in enumerate(top_signals, 1):
        lines.append(
            f"| {i} | {sig['symbol']} | {sig['direction']} | "
            f"{sig['entry_price']:.4f} | {sig['stop_loss']:.4f} | "
            f"{sig['take_profit_1']:.4f} | {sig.get('take_profit_2', 0):.4f} | "
            f"{sig['similarity']:.2%} | {sig['score']:.2f} | {sig['pattern_name']} |"
        )
    
    out_file.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\n✓ 已生成报告: {out_file}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())



