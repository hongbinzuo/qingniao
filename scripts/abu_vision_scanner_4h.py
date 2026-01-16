#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ABU Gemini Flash 视觉匹配扫描器（每4小时运行一次）

使用Gemini Flash进行深度视觉匹配，成本控制：每4小时运行一次
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
OUTPUTS = ROOT / 'outputs'
VISION_RESULTS = OUTPUTS / 'vision_matching'

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

VISION_RESULTS.mkdir(parents=True, exist_ok=True)

# Top 10币种（成本控制：视觉匹配只扫描前10个）
TOP_10_SYMBOLS = [
    'BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'SOL_USDT', 'XRP_USDT',
    'ADA_USDT', 'DOGE_USDT', 'TON_USDT', 'AVAX_USDT', 'SHIB_USDT'
]

# Top 30币种（用于模式匹配，视觉匹配不使用）
TOP_30_SYMBOLS = [
    'BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'SOL_USDT', 'XRP_USDT',
    'ADA_USDT', 'DOGE_USDT', 'TON_USDT', 'AVAX_USDT', 'SHIB_USDT',
    'DOT_USDT', 'MATIC_USDT', 'LINK_USDT', 'UNI_USDT', 'LTC_USDT',
    'ATOM_USDT', 'ETC_USDT', 'XLM_USDT', 'FIL_USDT', 'TRX_USDT',
    'APT_USDT', 'ARB_USDT', 'OP_USDT', 'NEAR_USDT', 'ALGO_USDT',
    'VET_USDT', 'ICP_USDT', 'HBAR_USDT', 'EOS_USDT', 'AAVE_USDT'
]

EXCL = set(['USDT', 'USDC', 'DAI', 'BUSD', 'FDUSD', 'TUSD', 'PYUSD', 'USDE', 'GUSD', 'EURT'])


def get_klines(symbol: str, timeframe: str, limit: int, exchange: str = 'gate') -> list:
    """获取K线数据
    
    Args:
        symbol: 币种符号，可以是 'BTC' 或 'BTC_USDT' 格式
        timeframe: 时间框架
        limit: K线数量
        exchange: 交易所
    """
    try:
        try:
            from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
            from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
        except ImportError:
            try:
                from src.generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
                from src.generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
            except ImportError:
                print("⚠️  无法导入K线获取函数", file=sys.stderr)
                return []
        
        # 处理符号格式：'BTC_USDT' → 'BTC'
        clean_symbol = symbol.replace('_USDT', '').replace('USDT', '')
        
        if exchange == 'gate' or exchange == 'auto':
            kl = _get_k_gate(symbol=clean_symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=clean_symbol, timeframe=timeframe, limit=limit)
            return kl or []
        elif exchange == 'binance':
            kl = _get_k_bin(symbol=clean_symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_gate(symbol=clean_symbol, timeframe=timeframe, limit=limit)
            return kl or []
        else:
            kl = _get_k_gate(symbol=clean_symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=clean_symbol, timeframe=timeframe, limit=limit)
            return kl or []
    except Exception as e:
        print(f"⚠️  获取K线数据失败 {symbol}: {e}", file=sys.stderr)
        return []
    return []


def scan_with_vision(symbol: str, matcher, exchange: str = 'gate') -> List[Dict]:
    """使用视觉匹配扫描单个币种"""
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"视觉匹配扫描: {symbol}", file=sys.stderr)
    print('='*80, file=sys.stderr)
    
    # 获取K线数据
    klines_5m = get_klines(symbol, '5m', limit=200, exchange=exchange)
    klines_15m = get_klines(symbol, '15m', limit=200, exchange=exchange)
    
    if not klines_15m or len(klines_15m) < 50:
        print(f"⚠️  {symbol}: K线数据不足", file=sys.stderr)
        return []
    
    klines_dict = {
        '5m': klines_5m or [],
        '15m': klines_15m
    }
    
    # 混合视觉匹配
    try:
        results = matcher.match_patterns(
            klines_dict=klines_dict,
            symbol=symbol,
            timeframe='15m'
        )
        
        # 转换为字典格式
        vision_results = []
        for result in results:
            vision_results.append({
                'symbol': symbol,
                'timeframe': '15m',
                'pattern_id': result.pattern_id,
                'pattern_name': result.pattern_name,
                'pattern_type': result.pattern_type,
                'algorithm_score': result.algorithm_score,
                'vision_score': result.vision_score,
                'final_score': result.final_score,
                'scan_time': datetime.now().isoformat()
            })
        
        if vision_results:
            vision_scored = sum(1 for r in vision_results if r.get('vision_score') is not None)
            print(f"✓ 找到 {len(vision_results)} 个候选（视觉覆盖 {vision_scored}/{len(vision_results)}）", file=sys.stderr)
            print(f"  Top 3:", file=sys.stderr)
            for i, r in enumerate(vision_results[:3], 1):
                vision_score = r.get('vision_score')
                vision_score_str = f"{vision_score:.3f}" if isinstance(vision_score, (int, float)) else "未视觉"
                print(
                    f"    {i}. {r['pattern_name']} (算法:{r['algorithm_score']:.3f}, "
                    f"视觉:{vision_score_str}, 综合:{r['final_score']:.3f})",
                    file=sys.stderr
                )
        else:
            print(f"✗ 未找到匹配", file=sys.stderr)
        
        return vision_results
    
    except Exception as e:
        print(f"✗ 视觉匹配失败 {symbol}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return []


def build_summary(results: List[Dict]) -> Dict:
    if not results:
        return {
            "symbols": [],
            "total_matches": 0,
            "vision_coverage": "0/0"
        }

    def fmt_score(val):
        return round(val, 6) if isinstance(val, (int, float)) else None

    grouped: Dict[str, List[Dict]] = {}
    for item in results:
        grouped.setdefault(item.get('symbol', 'UNKNOWN'), []).append(item)

    summary_rows = []
    total_vision_hits = 0
    total_rows = 0

    for symbol, items in sorted(grouped.items()):
        algo_top = max(items, key=lambda r: r.get('algorithm_score', 0))
        final_top = max(items, key=lambda r: r.get('final_score', 0))

        vision_hits = sum(1 for r in items if r.get('vision_score') is not None)
        total_vision_hits += vision_hits
        total_rows += len(items)

        summary_rows.append({
            "symbol": symbol,
            "algorithm_top_pattern": algo_top.get('pattern_name'),
            "algorithm_score": fmt_score(algo_top.get('algorithm_score')),
            "final_top_pattern": final_top.get('pattern_name'),
            "final_score": fmt_score(final_top.get('final_score')),
            "vision_score": fmt_score(final_top.get('vision_score')),
            "vision_coverage": f"{vision_hits}/{len(items)}",
            "rank_changed": algo_top.get('pattern_name') != final_top.get('pattern_name'),
            "final_vision_evaluated": final_top.get('vision_score') is not None
        })

    return {
        "symbols": summary_rows,
        "total_matches": len(results),
        "vision_coverage": f"{total_vision_hits}/{total_rows}"
    }

def save_vision_results(results: List[Dict], timestamp: str):
    """保存视觉匹配结果"""
    import json

    payload = {
        "generated_at": datetime.now().isoformat(),
        "results": results,
        "summary": build_summary(results)
    }
    
    result_file = VISION_RESULTS / f'vision_results_{timestamp}.json'
    result_file.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding='utf-8'
    )
    print(f"✅ 视觉匹配结果已保存: {result_file.name}", file=sys.stderr)

def summarize_results(results: List[Dict], timestamp: str):
    if not results:
        print("\n视觉/算法匹配对比汇总: 无结果")
        return

    def fmt_score(val):
        return f"{val:.3f}" if isinstance(val, (int, float)) else "N/A"

    summary = build_summary(results)
    lines = []
    lines.append("# 视觉/算法匹配对比汇总\n")
    lines.append("| 币种 | 算法Top(模式) | 算法分 | 综合Top(模式) | 综合分 | 视觉分 | 视觉覆盖 | 排名变化 |")
    lines.append("|------|---------------|--------|----------------|--------|--------|----------|----------|")

    for row in summary.get('symbols', []):
        vision_cell = fmt_score(row.get('vision_score'))
        if not row.get('final_vision_evaluated'):
            vision_cell = "未视觉"
        lines.append(
            f"| {row.get('symbol', 'N/A')} | {row.get('algorithm_top_pattern', 'N/A')} | "
            f"{fmt_score(row.get('algorithm_score'))} | {row.get('final_top_pattern', 'N/A')} | "
            f"{fmt_score(row.get('final_score'))} | {vision_cell} | "
            f"{row.get('vision_coverage', '0/0')} | {'是' if row.get('rank_changed') else '否'} |"
        )

    summary_text = "\n".join(lines) + "\n"
    print("\n" + summary_text)

    summary_file = VISION_RESULTS / f'vision_summary_{timestamp}.md'
    summary_file.write_text(summary_text, encoding='utf-8')
    print(f"✅ 汇总已保存: {summary_file.name}", file=sys.stderr)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ABU Gemini Flash 视觉匹配扫描器（每4小时）')
    parser.add_argument('--symbols', type=int, default=10, help='扫描币种数量（默认10，成本控制）')
    parser.add_argument('--symbols-list', type=str, default='', help='指定币种列表（逗号分隔，如 BTC,ETH 或 BTC_USDT）')
    parser.add_argument('--start-index', type=int, default=1, help='从第几个币种开始（1-based）')
    parser.add_argument('--exchange', type=str, default='gate', help='交易所')
    parser.add_argument('--once', action='store_true', help='只执行一次（不循环）')
    parser.add_argument('--interval', type=int, default=14400, help='扫描间隔（秒，默认14400=4小时）')
    parser.add_argument('--min-similarity', type=float, default=0.5, help='算法筛选最小相似度')
    parser.add_argument('--max-candidates', type=int, default=10, help='算法候选数（默认10）')
    parser.add_argument('--vision-all', action='store_true', help='对全部候选进行视觉匹配')
    parser.add_argument('--vision-top-n', type=int, default=2, help='视觉匹配候选数（默认2）')
    parser.add_argument('--vision-max-calls', type=int, default=2, help='每次扫描最大视觉调用数（默认2）')
    parser.add_argument('--cache-ttl', type=int, default=300, help='视觉缓存时间（秒）')
    parser.add_argument('--vision-model', type=str, default='google/gemini-2.5-flash-image', help='视觉模型名称')
    
    args = parser.parse_args()
    
    # 初始化混合视觉匹配器
    print("初始化Gemini Flash视觉匹配器...", file=sys.stderr)
    try:
        from abu.hybrid_vision_pattern_matcher import HybridVisionPatternMatcher
        
        matcher = HybridVisionPatternMatcher(
            min_similarity=args.min_similarity,
            max_candidates=args.max_candidates,
            use_vision=True,  # 启用视觉匹配
            use_all_candidates=args.vision_all,
            vision_top_n=args.vision_top_n,
            max_vision_calls_per_scan=args.vision_max_calls,
            vision_model=args.vision_model,
            enable_cache=True,
            cache_ttl=args.cache_ttl
        )
        
        stats = matcher.get_match_statistics()
        print(f"✓ 视觉匹配器已初始化", file=sys.stderr)
        print(f"  - 模式库: {stats['algorithm_matcher']['pattern_count']} 个模式", file=sys.stderr)
        print(f"  - 视觉匹配: 启用（Gemini Flash）", file=sys.stderr)
        print(f"  - 缓存: {'启用' if stats['cache_enabled'] else '禁用'}", file=sys.stderr)
    
    except Exception as e:
        print(f"✗ 匹配器初始化失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1
    
    # 使用Top 10币种（成本控制）
    if args.symbols_list:
        raw_symbols = [s.strip().upper() for s in args.symbols_list.split(',') if s.strip()]
        symbols = []
        for sym in raw_symbols:
            if '_' not in sym:
                symbols.append(f"{sym}_USDT")
            else:
                symbols.append(sym)
    else:
        symbols = TOP_10_SYMBOLS[:args.symbols]
        start_index = max(args.start_index, 1) - 1
        if start_index:
            symbols = symbols[start_index:]
    
    def run_scan():
        """执行一次扫描"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"开始视觉匹配扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", file=sys.stderr)
        print('='*80, file=sys.stderr)
        
        all_results = []
        start_time = time.time()
        
        for i, symbol in enumerate(symbols, 1):
            if symbol.replace('_USDT', '') in EXCL:
                continue
            
            print(f"\n[{i}/{len(symbols)}] 扫描 {symbol}...", file=sys.stderr)
            results = scan_with_vision(symbol, matcher, args.exchange)
            all_results.extend(results)
            
            # 避免API限流
            if i < len(symbols):
                time.sleep(2)
        
        elapsed = time.time() - start_time
        
        # 保存结果
        save_vision_results(all_results, timestamp)
        summarize_results(all_results, timestamp)
        
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"视觉匹配扫描完成", file=sys.stderr)
        print(f"  - 耗时: {elapsed:.1f} 秒", file=sys.stderr)
        print(f"  - 总匹配数: {len(all_results)}", file=sys.stderr)
        print(f"  - 结果文件: vision_results_{timestamp}.json", file=sys.stderr)
        print('='*80, file=sys.stderr)
        
        return all_results
    
    if args.once:
        # 只执行一次
        run_scan()
    else:
        # 循环执行（每4小时）
        print(f"\n开始循环视觉匹配扫描（每 {args.interval} 秒 = {args.interval/3600:.1f} 小时）", file=sys.stderr)
        print("按 Ctrl+C 停止\n", file=sys.stderr)
        
        try:
            while True:
                run_scan()
                
                print(f"\n下次扫描将在 {args.interval} 秒后（{args.interval/3600:.1f} 小时）...", file=sys.stderr)
                time.sleep(args.interval)
        
        except KeyboardInterrupt:
            print("\n\n视觉匹配扫描已停止", file=sys.stderr)


if __name__ == '__main__':
    main()
