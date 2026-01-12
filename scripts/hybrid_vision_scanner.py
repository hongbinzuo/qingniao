#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合视觉扫描器 - 扫描Top 10币种，每小时执行
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

# Top 10币种
TOP_10_SYMBOLS = [
    'BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'SOL_USDT', 'XRP_USDT',
    'ADA_USDT', 'DOGE_USDT', 'TON_USDT', 'AVAX_USDT', 'SHIB_USDT'
]

# 排除稳定币
EXCL = set(['USDT', 'USDC', 'DAI', 'BUSD', 'FDUSD', 'TUSD', 'PYUSD', 'USDE', 'GUSD', 'EURT'])


def get_klines(symbol: str, timeframe: str, limit: int, exchange: str = 'gate', days: int = None) -> list:
    """获取K线数据（优先Gate.io，支持扩展）"""
    try:
        # 导入K线获取函数
        try:
            from generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
            from generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
        except ImportError:
            try:
                from src.generate_comprehensive_trading_plans import get_kline_gateio as _get_k_gate
                from src.generate_comprehensive_trading_plans import get_kline_binance as _get_k_bin
            except ImportError:
                print("⚠️  无法导入K线获取函数")
                return []
        
        # 如果提供了days参数，尝试使用扩展API
        if days is not None and exchange in ['gate', 'auto']:
            try:
                from src.kline_db import get_klines as get_klines_db
                klines = get_klines_db(symbol, timeframe, limit=days * 96 if timeframe == '15m' else limit, exchange=exchange)
                if klines:
                    return klines
            except Exception:
                pass
        
        # 标准API获取
        if exchange == 'gate' or exchange == 'auto':
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        elif exchange == 'binance':
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
        else:
            kl = _get_k_gate(symbol=symbol, timeframe=timeframe, limit=limit)
            if kl:
                return kl
            kl = _get_k_bin(symbol=symbol, timeframe=timeframe, limit=limit)
            return kl or []
    except Exception as e:
        print(f"⚠️  获取K线数据失败 {symbol}: {e}")
        return []
    return []


def scan_symbol(
    matcher,
    symbol: str,
    exchange: str = 'gate'
) -> list:
    """扫描单个币种"""
    print(f"\n{'='*80}")
    print(f"扫描 {symbol}")
    print('='*80)
    
    # 获取K线数据（90天历史，但只使用最近的数据）
    klines_5m = get_klines(symbol, '5m', limit=200, exchange=exchange)
    klines_15m = get_klines(symbol, '15m', limit=200, exchange=exchange)
    
    if not klines_15m or len(klines_15m) < 50:
        print(f"⚠️  {symbol}: K线数据不足")
        return []
    
    klines_dict = {
        '5m': klines_5m or [],
        '15m': klines_15m
    }
    
    # 混合匹配
    results = matcher.match_patterns(
        klines_dict=klines_dict,
        symbol=symbol,
        timeframe='15m'
    )
    
    # 显示结果
    if results:
        print(f"\n✓ 找到 {len(results)} 个匹配")
        print(f"\nTop 5匹配:")
        for i, result in enumerate(results[:5], 1):
            print(f"  {i}. {result.pattern_name}")
            print(f"     算法分数: {result.algorithm_score:.3f}")
            if result.vision_score:
                print(f"     视觉分数: {result.vision_score:.3f}")
            print(f"     综合分数: {result.final_score:.3f}")
            print()
    else:
        print(f"✗ 未找到匹配")
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='混合视觉扫描器')
    parser.add_argument('--symbols', type=int, default=10, help='扫描币种数量')
    parser.add_argument('--exchange', type=str, default='gate', help='交易所')
    parser.add_argument('--vision-top-n', type=int, default=None, help='视觉匹配Top N（v3.0默认：全部候选，None=全部）')
    parser.add_argument('--use-top-n-only', action='store_true', help='只对Top N使用视觉匹配（默认：全部候选，v3.0特性）')
    parser.add_argument('--once', action='store_true', help='只执行一次（不循环）')
    parser.add_argument('--interval', type=int, default=3600, help='扫描间隔（秒，默认3600=1小时）')
    parser.add_argument('--min-similarity', type=float, default=0.5, help='最小相似度阈值')
    parser.add_argument('--disable-vision', action='store_true', help='禁用AI视觉匹配（只使用算法）')
    
    args = parser.parse_args()
    
    # 初始化匹配器
    print("初始化混合视觉匹配器...")
    try:
        from abu.hybrid_vision_pattern_matcher import HybridVisionPatternMatcher
        
        matcher = HybridVisionPatternMatcher(
            min_similarity=args.min_similarity,
            max_candidates=20,
            use_vision=not args.disable_vision,
            use_all_candidates=not args.use_top_n_only,  # v3.0默认True（全部候选）
            vision_top_n=args.vision_top_n,
            vision_model="google/gemini-2.5-flash-image",  # 或 "google/gemini-3-flash-preview" (如果OpenRouter支持)
            enable_cache=True,
            cache_ttl=300  # 5分钟缓存
        )
        
        stats = matcher.get_match_statistics()
        print(f"✓ 匹配器已初始化")
        print(f"  - 模式库: {stats['algorithm_matcher']['pattern_count']} 个模式")
        print(f"  - 视觉匹配: {'启用（v3.0: 全部候选）' if stats['vision_enabled'] else '禁用'}")
        if stats['vision_enabled'] and stats.get('vision_top_n'):
            print(f"  - 视觉Top N: {stats['vision_top_n']}")
        print(f"  - 缓存: {'启用' if stats['cache_enabled'] else '禁用'}")
    
    except Exception as e:
        print(f"✗ 匹配器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    symbols = TOP_10_SYMBOLS[:args.symbols]
    
    if args.once:
        # 只执行一次
        all_results = []
        for symbol in symbols:
            if symbol.replace('_USDT', '') in EXCL:
                continue
            results = scan_symbol(matcher, symbol, args.exchange)
            all_results.extend(results)
            time.sleep(1)  # 避免API限流
        
        print(f"\n{'='*80}")
        print(f"扫描完成")
        print(f"总共找到 {len(all_results)} 个匹配")
        print('='*80)
    
    else:
        # 循环执行
        print(f"\n开始循环扫描（每 {args.interval} 秒）")
        print("按 Ctrl+C 停止\n")
        
        try:
            while True:
                start_time = time.time()
                
                all_results = []
                for symbol in symbols:
                    if symbol.replace('_USDT', '') in EXCL:
                        continue
                    results = scan_symbol(matcher, symbol, args.exchange)
                    all_results.extend(results)
                    time.sleep(1)  # 避免API限流
                
                elapsed = time.time() - start_time
                print(f"\n{'='*80}")
                print(f"本轮扫描完成（耗时 {elapsed:.1f} 秒）")
                print(f"找到 {len(all_results)} 个匹配")
                print(f"下次扫描将在 {args.interval} 秒后...")
                print('='*80)
                
                # 等待到下次扫描时间
                sleep_time = args.interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            print("\n\n扫描已停止")


if __name__ == '__main__':
    main()

